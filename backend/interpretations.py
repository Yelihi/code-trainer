"""General interpretations retain their immutable source version and previous attempts."""
import json
import re
from . import ai, db, resources, usage, ai_settings
from .interpretation_schema import InterpretationDraft


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS interpretations (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, resource_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0), source_name TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('queued','running','ready','failed','interrupted')),
        data TEXT, error TEXT NOT NULL DEFAULT '', model TEXT NOT NULL,
        attempt INTEGER NOT NULL DEFAULT 1, archived INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,id),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')
    columns = {row['name'] for row in c.execute('PRAGMA table_info(interpretations)')}
    if 'attempt' not in columns:
        c.execute('ALTER TABLE interpretations ADD COLUMN attempt INTEGER NOT NULL DEFAULT 1')
    if 'archived' not in columns:
        c.execute('ALTER TABLE interpretations ADD COLUMN archived INTEGER NOT NULL DEFAULT 0')
    c.execute('CREATE INDEX IF NOT EXISTS interpretations_history ON interpretations(owner,created_at DESC,id DESC)')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS interpretations_pending ON interpretations(owner,resource_id,revision) WHERE state IN ('queued','running')")
    # Each concurrent request identity must still replay after the shared job completes.
    c.execute('''CREATE TABLE IF NOT EXISTS interpretation_requests (
        owner TEXT NOT NULL, request_id TEXT NOT NULL, interpretation_id TEXT NOT NULL,
        PRIMARY KEY(owner,request_id),
        FOREIGN KEY(owner,interpretation_id) REFERENCES interpretations(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS interpretation_retries (
        owner TEXT NOT NULL, request_id TEXT NOT NULL, interpretation_id TEXT NOT NULL,
        PRIMARY KEY(owner,request_id),
        FOREIGN KEY(owner,interpretation_id) REFERENCES interpretations(owner,id))''')


def view(owner, identifier):
    from . import service
    row = db.one('SELECT * FROM interpretations WHERE owner=? AND id=?', (owner, identifier))
    if not row:
        raise service.Error('해석 문서를 찾을 수 없습니다.', 404)
    document = row.pop('data')
    row['document'] = json.loads(document) if document else None
    row.pop('owner')
    row['current_revision'] = resources.view(owner, row['resource_id'])['revision']
    return row


def listing(owner, page, resource_id=None, archived=False):
    if resource_id:
        resources.view(owner, resource_id)
    where = ' WHERE owner=? AND archived=?' + (' AND resource_id=?' if resource_id else '')
    args = (owner, int(archived), resource_id) if resource_id else (owner, int(archived))
    with db.connect() as c:
        total = c.execute('SELECT COUNT(*) FROM interpretations' + where, args).fetchone()[0]
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        items = c.execute('''SELECT id,resource_id,revision,source_name,state,created_at,
                            COALESCE(json_extract(data,'$.title'),source_name) AS title
                            FROM interpretations''' + where + ' ORDER BY created_at DESC,id DESC LIMIT 20 OFFSET ?', (*args, (page - 1) * 20))
        return dict(items=[dict(r) for r in items], total=total, page=page, pages=pages)


def begin(owner, data):
    from . import service
    with db.connect(write=True) as c:
        previous = c.execute('''SELECT i.* FROM interpretation_requests r JOIN interpretations i
                                ON i.owner=r.owner AND i.id=r.interpretation_id
                                WHERE r.owner=? AND r.request_id=?''', (owner, data.request_id)).fetchone()
        if previous:
            if (previous['resource_id'], previous['revision']) != (data.resource_id, data.revision):
                raise service.Error('같은 요청 ID의 자료 또는 버전이 달라졌습니다.', 409)
            identifier, fresh = previous['id'], False
        else:
            source = resources.version(owner, data.resource_id, data.revision)
            if not (source['content'] or '').strip():
                raise service.Error('저장된 본문이 있는 버전을 선택해주세요.', 409)
            pending = c.execute("SELECT id FROM interpretations WHERE owner=? AND resource_id=? AND revision=? AND state IN ('queued','running')", (owner, data.resource_id, data.revision)).fetchone()
            fresh = pending is None
            identifier = pending['id'] if pending else service.uid()
            if fresh:
                if not ai.available(owner):
                    raise service.Error('AI 설정이 필요합니다. 원문은 그대로 보관됩니다.', 503)
                service.rate('interpretation:' + owner, 5, 3600)
                c.execute('''INSERT INTO interpretations(id,owner,resource_id,revision,source_name,state,model,created_at,updated_at)
                             VALUES (?,?,?,?,?,'queued',?,?,?)''', (identifier, owner, data.resource_id, data.revision, source['name'], ai_settings.model_name(owner), service.now(), service.now()))
            c.execute('INSERT INTO interpretation_requests VALUES (?,?,?)', (owner, data.request_id, identifier))
    return view(owner, identifier), fresh


def retry(owner, identifier, request_id):
    from . import service
    with db.connect(write=True) as c:
        row = c.execute('SELECT * FROM interpretations WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        if not row:
            raise service.Error('해석 문서를 찾을 수 없습니다.', 404)
        previous = c.execute('SELECT interpretation_id FROM interpretation_retries WHERE owner=? AND request_id=?', (owner, request_id)).fetchone()
        if previous:
            if previous['interpretation_id'] != identifier:
                raise service.Error('같은 요청 ID의 해석 자료가 달라졌습니다.', 409)
            fresh = False
        else:
            if row['archived']:
                raise service.Error('삭제한 해석은 복원한 뒤 다시 시도해주세요.', 409)
            if row['state'] not in ('failed', 'interrupted'):
                raise service.Error('실패하거나 중단된 해석만 다시 시도할 수 있습니다.', 409)
            if not ai.available(owner):
                raise service.Error('AI 설정이 필요합니다. 원문은 그대로 보관됩니다.', 503)
            service.rate('interpretation:' + owner, 5, 3600)
            c.execute("UPDATE interpretations SET state='queued',data=NULL,error='',model=?,attempt=attempt+1,updated_at=? WHERE owner=? AND id=?",
                      (ai_settings.model_name(owner), service.now(), owner, identifier))
            c.execute('INSERT INTO interpretation_retries VALUES (?,?,?)', (owner, request_id, identifier))
            fresh = True
    result = view(owner, identifier)
    return result, fresh


def archive(owner, identifier, archived):
    from . import service
    with db.connect(write=True) as c:
        row = c.execute('SELECT state FROM interpretations WHERE owner=? AND id=?', (owner, identifier)).fetchone()
        if not row:
            raise service.Error('해석 문서를 찾을 수 없습니다.', 404)
        if archived and row['state'] in ('queued', 'running'):
            raise service.Error('해석이 끝난 뒤 삭제해주세요.', 409)
        c.execute('UPDATE interpretations SET archived=?,updated_at=? WHERE owner=? AND id=?',
                  (int(archived), service.now(), owner, identifier))
    return view(owner, identifier)


def generate(identifier, attempt=None):
    from . import service
    with db.connect(write=True) as c:
        if attempt is None:
            current = c.execute('SELECT attempt FROM interpretations WHERE id=?', (identifier,)).fetchone()
            attempt = current['attempt'] if current else None
        claimed = c.execute("UPDATE interpretations SET state='running',updated_at=? WHERE id=? AND attempt=? AND state='queued'", (service.now(), identifier, attempt)).rowcount
        row = c.execute('SELECT * FROM interpretations WHERE id=?', (identifier,)).fetchone()
    if not claimed:
        return
    try:
        source = resources.version(row['owner'], row['resource_id'], row['revision'])
        token = usage.scope.set((row['owner'], identifier))
        try:
            result = ai.generate(InterpretationDraft,
                'Explain the saved source in Korean. Organize 1-6 sections with earlier-section prerequisite IDs. '
                'Write a concise summary, then give each section a substantive explanation rather than repeating that summary. '
                'When the source contains code, explain the relevant code step by step: what its inputs and outputs are, '
                'what each important operation does, why it works, and any limits or edge cases actually described by the source. '
                'Preserve representative original code in source_quotes as an EXACT contiguous substring of content, '
                'including its full Markdown code fence when it fits the 4000-character limit. '
                'Do not paraphrase, truncate, add ellipses, or normalize source_quotes. '
                'Use other source_quotes for the nearby original explanation that supports the code. '
                'When a code block exceeds the quote limit, choose a meaningful exact contiguous excerpt and explain its context in body. '
                'Keep explanations grounded; put additional knowledge ONLY in extensions and illustrative examples in examples. '
                'Questions invite the learner to explain in their own words. Do not invent code when the source has none; no execution language is required.',
                {'source_name': source['name'], 'revision': row['revision'], 'content': source['content']})
        finally:
            usage.scope.reset(token)
        for section in result.sections:
            for index, quote in enumerate(section.source_quotes):
                if quote in source['content']:
                    continue
                # Recover formatting-only differences while keeping the stored quote verbatim.
                pattern = r'\s+'.join(map(re.escape, re.split(r'\s+', quote.strip())))
                match = re.search(pattern, source['content'])
                if not match:
                    raise ai.InvalidDraft('AI가 원문에 없는 문장이나 코드를 인용해 해석을 저장하지 못했습니다. 원문은 보존되었습니다. 이 해석에서 다시 시도해주세요.')
                section.source_quotes[index] = match.group()
        db.execute("UPDATE interpretations SET state='ready',data=?,updated_at=? WHERE id=? AND attempt=? AND state='running'", (result.model_dump_json(), service.now(), identifier, attempt))
    except Exception as error:
        message = str(error) if isinstance(error, ai.AIError) else '해석을 완료하지 못했습니다. 원문은 보존되어 있으니 다시 시도해주세요.'
        db.execute("UPDATE interpretations SET state='failed',error=?,updated_at=? WHERE id=? AND attempt=? AND state='running'", (message, service.now(), identifier, attempt))

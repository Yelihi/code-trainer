"""General interpretations retain their immutable source version and previous attempts."""
import json
import os
from . import ai, db, resources, usage
from .interpretation_schema import InterpretationDraft


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS interpretations (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, resource_id TEXT NOT NULL,
        revision INTEGER NOT NULL CHECK(revision>0), source_name TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('queued','running','ready','failed','interrupted')),
        data TEXT, error TEXT NOT NULL DEFAULT '', model TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,id),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')
    c.execute('CREATE INDEX IF NOT EXISTS interpretations_history ON interpretations(owner,created_at DESC,id DESC)')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS interpretations_pending ON interpretations(owner,resource_id,revision) WHERE state IN ('queued','running')")
    # Each concurrent request identity must still replay after the shared job completes.
    c.execute('''CREATE TABLE IF NOT EXISTS interpretation_requests (
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


def listing(owner, page, resource_id=None):
    if resource_id:
        resources.view(owner, resource_id)
    where = ' WHERE owner=?' + (' AND resource_id=?' if resource_id else '')
    args = (owner, resource_id) if resource_id else (owner,)
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
                if not ai.available():
                    raise service.Error('AI 설정이 필요합니다. 원문은 그대로 보관됩니다.', 503)
                service.rate('interpretation:' + owner, 5, 3600)
                c.execute('''INSERT INTO interpretations(id,owner,resource_id,revision,source_name,state,model,created_at,updated_at)
                             VALUES (?,?,?,?,?,'queued',?,?,?)''', (identifier, owner, data.resource_id, data.revision, source['name'], os.environ.get('AI_MODEL', ''), service.now(), service.now()))
            c.execute('INSERT INTO interpretation_requests VALUES (?,?,?)', (owner, data.request_id, identifier))
    return view(owner, identifier), fresh


def generate(identifier):
    from . import service
    with db.connect(write=True) as c:
        claimed = c.execute("UPDATE interpretations SET state='running',updated_at=? WHERE id=? AND state='queued'", (service.now(), identifier)).rowcount
        row = c.execute('SELECT * FROM interpretations WHERE id=?', (identifier,)).fetchone()
    if not claimed:
        return
    try:
        source = resources.version(row['owner'], row['resource_id'], row['revision'])
        token = usage.scope.set((row['owner'], identifier))
        try:
            result = ai.generate(InterpretationDraft,
                'Explain the saved source in Korean. Organize 1-6 sections with earlier-section prerequisite IDs. '
                'Use short EXACT substrings of content for source_quotes, without ellipses or normalization. '
                'Keep explanations grounded; put additional knowledge ONLY in extensions and illustrative examples in examples. '
                'Questions invite the learner to explain in their own words. Code is optional; no execution language is required.',
                {'source_name': source['name'], 'revision': row['revision'], 'content': source['content']})
        finally:
            usage.scope.reset(token)
        if any(quote not in source['content'] for section in result.sections for quote in section.source_quotes):
            raise ai.InvalidDraft('AI가 제시한 인용이 저장된 원문과 일치하지 않습니다. 다시 해석해주세요.')
        db.execute("UPDATE interpretations SET state='ready',data=?,updated_at=? WHERE id=? AND state='running'", (result.model_dump_json(), service.now(), identifier))
    except Exception as error:
        message = str(error) if isinstance(error, ai.AIError) else '해석을 완료하지 못했습니다. 원문은 보존되어 있으니 다시 시도해주세요.'
        db.execute("UPDATE interpretations SET state='failed',error=?,updated_at=? WHERE id=? AND state='running'", (message, service.now(), identifier))

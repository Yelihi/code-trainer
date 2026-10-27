"""Explicit worksheet generation from immutable general interpretations."""
import json
from . import ai_settings, ai, db, interpretations, usage
from .worksheet_schema import WorksheetDraft


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS worksheets (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL, interpretation_id TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('queued','running','ready','failed','interrupted')),
        data TEXT, error TEXT NOT NULL DEFAULT '', model TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE(owner,id),
        FOREIGN KEY(owner,interpretation_id) REFERENCES interpretations(owner,id))''')
    c.execute('CREATE INDEX IF NOT EXISTS worksheets_history ON worksheets(owner,created_at DESC,id DESC)')
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS worksheets_pending ON worksheets(owner,interpretation_id) WHERE state IN ('queued','running')")
    c.execute('''CREATE TABLE IF NOT EXISTS worksheet_requests (
        owner TEXT NOT NULL, request_id TEXT NOT NULL, worksheet_id TEXT NOT NULL,
        PRIMARY KEY(owner,request_id),
        FOREIGN KEY(owner,worksheet_id) REFERENCES worksheets(owner,id))''')


def view(owner, identifier):
    from . import service
    row = db.one('SELECT * FROM worksheets WHERE owner=? AND id=?', (owner, identifier))
    if not row:
        raise service.Error('질문지를 찾을 수 없습니다.', 404)
    data = row.pop('data')
    row.pop('owner')
    row['document'] = json.loads(data) if data else None
    interpretation = interpretations.view(owner, row['interpretation_id'])
    row.update({key: interpretation[key] for key in ('resource_id', 'revision', 'current_revision', 'source_name')})
    row['interpretation_title'] = interpretation['document']['title']
    return row


def listing(owner, page, interpretation_id=None):
    if interpretation_id:
        interpretations.view(owner, interpretation_id)
    where = ' WHERE w.owner=?' + (' AND w.interpretation_id=?' if interpretation_id else '')
    args = (owner, interpretation_id) if interpretation_id else (owner,)
    with db.connect() as c:
        total = c.execute('SELECT COUNT(*) FROM worksheets w' + where, args).fetchone()[0]
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        items = c.execute('''SELECT w.id,w.interpretation_id,w.state,w.created_at,i.revision,i.source_name,
            COALESCE(json_extract(w.data,'$.title'),json_extract(i.data,'$.title')) AS title
            FROM worksheets w JOIN interpretations i ON i.owner=w.owner AND i.id=w.interpretation_id'''
            + where + ' ORDER BY w.created_at DESC,w.id DESC LIMIT 20 OFFSET ?', (*args, (page - 1) * 20))
        return dict(items=[dict(r) for r in items], total=total, page=page, pages=pages)


def begin(owner, request):
    from . import service
    with db.connect(write=True) as c:
        previous = c.execute('''SELECT w.id,w.interpretation_id FROM worksheet_requests r JOIN worksheets w
            ON w.owner=r.owner AND w.id=r.worksheet_id WHERE r.owner=? AND r.request_id=?''', (owner, request.request_id)).fetchone()
        if previous:
            if previous['interpretation_id'] != request.interpretation_id:
                raise service.Error('같은 요청 ID의 해석 자료가 달라졌습니다.', 409)
            identifier, fresh = previous['id'], False
        else:
            interpretation = interpretations.view(owner, request.interpretation_id)
            if interpretation['state'] != 'ready' or not interpretation['document']:
                raise service.Error('완료된 해석에서 질문지를 만들어주세요.', 409)
            pending = c.execute("SELECT id FROM worksheets WHERE owner=? AND interpretation_id=? AND state IN ('queued','running')", (owner, request.interpretation_id)).fetchone()
            fresh = pending is None
            identifier = pending['id'] if pending else service.uid()
            if fresh:
                if not ai.available(owner):
                    raise service.Error('AI 설정이 필요합니다. 기존 해석과 질문지는 보존됩니다.', 503)
                service.rate('worksheet:' + owner, 5, 3600)
                c.execute('''INSERT INTO worksheets(id,owner,interpretation_id,state,model,created_at,updated_at)
                    VALUES (?,?,?,'queued',?,?,?)''', (identifier, owner, request.interpretation_id, ai_settings.model_name(owner), service.now(), service.now()))
            c.execute('INSERT INTO worksheet_requests VALUES (?,?,?)', (owner, request.request_id, identifier))
    return view(owner, identifier), fresh


def generate(identifier):
    from . import service
    with db.connect(write=True) as c:
        claimed = c.execute("UPDATE worksheets SET state='running',updated_at=? WHERE id=? AND state='queued'", (service.now(), identifier)).rowcount
        row = c.execute('SELECT * FROM worksheets WHERE id=?', (identifier,)).fetchone()
    if not claimed:
        return
    try:
        interpretation = interpretations.view(row['owner'], row['interpretation_id'])
        token = usage.scope.set((row['owner'], identifier))
        try:
            result = ai.generate(WorksheetDraft,
                'Create a short worksheet in Korean from this interpretation. Ask learners to explain, compare and apply '
                'concepts in their own words. Link each question to a supplied section_id. Do not provide answers, '
                'grading, mandatory code or claims of mastery. Distinguish source-grounded content from AI extensions. '
                'Return 1-12 distinct questions, each with a unique q1-q12 ID.',
                {'interpretation': interpretation['document'], 'revision': interpretation['revision']})
        finally:
            usage.scope.reset(token)
        sections = {s['id'] for s in interpretation['document']['sections']}
        if any(question.section_id not in sections for question in result.questions):
            raise ai.InvalidDraft('질문이 해석에 없는 섹션을 참조합니다. 다시 생성해주세요.')
        db.execute("UPDATE worksheets SET state='ready',data=?,updated_at=? WHERE id=? AND state='running'", (result.model_dump_json(), service.now(), identifier))
    except Exception as error:
        message = str(error) if isinstance(error, ai.AIError) else '질문지를 만들지 못했습니다. 기존 해석과 기록은 보존되어 있으니 다시 시도해주세요.'
        db.execute("UPDATE worksheets SET state='failed',error=?,updated_at=? WHERE id=? AND state='running'", (message, service.now(), identifier))

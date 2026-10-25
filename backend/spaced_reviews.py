"""Explicit self-assessed review; immutable source snapshots, no AI or mastery inference."""
import json
from datetime import datetime, timedelta
from . import db, service, materials, reference_notes


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS spaced_reviews (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), kind TEXT NOT NULL,
        origin_id TEXT NOT NULL, source_revision INTEGER NOT NULL, snapshot TEXT NOT NULL,
        due_at TEXT NOT NULL, streak INTEGER NOT NULL DEFAULT 0, revision INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL, UNIQUE(owner,kind,origin_id,source_revision))''')
    c.execute('''CREATE TABLE IF NOT EXISTS spaced_review_responses (
        owner TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
        review_id TEXT NOT NULL REFERENCES spaced_reviews(id), payload TEXT NOT NULL,
        result TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(owner,request_id))''')
    c.execute('CREATE INDEX IF NOT EXISTS spaced_review_due ON spaced_reviews(owner,due_at)')


def source(owner, kind, identifier, revision):
    if kind != 'note': return materials.read(owner, kind, identifier, revision)
    note = reference_notes.owned(owner, identifier)
    state = 'archived' if note['archived'] else 'stale' if note['revision'] != revision else 'eligible'
    return dict(title=note['title'], body=note['body'], authorship='user', state=state,
                reason='노트가 변경되거나 보관되었습니다. 최신 버전을 다시 추가해주세요.' if state != 'eligible' else '')


def view(owner, identifier, history=True):
    row = db.one('SELECT * FROM spaced_reviews WHERE owner=? AND id=?', (owner, identifier))
    if not row: raise service.Error('복습할 자료를 찾을 수 없습니다.', 404)
    row['snapshot'] = json.loads(row['snapshot'])
    try:
        current = source(owner, row['kind'], row['origin_id'], row['source_revision'])
        row.update(state=current['state'], reason=current['reason'])
    except service.Error as e:
        row.update(state='unavailable', reason=str(e))
    row['due'] = row['state'] == 'eligible' and datetime.fromisoformat(row['due_at']) <= datetime.fromisoformat(service.now())
    if history:
        row['responses'] = [dict(json.loads(r['result']), created_at=r['created_at']) for r in db.all(
            'SELECT result,created_at FROM spaced_review_responses WHERE owner=? AND review_id=? ORDER BY created_at DESC,rowid DESC LIMIT 20', (owner, identifier))]
    return row


def enroll(owner, kind, identifier, revision):
    with db.connect(write=True) as c:
        previous = c.execute('SELECT id FROM spaced_reviews WHERE owner=? AND kind=? AND origin_id=? AND source_revision=?', (owner,kind,identifier,revision)).fetchone()
        if previous: key=previous['id']
        else:
            material=source(owner,kind,identifier,revision)
            if material['state'] != 'eligible': raise service.Error(material['reason'],409)
            key,clock=service.uid(),service.now()
            snapshot={k:material[k] for k in ('title','body','authorship')}
            c.execute('INSERT INTO spaced_reviews VALUES (?,?,?,?,?,?,?,0,0,?)',
                      (key,owner,kind,identifier,revision,service.dump(snapshot),(datetime.fromisoformat(clock)+timedelta(days=1)).isoformat(),clock))
    return view(owner,key)


def find(owner,kind,identifier,revision):
    source(owner,kind,identifier,revision)
    row=db.one('SELECT id FROM spaced_reviews WHERE owner=? AND kind=? AND origin_id=? AND source_revision=?',(owner,kind,identifier,revision))
    return view(owner,row['id']) if row else None


def respond(owner,identifier,request):
    payload=service.dump(dict(id=identifier,**request.model_dump()))
    with db.connect(write=True) as c:
        receipt=c.execute('SELECT * FROM spaced_review_responses WHERE owner=? AND request_id=?',(owner,request.request_id)).fetchone()
        if receipt:
            if receipt['payload'] != payload: raise service.Error('같은 복습 요청의 내용이 다릅니다.',409)
            return json.loads(receipt['result'])
        row=view(owner,identifier,history=False)
        if row['state'] != 'eligible': raise service.Error(row['reason'],409)
        if row['revision'] != request.revision: raise service.Error('다른 탭에서 복습을 완료했습니다. 최신 일정을 확인해주세요.',409)
        if not row['due']: raise service.Error('아직 복습 예정 시각이 아닙니다.',409)
        streak=min(row['streak']+1,3) if request.response=='can_explain' else 0
        clock=service.now();due=(datetime.fromisoformat(clock)+timedelta(days=(1,3,7,14)[streak])).isoformat()
        result=dict(id=identifier,revision=row['revision']+1,due_at=due,response=request.response)
        c.execute('UPDATE spaced_reviews SET streak=?,revision=?,due_at=? WHERE owner=? AND id=?',(streak,result['revision'],due,owner,identifier))
        c.execute('INSERT INTO spaced_review_responses VALUES (?,?,?,?,?,?)',(owner,request.request_id,identifier,payload,service.dump(result),clock))
    return result


def queue(owner):
    rows=[]
    for item in db.all('SELECT id FROM spaced_reviews WHERE owner=? ORDER BY due_at,id',(owner,)):
        row=view(owner,item['id'],history=False);row['snapshot'].pop('body');rows.append(row)
    return dict(items=rows,due_count=sum(r['due'] for r in rows))

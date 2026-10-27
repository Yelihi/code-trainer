"""User-authored answers, immutable versions and receipts for lost save responses."""
import hashlib
import json
from . import db, service, worksheets


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS practice_record_versions (
        owner TEXT NOT NULL, worksheet_id TEXT NOT NULL, revision INTEGER NOT NULL,
        answers TEXT NOT NULL, summary TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(owner,worksheet_id,revision),
        FOREIGN KEY(owner,worksheet_id) REFERENCES worksheets(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS practice_record_requests (
        owner TEXT NOT NULL, worksheet_id TEXT NOT NULL, request_id TEXT NOT NULL,
        digest TEXT NOT NULL, revision INTEGER NOT NULL,
        PRIMARY KEY(owner,worksheet_id,request_id),
        FOREIGN KEY(owner,worksheet_id,revision) REFERENCES practice_record_versions(owner,worksheet_id,revision))''')


def record(row):
    if row is None:
        return None
    result = dict(row)
    result.pop('owner')
    result['answers'] = json.loads(result['answers'])
    result['source_kind'] = 'user'
    return result


def view(owner, worksheet_id):
    worksheet = worksheets.view(owner, worksheet_id)
    with db.connect() as c:
        latest = c.execute('SELECT * FROM practice_record_versions WHERE owner=? AND worksheet_id=? ORDER BY revision DESC LIMIT 1', (owner, worksheet_id)).fetchone()
        versions = c.execute('SELECT revision,updated_at FROM practice_record_versions WHERE owner=? AND worksheet_id=? ORDER BY revision DESC', (owner, worksheet_id)).fetchall()
    return dict(worksheet=worksheet, record=record(latest), versions=[dict(v) for v in versions])


def version(owner, worksheet_id, revision):
    worksheets.view(owner, worksheet_id)
    result = record(db.one('SELECT * FROM practice_record_versions WHERE owner=? AND worksheet_id=? AND revision=?', (owner, worksheet_id, revision)))
    if not result:
        raise service.Error('학습 기록 버전을 찾을 수 없습니다.', 404)
    return result


def save(owner, worksheet_id, request):
    with db.connect(write=True) as c:
        worksheet = c.execute('SELECT state,data FROM worksheets WHERE owner=? AND id=?', (owner, worksheet_id)).fetchone()
        if not worksheet:
            raise service.Error('질문지를 찾을 수 없습니다.', 404)
        if worksheet['state'] != 'ready':
            raise service.Error('준비된 질문지에서 작성해주세요.', 409)
        question_ids = {q['id'] for q in json.loads(worksheet['data'])['questions']}
        if not request.answers.keys() <= question_ids:
            raise service.Error('질문지에 없는 질문의 답변입니다.', 422)
        answers = json.dumps({k: v for k, v in request.answers.items() if v != ''}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(json.dumps([request.revision, answers, request.summary], ensure_ascii=False).encode()).hexdigest()
        receipt = c.execute('SELECT digest,revision FROM practice_record_requests WHERE owner=? AND worksheet_id=? AND request_id=?', (owner, worksheet_id, request.request_id)).fetchone()
        if receipt:
            if receipt['digest'] != digest:
                raise service.Error('같은 저장 요청의 내용이 달라졌습니다.', 409)
            return record(c.execute('SELECT * FROM practice_record_versions WHERE owner=? AND worksheet_id=? AND revision=?', (owner, worksheet_id, receipt['revision'])).fetchone())
        previous = c.execute('SELECT * FROM practice_record_versions WHERE owner=? AND worksheet_id=? ORDER BY revision DESC LIMIT 1', (owner, worksheet_id)).fetchone()
        revision = previous['revision'] if previous else 0
        if request.revision != revision:
            raise service.Error('다른 화면에서 학습 기록이 변경되었습니다. 작성분을 유지한 채 서버 최신본을 확인해주세요.', 409)
        if not previous or (previous['answers'], previous['summary']) != (answers, request.summary):
            revision += 1
            c.execute('INSERT INTO practice_record_versions VALUES (?,?,?,?,?,?)', (owner, worksheet_id, revision, answers, request.summary, service.now()))
            c.execute("UPDATE knowledge_sources SET state='stale' WHERE owner=? AND kind='practice' AND origin_id=? AND state='active'", (owner, worksheet_id))
        c.execute('INSERT INTO practice_record_requests VALUES (?,?,?,?,?)', (owner, worksheet_id, request.request_id, digest, revision))
        return record(c.execute('SELECT * FROM practice_record_versions WHERE owner=? AND worksheet_id=? AND revision=?', (owner, worksheet_id, revision)).fetchone())

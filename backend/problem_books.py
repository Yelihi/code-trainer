"""Private, reusable problems and ordered books with versioned attempts."""
import json
from datetime import datetime, timedelta
from typing import Literal
from pydantic import Field, model_validator
from . import db, service, runner
from .schema import Model, Language


class TestCase(Model):
    stdin: str = Field(default='', max_length=6000)
    expected: str = Field(max_length=6000)
    public: bool = True


class ProblemInput(Model):
    title: str = Field(min_length=1, max_length=160)
    kind: Literal['text', 'code']
    language: Language | None = None
    prompt: str = Field(min_length=1, max_length=20000)
    answer: str = Field(min_length=1, max_length=20000)
    cases: list[TestCase] = Field(default_factory=list, max_length=8)
    explanation: str = Field(default='', max_length=20000)
    source_name: str = Field(default='', max_length=255)
    source_location: str = Field(default='', max_length=160)
    resource_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    revision: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def valid(self):
        if not self.title.strip() or not self.prompt.strip() or not self.answer.strip():
            raise ValueError('제목, 문제, 정답을 입력해주세요.')
        if self.kind == 'code' and self.language is None:
            raise ValueError('코드 문제의 언어를 선택해주세요.')
        if self.kind == 'text' and self.cases:
            raise ValueError('서술형 문제에는 실행 사례를 넣을 수 없습니다.')
        return self


class VerifyInput(Model):
    problem: ProblemInput
    id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')


class CodeExecutionInput(Model):
    code: str = Field(min_length=1, max_length=24000)
    problem_revision: int = Field(ge=1)
    request_id: str = Field(min_length=8, max_length=80)
    action: Literal['run', 'submit']


class BookInput(Model):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default='', max_length=2000)
    language: Language | None = None
    problem_ids: list[str] = Field(default_factory=list, max_length=200)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def valid(self):
        if not self.title.strip() or len(set(self.problem_ids)) != len(self.problem_ids):
            raise ValueError('제목과 중복 없는 문제 순서를 확인해주세요.')
        return self


class AttemptInput(Model):
    answer: str = Field(min_length=1, max_length=24000)
    problem_revision: int = Field(ge=1)
    request_id: str = Field(min_length=8, max_length=80)


class AssessmentInput(Model):
    assessment: Literal['understood', 'retry']


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS manual_problems (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), revision INTEGER NOT NULL,
        archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS manual_problem_versions (
        problem_id TEXT NOT NULL REFERENCES manual_problems(id), revision INTEGER NOT NULL,
        data TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(problem_id,revision))''')
    c.execute('''CREATE TABLE IF NOT EXISTS manual_books (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), title TEXT NOT NULL,
        description TEXT NOT NULL, language TEXT, revision INTEGER NOT NULL,
        archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS manual_book_items (
        book_id TEXT NOT NULL REFERENCES manual_books(id), problem_id TEXT NOT NULL REFERENCES manual_problems(id),
        position INTEGER NOT NULL, PRIMARY KEY(book_id,problem_id), UNIQUE(book_id,position))''')
    c.execute('''CREATE TABLE IF NOT EXISTS manual_problem_attempts (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), problem_id TEXT NOT NULL,
        problem_revision INTEGER NOT NULL, answer TEXT NOT NULL, assessment TEXT,
        request_id TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(owner,request_id),
        FOREIGN KEY(problem_id,problem_revision) REFERENCES manual_problem_versions(problem_id,revision))''')
    if 'result' not in {column['name'] for column in c.execute('PRAGMA table_info(manual_problem_attempts)')}:
        c.execute('ALTER TABLE manual_problem_attempts ADD COLUMN result TEXT')
    c.execute('''CREATE TABLE IF NOT EXISTS manual_problem_reviews (
        owner TEXT NOT NULL REFERENCES users(id), problem_id TEXT NOT NULL REFERENCES manual_problems(id),
        due_at TEXT NOT NULL, streak INTEGER NOT NULL, PRIMARY KEY(owner,problem_id))''')


def owned(c, table, owner, identifier):
    row = c.execute(f'SELECT * FROM {table} WHERE owner=? AND id=?', (owner, identifier)).fetchone()
    if not row:
        raise service.Error('항목을 찾을 수 없습니다.', 404)
    return row


def problem(owner, identifier, revision=None, reveal=False):
    with db.connect() as c:
        row = owned(c, 'manual_problems', owner, identifier)
        revision = revision or row['revision']
        version = c.execute('SELECT data FROM manual_problem_versions WHERE problem_id=? AND revision=?', (identifier, revision)).fetchone()
        if not version:
            raise service.Error('문제 버전을 찾을 수 없습니다.', 404)
        data = json.loads(version['data'])
        data.setdefault('cases', [])
        data.setdefault('verified', False)
        if not reveal:
            data.pop('answer'); data.pop('explanation')
            data['cases'] = [case for case in data['cases'] if case['public']]
        data.pop('image_id', None)
        return dict(id=identifier, revision=revision, current_revision=row['revision'], archived=bool(row['archived']), **data)


def problems(owner):
    rows = db.all('SELECT id,revision,archived FROM manual_problems WHERE owner=? ORDER BY updated_at DESC,id DESC', (owner,))
    return {'items': [problem(owner, r['id'], reveal=True) for r in rows]}


def save_problem(owner, body, identifier=None):
    from . import resources
    if body.resource_id:
        resources.view(owner, body.resource_id)
    with db.connect(write=True) as c:
        if identifier:
            old = owned(c, 'manual_problems', owner, identifier)
            if old['revision'] != body.revision:
                raise service.Error('다른 화면에서 문제가 수정되었습니다. 새로고침해주세요.', 409)
            revision = old['revision'] + 1
            c.execute('UPDATE manual_problems SET revision=?,updated_at=?,archived=0 WHERE id=?', (revision, service.now(), identifier))
        else:
            if body.revision:
                raise service.Error('새 문제의 버전을 확인해주세요.', 422)
            identifier, revision = service.uid(), 1
            c.execute('INSERT INTO manual_problems VALUES (?,?,?,0,?,?)', (identifier, owner, revision, service.now(), service.now()))
        data = {**body.model_dump(exclude={'revision'}), 'verified': False, 'image_id': None}
        c.execute('INSERT INTO manual_problem_versions VALUES (?,?,?,?)', (identifier, revision, service.dump(data), service.now()))
    return problem(owner, identifier, reveal=True)


def checks(language, code, cases, image_id):
    results = runner.run(language, code, [case['stdin'] for case in cases], image_id=image_id)
    items = []
    for index, case in enumerate(cases):
        result = results[index] if index < len(results) else None
        items.append({'passed': bool(result and result['status'] == 'ok' and service.normalized(result['stdout']) == service.normalized(case['expected'])),
                      'status': result['status'] if result else 'not_run', 'actual': result['stdout'] if result else '',
                      'expected': case['expected'], 'stdin': case['stdin'], 'public': case['public']})
    failure = next((result for result in results if result['status'] != 'ok'), None)
    return {'status': failure['status'] if failure else 'passed' if all(item['passed'] for item in items) else 'failed',
            'stderr': failure['stderr'] if failure else '', 'tests': items}


def verify(owner, body):
    if body.problem.kind != 'code':
        raise service.Error('코드형 문제만 실행할 수 있습니다.', 422)
    saved = save_problem(owner, body.problem, body.id)
    if len(saved['cases']) < 2 or not any(case['public'] for case in saved['cases']):
        return {'problem': saved, 'result': {'status': 'incomplete', 'stderr': '공개 사례를 포함해 실행 사례를 2개 이상 추가해주세요.', 'tests': []}}
    try:
        service.rate('execute:' + owner, 30)
        image_id = runner.pin_runtime()
        result = checks(saved['language'], saved['answer'], saved['cases'], image_id)
    except runner.Unavailable as error:
        return {'problem': saved, 'result': {'status': 'unavailable', 'stderr': str(error), 'tests': []}}
    if result['status'] == 'passed':
        with db.connect(write=True) as c:
            row = owned(c, 'manual_problems', owner, saved['id'])
            if row['revision'] != saved['revision']:
                raise service.Error('검증 중 문제가 수정되었습니다. 다시 검증해주세요.', 409)
            c.execute('UPDATE manual_problem_versions SET data=json_set(data, "$.verified", json("true"), "$.image_id", ?) WHERE problem_id=? AND revision=?',
                      (image_id, saved['id'], saved['revision']))
        saved['verified'] = True
    return {'problem': saved, 'result': result}


def book(owner, identifier):
    with db.connect() as c:
        row = dict(owned(c, 'manual_books', owner, identifier))
        ids = [r['problem_id'] for r in c.execute('SELECT problem_id FROM manual_book_items WHERE book_id=? ORDER BY position', (identifier,))]
    row.pop('owner')
    row['problem_ids'] = ids
    row['problems'] = [problem(owner, key) for key in ids]
    return row


def books(owner):
    rows = db.all('SELECT id FROM manual_books WHERE owner=? ORDER BY updated_at DESC,id DESC', (owner,))
    return {'items': [book(owner, row['id']) for row in rows]}


def catalog(owner):
    authored = []
    due = {r['problem_id'] for r in review_queue(owner)['items'] if r['due']}
    solved = {r['problem_id'] for r in db.all('SELECT DISTINCT problem_id FROM manual_problem_attempts WHERE owner=?', (owner,))}
    for b in books(owner)['items']:
        authored.append(dict(id=b['id'], title=b['title'], language=b['language'], source='manual',
                             href='/problem-books/' + b['id'], count=len(b['problem_ids']),
                             solved=sum(key in solved for key in b['problem_ids']), due=sum(key in due for key in b['problem_ids']),
                             archived=bool(b['archived'])))
    generated = [dict(id=r['id'], title=r['title'], language=r['language'], source='generated',
                      href='/practice/' + r['id'], count=r['count'], archived=bool(r['withdrawn']))
                 for r in db.all('''SELECT s.id,s.context_id,s.title,json_extract(c.data,'$.language') language,
                     s.withdrawn,(SELECT COUNT(*) FROM exercises e WHERE e.set_id=s.id) count
                     FROM sets s JOIN contexts c ON c.id=s.context_id WHERE c.owner=? ORDER BY s.created_at DESC''', (owner,))]
    from . import foundations, worksheets
    foundation_items = foundations.catalog(owner)['items']
    built_in = [dict(id='foundations', title='자료구조 · 알고리즘', language='typescript', source='foundation',
                     href='/foundations', count=len(foundation_items), archived=False)] if foundation_items else []
    questions = []
    page = 1
    while True:
        batch = worksheets.listing(owner, page)
        questions.extend(dict(id=r['id'], title=r['title'], language=None, source='worksheet',
                              href='/worksheets/' + r['id'], count=0, archived=False) for r in batch['items'])
        if page >= batch['pages']:
            break
        page += 1
    return {'items': authored + generated + built_in + questions}


def save_book(owner, body, identifier=None):
    with db.connect(write=True) as c:
        for key in body.problem_ids:
            item = owned(c, 'manual_problems', owner, key)
            if item['archived']:
                raise service.Error('보관된 문제는 문제집에 담을 수 없습니다.', 409)
            data = json.loads(c.execute('SELECT data FROM manual_problem_versions WHERE problem_id=? AND revision=?', (key,item['revision'])).fetchone()['data'])
            if body.language:
                if data['language'] and data['language'] != body.language:
                    raise service.Error('문제집과 문제의 언어가 다릅니다.', 422)
            if data['kind'] == 'code' and not data.get('verified'):
                raise service.Error('코드 문제의 정답을 검증한 뒤 문제집에 담아주세요.', 409)
        if identifier:
            old = owned(c, 'manual_books', owner, identifier)
            if old['revision'] != body.revision:
                raise service.Error('다른 화면에서 문제집이 수정되었습니다. 새로고침해주세요.', 409)
            revision = old['revision'] + 1
            c.execute('UPDATE manual_books SET title=?,description=?,language=?,revision=?,updated_at=? WHERE id=?',
                      (body.title, body.description, body.language, revision, service.now(), identifier))
            c.execute('DELETE FROM manual_book_items WHERE book_id=?', (identifier,))
        else:
            if body.revision:
                raise service.Error('새 문제집의 버전을 확인해주세요.', 422)
            identifier, revision = service.uid(), 1
            c.execute('INSERT INTO manual_books VALUES (?,?,?,?,?, ?,0,?,?)',
                      (identifier, owner, body.title, body.description, body.language, revision, service.now(), service.now()))
        for position, key in enumerate(body.problem_ids):
            c.execute('INSERT INTO manual_book_items VALUES (?,?,?)', (identifier, key, position))
    return book(owner, identifier)


def attempts(owner, identifier):
    problem(owner, identifier)
    return {'items': [{**dict(r), 'result': json.loads(r['result']) if r['result'] else None} for r in db.all('SELECT id,problem_revision,answer,assessment,result,created_at FROM manual_problem_attempts WHERE owner=? AND problem_id=? ORDER BY created_at DESC,id DESC', (owner, identifier))]}


def attempt_snapshot(owner, identifier, attempt_id):
    row = db.one('SELECT problem_revision,answer,assessment,result,created_at FROM manual_problem_attempts WHERE owner=? AND problem_id=? AND id=?', (owner, identifier, attempt_id))
    if not row:
        raise service.Error('풀이를 찾을 수 없습니다.', 404)
    return {'attempt': {**row, 'result': json.loads(row['result']) if row['result'] else None}, 'problem': problem(owner, identifier, row['problem_revision'], reveal=True)}


def attempt(owner, identifier, body):
    payload = problem(owner, identifier, body.problem_revision)
    if payload['kind'] == 'code':
        raise service.Error('코드형 문제는 실행 후 제출해주세요.', 409)
    if payload['archived'] or payload['current_revision'] != body.problem_revision:
        raise service.Error('최신 문제를 다시 열어주세요.', 409)
    with db.connect(write=True) as c:
        receipt = c.execute('SELECT * FROM manual_problem_attempts WHERE owner=? AND request_id=?', (owner, body.request_id)).fetchone()
        if receipt:
            if (receipt['problem_id'],receipt['answer'],receipt['problem_revision']) != (identifier,body.answer,body.problem_revision):
                raise service.Error('같은 저장 요청의 내용이 다릅니다.', 409)
            return dict(receipt)
        clock = service.now(); key = service.uid()
        c.execute('INSERT INTO manual_problem_attempts(id,owner,problem_id,problem_revision,answer,assessment,request_id,created_at) VALUES (?,?,?,?,?,?,?,?)',
                  (key,owner,identifier,body.problem_revision,body.answer,None,body.request_id,clock))
    return {'id': key, 'problem_id': identifier, 'problem_revision': body.problem_revision, 'answer': body.answer, 'assessment': None, 'created_at': clock}


def execute_code(owner, identifier, body):
    payload = problem(owner, identifier, body.problem_revision)
    if payload['kind'] != 'code' or not payload['verified']:
        raise service.Error('검증된 코드 문제가 아닙니다.', 409)
    if payload['archived'] or payload['current_revision'] != body.problem_revision:
        raise service.Error('최신 문제를 다시 열어주세요.', 409)
    with db.connect() as c:
        version = c.execute('SELECT data FROM manual_problem_versions WHERE problem_id=? AND revision=?', (identifier, body.problem_revision)).fetchone()
        stored = json.loads(version['data'])
        if body.action == 'submit':
            receipt = c.execute('SELECT * FROM manual_problem_attempts WHERE owner=? AND request_id=?', (owner, body.request_id)).fetchone()
            if receipt:
                if (receipt['problem_id'], receipt['answer'], receipt['problem_revision']) != (identifier, body.code, body.problem_revision):
                    raise service.Error('같은 제출 요청의 내용이 다릅니다.', 409)
                return {'result': json.loads(receipt['result']), 'attempt': {**dict(receipt), 'result': json.loads(receipt['result'])}}
    cases = stored['cases'] if body.action == 'submit' else [case for case in stored['cases'] if case['public']]
    service.rate('execute:' + owner, 30)
    result = checks(stored['language'], body.code, cases, stored['image_id'])
    if body.action == 'run':
        return {'result': result, 'attempt': None}
    result['tests'] = [item if item['public'] else {'passed': item['passed'], 'status': item['status'], 'public': False} for item in result['tests']]
    result['stderr'] = result['stderr'] if result['status'].startswith('compile_') else ''
    assessment = 'understood' if result['status'] == 'passed' else 'retry'
    with db.connect(write=True) as c:
        row = owned(c, 'manual_problems', owner, identifier)
        if row['revision'] != body.problem_revision or row['archived']:
            raise service.Error('실행 중 문제가 수정되었습니다. 다시 열어주세요.', 409)
        receipt = c.execute('SELECT * FROM manual_problem_attempts WHERE owner=? AND request_id=?', (owner, body.request_id)).fetchone()
        if receipt:
            if (receipt['problem_id'], receipt['answer'], receipt['problem_revision']) != (identifier, body.code, body.problem_revision):
                raise service.Error('같은 제출 요청의 내용이 다릅니다.', 409)
            return {'result': json.loads(receipt['result']), 'attempt': {**dict(receipt), 'result': json.loads(receipt['result'])}}
        clock, key = service.now(), service.uid()
        c.execute('INSERT INTO manual_problem_attempts(id,owner,problem_id,problem_revision,answer,assessment,request_id,created_at,result) VALUES (?,?,?,?,?,?,?,?,?)',
                  (key, owner, identifier, body.problem_revision, body.code, assessment, body.request_id, clock, service.dump(result)))
        old = c.execute('SELECT streak FROM manual_problem_reviews WHERE owner=? AND problem_id=?', (owner, identifier)).fetchone()
        streak = min(old['streak'] + 1, 3) if old and assessment == 'understood' else 0
        due = (datetime.fromisoformat(clock) + timedelta(days=(1, 3, 7, 14)[streak])).isoformat()
        c.execute('INSERT INTO manual_problem_reviews VALUES (?,?,?,?) ON CONFLICT(owner,problem_id) DO UPDATE SET due_at=excluded.due_at,streak=excluded.streak',
                  (owner, identifier, due, streak))
    return {'result': result, 'attempt': {'id': key, 'problem_id': identifier, 'problem_revision': body.problem_revision, 'answer': body.code,
                                          'assessment': assessment, 'created_at': clock, 'result': result}}


def assess(owner, identifier, attempt_id, body):
    problem(owner, identifier)
    with db.connect(write=True) as c:
        row = c.execute('SELECT * FROM manual_problem_attempts WHERE owner=? AND problem_id=? AND id=?', (owner,identifier,attempt_id)).fetchone()
        if not row:
            raise service.Error('풀이를 찾을 수 없습니다.', 404)
        if row['assessment']:
            if row['assessment'] != body.assessment:
                raise service.Error('이미 평가한 풀이입니다.', 409)
            due = c.execute('SELECT due_at FROM manual_problem_reviews WHERE owner=? AND problem_id=?', (owner,identifier)).fetchone()
            return {'due_at': due['due_at'] if due else None, 'assessment': row['assessment']}
        clock = service.now()
        c.execute('UPDATE manual_problem_attempts SET assessment=? WHERE id=?', (body.assessment,attempt_id))
        old = c.execute('SELECT streak FROM manual_problem_reviews WHERE owner=? AND problem_id=?', (owner,identifier)).fetchone()
        streak = min(old['streak']+1,3) if old and body.assessment == 'understood' else 0
        due = (datetime.fromisoformat(clock) + timedelta(days=(1,3,7,14)[streak])).isoformat()
        c.execute('INSERT INTO manual_problem_reviews VALUES (?,?,?,?) ON CONFLICT(owner,problem_id) DO UPDATE SET due_at=excluded.due_at,streak=excluded.streak', (owner,identifier,due,streak))
    return {'due_at': due, 'assessment': body.assessment}


def review_queue(owner):
    rows = db.all('SELECT r.problem_id,r.due_at,r.streak,p.revision,p.archived FROM manual_problem_reviews r JOIN manual_problems p ON p.id=r.problem_id AND p.owner=r.owner WHERE r.owner=? ORDER BY r.due_at', (owner,))
    now = service.now()
    return {'items': [dict(problem_id=r['problem_id'],title=problem(owner,r['problem_id'])['title'],due_at=r['due_at'],streak=r['streak'],due=r['due_at']<=now,archived=bool(r['archived'])) for r in rows]}


def archive(owner, table, identifier):
    with db.connect(write=True) as c:
        owned(c, table, owner, identifier)
        c.execute(f'UPDATE {table} SET archived=1,updated_at=? WHERE id=?', (service.now(), identifier))
    return {'ok': True}


def solution(owner, identifier):
    item = problem(owner, identifier, reveal=True)
    if not db.one('SELECT id FROM manual_problem_attempts WHERE owner=? AND problem_id=? AND problem_revision=? LIMIT 1', (owner, identifier, item['revision'])):
        raise service.Error('현재 버전의 풀이를 먼저 저장해주세요.', 403)
    return {'answer': item['answer'], 'explanation': item['explanation']}

import hashlib
import hmac
import json
import secrets
import threading
import time
import traceback
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from . import ai, db, diagnostics, runner, source
from .sample import sample
from .schema import ContextDraft, ExerciseDraft, SetDraft

Unavailable = runner.Unavailable
MAX_GENERATION_REPAIRS = 3


class Error(Exception):
    def __init__(self, message, status=400, feedback=None):
        super().__init__(message)
        self.status = status
        self.feedback = feedback


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


def dump(value):
    return json.dumps(value, ensure_ascii=False)


_requests = defaultdict(deque)
_rate_lock = threading.Lock()


def rate(key, limit, seconds=60):
    with _rate_lock:
        values = _requests[key]
        while values and values[0] <= time.monotonic() - seconds:
            values.popleft()
        if len(values) >= limit:
            raise Error('요청이 많습니다. 잠시 후 다시 시도해주세요.', 429)
        values.append(time.monotonic())


def initialize():
    db.initialize()
    from .learning import archive_existing
    archive_existing()
    diagnostics.initialize()
    db.execute("UPDATE generations SET state='failed', stage='작업 중단', error='서버가 다시 시작되었습니다. 자료 또는 저장된 Context로 다시 생성해주세요.' WHERE state IN ('generating','validating')")
    db.execute("DELETE FROM attempts WHERE status='running'")
    db.execute("UPDATE learning_summaries SET state='failed', error='서버가 다시 시작되었습니다. 배운 내용 정리를 다시 시도해주세요.' WHERE state='running'")
    try:
        runner.cleanup()
    except runner.Unavailable:
        pass


def health():
    return {'sandbox': runner.available(), 'ai': ai.available(), 'languages': list(runner.RUNTIMES)}


def session(token):
    user = db.one('SELECT u.id, u.username, u.admin FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())) if token else None
    return {'user': user, 'setup_required': db.one('SELECT id FROM users LIMIT 1') is None}


def authenticate(credentials):
    rate('auth', 10, 60)
    user = db.one('SELECT * FROM users WHERE username=?', (credentials.username,))
    if user:
        salt, expected = user['password'].split(':')
        actual = hashlib.scrypt(credentials.password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        if not hmac.compare_digest(actual, expected):
            raise Error('사용자 이름 또는 비밀번호를 확인해주세요.', 401)
    else:
        if credentials.admin_password and not hmac.compare_digest(credentials.admin_password.encode(), b'1202'):
            raise Error('관리자 비밀번호가 올바르지 않습니다.', 403)
        salt = secrets.token_bytes(16)
        password = salt.hex() + ':' + hashlib.scrypt(credentials.password.encode(), salt=salt, n=16384, r=8, p=1).hex()
        with db.connect(write=True) as c:
            if c.execute('SELECT id FROM users LIMIT 1').fetchone():
                raise Error('사용자 이름 또는 비밀번호를 확인해주세요.', 401)
            user = {'id': uid(), 'username': credentials.username}
            c.execute('INSERT INTO users VALUES (?,?,?,?)', (user['id'], user['username'], password, int(bool(credentials.admin_password))))
    token = secrets.token_urlsafe(32)
    with db.connect(write=True) as c:
        c.execute('DELETE FROM sessions WHERE expires<?', (time.time(),))
        c.execute('INSERT INTO sessions VALUES (?,?,?)', (hashlib.sha256(token.encode()).hexdigest(), user['id'], time.time() + 86400 * 7))
    return token


def logout(token):
    db.execute('DELETE FROM sessions WHERE token=?', (hashlib.sha256(token.encode()).hexdigest(),))


def require_user(token):
    user = session(token)['user']
    if not user:
        raise Error('로그인해주세요.', 401)
    return user


def context_owned(owner, context_id):
    row = db.one('SELECT * FROM contexts WHERE id=? AND owner=?', (context_id, owner))
    if not row:
        raise Error('학습 자료를 찾을 수 없습니다.', 404)
    return row


def set_owned(owner, set_id):
    row = db.one('SELECT s.*, c.owner, c.data AS context_data FROM sets s JOIN contexts c ON c.id=s.context_id WHERE s.id=? AND c.owner=?', (set_id, owner))
    if not row:
        raise Error('사용 가능한 문제를 찾을 수 없습니다.', 404)
    return row


def exercise_owned(owner, exercise_id, active=True):
    row = db.one('SELECT * FROM exercises WHERE id=?', (exercise_id,))
    if not row:
        raise Error('문제를 찾을 수 없습니다.', 404)
    problem_set = set_owned(owner, row['set_id'])
    if active and problem_set['withdrawn']:
        raise Error('오류 검토로 제공이 중단된 문제입니다. 기존 기록은 보존됩니다.', 409)
    return row, problem_set


def summaries(owner, context_id):
    return db.all('''SELECT s.id, s.title, s.unit_id, s.withdrawn, COUNT(e.id) AS total,
        COALESCE(SUM(EXISTS(SELECT 1 FROM attempts a WHERE a.exercise_id=e.id AND a.owner=? AND a.status='passed')),0) AS completed
        FROM sets s JOIN exercises e ON e.set_id=s.id
        WHERE s.context_id=? GROUP BY s.id ORDER BY s.created_at''', (owner, context_id))


def context_view(owner, row):
    value = json.loads(row['data'])
    value.setdefault('difficulty', 'beginner')
    value.pop('learning_notes', None)
    sets = summaries(owner, row['id'])
    return {**value, 'id': row['id'], 'source_url': row['source_url'], 'created_at': row['created_at'], 'sets': sets,
        'generation': diagnostics.view(db.one('SELECT id,state,stage,context_id,set_id,unit_id,error,events FROM generations WHERE context_id=? AND owner=? AND unit_id IS NULL ORDER BY created_at DESC LIMIT 1', (row['id'], owner))),
        'unit_generations': [diagnostics.view(g) for g in db.all('''SELECT id,state,stage,context_id,set_id,unit_id,error,events
            FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY unit_id ORDER BY created_at DESC) AS position
                  FROM generations WHERE context_id=? AND owner=? AND unit_id IS NOT NULL) WHERE position=1''', (row['id'], owner))],
        'completed': sum(s['completed'] for s in sets), 'total': sum(s['total'] for s in sets)}


def contexts(owner, page=None, page_size=6):
    if page is None:
        return [context_view(owner, r) for r in db.all('SELECT * FROM contexts WHERE owner=? ORDER BY created_at DESC, id DESC', (owner,))]
    total = db.one('SELECT COUNT(*) AS n FROM contexts WHERE owner=?', (owner,))['n']
    pages = max(1, (total + page_size - 1) // page_size)
    page = min(page, pages)
    rows = db.all('SELECT * FROM contexts WHERE owner=? ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?', (owner, page_size, (page - 1) * page_size))
    keys = ('id', 'title', 'description', 'concepts', 'language', 'difficulty', 'created_at', 'completed', 'total')
    return {'items': [{k: v for k, v in context_view(owner, row).items() if k in keys} for row in rows],
            'page': page, 'pages': pages, 'total': total}


def get_context(owner, context_id):
    return context_view(owner, context_owned(owner, context_id))


def delete_context(owner, context_id):
    with db.connect(write=True) as c:
        if not c.execute('SELECT id FROM contexts WHERE id=? AND owner=?', (context_id, owner)).fetchone():
            raise Error('학습 자료를 찾을 수 없습니다.', 404)
        if c.execute("SELECT id FROM generations WHERE context_id=? AND state IN ('generating','validating')", (context_id,)).fetchone():
            raise Error('자료를 생성 중입니다. 완료된 뒤 삭제해주세요.', 409)
        exercises = 'SELECT e.id FROM exercises e JOIN sets s ON e.set_id=s.id WHERE s.context_id=?'
        if c.execute(f"SELECT id FROM attempts WHERE status='running' AND exercise_id IN ({exercises})", (context_id,)).fetchone():
            raise Error('풀이를 채점 중입니다. 완료된 뒤 삭제해주세요.', 409)
        for table in ('reports', 'progress', 'attempts'):
            c.execute(f'DELETE FROM {table} WHERE exercise_id IN ({exercises})', (context_id,))
        c.execute('DELETE FROM exercises WHERE set_id IN (SELECT id FROM sets WHERE context_id=?)', (context_id,))
        for table in ('sets', 'generation_drafts', 'generations'):
            c.execute(f'DELETE FROM {table} WHERE context_id=?', (context_id,))
        c.execute('DELETE FROM contexts WHERE id=?', (context_id,))
    return {'ok': True}


def get_set(owner, set_id):
    row = set_owned(owner, set_id)
    exercises = []
    for item in db.all("SELECT * FROM exercises WHERE set_id=? ORDER BY CASE kind WHEN 'READ' THEN 0 WHEN 'FIX' THEN 1 WHEN 'MODIFY' THEN 2 ELSE 3 END", (set_id,)):
        data = json.loads(item['data'])
        # Explicit allowlist: never serialize evaluation or hints with the exercise.
        public = {key: data[key] for key in ('kind', 'title', 'description', 'requirements', 'starter', 'public_tests')}
        public.update(id=item['id'], test_mode=data.get('test_mode', 'stdio'), hints_count=len(data['hints']),
            progress=db.one('SELECT code,answer,revision FROM progress WHERE owner=? AND exercise_id=?', (owner, item['id'])),
            passed=bool(db.one("SELECT id FROM attempts WHERE owner=? AND exercise_id=? AND status='passed'", (owner, item['id']))),
            attempt_count=db.one("SELECT COUNT(*) AS n FROM attempts WHERE owner=? AND exercise_id=? AND status!='running'", (owner, item['id']))['n'])
        exercises.append(public)
    return {'id': row['id'], 'context_id': row['context_id'], 'title': row['title'], 'version': row['version'],
        'unit_id': row['unit_id'], 'language': json.loads(row['context_data'])['language'],
        'difficulty': json.loads(row['context_data']).get('difficulty', 'beginner'), 'withdrawn': bool(row['withdrawn']), 'exercises': exercises}


def solution(owner, exercise_id):
    row, _ = exercise_owned(owner, exercise_id, active=False)
    exercise = ExerciseDraft.model_validate_json(row['data'])
    return {'code': exercise.evaluation.reference if exercise.kind != 'READ' else '',
            'answer': exercise.evaluation.read_answer if exercise.kind == 'READ' else ''}


def generation(owner, generation_id):
    row = db.one('SELECT id,state,stage,context_id,set_id,unit_id,error,events FROM generations WHERE id=? AND owner=?', (generation_id, owner))
    if not row:
        raise Error('생성 기록을 찾을 수 없습니다.', 404)
    return diagnostics.view(row)


def generations(owner):
    return [diagnostics.view(row) for row in db.all('SELECT id,state,stage,context_id,set_id,unit_id,error,events FROM generations WHERE owner=? ORDER BY created_at DESC LIMIT 30', (owner,))]


def begin_generation(owner, request):
    existing = db.one('SELECT id FROM generations WHERE owner=? AND request_id=?', (owner, request.request_id))
    if existing:
        return generation(owner, existing['id']), False
    if request.source_kind == 'context':
        context = json.loads(context_owned(owner, request.context_id)['data'])
        if context['language'] != request.language:
            raise Error('자료의 실행 언어와 요청 언어가 다릅니다.')
        if request.unit_id:
            if not any(u['id'] == request.unit_id for u in context.get('units', [])):
                raise Error('학습 단원을 찾을 수 없습니다.', 404)
            if db.one('SELECT id FROM sets WHERE context_id=? AND unit_id=?', (request.context_id, request.unit_id)):
                raise Error('이 단원의 문제 세트는 이미 준비되어 있습니다.', 409)
        elif context.get('units'):
            raise Error('문제를 생성할 단원을 선택해주세요.', 409)
    if request.source_kind != 'sample' and not ai.available():
        raise Error('AI 연결을 설정하거나 준비된 예제를 사용해주세요.', 503)
    if (request.unit_id or request.source_kind == 'sample') and not runner.available():
        raise Error('Docker 실행 환경을 준비해주세요. ./start.sh --setup', 503)
    rate(f'generate:{owner}:{request.context_id or "new"}:{request.unit_id or "plan"}', 5, 3600)
    with db.connect(write=True) as c:
        existing = c.execute('SELECT id FROM generations WHERE owner=? AND request_id=?', (owner, request.request_id)).fetchone()
        if existing:
            generation_id, fresh = existing['id'], False
        else:
            if request.context_id and not c.execute('SELECT id FROM contexts WHERE id=? AND owner=?', (request.context_id, owner)).fetchone():
                raise Error('학습 자료를 찾을 수 없습니다.', 404)
            if c.execute("SELECT id FROM generations WHERE state IN ('generating','validating')").fetchone():
                raise Error('다른 문제를 생성 중입니다. 완료 후 다시 시도해주세요.', 429)
            if request.unit_id and c.execute('SELECT id FROM sets WHERE context_id=? AND unit_id=?', (request.context_id, request.unit_id)).fetchone():
                raise Error('이 단원의 문제 세트는 이미 준비되어 있습니다.', 409)
            generation_id, fresh = uid(), True
            c.execute('INSERT INTO generations (id,owner,request_id,state,stage,context_id,unit_id,created_at) VALUES (?,?,?,?,?,?,?,?)',
                (generation_id, owner, request.request_id, 'generating', '단원 문제 생성' if request.unit_id else '자료 분석', request.context_id, request.unit_id, now()))
            if request.source_kind in ('text', 'url'):
                c.execute('INSERT INTO source_documents VALUES (?,NULL,?,?,?,?)',
                          (generation_id, request.source_kind, request.source_name,
                           request.source if request.source_kind == 'url' else None,
                           request.source if request.source_kind == 'text' else None))
    return generation(owner, generation_id), fresh


def normalized(value):
    return value.replace('\r\n', '\n').rstrip('\n')


def evaluate(language, code, tests, image_id=None):
    results = ([runner.run(language, code + '\n' + t.code, [''], image_id=image_id)[0] for t in tests]
        if tests[0].code else runner.run(language, code, [t.stdin for t in tests], image_id=image_id))
    checks = []
    for index, test in enumerate(tests):
        result = results[index] if index < len(results) else None
        checks.append({'id': test.id, 'passed': bool(result and result['status'] == 'ok' and normalized(result['stdout']) == normalized(test.expected)),
            'stdin': test.stdin, 'code': test.code, 'expected': test.expected, 'actual': result['stdout'] if result else '',
            'status': result['status'] if result else 'not_run'})
    error = next((r for r in results if r['status'] != 'ok'), None)
    return {'status': error['status'] if error else 'passed' if all(t['passed'] for t in checks) else 'failed',
        'stdout': '', 'stderr': error['stderr'] if error else '', 'exit_code': error['exit_code'] if error else 0, 'tests': checks}


def validate_set(language, draft, image_id=None):
    checks, failures = [], []
    started = time.monotonic()

    def record(kind, name, passed, result):
        checks.append({'kind': kind, 'check': name, 'passed': passed})
        if not passed:
            # Private generation feedback, never serialized in learner-facing errors.
            failures.append({'kind': kind, 'check': name,
                             'required': 'wrong output without execution errors' if name == 'starter' or name.startswith('wrong:') else 'pass all tests',
                             'result': result})
            reason = ('예측한 출력이 실제 실행 결과와 다릅니다.' if name == 'prediction' else
                      '검증용 풀이가 테스트를 통과하지 못했습니다.' if name in ('reference', 'alternative') else
                      'FIX 시작 코드가 모든 테스트를 통과하여 고칠 오류가 없습니다.' if name == 'starter' else
                      '대표 오답이 테스트를 통과하여 잘못된 풀이를 구별하지 못했습니다.')
            if result.get('status') not in ('ok', 'passed', 'failed'):
                reason = '검증용 코드 실행이 실패했습니다: ' + {
                    'runtime_error': '실행 중 오류', 'compile_error': '컴파일 오류',
                    'time_limit': '실행 시간 초과', 'memory_limit': '메모리 초과',
                    'output_limit': '출력 크기 초과', 'compile_time_limit': '컴파일 시간 초과',
                    'compile_memory_limit': '컴파일 메모리 초과', 'compile_output_limit': '컴파일 출력 크기 초과',
                }.get(result.get('status'), '실행 환경 오류')
                # Classify runtime errors without exposing messages that may contain answers.
                for error_type, explanation in (
                    ('ReferenceError', '정의되지 않은 변수·함수·클래스를 참조했습니다.'),
                    ('NameError', '정의되지 않은 이름을 참조했습니다.'),
                    ('TypeError', '값의 자료형이나 함수·생성자 호출 방식이 맞지 않습니다.'),
                    ('AttributeError', '객체에 없는 속성이나 메서드를 사용했습니다.'),
                    ('SyntaxError', '생성된 코드의 문법이 올바르지 않습니다.'),
                ):
                    if error_type + ':' in result.get('stderr', ''):
                        reason += f' · {error_type}: {explanation}'
                        break
            diagnostics.event(reason, level='warning', phase='코드 검증', kind=kind,
                              code='code_validation_failed', check=name, status=result.get('status'))

    for exercise in draft.exercises:
        if time.monotonic() - started > 240:
            raise Error('생성 검증 작업량 제한을 초과했습니다.')
        if exercise.kind == 'READ':
            result = runner.run(language, exercise.starter, [''], image_id=image_id)[0]
            passed = result['status'] == 'ok' and normalized(result['stdout']) == normalized(exercise.evaluation.read_answer)
            record('READ', 'prediction', passed, result)
            if any(t.expected for t in exercise.public_tests):
                raise Error('READ의 공개 테스트에 정답이 포함되어 있습니다.')
            continue
        tests = exercise.public_tests + exercise.evaluation.hidden_tests
        for name in ('reference', 'alternative'):
            if not getattr(exercise.evaluation, name):
                continue
            result = evaluate(language, getattr(exercise.evaluation, name), tests, image_id)
            record(exercise.kind, name, result['status'] == 'passed', result)
        for wrong in exercise.evaluation.wrong_solutions:
            target = next(t for t in tests if t.id == wrong.failing_test)
            result = evaluate(language, wrong.code, [target], image_id)
            record(exercise.kind, 'wrong:' + wrong.requirement, result['status'] == 'failed', result)
        if exercise.kind == 'FIX':
            result = evaluate(language, exercise.starter, tests, image_id)
            record('FIX', 'starter', result['status'] == 'failed', result)
    if failures:
        raise Error('문제 실행 검증에 실패했습니다.', feedback=failures)
    return checks


def generate(owner, generation_id, request):
    token = diagnostics.job.set(generation_id)
    try:
        diagnostics.event('단원 문제 생성 시작' if request.unit_id else '학습 과정 생성 시작', phase='단원별 세트 생성' if request.unit_id else '개념 분리 · 학습 순서')
        if request.source_kind == 'sample':
            context, draft = sample()
        elif request.source_kind == 'context':
            context = ContextDraft.model_validate_json(context_owned(owner, request.context_id)['data'])
            if not context.units:
                context = ai.analyze(dump(context.model_dump()), request.language, context.difficulty)
        else:
            text = source.fetch(request.source) if request.source_kind == 'url' else request.source
            db.execute('UPDATE source_documents SET content=? WHERE id=?', (text, generation_id))
            if len(text.strip()) < 20:
                raise Error('학습할 자료를 20자 이상 입력해주세요.')
            context = ai.analyze(text, request.language, request.difficulty)
            context = context.model_copy(update={'difficulty': request.difficulty, 'framework': request.framework.strip()})
            del text
        if context.language != request.language:
            raise Error('자료와 목표 언어가 맞지 않습니다. 자료 또는 언어를 변경해주세요.')
        context_id = request.context_id or uid()
        source_url = request.source if request.source_kind == 'url' else ('https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures' if request.source_kind == 'sample' else None)
        # Raw source is retained only in the administrator archive, never public context or logs.
        request.source = ''
        with db.connect(write=True) as c:
            if not request.context_id:
                c.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (context_id, owner, dump(context.model_dump()), source_url, now()))
            else:
                c.execute('UPDATE contexts SET data=? WHERE id=? AND owner=?', (dump(context.model_dump()), context_id, owner))
            c.execute('UPDATE generations SET context_id=?,stage=? WHERE id=?', (context_id, '문제 생성', generation_id))
            c.execute('UPDATE source_documents SET context_id=? WHERE id=?', (context_id, generation_id))
        diagnostics.event('학습 과정 저장 완료', units=len(context.units))
        if request.source_kind != 'sample' and not request.unit_id:
            db.execute("UPDATE generations SET state='ready',stage='개념 학습 준비 완료' WHERE id=?", (generation_id,))
            diagnostics.event('개념 학습 준비 완료 · 단원별로 문제를 생성할 수 있습니다.')
            return
        image = runner.command(['image', 'inspect', '--format', '{{.Id}}', runner.IMAGE])
        if image.returncode:
            raise runner.Unavailable('실행 이미지를 확인하지 못했습니다.')
        image_id = image.stdout.strip()
        # Containerd may discard the previous image index when the build tag is moved.
        # Retain one immutable tag per validated runtime so old problems remain executable.
        pinned = runner.command(['tag', image_id, 'code-trainer-runtime:' + image_id.removeprefix('sha256:')])
        if pinned.returncode:
            raise runner.Unavailable('문제의 실행 환경 버전을 보존하지 못했습니다.')
        completed = {s['unit_id'] for s in summaries(owner, context_id)}
        for index, unit in enumerate(context.units):
            if request.unit_id and unit.id != request.unit_id:
                continue
            if unit.id in completed:
                continue
            label = f'{index + 1}/{len(context.units)} · {unit.title}'
            cached = db.one('SELECT data,feedback FROM generation_drafts WHERE context_id=? AND unit_id=?', (context_id, unit.id))
            previous = SetDraft.model_validate_json(cached['data']) if cached else None
            feedback = json.loads(cached['feedback']) if cached else None
            if previous:
                diagnostics.event('저장된 후보에서 이어갑니다. 통과한 문제는 유지하고 실패한 문제만 수정합니다.', unit=index + 1)
            max_attempts = 1 if request.source_kind == 'sample' else 1 + MAX_GENERATION_REPAIRS
            for candidate in range(1, max_attempts + 1):
                retry_label = f' · 자동 수정 {candidate - 1}/{MAX_GENERATION_REPAIRS}' if candidate > 1 else ''
                db.execute("UPDATE generations SET state='generating',stage=?,candidate=? WHERE id=?", ('문제 생성 ' + label + retry_label, candidate, generation_id))
                diagnostics.event('단원 생성 시작', unit=index + 1, candidate=candidate, phase='단원별 세트 생성')
                try:
                    if request.source_kind != 'sample':
                        draft = previous if previous and not feedback else ai.create_set(context, unit, retry=bool(previous), previous=previous, feedback=feedback)
                    # Private checkpoint: failed/restarted jobs must not discard passing exercises.
                    db.execute('INSERT INTO generation_drafts VALUES (?,?,?,?) ON CONFLICT(context_id,unit_id) DO UPDATE SET data=excluded.data,feedback=excluded.feedback',
                               (context_id, unit.id, dump(draft.model_dump()), '[]'))
                    db.execute("UPDATE generations SET state='validating',stage=? WHERE id=?", ('코드 검증 ' + label + retry_label, generation_id))
                    diagnostics.event('코드 검증 시작', phase='코드 검증', candidate=candidate, unit=index + 1)
                    checks = validate_set(context.language, draft, image_id)
                    break
                except (Error, ai.InvalidDraft) as error:
                    if request.source_kind == 'sample' or (isinstance(error, Error) and not error.feedback):
                        raise
                    if isinstance(error, Error) and error.feedback:
                        previous, feedback = draft, error.feedback
                        db.execute('UPDATE generation_drafts SET feedback=? WHERE context_id=? AND unit_id=?',
                                   (dump(feedback), context_id, unit.id))
                    if candidate == max_attempts:
                        message = f'자동 수정 {MAX_GENERATION_REPAIRS}회 후에도 문제를 완성하지 못했습니다. 마지막 원인: {error}'
                        diagnostics.event('자동 수정 횟수 제한에 도달했습니다. 저장된 내용에서 이어갈 수 있습니다.', code='retry_exhausted', candidate=candidate)
                        if isinstance(error, ai.InvalidDraft):
                            raise ai.InvalidDraft(message, code=error.code, issues=error.issues) from None
                        raise Error(message, feedback=error.feedback) from None
                    diagnostics.event(f'문제를 자동 수정하고 다시 검증합니다. ({candidate}/{MAX_GENERATION_REPAIRS})',
                                      candidate=candidate + 1, code='retry')
            set_id = uid()
            validation = dump({'candidate': candidate, 'runtime': image_id, 'checks': checks, 'human_review': 'pending', 'scope': 'stdout behavior only'})
            # Only validated sets are persisted. Completed units survive a later failure/restart.
            with db.connect(write=True) as c:
                row = c.execute('SELECT state,candidate FROM generations WHERE id=?', (generation_id,)).fetchone()
                if row['state'] != 'validating' or row['candidate'] != candidate:
                    raise Error('검증 버전이 변경되었습니다.')
                c.execute('INSERT INTO sets (id,context_id,title,version,validation,withdrawn,created_at,unit_id) VALUES (?,?,?,?,?,0,?,?)',
                    (set_id, context_id, draft.title, candidate, validation, now(), unit.id))
                for exercise in draft.exercises:
                    c.execute('INSERT INTO exercises VALUES (?,?,?,?)', (uid(), set_id, exercise.kind, dump(exercise.model_dump())))
                c.execute('UPDATE generations SET set_id=? WHERE id=?', (set_id, generation_id))
                c.execute('DELETE FROM generation_drafts WHERE context_id=? AND unit_id=?', (context_id, unit.id))
            diagnostics.event('단원 세트 저장 완료', unit=index + 1)
        diagnostics.event('단원 문제 준비 완료')
        db.execute("UPDATE generations SET state='ready',stage='단원 문제 준비 완료' WHERE id=?", (generation_id,))
    except (Error, ai.AIError, source.SourceError, runner.Unavailable) as error:
        diagnostics.event(str(error), level='error', code=getattr(error, 'code', 'generation_failed'),
                          issues=getattr(error, 'issues', []))
        db.execute("UPDATE generations SET state='failed',error=? WHERE id=?", (str(error), generation_id))
    except Exception as error:
        # Exception values can contain source/provider data; record stack locations only.
        frames = [f'{f.name}:{f.lineno}' for f in traceback.extract_tb(error.__traceback__)[-8:]]
        diagnostics.event('서버 내부 오류가 발생했습니다.', level='error', code='internal_error',
                          exception=type(error).__name__, frames=frames)
        db.execute("UPDATE generations SET state='failed',error=? WHERE id=?", ('서버 내부 오류로 중단되었습니다. 작업 ID와 진단 로그를 확인해주세요.', generation_id))
    finally:
        request.source = ''
        diagnostics.job.reset(token)


def save_progress(owner, exercise_id, request):
    exercise_owned(owner, exercise_id, active=False)
    with db.connect(write=True) as c:
        if not c.execute('SELECT id FROM exercises WHERE id=?', (exercise_id,)).fetchone():
            raise Error('문제를 찾을 수 없습니다.', 404)
        row = c.execute('SELECT revision FROM progress WHERE owner=? AND exercise_id=?', (owner, exercise_id)).fetchone()
        if (row['revision'] if row else 0) != request.revision:
            raise Error('다른 탭에서 저장한 내용이 있습니다. 서버 내용을 확인한 뒤 다시 저장해주세요.', 409)
        revision = request.revision + 1
        c.execute('INSERT INTO progress VALUES (?,?,?,?,?,?) ON CONFLICT(owner,exercise_id) DO UPDATE SET code=excluded.code,answer=excluded.answer,revision=excluded.revision,updated_at=excluded.updated_at',
            (owner, exercise_id, request.code, request.answer, revision, now()))
    return {'revision': revision}


def execute(owner, exercise_id, request):
    item, problem_set = exercise_owned(owner, exercise_id)
    if request.version != problem_set['version']:
        raise Error('문제 버전이 다릅니다. 화면을 다시 열어주세요.', 409)
    exercise = ExerciseDraft.model_validate_json(item['data'])
    image_id = json.loads(problem_set['validation'])['runtime']
    payload = dump({'exercise_id': exercise_id, **request.model_dump()})
    attempt_id = None
    if request.action == 'submit':
        with db.connect(write=True) as c:
            if not c.execute('SELECT id FROM exercises WHERE id=?', (exercise_id,)).fetchone():
                raise Error('문제를 찾을 수 없습니다.', 404)
            existing = c.execute('SELECT * FROM attempts WHERE owner=? AND request_id=?', (owner, request.request_id)).fetchone()
            if existing:
                if existing['payload'] != payload:
                    raise Error('같은 제출 식별자를 다른 코드에 사용할 수 없습니다.', 409)
                if existing['status'] == 'running':
                    raise Error('같은 제출을 처리 중입니다. 잠시 후 다시 시도해주세요.', 409)
                return json.loads(existing['result'])
            attempt_id = uid()
            c.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)', (attempt_id, owner, exercise_id, request.request_id, payload, 'running', '{}', now()))
    try:
        rate('execute:' + owner, 30)
        if exercise.kind == 'READ':
            if not request.answer.strip():
                raise Error('실행 전에 예상 출력 답안을 작성해주세요.')
            if request.action == 'submit':
                passed = normalized(request.answer) == normalized(exercise.evaluation.read_answer)
                result = {'status': 'passed' if passed else 'failed', 'stdout': '', 'stderr': '', 'exit_code': None, 'tests': []}
            else:
                result = {**runner.run(json.loads(problem_set['context_data'])['language'], exercise.starter, [''], image_id=image_id)[0], 'tests': []}
        elif request.action == 'run':
            if exercise.test_mode == 'code' and not request.test_code.strip():
                raise Error('실행할 테스트 코드를 입력해주세요.')
            code = request.code + '\n' + request.test_code if exercise.test_mode == 'code' else request.code
            result = {**runner.run(json.loads(problem_set['context_data'])['language'], code,
                ['' if exercise.test_mode == 'code' else request.stdin], image_id=image_id)[0], 'tests': []}
        else:
            tests = exercise.public_tests + (exercise.evaluation.hidden_tests if request.action == 'submit' else [])
            result = evaluate(json.loads(problem_set['context_data'])['language'], request.code, tests, image_id)
            if request.action == 'submit':
                public_ids = {t.id for t in exercise.public_tests}
                result['tests'] = [t if t['id'] in public_ids else {'id': '비공개 ' + str(i + 1 - len(public_ids)), 'passed': t['passed']} for i, t in enumerate(result['tests'])]
                # Appended test code can appear in compiler diagnostics as well as runtime errors.
                if exercise.test_mode == 'code' or not result['status'].startswith('compile_'):
                    result['stderr'] = ''
        if attempt_id:
            result['attempt_id'] = attempt_id
            with db.connect(write=True) as c:
                if c.execute('SELECT withdrawn FROM sets WHERE id=?', (problem_set['id'],)).fetchone()['withdrawn']:
                    raise Error('검토 중 문제가 중단되었습니다. 이번 결과는 기록하지 않았습니다.', 409)
                c.execute('UPDATE attempts SET status=?,result=? WHERE id=?', ('passed' if result['status'] == 'passed' else 'failed', dump(result), attempt_id))
        return result
    except BaseException:
        if attempt_id:
            db.execute("DELETE FROM attempts WHERE id=? AND status='running'", (attempt_id,))
        raise


def hints(owner, exercise_id, step):
    item, _ = exercise_owned(owner, exercise_id)
    values = json.loads(item['data'])['hints']
    if step < 1 or step > len(values):
        raise Error('힌트를 찾을 수 없습니다.', 404)
    return {'hint': values[step - 1]}


def report(owner, exercise_id, request):
    exercise_owned(owner, exercise_id, active=False)
    if request.attempt_id and not db.one('SELECT id FROM attempts WHERE id=? AND owner=? AND exercise_id=? AND status!=?', (request.attempt_id, owner, exercise_id, 'running')):
        raise Error('본인의 해당 문제 제출만 첨부할 수 있습니다.', 400)
    rate('report:' + owner, 5, 3600)
    report_id = uid()
    with db.connect(write=True) as c:
        if not c.execute('SELECT id FROM exercises WHERE id=?', (exercise_id,)).fetchone():
            raise Error('문제를 찾을 수 없습니다.', 404)
        c.execute('INSERT INTO reports VALUES (?,?,?,?,?,?,?)', (report_id, owner, exercise_id, request.attempt_id, request.message, 'received', now()))
    return {'id': report_id}


def report_generation(owner, generation_id, request):
    job = generation(owner, generation_id)
    if job['state'] != 'failed' or request.attempt_id:
        raise Error('실패한 생성 작업만 제보할 수 있습니다.')
    existing = db.one('SELECT id FROM generation_reports WHERE generation_id=? AND owner=?', (generation_id, owner))
    if existing:
        return existing
    rate('report:' + owner, 5, 3600)
    with db.connect(write=True) as c:
        if not c.execute('SELECT id FROM generations WHERE id=? AND owner=?', (generation_id, owner)).fetchone():
            raise Error('생성 기록을 찾을 수 없습니다.', 404)
        c.execute('INSERT OR IGNORE INTO generation_reports VALUES (?,?,?,?,?,?)',
                  (uid(), owner, generation_id, request.message, 'received', now()))
        return {'id': c.execute('SELECT id FROM generation_reports WHERE generation_id=?', (generation_id,)).fetchone()['id']}


def learning_map(owner):
    roots = {}
    for row in db.all('SELECT * FROM contexts WHERE owner=? ORDER BY created_at DESC,id DESC', (owner,)):
        context = json.loads(row['data'])
        units = {u['id']: u for u in context.get('units', [])}
        framework = context.get('framework', '').strip()
        key = ('framework:' + framework.casefold()) if framework else context['language']
        for problem_set in summaries(owner, row['id']):
            exercises = db.all('''SELECT e.id,e.kind,json_extract(e.data,'$.title') AS title,
                EXISTS(SELECT 1 FROM attempts a WHERE a.owner=? AND a.exercise_id=e.id AND a.status='passed') AS passed,
                (EXISTS(SELECT 1 FROM attempts a WHERE a.owner=? AND a.exercise_id=e.id AND a.status!='running') OR
                 EXISTS(SELECT 1 FROM progress p WHERE p.owner=? AND p.exercise_id=e.id)) AS attempted
                FROM exercises e WHERE set_id=?
                ORDER BY CASE kind WHEN 'READ' THEN 0 WHEN 'FIX' THEN 1 WHEN 'MODIFY' THEN 2 ELSE 3 END''',
                (owner, owner, owner, problem_set['id']))
            if not any(e['attempted'] for e in exercises):
                continue
            unit = units.get(problem_set['unit_id'], context)
            branch = roots.setdefault(key, {'key': key, 'label': framework or context['language'], 'framework': bool(framework), 'concepts': {}})
            entry = {'context_id': row['id'], 'context_title': context['title'], 'unit_id': problem_set['unit_id'],
                     'title': unit['title'], 'set_id': problem_set['id'], 'withdrawn': bool(problem_set['withdrawn']),
                     'completed': sum(e['passed'] for e in exercises), 'total': len(exercises), 'exercises': exercises}
            for name in dict.fromkeys(unit['concepts']):
                concept = branch['concepts'].setdefault(name.strip().casefold(), {'name': name, 'units': []})
                concept['units'].append(entry)
    return [{**root, 'concepts': list(root['concepts'].values())} for root in roots.values()]


def history(owner):
    sets = []
    for context in contexts(owner):
        for item in context['sets']:
            if db.one('SELECT p.exercise_id FROM progress p JOIN exercises e ON e.id=p.exercise_id WHERE e.set_id=? AND p.owner=? UNION SELECT a.exercise_id FROM attempts a JOIN exercises e ON e.id=a.exercise_id WHERE e.set_id=? AND a.owner=?', (item['id'], owner, item['id'], owner)):
                sets.append({**item, 'context_title': context['title'], 'updated_at': context['created_at']})
    attempts = db.all("SELECT a.id,a.exercise_id,a.status,a.created_at,e.kind,json_extract(e.data,'$.title') AS title FROM attempts a JOIN exercises e ON e.id=a.exercise_id WHERE a.owner=? AND a.status!='running' ORDER BY a.created_at DESC LIMIT 100", (owner,))
    reports = db.all("SELECT r.id,r.message,r.status,r.created_at,json_extract(e.data,'$.title') AS exercise_title FROM reports r JOIN exercises e ON e.id=r.exercise_id WHERE r.owner=? ORDER BY r.created_at DESC", (owner,))
    reports += db.all("SELECT r.id,r.message,r.status,r.created_at,'문제 생성 · ' || g.stage AS exercise_title FROM generation_reports r JOIN generations g ON g.id=r.generation_id WHERE r.owner=?", (owner,))
    reports.sort(key=lambda r: r['created_at'], reverse=True)
    return {'sets': sets, 'attempts': attempts, 'reports': reports, 'learning_map': learning_map(owner)}


def admin_sources(user):
    if not user['admin']:
        raise Error('관리자 권한이 필요합니다.', 403)
    documents = db.all('''SELECT d.id,d.context_id,d.kind,d.name,d.url,d.content IS NOT NULL AS has_content,
        COALESCE(json_extract(c.data,'$.title'), NULLIF(d.name,''),d.url,'학습 자료') AS title,
        g.created_at,g.state FROM source_documents d JOIN generations g ON g.id=d.id
        LEFT JOIN contexts c ON c.id=d.context_id''')
    documents += db.all('''SELECT 'legacy:' || c.id AS id,c.id AS context_id,'legacy' AS kind,'' AS name,c.source_url AS url,
        0 AS has_content,json_extract(c.data,'$.title') AS title,c.created_at,'ready' AS state
        FROM contexts c WHERE NOT EXISTS(SELECT 1 FROM source_documents d WHERE d.context_id=c.id)''')
    return sorted(documents, key=lambda d: (d['created_at'], d['id']), reverse=True)


def admin_source(user, source_id):
    if not user['admin']:
        raise Error('관리자 권한이 필요합니다.', 403)
    item = next((d for d in admin_sources(user) if d['id'] == source_id), None)
    if not item:
        raise Error('원본 자료를 찾을 수 없습니다.', 404)
    document = db.one('SELECT content FROM source_documents WHERE id=?', (source_id,))
    return {**item, 'content': document['content'] if document else None}


def get_attempt(owner, attempt_id):
    row = db.one("SELECT * FROM attempts WHERE id=? AND owner=? AND status!='running'", (attempt_id, owner))
    if not row:
        raise Error('제출 기록을 찾을 수 없습니다.', 404)
    exercise_owned(owner, row['exercise_id'], active=False)
    payload = json.loads(row['payload'])
    return {'id': row['id'], 'exercise_id': row['exercise_id'], 'created_at': row['created_at'],
        'code': payload['code'], 'answer': payload['answer'], 'version': payload['version'], 'result': json.loads(row['result'])}


def admin_reports(user):
    if not user['admin']:
        raise Error('운영자 권한이 필요합니다.', 403)
    reports = db.all("SELECT r.*, e.set_id, json_extract(e.data,'$.title') AS exercise_title FROM reports r JOIN exercises e ON e.id=r.exercise_id ORDER BY r.created_at DESC LIMIT 100")
    for row in db.all("SELECT r.*, NULL AS set_id, '문제 생성 · ' || g.stage AS exercise_title FROM generation_reports r JOIN generations g ON g.id=r.generation_id ORDER BY r.created_at DESC LIMIT 100"):
        reports.append({**row, 'generation': generation(row['owner'], row['generation_id'])})
    return sorted(reports, key=lambda r: r['created_at'], reverse=True)[:100]


def review_report(user, report_id, request):
    if not user['admin']:
        raise Error('운영자 권한이 필요합니다.', 403)
    with db.connect(write=True) as c:
        row = c.execute('SELECT e.set_id FROM reports r JOIN exercises e ON e.id=r.exercise_id WHERE r.id=?', (report_id,)).fetchone()
        if not row:
            if c.execute('SELECT id FROM generation_reports WHERE id=?', (report_id,)).fetchone():
                if request.withdraw:
                    raise Error('생성 제보에는 중단할 문제 세트가 없습니다.')
                c.execute('UPDATE generation_reports SET status=? WHERE id=?', (request.status, report_id))
                return {'ok': True}
            raise Error('제보를 찾을 수 없습니다.', 404)
        c.execute('UPDATE reports SET status=? WHERE id=?', (request.status, report_id))
        if request.withdraw:
            c.execute('UPDATE sets SET withdrawn=1 WHERE id=?', (row['set_id'],))
    return {'ok': True}

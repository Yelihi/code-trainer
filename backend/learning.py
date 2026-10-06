"""Persisted, evidence-backed summaries of passed exercises."""
import hashlib
import json
from . import ai, db, service, usage
from .schema import LearningSummary


def evidence(owner):
    # One passed submission per problem: retries and later failures do not duplicate learning.
    rows = db.all('''SELECT e.id,e.data,e.kind,s.id AS set_id,s.unit_id,s.withdrawn,
        c.id AS context_id,c.data AS context,a.payload,
        COALESCE((SELECT assistance FROM attempt_learning WHERE attempt_id=a.id),'unknown') AS assistance
        FROM exercises e JOIN sets s ON s.id=e.set_id JOIN contexts c ON c.id=s.context_id
        JOIN attempts a ON a.id=(SELECT p.id FROM attempts p
          WHERE p.owner=? AND p.exercise_id=e.id AND p.status='passed'
          ORDER BY p.created_at,p.id LIMIT 1)
        WHERE c.owner=? ORDER BY e.id''', (owner, owner))
    items = []
    for row in rows:
        problem, context, submission = (json.loads(row[key]) for key in ('data', 'context', 'payload'))
        unit = next((u for u in context.get('units', []) if u['id'] == row['unit_id']), context)
        framework = context.get('framework', '').strip()
        items.append({
            'id': row['id'], 'root_key': 'framework:' + framework.casefold() if framework else context['language'],
            'root_label': framework or context['language'], 'framework': bool(framework),
            'language': context['language'], 'set_id': row['set_id'], 'context_id': row['context_id'],
            'unit_id': row['unit_id'], 'withdrawn': bool(row['withdrawn']),
            'title': problem['title'], 'kind': row['kind'], 'assistance': row['assistance'], 'unit_title': unit['title'],
            'concept_labels': unit['concepts'], 'description': problem['description'],
            'requirements': problem['requirements'], 'starter': problem['starter'],
            'submitted_code': submission.get('code', ''), 'submitted_answer': submission.get('answer', ''),
        })
    return items


def fingerprint(items):
    return hashlib.sha256(service.dump(items).encode()).hexdigest()


def public_evidence(items):
    keys = ('id', 'root_key', 'root_label', 'framework', 'set_id', 'context_id', 'unit_id', 'withdrawn', 'title', 'kind', 'assistance')
    return [{k: item[k] for k in keys} for item in items]


def archive_existing():
    # Preserve the successful generation date of summaries made before dated records existed.
    for row in db.all("SELECT * FROM learning_summaries s WHERE state='ready' AND NOT EXISTS (SELECT 1 FROM learning_records r WHERE r.owner=s.owner AND r.fingerprint=s.fingerprint)"):
        data = json.loads(row['data'])
        if 'exercises' not in data:
            live = {item['id']: item for item in public_evidence(evidence(row['owner']))}
            saved = {}
            for concept in data['concepts']:
                for outcome in concept['outcomes']:
                    for exercise_id in outcome['exercise_ids']:
                        saved[exercise_id] = live.get(exercise_id, {
                            'id': exercise_id, 'root_key': concept['root_key'],
                            'root_label': concept['root_key'].removeprefix('framework:'),
                            'framework': concept['root_key'].startswith('framework:'),
                            'set_id': None, 'context_id': None, 'unit_id': None,
                            'withdrawn': False, 'title': '이전 통과 문제', 'kind': '',
                        })
            data['exercises'] = list(saved.values())
        db.execute('INSERT OR IGNORE INTO learning_records VALUES (?,?,?,?,?)',
                   (service.uid(), row['owner'], row['fingerprint'], service.dump(data), row['updated_at']))


def status(owner, record_id=None):
    items = evidence(owner)
    cached = db.one('SELECT * FROM learning_summaries WHERE owner=?', (owner,))
    current = bool(cached and cached['fingerprint'] == fingerprint(items))
    state = 'empty' if not items else cached['state'] if current or (cached and cached['state'] == 'running') else 'stale'
    records = db.all('SELECT id,created_at FROM learning_records WHERE owner=? ORDER BY created_at DESC,id DESC', (owner,))
    selected = record_id or (records[0]['id'] if records else None)
    record = db.one('SELECT * FROM learning_records WHERE owner=? AND id=?', (owner, selected)) if selected else None
    if record_id and not record:
        raise service.Error('학습 기록을 찾을 수 없습니다.', 404)
    saved = json.loads(record['data']) if record else {'concepts': [], 'exercises': []}
    live = {item['id']: item for item in items}
    for exercise in saved['exercises']:
        exercise['deleted'] = exercise['id'] not in live
        if not exercise['deleted']:
            exercise['withdrawn'] = live[exercise['id']]['withdrawn']
    return {'state': state, 'concepts': saved['concepts'], 'exercises': saved['exercises'] if record else public_evidence(items),
            'records': records, 'record_id': selected, 'created_at': record['created_at'] if record else None,
            'current_passed_count': len(items),
            'error': cached['error'] if current else '', 'updated_at': cached['updated_at'] if current else None,
            'ai_available': ai.available()}


def begin(owner):
    items = evidence(owner)
    if not items:
        raise service.Error('Submit을 통과한 문제가 아직 없습니다.')
    key = fingerprint(items)
    # ponytail: one summary request for the local library; batch by root if it outgrows this limit.
    if len(service.dump(items).encode()) > 240000:
        raise service.Error('정리할 학습 기록이 한 번에 처리할 수 있는 범위를 넘었습니다.')
    with db.connect(write=True) as c:
        row = c.execute('SELECT * FROM learning_summaries WHERE owner=?', (owner,)).fetchone()
        if row and (row['state'] == 'running' or (row['state'] == 'ready' and row['fingerprint'] == key)):
            return None
        if not ai.available():
            raise service.Error('AI_API_KEY와 AI_MODEL 환경변수를 설정해주세요.', 503)
        c.execute('''INSERT INTO learning_summaries(owner,fingerprint,state,updated_at) VALUES (?,?,'running',?)
            ON CONFLICT(owner) DO UPDATE SET fingerprint=excluded.fingerprint,state='running',error='',
            data='{"concepts":[]}',updated_at=excluded.updated_at''', (owner, key, service.now()))
    return items


def summarize(owner, items):
    usage_token = usage.scope.set((owner, None))
    try:
        draft = ai.generate(LearningSummary, '''Build a concept map from ONLY the supplied PASSED exercises.
Merge semantic synonyms across courses and units into one canonical topic within each root_key.
For example, 클래스 정의법, 클래스 키워드 and 클래스의 특징 belong under 클래스(class),
not three unrelated folders. Keep genuinely different topics distinct. Use the supplied root_key
exactly; languages/frameworks are separate roots. Do not simply repeat the unit's concept labels:
they are hints, not proof that every concept in that unit was practiced.
For each topic write concrete Korean outcome sentences grounded in the actual problem requirements,
starter, and passed submission. Explain what the learner practiced and why/how it works (e.g.
생성자에서 전달받은 값을 인스턴스 속성에 저장해 객체마다 서로 다른 상태를 갖도록 구성하는 방법을 연습했습니다.).
READ supports tracing/explaining behavior, not claiming implementation. FIX supports repairing the
specific bug; MODIFY/BUILD support implementing the requested behavior. Never claim expert mastery,
independent authorship, or untested abilities; assistance is app-observed help (unknown for legacy records), not proof of independence; a passed submission may follow a provided solution.
Consolidate repeated outcomes from multiple exercises; retain distinct subskills as separate sentences.
Every outcome must cite exercise_ids from that SAME root which directly support the sentence.
Cover all supplied exercises where possible; a problem can support more than one outcome.
Never cite unsolved problems, invent IDs, or include code/answers in the summary.
Use plain text, not markdown, for names and sentences.''', {'passed_exercises': items})
        allowed = {item['id']: item['root_key'] for item in items}
        grouped = {}
        for concept in draft.concepts:
            key = (concept.root_key, concept.name.strip().casefold())
            target = grouped.setdefault(key, {'root_key': concept.root_key, 'name': concept.name.strip(), 'outcomes': []})
            for outcome in concept.outcomes:
                ids = list(dict.fromkeys(outcome.exercise_ids))
                if any(allowed.get(exercise_id) != concept.root_key for exercise_id in ids):
                    raise ai.AIError('정리 내용의 근거 문제를 확인하지 못했습니다. 다시 정리해주세요.')
                value = {'summary': outcome.summary.strip(), 'exercise_ids': ids}
                if value not in target['outcomes']:
                    target['outcomes'].append(value)
        data = service.dump({'concepts': list(grouped.values()), 'exercises': public_evidence(items)})
        created_at = service.now()
        with db.connect(write=True) as c:
            updated = c.execute('''UPDATE learning_summaries SET state='ready',data=?,error='',updated_at=?
                WHERE owner=? AND fingerprint=?''', (data, created_at, owner, fingerprint(items)))
            if updated.rowcount:
                c.execute('INSERT OR IGNORE INTO learning_records VALUES (?,?,?,?,?)',
                          (service.uid(), owner, fingerprint(items), data, created_at))
    except Exception as error:
        message = str(error) if isinstance(error, ai.AIError) else '학습 내용을 정리하지 못했습니다. 잠시 후 다시 시도해주세요.'
        db.execute("UPDATE learning_summaries SET state='failed',error=?,updated_at=? WHERE owner=? AND fingerprint=?",
                   (message, service.now(), owner, fingerprint(items)))

    finally:
        usage.scope.reset(usage_token)

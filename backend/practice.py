"""Help provenance and isolated, persisted review sessions; no AI calls."""
from datetime import datetime, timedelta, timezone
import json
from . import db, service

LEVELS = {'none': 0, 'hint': 1, 'solution': 2}


def session(owner, review_id, exercise_id=None):
    row = db.one('SELECT * FROM review_sessions WHERE id=? AND owner=?', (review_id, owner))
    if not row or (exercise_id and row['exercise_id'] != exercise_id):
        raise service.Error('복습을 찾을 수 없습니다.', 404)
    service.exercise_owned(owner, row['exercise_id'])
    return row


def help_used(owner, exercise_id, level, review_id=None):
    # Called only when help is actually returned. Repeated fetches are idempotent.
    service.exercise_owned(owner, exercise_id, active=False)
    if review_id:
        session(owner, review_id, exercise_id)
    with db.connect(write=True) as c:
        c.execute("INSERT OR IGNORE INTO assistance VALUES (?,?,'none')", (owner, exercise_id))
        old = c.execute('SELECT level FROM assistance WHERE owner=? AND exercise_id=?', (owner, exercise_id)).fetchone()['level']
        if LEVELS[level] > LEVELS[old]:
            c.execute('UPDATE assistance SET level=? WHERE owner=? AND exercise_id=?', (level, owner, exercise_id))
        # Opening the normal exercise in another tab during a review is still help.
        row = c.execute("SELECT id,assistance FROM review_sessions WHERE owner=? AND exercise_id=? AND state='active'", (owner, exercise_id)).fetchone()
        if row and LEVELS[level] > LEVELS[row['assistance']]:
            c.execute('UPDATE review_sessions SET assistance=? WHERE id=?', (level, row['id']))


def record(c, owner, exercise_id, attempt_id, passed, review_id=None):
    """Part of the submission transaction. Replayed requests never reach here."""
    if review_id:
        row = c.execute('SELECT * FROM review_sessions WHERE id=? AND owner=? AND exercise_id=?', (review_id, owner, exercise_id)).fetchone()
        if not row or row['state'] != 'active':
            raise service.Error('이미 마친 복습입니다. 복습 목록에서 다시 시작해주세요.', 409)
        level = row['assistance']
    else:
        row = c.execute('SELECT level FROM assistance WHERE owner=? AND exercise_id=?', (owner, exercise_id)).fetchone()
        level = row['level'] if row else 'none'
    c.execute('INSERT INTO attempt_learning VALUES (?,?,?)', (attempt_id, level, review_id))
    clock = datetime.now(timezone.utc)
    if review_id:
        current = c.execute('SELECT streak FROM review_schedule WHERE owner=? AND exercise_id=?', (owner, exercise_id)).fetchone()
        failed_before = c.execute("SELECT 1 FROM attempt_learning l JOIN attempts a ON a.id=l.attempt_id WHERE l.review_id=? AND a.status='failed' LIMIT 1", (review_id,)).fetchone()
        streak = min((current['streak'] if current else 0) + 1, 3) if passed and level == 'none' and not failed_before else 0
        days = (1, 3, 7, 14)[streak]
        c.execute('INSERT INTO review_schedule VALUES (?,?,?,?) ON CONFLICT(owner,exercise_id) DO UPDATE SET due_at=excluded.due_at,streak=excluded.streak',
                  (owner, exercise_id, (clock + timedelta(days=days)).isoformat(), streak))
        if passed:
            c.execute("UPDATE review_sessions SET state='completed',completed_at=? WHERE id=?", (clock.isoformat(), review_id))
    elif passed:
        c.execute('INSERT OR IGNORE INTO review_schedule VALUES (?,?,?,0)', (owner, exercise_id, (clock + timedelta(days=1)).isoformat()))
    return level


def queue(owner):
    # Legacy passes become due one day after that pass, with unknown help provenance.
    with db.connect(write=True) as c:
        c.execute('''INSERT OR IGNORE INTO review_schedule(owner,exercise_id,due_at)
            SELECT a.owner,a.exercise_id,strftime('%Y-%m-%dT%H:%M:%f+00:00',MIN(a.created_at),'+1 day')
            FROM attempts a JOIN exercises e ON e.id=a.exercise_id JOIN sets s ON s.id=e.set_id
            WHERE a.owner=? AND a.status='passed' AND s.withdrawn=0 GROUP BY a.owner,a.exercise_id''', (owner,))
    rows = db.all('''SELECT r.*,e.kind,json_extract(e.data,'$.title') AS title,s.id AS set_id,
        json_extract(ctx.data,'$.title') AS context_title,
        (SELECT id FROM review_sessions v WHERE v.owner=r.owner AND v.exercise_id=r.exercise_id AND v.state='active') AS active_review_id,
        COALESCE((SELECT l.assistance FROM attempts a LEFT JOIN attempt_learning l ON l.attempt_id=a.id
          WHERE a.owner=r.owner AND a.exercise_id=r.exercise_id AND a.status='passed' ORDER BY a.created_at DESC,a.id DESC LIMIT 1),'unknown') AS assistance
        FROM review_schedule r JOIN exercises e ON e.id=r.exercise_id JOIN sets s ON s.id=e.set_id
        JOIN contexts ctx ON ctx.id=s.context_id WHERE r.owner=? AND ctx.owner=? AND s.withdrawn=0
        ORDER BY r.due_at,e.id''', (owner, owner))
    clock = service.now()
    for row in rows:
        row['due'] = row['due_at'] <= clock
    rows.sort(key=lambda r: (not bool(r['active_review_id']), not r['due'], -LEVELS.get(r['assistance'], 0), r['due_at']))
    return {'items': rows, 'due_count': sum(r['due'] or bool(r['active_review_id']) for r in rows)}


def begin(owner, exercise_id):
    item, _ = service.exercise_owned(owner, exercise_id)
    if not db.one("SELECT id FROM attempts WHERE owner=? AND exercise_id=? AND status='passed'", (owner, exercise_id)):
        raise service.Error('통과한 문제부터 복습할 수 있습니다.', 409)
    queue(owner)
    with db.connect(write=True) as c:
        old = c.execute("SELECT id FROM review_sessions WHERE owner=? AND exercise_id=? AND state='active'", (owner, exercise_id)).fetchone()
        if old:
            return {'id': old['id']}
        due = c.execute('SELECT due_at FROM review_schedule WHERE owner=? AND exercise_id=?', (owner, exercise_id)).fetchone()
        if due['due_at'] > service.now():
            raise service.Error('아직 복습 예정일이 아닙니다.', 409)
        review_id = service.uid()
        c.execute('INSERT INTO review_sessions(id,owner,exercise_id,code,created_at) VALUES (?,?,?,?,?)',
                  (review_id, owner, exercise_id, json.loads(item['data'])['starter'], service.now()))
    return {'id': review_id}


def view(owner, review_id):
    row = session(owner, review_id)
    item, _ = service.exercise_owned(owner, row['exercise_id'])
    result = service.get_set(owner, item['set_id'])
    exercise = next(e for e in result['exercises'] if e['id'] == row['exercise_id'])
    exercise.update(progress={k: row[k] for k in ('code', 'answer', 'revision')}, passed=row['state'] == 'completed', assistance=row['assistance'])
    result.update(exercises=[exercise], review_id=review_id)
    return result


def save(owner, review_id, request):
    session(owner, review_id)
    with db.connect(write=True) as c:
        updated = c.execute('UPDATE review_sessions SET code=?,answer=?,revision=revision+1 WHERE id=? AND owner=? AND revision=?',
                            (request.code, request.answer, review_id, owner, request.revision))
        if not updated.rowcount:
            raise service.Error('다른 탭에서 복습이 변경되었습니다.', 409)
    return {'revision': request.revision + 1}

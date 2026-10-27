"""Default-off weekly checks with a durable automatic-attempt budget."""
import asyncio
import logging
from datetime import datetime,timedelta
from . import ai,db,service,insights,insight_context


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS insight_schedules (
        owner TEXT PRIMARY KEY REFERENCES users(id), enabled INTEGER NOT NULL DEFAULT 0,
        revision INTEGER NOT NULL DEFAULT 0, next_at TEXT, fingerprint TEXT NOT NULL DEFAULT '',
        reason TEXT NOT NULL DEFAULT 'off', checked_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS insight_auto_attempts (
        job_id TEXT PRIMARY KEY REFERENCES insight_jobs(id), owner TEXT NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL)''')
    c.execute('CREATE INDEX IF NOT EXISTS insight_auto_owner_time ON insight_auto_attempts(owner,created_at)')


def cutoff():return (datetime.fromisoformat(service.now())-timedelta(days=30)).isoformat()


def status(owner):
    row=db.one('SELECT * FROM insight_schedules WHERE owner=?',(owner,)) or dict(enabled=0,revision=0,next_at=None,reason='off',checked_at=None)
    return dict(enabled=bool(row['enabled']),revision=row['revision'],next_at=row['next_at'],reason=row['reason'],checked_at=row['checked_at'],
                job=insights.job_view(db.one('SELECT j.* FROM insight_auto_attempts a JOIN insight_jobs j ON j.id=a.job_id WHERE a.owner=? ORDER BY a.created_at DESC,a.rowid DESC LIMIT 1',(owner,))),
                used=db.one('SELECT COUNT(*) n FROM insight_auto_attempts WHERE owner=? AND created_at>?',(owner,cutoff()))['n'],limit=4,days=30,interval_days=7,output_tokens=4000)


def configure(owner,request):
    with db.connect(write=True) as c:
        c.execute('INSERT OR IGNORE INTO insight_schedules(owner) VALUES (?)',(owner,))
        row=c.execute('SELECT * FROM insight_schedules WHERE owner=?',(owner,)).fetchone()
        if bool(row['enabled'])==request.enabled:return status(owner)
        if row['revision']!=request.revision:raise service.Error('다른 화면에서 예약 설정이 바뀌었습니다. 최신 상태를 확인해주세요.',409)
        next_at=(datetime.fromisoformat(service.now())+timedelta(days=7)).isoformat() if request.enabled else None
        c.execute('UPDATE insight_schedules SET enabled=?,revision=revision+1,next_at=?,reason=? WHERE owner=?',(int(request.enabled),next_at,'waiting' if request.enabled else 'off',owner))
        if not request.enabled:
            c.execute("UPDATE insight_jobs SET state='interrupted',snapshot=NULL,error='예약 생성을 꺼서 대기 작업을 중단했습니다.' WHERE owner=? AND state='queued' AND id IN (SELECT job_id FROM insight_auto_attempts WHERE owner=?)",(owner,owner))
    return status(owner)


def claim(owner):
    with db.connect(write=True) as c:
        clock=service.now();row=c.execute('SELECT * FROM insight_schedules WHERE owner=?',(owner,)).fetchone()
        if not row or not row['enabled'] or row['next_at']>clock:return None
        context=insight_context.build(owner);fingerprint=insight_context.fingerprint(context)
        recent=c.execute('SELECT fingerprint FROM insight_jobs WHERE owner=? ORDER BY created_at DESC,rowid DESC LIMIT 1',(owner,)).fetchone()
        reason='queued';job=None
        if c.execute("SELECT 1 FROM insight_jobs WHERE owner=? AND state IN ('queued','running')",(owner,)).fetchone():reason='pending'
        elif not context['assertions']:reason='insufficient'
        elif fingerprint==row['fingerprint'] or (recent and recent['fingerprint']==fingerprint):reason='unchanged'
        elif not ai.available(owner):reason='ai-unavailable'
        elif c.execute('SELECT COUNT(*) FROM insight_auto_attempts WHERE owner=? AND created_at>?',(owner,cutoff())).fetchone()[0]>=4:reason='budget'
        else:
            job=insights.enqueue(c,owner,context)
            c.execute('INSERT INTO insight_auto_attempts VALUES (?,?,?)',(job['id'],owner,clock))
            c.execute('UPDATE insight_schedules SET fingerprint=? WHERE owner=?',(fingerprint,owner))
        next_at=(datetime.fromisoformat(clock)+timedelta(days=7)).isoformat()
        c.execute('UPDATE insight_schedules SET next_at=?,reason=?,checked_at=? WHERE owner=?',(next_at,reason,clock,owner))
        return job['id'] if job else None


def cleanup():
    with db.connect(write=True) as c:
        c.execute('DELETE FROM insight_bundles WHERE expires_at<=?',(service.now(),))
        c.execute('DELETE FROM insight_skips WHERE expires_at<=?',(service.now(),))


def tick(owner):
    job=claim(owner)
    if job:insights.generate(job)


async def poll():
    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(cleanup)
            owners=db.all('SELECT owner FROM insight_schedules WHERE enabled=1 AND next_at<=?',(service.now(),))
        except Exception:
            logging.getLogger(__name__).exception('Insight schedule lookup failed');continue
        for row in owners:
            try:await asyncio.to_thread(tick,row['owner'])
            except Exception:logging.getLogger(__name__).exception('Insight schedule check failed')

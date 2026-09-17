"""Generation metadata only: never pass source, provider bodies or grading outputs."""
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from . import db

job = ContextVar('generation_id', default=None)
logger = logging.getLogger('trainer.generation')


def initialize():
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
    path = db.path().parent / 'generation.log'
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    logger.addHandler(RotatingFileHandler(path, maxBytes=2_000_000, backupCount=2, encoding='utf-8'))
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.INFO)
    logger.propagate = False


def event(message, level='info', **metadata):
    record = {'time': datetime.now(timezone.utc).isoformat(), 'level': level, 'message': message, **metadata}
    generation_id = job.get()
    if generation_id:
        with db.connect(write=True) as c:
            row = c.execute('SELECT events FROM generations WHERE id=?', (generation_id,)).fetchone()
            events = (json.loads(row['events']) + [record])[-100:]
            c.execute('UPDATE generations SET events=? WHERE id=?', (json.dumps(events, ensure_ascii=False), generation_id))
    logger.info(json.dumps({'generation_id': generation_id, **record}, ensure_ascii=False))


def view(row):
    if row:
        row['events'] = json.loads(row['events'])
    return row

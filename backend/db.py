import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def path():
    return Path(os.environ.get('TRAINER_DB', 'data/trainer.sqlite3')).resolve()


@contextmanager
def connect(write=False):
    connection = sqlite3.connect(path(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute('PRAGMA foreign_keys=ON')
    try:
        if write:
            connection.execute('BEGIN IMMEDIATE')
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize():
    path().parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with connect() as c:
        c.execute('PRAGMA journal_mode=WAL')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
          id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
          password TEXT NOT NULL, admin INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions (
          token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS contexts (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
          data TEXT NOT NULL, source_url TEXT, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS generations (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
          state TEXT NOT NULL, stage TEXT NOT NULL, context_id TEXT REFERENCES contexts(id),
          set_id TEXT, error TEXT, candidate INTEGER NOT NULL DEFAULT 1,
          created_at TEXT NOT NULL, UNIQUE(owner, request_id));
        CREATE TABLE IF NOT EXISTS sets (
          id TEXT PRIMARY KEY, context_id TEXT NOT NULL REFERENCES contexts(id),
          title TEXT NOT NULL, version INTEGER NOT NULL, validation TEXT NOT NULL,
          withdrawn INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS generation_drafts (
          context_id TEXT NOT NULL REFERENCES contexts(id), unit_id TEXT NOT NULL,
          data TEXT NOT NULL, feedback TEXT NOT NULL,
          PRIMARY KEY(context_id, unit_id));
        CREATE TABLE IF NOT EXISTS exercises (
          id TEXT PRIMARY KEY, set_id TEXT NOT NULL REFERENCES sets(id),
          kind TEXT NOT NULL, data TEXT NOT NULL, UNIQUE(set_id, kind));
        CREATE TABLE IF NOT EXISTS progress (
          owner TEXT NOT NULL REFERENCES users(id), exercise_id TEXT NOT NULL REFERENCES exercises(id),
          code TEXT NOT NULL, answer TEXT NOT NULL, revision INTEGER NOT NULL,
          updated_at TEXT NOT NULL, PRIMARY KEY(owner, exercise_id));
        CREATE TABLE IF NOT EXISTS attempts (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
          exercise_id TEXT NOT NULL REFERENCES exercises(id), request_id TEXT NOT NULL,
          payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT NOT NULL, created_at TEXT NOT NULL,
          UNIQUE(owner, request_id));
        CREATE TABLE IF NOT EXISTS reports (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
          exercise_id TEXT NOT NULL REFERENCES exercises(id), attempt_id TEXT REFERENCES attempts(id),
          message TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS generation_reports (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
          generation_id TEXT UNIQUE NOT NULL REFERENCES generations(id) ON DELETE CASCADE,
          message TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS source_documents (
          id TEXT PRIMARY KEY REFERENCES generations(id) ON DELETE CASCADE,
          context_id TEXT REFERENCES contexts(id) ON DELETE CASCADE,
          kind TEXT NOT NULL, name TEXT NOT NULL, url TEXT, content TEXT);
        CREATE INDEX IF NOT EXISTS attempts_progress ON attempts(owner, exercise_id, status);
        CREATE TABLE IF NOT EXISTS learning_summaries (
          owner TEXT PRIMARY KEY REFERENCES users(id), fingerprint TEXT NOT NULL,
          state TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{"concepts":[]}',
          error TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS learning_records (
          id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), fingerprint TEXT NOT NULL,
          data TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(owner, fingerprint));
        ''')
        if 'unit_id' not in {row['name'] for row in c.execute('PRAGMA table_info(sets)')}:
            c.execute('ALTER TABLE sets ADD COLUMN unit_id TEXT')
        if 'events' not in {row['name'] for row in c.execute('PRAGMA table_info(generations)')}:
            c.execute("ALTER TABLE generations ADD COLUMN events TEXT NOT NULL DEFAULT '[]'")
        if 'unit_id' not in {row['name'] for row in c.execute('PRAGMA table_info(generations)')}:
            c.execute('ALTER TABLE generations ADD COLUMN unit_id TEXT')
            # Attach earlier whole-course failures to the unit where they stopped.
            c.execute('''UPDATE generations SET unit_id=(
                SELECT json_extract(c.data, '$.units[' || (json_extract(e.value, '$.unit') - 1) || '].id')
                FROM contexts c, json_each(generations.events) e
                WHERE c.id=generations.context_id AND json_type(e.value, '$.unit')='integer'
                ORDER BY CAST(e.key AS INTEGER) DESC LIMIT 1) WHERE state='failed' ''')
        c.execute('CREATE UNIQUE INDEX IF NOT EXISTS sets_unit ON sets(context_id, unit_id) WHERE unit_id IS NOT NULL')
    path().chmod(0o600)


def one(sql, params=()):
    with connect() as c:
        row = c.execute(sql, params).fetchone()
        return dict(row) if row else None


def all(sql, params=()):
    with connect() as c:
        return [dict(row) for row in c.execute(sql, params).fetchall()]


def execute(sql, params=()):
    with connect(write=True) as c:
        c.execute(sql, params)

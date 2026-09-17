"""Check local prerequisites; this does not execute submitted code."""

import shutil
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def check_sqlite():
    with tempfile.TemporaryDirectory(prefix="code-trainer-check-") as directory:
        path = Path(directory) / "probe.sqlite3"
        connection = sqlite3.connect(path)
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript("""
                CREATE TABLE exercise (id INTEGER PRIMARY KEY);
                CREATE TABLE attempt (
                    exercise_id INTEGER REFERENCES exercise(id),
                    code TEXT NOT NULL
                );
                INSERT INTO exercise VALUES (1);
            """)
            connection.execute("INSERT INTO attempt VALUES (?, ?)", (1, "예제 코드"))
            connection.commit()
            try:
                connection.execute("INSERT INTO attempt VALUES (?, ?)", (99, "invalid"))
            except sqlite3.IntegrityError:
                connection.rollback()
            else:
                raise RuntimeError("Foreign key enforcement failed")
        finally:
            connection.close()

        connection = sqlite3.connect(path)
        try:
            if connection.execute("SELECT * FROM attempt").fetchall() != [(1, "예제 코드")]:
                raise RuntimeError("Stored data did not survive reopening")
        finally:
            connection.close()
    print("PASS SQLite {}: file persistence and foreign keys".format(sqlite3.sqlite_version))


def check_docker():
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("Docker CLI not found")
    result = subprocess.run(
        [docker, "version", "--format", "{{.Server.Version}}"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode or not result.stdout.strip():
        raise RuntimeError("Docker engine unavailable; check Docker startup and socket access")
    print("PASS Docker engine: " + result.stdout.strip())


def check_env_file():
    with tempfile.TemporaryDirectory(prefix="code-trainer-env-") as directory:
        path = Path(directory) / '.env'
        path.write_text('TRAINER_ENV_PROBE="local value"\nTRAINER_ENV_PRIORITY=file\n')
        environment = {**os.environ, 'UV_ENV_FILE': str(path), 'TRAINER_ENV_PRIORITY': 'shell'}
        environment.pop('TRAINER_ENV_PROBE', None)
        environment.pop('UV_NO_ENV_FILE', None)
        subprocess.run(['uv', 'run', '--no-project', sys.executable, '-c',
            'import os; assert os.environ["TRAINER_ENV_PROBE"] == "local value"; '
            'assert os.environ["TRAINER_ENV_PRIORITY"] == "shell"'],
            env=environment, check=True, timeout=10)
    print('PASS .env loading: quoted values and shell precedence')


if __name__ == "__main__":
    failed = False
    for check in (check_sqlite, check_docker, check_env_file):
        try:
            check()
        except (OSError, RuntimeError, sqlite3.Error, subprocess.SubprocessError) as error:
            print("FAIL {}: {}".format(check.__name__, error), file=sys.stderr)
            failed = True
    print("Sandbox compilation, resource limits and cleanup: NOT TESTED")
    sys.exit(1 if failed else 0)

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from .volume import install, validate_source


class VolumeTest(unittest.TestCase):
    def test_consistent_backup_and_fail_closed_import(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original.sqlite3'
            with sqlite3.connect(original) as connection:
                connection.execute('PRAGMA journal_mode=WAL')
                connection.execute('CREATE TABLE users(id TEXT)')
                connection.execute("INSERT INTO users VALUES ('preserved-owner')")
                connection.commit()
                destination = root / 'snapshot'
                destination.mkdir()
                backup = destination / 'trainer.sqlite3'
                command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'scripts/backup.py'), str(backup)]
                env = {**os.environ, 'TRAINER_DB': str(original)}
                subprocess.run(command, env=env, check=True, capture_output=True)
                self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
                self.assertEqual(validate_source(destination, 'data'), destination.resolve())
                with patch('deploy.volume.subprocess.run', side_effect=AssertionError('Docker must not run for invalid input')):
                    for context, replacement in [('colima-code-trainer-runner', None), ('colima-code-trainer-app', 'resume-agent-data')]:
                        with self.assertRaises(ValueError):
                            install(context, 'sha256:' + 'a' * 64, 'data', destination, replacement)
                with sqlite3.connect(backup) as copied:
                    self.assertEqual(copied.execute('SELECT id FROM users').fetchone()[0], 'preserved-owner')
                self.assertNotEqual(subprocess.run(command, env=env, capture_output=True).returncode, 0)
                (destination / '.env').write_text('never import secrets with DB')
                with self.assertRaises(ValueError):
                    validate_source(destination, 'data')
                (destination / '.env').unlink()
                backup.unlink()
                backup.symlink_to(original)
                with self.assertRaises(ValueError):
                    validate_source(destination, 'data')


if __name__ == '__main__':
    unittest.main()

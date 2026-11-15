import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
import zipfile
from . import db, record_export, test_app


class ExportTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def test_owned_archive_and_backup_restoration(self):
        self.client.post('/api/questions', json={'request_id': 'export-question', 'text': '보존할 질문'})
        db.execute("INSERT INTO users VALUES ('other','other','secret',0)")
        db.execute("INSERT INTO question_memos(id,owner,request_id,text,created_at,updated_at) VALUES ('other','other','request','다른 소유자','now','now')")
        with zipfile.ZipFile(io.BytesIO(record_export.export(self.owner))) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            self.assertEqual(manifest['tables']['question_memos'], 1)
            self.assertEqual(json.loads(archive.read('records/question_memos.json'))[0]['text'], '보존할 질문')
            self.assertFalse(any(name in ('records/sessions.json', 'records/users.json') for name in archive.namelist()))
            for name in archive.namelist():
                self.assertNotIn('다른 소유자', archive.read(name).decode())
        backup = Path(self.directory.name) / 'backup.sqlite3'
        subprocess.run([sys.executable, 'scripts/backup.py', str(backup)], check=True, capture_output=True)
        restored = Path(self.directory.name) / 'restored.sqlite3'
        with sqlite3.connect(backup) as source, sqlite3.connect(restored) as target:
            source.backup(target)
            self.assertEqual(target.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(target.execute('SELECT text FROM question_memos WHERE owner=?', (self.owner,)).fetchone()[0], '보존할 질문')
            self.assertEqual(target.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(os.stat(backup).st_mode & 0o777, 0o600)

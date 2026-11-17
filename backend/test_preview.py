import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from . import db, preview, test_app
from .api import app


class PreviewTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def test_fresh_clients_reuse_existing_owner_without_cookies_or_password(self):
        with patch.dict(os.environ, {'TRAINER_PREVIEW': '1'}), patch.object(preview, 'PREVIEW_DB', db.path()):
            for _ in range(2):
                with TestClient(app, client=('127.0.0.1', 50000)) as client:
                    session = client.get('/api/session').json()
                    self.assertEqual((session['user']['id'], session['auth_mode'], session['setup_required']), (self.owner, 'preview', False))
                    response = client.post('/api/questions', json={'text': '쿠키 없는 미리보기 질문', 'request_id': 'preview-question'}, headers={'origin': 'http://127.0.0.1:4173'})
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(client.post('/api/auth', json=self.credentials).status_code, 403)
                    self.assertEqual(client.post('/api/logout', json={}).status_code, 403)
                    self.assertFalse(client.cookies)
            self.assertEqual(db.one('SELECT COUNT(*) AS n FROM question_memos WHERE owner=?', (self.owner,))['n'], 1)
        with TestClient(app, client=('127.0.0.1', 50000)) as client:
            self.assertIsNone(client.get('/api/session').json()['user'])
            self.assertEqual(client.get('/api/questions').status_code, 401)

    def test_preview_rejects_remote_forwarded_and_cross_site_requests(self):
        with patch.dict(os.environ, {'TRAINER_PREVIEW': '1'}), patch.object(preview, 'PREVIEW_DB', db.path()):
            with TestClient(app, client=('192.0.2.1', 50000)) as client:
                self.assertEqual(client.get('/api/session').status_code, 403)
            with TestClient(app, client=('127.0.0.1', 50000)) as client:
                for header in ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'cf-connecting-ip', 'cf-access-jwt-assertion', 'x-trainer-user-jwt'):
                    self.assertEqual(client.get('/api/session', headers={header: 'untrusted'}).status_code, 403, header)
                self.assertEqual(client.post('/api/questions', json={'text': '거부', 'request_id': 'preview-cross-site'}, headers={'origin': 'https://attacker.example'}).status_code, 403)
                self.assertEqual(db.one('SELECT COUNT(*) AS n FROM question_memos')['n'], 0)

    def test_preview_cannot_use_server_mode_or_a_non_development_database(self):
        with patch.dict(os.environ, {'TRAINER_PREVIEW': '1'}), patch.object(preview, 'PREVIEW_DB', db.path()):
            preview.validate_config()
            with patch.dict(os.environ, {'TRAINER_MODE': 'server'}), self.assertRaises(ValueError):
                preview.validate_config()
            with patch.dict(os.environ, {'TRAINER_DB': str(db.path().parent / 'other.sqlite3')}), self.assertRaises(ValueError):
                preview.validate_config()

    def test_new_preview_creates_one_owner_and_rejects_ambiguous_ownership(self):
        with patch.dict(os.environ, {'TRAINER_PREVIEW': '1'}), patch.object(preview, 'PREVIEW_DB', db.path()):
            db.execute('DELETE FROM sessions')
            db.execute('DELETE FROM users')
            preview.initialize()
            first = db.one('SELECT id FROM users')['id']
            preview.initialize()
            self.assertEqual(db.all('SELECT id FROM users'), [{'id': first}])
            db.execute('INSERT INTO users VALUES (?,?,?,?)', ('other-owner', 'other', 'unused', 0))
            with self.assertRaises(ValueError):
                preview.initialize()

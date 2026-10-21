import json
import os
import unittest
from unittest.mock import patch
import httpx
from cryptography.fernet import Fernet
from . import db, github_sharing as github, knowledge, service, test_app
from . import test_reference_notes


class GitHubSharingTest(unittest.TestCase):
    note = test_reference_notes.ReferenceNotesTest.note
    graph_data = test_reference_notes.ReferenceNotesTest.graph_data
    register = test_reference_notes.ReferenceNotesTest.register
    tearDown = test_app.AppTest.tearDown

    def setUp(self):
        test_app.AppTest.setUp(self)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'TRAINER_GITHUB_ENCRYPTION_KEY': Fernet.generate_key().decode()}).start()
        self.token = 'github_pat_' + 'test_only_never_real_' * 3
        self.requests = []
        self.repo = {'id': 123, 'full_name': 'owner/notes', 'private': True, 'has_issues': True, 'archived': False, 'disabled': False}
        self.remote_status = 201
        self.timeout = False
        self.user_status = 200
        self.issue_body = ''
        self.issue_user = 456
        self.revoke_during_check = False

        def handle(request):
            self.requests.append(request)
            self.assertEqual(request.url.host, 'api.github.com')
            self.assertEqual(request.headers['authorization'], 'Bearer ' + self.token)
            if request.url.path == '/user':
                return httpx.Response(self.user_status, json={'id': 456, 'login': 'reader'})
            if request.method == 'POST':
                self.issue_body = json.loads(request.content)['body']
                if self.timeout:
                    raise httpx.ReadTimeout('secret-token-must-not-leak', request=request)
                return httpx.Response(self.remote_status, json={'number': 42})
            if request.url.path.endswith('/issues/42'):
                return httpx.Response(200, json={'number': 42, 'body': self.issue_body, 'user': {'id': self.issue_user}})
            if self.revoke_during_check:
                db.execute('DELETE FROM github_connections WHERE owner=?', (self.owner,))
            return httpx.Response(200, json=self.repo)

        client = httpx.Client
        patch.object(github.httpx, 'Client', side_effect=lambda **kw: client(transport=httpx.MockTransport(handle), **kw)).start()

    def connect(self):
        value = self.client.put('/api/github/connection', json={'token': self.token})
        self.assertEqual(value.status_code, 200, value.text)
        return value.json()

    def payload(self):
        self.connect()
        note, _ = self.note()
        self.register(note)
        preview = self.client.post('/api/github/preview', json={'kind': 'note', 'id': note['id']}).json()
        checked = self.client.post('/api/github/repository-check', json={'url': 'https://github.com/owner/notes'}).json()
        return {'kind': 'note', 'id': note['id'], 'version': preview['version'], 'url': checked['url'],
                'connection_id': checked['connection_id'], 'repo_id': checked['repo_id'], 'private': checked['private'],
                'request_id': service.uid(), 'title': preview['title'], 'body': preview['body'],
                'permissions_confirmed': True, 'content_confirmed': True}

    def test_token_encrypted_never_returned_and_validation_is_read_only(self):
        status = self.connect()
        encrypted = db.one('SELECT token FROM github_connections')['token']
        self.assertNotIn(self.token, encrypted)
        self.assertNotIn(self.token, json.dumps(status))
        self.assertEqual(github.credential(self.owner)['token'], self.token)
        checked = self.client.post('/api/github/repository-check', json={'url': 'https://github.com/owner/notes.git/'}).json()
        self.assertTrue(checked['can_attempt'])
        self.assertEqual(checked['write_permission'], 'unverified')
        self.assertTrue(all(r.method == 'GET' for r in self.requests))
        self.assertEqual(github.status('stranger')['connection'], None)
        with self.assertRaises(service.Error):
            github.credential('stranger')
        self.client.request('DELETE', '/api/github/connection', json={})
        self.assertEqual(db.all('SELECT * FROM github_connections'), [])
        self.assertEqual(self.client.post('/api/github/repository-check', json={'url': checked['url']}).status_code, 409)

    def test_repository_url_is_not_an_arbitrary_network_destination(self):
        for url in ('http://github.com/a/b', 'https://evil.test/a/b', 'https://github.com@evil.test/a/b',
                    'https://github.com:443/a/b', 'https://github.com/a/../b', 'https://github.com/a/%2Fb',
                    'https://github.com/a/b/issues', 'https://github.com/a/b?x=1', 'https://github.com/a/b#x',
                    'https://github.com/a/..', 'https://github.com/a\\b/c'):
            with self.subTest(url=url), self.assertRaises(service.Error):
                github.repository_name(url)
        self.assertEqual(self.requests, [])
        self.assertEqual(github.repository_name(' https://github.com/Owner/repo.name.git/ '), 'Owner/repo.name')

    def test_preview_keeps_ontology_ids_evidence_versions_and_owner_boundary(self):
        note, _ = self.note()
        self.register(note)
        preview = github.preview(self.owner, 'note', note['id'])
        body = preview['body']
        self.assertIn('USED_IN', body)
        self.assertIn('retrieval practice', body)
        for table in ('knowledge_concepts', 'knowledge_sources', 'knowledge_evidence', 'knowledge_assertions'):
            for row in db.all('SELECT id FROM ' + table):
                self.assertIn(row['id'], body)
        self.assertNotIn(self.owner, body)
        with self.assertRaises(service.Error):
            github.preview('stranger', 'note', note['id'])
        concept_id = db.one('SELECT id FROM knowledge_concepts')['id']
        self.assertIn('USED_IN', github.preview(self.owner, 'concept', concept_id)['body'])
        self.assertIn('42쪽', github.preview(self.owner, 'concept', concept_id)['body'])
        with self.assertRaises(service.Error):
            github.preview('stranger', 'concept', concept_id)
        db.execute('UPDATE reference_notes SET body=? WHERE id=?', ('![내 그림](/api/reference-images/' + 'a' * 32 + ')', note['id']))
        updated = github.preview(self.owner, 'note', note['id'])
        self.assertTrue(updated['has_images'])
        self.assertNotIn('/api/reference-images/', updated['body'])
        self.assertNotEqual(preview['version'], updated['version'])
        self.assertEqual(len(db.all('SELECT id FROM knowledge_concepts')), 2)

    def test_explicit_learning_snapshot_and_symmetric_relation_exports(self):
        data = {'title': '학습 기록', 'descriptions': ['한 개념을 정리한 기록'], 'scope': 'typescript',
                'concepts': ['기억'], 'prerequisites': [], 'source_url': 'https://example.com/article'}
        with db.connect(write=True) as c:
            knowledge.save(c, self.owner, 'unit:registered', 'context', 'unit', 1, data)
        preview = github.preview(self.owner, 'learning', 'unit:registered')
        self.assertIn('https://example.com/article', preview['body'])
        self.assertIn('한 개념을 정리한 기록', preview['body'])
        with self.assertRaises(service.Error):
            github.preview('stranger', 'learning', 'unit:registered')
        note, _ = self.note()
        self.register(note, self.graph_data(note, kind='RELATED_TO'))
        self.assertIn(' ↔ ', github.preview(self.owner, 'note', note['id'])['body'])

    def test_publish_is_explicit_revalidated_and_idempotent(self):
        data = self.payload()
        self.assertEqual(self.client.post('/api/github/shares', json={**data, 'content_confirmed': False}).status_code, 422)
        first = self.client.post('/api/github/shares', json=data)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['state'], 'published')
        self.assertEqual(first.json()['issue_url'], 'https://github.com/owner/notes/issues/42')
        self.assertIn('code-trainer-share:' + first.json()['id'], self.issue_body)
        same = self.client.post('/api/github/shares', json=data)
        duplicate = self.client.post('/api/github/shares', json={**data, 'request_id': service.uid()})
        self.assertEqual(same.json()['id'], first.json()['id'])
        self.assertEqual(duplicate.json()['id'], first.json()['id'])
        self.assertEqual(len([r for r in self.requests if r.method == 'POST']), 1)
        self.assertEqual(github.history('stranger'), [])
        reused = self.client.post('/api/github/shares', json={**data, 'repo_id': 999})
        self.assertEqual(reused.status_code, 409)
        with self.assertRaises(service.Error):
            github.recover('stranger', first.json()['id'], first.json()['issue_url'])

    def test_changed_source_visibility_connection_and_disabled_issues_block_publication(self):
        data = self.payload()
        cases = [{'version': '0' * 64}, {'private': False}, {'connection_id': '0' * 32}, {'repo_id': 99}]
        for change in cases:
            with self.subTest(change=change):
                result = self.client.post('/api/github/shares', json={**data, **change})
                self.assertEqual(result.status_code, 409, result.text)
        self.repo['has_issues'] = False
        checked = self.client.post('/api/github/repository-check', json={'url': data['url']}).json()
        self.assertFalse(checked['can_attempt'])
        self.assertEqual(self.client.post('/api/github/shares', json=data).status_code, 409)
        self.repo['has_issues'], self.repo['archived'] = True, True
        self.assertEqual(self.client.post('/api/github/shares', json=data).status_code, 409)
        self.assertFalse(any(r.method == 'POST' for r in self.requests))

    def test_revoked_token_does_not_expire_application_session_or_leak(self):
        self.connect()
        self.user_status = 401
        result = self.client.post('/api/github/repository-check', json={'url': 'https://github.com/owner/notes'})
        self.assertEqual(result.status_code, 400)
        self.assertIn('만료', result.json()['detail'])
        self.assertNotIn(self.token, result.text)
        self.assertIsNotNone(self.client.get('/api/session').json()['user'])

    def test_timeout_never_reposts_and_recovery_checks_marker_account_and_repo(self):
        data = self.payload()
        self.timeout = True
        first = self.client.post('/api/github/shares', json=data).json()
        self.assertEqual(first['state'], 'unknown')
        self.assertNotIn('secret-token', first['error'])
        repeat = self.client.post('/api/github/shares', json={**data, 'request_id': service.uid()}).json()
        self.assertEqual(first['id'], repeat['id'])
        self.assertEqual(len([r for r in self.requests if r.method == 'POST']), 1)
        endpoint = '/api/github/shares/' + first['id'] + '/recover'
        url = 'https://github.com/owner/notes/issues/42'
        self.issue_user = 999
        self.assertEqual(self.client.post(endpoint, json={'url': url}).status_code, 409)
        self.issue_user = 456
        saved, self.issue_body = self.issue_body, 'different issue'
        self.assertEqual(self.client.post(endpoint, json={'url': url}).status_code, 409)
        self.issue_body = saved
        self.assertEqual(self.client.post(endpoint, json={'url': url}).json()['state'], 'published')

    def test_known_rejection_can_retry_and_disconnect_is_blocked_during_send(self):
        data = self.payload()
        self.remote_status = 403
        first = self.client.post('/api/github/shares', json=data).json()
        self.assertEqual(first['state'], 'failed')
        self.remote_status = 201
        second = self.client.post('/api/github/shares', json={**data, 'request_id': service.uid()}).json()
        self.assertEqual(second['state'], 'published')
        db.execute("UPDATE github_shares SET state='sending'")
        self.assertEqual(self.client.request('DELETE', '/api/github/connection', json={}).status_code, 409)
        self.assertEqual(self.client.put('/api/github/connection', json={'token': self.token}).status_code, 409)
        service.initialize()
        self.assertEqual(db.one('SELECT state FROM github_shares')['state'], 'unknown')

    def test_connection_removed_during_preflight_prevents_send(self):
        data = self.payload()
        self.revoke_during_check = True
        self.assertEqual(self.client.post('/api/github/shares', json=data).status_code, 409)
        self.assertFalse(any(r.method == 'POST' for r in self.requests))

    def test_missing_master_key_and_bad_tokens_never_store_plaintext(self):
        with patch.dict(os.environ, {'TRAINER_GITHUB_ENCRYPTION_KEY': ''}):
            self.assertFalse(self.client.get('/api/github/connection').json()['storage_ready'])
            self.assertEqual(self.client.put('/api/github/connection', json={'token': self.token}).status_code, 503)
        for token in ('ghp_classic_token', 'github_pat_bad\nheader', self.token + ' bad'):
            result = self.client.put('/api/github/connection', json={'token': token})
            self.assertEqual(result.status_code, 422)
            self.assertNotIn(token, result.text)
        self.assertEqual(db.all('SELECT * FROM github_connections'), [])


if __name__ == '__main__':
    unittest.main()

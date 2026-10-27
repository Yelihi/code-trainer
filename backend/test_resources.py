"""Independent raw-source migration contracts; all data lives in temporary databases."""
import sqlite3
import unittest
from . import db, knowledge, service, test_app
from .sample import sample


class ResourcesTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    make_set = test_app.AppTest.make_set

    def legacy_source(self, key, *, owner=None, context_id=None, kind='text', content='원문\r\n  그대로\n'):
        owner = owner or self.owner
        db.execute('''INSERT INTO generations(id,owner,request_id,state,stage,context_id,created_at)
                      VALUES (?,?,?,'failed','분석',?,'2026-01-02T03:04:05+00:00')''',
                   (key, owner, key, context_id))
        db.execute('INSERT INTO source_documents VALUES (?,?,?,?,?,?)',
                   (key, context_id, kind, key + '.md', 'https://example.com/original' if kind == 'url' else None, content))

    def versions(self, origin):
        return db.all('''SELECT v.* FROM resource_versions v JOIN resources r
                         ON r.owner=v.owner AND r.id=v.resource_id
                         WHERE r.kind='source' AND r.origin_id=? ORDER BY v.revision''', (origin,))

    def test_legacy_idempotency_preserves_exact_sources_and_note_history(self):
        for key, kind, content in [('text', 'text', '원문\r\n  그대로\n'),
                                   ('fetched', 'url', '```js\nlet x = 1;\n```'),
                                   ('unfetched', 'url', None), ('empty', 'text', '')]:
            self.legacy_source(key, kind=kind, content=content)
        payload = {'id': service.uid(), 'revision': 0, 'title': '직접 노트', 'body': '첫 번째 내용', 'metadata': {}}
        self.assertEqual(self.client.post('/api/reference-notes', json=payload).status_code, 200)
        self.assertEqual(self.client.post('/api/reference-notes', json={**payload, 'revision': 1, 'body': '두 번째 내용'}).status_code, 200)
        self.client.post(f"/api/reference-notes/{payload['id']}/archive", json={'archived': True})
        notes = db.all('SELECT * FROM reference_notes')
        history = db.all('SELECT * FROM reference_note_versions')
        originals = db.all('SELECT * FROM source_documents ORDER BY id')
        db.initialize()
        first = db.all('SELECT * FROM resources ORDER BY id')
        snapshots = db.all('SELECT * FROM resource_versions ORDER BY resource_id,revision')
        db.initialize()
        self.assertEqual(db.all('SELECT * FROM resources ORDER BY id'), first)
        self.assertEqual(db.all('SELECT * FROM resource_versions ORDER BY resource_id,revision'), snapshots)
        self.assertEqual(len(first), 5)
        self.assertEqual(len(snapshots), 4)
        for original in originals:
            version = self.versions(original['id'])[0]
            for field in ('kind', 'name', 'url', 'content'):
                self.assertEqual(version[field], original[field], field)
            resource = next(r for r in first if r['origin_id'] == original['id'])
            self.assertEqual(resource['owner'], self.owner)
            self.assertEqual(resource['created_at'], '2026-01-02T03:04:05+00:00')
        note_resource = next(r for r in first if r['kind'] == 'note')
        self.assertEqual((note_resource['origin_id'], note_resource['note_id'], note_resource['created_at']),
                         (payload['id'], payload['id'], notes[0]['created_at']))
        self.assertEqual(db.all('SELECT * FROM reference_notes'), notes)
        self.assertEqual(db.all('SELECT * FROM reference_note_versions'), history)
        self.assertEqual(db.all('SELECT * FROM source_documents ORDER BY id'), originals)

    def test_immutable_versions_append_only_on_change(self):
        self.legacy_source('url', kind='url', content=None)
        db.initialize()
        original = self.versions('url')[0]
        for content in ('', '수집한 원문', None):
            db.execute('UPDATE source_documents SET content=? WHERE id=?', (content, 'url'))
            db.initialize()
            db.initialize()
        versions = self.versions('url')
        self.assertEqual(versions[0], original)
        self.assertEqual([v['content'] for v in versions], [None, '', '수집한 원문', None])
        self.assertEqual([v['revision'] for v in versions], [1, 2, 3, 4])

    def test_deletion_survival_covers_late_sources_and_keeps_graph_history(self):
        problem_set = self.make_set()
        context_id = problem_set['context_id']
        knowledge.add_unit(self.owner, context_id, 'u1')
        entries = db.all('SELECT * FROM knowledge_entries')
        concepts = db.all('SELECT * FROM knowledge_concepts')
        self.legacy_source('before', context_id=context_id)
        db.initialize()
        self.legacy_source('late', context_id=context_id, content='서버 시작 후 등록')
        # Either legacy foreign key can cascade a source, even if the other is unset.
        db.execute('UPDATE source_documents SET context_id=NULL WHERE id=?', ('late',))
        self.legacy_source('document-link', content='원문 쪽 연결만 존재')
        db.execute('UPDATE source_documents SET context_id=? WHERE id=?', (context_id, 'document-link'))
        db.execute('INSERT INTO learning_records VALUES (?,?,?,?,?)',
                   ('history', self.owner, 'fingerprint', '{"concepts":[],"exercises":[]}', 'old-time'))
        history = db.all('SELECT * FROM learning_records')
        response = self.client.request('DELETE', '/api/contexts/' + context_id, json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(db.one('SELECT id FROM contexts WHERE id=?', (context_id,)))
        self.assertEqual(db.all('SELECT * FROM source_documents'), [])
        self.assertEqual(db.all('SELECT * FROM exercises'), [])
        for key, content in [('before', '원문\r\n  그대로\n'), ('late', '서버 시작 후 등록'), ('document-link', '원문 쪽 연결만 존재')]:
            self.assertEqual(self.versions(key)[0]['content'], content)
        self.assertEqual(db.all('SELECT * FROM knowledge_entries'), entries)
        self.assertEqual(db.all('SELECT * FROM knowledge_concepts'), concepts)
        self.assertEqual(db.all('SELECT * FROM learning_records'), history)
        self.assertTrue(all(r['state'] == 'deleted' for r in db.all("SELECT state FROM knowledge_sources WHERE kind='learning'")))
        self.assertEqual(self.client.get('/api/admin/sources/late').status_code, 404)
        db.initialize()
        self.assertEqual(len(db.all('SELECT * FROM resources')), 3)

    def test_rollback_preserves_originals_on_migration_and_delete_failures(self):
        context, _ = sample()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', ('context', self.owner, context.model_dump_json(), None, 'old'))
        self.legacy_source('raw', context_id='context')
        source = db.all('SELECT * FROM source_documents')
        db.execute("CREATE TRIGGER block_snapshot BEFORE INSERT ON resource_versions BEGIN SELECT RAISE(ABORT, 'snapshot failure'); END")
        for action in (db.initialize, lambda: service.delete_context(self.owner, 'context')):
            with self.assertRaises(sqlite3.IntegrityError):
                action()
            self.assertEqual(db.all('SELECT * FROM resources'), [])
            self.assertEqual(db.all('SELECT * FROM resource_versions'), [])
            self.assertEqual(db.all('SELECT * FROM source_documents'), source)
            self.assertIsNotNone(db.one("SELECT id FROM contexts WHERE id='context'"))
        db.execute('DROP TRIGGER block_snapshot')
        db.execute("CREATE TRIGGER block_delete BEFORE DELETE ON contexts BEGIN SELECT RAISE(ABORT, 'delete failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            service.delete_context(self.owner, 'context')
        self.assertEqual(db.all('SELECT * FROM resources'), [])
        self.assertEqual(db.all('SELECT * FROM resource_versions'), [])
        self.assertEqual(db.all('SELECT * FROM source_documents'), source)
        db.execute('DROP TRIGGER block_delete')
        service.delete_context(self.owner, 'context')
        self.assertEqual(self.versions('raw')[0]['content'], source[0]['content'])

    def test_ownership_and_busy_guards_precede_preservation(self):
        problem_set = self.make_set()
        context_id = problem_set['context_id']
        self.legacy_source('raw', context_id=context_id)
        db.execute('INSERT INTO users VALUES (?,?,?,0)', ('other', 'other', 'unused'))
        self.legacy_source('other-raw', owner='other')
        with self.assertRaises(service.Error) as denied:
            service.delete_context('other', context_id)
        self.assertEqual(denied.exception.status, 404)
        self.assertEqual(db.all('SELECT * FROM resources'), [])
        for state in ('generating', 'validating'):
            db.execute('UPDATE generations SET state=? WHERE id=?', (state, 'raw'))
            with self.assertRaises(service.Error) as busy:
                service.delete_context(self.owner, context_id)
            self.assertEqual(busy.exception.status, 409)
            self.assertEqual(db.all('SELECT * FROM resources'), [])
        db.execute("UPDATE generations SET state='failed' WHERE id='raw'")
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',
                   ('active', self.owner, problem_set['exercises'][0]['id'], 'active', '{}', 'running', '{}', 'old'))
        with self.assertRaises(service.Error) as busy:
            service.delete_context(self.owner, context_id)
        self.assertEqual(busy.exception.status, 409)
        self.assertEqual(db.all('SELECT * FROM resources'), [])
        db.execute('DELETE FROM attempts WHERE id=?', ('active',))
        note_id = service.uid()
        self.client.post('/api/reference-notes', json={'id': note_id, 'revision': 0, 'title': '노트', 'body': '내 노트', 'metadata': {}})
        db.initialize()
        self.assertEqual({r['origin_id']: r['owner'] for r in db.all("SELECT * FROM resources WHERE kind='source'")},
                         {'raw': self.owner, 'other-raw': 'other'})
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute('''INSERT INTO resources(id,owner,kind,origin_id,note_id,created_at)
                          VALUES ('bad','other','note',?,?, 'old')''', (note_id, note_id))
        source_resource = db.one("SELECT id FROM resources WHERE origin_id='raw'")['id']
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute('''INSERT INTO resource_versions(owner,resource_id,revision,kind,name,url,content,created_at)
                          VALUES ('other',?,2,'text','bad',NULL,'bad','old')''', (source_resource,))
        service.delete_context(self.owner, context_id)
        self.assertEqual(self.versions('other-raw')[0]['owner'], 'other')
        self.assertIsNotNone(db.one("SELECT id FROM source_documents WHERE id='other-raw'"))
        with db.connect() as c:
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_missing_source_is_not_reconstructed_from_generated_material(self):
        self.make_set()
        db.initialize()
        db.initialize()
        self.assertEqual(db.all('SELECT * FROM resources'), [])
        self.assertEqual(db.all('SELECT * FROM resource_versions'), [])


class ResourceRegistrationTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def register(self, **changes):
        payload = {'request_id': service.uid(), 'kind': 'text', 'name': '원문', 'content': '# 원문\r\n  그대로\n'}
        payload.update(changes)
        response = self.client.post('/api/resources', json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_text_registration_replay_metadata_and_stale_edit(self):
        from unittest.mock import patch
        with patch.object(service.runner, 'available', side_effect=AssertionError('runner called')), patch('backend.ai.generate', side_effect=AssertionError('AI called')):
            first = self.register(request_id='text-request')
            self.assertEqual(first['content'], '# 원문\r\n  그대로\n')
            self.assertEqual(self.register(request_id='text-request'), first)
        resource_id = first['id']
        same = self.register(resource_id=resource_id, revision=1, name='제목 변경')
        self.assertEqual((same['name'], same['revision']), ('제목 변경', 1))
        changed = self.register(resource_id=resource_id, revision=1, content='변경 본문')
        self.assertEqual(changed['revision'], 2)
        old = self.client.get(f'/api/resources/{resource_id}/versions/1').json()
        self.assertEqual((old['name'], old['content']), ('원문', first['content']))
        payload = {'request_id': 'stale-request', 'kind': 'text', 'name': '원문', 'content': '덮어쓰기', 'resource_id': resource_id, 'revision': 1}
        self.assertEqual(self.client.post('/api/resources', json=payload).status_code, 409)
        self.assertEqual(self.client.post('/api/resources', json={**payload, 'request_id': 'text-request'}).status_code, 409)

    def test_url_versions_failed_retry_and_no_refetch_on_replay(self):
        from unittest.mock import patch
        from . import source
        payload = {'kind': 'url', 'url': 'https://example.com/article', 'content': ''}
        with patch.object(source, 'fetch', return_value='첫 본문') as fetch:
            first = self.register(request_id='url-request', **payload)
            self.assertEqual(self.register(request_id='url-request', **payload), first)
            self.assertEqual(fetch.call_count, 1)
            same = self.register(name='제목만 변경', **payload)
        self.assertEqual((same['id'], same['revision']), (first['id'], 1))
        with patch.object(source, 'fetch', side_effect=source.SourceError('수집 실패')):
            failed = self.register(**payload)
        self.assertEqual((failed['state'], failed['content'], failed['revision']), ('failed', '첫 본문', 1))
        with patch.object(source, 'fetch', return_value='바뀐 본문'):
            changed = self.register(**payload)
        self.assertEqual((changed['id'], changed['revision']), (first['id'], 2))
        self.assertEqual([v['revision'] for v in changed['versions']], [2, 1])
        self.assertEqual(len(db.all('SELECT * FROM resources')), 1)

    def test_initial_url_failure_and_ssrf_keep_retryable_record(self):
        failed = self.register(kind='url', url='http://127.0.0.1/private', content='')
        self.assertEqual((failed['state'], failed['revision'], failed['content']), ('failed', 0, None))
        self.assertTrue(failed['error'])
        detail = self.client.get('/api/resources/' + failed['id']).json()
        self.assertEqual(detail['url'], 'http://127.0.0.1/private')

    def test_owned_listing_note_save_and_versions(self):
        from . import resources
        own = self.register()
        note_id = service.uid()
        response = self.client.post('/api/reference-notes', json={'id': note_id, 'revision': 0, 'title': '내 노트', 'body': '새 노트', 'metadata': {}})
        self.assertEqual(response.status_code, 200)
        listing = self.client.get('/api/resources?page=99').json()
        self.assertEqual((listing['total'], listing['page']), (2, 1))
        self.assertEqual(self.client.get('/api/resources?kind=note&q=새').json()['items'][0]['note_id'], note_id)
        self.client.post(f'/api/reference-notes/{note_id}/archive', json={'archived': True})
        self.assertEqual(self.client.get('/api/resources?kind=note').json()['total'], 0)
        self.assertEqual(resources.listing('other', '', 1, 'all')['total'], 0)
        db.execute('INSERT INTO users VALUES (?,?,?,0)', ('other', 'other', 'unused'))
        db.execute('UPDATE sessions SET user_id=?', ('other',))
        for endpoint in ('/api/resources/' + own['id'], '/api/resources/' + own['id'] + '/versions/1'):
            self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.post('/api/resources', json={'request_id': 'other-request', 'resource_id': own['id'], 'revision': 1, 'kind': 'text', 'name': 'bad', 'content': 'bad'}).status_code, 404)

    def test_concurrent_fetch_is_reserved_without_holding_database_lock(self):
        from unittest.mock import patch
        from . import resources, source
        from .resource_schema import ResourceInput
        payload = {'request_id': 'first-request', 'kind': 'url', 'name': 'URL', 'url': 'https://example.com/concurrent'}
        def fetch(_):
            # A separate connection can write during network IO; a second request cannot overwrite it.
            db.execute("UPDATE users SET username=username WHERE id=?", (self.owner,))
            with self.assertRaises(service.Error) as busy:
                resources.register(self.owner, ResourceInput(**{**payload, 'request_id': 'second-request'}))
            self.assertEqual(busy.exception.status, 409)
            return '원문'
        with patch.object(source, 'fetch', side_effect=fetch):
            result = resources.register(self.owner, ResourceInput(**payload))
        self.assertEqual(result['revision'], 1)

    def test_expired_fetch_can_retry_and_late_result_cannot_overwrite(self):
        from unittest.mock import patch
        from . import resources, source
        from .resource_schema import ResourceInput
        payload = {'request_id': 'first-request', 'kind': 'url', 'name': 'URL', 'url': 'https://example.com/expired'}
        def fetch(_):
            db.execute('UPDATE resource_registrations SET lease_until=0')
            with patch.object(source, 'fetch', return_value='재시도 본문'):
                resources.register(self.owner, ResourceInput(**{**payload, 'request_id': 'retry-request'}))
            return '늦은 이전 응답'
        with patch.object(source, 'fetch', side_effect=fetch):
            with self.assertRaises(service.Error) as stale:
                resources.register(self.owner, ResourceInput(**payload))
        self.assertEqual(stale.exception.status, 409)
        self.assertEqual(db.one('SELECT content FROM resource_versions')['content'], '재시도 본문')

    def test_adopted_legacy_url_survives_restart_without_reverting_body(self):
        from unittest.mock import patch
        from . import source
        for key in ('legacy-one', 'legacy-two'):
            db.execute("INSERT INTO generations(id,owner,request_id,state,stage,created_at) VALUES (?,?,?,'failed','old','old')", (key, self.owner, key))
            db.execute('INSERT INTO source_documents VALUES (?,NULL,?,?,?,?)', (key, 'url', key, 'https://example.com/legacy', '이전 본문'))
        db.initialize()
        with patch.object(source, 'fetch', return_value='변경 본문'):
            result = self.register(kind='url', url='https://example.com/legacy', content='')
        db.initialize()
        self.assertEqual(self.client.get('/api/resources/' + result['id']).json()['content'], '변경 본문')
        self.assertEqual(len(db.all('SELECT * FROM resources')), 2)
        other = db.one('SELECT id FROM resources WHERE id<>?', (result['id'],))['id']
        response = self.client.post('/api/resources', json={'request_id': 'legacy-other', 'resource_id': other, 'kind': 'url', 'name': 'other', 'url': result['url']})
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get('/api/resources/' + other).json()['content'], '이전 본문')

    def test_snapshot_failure_rolls_back_completion_and_preserves_last_good_body(self):
        first = self.register()
        db.execute("CREATE TRIGGER block_new_snapshot BEFORE INSERT ON resource_versions BEGIN SELECT RAISE(ABORT, 'snapshot failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.register(resource_id=first['id'], revision=1, content='저장 실패 본문')
        self.assertEqual(self.client.get('/api/resources/' + first['id']).json()['content'], first['content'])
        self.assertEqual(len(db.all('SELECT * FROM resource_versions')), 1)
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM resource_requests WHERE response IS NULL')['n'], 1)

    def test_registration_validation_and_note_version_shape(self):
        for patch_data in ({'content': ' '}, {'content': 'x' * 60001}, {'kind': 'sample'}, {'name': ' '}, {'kind': 'url', 'url': ''}):
            response = self.client.post('/api/resources', json={'request_id': service.uid(), 'kind': 'text', 'name': '검증', 'content': '본문', **patch_data})
            self.assertEqual(response.status_code, 422)
        note_id = service.uid()
        self.client.post('/api/reference-notes', json={'id': note_id, 'revision': 0, 'title': '노트', 'body': '본문', 'metadata': {}})
        resource_id = db.one('SELECT id FROM resources WHERE note_id=?', (note_id,))['id']
        self.assertEqual(self.client.get(f'/api/resources/{resource_id}/versions/1').json(), {'revision': 1, 'name': '노트', 'content': '본문'})
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/resources').status_code, 401)
        self.assertEqual(self.client.post('/api/resources', json={'request_id': service.uid(), 'kind': 'text', 'name': '검증', 'content': '본문'}).status_code, 401)

    def test_pre_rsa_request_hash_still_replays_without_fetch(self):
        import hashlib
        import json
        from unittest.mock import patch
        from . import source
        body = {'request_id': 'pre-rsa-request', 'kind': 'url', 'name': 'Original', 'url': 'https://example.com/original'}
        with patch.object(source, 'fetch', return_value='Original source'):
            response = self.client.post('/api/resources', json=body)
        self.assertEqual(response.status_code, 200)
        # Exact pre-RSA model field order/defaults, independent of the new schema.
        old = dict(request_id=body['request_id'], resource_id=None, revision=0, kind='url', name=body['name'], url=body['url'], content='')
        digest = hashlib.sha256(json.dumps(old, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
        db.execute('UPDATE resource_requests SET payload_hash=? WHERE owner=? AND request_id=?', (digest, self.owner, body['request_id']))
        with patch.object(source, 'fetch') as fetch:
            replay = self.client.post('/api/resources', json=body)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), response.json())
        fetch.assert_not_called()

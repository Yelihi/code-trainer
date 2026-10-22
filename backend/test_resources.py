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

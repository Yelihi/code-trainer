import base64
import copy
import io
import json
import zipfile
import unittest
from unittest.mock import patch
from PIL import Image
from . import ai, db, ontology, reference_notes, service, test_app
from .note_schema import KnowledgeProposal, ReferenceReviewFeedback
from .sample import sample


class ReferenceNotesTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def note(self, body='간격을 두고 기억을 떠올리는 인출 연습은 복습에 활용된다.', title='책에서 배운 인출 연습'):
        data = {'id': service.uid(), 'revision': 0, 'title': title, 'body': body,
                'metadata': {'kind': 'book', 'title': '학습 기록', 'author': '저자', 'locator': '42쪽', 'url': ''}}
        result = self.client.post('/api/reference-notes', json=data)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json(), data

    def graph_data(self, note, concepts=None, kind='USED_IN'):
        concepts = concepts or [
            {'key': 'a', 'existing_id': '', 'pref_label': '인출 연습', 'definition': '기억을 스스로 떠올리는 연습',
             'scope': '학습', 'aliases': ['retrieval practice'], 'quote': note['body'], 'basis': 'source'},
            {'key': 'b', 'existing_id': '', 'pref_label': '복습', 'definition': '배운 내용을 다시 살펴보는 학습',
             'scope': '학습', 'aliases': [], 'quote': note['body'], 'basis': 'source'}]
        return {'concepts': concepts, 'assertions': [
            {'subject': 'a', 'kind': kind, 'object': 'b', 'text': '인출 연습을 복습에 활용한다.',
             'scope': '학습', 'quote': note['body'], 'basis': 'source'},
            {'subject': 'a', 'kind': 'CLAIM', 'object': '', 'text': '기억을 스스로 떠올리는 연습이다.',
             'scope': '학습', 'quote': note['body'], 'basis': 'interpretation'}]}

    def register(self, note, data=None, **extra):
        payload = {'revision': note['revision'], 'request_id': service.uid(), 'data': data or self.graph_data(note), **extra}
        result = self.client.post(f"/api/reference-notes/{note['id']}/knowledge", json=payload)
        return result, payload

    def test_explicit_save_versions_conflicts_and_no_implicit_graph(self):
        note, payload = self.note()
        self.assertEqual(note['revision'], 1)
        self.assertEqual(self.client.post('/api/reference-notes', json=payload).json()['revision'], 1)
        self.assertEqual(self.client.get('/api/me/knowledge-graph').json()['nodes'], [])
        self.assertEqual(db.all('SELECT * FROM learning_observations'), [])
        payload.update(revision=1, body='새로 이해한 내용입니다.')
        updated = self.client.post('/api/reference-notes', json=payload)
        self.assertEqual(updated.json()['revision'], 2)
        self.assertEqual(self.client.post('/api/reference-notes', json={**payload, 'body': '충돌하는 수정'}).status_code, 409)
        old = self.client.get(f"/api/reference-notes/{note['id']}/versions/1").json()
        self.assertEqual(old['body'], note['body'])
        self.assertEqual(self.client.get('/api/reference-notes?q=새로').json()['total'], 1)
        with self.assertRaises(service.Error):
            reference_notes.view('not-owner', note['id'])
        self.assertEqual(self.client.get('/api/reference-notes?page=0').status_code, 422)
        payload.update(id=service.uid(), revision=0, metadata={'url': 'javascript:alert(1)'})
        self.assertEqual(self.client.post('/api/reference-notes', json=payload).status_code, 422)

    def test_registration_is_explicit_idempotent_typed_and_versioned(self):
        note, payload = self.note()
        result, registration = self.register(note)
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(self.client.post(f"/api/reference-notes/{note['id']}/knowledge", json=registration).status_code, 200)
        self.assertEqual(len(db.all('SELECT id FROM knowledge_concepts')), 2)
        self.assertEqual(len(db.all('SELECT id FROM knowledge_evidence')), 4)
        self.assertEqual(len(db.all('SELECT id FROM knowledge_assertions')), 2)
        self.assertEqual(db.all('SELECT * FROM learning_observations'), [])
        graph = self.client.get('/api/me/knowledge-graph').json()
        self.assertEqual(len([n for n in graph['nodes'] if n['kind'] == 'note']), 1)
        self.assertEqual(len([e for e in graph['edges'] if e['kind'] == 'USED_IN']), 1)
        concept_ids = [n['id'] for n in graph['nodes'] if n['kind'] == 'concept']
        self.assertTrue(all(len(key) == 32 for key in concept_ids))
        self.assertEqual(self.register(note)[0].status_code, 409)
        newer = self.client.post('/api/reference-notes', json={**payload, 'revision': 1, 'body': note['body'] + '\n조건을 다시 검토합니다.'}).json()
        self.assertEqual(newer['registration']['state'], 'stale')
        graph = self.client.get('/api/me/knowledge-graph').json()
        self.assertFalse(any(e['kind'] == 'USED_IN' for e in graph['edges']))
        self.assertTrue(next(n for n in graph['nodes'] if n['kind'] == 'note')['needs_review'])
        self.assertEqual(self.register(note)[0].status_code, 409)
        data = self.graph_data(newer)
        for c in data['concepts']:
            c['existing_id'] = db.one('SELECT id FROM knowledge_concepts WHERE pref_label=?', (c['pref_label'],))['id']
        self.assertEqual(self.register(newer, data)[0].status_code, 200)
        self.assertEqual(len(db.all('SELECT id FROM knowledge_concepts')), 2)
        self.assertEqual(len(db.all('SELECT id FROM knowledge_sources')), 2)
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM knowledge_registrations')['n'], 2)
        self.assertTrue(any(e['kind'] == 'USED_IN' for e in self.client.get('/api/me/knowledge-graph').json()['edges']))

    def test_ontology_rejects_bad_evidence_foreign_ids_self_edges_cycles_and_rolls_back(self):
        note, _ = self.note()
        bad = self.graph_data(note)
        bad['concepts'][0]['quote'] = '원문에 없는 근거'
        self.assertEqual(self.register(note, bad)[0].status_code, 422)
        bad = self.graph_data(note)
        bad['concepts'][0]['existing_id'] = 'foreign'
        self.assertEqual(self.register(note, bad)[0].status_code, 422)
        bad = self.graph_data(note)
        bad['assertions'][0]['subject'] = 'missing'
        self.assertEqual(self.register(note, bad)[0].status_code, 422)
        bad = self.graph_data(note, kind='BROADER_THAN')
        bad['assertions'].append({**bad['assertions'][0], 'subject': 'b', 'object': 'a'})
        self.assertEqual(self.register(note, bad)[0].status_code, 422)
        self.assertEqual(db.all('SELECT * FROM knowledge_sources'), [])
        self.assertEqual(db.all('SELECT * FROM knowledge_concepts'), [])
        bad = self.graph_data(note)
        bad['assertions'][0]['object'] = 'a'
        self.assertEqual(self.register(note, bad)[0].status_code, 422)
        self.assertEqual(self.register(note, self.graph_data(note, kind='RELATED_TO'))[0].status_code, 200)
        second, _ = self.note(title='다른 출처')
        data = self.graph_data(second, kind='RELATED_TO')
        for c in data['concepts']:
            c['existing_id'] = db.one('SELECT id FROM knowledge_concepts WHERE pref_label=?', (c['pref_label'],))['id']
        data['assertions'][0].update(subject='b', object='a')
        self.assertEqual(self.register(second, data)[0].status_code, 200)
        self.assertEqual(len(db.all("SELECT id FROM knowledge_assertions WHERE kind='RELATED_TO'")), 1)
        self.assertEqual(len(db.all("SELECT id FROM knowledge_concepts")), 2)

    def test_question_evidence_does_not_become_an_established_relation(self):
        note, _ = self.note(body='인출 연습은 복습에 도움이 될까?')
        data = self.graph_data(note)
        for a in data['assertions']:
            a['basis'] = 'question'
        self.assertEqual(self.register(note, data)[0].status_code, 200)
        graph = self.client.get('/api/me/knowledge-graph').json()
        self.assertFalse(any(e['kind'] == 'USED_IN' for e in graph['edges']))
        self.assertTrue(all(not n.get('claims') for n in graph['nodes']))

    def test_refuting_evidence_is_preserved_and_not_used_as_a_positive_review_link(self):
        note, _ = self.note()
        data = self.graph_data(note)
        data['assertions'][0]['disposition'] = 'refutes'
        self.assertEqual(self.register(note, data)[0].status_code, 200)
        edge = next(e for e in self.client.get('/api/me/knowledge-graph').json()['edges'] if e['kind'] == 'USED_IN')
        self.assertIn('반박', edge['label'])
        self.assertEqual(edge['sources'][0]['disposition'], 'refutes')
        schema = ai.response_schema(ReferenceReviewFeedback, source_ids=['source-one', 'source-two'])
        self.assertEqual(schema['properties']['data']['anyOf'][0]['properties']['citations']['items']['enum'], ['source-one', 'source-two'])

    def test_images_owned_sanitized_exported_and_foreign_image_rejected(self):
        output = io.BytesIO()
        Image.new('RGB', (12, 8), 'red').save(output, format='PNG')
        body = {'name': '../../image.png', 'content': base64.b64encode(output.getvalue()).decode()}
        image = self.client.post('/api/reference-images', json=body)
        self.assertEqual(image.status_code, 200, image.text)
        self.assertEqual(self.client.post('/api/reference-images', json=body).json(), image.json())
        raw = self.client.get(image.json()['url'])
        self.assertEqual(raw.headers['content-type'], 'image/webp')
        self.assertEqual(raw.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(Image.open(io.BytesIO(raw.content)).size, (12, 8))
        with self.assertRaises(service.Error):
            reference_notes.image_read('not-owner', image.json()['id'])
        self.assertEqual(self.client.post('/api/reference-images', json={'name': 'x.svg', 'content': base64.b64encode(b'<svg onload="alert(1)"/>').decode()}).status_code, 422)
        note, _ = self.note(body='사진 정리\n\n![그림](' + image.json()['url'] + ')')
        exported = self.client.get(f"/api/reference-notes/{note['id']}/export")
        with zipfile.ZipFile(io.BytesIO(exported.content)) as bundle:
            self.assertEqual(len(bundle.namelist()), 3)
            self.assertIn('images/' + image.json()['id'] + '.webp', bundle.namelist())
            self.assertNotIn('/api/', bundle.read('note.md').decode())
            self.assertEqual(json.loads(bundle.read('metadata.json'))['note']['id'], note['id'])
        other, payload = self.note()
        db.execute("UPDATE reference_images SET owner=? WHERE id=?", (self.owner, image.json()['id']))
        payload.update(body='![bad](/api/reference-images/' + 'f' * 32 + ')', revision=1)
        self.assertEqual(self.client.post('/api/reference-notes', json=payload).status_code, 422)
        self.client.post('/api/logout', json={})
        for endpoint in (image.json()['url'], '/api/reference-notes/' + note['id'], f"/api/reference-notes/{note['id']}/export"):
            self.assertEqual(self.client.get(endpoint).status_code, 401)

    def test_ai_proposals_are_candidates_only_and_validate_citations(self):
        note, _ = self.note()
        data = KnowledgeProposal.model_validate(self.graph_data(note))
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=data):
            result = self.client.post(f"/api/reference-notes/{note['id']}/proposals", json={'revision': 1})
        proposal = self.client.get('/api/reference-proposals/' + result.json()['id']).json()
        self.assertEqual(proposal['state'], 'ready')
        self.assertEqual(db.all('SELECT * FROM knowledge_concepts'), [])
        self.assertEqual(self.register(note, proposal['data'], proposal_id=proposal['id'])[0].status_code, 200)
        provenance = json.loads(db.one('SELECT provenance FROM knowledge_registrations')['provenance'])
        self.assertEqual(provenance['prompt_version'], 'reference-ontology-v1')
        second, _ = self.note()
        data.concepts[0].quote = '만들어 낸 문장'
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=data):
            result = self.client.post(f"/api/reference-notes/{second['id']}/proposals", json={'revision': 1})
        self.assertEqual(self.client.get('/api/reference-proposals/' + result.json()['id']).json()['state'], 'failed')
        with self.assertRaises(service.Error):
            reference_notes.proposal_view('other', proposal['id'])

    def test_connected_review_preserves_answers_and_grounds_followups(self):
        note, _ = self.note()
        self.assertEqual(self.register(note)[0].status_code, 200)
        second, _ = self.note(body='기억을 꺼내는 연습을 여러 날에 나눠 반복해보았다.', title='강의 뒤의 실험')
        candidates = self.graph_data(second)['concepts']
        for c in candidates:
            c['existing_id'] = db.one('SELECT id FROM knowledge_concepts WHERE pref_label=?', (c['pref_label'],))['id']
        self.assertEqual(self.register(second, {'concepts': candidates, 'assertions': []})[0].status_code, 200)
        request = {'request_id': service.uid(), 'note_id': note['id']}
        review = self.client.post('/api/reference-reviews', json=request).json()
        self.assertEqual(len(review['sources']), 2)
        self.assertEqual(self.client.post('/api/reference-reviews', json=request).json()['id'], review['id'])
        self.assertIn(second['id'], [s['note_id'] for s in review['sources']])
        body = {'request_id': service.uid(), 'revision': 0, 'answer': '기억을 꺼내려 시도하는 과정이라고 이해했습니다.'}
        with patch.object(ai, 'available', return_value=False):
            result = self.client.post('/api/reference-reviews/' + review['id'] + '/answers', json=body)
        self.assertEqual(result.json()['state'], 'failed')
        self.assertEqual(result.json()['turns'][-1]['answer'], body['answer'])
        self.assertEqual(len(db.all('SELECT * FROM learning_observations')), 2)
        feedback = ReferenceReviewFeedback(feedback='인출의 과정을 설명했습니다.', question='두 번째 노트에서 간격을 둔 이유는 무엇인가요?',
                                          citations=['S2'])
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=feedback):
            self.client.post('/api/reference-reviews/' + review['id'] + '/answers', json=body)
        ready = self.client.get('/api/reference-reviews/' + review['id']).json()
        self.assertEqual(ready['state'], 'ready')
        self.assertEqual(ready['turns'][-1]['citations'], [review['sources'][1]['id']])
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate') as generate:
            self.client.post('/api/reference-reviews/' + review['id'] + '/answers', json=body)
            generate.assert_not_called()
        self.assertEqual(len(db.all('SELECT * FROM learning_observations')), 2)
        before = copy.deepcopy(ready['sources'])
        self.client.post(f"/api/reference-notes/{second['id']}/archive", json={'archived': True})
        self.assertEqual(self.client.get('/api/reference-reviews/' + review['id']).json()['sources'], before)
        new = self.client.post('/api/reference-reviews', json={**request, 'request_id': service.uid()}).json()
        self.assertEqual(len(new['sources']), 1)
        with self.assertRaises(service.Error):
            reference_notes.review_view('other', review['id'])
        feedback.citations = ['foreign-source']
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=feedback):
            self.client.post('/api/reference-reviews/' + ready['id'] + '/answers', json={**body, 'request_id': service.uid(), 'revision': ready['revision']})
        failed = self.client.get('/api/reference-reviews/' + ready['id']).json()
        self.assertEqual(failed['state'], 'failed')
        self.assertEqual(failed['turns'][-1]['role'], 'user')

    def test_archive_restore_requires_new_explicit_registration(self):
        note, _ = self.note()
        self.assertEqual(self.register(note)[0].status_code, 200)
        endpoint = f"/api/reference-notes/{note['id']}/archive"
        self.assertEqual(self.client.post(endpoint, json={'archived': True}).status_code, 200)
        self.assertFalse(any(n['kind'] == 'note' for n in self.client.get('/api/me/knowledge-graph').json()['nodes']))
        self.assertEqual(self.client.get('/api/reference-notes').json()['total'], 0)
        restored = self.client.post(endpoint, json={'archived': False}).json()
        self.assertEqual(restored['revision'], 2)
        self.assertEqual(restored['registration']['state'], 'stale')
        self.assertEqual(self.register(restored)[0].status_code, 200)

    def test_correcting_an_outdated_direction_does_not_create_a_false_cycle(self):
        note, payload = self.note()
        data = self.graph_data(note, kind='PREREQUISITE_OF')
        self.assertEqual(self.register(note, data)[0].status_code, 200)
        updated = self.client.post('/api/reference-notes', json={**payload, 'revision': 1, 'body': note['body'] + '\n선행 방향을 수정한다.'}).json()
        for concept in data['concepts']:
            concept['existing_id'] = db.one('SELECT id FROM knowledge_concepts WHERE pref_label=?', (concept['pref_label'],))['id']
        data['assertions'][0].update(subject='b', object='a')
        self.assertEqual(self.register(updated, data)[0].status_code, 200)
        graph = self.client.get('/api/me/knowledge-graph').json()
        self.assertEqual(len([e for e in graph['edges'] if e['kind'] == 'PREREQUISITE_OF']), 1)

    def test_existing_course_concepts_share_storage_and_can_link_to_notes(self):
        context, _ = sample()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', ('source-course', self.owner, context.model_dump_json(), None, service.now()))
        self.client.post('/api/contexts/source-course/units/u1/knowledge', json={})
        old = db.all('SELECT * FROM knowledge_concepts')
        self.assertTrue(old)
        ontology.migrate()
        self.assertEqual(db.all('SELECT * FROM knowledge_concepts'), old)
        note, _ = self.note(body='이 수업의 개념을 책의 사례와 연결해서 이해했습니다.')
        first = old[0]
        data = {'concepts': [{'key': 'a', 'existing_id': first['id'], 'pref_label': first['pref_label'],
                'definition': first['definition'], 'scope': first['scope'], 'aliases': [], 'quote': note['body'], 'basis': 'interpretation'}], 'assertions': []}
        self.assertEqual(self.register(note, data)[0].status_code, 200)
        graph = self.client.get('/api/me/knowledge-graph').json()
        concept = next(n for n in graph['nodes'] if n['id'] == first['id'])
        self.assertEqual(len(concept['sources']), 2)
        self.assertEqual(len([e for e in graph['edges'] if e['target'] == first['id']]), 2)
        self.client.request('DELETE', '/api/contexts/source-course', json={})
        self.assertEqual(db.one("SELECT state FROM knowledge_sources WHERE kind='learning'")['state'], 'deleted')


if __name__ == '__main__':
    unittest.main()

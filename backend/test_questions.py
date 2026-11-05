import unittest
from unittest.mock import patch
from . import db, questions, test_app
from .questions import Guide


class QuestionsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    @staticmethod
    def edit(item, **changes):
        return {key: changes.get(key, item[key]) for key in ('revision', 'text', 'context', 'status', 'links', 'note_id')}

    def test_capture_link_guide_and_note(self):
        created = self.client.post('/api/questions', json={'text': 'Zustand는 왜 store인가?', 'request_id': 'question-one'})
        self.assertEqual(created.status_code, 200, created.text)
        item = created.json()
        self.assertEqual(self.client.post('/api/questions', json={'text': 'Zustand는 왜 store인가?', 'request_id': 'question-one'}).json()['id'], item['id'])
        self.assertEqual(self.client.get('/api/questions?status=open').json()['total'], 1)
        resource = self.client.post('/api/resources', json={'request_id': 'source-one', 'revision': 0, 'kind': 'text',
            'name': '상태 관리 메모', 'content': 'store는 컴포넌트 밖에 둔 상태 저장소다.', 'url': ''}).json()
        updated = self.client.put('/api/questions/' + item['id'], json=self.edit(item, links=[
            {'resource_id': resource['id'], 'excerpt': 'store는 컴포넌트 밖에 둔 상태 저장소다.'}])).json()
        self.assertEqual(updated['revision'], 2)
        self.assertEqual(self.client.put('/api/questions/' + item['id'], json=self.edit(item, text='충돌')).status_code, 409)
        with patch.object(questions.ai, 'available', return_value=True), patch.object(questions.ai, 'generate', return_value=Guide(
            title='상태 저장소 확인', reading='원문에서 저장소 범위를 확인', checks=['컴포넌트 경계는?'],
            practice='두 컴포넌트에서 공유', expected_output='관찰 기록', source_ids=[resource['id']])):
            job, fresh = questions.begin(self.owner, item['id'], questions.GuideRequest(request_id='guide-one', revision=2))
            self.assertTrue(fresh)
            questions.generate(job['id'])
        self.assertEqual(questions.latest_guide(self.owner, item['id'])['guide']['state'], 'ready')
        note_id = 'a' * 32
        self.assertEqual(self.client.post('/api/reference-notes', json={'id': note_id, 'revision': 0, 'title': '내 설명',
            'body': '직접 설명한 내용', 'metadata': {}}).status_code, 200)
        finished = self.client.put('/api/questions/' + item['id'], json=self.edit(updated, note_id=note_id, status='done')).json()
        self.assertEqual((finished['note_id'], finished['status']), (note_id, 'done'))
        self.assertEqual(self.client.get('/api/questions?status=done').json()['total'], 1)
        self.assertEqual(self.client.get('/api/questions/' + item['id']).status_code, 200)
        self.assertEqual(self.client.request('DELETE', '/api/questions/' + item['id'], json={}).status_code, 200)
        self.assertEqual(self.client.get('/api/questions/' + item['id']).status_code, 404)

    def test_source_and_owner_boundaries(self):
        item = self.client.post('/api/questions', json={'text': '무엇인가?', 'request_id': 'question-two'}).json()
        self.assertEqual(self.client.post('/api/questions/' + item['id'] + '/guide', json={'request_id': 'guide-two', 'revision': 1}).status_code, 409)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        self.assertEqual(self.client.get('/api/questions/' + item['id']).status_code, 200)
        self.assertEqual(questions.listing('other')['total'], 0)
        with self.assertRaises(Exception): questions.view('other', item['id'])

    def test_guide_is_stale_when_linked_source_changes(self):
        item = self.client.post('/api/questions', json={'text': '본문은 무엇을 설명하나?', 'request_id': 'question-three'}).json()
        source = self.client.post('/api/resources', json={'request_id': 'source-three', 'kind': 'text',
            'name': '원문', 'content': '처음 본문'}).json()
        linked = self.client.put('/api/questions/' + item['id'], json=self.edit(item, links=[{'resource_id': source['id'], 'excerpt': ''}])).json()
        with patch.object(questions.ai, 'available', return_value=True):
            job, _ = questions.begin(self.owner, item['id'], questions.GuideRequest(request_id='guide-three', revision=linked['revision']))
        def change_source(*_args):
            result = self.client.post('/api/resources', json={'request_id': 'source-three-edit', 'resource_id': source['id'],
                'revision': 1, 'kind': 'text', 'name': '원문', 'content': '바뀐 본문'})
            self.assertEqual(result.status_code, 200, result.text)
            return Guide(title='읽기', reading='확인', checks=['차이'], practice='비교', expected_output='기록', source_ids=[source['id']])
        with patch.object(questions.ai, 'generate', side_effect=change_source):
            questions.generate(job['id'])
        self.assertEqual(questions.latest_guide(self.owner, item['id'])['guide']['state'], 'stale')

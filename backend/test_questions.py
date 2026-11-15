import unittest
import json
import sqlite3
from unittest.mock import patch
from . import db, questions, test_app
from .questions import Guide


class QuestionsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    @staticmethod
    def edit(item, **changes):
        return {key: changes.get(key, item[key]) for key in ('revision', 'text', 'context', 'status', 'links', 'note_id')}

    def test_existing_database_migration_preserves_questions(self):
        with sqlite3.connect(':memory:') as c:
            c.row_factory = sqlite3.Row
            c.execute('CREATE TABLE users (id TEXT PRIMARY KEY)')
            c.execute("CREATE TABLE question_memos (id TEXT PRIMARY KEY,owner TEXT,request_id TEXT,text TEXT,context TEXT,status TEXT,links TEXT,note_id TEXT,revision INTEGER,created_at TEXT,updated_at TEXT)")
            c.execute("INSERT INTO question_memos VALUES ('existing','owner','request','기존 질문','','open','[]',NULL,1,'now','now')")
            questions.initialize(c)
            questions.initialize(c)
            row = questions.row_view(c.execute('SELECT * FROM question_memos').fetchone())
            self.assertEqual(row['text'], '기존 질문')
            self.assertIsNone(row['parent_id'])

    def capture(self, text, parent=None):
        response = self.client.post('/api/questions', json={'text': text, 'parent_id': parent, 'request_id': questions.service.uid()})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_follow_up_tree_search_status_and_relations(self):
        root = self.capture('상태 관리')
        child = self.capture('구독 범위', root['id'])
        leaf = self.capture('렌더링 비용', child['id'])
        self.client.put('/api/questions/' + root['id'], json=self.edit(root, status='done'))
        result = self.client.get('/api/questions?q=렌더링').json()
        self.assertEqual([item['id'] for item in result['items']], [root['id'], child['id'], leaf['id']])
        self.assertEqual([item['depth'] for item in result['items']], [0, 1, 2])
        self.assertEqual([item['matches_filter'] for item in result['items']], [False, False, True])
        self.assertEqual((result['total'], result['pages']), (1, 1))
        related = self.client.get('/api/questions/' + child['id'] + '/relations').json()
        self.assertEqual(related['parent']['id'], root['id'])
        self.assertEqual([item['id'] for item in related['children']], [leaf['id']])
        self.assertEqual(self.client.get('/api/questions?status=open').json()['total'], 2)
        self.assertEqual(self.client.get('/api/questions?status=done').json()['total'], 1)
        self.assertEqual(self.client.get('/api/questions?q=없음').json()['items'], [])

    def test_follow_up_owner_validation_and_retry(self):
        root = self.capture('부모')
        body = {'text': '자식', 'parent_id': root['id'], 'request_id': 'follow-up-retry'}
        first = self.client.post('/api/questions', json=body).json()
        self.assertEqual(self.client.post('/api/questions', json=body).json()['id'], first['id'])
        self.assertEqual(self.client.post('/api/questions', json={**body, 'parent_id': None}).status_code, 409)
        self.assertEqual(self.client.post('/api/questions', json={**body, 'text': ' ', 'request_id': 'empty-follow-up'}).status_code, 422)
        self.assertEqual(self.client.post('/api/questions', json={**body, 'parent_id': 'missing', 'request_id': 'invalid-parent'}).status_code, 422)
        self.assertEqual(self.client.post('/api/questions', json={**body, 'parent_id': 'f' * 32, 'request_id': 'missing-parent'}).status_code, 404)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        with self.assertRaises(questions.service.Error) as failure:
            questions.create('other', questions.Create(**body))
        self.assertEqual(failure.exception.status, 404)
        with self.assertRaises(questions.service.Error):
            questions.relations('other', root['id'])
        self.assertEqual(questions.listing('other')['items'], [])

    def test_delete_preserves_and_reconnects_descendants(self):
        root = self.capture('시작')
        child = self.capture('중간', root['id'])
        leaf = self.capture('끝', child['id'])
        self.client.request('DELETE', '/api/questions/' + child['id'], json={})
        self.assertEqual(self.client.get('/api/questions/' + leaf['id']).json()['parent_id'], root['id'])
        self.client.request('DELETE', '/api/questions/' + root['id'], json={})
        self.assertIsNone(self.client.get('/api/questions/' + leaf['id']).json()['parent_id'])
        self.assertEqual(self.client.get('/api/questions').json()['total'], 1)

    def test_pagination_keeps_branch_together(self):
        root = self.capture('가지 시작')
        for index in range(32):
            self.capture(f'꼬리 {index}', root['id'])
        for index in range(30):
            self.capture(f'다른 질문 {index}')
        pages = [self.client.get(f'/api/questions?page={page}').json() for page in (1, 2)]
        self.assertEqual([page['pages'] for page in pages], [2, 2])
        self.assertEqual(pages[0]['total'], 63)
        branch = [page for page in pages if any(item['id'] == root['id'] for item in page['items'])]
        self.assertEqual(len(branch), 1)
        self.assertEqual(sum(item['parent_id'] == root['id'] for item in branch[0]['items']), 32)
        self.assertFalse({item['id'] for item in pages[0]['items']} & {item['id'] for item in pages[1]['items']})

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

    def test_legacy_daily_recommendation_never_calls_ai(self):
        with patch.object(questions.ai, 'generate') as generate:
            result = self.client.get('/api/questions/daily').json()
            self.assertIsNone(result['recommendation'])
            self.assertIn('오늘의 학습', result['reason'])
            self.assertEqual(self.client.post('/api/questions/daily/save', json={'recommendation_id': 'a' * 32}).status_code, 410)
        generate.assert_not_called()

    def test_learning_context_ownership_replay_and_unlink(self):
        resource = self.client.post('/api/resources', json={'request_id': 'context-source', 'revision': 0, 'kind': 'text',
            'name': '연결 자료', 'content': '원자료', 'url': ''}).json()
        target = {'kind': 'resource', 'id': resource['id']}
        body = {'request_id': 'context-question', 'text': '연결 질문', 'origin': '/library/' + resource['id'], 'targets': [target]}
        item = self.client.post('/api/questions', json=body).json()
        self.assertEqual(item['targets'][0]['title'], '연결 자료')
        self.assertEqual(self.client.post('/api/questions', json=body).json()['id'], item['id'])
        self.assertEqual(self.client.post('/api/questions', json={**body, 'targets': []}).status_code, 409)
        self.assertEqual(self.client.get('/api/learning-target', params={'path': body['origin']}).json()['target']['id'], resource['id'])
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        with self.assertRaises(questions.service.Error) as failure:
            questions.create('other', questions.Create(**body))
        self.assertEqual(failure.exception.status, 404)
        updated = self.client.put('/api/questions/' + item['id'], json={**self.edit(item), 'targets': []}).json()
        self.assertEqual(updated['targets'], [])
        self.assertEqual(updated['status'], 'open')

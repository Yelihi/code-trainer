import unittest
import json
from unittest.mock import patch
from . import db, questions, test_app
from .questions import DailyFeedQuestion, Guide


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

    def test_daily_feed_question_changes_next_day_and_only_saved_item_persists(self):
        db.execute("INSERT INTO feed_sources(id,name,url) VALUES ('feed-preview','구독 글','https://example.com/rss')")
        for index in (1, 2):
            db.execute('''INSERT INTO feed_posts(id,guid,url,title,summary,published,collected,feed_id)
                VALUES (?,?,?,?,?,?,?,?)''', (f'post-{index}', f'guid-{index}', f'https://example.com/{index}',
                    f'포스팅 {index}', '요약', f'2026-11-0{index}T00:00:00+00:00', '2026-11-05T00:00:00+00:00', 'feed-preview'))
        article = 'React의 상태가 컴포넌트 트리 밖에 있을 때 구독 범위를 줄일 수 있다. ' * 12
        generated = DailyFeedQuestion(question='React 상태를 컴포넌트 밖에 둘 때 구독 범위와 렌더링 비용은 어떻게 달라질까요?',
                                      evidence='React의 상태가 컴포넌트 트리 밖에 있을 때 구독 범위를 줄일 수 있다.')
        with patch.object(questions, 'today', return_value='2026-11-05'), patch.object(questions.ai, 'available', return_value=True), \
             patch.object(questions.source, 'fetch', return_value=article), patch.object(questions.ai, 'generate', return_value=generated) as generate:
            first = self.client.get('/api/questions/daily').json()['recommendation']
            self.assertEqual(first['source_kind'], 'feed')
            self.assertEqual(first['state'], 'queued')
            first = self.client.get('/api/questions/daily').json()['recommendation']
            self.assertEqual(first['text'], generated.question)
            self.assertEqual(first['evidence'], generated.evidence)
            self.assertNotIn('kind', generate.call_args.kwargs)
            self.assertEqual(self.client.get('/api/questions/daily').json()['recommendation']['id'], first['id'])
            self.assertEqual(self.client.get('/api/questions').json()['total'], 0)
            saved = self.client.post('/api/questions/daily/save', json={'recommendation_id': first['id']}).json()
            self.assertEqual(self.client.post('/api/questions/daily/save', json={'recommendation_id': first['id']}).json()['id'], saved['id'])
            self.assertEqual(self.client.get('/api/questions').json()['total'], 1)
            self.assertEqual(self.client.request('DELETE', '/api/questions/' + saved['id'], json={}).status_code, 200)
            self.assertIsNone(self.client.get('/api/questions/daily').json()['recommendation']['saved_question_id'])
            self.assertNotEqual(self.client.post('/api/questions/daily/save', json={'recommendation_id': first['id']}).json()['id'], saved['id'])
        with patch.object(questions, 'today', return_value='2026-11-06'), patch.object(questions.ai, 'available', return_value=True), \
             patch.object(questions.source, 'fetch', return_value=article), patch.object(questions.ai, 'generate', return_value=generated):
            second = self.client.get('/api/questions/daily').json()['recommendation']
            self.assertNotEqual(second['source_title'], first['source_title'])
            self.assertEqual(self.client.post('/api/questions/daily/save', json={'recommendation_id': first['id']}).status_code, 409)
            self.assertEqual(self.client.get('/api/questions').json()['total'], 1)

    def test_daily_deep_inside_reuses_existing_question_without_ai_call(self):
        db.execute('''INSERT INTO insight_bundles(owner,id,context,data,fingerprint,model,created_at,expires_at)
            VALUES (?,?,?,?,?,?,?,?)''', (self.owner, 'bundle-one', '{}', json.dumps({'suggestions': [
                {'title': '상태 비교', 'question': '상태를 어디에 두어야 할까요?'}]}), 'fingerprint', 'test-model',
                '2026-11-05T00:00:00+00:00', '2999-01-01T00:00:00+00:00'))
        with patch.object(questions, 'today', return_value='2026-11-06'), patch.object(questions.insight_context, 'valid', return_value=True), patch.object(questions.ai, 'generate', side_effect=AssertionError('AI called')):
            selected = self.client.get('/api/questions/daily').json()['recommendation']
            self.assertEqual((selected['source_kind'], selected['text']), ('deep_inside', '상태를 어디에 두어야 할까요?'))
            saved = self.client.post('/api/questions/daily/save', json={'recommendation_id': selected['id']}).json()
            self.assertIn('상태 비교', saved['context'])

    def test_daily_feed_rejects_question_without_article_evidence(self):
        db.execute("INSERT INTO feed_sources(id,name,url) VALUES ('feed-preview','구독 글','https://example.com/rss')")
        db.execute('''INSERT INTO feed_posts(id,guid,url,title,summary,published,collected,feed_id)
            VALUES (?,?,?,?,?,?,?,?)''', ('post-one', 'guid-one', 'https://example.com/post', '제목', '글 링크: https://example.com/original',
                                         '2026-11-05T00:00:00+00:00', '2026-11-05T00:00:00+00:00', 'feed-preview'))
        article = '브라우저는 자바스크립트 작업이 끝나야 다음 화면을 그릴 수 있다. ' * 12
        unsupported = DailyFeedQuestion(question='이 글은 무엇을 알려줄까요?', evidence='해당 본문에 없는 긴 문장입니다. 근거가 아닙니다.')
        with patch.object(questions, 'today', return_value='2026-11-05'), patch.object(questions.ai, 'available', return_value=True), \
             patch.object(questions.source, 'fetch', return_value=article) as fetch, patch.object(questions.ai, 'generate', return_value=unsupported):
            item = self.client.get('/api/questions/daily').json()['recommendation']
            fetch.assert_called_once_with('https://example.com/original')
            self.assertEqual(item['state'], 'queued')
            item = self.client.get('/api/questions/daily').json()['recommendation']
            self.assertEqual(item['state'], 'failed')
            self.assertEqual(item['text'], '')
            self.assertEqual(self.client.post('/api/questions/daily/save', json={'recommendation_id': item['id']}).status_code, 409)

    def test_daily_does_not_guess_from_feed_title_without_ai(self):
        db.execute("INSERT INTO feed_sources(id,name,url) VALUES ('feed-preview','구독 글','https://example.com/rss')")
        db.execute('''INSERT INTO feed_posts(id,guid,url,title,summary,published,collected,feed_id)
            VALUES (?,?,?,?,?,?,?,?)''', ('post-one', 'guid-one', 'https://example.com/post', '매력적인 제목', '글 링크: https://example.com/original',
                                         '2026-11-05T00:00:00+00:00', '2026-11-05T00:00:00+00:00', 'feed-preview'))
        with patch.object(questions, 'today', return_value='2026-11-05'), patch.object(questions.ai, 'available', return_value=False):
            result = self.client.get('/api/questions/daily').json()
            self.assertIsNone(result['recommendation'])
            self.assertIn('AI 연결', result['reason'])

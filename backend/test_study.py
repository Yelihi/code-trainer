import unittest
from unittest.mock import patch
from . import db, service, study, test_app


class StudyTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def test_question_policy_snooze_hide_and_reopen_without_duplicates(self):
        question = self.client.post('/api/questions', json={'text': '오래된 질문', 'request_id': 'study-question'}).json()
        db.execute('UPDATE question_memos SET created_at=? WHERE id=?', ('2026-11-01T00:00:00+00:00', question['id']))
        with patch.object(service, 'now', return_value='2026-11-15T16:00:00+00:00'):
            first = study.today(self.owner)
            self.assertEqual(first['day'], '2026-11-16')
            self.assertEqual(len(first['questions']), 1)
            self.assertEqual(len(study.today(self.owner)['questions']), 1)
            key = first['questions'][0]['key']
            study.choice(self.owner, study.Choice(key=key, action='snooze'))
            self.assertEqual(study.today(self.owner)['questions'], [])
            self.assertEqual(db.one('SELECT status FROM question_memos WHERE id=?', (question['id'],))['status'], 'open')
        with patch.object(service, 'now', return_value='2026-11-19T16:00:00+00:00'):
            # The explicit snooze is independent of the normal resurfacing interval.
            self.assertEqual(len(study.today(self.owner)['questions']), 1)
        with patch.object(service, 'now', return_value='2026-11-27T16:00:00+00:00'):
            self.assertEqual(len(study.today(self.owner)['questions']), 1)
            study.choice(self.owner, study.Choice(key=key, action='hide'))
            self.assertEqual(study.today(self.owner)['questions'], [])
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM question_memos WHERE owner=?', (self.owner,))['n'], 1)
        self.assertEqual(study.today('other')['questions'], [])

    def test_recent_question_excluded_and_policy_bounded(self):
        self.client.post('/api/questions', json={'text': '최근 질문', 'request_id': 'recent-question'})
        self.assertEqual(study.today(self.owner)['questions'], [])
        self.assertEqual(self.client.put('/api/study/policy', json={'question_limit': 1000}).status_code, 422)
        self.assertEqual(self.client.post('/api/study/choice', json={'key': 'question:' + 'f' * 32, 'action': 'hide'}).status_code, 404)
        self.assertEqual(self.client.get('/api/study/today').status_code, 200)

    def prepare_ai(self):
        question = self.client.post('/api/questions', json={'text': '현재 질문', 'request_id': 'ai-question'}).json()
        self.client.post('/api/resources', json={'request_id': 'ai-resource', 'revision': 0, 'kind': 'text', 'name': '자료', 'content': '기술 자료', 'url': ''})
        return question

    def test_ai_explicit_generation_cache_and_resolved_invalidation(self):
        question = self.prepare_ai()
        value = study.snapshot(self.owner)
        result = study.Suggestions(suggestions=[study.Suggestion(title='다시 설명하기', reason='질문과 원자료를 함께 확인해보세요.',
            evidence_ids=[value['items'][0]['id']], action_id=value['items'][0]['id'], uncertain=True)])
        with patch.object(study.ai, 'available', return_value=True), patch.object(study.ai, 'generate', return_value=result) as generate:
            job, fresh = study.begin_recommendations(self.owner)
            self.assertTrue(fresh)
            study.generate_recommendations(job['id'])
            self.assertEqual(len(study.recommendation_status(self.owner)['items']), 1)
            repeated, fresh = study.begin_recommendations(self.owner)
            self.assertFalse(fresh)
            self.assertEqual(repeated['id'], job['id'])
            self.assertEqual(generate.call_count, 1)
            db.execute("UPDATE question_memos SET status='done',revision=revision+1 WHERE id=?", (question['id'],))
            self.assertEqual(study.recommendation_status(self.owner)['items'], [])
        self.assertEqual(db.one('SELECT status FROM question_memos WHERE id=?', (question['id'],))['status'], 'done')
        self.assertEqual(study.recommendation_status('other')['items'], [])

    def test_ai_rejects_fabricated_evidence_and_never_blocks_today(self):
        self.prepare_ai()
        result = study.Suggestions(suggestions=[study.Suggestion(title='잘못된 추천', reason='검사', evidence_ids=['invented'], action_id='invented', uncertain=False)])
        with patch.object(study.ai, 'available', return_value=True), patch.object(study.ai, 'generate', return_value=result):
            job, _ = study.begin_recommendations(self.owner)
            study.generate_recommendations(job['id'])
            self.assertEqual(study.recommendation_status(self.owner)['job']['state'], 'failed')
            self.assertEqual(study.recommendation_status(self.owner)['items'], [])
            with self.assertRaises(service.Error) as failure:
                study.begin_recommendations(self.owner)
            self.assertEqual(failure.exception.status, 429)
        self.assertEqual(self.client.get('/api/study/today').status_code, 200)

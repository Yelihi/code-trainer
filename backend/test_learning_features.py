"""Learning/review state, provenance, metering and monitoring contract checks."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import httpx
from . import ai, db, learning, operations, service, usage
from . import test_app
from .schema import ExerciseDraft, ExecutionInput
from .sample import sample


class LearningFeaturesTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    make_set = test_app.AppTest.make_set

    def submit(self, exercise, request_id, **extra):
        return self.client.post('/api/exercises/' + exercise + '/execute', json={
            'action': 'submit', 'version': 1, 'request_id': request_id, 'answer': '1 2 11 3', **extra})

    def due_review(self):
        problem_set = self.make_set()
        exercise = problem_set['exercises'][0]['id']
        self.submit(exercise, 'first-pass')
        db.execute('UPDATE review_schedule SET due_at=?', ((datetime.now(timezone.utc)-timedelta(days=1)).isoformat(),))
        response = self.client.post(f'/api/exercises/{exercise}/reviews', json={})
        self.assertEqual(response.status_code, 200, response.text)
        return problem_set, exercise, response.json()['id']

    def test_help_is_monotonic_and_frozen_at_submission(self):
        exercise = self.make_set()['exercises'][0]['id']
        self.client.get(f'/api/exercises/{exercise}/hints/1')
        first = self.submit(exercise, 'help-first').json()
        self.assertEqual(first['assistance'], 'hint')
        self.client.get(f'/api/exercises/{exercise}/solution')
        self.client.get(f'/api/exercises/{exercise}/hints/1')
        self.assertEqual(self.submit(exercise, 'help-second').json()['assistance'], 'solution')
        self.assertEqual(self.submit(exercise, 'help-first').json(), first)
        self.assertEqual(learning.evidence(self.owner)[0]['assistance'], 'hint')
        self.assertEqual(len(db.all('SELECT * FROM attempt_learning')), 2)

    def test_legacy_evidence_is_unknown_and_review_due_is_backfilled(self):
        exercise = self.make_set()['exercises'][0]['id']
        self.submit(exercise, 'legacy-pass')
        db.execute('DELETE FROM attempt_learning')
        db.execute('DELETE FROM review_schedule')
        self.assertEqual(learning.evidence(self.owner)[0]['assistance'], 'unknown')
        result = self.client.get('/api/me/reviews').json()
        self.assertEqual(result['items'][0]['assistance'], 'unknown')
        self.assertEqual(result['due_count'], 0)
        self.assertEqual(self.client.post(f'/api/exercises/{exercise}/reviews', json={}).status_code, 409)

    def test_review_is_separate_resumable_owned_and_revision_checked(self):
        problem_set, exercise, review = self.due_review()
        self.client.put(f'/api/exercises/{exercise}/progress', json={'code': 'original code', 'answer': 'old answer', 'revision': 0})
        view = self.client.get(f'/api/reviews/{review}').json()
        self.assertEqual(view['exercises'][0]['progress']['answer'], '')
        self.assertNotEqual(view['exercises'][0]['progress']['code'], 'original code')
        self.assertFalse(view['exercises'][0]['passed'])
        self.assertEqual(self.client.post(f'/api/exercises/{exercise}/reviews', json={}).json()['id'], review)
        draft = {'code': 'review code', 'answer': 'review answer', 'revision': 0}
        self.assertEqual(self.client.put(f'/api/reviews/{review}/progress', json=draft).status_code, 200)
        self.assertEqual(self.client.put(f'/api/reviews/{review}/progress', json=draft).status_code, 409)
        self.assertEqual(self.client.get(f'/api/reviews/{review}').json()['exercises'][0]['progress']['code'], 'review code')
        self.assertEqual(db.one('SELECT code FROM progress WHERE exercise_id=?', (exercise,))['code'], 'original code')
        from . import practice
        with self.assertRaises(service.Error):
            practice.view('other-owner', review)
        other = problem_set['exercises'][1]['id']
        self.assertEqual(self.submit(other, 'cross-review', review_id=review).status_code, 404)
        self.assertEqual(self.client.get(f'/api/exercises/{other}/solution?review_id={review}').status_code, 404)

    def test_review_schedule_idempotency_and_help_reset(self):
        _, exercise, review = self.due_review()
        response = self.submit(exercise, 'review-pass', review_id=review)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['assistance'], 'none')
        scheduled = db.one('SELECT * FROM review_schedule')
        self.assertEqual(scheduled['streak'], 1)
        self.assertGreater((datetime.fromisoformat(scheduled['due_at'])-datetime.now(timezone.utc)).total_seconds(), 2.9*86400)
        self.assertEqual(self.submit(exercise, 'review-pass', review_id=review).json(), response.json())
        self.assertEqual(db.one('SELECT * FROM review_schedule'), scheduled)
        self.assertEqual(self.submit(exercise, 'review-again', review_id=review).status_code, 409)
        db.execute('UPDATE review_schedule SET due_at=?', ('2020-01-01T00:00:00+00:00',))
        new = self.client.post(f'/api/exercises/{exercise}/reviews', json={}).json()['id']
        self.client.get(f'/api/exercises/{exercise}/hints/1?review_id={new}')
        self.assertEqual(self.submit(exercise, 'review-hint', review_id=new).json()['assistance'], 'hint')
        self.assertEqual(db.one('SELECT streak FROM review_schedule')['streak'], 0)

    def test_failed_review_does_not_clear_original_pass_and_can_retry(self):
        problem_set, exercise, review = self.due_review()
        self.assertEqual(self.submit(exercise, 'review-fail', review_id=review, answer='wrong').json()['status'], 'failed')
        self.assertEqual(db.one('SELECT state FROM review_sessions')['state'], 'active')
        self.assertTrue(self.client.get('/api/sets/' + problem_set['id']).json()['exercises'][0]['passed'])
        self.assertEqual(self.client.get('/api/me/reviews').json()['due_count'], 1)
        self.assertEqual(self.submit(exercise, 'retry-passed', review_id=review).json()['status'], 'passed')
        self.client.request('DELETE', '/api/contexts/' + problem_set['context_id'], json={})
        self.assertEqual(db.all('SELECT * FROM review_sessions'), [])
        self.assertEqual(db.all('SELECT * FROM attempt_learning'), [])

    def test_help_from_another_tab_marks_active_review(self):
        _, exercise, review = self.due_review()
        self.client.get(f'/api/exercises/{exercise}/solution')
        self.assertEqual(self.submit(exercise, 'other-tab-pass', review_id=review).json()['assistance'], 'solution')
        self.assertEqual(db.one('SELECT streak FROM review_schedule')['streak'], 0)

    def test_read_run_is_recorded_as_answer_exposure(self):
        exercise = self.make_set()['exercises'][0]['id']
        with patch.object(service.runner, 'run', return_value=[{'status':'ok','stdout':'1 2 11 3','stderr':'','exit_code':0}]):
            self.submit(exercise, 'read-run', action='run')
        self.assertEqual(self.submit(exercise, 'after-run').json()['assistance'], 'solution')

    def test_usage_tracks_provider_tokens_and_missing_usage_without_source(self):
        _, draft = sample()
        read = draft.exercises[0].model_dump()
        reply = {'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps({'data': read, 'error': ''})}}],
                 'usage': {'prompt_tokens': 12, 'completion_tokens': 34}}
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=reply))
        real_client = httpx.Client
        token = usage.scope.set((self.owner, None))
        try:
            with patch.dict(os.environ, {'AI_API_KEY': 'private-test-key', 'AI_MODEL': 'test-model'}), \
                    patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real_client(transport=transport, **kw)):
                ai.generate(ExerciseDraft, 'READ only', {'source': 'private-source'}, kind='READ')
                reply.pop('usage')
                ai.generate(ExerciseDraft, 'READ only', {'validation_failures': ['example']}, kind='READ')
                reply['choices'][0]['message']['content'] = 'not JSON'
                with self.assertRaises(ai.AIError):
                    ai.generate(ExerciseDraft, 'READ only', {}, kind='READ')
        finally:
            usage.scope.reset(token)
        result = self.client.get('/api/me/ai-usage').json()
        self.assertEqual(result['totals'], {'calls': 3, 'repair_calls': 1, 'input_tokens': 12, 'output_tokens': 34, 'unknown_usage_calls': 2, 'failed_calls': 1})
        self.assertNotIn('private-source', json.dumps(db.all('SELECT * FROM ai_usage')))
        self.assertEqual(usage.summary('other-owner')['totals']['calls'], 0)

    def test_wrong_solution_must_fail_by_output_not_runtime_error(self):
        _, draft = sample()
        # All references and FIX starter get expected outcomes; representative wrong code raises.
        def evaluate(language, code, tests, image_id=None):
            wrong = any(code == w.code for e in draft.exercises for w in e.evaluation.wrong_solutions)
            starter = code == draft.exercises[1].starter
            return {'status': 'runtime_error' if wrong else 'failed' if starter else 'passed', 'stdout':'', 'stderr':'', 'tests': []}
        with patch.object(service, 'evaluate', side_effect=evaluate), patch.object(service.runner, 'run', return_value=[{'status':'ok','stdout':draft.exercises[0].evaluation.read_answer}]):
            with self.assertRaises(service.Error) as caught:
                service.validate_set('javascript', draft)
        self.assertTrue(any(f['check'].startswith('wrong:') for f in caught.exception.feedback))

    def test_operations_missing_stale_and_admin_boundary(self):
        self.assertFalse(self.client.get('/api/admin/operations').json()['available'])
        file = Path(self.directory.name) / 'operations.json'
        file.write_text(json.dumps({'collected_at':'2020-01-01T00:00:00+00:00', 'backup_at':None,
            'internal_free_gib':4, 'external_free_gib':100, 'certificates':[{'name':'실행기 연결','days_left':2}],
            'checks':{}, 'secret':'never-return'}))
        result = self.client.get('/api/admin/operations').json()
        self.assertTrue(result['stale'])
        self.assertEqual(len(result['warnings']), 4)
        self.assertNotIn('secret', result)
        file.write_text('{"collected_at": 42}')
        self.assertFalse(self.client.get('/api/admin/operations').json()['available'])
        db.execute('UPDATE users SET admin=0 WHERE id=?', (self.owner,))
        self.assertEqual(self.client.get('/api/admin/operations').status_code, 403)

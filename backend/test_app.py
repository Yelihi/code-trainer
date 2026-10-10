"""Contract tests use stubbed execution; scripts/check-sandbox.py executes real containers."""
import ast
import json
import os
import sqlite3
import tempfile
import unittest
import httpx
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from . import ai, db, service, source, learning
from .api import app
from .sample import sample
from .schema import Case, Credentials, CurriculumDraft, ExerciseCodeRepair, ExerciseDraft, FixStarterRepair, GenerationInput, ReportInput, SetDraft, LearningSummary


class AppTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.environment = patch.dict(os.environ, {'TRAINER_DB': self.directory.name + '/test.sqlite3'})
        self.environment.start()
        service._requests.clear()
        self.cleanup = patch.object(service.runner, 'cleanup')
        self.cleanup.start()
        self.client = TestClient(app)
        self.client.__enter__()
        self.credentials = {'username': '한', 'password': 'test-password-only', 'admin_password': '1202'}
        self.assertEqual(self.client.post('/api/auth', json=self.credentials).status_code, 200)
        self.owner = self.client.get('/api/session').json()['user']['id']

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.cleanup.stop()
        self.environment.stop()
        self.directory.cleanup()

    def make_set(self):
        with patch.object(service.runner, 'available', return_value=True), patch.object(service, 'validate_set', return_value=[{'stub': True}]), patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)) as runtime_command:
            response = self.client.post('/api/generations', json={'request_id': 'sample-001', 'source_kind': 'sample'})
        self.assertTrue(any(call.args[0] == ['tag', 'sha256:test', 'code-trainer-runtime:test'] for call in runtime_command.call_args_list))
        self.assertEqual(response.status_code, 202, response.text)
        generation = self.client.get('/api/generations/' + response.json()['id']).json()
        self.assertEqual(generation['state'], 'ready', generation)
        return self.client.get('/api/sets/' + generation['set_id']).json()

    def test_library_pages_are_owned_stable_and_clamped(self):
        context, _ = sample()
        for i in range(7):
            db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (f'c{i}', self.owner, context.model_dump_json(), None, 'same-time'))
        first = self.client.get('/api/contexts?page=1').json()
        last = self.client.get('/api/contexts?page=99').json()
        self.assertEqual((first['total'], first['pages'], len(first['items'])), (7, 2, 6))
        self.assertEqual((last['page'], len(last['items'])), (2, 1))
        self.assertEqual({c['id'] for c in first['items']} & {c['id'] for c in last['items']}, set())
        self.assertNotIn('lesson', json.dumps(first))
        self.assertEqual(service.contexts('other-owner', 1)['total'], 0)
        for query in ('page=0', 'page=-1', 'page_size=999', 'page=1.5'):
            self.assertEqual(self.client.get('/api/contexts?' + query).status_code, 422)

    def test_admin_code_is_checked_only_during_account_creation(self):
        self.client.post('/api/logout', json={})
        db.execute('DELETE FROM sessions')
        db.execute('DELETE FROM users')
        self.assertEqual(self.client.post('/api/auth', json={**self.credentials, 'admin_password': 'wrong'}).status_code, 403)
        self.assertEqual(db.all('SELECT id FROM users'), [])
        self.assertEqual(self.client.post('/api/auth', json={**self.credentials, 'admin_password': ''}).status_code, 200)
        self.assertEqual(self.client.get('/api/session').json()['user']['admin'], 0)
        for endpoint in ('/api/admin/sources', '/api/admin/sources/private-id', '/api/admin/reports'):
            self.assertEqual(self.client.get(endpoint).status_code, 403)
        self.client.post('/api/logout', json={})
        self.client.post('/api/auth', json=self.credentials)
        self.assertEqual(self.client.get('/api/session').json()['user']['admin'], 0)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/admin/sources').status_code, 401)

    def test_admin_archive_preserves_documents_and_failed_url_analysis(self):
        context, _ = sample()
        original = '# 원본\n\nprivate-source-doc\n```js\nconst x = 1;\n```'
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze', return_value=context):
            response = self.client.post('/api/generations', json={'request_id': 'archive-text', 'source_kind': 'text',
                'source': original, 'source_name': 'study.md', 'framework': 'React'})
        job = service.generation(self.owner, response.json()['id'])
        listing = self.client.get('/api/admin/sources').json()
        self.assertEqual(listing[0]['name'], 'study.md')
        self.assertNotIn('private-source-doc', json.dumps(listing))
        detail = self.client.get('/api/admin/sources/' + job['id']).json()
        self.assertEqual(detail['content'], original)
        public = self.client.get('/api/contexts/' + job['context_id']).json()
        self.assertEqual(public['framework'], 'React')
        self.assertNotIn('private-source-doc', json.dumps(public) + json.dumps(job))
        with patch.object(ai, 'available', return_value=True), patch.object(source, 'fetch', return_value=original), \
                patch.object(ai, 'analyze', side_effect=ai.AIError('분석에 실패했습니다.')):
            failed = self.client.post('/api/generations', json={'request_id': 'archive-url', 'source_kind': 'url', 'source': 'https://example.com/lesson'}).json()
        detail = self.client.get('/api/admin/sources/' + failed['id']).json()
        self.assertEqual((detail['content'], detail['url'], detail['state']), (original, 'https://example.com/lesson', 'failed'))
        self.assertIsNone(detail['context_id'])
        self.assertNotIn('private-source-doc', (Path(self.directory.name) / 'generation.log').read_text())
        self.client.request('DELETE', '/api/contexts/' + job['context_id'], json={})
        self.assertEqual(self.client.get('/api/admin/sources/' + job['id']).status_code, 404)
        problem_set = self.make_set()
        legacy = self.client.get('/api/admin/sources/legacy:' + problem_set['context_id']).json()
        self.assertIsNone(legacy['content'])
        self.assertTrue(legacy['url'])

    def test_learning_map_tracks_passed_evidence_and_drafts_without_duplicate_attempts(self):
        problem_set = self.make_set()
        read, fix = problem_set['exercises'][:2]
        self.assertEqual(service.learning_map(self.owner), [])
        endpoint = '/api/exercises/' + read['id'] + '/execute'
        for request_id, answer in [('learn-pass-1', '1 2 11 3'), ('learn-pass-2', '1 2 11 3'), ('learn-fail-1', 'wrong')]:
            self.client.post(endpoint, json={'action': 'submit', 'request_id': request_id, 'version': 1, 'answer': answer})
        self.client.put('/api/exercises/' + fix['id'] + '/progress', json={'code': 'my draft', 'revision': 0})
        tree = service.learning_map(self.owner)
        self.assertEqual(tree[0]['label'], 'javascript')
        unit = tree[0]['concepts'][0]['units'][0]
        self.assertEqual((unit['completed'], unit['total']), (1, 4))
        self.assertTrue(unit['exercises'][0]['passed'])
        self.assertTrue(unit['exercises'][1]['attempted'])
        self.assertFalse(unit['exercises'][1]['passed'])
        self.assertEqual(unit['exercises'][1]['id'], fix['id'])
        self.assertEqual(service.learning_map('other-owner'), [])
        context = json.loads(service.context_owned(self.owner, problem_set['context_id'])['data'])
        context['framework'] = 'React'
        db.execute('UPDATE contexts SET data=? WHERE id=?', (json.dumps(context), problem_set['context_id']))
        tree = service.learning_map(self.owner)
        self.assertEqual((tree[0]['label'], tree[0]['framework']), ('React', True))
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM attempts')['n'], 3)

    def test_ai_learning_summary_uses_passed_evidence_and_caches_with_safe_retries(self):
        endpoint = '/api/me/learning-summary'
        self.assertEqual(self.client.get(endpoint).json()['state'], 'empty')
        self.assertEqual(self.client.post(endpoint, json={}).status_code, 400)
        problem_set = self.make_set()
        read, fix = problem_set['exercises'][:2]
        execute = '/api/exercises/' + read['id'] + '/execute'
        self.client.post(execute, json={'action': 'submit', 'request_id': 'summary-pass', 'version': 1, 'answer': '1 2 11 3'})
        self.client.put('/api/exercises/' + fix['id'] + '/progress', json={'code': 'unsolved-private-draft', 'revision': 0})
        draft = LearningSummary(concepts=[{'root_key': 'javascript', 'name': '클로저', 'outcomes': [
            {'summary': '함수별 상태가 독립적으로 증가하는 실행 순서를 추적하는 연습을 했습니다.', 'exercise_ids': [read['id'], read['id']]}]}])
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=draft) as generate:
            items = learning.begin(self.owner)
            self.assertIsNone(learning.begin(self.owner))  # Concurrent duplicate request.
            self.assertEqual(learning.status(self.owner)['state'], 'running')
            learning.summarize(self.owner, items)
            result = self.client.get(endpoint).json()
            self.assertEqual(result['state'], 'ready')
            original_record = result['record_id']
            original_date = result['created_at']
            self.assertTrue(original_date)
            self.assertEqual(len(result['records']), 1)
            self.assertEqual(result['concepts'][0]['outcomes'][0]['exercise_ids'], [read['id']])
            sent = generate.call_args.args[2]['passed_exercises']
            self.assertEqual([item['id'] for item in sent], [read['id']])
            self.assertNotIn('unsolved-private-draft', json.dumps(sent))
            self.assertNotIn('hidden_tests', json.dumps(sent))
            self.assertNotIn('submitted_answer', json.dumps(result))
            self.assertEqual(learning.status('other-owner')['exercises'], [])
            # Repeated passes and later failures do not invalidate an existing summary.
            for request_id, answer in [('summary-repeat', '1 2 11 3'), ('summary-failure', 'wrong')]:
                self.client.post(execute, json={'action': 'submit', 'request_id': request_id, 'version': 1, 'answer': answer})
            self.client.post(endpoint, json={})
            self.assertEqual(generate.call_count, 1)
            db.execute("UPDATE learning_summaries SET state='failed' WHERE owner=?", (self.owner,))
            with patch.object(ai, 'generate', side_effect=ai.AIError('테스트 타임아웃')):
                self.client.post(endpoint, json={})
            self.assertEqual(self.client.get(endpoint).json()['state'], 'failed')
            self.client.post(endpoint, json={})
            self.assertEqual(self.client.get(endpoint).json()['state'], 'ready')
            self.assertEqual(self.client.get(endpoint).json()['created_at'], original_date)
            # A draft/unsolved exercise cannot be cited even if AI returns its real ID.
            draft.concepts[0].outcomes[0].exercise_ids = [fix['id']]
            db.execute("UPDATE learning_summaries SET state='failed' WHERE owner=?", (self.owner,))
            self.client.post(endpoint, json={})
            rejected = self.client.get(endpoint).json()
            self.assertEqual(rejected['state'], 'failed')
            self.assertEqual(rejected['concepts'], result['concepts'])  # Last successful record survives failure.
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',
                (service.uid(), self.owner, fix['id'], 'new-pass', '{"code":"passed implementation"}', 'passed', '{}', service.now()))
            self.assertEqual(self.client.get(endpoint).json()['state'], 'stale')
            # A dated snapshot survives deletion, including deletion during generation.
            items = learning.begin(self.owner)
            self.assertEqual(len(items), 2)
            self.client.request('DELETE', '/api/contexts/' + problem_set['context_id'], json={})
            draft.concepts[0].outcomes[0].exercise_ids = [read['id']]
            learning.summarize(self.owner, items)
            self.assertEqual(self.client.get(endpoint).json()['state'], 'empty')
            saved = self.client.get(endpoint).json()
            self.assertEqual(len(saved['records']), 2)
            self.assertTrue(all(e['deleted'] for e in saved['exercises']))
            self.assertEqual(saved['current_passed_count'], 0)
            historical = self.client.get(endpoint + '?record_id=' + original_record).json()
            self.assertEqual(historical['created_at'], original_date)
            self.assertEqual(historical['concepts'], result['concepts'])
            self.assertEqual(len(historical['exercises']), 1)
            with self.assertRaises(service.Error) as forbidden:
                learning.status('other-owner', original_record)
            self.assertEqual(forbidden.exception.status, 404)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get(endpoint).status_code, 401)
        self.assertEqual(self.client.post(endpoint, json={}).status_code, 401)

    def test_legacy_learning_record_keeps_original_date_even_after_source_deletion(self):
        data = {'concepts': [{'root_key': 'javascript', 'name': '클래스', 'outcomes': [
            {'summary': '인스턴스 속성을 초기화하는 방법을 연습했습니다.', 'exercise_ids': ['deleted-exercise']}]}]}
        created_at = '2026-09-16T12:34:56+00:00'
        db.execute('INSERT INTO learning_summaries VALUES (?,?,?,?,?,?)',
                   (self.owner, 'legacy-fingerprint', 'ready', service.dump(data), '', created_at))
        learning.archive_existing()
        learning.archive_existing()
        record = learning.status(self.owner)
        self.assertEqual(record['created_at'], created_at)
        self.assertEqual(len(record['records']), 1)
        self.assertEqual(record['concepts'], data['concepts'])
        self.assertTrue(record['exercises'][0]['deleted'])
        self.assertNotIn('submitted_code', service.dump(record))

    def test_auth_origin_validation_and_private_data(self):
        for name in ('a', '한', '이름 !', 'x' * 41):
            self.assertEqual(Credentials(username=name, password='password123').username, name)
        for name in ('', '   ', '\t\n'):
            self.assertEqual(self.client.post('/api/auth', json={**self.credentials, 'username': name}).status_code, 422)
        self.assertEqual(self.client.post('/api/auth', json={**self.credentials, 'username': ' 한 '}).status_code, 200)
        self.assertEqual(self.client.post('/api/logout', json={}, headers={'Origin': 'https://attacker.example'}).status_code, 403)
        self.assertEqual(self.client.get('/api/session', headers={'host': 'attacker.example'}).status_code, 403)
        response = self.client.post('/api/generations', json={'source': 'private-source-do-not-echo'})
        self.assertEqual(response.status_code, 422)
        self.assertNotIn('private-source', response.text)
        self.assertEqual(self.client.post('/api/auth', content=b'x'*270000, headers={'content-type': 'application/json'}).status_code, 413)
        problem_set = self.make_set()
        serialized = json.dumps(problem_set)
        for secret in ('reference', 'alternative', 'hidden_tests', 'read_answer', 'wrong_solutions', 'learning_notes'):
            self.assertNotIn(secret, serialized)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/sets/' + problem_set['id']).status_code, 401)
        self.assertEqual(self.client.post('/api/auth', json={'username': 'new-user', 'password': 'password123'}).status_code, 401)

    def test_save_conflict_idempotency_and_restored_progress(self):
        problem_set = self.make_set()
        exercise = problem_set['exercises'][0]
        endpoint = '/api/exercises/' + exercise['id']
        snapshot = {'code': exercise['starter'], 'answer': '1 2 11 3', 'revision': 0}
        self.assertEqual(self.client.put(endpoint + '/progress', json=snapshot).json()['revision'], 1)
        self.assertEqual(self.client.put(endpoint + '/progress', json=snapshot).status_code, 409)
        payload = {'action': 'submit', 'request_id': 'submit-001', 'version': 1, 'answer': '1 2 11 3'}
        first = self.client.post(endpoint + '/execute', json=payload)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['status'], 'passed')
        self.assertEqual(self.client.post(endpoint + '/execute', json=payload).json(), first.json())
        self.assertEqual(self.client.post(endpoint + '/execute', json={**payload, 'answer': 'wrong'}).status_code, 409)
        failed = self.client.post(endpoint + '/execute', json={**payload, 'request_id': 'submit-002', 'answer': 'wrong'}).json()
        self.assertEqual(failed['status'], 'failed')
        detail = self.client.get('/api/attempts/' + first.json()['attempt_id']).json()
        self.assertEqual(detail['answer'], '1 2 11 3')
        self.client.post('/api/logout', json={})
        self.client.post('/api/auth', json=self.credentials)
        value = self.client.get('/api/sets/' + problem_set['id']).json()['exercises'][0]
        self.assertTrue(value['passed'])
        self.assertEqual(value['progress']['answer'], snapshot['answer'])
        self.assertEqual(value['attempt_count'], 2)
        with db.connect() as c:
            self.assertEqual(c.execute('PRAGMA foreign_keys').fetchone()[0], 1)
        other = 'other-owner'
        db.execute('INSERT INTO users VALUES (?,?,?,0)', (other, 'other', 'unused'))
        with self.assertRaises(service.Error) as error:
            service.get_set(other, problem_set['id'])
        self.assertEqual(error.exception.status, 404)
        with self.assertRaises(service.Error):
            service.get_attempt(other, first.json()['attempt_id'])

    def test_read_submission_compares_values_without_changing_code_test_comparison(self):
        problem_set = self.make_set()
        exercise = problem_set['exercises'][0]
        endpoint = '/api/exercises/' + exercise['id'] + '/execute'
        for index, (answer, status) in enumerate(((' 1.0, 2\n11\t3 ', 'passed'), ('1 2 3 11', 'failed'))):
            result = self.client.post(endpoint, json={'action': 'submit', 'request_id': f'values-{index:04}',
                'version': 1, 'answer': answer})
            self.assertEqual(result.status_code, 200, result.text)
            self.assertEqual(result.json()['status'], status)
        self.assertNotEqual(service.normalized('true false'), service.normalized('true\nfalse'))

    def test_reports_withdrawal_and_history_survive(self):
        problem_set = self.make_set()
        exercise = problem_set['exercises'][0]
        endpoint = '/api/exercises/' + exercise['id']
        attempt = self.client.post(endpoint + '/execute', json={'action': 'submit', 'request_id': 'submit-001', 'version': 1, 'answer': '1 2 11 3'}).json()
        self.assertEqual(self.client.post(endpoint + '/reports', json={'message': '문제를 확인해주세요', 'attempt_id': 'not-owned'}).status_code, 400)
        report = self.client.post(endpoint + '/reports', json={'message': '문제를 확인해주세요', 'attempt_id': attempt['attempt_id']}).json()
        response = self.client.patch('/api/admin/reports/' + report['id'], json={'status': 'reviewed', 'withdraw': True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post(endpoint + '/execute', json={'action': 'run', 'version': 1, 'request_id': 'run-00001', 'answer': 'prediction'}).status_code, 409)
        history = self.client.get('/api/me').json()
        self.assertEqual(len(history['attempts']), 1)
        self.assertEqual(history['reports'][0]['status'], 'reviewed')

    def test_failed_generation_and_infrastructure_are_not_wrong_answers(self):
        with patch.object(service.runner, 'available', return_value=True), patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), patch.object(service, 'validate_set', side_effect=service.Error('broken')):
            response = self.client.post('/api/generations', json={'source_kind': 'sample', 'request_id': 'failed-001'}).json()
        generation = self.client.get('/api/generations/' + response['id']).json()
        self.assertEqual(generation['state'], 'failed')
        self.assertIsNone(generation['set_id'])
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM sets')['n'], 0)
        problem_set = self.make_set()
        endpoint = '/api/exercises/' + problem_set['exercises'][1]['id'] + '/execute'
        with patch.object(service.runner, 'run', side_effect=service.runner.Unavailable('disconnected')):
            response = self.client.post(endpoint, json={'action': 'submit', 'request_id': 'submit-001', 'version': 1, 'code': 'code'})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM attempts')['n'], 0)

    def test_generation_retries_do_not_duplicate_and_stale_work_fails(self):
        problem_set = self.make_set()
        with patch.object(service.runner, 'available', return_value=True), patch.object(service, 'generate') as generate:
            value = self.client.post('/api/generations', json={'source_kind': 'sample', 'request_id': 'sample-001'}).json()
            generate.assert_not_called()
        self.assertEqual(value['set_id'], problem_set['id'])
        db.execute("UPDATE generations SET state='validating' WHERE id=?", (value['id'],))
        # A previously validated unit remains usable when a later unit is interrupted.
        self.assertEqual(self.client.get('/api/sets/' + problem_set['id']).status_code, 200)
        service.initialize()
        self.assertEqual(service.generation(self.owner, value['id'])['state'], 'failed')

    def test_delete_material_removes_related_records_and_preserves_other_material(self):
        problem_set = self.make_set()
        context_id = problem_set['context_id']
        endpoint = '/api/contexts/' + context_id
        exercise = problem_set['exercises'][0]
        exercise_endpoint = '/api/exercises/' + exercise['id']
        self.client.put(exercise_endpoint + '/progress', json={'answer': 'draft', 'revision': 0})
        attempt = self.client.post(exercise_endpoint + '/execute', json={
            'action': 'submit', 'request_id': 'delete-submit', 'version': 1, 'answer': '1 2 11 3'}).json()
        self.client.post(exercise_endpoint + '/reports', json={'message': '삭제 전 제보 기록', 'attempt_id': attempt['attempt_id']})
        context, draft = sample()
        db.execute('INSERT INTO generation_drafts VALUES (?,?,?,?)', (context_id, 'u2', draft.model_dump_json(), '[]'))
        other = service.uid()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (other, self.owner, context.model_dump_json(), None, service.now()))
        tables = ('sets', 'exercises', 'reports', 'attempts', 'progress', 'generation_drafts', 'generations')
        records = {table: db.all(f'SELECT * FROM {table}') for table in tables}
        self.assertEqual(self.client.request('DELETE', '/api/contexts/' + other, json={}).status_code, 200)
        for table in tables:
            self.assertEqual(db.all(f'SELECT * FROM {table}'), records[table], table)
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (other, self.owner, context.model_dump_json(), None, service.now()))
        with self.assertRaises(service.Error) as denied:
            service.delete_context('another-owner', context_id)
        self.assertEqual(denied.exception.status, 404)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.request('DELETE', endpoint, json={}).status_code, 401)
        self.client.post('/api/auth', json=self.credentials)
        # If the final deletion fails, every preceding deletion must roll back.
        db.execute("CREATE TRIGGER block_delete BEFORE DELETE ON contexts BEGIN SELECT RAISE(ABORT, 'test rollback'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            service.delete_context(self.owner, context_id)
        self.assertIsNotNone(db.one('SELECT id FROM reports'))
        self.assertIsNotNone(db.one('SELECT id FROM attempts'))
        db.execute('DROP TRIGGER block_delete')
        response = self.client.request('DELETE', endpoint, json={})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get(endpoint).status_code, 404)
        self.assertEqual(self.client.get('/api/sets/' + problem_set['id']).status_code, 404)
        self.assertEqual(self.client.get('/api/contexts/' + other).status_code, 200)
        self.assertEqual(self.client.get('/api/me').json(), {'sets': [], 'attempts': [], 'reports': [], 'learning_map': []})
        for table in tables:
            self.assertEqual(db.all(f'SELECT * FROM {table}'), [], table)
        with db.connect() as c:
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.assertEqual(self.client.request('DELETE', endpoint, json={}).status_code, 404)
        self.assertEqual(self.client.request('DELETE', '/api/contexts/' + other, json={}).status_code, 200)

    def test_delete_material_waits_for_generation_and_submission(self):
        problem_set = self.make_set()
        context_id = problem_set['context_id']
        endpoint = '/api/contexts/' + context_id
        for state in ('generating', 'validating'):
            db.execute('UPDATE generations SET state=? WHERE context_id=?', (state, context_id))
            self.assertEqual(self.client.request('DELETE', endpoint, json={}).status_code, 409)
            self.assertIsNotNone(db.one('SELECT id FROM contexts WHERE id=?', (context_id,)))
        db.execute("UPDATE generations SET state='failed' WHERE context_id=?", (context_id,))
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)',
                   (service.uid(), self.owner, problem_set['exercises'][0]['id'], 'running-delete', '{}', 'running', '{}', service.now()))
        response = self.client.request('DELETE', endpoint, json={})
        self.assertEqual(response.status_code, 409)
        self.assertIn('채점 중', response.json()['detail'])
        db.execute("UPDATE attempts SET status='failed'")
        self.assertEqual(self.client.request('DELETE', endpoint, json={}).status_code, 200)

    def test_source_html_preserves_code_and_section_context(self):
        parser = source.TextParser()
        parser.feed('''<nav>unrelated menu</nav><main><article><h1>객체의 세부 동작</h1>
<h2>수신자와 getter</h2><p><code>this</code>는 접근한 객체입니다.</p>
<pre><code class="language-python"><span>def read(obj):</span>\n    if obj:\n        return obj[&quot;x&quot;] &lt; 3\n</code></pre>
<script>ignore()</script><p>원문의 마지막 핵심 사항</p></article></main><footer>footer</footer>''')
        text = parser.text()
        self.assertNotIn('unrelated menu', text)
        self.assertNotIn('ignore()', text)
        self.assertNotIn('footer', text)
        self.assertIn('`this`', text)
        self.assertIn('원문의 마지막 핵심 사항', text)
        document, examples = source.prepare(text)
        self.assertEqual(len(examples), 1)
        self.assertEqual(examples[0]['code'], 'def read(obj):\n    if obj:\n        return obj["x"] < 3\n')
        self.assertEqual(examples[0]['section'], '객체의 세부 동작 / 수신자와 getter')
        self.assertEqual(examples[0]['language'], 'python')
        self.assertIn('[코드 예제 s1]', document)
        self.assertNotIn('def read', document)
        markdown = '# 첫 절\n~~~~javascript\nconst value = "```";\n~~~~\n## 끝 절\n```js\nconst other = 2;\n```\n'
        document, examples = source.prepare(markdown)
        self.assertEqual([e['section'] for e in examples], ['첫 절', '첫 절 / 끝 절'])
        self.assertEqual(examples[0]['code'], 'const value = "```";\n')
        self.assertIn('[코드 예제 s2]', document)
        document, examples = source.prepare('# 들여쓴 코드\n\n    def run():\n        return 1\n\n설명')
        self.assertEqual(examples[0]['code'], 'def run():\n    return 1\n\n')
        self.assertIn('설명', document)

    def test_source_examples_are_attached_exactly_and_reach_generation_after_reload(self):
        context, draft = sample()
        unit = context.units[0]
        unit.source_example_ids = ['s2', 'unknown', 's2']
        context.learning_notes = 'getter의 수신자와 프로토타입 속성 가림을 구별한다.'
        material = '# 기본\n```js\nconst basic = {};\n```\n## 속성 가림\n```js\nconst base = { x: 1 };\nconst child = Object.create(base);\nchild.x = 2;\n```\n'
        with patch.object(ai, 'generate', return_value=context) as generate:
            plan = ai.analyze(material, 'javascript', 'advanced')
            payload = generate.call_args.args[2]
            self.assertEqual(len(payload['source_examples']), 2)
            self.assertNotIn('const child', payload['source'])
        self.assertEqual(plan.units[0].source_example_ids, ['s2'])
        self.assertEqual(plan.units[0].source_examples[0].code, payload['source_examples'][1]['code'])
        reloaded = CurriculumDraft.model_validate_json(plan.model_dump_json())
        with patch.object(ai, 'generate', side_effect=draft.exercises) as generate:
            ai.create_set(reloaded, reloaded.units[0])
        for call in generate.call_args_list:
            data = call.args[2]
            self.assertEqual(data['target_unit']['source_examples'], [payload['source_examples'][1]])
            self.assertEqual(data['target_unit']['lesson'][0], unit.lesson[0].model_dump())
            self.assertEqual(data['document_coverage'], context.learning_notes)
        legacy = context.model_dump()
        for u in legacy['units']:
            u.pop('source_example_ids')
            u.pop('source_examples')
        self.assertEqual(CurriculumDraft.model_validate(legacy).units[0].source_examples, [])

    def test_advanced_schema_allows_multiple_requirements_and_test_cases(self):
        for kind in ('FIX', 'MODIFY', 'BUILD'):
            schema = ai.response_schema(ExerciseDraft, kind, 'advanced')
            properties = schema['properties']['data']['anyOf'][0]['properties']
            self.assertEqual(properties['requirements']['maxItems'], 4)
            self.assertEqual(properties['public_tests']['maxItems'], 4)
            self.assertEqual(schema['$defs']['Evaluation']['properties']['hidden_tests']['maxItems'], 4)
            self.assertNotIn('enum', schema['$defs']['Requirement']['properties']['id'])
        curriculum = ai.response_schema(CurriculumDraft)
        self.assertIn('source_example_ids', curriculum['$defs']['LearningUnit']['properties'])
        self.assertNotIn('source_examples', curriculum['$defs']['LearningUnit']['properties'])

    def test_source_addresses_and_schema_and_layer_direction(self):
        for address in ('127.0.0.1', '10.0.0.1', '169.254.169.254', '::1', '::ffff:127.0.0.1'):
            with self.assertRaises(source.SourceError):
                source.public_address(address, 80)
        _, draft = sample()
        invalid = draft.model_dump()
        invalid['exercises'][1]['evaluation']['hidden_tests'] = []
        with self.assertRaises(ValueError):
            SetDraft.model_validate(invalid)
        invalid = draft.model_dump()
        invalid['exercises'][0]['kind'] = 'BUILD'
        with self.assertRaises(ValueError):
            SetDraft.model_validate(invalid)
        root = Path(__file__).parent
        for module in ('db', 'runner', 'source', 'ai', 'schema'):
            tree = ast.parse((root / f'{module}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    names = [a.name for a in node.names] + [node.module or '']
                    self.assertFalse({'api', 'service', 'fastapi'} & set(names), module)
        self.assertNotIn('fastapi', (root / 'service.py').read_text())

    def test_code_tests_run_custom_calls_but_grade_server_cases(self):
        problem_set = self.make_set()
        exercise = problem_set['exercises'][1]
        self.assertEqual(exercise['test_mode'], 'code')
        endpoint = '/api/exercises/' + exercise['id'] + '/execute'
        payload = {'action': 'run', 'request_id': 'code-test-001', 'version': 1,
                   'code': 'function makeCounter(n) { return () => ++n; }',
                   'test_code': 'console.log(makeCounter(100)());', 'stdin': 'ignored'}
        ok = {'status': 'ok', 'stdout': '101\n', 'stderr': '', 'exit_code': 0}
        with patch.object(service.runner, 'run', return_value=[ok]) as run:
            self.assertEqual(self.client.post(endpoint, json=payload).json()['stdout'], '101\n')
            self.assertEqual(run.call_args.args[1:3], (payload['code'] + '\n' + payload['test_code'], ['']))
            run.reset_mock()
            self.assertEqual(self.client.post(endpoint, json={**payload, 'test_code': ' '}).status_code, 400)
            run.assert_not_called()
        public = exercise['public_tests'][0]
        with patch.object(service.runner, 'run', return_value=[{**ok, 'stdout': public['expected']}]) as run:
            response = self.client.post(endpoint, json={**payload, 'action': 'test'}).json()
            self.assertEqual(response['status'], 'passed')
            self.assertEqual(run.call_args.args[1], payload['code'] + '\n' + public['code'])
            self.assertEqual(response['tests'][0]['code'], public['code'])
        with patch.object(service.runner, 'run', side_effect=[
            [{**ok, 'stdout': public['expected']}],
            [{'status': 'compile_error', 'stdout': '', 'stderr': 'secret hidden test source', 'exit_code': 1}],
        ]):
            response = self.client.post(endpoint, json={**payload, 'action': 'submit'}).json()
        self.assertEqual(response['status'], 'compile_error')
        self.assertEqual(response['stderr'], '')
        self.assertEqual(response['tests'][1], {'id': '비공개 1', 'passed': False})
        self.assertNotIn('secret', self.client.get('/api/attempts/' + response['attempt_id']).text)

    def test_test_modes_are_validated_and_legacy_stdin_still_works(self):
        _, draft = sample()
        for mode, code, stdin in [('code', '', ''), ('code', 'print(1)', 'input'), ('stdio', 'print(1)', '')]:
            invalid = draft.model_dump()
            invalid['exercises'][1]['test_mode'] = mode
            invalid['exercises'][1]['public_tests'][0].update(code=code, stdin=stdin)
            with self.assertRaises(ValueError):
                SetDraft.model_validate(invalid)
        legacy = draft.model_dump()
        for exercise in legacy['exercises']:
            exercise.pop('test_mode')
            for test in exercise['public_tests'] + exercise['evaluation']['hidden_tests']:
                test.pop('code')
        self.assertTrue(all(e.test_mode == 'stdio' for e in SetDraft.model_validate(legacy).exercises))
        tests = [Case(id='a', stdin='42', expected='42', requirements=['r1'])]
        with patch.object(service.runner, 'run', return_value=[{'status': 'ok', 'stdout': '42\n', 'stderr': '', 'exit_code': 0}]) as run:
            self.assertEqual(service.evaluate('python', 'print(input())', tests)['status'], 'passed')
            self.assertEqual(run.call_args.args, ('python', 'print(input())', ['42']))

    def test_completed_curriculum_rejects_random_sets_and_keeps_hints(self):
        first = self.make_set()
        context, draft = sample()
        with patch.object(service.ai, 'available', return_value=True), \
                patch.object(service.ai, 'create_set', return_value=draft) as create_set, \
                patch.object(service.ai, 'analyze') as analyze, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service, 'validate_set', return_value=[{'stub': True}]):
            response = self.client.post('/api/generations', json={
                'request_id': 'second-context-set', 'source_kind': 'context',
                'context_id': first['context_id'], 'language': context.language,
            })
            self.assertEqual(response.status_code, 409, response.text)
            analyze.assert_not_called()
            create_set.assert_not_called()
        contexts = self.client.get('/api/contexts').json()
        self.assertEqual(len(contexts), 1)
        self.assertEqual(len(contexts[0]['sets']), 1)
        self.assertEqual(contexts[0]['source_url'], 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Closures')
        for exercise, expected in zip(first['exercises'], draft.exercises):
            self.assertEqual(exercise['hints_count'], 3)
            endpoint = '/api/exercises/' + exercise['id'] + '/hints/'
            for step in range(1, 4):
                self.assertEqual(self.client.get(endpoint + str(step)).json(), {'hint': expected.hints[step - 1]})
            self.assertEqual(self.client.get(endpoint + '4').status_code, 404)

    def test_curriculum_then_independent_unit_generation_retry_and_report(self):
        context, draft = sample()
        plan = context.model_dump()
        template = plan['units'][0]
        plan['units'] = [{**template, 'id': f'u{i+1}', 'title': concept,
                          'concepts': [concept, '함수 호출'], 'prerequisites': [f'u{i}'] if i else []}
                         for i, concept in enumerate(plan['concepts'])]
        plan['concepts'] = ['클로저와 함수 상태 관리']
        curriculum = CurriculumDraft.model_validate(plan)
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze', return_value=curriculum) as analyze, \
                patch.object(ai, 'create_set') as create_set, patch.object(service.runner, 'available', return_value=False), \
                patch.object(service.runner, 'command') as runtime:
            response = self.client.post('/api/generations', json={'request_id': 'course-first', 'source_kind': 'text', 'source': 'private-source-' * 4})
            self.assertEqual(response.status_code, 202, response.text)
            job = service.generation(self.owner, response.json()['id'])
            self.assertEqual(job['state'], 'ready')
            self.assertIsNone(job['set_id'])
            create_set.assert_not_called()
            runtime.assert_not_called()
            analyze.assert_called_once()
        context_id = job['context_id']
        view = service.get_context(self.owner, context_id)
        self.assertEqual(len(view['units']), 3)
        self.assertEqual(view['sets'], [])
        feedback = [{'kind': 'FIX', 'check': 'reference', 'result': {'status': 'failed', 'private': 'private-expected-output'}}]
        payload = {'request_id': 'unit-two-fail', 'source_kind': 'context', 'context_id': context_id, 'unit_id': 'u2'}
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze') as analyze, \
                patch.object(ai, 'create_set', return_value=draft) as create_set, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service, 'validate_set', side_effect=service.Error('invalid', feedback=feedback)):
            response = self.client.post('/api/generations', json=payload)
            failed = service.generation(self.owner, response.json()['id'])
            self.assertEqual(failed['state'], 'failed')
            self.assertEqual(failed['unit_id'], 'u2')
            self.assertEqual([c.args[1].id for c in create_set.call_args_list], ['u2'] * (1 + service.MAX_GENERATION_REPAIRS))
            analyze.assert_not_called()
        view = service.get_context(self.owner, context_id)
        self.assertEqual(view['generation']['state'], 'ready')
        self.assertEqual(view['unit_generations'][0]['state'], 'failed')
        self.assertNotIn('private-expected-output', json.dumps(view))
        self.assertNotIn('learning_notes', json.dumps(view))
        self.assertNotIn('private-source', json.dumps(view))
        endpoint = '/api/generations/' + failed['id'] + '/reports'
        report = self.client.post(endpoint, json={'message': '이 단원 생성이 계속 실패합니다.'})
        self.assertEqual(report.status_code, 201)
        self.assertEqual(self.client.post(endpoint, json={'message': '다시 제보합니다.'}).json(), report.json())
        self.assertEqual(len(self.client.get('/api/me').json()['reports']), 1)
        review = self.client.get('/api/admin/reports').json()[0]
        self.assertEqual(review['generation']['id'], failed['id'])
        self.assertNotIn('private-expected-output', json.dumps(review))
        self.assertEqual(self.client.patch('/api/admin/reports/' + report.json()['id'], json={'status': 'resolved'}).status_code, 200)
        service.initialize()
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze') as analyze, \
                patch.object(ai, 'create_set', return_value=draft) as create_set, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service, 'validate_set', return_value=[{'passed': True}]):
            for unit in ('u3', 'u2', 'u1'):
                response = self.client.post('/api/generations', json={**payload, 'request_id': 'resume-' + unit, 'unit_id': unit})
                result = service.generation(self.owner, response.json()['id'])
                self.assertEqual(result['state'], 'ready')
                if unit == 'u3':
                    self.assertEqual([s['unit_id'] for s in service.get_context(self.owner, context_id)['sets']], ['u3'])
                    saved = db.all('SELECT * FROM exercises WHERE set_id=?', (result['set_id'],))
                    saved_set = result['set_id']
            self.assertEqual([c.args[1].id for c in create_set.call_args_list], ['u3', 'u2', 'u1'])
            self.assertEqual(create_set.call_args_list[1].kwargs['feedback'], feedback)
            self.assertEqual(create_set.call_args_list[1].kwargs['previous'], draft)
            self.assertIsNone(create_set.call_args_list[0].kwargs['previous'])
            analyze.assert_not_called()
            self.assertEqual(self.client.post('/api/generations', json={**payload, 'request_id': 'duplicate-unit'}).status_code, 409)
        view = service.get_context(self.owner, context_id)
        self.assertEqual(view['total'], 12)
        self.assertEqual(view['units'], plan['units'])
        self.assertTrue(all(g['state'] == 'ready' for g in view['unit_generations']))
        self.assertEqual(db.all('SELECT * FROM exercises WHERE set_id=?', (saved_set,)), saved)
        self.assertEqual(db.all('SELECT * FROM generation_drafts'), [])
        self.assertEqual(self.client.delete('/api/contexts/' + context_id, headers={'content-type': 'application/json'}).status_code, 200)
        self.assertEqual(db.all('SELECT * FROM generation_reports'), [])
        self.assertEqual(db.all('PRAGMA foreign_key_check'), [])

    def test_unit_request_ownership_idempotency_and_running_job(self):
        context, _ = sample()
        context_id = service.uid()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (context_id, self.owner, context.model_dump_json(), None, service.now()))
        payload = {'request_id': 'unit-idempotent', 'source_kind': 'context', 'context_id': context_id, 'unit_id': context.units[0].id}
        with patch.object(ai, 'available', return_value=True), patch.object(service.runner, 'available', return_value=True), patch.object(service, 'generate') as generate:
            response = self.client.post('/api/generations', json=payload)
            self.assertEqual(response.status_code, 202)
            job = response.json()
            self.assertEqual(self.client.post('/api/generations', json=payload).json(), job)
            generate.assert_called_once()
            self.assertEqual(self.client.post('/api/generations', json={**payload, 'request_id': 'second-request'}).status_code, 429)
            self.assertEqual(self.client.post('/api/generations', json={**payload, 'request_id': 'missing-unit', 'unit_id': 'missing'}).status_code, 404)
            with self.assertRaises(service.Error) as error:
                service.begin_generation('other-owner', GenerationInput(**payload))
            self.assertEqual(error.exception.status, 404)
            with self.assertRaises(service.Error) as error:
                service.report_generation('other-owner', job['id'], ReportInput(message='다른 사용자 제보'))
            self.assertEqual(error.exception.status, 404)
            self.assertEqual(self.client.post('/api/generations/' + job['id'] + '/reports', json={'message': '진행 중인 작업'}).status_code, 400)
            self.assertEqual(self.client.post('/api/generations', json={'request_id': 'invalid-target', 'source_kind': 'sample', 'unit_id': 'missing'}).status_code, 422)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.post('/api/generations/' + job['id'] + '/reports', json={'message': '인증하지 않은 제보'}).status_code, 401)

    def test_legacy_failure_migrates_to_its_last_unit(self):
        context, _ = sample()
        plan = context.model_dump()
        plan['units'] = [{**plan['units'][0], 'id': 'u1'}, {**plan['units'][0], 'id': 'u2'}]
        context_id = service.uid()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (context_id, self.owner, json.dumps(plan), None, service.now()))
        db.execute('''INSERT INTO generations (id,owner,request_id,state,stage,context_id,created_at,events)
                   VALUES (?,?,?,'failed','문제 생성',?,?,?)''',
                   ('old-job', self.owner, 'old-request', context_id, service.now(), json.dumps([{'unit': 1}, {'unit': 2}, {'message': 'failed'}])))
        db.execute('ALTER TABLE generations DROP COLUMN unit_id')
        db.initialize()
        db.initialize()
        view = service.get_context(self.owner, context_id)
        self.assertIsNone(view['generation'])
        self.assertEqual(view['unit_generations'][0]['unit_id'], 'u2')
        self.assertEqual(view['units'], plan['units'])

    def test_generation_automatically_repairs_identical_fix_until_last_allowed_attempt(self):
        context, draft = sample()
        for exercise in draft.exercises:
            exercise.evaluation.alternative = ''
            exercise.evaluation.wrong_solutions = []
        fix = draft.exercises[1]
        buggy_starter = fix.starter
        fix.starter = fix.evaluation.reference
        repairs = []
        context_id = service.uid()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)', (context_id, self.owner, context.model_dump_json(), None, service.now()))

        def generate(model, instruction, data, kind=None):
            job = db.one('SELECT state,stage,error FROM generations ORDER BY created_at DESC LIMIT 1')
            self.assertEqual(job['state'], 'generating')
            self.assertIsNone(job['error'])
            if model is FixStarterRepair:
                repairs.append(data)
                self.assertIn(f'자동 수정 {len(repairs)}/{service.MAX_GENERATION_REPAIRS}', job['stage'])
                self.assertEqual(data['validation_failures'][0]['check'], 'starter')
                self.assertEqual(data['validation_failures'][0]['result']['status'], 'passed')
                return FixStarterRepair(
                    starter=buggy_starter if len(repairs) == service.MAX_GENERATION_REPAIRS else fix.starter,
                    hints=fix.hints)
            self.assertIs(model, ExerciseDraft)
            return next(e for e in draft.exercises if e.kind == kind)

        with patch.object(ai, 'available', return_value=True), \
                patch.object(ai, 'analyze', return_value=context), \
                patch.object(ai, 'generate', side_effect=generate) as generation_call, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service.runner, 'run', side_effect=lambda language, code, inputs, **kwargs:
                             [{'status': 'ok', 'stdout': draft.exercises[0].evaluation.read_answer if code == draft.exercises[0].starter else ''}]), \
                patch.object(service, 'evaluate', side_effect=lambda language, code, tests, image_id=None:
                             {'status': 'failed' if code == buggy_starter else 'passed', 'tests': []}):
            response = self.client.post('/api/generations', json={
                'request_id': 'automatic-fix-loop', 'source_kind': 'context', 'context_id': context_id, 'unit_id': context.units[0].id})
        result = self.client.get('/api/generations/' + response.json()['id']).json()
        self.assertEqual(result['state'], 'ready')
        self.assertIsNone(result['error'])
        self.assertEqual(generation_call.call_count, 4 + service.MAX_GENERATION_REPAIRS)
        self.assertEqual(len(repairs), service.MAX_GENERATION_REPAIRS)
        self.assertEqual(sum(e.get('code') == 'retry' for e in result['events']), service.MAX_GENERATION_REPAIRS)
        self.assertFalse(any(e.get('code') == 'retry_exhausted' for e in result['events']))
        saved = db.all('SELECT kind,data FROM exercises WHERE set_id=?', (result['set_id'],))
        self.assertEqual(len(saved), 4)
        for row in saved:
            expected = next(e.model_dump() for e in draft.exercises if e.kind == row['kind'])
            if row['kind'] == 'FIX':
                expected['starter'] = buggy_starter
            self.assertEqual(json.loads(row['data']), expected)
        self.assertIsNone(db.one('SELECT * FROM generation_drafts WHERE context_id=?', (result['context_id'],)))

    def test_curriculum_rejects_missing_lessons_and_future_prerequisites(self):
        context, _ = sample()
        detailed = context.model_dump()
        detailed['units'][0]['concepts'].append('상태의 수명')
        CurriculumDraft.model_validate(detailed)  # Units can name finer subtopics than overview tags.
        detailed['concepts'] = ['자바스크립트 함수의 상태 관리']
        detailed['units'].append({**detailed['units'][0], 'id': 'u2', 'title': '상태 관리 응용', 'prerequisites': ['u1']})
        self.assertEqual(len(CurriculumDraft.model_validate(detailed).units), 2)
        for change in ('empty', 'future', 'duplicate_id', 'empty_concepts', 'missing_example', 'missing_walkthrough'):
            value = context.model_dump()
            if change == 'empty':
                value['units'] = []
            elif change == 'future':
                value['units'][0]['prerequisites'] = ['u2']
            elif change == 'duplicate_id':
                value['units'].append(value['units'][0].copy())
            elif change == 'empty_concepts':
                value['units'][0]['concepts'] = []
            elif change == 'missing_walkthrough':
                value['units'][0]['lesson'][0].pop('walkthrough')
            else:
                for section in value['units'][0]['lesson']:
                    section['code'] = ''
            with self.assertRaises(ValueError):
                CurriculumDraft.model_validate(value)

    def test_solution_is_on_demand_owned_and_does_not_change_progress(self):
        problem_set = self.make_set()
        _, draft = sample()
        for exercise, expected in zip(problem_set['exercises'], draft.exercises):
            response = self.client.get('/api/exercises/' + exercise['id'] + '/solution')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json(), {'code': expected.evaluation.reference if expected.kind != 'READ' else '',
                                              'answer': expected.evaluation.read_answer if expected.kind == 'READ' else ''})
        for exercise in problem_set['exercises']:
            exercise['assistance'] = 'solution'
        self.assertEqual(self.client.get('/api/sets/' + problem_set['id']).json(), problem_set)
        self.assertEqual(db.all('SELECT * FROM attempts'), [])
        self.assertEqual(db.all('SELECT * FROM progress'), [])
        with self.assertRaises(service.Error) as error:
            service.solution('another-owner', problem_set['exercises'][0]['id'])
        self.assertEqual(error.exception.status, 404)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/exercises/' + problem_set['exercises'][0]['id'] + '/solution').status_code, 401)

    def test_selected_difficulty_is_used_and_persisted(self):
        context, draft = sample()
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze', return_value=context) as analyze, \
                patch.object(ai, 'create_set', return_value=draft) as create_set, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service, 'validate_set', return_value=[{'passed': True}]):
            response = self.client.post('/api/generations', json={'request_id': 'difficulty-advanced', 'source_kind': 'text',
                'source': 'A sufficiently long learning source', 'language': 'javascript', 'difficulty': 'advanced'})
            plan_job = service.generation(self.owner, response.json()['id'])
            create_set.assert_not_called()
            response = self.client.post('/api/generations', json={'request_id': 'difficulty-unit', 'source_kind': 'context',
                'context_id': plan_job['context_id'], 'unit_id': context.units[0].id})
        generation = self.client.get('/api/generations/' + response.json()['id']).json()
        self.assertEqual(generation['state'], 'ready')
        analyze.assert_called_once_with('A sufficiently long learning source', 'javascript', 'advanced')
        self.assertEqual(create_set.call_args.args[0].difficulty, 'advanced')
        self.assertEqual(self.client.get('/api/contexts/' + generation['context_id']).json()['difficulty'], 'advanced')
        self.assertEqual(self.client.get('/api/sets/' + generation['set_id']).json()['difficulty'], 'advanced')
        self.assertEqual(self.client.post('/api/generations', json={'request_id': 'difficulty-invalid', 'source_kind': 'sample', 'difficulty': 'invalid'}).status_code, 422)
        self.assertEqual(self.make_set()['difficulty'], 'beginner')
        for difficulty in ('beginner', 'intermediate', 'advanced'):
            with patch.object(ai, 'generate', return_value=context) as generate:
                plan = ai.analyze('A learning source', 'javascript', difficulty)
                self.assertEqual(plan.difficulty, difficulty)
                self.assertEqual(generate.call_args.args[2]['difficulty_guidance'], ai.DIFFICULTY_GUIDANCE[difficulty])
            with patch.object(ai, 'generate', side_effect=draft.exercises) as generate:
                ai.create_set(plan, plan.units[0])
                self.assertEqual(len(generate.call_args_list), 4)
                for call in generate.call_args_list:
                    self.assertEqual(call.args[2]['difficulty'], difficulty)
                    self.assertEqual(call.args[2]['difficulty_guidance'], ai.DIFFICULTY_GUIDANCE[difficulty])

    def test_checkpoint_without_feedback_is_revalidated_before_publication(self):
        context, draft = sample()
        context = context.model_copy(update={'difficulty': 'advanced'})
        context_id = service.uid()
        db.execute('INSERT INTO contexts VALUES (?,?,?,?,?)',
                   (context_id, self.owner, context.model_dump_json(), None, service.now()))
        db.execute('INSERT INTO generation_drafts VALUES (?,?,?,?)',
                   (context_id, context.units[0].id, draft.model_dump_json(), '[]'))
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'create_set') as create_set, \
                patch.object(service.runner, 'available', return_value=True), \
                patch.object(service.runner, 'command', return_value=SimpleNamespace(stdout='sha256:test', returncode=0)), \
                patch.object(service, 'validate_set', return_value=[{'passed': True}]) as validate:
            response = self.client.post('/api/generations', json={'request_id': 'checkpoint-resume',
                'source_kind': 'context', 'context_id': context_id, 'unit_id': context.units[0].id})
        result = self.client.get('/api/generations/' + response.json()['id']).json()
        self.assertEqual(result['state'], 'ready', result)
        self.assertEqual(self.client.get('/api/sets/' + result['set_id']).json()['difficulty'], 'advanced')
        create_set.assert_not_called()
        validate.assert_called_once_with(context.language, draft, 'sha256:test')
        self.assertEqual(db.all('SELECT * FROM generation_drafts WHERE context_id=?', (context_id,)), [])
        self.assertNotIn('evaluation', json.dumps(result))

    def test_ai_structured_response_and_failure_boundaries(self):
        context, draft = sample()
        reply = {'data': context.model_dump(), 'error': ''}
        finish = 'stop'
        def handle(request):
            payload = json.loads(request.content)
            format = payload['response_format']
            self.assertEqual(format['type'], 'json_schema')
            self.assertTrue(format['json_schema']['strict'])
            def check(node):
                if isinstance(node, dict):
                    self.assertNotIn('default', node)
                    if node.get('type') == 'object':
                        self.assertFalse(node['additionalProperties'])
                        self.assertEqual(set(node['required']), set(node['properties']))
                    for value in node.values(): check(value)
                elif isinstance(node, list):
                    for value in node: check(value)
            check(format['json_schema']['schema'])
            return httpx.Response(200, json={'choices': [{'finish_reason': finish, 'message': {'content': json.dumps(reply)}}]})
        client = httpx.Client
        with patch.dict(os.environ, {'AI_API_KEY': 'test-key', 'AI_MODEL': 'test-model'}), \
                patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
            self.assertEqual(ai.analyze('Synthetic source for a contract test', 'javascript').units, context.units)
            read = draft.exercises[0].model_dump()
            read['evaluation'].pop('reference')
            reply = {'data': read, 'error': ''}
            generated = ai.generate(ExerciseDraft, 'READ only', {}, kind='READ')
            self.assertEqual(generated.evaluation.reference, generated.starter)
            for kind in ('READ', 'FIX', 'MODIFY', 'BUILD'):
                schema = ai.response_schema(ExerciseDraft, kind)
                exercise = schema['properties']['data']['anyOf'][0]['properties']
                self.assertEqual(exercise['kind']['enum'], [kind])
                self.assertEqual(exercise['starter']['minLength'], 1)
                self.assertEqual(exercise['public_tests']['items']['properties']['id']['const'], 'public')
                self.assertNotIn('alternative', schema['$defs']['Evaluation']['properties'])
                if kind == 'READ':
                    self.assertNotIn('wrong_solutions', schema['$defs']['Evaluation']['properties'])
                else:
                    wrong = schema['$defs']['Evaluation']['properties']['wrong_solutions']
                    self.assertEqual((wrong['minItems'], wrong['maxItems']), (1, 1))
                hidden = schema['$defs']['Evaluation']['properties']['hidden_tests']
                self.assertEqual(hidden['maxItems'], 0 if kind == 'READ' else 1)
            reply = {'data': None, 'error': 'private-source-do-not-echo'}
            with self.assertRaises(ai.AIError) as error:
                ai.analyze('not programming', 'javascript')
            self.assertNotIn('private-source', str(error.exception))
            reply = {'data': {**context.model_dump(), 'private-source-do-not-echo': 'test-key'}, 'error': ''}
            reply['data']['units'][0]['lesson'][0].pop('walkthrough')
            with self.assertRaises(ai.InvalidDraft) as error:
                ai.analyze('private-source-do-not-echo', 'javascript')
            issues = error.exception.issues
            self.assertEqual(error.exception.code, 'ai_schema_invalid')
            self.assertTrue(any(i['path'] == 'units.0.lesson.0.walkthrough' and i['type'] == 'missing' for i in issues))
            self.assertNotIn('private-source', json.dumps(issues))
            self.assertNotIn('test-key', json.dumps(issues))
            finish = 'length'
            with self.assertRaises(ai.InvalidDraft):
                ai.analyze('source', 'javascript')

    def test_ai_timeout_budget_and_safe_failure_message(self):
        client = httpx.Client
        def handle(request):
            self.assertEqual(request.extensions['timeout']['read'], 300)
            self.assertEqual(request.extensions['timeout']['connect'], 10)
            if timeout:
                raise timeout('private-provider-details')
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({
                'data': sample()[0].model_dump(), 'error': ''})}}]})
        with patch.dict(os.environ, {'AI_API_KEY': 'test-key', 'AI_MODEL': 'test-model'}), \
                patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
            for timeout, message in ((httpx.ReadTimeout, '300초'), (httpx.ConnectTimeout, '10초')):
                with self.subTest(timeout=timeout), self.assertRaises(ai.AIError) as error:
                    ai.generate(CurriculumDraft, 'test', {})
                self.assertEqual(error.exception.code, 'ai_timeout')
                self.assertIn(message, str(error.exception))
                self.assertNotIn('private-provider-details', str(error.exception))
            timeout = None
            with patch.object(ai.time, 'monotonic', side_effect=[0, 130]):
                self.assertIsInstance(ai._generate(CurriculumDraft, 'test', {}), CurriculumDraft)
            with patch.object(ai.time, 'monotonic', side_effect=[0, 301]), self.assertRaises(ai.AIError) as error:
                ai._generate(CurriculumDraft, 'test', {})
            self.assertEqual(error.exception.code, 'ai_timeout')

    def test_failed_generation_keeps_diagnostics_and_stage_without_private_values(self):
        failure = ai.InvalidDraft('필수 해설 항목이 누락되었습니다.', code='ai_schema_invalid',
                                  issues=[{'path': 'units.0.lesson.0.walkthrough', 'type': 'missing', 'reason': '필수 항목이 누락되었습니다.'}])
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'analyze', side_effect=failure), \
                patch.object(service.runner, 'available', return_value=True):
            response = self.client.post('/api/generations', json={'request_id': 'diagnostics-001', 'source_kind': 'text',
                'source': 'private-source-do-not-echo-long-enough', 'language': 'javascript'})
        self.assertEqual(response.status_code, 202, response.text)
        job_id = response.json()['id']
        result = self.client.get('/api/generations/' + job_id).json()
        self.assertEqual(result['state'], 'failed')
        self.assertNotEqual(result['stage'], '생성 실패')
        self.assertEqual(result['events'][-1]['code'], 'ai_schema_invalid')
        self.assertEqual(result['events'][-1]['issues'], failure.issues)
        self.assertEqual(self.client.get('/api/generations').json()[0]['events'], result['events'])
        log = (Path(self.directory.name) / 'generation.log').read_text()
        self.assertIn(job_id, log)
        self.assertIn('ai_schema_invalid', log)
        self.assertNotIn('private-source', log + json.dumps(result))
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/generations/' + job_id).status_code, 401)

    def test_retry_repairs_only_failed_stages_with_private_execution_feedback(self):
        context, draft = sample()
        feedback = [{'kind': 'FIX', 'check': 'reference', 'result': 'private expected/actual comparison'}]
        original = draft.model_dump()
        exercise = draft.exercises[1]
        patch_data = ExerciseCodeRepair(starter=exercise.starter, reference=exercise.evaluation.reference,
                                       public_tests=exercise.public_tests, hidden_tests=exercise.evaluation.hidden_tests)
        with patch.object(ai, 'generate', return_value=patch_data) as generate:
            repaired = ai.create_set(context, context.units[0], retry=True, previous=draft, feedback=feedback)
            generate.assert_called_once()
            self.assertEqual(generate.call_args.args[0], ExerciseCodeRepair)
            self.assertEqual(generate.call_args.args[2]['validation_failures'], feedback)
            self.assertEqual(generate.call_args.args[2]['exercise'], original['exercises'][1])
        self.assertEqual(repaired.exercises, draft.exercises)
        self.assertEqual(draft.model_dump(), original)
        error = service.Error('문제 실행 검증에 실패했습니다.', feedback=feedback)
        self.assertNotIn('private', str(error))

    def test_fix_starter_repair_preserves_validated_solution_tests_and_other_stages(self):
        context, draft = sample()
        original = draft.model_dump()
        fixed = draft.exercises[1]
        repair = FixStarterRepair(starter=fixed.starter, hints=['공유한 상태가 어디에 있는지 확인하세요.'])
        fixed.starter = fixed.evaluation.reference
        before = draft.model_dump()
        for status in ('passed', 'runtime_error'):
            feedback = [{'kind': 'FIX', 'check': 'starter', 'result': {'status': status}}]
            with self.subTest(status=status), patch.object(ai, 'generate', return_value=repair) as generate:
                repaired = ai.create_set(context, context.units[0], retry=True, previous=draft, feedback=feedback)
                generate.assert_called_once()
                self.assertIs(generate.call_args.args[0], FixStarterRepair)
                self.assertEqual(generate.call_args.args[2]['validation_failures'], feedback)
                expected = original['exercises']
                expected[1]['hints'] = repair.hints
                self.assertEqual([e.model_dump() for e in repaired.exercises], expected)
                self.assertEqual(draft.model_dump(), before)

    def test_generation_removes_only_exact_trailing_test_copies(self):
        context, draft = sample()
        exercise = draft.exercises[2]
        exercise.test_mode = 'code'
        for test in exercise.public_tests + exercise.evaluation.hidden_tests:
            test.stdin = ''
            test.code = 'console.log(example());'
        implementation = "const value = 1;\nfunction example() { return value; }"
        exercise.starter = implementation + '\n' + exercise.public_tests[0].code
        exercise.evaluation.reference = exercise.starter
        original = draft.model_dump()
        with patch.object(ai, 'generate', side_effect=draft.exercises):
            repaired = ai.create_set(context, context.units[0])
        self.assertEqual(repaired.exercises[2].starter, implementation)
        self.assertEqual(repaired.exercises[2].evaluation.reference, implementation)
        self.assertEqual(repaired.exercises[2].public_tests, exercise.public_tests)
        self.assertEqual(draft.model_dump(), original)
        with patch.object(ai, 'generate') as generate:
            preserved = ai.create_set(context, context.units[0], previous=draft,
                feedback=[{'kind': 'READ', 'check': 'prediction', 'result': {'status': 'ok', 'stdout': 'answer'}}])
            generate.assert_not_called()
            self.assertEqual(preserved.exercises[2], exercise)
        exercise.starter = implementation + '\nconsole.log(example() + 1);'
        exercise.evaluation.reference = implementation + '\n' + exercise.public_tests[0].code + '\nconst next = 2;'
        with patch.object(ai, 'generate', side_effect=draft.exercises):
            unchanged = ai.create_set(context, context.units[0])
        self.assertEqual(unchanged.exercises[2], exercise)

    def test_read_answer_uses_execution_feedback_and_is_revalidated_without_ai(self):
        context, draft = sample()
        original = draft.model_dump()
        output = 'true\nfalse\n0\ntrue\nfalse\n'
        feedback = [{'kind': 'READ', 'check': 'prediction', 'result': {'status': 'ok', 'stdout': output}}]
        with patch.object(ai, 'generate') as generate:
            repaired = ai.create_set(context, context.units[0], previous=draft, feedback=feedback)
            generate.assert_not_called()
        expected = draft.model_dump()
        expected['exercises'][0]['evaluation']['read_answer'] = output
        self.assertEqual([e.model_dump() for e in repaired.exercises], expected['exercises'])
        self.assertEqual(draft.model_dump(), original)
        starter = repaired.exercises[1].starter
        wrong = {w.code for e in repaired.exercises for w in e.evaluation.wrong_solutions}
        with patch.object(service.runner, 'run', side_effect=lambda language, code, inputs, **kwargs:
                             [{'status': 'ok', 'stdout': output if code == repaired.exercises[0].starter else ''}]) as run, \
                patch.object(service, 'evaluate', side_effect=lambda language, code, tests, image_id=None:
                             {'status': 'failed' if code == starter or code in wrong else 'passed'}):
            self.assertTrue(all(c['passed'] for c in service.validate_set(context.language, repaired)))
            self.assertEqual(sum(call.args[1] == repaired.exercises[0].starter for call in run.call_args_list), 1)
            run.side_effect = lambda language, code, inputs, **kwargs: [{'status': 'ok', 'stdout': 'different output' if code == repaired.exercises[0].starter else ''}]
            with self.assertRaises(service.Error) as error:
                service.validate_set(context.language, repaired)
            self.assertEqual(error.exception.feedback[0]['kind'], 'READ')
        for result in ({'status': 'runtime_error', 'stdout': ''}, {'status': 'ok', 'stdout': ''},
                       {'status': 'ok', 'stdout': 'x' * 4001}):
            with self.subTest(result=result['status']), patch.object(ai, 'generate', return_value=draft.exercises[0]) as generate:
                ai.create_set(context, context.units[0], previous=draft,
                              feedback=[{'kind': 'READ', 'check': 'prediction', 'result': result}])
                generate.assert_called_once()

    def test_execution_diagnostics_explain_failure_without_answer_output(self):
        context, draft = sample()
        with patch.object(service.runner, 'run', side_effect=lambda language, code, inputs, **kwargs:
                             [{'status': 'ok', 'stdout': draft.exercises[0].evaluation.read_answer if code == draft.exercises[0].starter else ''}]), \
                patch.object(service, 'evaluate', return_value={'status': 'runtime_error', 'stderr': 'ReferenceError: private-answer-output'}):
            with self.assertRaises(service.Error) as error:
                service.validate_set(context.language, draft)
        self.assertIn('private-answer-output', str(error.exception.feedback))
        log = (Path(self.directory.name) / 'generation.log').read_text()
        self.assertIn('실행 중 오류', log)
        self.assertIn('ReferenceError', log)
        self.assertIn('정의되지 않은 변수·함수·클래스를 참조했습니다.', log)
        self.assertIn('code_validation_failed', log)
        self.assertNotIn('private-answer-output', log)

    def test_read_prose_output_is_regenerated_instead_of_becoming_the_answer(self):
        context, draft = sample()
        exercise = draft.exercises[0]
        exercise.starter = 'console.log("--- 시나리오 1 ---"); console.log("참조 변경 (changed)");'
        exercise.evaluation.reference = exercise.starter
        exercise.evaluation.read_answer = '--- 시나리오 1 ---\n참조 변경 (changed)\n'
        wrong = {w.code for e in draft.exercises for w in e.evaluation.wrong_solutions}
        with patch.object(service.runner, 'run', side_effect=lambda language, code, inputs, **kwargs:
                         [{'status': 'ok', 'stdout': exercise.evaluation.read_answer if code == exercise.starter else ''}]), \
                patch.object(service, 'evaluate', side_effect=lambda language, code, tests, image_id=None:
                             {'status': 'failed' if code == draft.exercises[1].starter or code in wrong else 'passed'}):
            with self.assertRaises(service.Error) as error:
                service.validate_set(context.language, draft)
        feedback = error.exception.feedback
        self.assertEqual([f['check'] for f in feedback], ['prediction_format'])
        replacement = sample()[1].exercises[0]
        with patch.object(ai, 'generate', return_value=replacement) as generate:
            repaired = ai.create_set(context, context.units[0], previous=draft, feedback=feedback)
        generate.assert_called_once()
        self.assertIn('Scenario headings, separators and explanations belong ONLY in source comments', generate.call_args.args[1])
        self.assertEqual(repaired.exercises[0], replacement)
        self.assertEqual(repaired.exercises[1:], draft.exercises[1:])

    def test_minimal_generated_set_still_requires_correct_answers_and_a_real_fix(self):
        context, sample_draft = sample()
        value = sample_draft.model_dump()
        for exercise in value['exercises']:
            exercise['evaluation'].pop('alternative')
            exercise['evaluation'].pop('wrong_solutions')
        draft = SetDraft.model_validate(value)
        starter = draft.exercises[1].starter
        def evaluate(language, code, tests, image_id=None):
            return {'status': 'failed' if code == starter else 'passed', 'tests': []}
        with patch.object(service.runner, 'run', side_effect=lambda language, code, inputs, **kwargs:
                             [{'status': 'ok', 'stdout': draft.exercises[0].evaluation.read_answer if code == draft.exercises[0].starter else ''}]), \
                patch.object(service, 'evaluate', side_effect=evaluate) as execution:
            checks = service.validate_set(context.language, draft)
            self.assertEqual(len(checks), 11)
            self.assertTrue(all(check['passed'] for check in checks))
            self.assertEqual(execution.call_count, 6)
            execution.side_effect = None
            execution.return_value = {'status': 'runtime_error', 'stderr': 'private execution detail'}
            with self.assertRaises(service.Error) as error:
                service.validate_set(context.language, draft)
            self.assertIsInstance(error.exception.feedback[0]['result'], dict)
            self.assertEqual(error.exception.feedback[0]['required'], 'pass all tests')
            execution.return_value = {'status': 'passed'}
            with self.assertRaises(service.Error) as error:
                service.validate_set(context.language, draft)
            self.assertEqual([f['check'] for f in error.exception.feedback], ['starter'])

    def test_modify_and_build_starters_reject_test_collisions_and_demo_output(self):
        context, draft = sample()
        wrong = {w.code for e in draft.exercises for w in e.evaluation.wrong_solutions}
        for exercise in draft.exercises[2:]:
            for fault in ('collision', 'demo'):
                with self.subTest(kind=exercise.kind, fault=fault):
                    def evaluate(language, code, tests, image_id=None):
                        if code == exercise.starter and fault == 'collision':
                            return {'status': 'runtime_error', 'stderr': "SyntaxError: Identifier 'plain' has already been declared"}
                        return {'status': 'failed' if code in wrong or code == draft.exercises[1].starter else 'passed'}
                    def run(language, code, inputs, **kwargs):
                        output = draft.exercises[0].evaluation.read_answer if code == draft.exercises[0].starter else 'demo output' if code == exercise.starter and fault == 'demo' else ''
                        return [{'status': 'ok', 'stdout': output}]
                    with patch.object(service, 'evaluate', side_effect=evaluate), patch.object(service.runner, 'run', side_effect=run):
                        with self.assertRaises(service.Error) as caught:
                            service.validate_set(context.language, draft)
                    self.assertEqual([(f['kind'], f['check']) for f in caught.exception.feedback],
                                     [(exercise.kind, 'starter' if fault == 'collision' else 'starter_setup')])


if __name__ == '__main__':
    unittest.main()

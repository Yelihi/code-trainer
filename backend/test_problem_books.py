import unittest
from unittest.mock import patch
from . import db, problem_books, service, test_app
from .problem_books import ProblemInput, BookInput, AttemptInput, AssessmentInput


class ProblemBooksTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def create_problem(self, title='문제'):
        return problem_books.save_problem(self.owner, ProblemInput(title=title, kind='text', language='cpp', prompt='구현하세요', answer='int main() {}'))

    def test_reuse_order_owner_and_versioned_attempt(self):
        first, second = self.create_problem('첫째'), self.create_problem('둘째')
        one = problem_books.save_book(self.owner, BookInput(title='A', language='cpp', problem_ids=[first['id'], second['id']]))
        two = problem_books.save_book(self.owner, BookInput(title='B', problem_ids=[first['id']]))
        self.assertEqual(one['problem_ids'], [first['id'], second['id']])
        self.assertEqual(two['problem_ids'], [first['id']])
        updated = problem_books.save_book(self.owner, BookInput(title='A', language='cpp', problem_ids=[second['id'], first['id']], revision=1), one['id'])
        self.assertEqual(updated['problem_ids'], [second['id'], first['id']])
        with self.assertRaises(service.Error): problem_books.book('someone-else', one['id'])
        self.assertNotIn('answer', problem_books.problem(self.owner, first['id']))
        with self.assertRaises(service.Error): problem_books.solution(self.owner, first['id'])
        attempt = problem_books.attempt(self.owner, first['id'], AttemptInput(answer='mine', problem_revision=1, request_id='request-1'))
        self.assertEqual(problem_books.solution(self.owner, first['id'])['answer'], 'int main() {}')
        self.assertEqual(problem_books.attempt(self.owner, first['id'], AttemptInput(answer='mine', problem_revision=1, request_id='request-1'))['id'], attempt['id'])
        problem_books.assess(self.owner, first['id'], attempt['id'], AssessmentInput(assessment='retry'))
        self.assertEqual(len(problem_books.review_queue(self.owner)['items']), 1)
        edited = problem_books.save_problem(self.owner, ProblemInput(title='수정', kind='code', language='cpp', prompt='새 문제', answer='new', revision=1), first['id'])
        self.assertEqual(edited['revision'], 2)
        self.assertEqual(problem_books.problem(self.owner, first['id'], 1, True)['answer'], 'int main() {}')
        self.assertEqual(problem_books.attempts(self.owner, first['id'])['items'][0]['problem_revision'], 1)
        self.assertEqual(len(problem_books.review_queue(self.owner)['items']), 1)

    def test_api_does_not_leak_answer_before_attempt(self):
        row = self.create_problem()
        response = self.client.get('/api/manual-problems/' + row['id'])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('answer', response.json())
        self.assertEqual(self.client.get('/api/manual-problems/' + row['id'] + '/solution').status_code, 403)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/manual-problems/' + row['id']).status_code, 401)

    def test_catalog_and_snapshot_keep_existing_paths_and_old_answer(self):
        row = self.create_problem()
        book = problem_books.save_book(self.owner, BookInput(title='C++ 연습', language='cpp', problem_ids=[row['id']]))
        catalog = problem_books.catalog(self.owner)['items']
        self.assertTrue(any(item['href'] == '/problem-books/' + book['id'] and item['language'] == 'cpp' for item in catalog))
        self.assertTrue(any(item['source'] == 'foundation' and item['href'] == '/foundations' for item in catalog))
        attempt = problem_books.attempt(self.owner, row['id'], AttemptInput(answer='풀이', problem_revision=1, request_id='snapshot-1'))
        problem_books.save_problem(self.owner, ProblemInput(title='새 제목', kind='code', language='cpp', prompt='새 문제', answer='new', revision=1), row['id'])
        saved = problem_books.attempt_snapshot(self.owner, row['id'], attempt['id'])
        self.assertEqual(saved['problem']['answer'], 'int main() {}')
        self.assertEqual(saved['attempt']['answer'], '풀이')
        with self.assertRaises(service.Error): problem_books.attempt_snapshot('someone-else', row['id'], attempt['id'])

    def test_code_requires_verified_answer_and_records_sandbox_result(self):
        draft = {'title': '합계', 'kind': 'code', 'language': 'python', 'prompt': '두 수의 합을 출력하세요.',
                 'answer': 'a,b=map(int,input().split());print(a+b)', 'cases': [
                     {'stdin': '1 2\n', 'expected': '3\n', 'public': True},
                     {'stdin': '4 5\n', 'expected': '9\n', 'public': False}]}
        created = self.client.post('/api/manual-problems', json=draft).json()
        self.assertFalse(created['verified'])
        self.assertEqual(self.client.post('/api/problem-books', json={'title': '합계', 'problem_ids': [created['id']]}).status_code, 409)
        self.assertEqual(self.client.post(f"/api/manual-problems/{created['id']}/execute", json={
            'action': 'submit', 'code': draft['answer'], 'problem_revision': 1, 'request_id': 'early-run'}).status_code, 409)
        with patch.object(problem_books.runner, 'pin_runtime', return_value='sha256:' + 'a' * 64), \
                patch.object(problem_books.runner, 'run', return_value=[{'status': 'ok', 'stdout': '3\n', 'stderr': '', 'exit_code': 0},
                                                                         {'status': 'ok', 'stdout': '9\n', 'stderr': '', 'exit_code': 0}]) as run:
            checked = self.client.post('/api/manual-problems/verify', json={'id': created['id'], 'problem': {**draft, 'revision': 1}}).json()
        self.assertEqual(checked['result']['status'], 'passed')
        self.assertTrue(checked['problem']['verified'])
        self.assertEqual(run.call_args.kwargs['image_id'], 'sha256:' + 'a' * 64)
        visible = self.client.get('/api/manual-problems/' + created['id']).json()
        self.assertEqual(len(visible['cases']), 1)
        self.assertNotIn('answer', visible)
        self.assertEqual(self.client.post('/api/problem-books', json={'title': '합계', 'problem_ids': [created['id']]}).status_code, 200)
        with patch.object(problem_books.runner, 'run', return_value=[{'status': 'ok', 'stdout': '3\n', 'stderr': '', 'exit_code': 0},
                                                                      {'status': 'ok', 'stdout': '0\n', 'stderr': '', 'exit_code': 0}]):
            response = self.client.post(f"/api/manual-problems/{created['id']}/execute", json={
                'action': 'submit', 'code': draft['answer'], 'problem_revision': 2, 'request_id': 'code-submit'})
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload['result']['status'], 'failed')
        self.assertEqual(payload['attempt']['assessment'], 'retry')
        self.assertNotIn('expected', payload['result']['tests'][1])
        self.assertEqual(len(self.client.get(f"/api/manual-problems/{created['id']}/attempts").json()['items']), 1)
        self.assertEqual(self.client.get(f"/api/manual-problems/{created['id']}/solution").status_code, 200)
        with patch.object(problem_books.runner, 'run', return_value=[{'status': 'ok', 'stdout': '3\n', 'stderr': '', 'exit_code': 0}]) as preview:
            run_result = self.client.post(f"/api/manual-problems/{created['id']}/execute", json={
                'action': 'run', 'code': draft['answer'], 'problem_revision': 2, 'request_id': 'code-preview'}).json()
        self.assertEqual(run_result['result']['status'], 'passed')
        self.assertIsNone(run_result['attempt'])
        self.assertEqual(preview.call_args.args[2], ['1 2\n'])
        self.assertEqual(len(self.client.get(f"/api/manual-problems/{created['id']}/attempts").json()['items']), 1)
        with patch.object(problem_books.runner, 'run', return_value=[{'status': 'ok', 'stdout': '3\n', 'stderr': '', 'exit_code': 0},
                                                                      {'status': 'ok', 'stdout': '9\n', 'stderr': '', 'exit_code': 0}]):
            passed = self.client.post(f"/api/manual-problems/{created['id']}/execute", json={
                'action': 'submit', 'code': draft['answer'], 'problem_revision': 2, 'request_id': 'code-pass'}).json()
        self.assertEqual(passed['result']['status'], 'passed')
        self.assertEqual(passed['attempt']['assessment'], 'understood')
        self.assertEqual(len(self.client.get(f"/api/manual-problems/{created['id']}/attempts").json()['items']), 2)
        self.assertFalse(self.client.put(f"/api/manual-problems/{created['id']}", json={**draft, 'revision': 2}).json()['verified'])

    def test_failed_verification_remains_draft_and_preview_does_not_record(self):
        draft = {'title': '출력', 'kind': 'code', 'language': 'python', 'prompt': '수를 출력하세요.', 'answer': 'print(1)',
                 'cases': [{'stdin': '', 'expected': '2', 'public': True}, {'stdin': '', 'expected': '2', 'public': False}]}
        with patch.object(problem_books.runner, 'pin_runtime', return_value='sha256:' + 'b' * 64), \
                patch.object(problem_books.runner, 'run', return_value=[{'status': 'ok', 'stdout': '1\n', 'stderr': '', 'exit_code': 0}] * 2):
            response = self.client.post('/api/manual-problems/verify', json={'problem': draft})
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertFalse(result['problem']['verified'])
        self.assertEqual(result['result']['status'], 'failed')
        identifier = result['problem']['id']
        self.assertEqual(self.client.get('/api/manual-problems/' + identifier).json()['cases'], [draft['cases'][0]])
        self.assertEqual(self.client.get('/api/manual-problems/' + identifier + '/attempts').json()['items'], [])

    def test_legacy_code_problem_requires_new_cases_before_solving(self):
        row = problem_books.save_problem(self.owner, ProblemInput(title='기존 코드', kind='code', language='cpp', prompt='작성', answer='int main() {}'))
        with db.connect(write=True) as c:
            c.execute('UPDATE manual_problem_versions SET data=json_remove(data, "$.cases", "$.verified", "$.image_id") WHERE problem_id=?', (row['id'],))
        restored = problem_books.problem(self.owner, row['id'])
        self.assertEqual(restored['cases'], [])
        self.assertFalse(restored['verified'])
        self.assertEqual(self.client.post(f"/api/manual-problems/{row['id']}/execute", json={
            'action': 'run', 'code': 'int main() {}', 'problem_revision': 1, 'request_id': 'legacy-run'}).status_code, 409)

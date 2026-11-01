import unittest
from unittest.mock import patch
from . import db, problem_books, service, test_app
from .problem_books import ProblemInput, BookInput, AttemptInput, AssessmentInput


class ProblemBooksTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def create_problem(self, title='문제'):
        return problem_books.save_problem(self.owner, ProblemInput(title=title, kind='code', language='cpp', prompt='구현하세요', answer='int main() {}'))

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

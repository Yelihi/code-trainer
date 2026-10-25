"""Learning records preserve learner text, provenance and concurrent edits."""
import unittest
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from . import ai, db, service, test_app, worksheets
from . import test_worksheets
from .test_worksheets import WORKSHEET


class PracticeRecordsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    interpretation = test_worksheets.WorksheetsTest.interpretation
    begin = test_worksheets.WorksheetsTest.begin

    def worksheet(self):
        interpretation, raw = self.interpretation()
        job, _ = self.begin(interpretation)
        with patch.object(ai, 'generate', side_effect=lambda model, *args: model.model_validate(WORKSHEET)):
            worksheets.generate(job['id'])
        return job, raw

    def test_save_partial_reopen_replay_and_changed_content_only(self):
        job, raw = self.worksheet()
        url = '/api/worksheets/' + job['id'] + '/practice'
        body = dict(request_id='first-save', revision=0, answers={'q1': '내 예시'}, summary='내 요약')
        with patch.object(ai, 'generate') as generate, patch.object(service.runner, 'available') as runner:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertIsNone(response.json()['record'])
            saved = self.client.post(url, json=body)
            self.assertEqual(saved.status_code, 200, saved.text)
            self.assertEqual(saved.json()['revision'], 1)
            self.assertEqual(self.client.post(url, json=body).json(), saved.json())
            same = {**body, 'request_id': 'same-save', 'revision': 1, 'answers': {'q2': '', 'q1': '내 예시'}}
            self.assertEqual(self.client.post(url, json=same).json()['revision'], 1)
            changed = {**same, 'request_id': 'second-save', 'summary': '추가 요약'}
            self.assertEqual(self.client.post(url, json=changed).json()['revision'], 2)
            # A lost response replay after another save returns its original receipt, never overwrites v2.
            self.assertEqual(self.client.post(url, json=body).json(), saved.json())
            detail = self.client.get(url).json()
            self.assertEqual(detail['record']['summary'], '추가 요약')
            self.assertEqual(detail['record']['source_kind'], 'user')
            self.assertEqual(len(detail['versions']), 2)
            self.assertEqual(detail['worksheet']['resource_id'], raw['id'])
            self.assertEqual(self.client.get(url + '/versions/1').json()['summary'], '내 요약')
            generate.assert_not_called()
            runner.assert_not_called()

    def test_conflict_validation_ownership_and_atomicity(self):
        job, _ = self.worksheet()
        url = '/api/worksheets/' + job['id'] + '/practice'
        body = dict(request_id='valid-save', revision=0, answers={'q1': '첫 답변'}, summary='')
        self.assertEqual(self.client.post(url, json=body).status_code, 200)
        for payload, status in [
            ({**body, 'request_id': 'stale-save', 'summary': '다른 탭'}, 409),
            ({**body, 'summary': '요청 ID 오용'}, 409),
            ({**body, 'request_id': 'bad-question', 'revision': 1, 'answers': {'q12': '없음'}}, 422),
            ({**body, 'owner': 'other'}, 422),
            ({**body, 'revision': -1}, 422),
            ({**body, 'answers': {'q1': 'x' * 20001}}, 422),
        ]:
            self.assertEqual(self.client.post(url, json=payload).status_code, status)
        self.assertEqual(self.client.get(url).json()['record']['answers'], {'q1': '첫 답변'})
        from . import practice_records
        from .practice_record_schema import PracticeRecordInput
        for action in [lambda: practice_records.view('other', job['id']), lambda: practice_records.version('other', job['id'], 1), lambda: practice_records.save('other', job['id'], PracticeRecordInput(**body))]:
            with self.assertRaises(service.Error) as denied:
                action()
            self.assertEqual(denied.exception.status, 404)
        db.execute("CREATE TRIGGER reject_practice_request BEFORE INSERT ON practice_record_requests BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            practice_records.save(self.owner, job['id'], PracticeRecordInput(**{**body, 'request_id': 'rollback-save', 'revision': 1, 'summary': 'rollback'}))
        self.assertEqual(len(self.client.get(url).json()['versions']), 1)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get(url).status_code, 401)
        self.assertEqual(self.client.post(url, json=body).status_code, 401)
        self.assertEqual(self.client.get(url + '/versions/1').status_code, 401)

    def test_concurrent_updates_and_separate_worksheets(self):
        from . import practice_records
        from .practice_record_schema import PracticeRecordInput
        job, _ = self.worksheet()
        def save(text):
            try:
                return practice_records.save(self.owner, job['id'], PracticeRecordInput(request_id='request-' + text, revision=0, answers={}, summary=text))['revision']
            except service.Error as error:
                return error.status
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(save, ['one', 'two'])), [1, 409])
        other, _ = self.worksheet()
        self.assertIsNone(practice_records.view(self.owner, other['id'])['record'])
        db.execute("UPDATE worksheets SET state='failed' WHERE id=?", (other['id'],))
        with self.assertRaises(service.Error) as unready:
            practice_records.save(self.owner, other['id'], PracticeRecordInput(request_id='not-ready', revision=0, answers={}, summary='text'))
        self.assertEqual(unready.exception.status, 409)

    def test_same_request_concurrency_and_raw_revision_provenance(self):
        from . import practice_records, resources
        from .practice_record_schema import PracticeRecordInput
        from .resource_schema import ResourceInput
        job, raw = self.worksheet()
        request = PracticeRecordInput(request_id='shared-request', revision=0, answers={'q1': '고정된 출처'}, summary='')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: practice_records.save(self.owner, job['id'], request), range(2)))
        self.assertEqual(results[0], results[1])
        resources.register(self.owner, ResourceInput(request_id=service.uid(), resource_id=raw['id'], revision=1, kind='text', name='새 원문', content='새 본문'))
        detail = practice_records.view(self.owner, job['id'])
        self.assertEqual((detail['worksheet']['revision'], detail['worksheet']['current_revision']), (1, 2))
        self.assertEqual(detail['record']['answers'], {'q1': '고정된 출처'})
        self.assertEqual(len(detail['versions']), 1)

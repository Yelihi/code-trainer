"""Worksheet generation contracts use an isolated DB and controlled provider."""
import json
import os
import sqlite3
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from pydantic import ValidationError
from . import ai, db, interpretations, resources, service, test_app, usage
from .interpretation_schema import InterpretationInput, InterpretationDraft
from .resource_schema import ResourceInput
from .test_interpretations import BODY, DOCUMENT


WORKSHEET = dict(title='관찰을 내 말로 설명하기', questions=[
    dict(id='q1', section_id='s1', prompt='관찰과 가설의 차이를 자신의 예시로 설명해주세요.'),
    dict(id='q2', section_id='s1', prompt='관찰의 맥락을 기록하지 않으면 어떤 문제가 생길까요?'),
])


class WorksheetsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def interpretation(self):
        raw = resources.register(self.owner, ResourceInput(request_id=service.uid(), kind='text', name='관찰', content=BODY))
        with patch.object(ai, 'available', return_value=True):
            job, _ = interpretations.begin(self.owner, InterpretationInput(request_id=service.uid(), resource_id=raw['id'], revision=1))
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(DOCUMENT)):
            interpretations.generate(job['id'])
        return job, raw

    def begin(self, interpretation, request_id=None):
        from . import worksheets
        from .worksheet_schema import WorksheetInput
        with patch.object(ai, 'available', return_value=True):
            return worksheets.begin(self.owner, WorksheetInput(interpretation_id=interpretation['id'], request_id=request_id or service.uid()))

    def test_api_creates_worksheet_once_and_reads_do_not_generate(self):
        interpretation, _ = self.interpretation()
        body = dict(interpretation_id=interpretation['id'], request_id='api-worksheet')
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', side_effect=lambda model, *args: model.model_validate(WORKSHEET)) as generate:
            response = self.client.post('/api/worksheets', json=body)
            self.assertEqual(response.status_code, 202, response.text)
            identifier = response.json()['id']
            detail = self.client.get('/api/worksheets/' + identifier).json()
            self.assertEqual((detail['state'], detail['document']), ('ready', WORKSHEET))
            self.assertEqual(self.client.get('/api/worksheets').json()['total'], 1)
            self.assertEqual(self.client.post('/api/worksheets', json=body).json()['id'], identifier)
            self.assertEqual(generate.call_count, 1)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/worksheets/' + identifier).status_code, 401)
        self.assertEqual(self.client.post('/api/worksheets', json=body).status_code, 401)

    def test_immutable_interpretation_and_usage_after_raw_changes(self):
        from . import worksheets
        interpretation, raw = self.interpretation()
        job, _ = self.begin(interpretation)
        def generate(model, instruction, data):
            self.assertEqual(data['interpretation'], DOCUMENT)
            self.assertEqual(data['revision'], 1)
            self.assertEqual(usage.scope.get(), (self.owner, job['id']))
            resources.register(self.owner, ResourceInput(request_id=service.uid(), resource_id=raw['id'], revision=1, kind='text', name='관찰 v2', content='바뀐 본문'))
            return model.model_validate(WORKSHEET)
        with patch.object(ai, 'generate', side_effect=generate), patch.object(service.runner, 'available') as runner:
            worksheets.generate(job['id'])
            runner.assert_not_called()
        detail = worksheets.view(self.owner, job['id'])
        self.assertEqual((detail['interpretation_id'], detail['revision'], detail['current_revision']), (interpretation['id'], 1, 2))
        self.assertIsNone(usage.scope.get())
        self.assertEqual(interpretations.view(self.owner, interpretation['id'])['document'], DOCUMENT)

    def test_concurrent_requests_share_pending_job_and_replay_after_completion(self):
        from . import worksheets
        from .worksheet_schema import WorksheetInput
        interpretation, _ = self.interpretation()
        with patch.object(ai, 'available', return_value=True), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda key: worksheets.begin(self.owner, WorksheetInput(request_id=key, interpretation_id=interpretation['id'])), ['request-one', 'request-two']))
        self.assertEqual(sum(fresh for _, fresh in results), 1)
        self.assertEqual(results[0][0]['id'], results[1][0]['id'])
        identifier = results[0][0]['id']
        with patch.object(ai, 'generate', side_effect=lambda model, *args: model.model_validate(WORKSHEET)) as generate:
            worksheets.generate(identifier)
            worksheets.generate(identifier)
            self.assertEqual(generate.call_count, 1)
        for key in ['request-one', 'request-two']:
            with patch.object(ai, 'available', return_value=False):
                replay, fresh = worksheets.begin(self.owner, WorksheetInput(request_id=key, interpretation_id=interpretation['id']))
            self.assertEqual(replay['id'], identifier)
            self.assertFalse(fresh)
        another, _ = self.interpretation()
        with self.assertRaises(service.Error) as conflict:
            self.begin(another, 'request-one')
        self.assertEqual(conflict.exception.status, 409)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM worksheets')['n'], 1)

    def test_restart_and_failure_retain_records_and_retry_same_interpretation(self):
        from . import worksheets
        interpretation, _ = self.interpretation()
        job, _ = self.begin(interpretation)
        def late(model, *args):
            service.initialize()
            return model.model_validate(WORKSHEET)
        with patch.object(ai, 'generate', side_effect=late):
            worksheets.generate(job['id'])
        old = worksheets.view(self.owner, job['id'])
        self.assertEqual(old['state'], 'interrupted')
        self.assertIsNone(old['document'])
        retry, fresh = self.begin(interpretation)
        self.assertTrue(fresh)
        self.assertNotEqual(retry['id'], job['id'])
        self.assertEqual(retry['interpretation_id'], job['interpretation_id'])
        with patch.object(ai, 'generate', side_effect=RuntimeError('private-token')):
            worksheets.generate(retry['id'])
        failed = worksheets.view(self.owner, retry['id'])
        self.assertEqual(failed['state'], 'failed')
        self.assertNotIn('private-token', failed['error'])
        self.assertIsNone(usage.scope.get())
        self.assertEqual(worksheets.listing(self.owner, 1, interpretation['id'])['total'], 2)

    def test_schema_and_section_identity_are_enforced(self):
        from . import worksheets
        from .worksheet_schema import WorksheetDraft
        for questions in [[], [WORKSHEET['questions'][0]] * 2, [{**WORKSHEET['questions'][0], 'prompt': ' '}]]:
            with self.assertRaises(ValidationError):
                WorksheetDraft.model_validate({**WORKSHEET, 'questions': questions})
        interpretation, _ = self.interpretation()
        job, _ = self.begin(interpretation)
        bad = {**WORKSHEET, 'questions': [{**WORKSHEET['questions'][0], 'section_id': 's6'}]}
        with patch.object(ai, 'generate', return_value=WorksheetDraft.model_validate(bad)):
            worksheets.generate(job['id'])
        self.assertEqual(worksheets.view(self.owner, job['id'])['state'], 'failed')
        self.assertIsNone(worksheets.view(self.owner, job['id'])['document'])

    def test_owner_readiness_unavailable_and_transaction_rollback(self):
        from . import worksheets
        from .worksheet_schema import WorksheetInput
        interpretation, _ = self.interpretation()
        job, _ = self.begin(interpretation)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        request = WorksheetInput(interpretation_id=interpretation['id'], request_id='other-request')
        for action in [lambda: worksheets.view('other', job['id']), lambda: worksheets.listing('other', 1, interpretation['id']), lambda: worksheets.begin('other', request)]:
            with self.assertRaises(service.Error) as denied:
                action()
            self.assertEqual(denied.exception.status, 404)
        self.assertEqual(worksheets.listing('other', 1)['total'], 0)
        db.execute("UPDATE worksheets SET state='failed'")
        with patch.object(ai, 'available', return_value=False), self.assertRaises(service.Error) as unavailable:
            worksheets.begin(self.owner, request)
        self.assertEqual(unavailable.exception.status, 503)
        db.execute("UPDATE interpretations SET state='failed' WHERE id=?", (interpretation['id'],))
        with self.assertRaises(service.Error) as unready:
            self.begin(interpretation)
        self.assertEqual(unready.exception.status, 409)
        db.execute("UPDATE interpretations SET state='ready' WHERE id=?", (interpretation['id'],))
        db.execute("CREATE TRIGGER reject_worksheet_request BEFORE INSERT ON worksheet_requests BEGIN SELECT RAISE(ABORT,'fixture'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            self.begin(interpretation)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM worksheets')['n'], 1)
        self.assertEqual(self.client.post('/api/worksheets', json={'request_id': 'invalid-input', 'interpretation_id': 'bad'}).status_code, 422)

    def test_provider_transport_uses_general_prompt_and_records_usage(self):
        from . import worksheets
        interpretation, _ = self.interpretation()
        job, _ = self.begin(interpretation)
        client = httpx.Client
        def handle(request):
            body = json.loads(request.content)
            self.assertNotIn('not educational programming content', body['messages'][0]['content'])
            self.assertIn('untrusted', body['messages'][0]['content'])
            self.assertEqual(body['response_format']['json_schema']['name'], 'WorksheetDraft')
            self.assertEqual(json.loads(body['messages'][1]['content'])['interpretation'], DOCUMENT)
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': WORKSHEET, 'error': ''})}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 120, 'completion_tokens': 60}})
        with patch.dict(os.environ, {'AI_API_KEY': 'fixture-only', 'AI_MODEL': 'fixture-model'}), patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
            worksheets.generate(job['id'])
        self.assertEqual(worksheets.view(self.owner, job['id'])['state'], 'ready')
        record = db.one('SELECT * FROM ai_usage WHERE generation_id=?', (job['id'],))
        self.assertEqual((record['owner'], record['state'], record['input_tokens']), (self.owner, 'ok', 120))
        self.assertIsNone(usage.scope.get())

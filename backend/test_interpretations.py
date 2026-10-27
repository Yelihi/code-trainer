"""Versioned general interpretation contracts; no paid AI or sandbox calls."""
import json
import os
import unittest
import httpx
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pydantic import ValidationError
from . import ai, db, interpretations, resources, service, test_app, usage
from .interpretation_schema import InterpretationDraft, InterpretationInput
from .resource_schema import ResourceInput
from .sample import sample
from .schema import CurriculumDraft


BODY = '관찰은 가설을 검토하는 출발점이다. 기록은 관찰의 맥락을 보존한다.'
DOCUMENT = dict(title='관찰과 기록', summary='관찰을 기록하며 가설을 검토합니다.', concepts=['관찰', '기록'],
                sections=[dict(id='s1', title='관찰에서 출발하기', body='관찰과 해석을 구분합니다.',
                               prerequisites=[], source_quotes=['관찰은 가설을 검토하는 출발점이다.'],
                               examples=['오늘의 관찰을 한 문장으로 기록해보세요.'],
                               extensions=['관찰자에 따른 차이도 비교할 수 있습니다.'],
                               questions=['관찰과 가설은 어떻게 다른가요?'])])


class InterpretationsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def raw(self):
        return resources.register(self.owner, ResourceInput(request_id=service.uid(), kind='text', name='관찰 노트', content=BODY))

    def start(self, raw, request_id=None):
        with patch.object(ai, 'available', return_value=True):
            return interpretations.begin(self.owner, InterpretationInput(request_id=request_id or service.uid(), resource_id=raw['id'], revision=raw['revision']))

    def test_general_document_pins_original_version_and_retains_all_results(self):
        raw = self.raw()
        job, fresh = self.start(raw)
        self.assertTrue(fresh)
        def generate(model, instruction, data):
            self.assertEqual(data['content'], BODY)
            resources.register(self.owner, ResourceInput(request_id=service.uid(), resource_id=raw['id'], revision=1, kind='text', name='수정', content='새로운 본문'))
            return model.model_validate(DOCUMENT)
        with patch.object(ai, 'generate', side_effect=generate), patch.object(service.runner, 'available') as runner:
            interpretations.generate(job['id'])
            runner.assert_not_called()
        result = interpretations.view(self.owner, job['id'])
        self.assertEqual((result['state'], result['revision'], result['current_revision']), ('ready', 1, 2))
        self.assertEqual(result['document'], DOCUMENT)
        second, fresh = self.start(raw)
        self.assertNotEqual(second['id'], job['id'])
        self.assertEqual(interpretations.listing(self.owner, 1, raw['id'])['total'], 2)
        self.assertEqual(interpretations.view(self.owner, job['id'])['document'], DOCUMENT)

    def test_identity_replay_conflict_and_concurrent_pending_dedup(self):
        raw = self.raw()
        first, _ = self.start(raw, 'original-request')
        with patch.object(ai, 'available', return_value=False):
            replay, fresh = interpretations.begin(self.owner, InterpretationInput(request_id='original-request', resource_id=raw['id'], revision=1))
        self.assertEqual(replay['id'], first['id'])
        self.assertFalse(fresh)
        with self.assertRaises(service.Error) as conflict:
            self.start({**raw, 'revision': 2}, 'original-request')
        self.assertEqual(conflict.exception.status, 409)
        with patch.object(ai, 'available', return_value=True), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda key: interpretations.begin(self.owner, InterpretationInput(request_id=key, resource_id=raw['id'], revision=raw['revision'])), ['concurrent-one', 'concurrent-two']))
        self.assertTrue(all(not fresh and job['id'] == first['id'] for job, fresh in results))
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM interpretations')['n'], 1)
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(DOCUMENT)):
            interpretations.generate(first['id'])
        replay, fresh = self.start(raw, 'concurrent-one')
        self.assertEqual(replay['id'], first['id'])
        self.assertFalse(fresh)

    def test_quotes_and_prerequisites_are_validated_without_weakening_coding(self):
        job, _ = self.start(self.raw())
        invalid = {**DOCUMENT, 'sections': [{**DOCUMENT['sections'][0], 'source_quotes': ['원문에 없는 주장']}]}
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(invalid)):
            interpretations.generate(job['id'])
        self.assertEqual(interpretations.view(self.owner, job['id'])['state'], 'failed')
        self.assertIsNone(interpretations.view(self.owner, job['id'])['document'])
        with self.assertRaises(ValidationError):
            InterpretationDraft.model_validate({**DOCUMENT, 'sections': [{**DOCUMENT['sections'][0], 'prerequisites': ['s1']}]})
        context, _ = sample()
        old = context.model_dump()
        for section in old['units'][0]['lesson']:
            section.update(code='', walkthrough='')
        with self.assertRaises(ValidationError):
            CurriculumDraft.model_validate(old)

    def test_concurrent_first_requests_reserve_only_one_job_and_worker(self):
        raw = self.raw()
        def begin(key):
            return interpretations.begin(self.owner, InterpretationInput(request_id=key, resource_id=raw['id'], revision=1))
        with patch.object(ai, 'available', return_value=True), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(begin, ['fresh-request-one', 'fresh-request-two']))
        self.assertEqual(sum(fresh for _, fresh in results), 1)
        self.assertEqual(results[0][0]['id'], results[1][0]['id'])
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(DOCUMENT)) as generate:
            interpretations.generate(results[0][0]['id'])
            interpretations.generate(results[0][0]['id'])
        self.assertEqual(generate.call_count, 1)

    def test_unavailable_invalid_input_and_request_mapping_rollback(self):
        raw = self.raw()
        with patch.object(ai, 'available', return_value=False), self.assertRaises(service.Error) as unavailable:
            interpretations.begin(self.owner, InterpretationInput(request_id='no-provider', resource_id=raw['id'], revision=1))
        self.assertEqual(unavailable.exception.status, 503)
        self.assertEqual(db.all('SELECT * FROM interpretations'), [])
        self.assertEqual(self.client.post('/api/interpretations', json={'request_id': 'invalid-input', 'resource_id': raw['id'], 'revision': 0}).status_code, 422)
        db.execute("CREATE TRIGGER reject_mapping BEFORE INSERT ON interpretation_requests BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            self.start(raw)
        self.assertEqual(db.all('SELECT * FROM interpretations'), [])
        self.assertEqual(resources.version(self.owner, raw['id'], 1)['content'], BODY)

    def test_restart_fences_late_worker_and_explicit_retry_keeps_revision(self):
        raw = self.raw()
        job, _ = self.start(raw)
        def late(*args):
            service.initialize()
            return InterpretationDraft.model_validate(DOCUMENT)
        with patch.object(ai, 'generate', side_effect=late):
            interpretations.generate(job['id'])
        interrupted = interpretations.view(self.owner, job['id'])
        self.assertEqual(interrupted['state'], 'interrupted')
        self.assertIsNone(interrupted['document'])
        retry, fresh = self.start(raw)
        self.assertTrue(fresh)
        self.assertNotEqual(retry['id'], job['id'])
        self.assertEqual(retry['revision'], 1)
        with patch.object(ai, 'generate', side_effect=RuntimeError('private secret')):
            interpretations.generate(retry['id'])
        failed = interpretations.view(self.owner, retry['id'])
        self.assertEqual(failed['state'], 'failed')
        self.assertNotIn('private secret', failed['error'])

    def test_owned_api_no_generation_on_reads_or_replay_and_empty_source(self):
        raw = self.raw()
        body = dict(request_id='api-request', resource_id=raw['id'], revision=1)
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(DOCUMENT)) as generate:
            response = self.client.post('/api/interpretations', json=body)
            self.assertEqual(response.status_code, 202, response.text)
            identifier = response.json()['id']
            self.assertEqual(self.client.get('/api/interpretations/' + identifier).json()['state'], 'ready')
            self.assertEqual(self.client.get('/api/interpretations').json()['total'], 1)
            self.assertEqual(self.client.post('/api/interpretations', json=body).json()['id'], identifier)
            self.assertEqual(generate.call_count, 1)
        db.execute("INSERT INTO users VALUES ('other','other','unused',0)")
        for operation in (lambda: interpretations.view('other', identifier), lambda: interpretations.listing('other', 1, raw['id']),
                          lambda: interpretations.begin('other', InterpretationInput(**body))):
            with self.assertRaises(service.Error) as denied:
                operation()
            self.assertEqual(denied.exception.status, 404)
        db.execute('UPDATE resource_versions SET content=NULL WHERE resource_id=?', (raw['id'],))
        with self.assertRaises(service.Error):
            self.start(raw)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/interpretations/' + identifier).status_code, 401)

    def test_note_snapshot_is_used_after_edits(self):
        note = dict(id=service.uid(), revision=0, title='노트', body=BODY, metadata={})
        self.assertEqual(self.client.post('/api/reference-notes', json=note).status_code, 200)
        resource = db.one('SELECT id FROM resources WHERE note_id=?', (note['id'],))
        job, _ = self.start({**resource, 'revision': 1})
        self.client.post('/api/reference-notes', json={**note, 'revision': 1, 'body': '다음 버전'})
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(DOCUMENT)) as generate:
            interpretations.generate(job['id'])
        self.assertEqual(generate.call_args.args[2]['content'], BODY)
        self.assertEqual(interpretations.view(self.owner, job['id'])['current_revision'], 2)

    def test_existing_provider_transport_records_usage_and_general_prompt(self):
        raw = self.raw()
        job, _ = self.start(raw)
        client = httpx.Client
        def handle(request):
            body = json.loads(request.content)
            prompt = body['messages'][0]['content']
            self.assertIn('about any subject', prompt)
            self.assertNotIn('not educational programming content', prompt)
            self.assertEqual(json.loads(body['messages'][1]['content'])['content'], BODY)
            self.assertEqual(body['response_format']['json_schema']['name'], 'InterpretationDraft')
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': DOCUMENT, 'error': ''})}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 200}})
        with patch.dict(os.environ, {'AI_API_KEY': 'fixture-only', 'AI_MODEL': 'fixture-model'}), \
                patch.object(ai.httpx, 'Client', side_effect=lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)):
            interpretations.generate(job['id'])
        self.assertEqual(interpretations.view(self.owner, job['id'])['state'], 'ready')
        record = db.one('SELECT * FROM ai_usage WHERE generation_id=?', (job['id'],))
        self.assertEqual((record['owner'], record['state'], record['input_tokens'], record['output_tokens']), (self.owner, 'ok', 100, 200))
        self.assertIsNone(usage.scope.get())


if __name__ == '__main__':
    unittest.main()

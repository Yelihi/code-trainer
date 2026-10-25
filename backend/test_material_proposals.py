import copy
import json
import os
import httpx
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from . import ai, db, materials, material_proposals, practice_records, resources, service, test_app, test_worksheets, test_practice_records
from .material_schema import MaterialProposalInput
from .practice_record_schema import PracticeRecordInput
from .resource_schema import ResourceInput


class MaterialProposalsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    interpretation = test_worksheets.WorksheetsTest.interpretation
    begin = test_worksheets.WorksheetsTest.begin
    worksheet = test_practice_records.PracticeRecordsTest.worksheet

    def reviewed(self, kind='interpretation'):
        if kind == 'interpretation':
            source, raw = self.interpretation()
        else:
            source, raw = self.worksheet()
            practice_records.save(self.owner, source['id'], PracticeRecordInput(request_id='reviewed-record', revision=0, answers={}, summary='내가 설명한 관찰과 기록의 관계.'))
        return materials.mark(self.owner, kind, source['id'], 1), raw

    def begin_proposal(self, review, request='proposal-request-one'):
        with patch.object(ai, 'available', return_value=True):
            return material_proposals.begin(self.owner, review['id'], MaterialProposalInput(request_id=request))

    def answer(self, material):
        quote = material['body'].split('\n')[0]
        return dict(concepts=[dict(key='a', existing_id='', pref_label='관찰', definition='맥락을 살펴 기록한다.', scope='학습', aliases=[], quote=quote, basis='source')], assertions=[], review=dict(summary='제공된 본문 범위에서 검토했습니다.', issues=[]), matches=[])

    def provider(self, material):
        answer = self.answer(material)
        def generate(model, instruction, payload, **kwargs):
            self.assertEqual(payload['note']['body'], material['body'])
            self.assertEqual(payload['note']['authorship'], material['authorship'])
            value = copy.deepcopy(answer)
            if model.__name__ == 'KnowledgeProposal':
                value.pop('review'); value.pop('matches')
            return model.model_validate(value)
        return generate

    def test_explicit_owned_extraction_reuses_review_and_preserves_authorship(self):
        for kind in ['interpretation', 'practice']:
            review, _ = self.reviewed(kind)
            self.assertEqual(material_proposals.listing(self.owner, review['id']), [])
            job, fresh = self.begin_proposal(review, service.uid())
            self.assertTrue(fresh)
            with patch.object(ai, 'generate', side_effect=self.provider(review)) as generate:
                material_proposals.generate(job['id'])
                material_proposals.generate(job['id'])
                self.assertEqual(generate.call_count, 2)
            result = material_proposals.view(self.owner, job['id'])
            self.assertEqual(result['state'], 'ready')
            self.assertEqual(result['material']['kind'], kind)
            self.assertEqual(result['data']['concepts'][0]['basis'], 'interpretation')
            self.assertEqual(result['data']['concepts'][0]['existing_id'], '')
            with self.assertRaises(service.Error) as denied: material_proposals.view('other', job['id'])
            self.assertEqual(denied.exception.status, 404)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_sources')['n'], 0)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM reference_notes')['n'], 0)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM learning_observations')['n'], 0)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/material-proposals/' + job['id']).status_code, 401)

    def test_concurrent_request_aliases_replay_and_reject_changed_target(self):
        review, _ = self.reviewed()
        with patch.object(ai, 'available', return_value=True), ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda key: material_proposals.begin(self.owner, review['id'], MaterialProposalInput(request_id=key)), ['request-first', 'request-second']))
        self.assertEqual(outcomes[0][0]['id'], outcomes[1][0]['id'])
        self.assertEqual(sum(fresh for _, fresh in outcomes), 1)
        with patch.object(ai, 'generate', side_effect=self.provider(review)):
            material_proposals.generate(outcomes[0][0]['id'])
        with patch.object(ai, 'available', return_value=False):
            self.assertFalse(material_proposals.begin(self.owner, review['id'], MaterialProposalInput(request_id='request-second'))[1])
        other, _ = self.reviewed('practice')
        with self.assertRaises(service.Error) as conflict: self.begin_proposal(other, 'request-first')
        self.assertEqual(conflict.exception.status, 409)
        with self.assertRaises(service.Error): self.begin_proposal({'id': service.uid()}, 'not-reviewed')

    def test_changed_material_during_generation_and_restart_cannot_publish_ready(self):
        review, raw = self.reviewed()
        job, _ = self.begin_proposal(review)
        provider = self.provider(review)
        def changed(model, instruction, payload):
            if model.__name__ == 'ReviewedKnowledgeProposal':
                resources.register(self.owner, ResourceInput(request_id='raw-updated', resource_id=raw['id'], revision=1, kind='text', name='changed', content='Changed body'))
            return provider(model, instruction, payload)
        with patch.object(ai, 'generate', side_effect=changed): material_proposals.generate(job['id'])
        result = material_proposals.view(self.owner, job['id'])
        self.assertEqual(result['state'], 'stale')
        self.assertIsNotNone(result['data'])
        with self.assertRaises(service.Error): self.begin_proposal(review, 'stale-cannot-start')
        queued, _ = self.reviewed('practice')
        stale_job, _ = self.begin_proposal(queued, 'changed-before-start')
        practice_records.save(self.owner, queued['origin_id'], PracticeRecordInput(request_id='edit-before-worker', revision=1, answers={}, summary='updated learner body'))
        with patch.object(ai, 'generate') as provider:
            material_proposals.generate(stale_job['id'])
            provider.assert_not_called()
        self.assertEqual(material_proposals.view(self.owner, stale_job['id'])['state'], 'stale')
        other, _ = self.reviewed('practice')
        new, _ = self.begin_proposal(other, 'restart-request')
        def restarted(model, instruction, payload):
            if model.__name__ == 'ReviewedKnowledgeProposal': service.initialize()
            return self.provider(other)(model, instruction, payload)
        with patch.object(ai, 'generate', side_effect=restarted): material_proposals.generate(new['id'])
        self.assertEqual(material_proposals.view(self.owner, new['id'])['state'], 'interrupted')

    def test_invalid_quotes_or_identity_fail_without_graph_or_automatic_retry(self):
        review, _ = self.reviewed()
        job, _ = self.begin_proposal(review)
        answer = self.answer(review)
        answer['concepts'][0]['quote'] = 'invented quote absent from body'
        def invalid(model, instruction, payload):
            if model.__name__ == 'NoteQuoteRepair': return model.model_validate({'quotes': ['still invented']})
            return model.model_validate({k: v for k, v in answer.items() if k not in ['review','matches']})
        with patch.object(ai, 'generate', side_effect=invalid) as generate:
            material_proposals.generate(job['id']); material_proposals.generate(job['id'])
            self.assertEqual(generate.call_count, 2)
        self.assertEqual(material_proposals.view(self.owner, job['id'])['state'], 'failed')
        again, fresh = self.begin_proposal(review)
        self.assertFalse(fresh); self.assertEqual(again['id'], job['id'])
        retry, _ = self.begin_proposal(review, 'explicit-new-request')
        answer['concepts'][0].update(quote=review['body'].split('\n')[0], existing_id='foreign')
        with patch.object(ai, 'generate', side_effect=lambda model, *args: model.model_validate({k: v for k, v in answer.items() if k not in ['review','matches']})):
            material_proposals.generate(retry['id'])
        self.assertEqual(material_proposals.view(self.owner, retry['id'])['state'], 'failed')
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_concepts')['n'], 0)

    def test_actual_provider_call_records_current_owner_model_and_usage(self):
        review, _ = self.reviewed()
        job, _ = self.begin_proposal(review)
        answer = self.answer(review)
        real = httpx.Client
        def handle(request):
            payload = json.loads(request.content)
            self.assertEqual(payload['model'], 'changed-before-worker')
            self.assertEqual(request.headers['authorization'], 'Bearer fixture-only')
            draft = copy.deepcopy(answer)
            if payload['response_format']['json_schema']['name'] == 'KnowledgeProposal':
                draft.pop('review'); draft.pop('matches')
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': draft, 'error': ''})}}], 'usage': {'prompt_tokens': 100, 'completion_tokens': 50}})
        with patch.dict(os.environ, AI_API_KEY='fixture-only', AI_MODEL='changed-before-worker'), patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real(transport=httpx.MockTransport(handle), **kw)):
            material_proposals.generate(job['id'])
        result = material_proposals.view(self.owner, job['id'])
        self.assertEqual((result['state'], result['model']), ('ready', 'changed-before-worker'))
        calls = db.all('SELECT * FROM ai_usage WHERE generation_id=?', (job['id'],))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(r['owner'] == self.owner and r['output_tokens'] == 50 for r in calls))

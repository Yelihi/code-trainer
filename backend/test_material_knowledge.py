import copy
import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from . import ai, db, materials, material_proposals, material_knowledge, ontology, practice_records, resources, service, test_material_proposals
from .note_schema import RegisterKnowledge
from .practice_record_schema import PracticeRecordInput
from .resource_schema import ResourceInput


class MaterialKnowledgeTest(unittest.TestCase):
    fixture = test_material_proposals.MaterialProposalsTest
    setUp, tearDown = fixture.setUp, fixture.tearDown
    interpretation, begin, worksheet = fixture.interpretation, fixture.begin, fixture.worksheet
    reviewed, answer, provider, begin_proposal = fixture.reviewed, fixture.answer, fixture.provider, fixture.begin_proposal

    def prepared(self, kind='interpretation'):
        review, raw = self.reviewed(kind)
        job, _ = self.begin_proposal(review, service.uid())
        with patch.object(ai, 'generate', side_effect=self.provider(review)): material_proposals.generate(job['id'])
        proposal = material_proposals.view(self.owner, job['id'])
        data = {k: proposal['data'][k] for k in ('concepts','assertions')}
        request = RegisterKnowledge(revision=review['revision'], request_id=service.uid(), proposal_id=job['id'], data=data)
        return review, raw, request

    def test_register_each_authorship_and_replay_without_invented_mastery(self):
        for kind in ['interpretation', 'practice']:
            review, _, request = self.prepared(kind)
            route = '/api/material-reviews/' + review['id'] + '/knowledge'
            response = self.client.post(route, json=request.model_dump())
            self.assertEqual(response.status_code, 200, response.text)
            source = db.one('SELECT * FROM knowledge_sources WHERE id=?', (response.json()['registration']['id'],))
            self.assertEqual((source['kind'], source['origin_id'], source['version']), (kind, review['origin_id'], review['revision']))
            self.assertEqual(json.loads(source['metadata'])['review_id'], review['id'])
            before = db.all('SELECT * FROM learning_observations')
            self.assertEqual(len(before), int(kind == 'practice'))
            self.assertEqual(self.client.post(route, json=request.model_dump()).json()['registration']['id'], source['id'])
            self.assertEqual(db.all('SELECT * FROM learning_observations'), before)
            graph = ontology.extend_graph(self.owner, {'nodes': [], 'edges': []})
            concept = next(n for n in graph['nodes'] if any(s['id'] == source['id'] for s in n['sources']))
            self.assertEqual(concept['sources'][0]['material_review_id'], review['id'])
            self.assertEqual(len(concept['observations']), int(kind == 'practice'))
        self.assertEqual(db.one('SELECT COUNT(*) n FROM review_schedule')['n'], 0)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_concepts')['n'], 2)  # Same name is not an identity choice.

    def test_concurrent_receipt_and_invalid_quote_review_owner_or_identity(self):
        review, _, request = self.prepared('practice')
        invalid = request.model_copy(deep=True); invalid.data.concepts[0].quote = 'invented'
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], invalid)
        foreign = request.model_copy(deep=True); foreign.data.concepts[0].existing_id = 'not-owned'
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], foreign)
        heading = request.model_copy(deep=True); heading.data.concepts[0].quote = '## 내 말로 쓴 요약'
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], heading)
        source_basis = request.model_copy(deep=True); source_basis.data.concepts[0].basis = 'source'
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], source_basis)
        with self.assertRaises(service.Error): material_knowledge.register('other', review['id'], request)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_sources')['n'], 0)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: material_knowledge.register(self.owner, review['id'], request), range(2)))
        self.assertEqual(results[0]['registration']['id'], results[1]['registration']['id'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM learning_observations')['n'], 1)
        changed = request.model_copy(deep=True); changed.data.concepts[0].definition = 'different'
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], changed)
        duplicate = request.model_copy(update={'request_id': service.uid()})
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, review['id'], duplicate)
        other, _, payload = self.prepared()
        row = db.one('SELECT data FROM material_proposals WHERE id=?', (payload.proposal_id,)); data = json.loads(row['data'])
        data['review']['issues'] = [dict(kind='needs_verification', quote=data['concepts'][0]['quote'], explanation='확인 필요', suggestion='근거 비교', replacement='')]
        db.execute('UPDATE material_proposals SET data=? WHERE id=?', (json.dumps(data), payload.proposal_id))
        with self.assertRaises(service.Error): material_knowledge.register(self.owner, other['id'], payload)

    def test_raw_and_learner_edits_invalidate_only_related_evidence(self):
        review, raw, request = self.prepared('practice')
        first = material_knowledge.register(self.owner, review['id'], request)['registration']['id']
        separate, _, payload = self.prepared()
        second = material_knowledge.register(self.owner, separate['id'], payload)['registration']['id']
        practice_records.save(self.owner, review['origin_id'], PracticeRecordInput(request_id='updated-answer', revision=1, answers={}, summary='새로운 설명'))
        self.assertEqual(db.one('SELECT state FROM knowledge_sources WHERE id=?', (first,))['state'], 'stale')
        self.assertEqual(db.one('SELECT state FROM knowledge_sources WHERE id=?', (second,))['state'], 'active')
        resources.register(self.owner, ResourceInput(request_id='new-raw-body', resource_id=separate['resource_id'], revision=1, kind='text', name='changed', content='Changed raw body'))
        self.assertEqual(db.one('SELECT state FROM knowledge_sources WHERE id=?', (second,))['state'], 'stale')
        self.assertEqual(db.one('SELECT COUNT(*) n FROM learning_observations')['n'], 1)
        self.assertEqual(material_knowledge.register(self.owner, review['id'], request)['registration']['id'], first)
        self.assertIn('내가 설명한', db.one('SELECT body FROM knowledge_sources WHERE id=?', (first,))['body'])

    def test_cycle_failure_rolls_back_source_concepts_evidence_and_receipt(self):
        first, _, request = self.prepared()
        a = request.data.concepts[0]
        request.data.concepts.append(a.model_copy(update={'key': 'b', 'pref_label': '기록'}))
        relation = dict(subject='a', kind='PREREQUISITE_OF', object='b', text='관찰을 먼저 검토한다.', scope='학습', quote=a.quote, basis='interpretation', disposition='supports')
        payload = request.model_dump(); payload['data']['assertions'] = [relation]; request = RegisterKnowledge.model_validate(payload)
        result = material_knowledge.register(self.owner, first['id'], request)
        keys = {r['pref_label']: r['id'] for r in db.all('SELECT * FROM knowledge_concepts')}
        second, _, next_request = self.prepared()
        data = copy.deepcopy(payload['data'])
        data['concepts'][0]['existing_id'] = keys['관찰']; data['concepts'][1]['existing_id'] = keys['기록']
        data['assertions'][0].update(subject='b', object='a')
        next_request = RegisterKnowledge.model_validate({**next_request.model_dump(), 'data': data})
        with self.assertRaises(service.Error) as cycle: material_knowledge.register(self.owner, second['id'], next_request)
        self.assertEqual(cycle.exception.status, 422)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_sources')['n'], 1)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_registrations')['n'], 1)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_concepts')['n'], 2)
        self.assertIsNotNone(result['registration'])

    def test_note_archive_marks_derived_evidence_without_deleting_history(self):
        from . import reference_notes, interpretations, test_worksheets
        from .note_schema import ReferenceInput, ReferenceMetadata
        from .interpretation_schema import InterpretationInput, InterpretationDraft
        note = reference_notes.save(self.owner, ReferenceInput(id=service.uid(), revision=0, title='원문 노트', body=test_worksheets.BODY, metadata=ReferenceMetadata()))
        raw_id = db.one('SELECT id FROM resources WHERE note_id=?', (note['id'],))['id']
        with patch.object(ai, 'available', return_value=True): job, _ = interpretations.begin(self.owner, InterpretationInput(request_id='note-graph-source', resource_id=raw_id, revision=1))
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(test_worksheets.DOCUMENT)): interpretations.generate(job['id'])
        review = materials.mark(self.owner, 'interpretation', job['id'], 1)
        proposal, _ = self.begin_proposal(review)
        with patch.object(ai, 'generate', side_effect=self.provider(review)): material_proposals.generate(proposal['id'])
        data = material_proposals.view(self.owner, proposal['id'])['data']
        request = RegisterKnowledge(revision=1, request_id='note-graph-register', proposal_id=proposal['id'], data={k:data[k] for k in ('concepts','assertions')})
        source = material_knowledge.register(self.owner, review['id'], request)['registration']['id']
        reference_notes.archive(self.owner, note['id'], True)
        self.assertEqual(db.one('SELECT state FROM knowledge_sources WHERE id=?', (source,))['state'], 'deleted')
        reference_notes.archive(self.owner, note['id'], False)
        self.assertEqual(db.one('SELECT state FROM knowledge_sources WHERE id=?', (source,))['state'], 'stale')
        self.assertEqual(db.one('SELECT COUNT(*) n FROM knowledge_concepts')['n'], 1)

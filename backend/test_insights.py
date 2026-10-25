import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import httpx
from . import ai, db, service, insights, insight_context, reference_notes, test_reference_notes
from .insight_schema import InsightBundle


class InsightsTest(unittest.TestCase):
    fixture=test_reference_notes.ReferenceNotesTest
    setUp,tearDown=fixture.setUp,fixture.tearDown
    note,graph_data,register=fixture.note,fixture.graph_data,fixture.register

    def graph(self):
        note,payload=self.note();response,_=self.register(note);self.assertEqual(response.status_code,200,response.text)
        return note,payload

    def begin_insight(self,request_id=None):
        with patch.object(ai,'available',return_value=True):return insights.begin(self.owner,request_id or service.uid())

    def answer(self,context):
        a=context['assertions'][0]
        evidence=[e['id'] for e in context['evidence'] if e['assertion_id']==a['id']]
        return InsightBundle(suggestions=[dict(title='인출과 복습의 차이를 관찰하기',connection_kind='known_relation',why='등록한 활용 관계를 구체적인 상황에서 확인합니다.',concept_ids=[a['subject'],a['object']],assertion_ids=[a['id']],evidence_ids=evidence,question='읽기와 인출을 비교하면 무엇이 달라지나요?',reading_guide='인용한 문장의 적용 조건을 다시 확인하세요.',practice_guide='한 개념을 읽은 뒤 자료를 덮고 설명해보세요.',expected_output='내 설명과 다시 확인할 질문을 작성하세요.')])

    def test_insufficient_refuted_or_stale_graph_never_calls_ai(self):
        with patch.object(ai,'generate') as generate:
            with self.assertRaises(service.Error):self.begin_insight()
            note,_=self.graph()
            self.assertTrue(insight_context.build(self.owner)['assertions'])
            db.execute("UPDATE knowledge_evidence SET disposition='refutes' WHERE assertion_id IS NOT NULL")
            self.assertEqual(insight_context.build(self.owner)['assertions'],[])
            with self.assertRaises(service.Error):self.begin_insight()
            db.execute("UPDATE knowledge_evidence SET disposition='supports'")
            reference_notes.archive(self.owner,note['id'],True)
            with self.assertRaises(service.Error):self.begin_insight()
            generate.assert_not_called()
        self.assertEqual(insight_context.build('other')['concepts'],[])

    def test_ready_bundle_replay_claim_and_no_graph_or_mastery_mutation(self):
        self.graph();before=db.all('SELECT * FROM knowledge_evidence')
        first,fresh=self.begin_insight('same-insight');self.assertTrue(fresh)
        second,fresh=self.begin_insight('other-request');self.assertFalse(fresh);self.assertEqual(first['id'],second['id'])
        with patch.object(ai,'generate',side_effect=lambda model,instruction,data:self.answer(data)) as generate:
            with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:insights.generate(first['id']),range(2)))
            self.assertEqual(generate.call_count,1)
        status=insights.status(self.owner);self.assertEqual(status['job']['state'],'ready');self.assertEqual(status['bundle']['state'],'current')
        self.assertIsNone(db.one('SELECT snapshot FROM insight_jobs WHERE id=?',(first['id'],))['snapshot'])
        self.assertEqual(self.begin_insight('same-insight')[0]['id'],first['id'])
        self.assertEqual(db.all('SELECT * FROM knowledge_evidence'),before)
        self.assertEqual(db.all('SELECT * FROM learning_observations'),[])
        self.assertIsNone(insights.status('other')['bundle'])

    def test_invalid_ids_quotes_or_answers_rejected_without_replacing_bundle(self):
        self.graph();context=insight_context.build(self.owner);draft=self.answer(context)
        for field in ['concept_ids','assertion_ids','evidence_ids']:
            invalid=draft.model_copy(deep=True);getattr(invalid.suggestions[0],field).append('foreign')
            with self.assertRaises(service.Error):insight_context.validate(context,invalid)
        invalid=draft.model_copy(deep=True);invalid.suggestions[0].practice_guide='```python\nprint(1)\n```'
        with self.assertRaises(service.Error):insight_context.validate(context,invalid)
        job,_=self.begin_insight()
        with patch.object(ai,'generate',return_value=draft):insights.generate(job['id'])
        saved=insights.status(self.owner)['bundle']
        retry,_=self.begin_insight()
        with patch.object(ai,'generate',return_value=invalid):insights.generate(retry['id'])
        self.assertEqual(insights.status(self.owner)['job']['state'],'failed')
        self.assertEqual(insights.status(self.owner)['bundle']['id'],saved['id'])

    def test_midflight_source_change_and_restart_cannot_publish_late_result(self):
        note,_=self.graph();job,_=self.begin_insight();draft=self.answer(insight_context.build(self.owner))
        def stale(*args):reference_notes.archive(self.owner,note['id'],True);return draft
        with patch.object(ai,'generate',side_effect=stale):insights.generate(job['id'])
        self.assertEqual(insights.status(self.owner)['job']['state'],'stale');self.assertIsNone(insights.status(self.owner)['bundle'])
        self.graph();job,_=self.begin_insight();draft=self.answer(insight_context.build(self.owner))
        def restart(*args):service.initialize();return draft
        with patch.object(ai,'generate',side_effect=restart):insights.generate(job['id'])
        self.assertEqual(insights.status(self.owner)['job']['state'],'interrupted');self.assertIsNone(insights.status(self.owner)['bundle'])
        self.assertIsNone(db.one('SELECT snapshot FROM insight_jobs WHERE id=?',(job['id'],))['snapshot'])

    def test_replacement_expiry_and_current_source_state(self):
        note,_=self.graph();draft=self.answer(insight_context.build(self.owner))
        ids=[]
        for _ in range(2):
            job,_=self.begin_insight();ids.append(job['id'])
            with patch.object(ai,'generate',return_value=draft):insights.generate(job['id'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM insight_bundles')['n'],1)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM insight_jobs WHERE snapshot IS NOT NULL')['n'],0)
        self.assertEqual(insights.status(self.owner)['bundle']['id'],ids[-1])
        reference_notes.archive(self.owner,note['id'],True)
        self.assertEqual(insights.status(self.owner)['bundle']['state'],'stale')
        with patch.object(service,'now',return_value='2099-01-01T00:00:00+00:00'):
            self.assertIsNone(insights.status(self.owner)['bundle'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM insight_bundles')['n'],0)

    def test_actual_provider_settings_usage_and_output_cap(self):
        self.graph();job,_=self.begin_insight();draft=self.answer(insight_context.build(self.owner));real=httpx.Client
        def handle(request):
            payload=json.loads(request.content);self.assertEqual(payload['max_completion_tokens'],4000)
            self.assertEqual(payload['model'],'insight-current-model');self.assertEqual(request.headers['authorization'],'Bearer fixture-only')
            self.assertNotIn('deterministic coding exercises',payload['messages'][0]['content'])
            self.assertNotIn('body',json.loads(payload['messages'][1]['content'])['sources'][0])
            return httpx.Response(200,json={'choices':[{'message':{'content':json.dumps({'data':draft.model_dump(),'error':''})}}],'usage':{'prompt_tokens':100,'completion_tokens':50}})
        with patch.dict(os.environ,AI_API_KEY='fixture-only',AI_MODEL='insight-current-model'),patch.object(ai.httpx,'Client',side_effect=lambda **kw:real(transport=httpx.MockTransport(handle),**kw)):
            insights.generate(job['id'])
        self.assertEqual(insights.status(self.owner)['bundle']['model'],'insight-current-model')
        calls=db.all('SELECT * FROM ai_usage WHERE generation_id=?',(job['id'],));self.assertEqual(len(calls),1);self.assertEqual(calls[0]['output_tokens'],50)

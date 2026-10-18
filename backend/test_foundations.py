"""Ownership, state transitions, privacy and grading contracts for the two-step course."""
import json
import re
import unittest
from unittest.mock import patch
from . import ai, db, foundations as f, learning, service, test_app
from .foundation_catalog import CATALOG, public


def feedback():
    return f.ExplanationFeedback(items=[f.ConceptFeedback(question_id=q, understood='핵심 동작을 설명했습니다.', missing='빈 상태도 설명해주세요.', correction='') for q in ('q1','q2')])


class FoundationsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def explain(self, request_id='explanation-one', answers=None):
        with patch.object(ai, 'available', return_value=True), patch.object(ai, 'generate', return_value=feedback()) as call:
            response = self.client.post('/api/foundations/queue/explain', json={'version':1, 'request_id':request_id, 'answers':answers or ['먼저 들어온 값을 먼저 꺼냅니다.', 'head를 이동합니다.']})
        self.assertEqual(response.status_code,202,response.text)
        return self.client.get('/api/foundation-reviews/'+response.json()['id']).json(), call.call_count

    def submit(self, request_id='implementation-one', passed=True):
        checks = [{'label':str(i), 'passed':passed, 'status':'passed' if passed else 'assertion_failed', 'detail':''} for i in range(6)]
        with patch.object(f.runner,'pin_runtime',return_value='sha256:'+'a'*64), patch.object(f,'grade',return_value=checks) as call:
            response = self.client.post('/api/foundations/queue/submit', json={'version':1,'request_id':request_id, 'code':'learner-code','test_code':'learner-tests'})
        return response, call.call_count

    def test_catalog_has_all_units_and_never_exposes_private_answers(self):
        self.assertEqual(len(CATALOG),12)
        self.assertEqual(len(self.client.get('/api/foundations').json()['items']),12)
        for item in CATALOG.values():
            response = self.client.get('/api/foundations/'+item['id'])
            self.assertEqual(response.status_code,200)
            value=response.json()
            self.assertNotIn('reference',value); self.assertNotIn('hidden_tests',value); self.assertNotIn('mutations',value)
            self.assertNotIn('answer',value['questions'][0])
            self.assertFalse(value['unlocked']); self.assertFalse(value['completed'])
            self.assertEqual(len(item['questions']),2)
            self.assertEqual(len({w['code'] for w in item['mutations']}),2)
            self.assertTrue(all(w['code'] != item['reference'] for w in item['mutations']))
            self.assertTrue(all(p in CATALOG for p in item['prerequisites']))
            copy=public(item); copy['questions'][0]['prompt']='changed'
            self.assertNotEqual(item['questions'][0]['prompt'],'changed')
        self.assertEqual(self.client.get('/api/foundations/nope').status_code,404)

    def test_revision_validation_and_owner_isolation(self):
        body={'version':1,'revision':0,'answers':['first','second'],'code':'draft','test_code':'tests'}
        url='/api/foundations/queue/progress'
        self.assertEqual(self.client.put(url,json=body).json(),{'revision':1})
        self.assertEqual(self.client.put(url,json=body).status_code,409)
        self.assertEqual(self.client.get('/api/foundations/queue').json()['progress']['code'],'draft')
        self.assertIsNone(f.view('someone-else','queue')['progress'])
        self.assertEqual(self.client.put(url,json={**body,'version':2}).status_code,409)
        self.assertEqual(self.client.put(url,json={**body,'code':'x'*24001}).status_code,422)
        self.assertEqual(self.client.post('/api/foundations/queue/explain',json={'version':1,'request_id':'long-enough','answers':[' ','ok']}).status_code,422)
        self.assertEqual(self.client.post('/api/foundations/queue/explain',json={'version':1,'request_id':'long-enough','answers':['one']}).status_code,422)

    def test_feedback_unlocks_with_missing_concepts_and_replay_is_free(self):
        job,calls=self.explain()
        self.assertEqual(calls,1); self.assertEqual(job['state'],'ready')
        self.assertTrue(job['result']['items'][0]['missing'])
        self.assertTrue(self.client.get('/api/foundations/queue').json()['unlocked'])
        replay,calls=self.explain()
        self.assertEqual(calls,0); self.assertEqual(replay,job)
        with self.assertRaises(service.Error): f.job('someone-else',job['id'],True)
        conflict=self.client.post('/api/foundations/queue/explain',json={'version':1,'request_id':'explanation-one','answers':['different','text']})
        self.assertEqual(conflict.status_code,409)
        self.assertEqual(f.view('someone-else','queue')['unlocked'],False)

    def test_ai_failure_or_invalid_feedback_does_not_unlock_and_input_is_kept(self):
        for index,outcome in enumerate((RuntimeError('private-key'),f.ExplanationFeedback(items=[feedback().items[0],feedback().items[0]]))):
            with patch.object(ai,'available',return_value=True), patch.object(ai,'generate',side_effect=outcome if isinstance(outcome,Exception) else None,return_value=outcome):
                response=self.client.post('/api/foundations/queue/explain',json={'version':1,'request_id':f'failed-review-{index}','answers':['saved-a','saved-b']})
            job=self.client.get('/api/foundation-reviews/'+response.json()['id']).json()
            self.assertEqual(job['state'],'failed'); self.assertEqual(job['payload']['answers'],['saved-a','saved-b'])
            self.assertNotIn('private-key',json.dumps(job)); self.assertFalse(f.view(self.owner,'queue')['unlocked'])
        with patch.object(ai,'available',return_value=False):
            response=self.client.post('/api/foundations/queue/explain',json={'version':1,'request_id':'disabled-review','answers':['a','b']})
            self.assertEqual(response.status_code,503)

    def test_implementation_requires_review_and_persists_evidence_and_history(self):
        response,calls=self.submit(); self.assertEqual(response.status_code,409); self.assertEqual(calls,0)
        self.explain()
        response,calls=self.submit(); self.assertEqual(response.status_code,202); self.assertEqual(calls,1)
        job=self.client.get('/api/foundation-attempts/'+response.json()['id']).json()
        self.assertEqual(job['state'],'passed')
        replay,calls=self.submit(); self.assertEqual(calls,0); self.assertEqual(replay.json(),job)
        evidence=learning.evidence(self.owner)
        self.assertEqual(len(evidence),1); self.assertEqual(evidence[0]['kind'],'FOUNDATION')
        self.assertEqual(evidence[0]['submitted_tests'],'learner-tests')
        self.assertEqual(evidence[0]['content_version'],1)
        self.assertEqual(evidence[0]['assistance'],'hint')
        self.assertEqual(self.client.get('/api/me/learning-summary').json()['current_passed_count'],1)
        self.assertEqual(len(self.client.get('/api/me/foundations').json()['items']),1)
        self.assertEqual(f.history('someone-else'),[])
        self.assertEqual(f.evidence('someone-else'),[])
        with self.assertRaises(service.Error): f.job('someone-else',job['id'])
        self.submit('implementation-failed',False)
        self.assertEqual(len(f.history(self.owner)),1); self.assertTrue(f.view(self.owner,'queue')['completed'])
        records=self.client.get('/api/foundations/queue/history').json()
        self.assertEqual(len(records['attempts']),2); self.assertEqual(len(records['reviews']),1)
        self.assertNotIn('snapshot',records['attempts'][0])

    def test_reference_view_is_owned_gated_and_help_stays_after_save(self):
        self.assertEqual(self.client.get('/api/foundations/queue/solution').status_code,409)
        self.explain()
        self.assertEqual(self.client.get('/api/foundations/queue/solution').json()['code'],CATALOG['queue']['reference'])
        self.client.put('/api/foundations/queue/progress',json={'version':1,'revision':0,'answers':['a','b'],'code':'my code','test_code':'tests'})
        self.submit()
        self.assertEqual(f.evidence(self.owner)[0]['assistance'],'solution')
        with self.assertRaises(service.Error): f.solution('someone-else','queue')

    def test_inflight_jobs_are_recoverable_and_busy_requests_do_not_duplicate(self):
        body=f.ExplanationInput(version=1,request_id='inflight-review',answers=['a','b'])
        with patch.object(ai,'available',return_value=True):
            job,fresh=f.begin(self.owner,'queue',body,True); self.assertTrue(fresh)
            self.assertFalse(f.begin(self.owner,'queue',body,True)[1])
            with self.assertRaises(service.Error): f.begin(self.owner,'queue',body.model_copy(update={'request_id':'another-review'}),True)
        service.initialize()
        self.assertEqual(f.job(self.owner,job['id'],True)['state'],'error')
        self.assertEqual(f.job(self.owner,job['id'],True)['payload']['answers'],['a','b'])

    def test_no_auth_cannot_access_lessons_or_records(self):
        self.client.post('/api/logout',json={})
        for path in ('/api/foundations','/api/foundations/queue','/api/me/foundations','/api/foundations/queue/history','/api/foundation-reviews/x'):
            self.assertEqual(self.client.get(path).status_code,401)

    def test_grading_does_not_count_crashes_or_empty_tests_as_detecting_mutants(self):
        def run(language,code,inputs,image_id=None):
            marker=re.search(r'FOUNDATION_[a-f0-9]+',code).group(0)
            return [{'status':'ok','stdout':marker+' '+json.dumps(output),'stderr':'','exit_code':0}]
        with patch.object(f.runner,'run',side_effect=run):
            for output,passed,caught in [({'assertions':0,'mismatches':0,'error':False},False,False),
                ({'assertions':2,'mismatches':0,'error':False},True,False),
                ({'assertions':1,'mismatches':1,'error':False},False,True),
                ({'assertions':1,'mismatches':0,'error':True},False,False)]:
                result=f.check('code','tests'); self.assertEqual((result['passed'],result['caught']),(passed,caught))
        with patch.object(f.runner,'run',return_value=[{'status':'compile_error','stdout':'private reference code','stderr':'secret','exit_code':1}]):
            self.assertEqual(f.check('code','tests')['detail'],'')
            self.assertIn('private reference code',f.check('code','tests',details=True)['detail'])
        with patch.object(f,'check',return_value={'passed':True,'caught':False,'status':'passed','detail':''}):
            checks=f.grade(CATALOG['queue'],'code','tests',None)
            self.assertFalse(checks[-1]['passed']); self.assertFalse(checks[-2]['passed'])

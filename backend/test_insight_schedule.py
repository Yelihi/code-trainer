import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from . import ai,db,service,insights,insight_schedule,insight_adoptions,test_insights,insight_context
from .insight_schema import InsightScheduleInput

class ScheduleTest(unittest.TestCase):
    fixture=test_insights.InsightsTest
    setUp,tearDown=fixture.setUp,fixture.tearDown
    note,graph_data,register=fixture.note,fixture.graph_data,fixture.register
    graph,begin_insight,answer=fixture.graph,fixture.begin_insight,fixture.answer
    def at(self,day):return patch.object(service,'now',return_value=(datetime(2030,1,1,tzinfo=timezone.utc)+timedelta(days=day)).isoformat())
    def enable(self):
        with self.at(0):return insight_schedule.configure(self.owner,InsightScheduleInput(enabled=True,revision=0))
    def claim(self):
        with patch.object(ai,'available',return_value=True):return insight_schedule.claim(self.owner)
    def finish(self,job,fail=False):
        with patch.object(ai,'generate',side_effect=ai.AIError('fixture') if fail else None,return_value=self.answer(insight_context.build(self.owner))):insights.generate(job)
    def test_defaultoff_firstdue_atomic_claim_and_restart_no_retry(self):
        self.graph();self.assertFalse(insight_schedule.status(self.owner)['enabled']);self.assertIsNone(self.claim())
        enabled=self.enable();self.assertEqual(enabled['next_at'],'2030-01-08T00:00:00+00:00')
        with self.at(6):self.assertIsNone(self.claim())
        with self.at(7),patch.object(ai,'available',return_value=True):
            with ThreadPoolExecutor(max_workers=2) as pool:jobs=list(pool.map(lambda _:insight_schedule.claim(self.owner),range(2)))
            job=next(x for x in jobs if x);self.assertEqual(len([x for x in jobs if x]),1)
            service.initialize();self.assertEqual(db.one('SELECT state FROM insight_jobs WHERE id=?',(job,))['state'],'interrupted')
            self.assertEqual(insight_schedule.status(self.owner)['used'],1)
        with self.at(70):self.assertIsNone(self.claim());self.assertEqual(insight_schedule.status(self.owner)['reason'],'unchanged');self.assertEqual(insight_schedule.status(self.owner)['next_at'],'2030-03-19T00:00:00+00:00')
    def test_budget_rolling30days_counts_failures_and_toggle_does_not_reset(self):
        self.graph();self.enable()
        for i,day in enumerate([7,14,21,28]):
            db.execute('UPDATE knowledge_concepts SET definition=?',(str(i),))
            with self.at(day):job=self.claim();self.assertTrue(job);self.finish(job,fail=True)
        db.execute("UPDATE knowledge_concepts SET definition='new'")
        with self.at(35):
            self.assertIsNone(self.claim());self.assertEqual(insight_schedule.status(self.owner)['reason'],'budget');self.assertEqual(insight_schedule.status(self.owner)['used'],4)
            insight_schedule.configure(self.owner,InsightScheduleInput(enabled=False,revision=1));insight_schedule.configure(self.owner,InsightScheduleInput(enabled=True,revision=2))
            self.assertEqual(insight_schedule.status(self.owner)['used'],4)
        with self.at(37):self.assertEqual(insight_schedule.status(self.owner)['used'],3)
        with self.at(42):self.assertTrue(self.claim());self.assertEqual(insight_schedule.status(self.owner)['used'],4)
    def test_insufficient_disconnected_and_pending_do_not_spend(self):
        self.enable()
        with self.at(7):self.assertIsNone(self.claim());self.assertEqual(insight_schedule.status(self.owner)['reason'],'insufficient')
        self.graph()
        with self.at(14),patch.object(ai,'available',return_value=False):self.assertIsNone(insight_schedule.claim(self.owner));self.assertEqual(insight_schedule.status(self.owner)['reason'],'ai-unavailable')
        with self.at(21):
            manual,_=self.begin_insight();self.assertIsNone(self.claim());self.assertEqual(insight_schedule.status(self.owner)['reason'],'pending');self.assertEqual(insight_schedule.status(self.owner)['used'],0)
    def test_disable_queued_guard_and_settings_conflicts(self):
        self.graph();self.enable()
        with self.at(7):
            job=self.claim();insight_schedule.configure(self.owner,InsightScheduleInput(enabled=False,revision=1))
            with patch.object(ai,'generate') as generate:insights.generate(job);generate.assert_not_called()
            self.assertEqual(insight_schedule.status(self.owner)['used'],1)
            with self.assertRaises(service.Error):insight_schedule.configure(self.owner,InsightScheduleInput(enabled=True,revision=0))
        self.assertFalse(insight_schedule.status('other')['enabled'])
        response=self.client.put('/api/insights/schedule',json={'enabled':'true','revision':0});self.assertEqual(response.status_code,422)
    def test_success_actualjob_failure_preserves_current_and_cleanup_adoption(self):
        self.graph();self.enable()
        with self.at(7):
            job=self.claim();self.finish(job);self.assertEqual(insights.status(self.owner)['job']['state'],'ready');adopt=insight_adoptions.choose(self.owner,job,0,'adopt')
        db.execute("UPDATE knowledge_concepts SET definition='changed'")
        with self.at(14):job2=self.claim();self.finish(job2,fail=True);self.assertEqual(insights.status(self.owner)['bundle']['id'],job)
        with self.at(45):
            insight_schedule.cleanup();self.assertEqual(db.all('SELECT * FROM insight_bundles'),[]);self.assertTrue(insight_adoptions.read(self.owner,adopt['id']))
    def test_manual_same_context_suppresses_automatic_attempt(self):
        self.graph();self.enable()
        with self.at(1):job,_=self.begin_insight();self.finish(job['id'])
        with self.at(7):self.assertIsNone(self.claim());self.assertEqual(insight_schedule.status(self.owner)['reason'],'unchanged');self.assertEqual(insight_schedule.status(self.owner)['used'],0)

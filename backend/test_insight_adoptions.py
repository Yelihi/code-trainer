import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from . import ai,db,service,insights,insight_adoptions,reference_notes,test_insights,insight_context
from .insight_schema import ExplorationNotes

class AdoptionTest(unittest.TestCase):
    fixture=test_insights.InsightsTest
    setUp,tearDown=fixture.setUp,fixture.tearDown
    note,graph_data,register=fixture.note,fixture.graph_data,fixture.register
    graph,begin_insight,answer=fixture.graph,fixture.begin_insight,fixture.answer
    def bundle(self):
        note,_=self.graph();job,_=self.begin_insight()
        with patch.object(ai,'generate',return_value=self.answer(insight_context.build(self.owner))):insights.generate(job['id'])
        return note,job['id']
    def test_adoption_once_independent_and_owner_guard(self):
        note,bundle=self.bundle()
        with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:insight_adoptions.choose(self.owner,bundle,0,'adopt'),range(2)))
        self.assertEqual(results[0]['id'],results[1]['id']);record=insight_adoptions.read(self.owner,results[0]['id'])
        self.assertEqual(record['notes'],'');self.assertEqual(record['context']['sources'][0]['version'],1)
        db.execute('DELETE FROM insight_bundles');self.assertEqual(insight_adoptions.choose(self.owner,bundle,0,'adopt')['id'],record['id'])
        with self.assertRaises(service.Error):insight_adoptions.read('other',record['id'])
        reference_notes.archive(self.owner,note['id'],True)
        self.assertEqual(insight_adoptions.read(self.owner,record['id'])['state'],'stale')
        self.assertEqual(db.all('SELECT * FROM learning_observations'),[])
    def test_expiry_stale_index_and_other_owner_rejected(self):
        note,bundle=self.bundle()
        for owner,index in [('other',0),(self.owner,3), (self.owner,-1)]:
            with self.assertRaises(service.Error):insight_adoptions.choose(owner,bundle,index,'adopt')
        with patch.object(service,'now',return_value='2099-01-01T00:00:00+00:00'):
            with self.assertRaises(service.Error):insight_adoptions.choose(self.owner,bundle,0,'adopt')
        reference_notes.archive(self.owner,note['id'],True)
        with self.assertRaises(service.Error):insight_adoptions.choose(self.owner,bundle,0,'adopt')
    def test_notes_same_body_replay_and_conflict(self):
        _,bundle=self.bundle();record=insight_adoptions.choose(self.owner,bundle,0,'adopt');rid=record['id']
        req=ExplorationNotes(revision=0,notes='내 예상과 관찰')
        saved=insight_adoptions.save(self.owner,rid,req);self.assertEqual(saved['revision'],1)
        self.assertEqual(insight_adoptions.save(self.owner,rid,req)['revision'],1)
        self.assertEqual(insight_adoptions.save(self.owner,rid,ExplorationNotes(revision=1,notes=req.notes))['revision'],1)
        with self.assertRaises(service.Error):insight_adoptions.save(self.owner,rid,ExplorationNotes(revision=0,notes='충돌'))
        self.assertEqual(insight_adoptions.read(self.owner,rid)['notes'],req.notes)
    def test_skip_minimal_fingerprint_suppression_and_expiry(self):
        _,bundle=self.bundle();before=insights.status(self.owner)['bundle'];draft=self.answer(before['context'])
        insight_adoptions.choose(self.owner,bundle,0,'skip')
        self.assertEqual(insight_adoptions.choose(self.owner,bundle,0,'skip')['action'],'skip')
        with self.assertRaises(service.Error):insight_adoptions.choose(self.owner,bundle,0,'adopt')
        self.assertEqual(insights.status(self.owner)['bundle']['choices']['0']['action'],'skip')
        job,_=self.begin_insight()
        with patch.object(ai,'generate',return_value=draft):insights.generate(job['id'])
        self.assertEqual(insights.status(self.owner)['bundle']['id'],bundle)
        self.assertEqual(insights.status(self.owner)['job']['state'],'empty')
        self.assertNotIn('data',db.one('SELECT * FROM insight_skips'))
        with patch.object(service,'now',return_value='2099-01-01T00:00:00+00:00'):
            self.assertEqual(insight_adoptions.filter_skipped(self.owner,draft.suggestions),draft.suggestions)
        self.assertEqual(db.all('SELECT * FROM insight_skips'),[])

import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch
from . import ai, db, service, spaced_reviews, test_materials, reference_notes, practice_records, resources
from .note_schema import ReferenceInput, ReferenceMetadata
from .practice_record_schema import PracticeRecordInput
from .resource_schema import ResourceInput
from .spaced_review_schema import ReviewResponse


class SpacedReviewsTest(unittest.TestCase):
    fixture = test_materials.MaterialsTest
    setUp, tearDown = fixture.setUp, fixture.tearDown
    interpretation, begin, worksheet = fixture.interpretation, fixture.begin, fixture.worksheet

    def note(self):
        return reference_notes.save(self.owner, ReferenceInput(id=service.uid(), revision=0, title='내 노트', body='관찰과 해석을 구분한다.', metadata=ReferenceMetadata()))

    def enroll(self, kind, identifier, revision=1):
        response = self.client.post('/api/spaced-reviews', json=dict(kind=kind, origin_id=identifier, revision=revision))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_enrollment_is_independent_owned_versioned_and_idempotent(self):
        interpretation, _ = self.interpretation(); worksheet, _ = self.worksheet(); note = self.note()
        practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='saved-review', revision=0, answers={'q1':'내 답변'}, summary='내 요약'))
        with patch.object(service, 'now', return_value='2026-10-25T23:59:59+00:00'), patch.object(ai, 'generate') as generate:
            for kind, identifier in [('interpretation',interpretation['id']),('practice',worksheet['id']),('note',note['id'])]:
                row = self.enroll(kind, identifier)
                self.assertEqual(row['due_at'], '2026-10-26T23:59:59+00:00')
                self.assertFalse(row['due'])
                self.assertEqual(self.enroll(kind, identifier)['id'], row['id'])
                with self.assertRaises(service.Error): spaced_reviews.view('other', row['id'])
            generate.assert_not_called()
        self.assertEqual(db.one('SELECT COUNT(*) n FROM spaced_reviews')['n'], 3)
        for table in ['material_reviews','review_schedule','learning_observations']:
            self.assertEqual(db.one('SELECT COUNT(*) n FROM '+table)['n'], 0)
        self.client.post('/api/logout',json={})
        self.assertEqual(self.client.get('/api/spaced-reviews').status_code,401)

    def test_explicit_completion_due_boundary_intervals_and_replay(self):
        row = self.enroll('note', self.note()['id']); identifier = row['id']; original = dict(row)
        self.assertEqual(spaced_reviews.view(self.owner,identifier)['revision'], 0)
        for days in [3,7,14,14,1,3]:
            answer = 'needs_review' if days == 1 else 'can_explain'
            request = ReviewResponse(request_id=service.uid(), revision=row['revision'], response=answer)
            due = datetime.fromisoformat(row['due_at'])
            with patch.object(service,'now',return_value=(due-timedelta(microseconds=1)).isoformat()):
                with self.assertRaises(service.Error): spaced_reviews.respond(self.owner,identifier,request)
            with patch.object(service,'now',return_value=due.isoformat()):
                result = spaced_reviews.respond(self.owner,identifier,request)
                self.assertEqual(result['due_at'],(due+timedelta(days=days)).isoformat())
                self.assertEqual(spaced_reviews.respond(self.owner,identifier,request),result)
                changed=request.model_copy(update={'response':'needs_review' if answer=='can_explain' else 'can_explain'})
                with self.assertRaises(service.Error): spaced_reviews.respond(self.owner,identifier,changed)
                row=spaced_reviews.view(self.owner,identifier)
        self.assertEqual(len(row['responses']),6)
        self.assertEqual(row['snapshot'],original['snapshot'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM learning_observations')['n'],0)

    def test_concurrent_completion_and_old_revision_do_not_advance_twice(self):
        row=self.enroll('note',self.note()['id']);request=ReviewResponse(request_id='same-request',revision=0,response='can_explain')
        with patch.object(service,'now',return_value=row['due_at']):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results=list(pool.map(lambda _:spaced_reviews.respond(self.owner,row['id'],request),range(2)))
            self.assertEqual(results[0],results[1])
            with self.assertRaises(service.Error):spaced_reviews.respond(self.owner,row['id'],request.model_copy(update={'request_id':'another-request'}))
        self.assertEqual(db.one('SELECT COUNT(*) n FROM spaced_review_responses')['n'],1)
        with self.assertRaises(service.Error):spaced_reviews.respond('other',row['id'],request)

    def test_source_changes_and_archive_block_completion_preserve_snapshot(self):
        interpretation,raw=self.interpretation();row=self.enroll('interpretation',interpretation['id'])
        resources.register(self.owner,ResourceInput(request_id='changed-raw',resource_id=raw['id'],revision=1,kind='text',name='new',content='New body'))
        self.assertEqual(spaced_reviews.view(self.owner,row['id'])['state'],'stale')
        self.assertEqual(spaced_reviews.enroll(self.owner,'interpretation',interpretation['id'],1)['id'],row['id'])
        worksheet,_=self.worksheet()
        practice_records.save(self.owner,worksheet['id'],PracticeRecordInput(request_id='practice-one',revision=0,answers={},summary='original'))
        practice=self.enroll('practice',worksheet['id'])
        practice_records.save(self.owner,worksheet['id'],PracticeRecordInput(request_id='practice-two',revision=1,answers={},summary='changed'))
        self.assertEqual(spaced_reviews.view(self.owner,practice['id'])['state'],'stale')
        self.assertIn('original',spaced_reviews.view(self.owner,practice['id'])['snapshot']['body'])
        note=self.note();target=self.enroll('note',note['id']);reference_notes.archive(self.owner,note['id'],True)
        self.assertEqual(spaced_reviews.view(self.owner,target['id'])['state'],'archived')
        with patch.object(service,'now',return_value=target['due_at']):
            for item in [row,practice,target]:
                with self.assertRaises(service.Error):spaced_reviews.respond(self.owner,item['id'],ReviewResponse(request_id=service.uid(),revision=0,response='can_explain'))
        reference_notes.archive(self.owner,note['id'],False)
        self.assertEqual(spaced_reviews.view(self.owner,target['id'])['state'],'stale')
        self.assertEqual(len(spaced_reviews.queue(self.owner)['items']),3)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM spaced_review_responses')['n'],0)
        db.execute("UPDATE interpretations SET state='failed' WHERE id=?",(interpretation['id'],))
        self.assertEqual(spaced_reviews.view(self.owner,row['id'])['state'],'unavailable')

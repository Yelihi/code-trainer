import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from . import ai, db, service, test_app, test_worksheets, test_practice_records, practice_records, resources
from .practice_record_schema import PracticeRecordInput
from .resource_schema import ResourceInput


class MaterialsTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    interpretation = test_worksheets.WorksheetsTest.interpretation
    begin = test_worksheets.WorksheetsTest.begin
    worksheet = test_practice_records.PracticeRecordsTest.worksheet

    def test_explicit_verification_is_owned_idempotent_and_has_no_learning_side_effects(self):
        from . import materials
        interpretation, _ = self.interpretation()
        path = '/api/materials/interpretation/' + interpretation['id']
        with patch.object(ai, 'generate') as generate:
            self.assertIsNone(self.client.get(path + '?revision=1').json()['review'])
            self.assertEqual(self.client.get('/api/material-reviews').json()['total'], 0)
            response = self.client.post(path + '/review', json={'revision': 1})
            self.assertEqual(response.status_code, 200, response.text)
            first = response.json()
            self.assertEqual(self.client.post(path + '/review', json={'revision': 1}).json(), first)
            self.assertEqual(self.client.get('/api/material-reviews').json()['total'], 1)
            self.assertEqual(first['authorship'], 'ai')
            self.assertIn(test_worksheets.DOCUMENT['sections'][0]['body'], first['body'])
            for table in ['knowledge_sources', 'review_schedule', 'learning_observations']:
                self.assertEqual(db.one('SELECT COUNT(*) n FROM ' + table)['n'], 0)
            generate.assert_not_called()
        with self.assertRaises(service.Error) as denied: materials.detail('other', first['id'])
        self.assertEqual(denied.exception.status, 404)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.post(path + '/review', json={'revision': 1}).status_code, 401)
        self.assertEqual(self.client.get('/api/material-reviews').status_code, 401)

    def test_concurrent_review_and_changed_learner_version(self):
        from . import materials
        worksheet, _ = self.worksheet()
        saved = practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='saved-one', revision=0, answers={'q1': '내 설명'}, summary='내 요약'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: materials.mark(self.owner, 'practice', worksheet['id'], 1), range(2)))
        self.assertEqual(results[0]['id'], results[1]['id'])
        self.assertEqual(db.one('SELECT COUNT(*) n FROM material_reviews')['n'], 1)
        practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='saved-two', revision=saved['revision'], answers={'q1': '새 설명'}, summary='새 요약'))
        old = materials.detail(self.owner, results[0]['id'])
        self.assertEqual(old['state'], 'stale')
        self.assertIn('내 설명', old['body'])
        self.assertNotIn('새 설명', old['body'])
        self.assertIsNone(materials.status(self.owner, 'practice', worksheet['id'], 2)['review'])
        current = materials.mark(self.owner, 'practice', worksheet['id'], 2)
        self.assertEqual(current['state'], 'eligible')
        self.assertEqual(current['authorship'], 'user')
        self.assertEqual(materials.listing(self.owner, 1)['total'], 2)

    def test_stale_confirmation_empty_unready_and_archived_sources(self):
        from . import materials, reference_notes
        worksheet, raw = self.worksheet()
        practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='empty-record', revision=0, answers={}, summary='   '))
        with self.assertRaises(service.Error) as empty: materials.mark(self.owner, 'practice', worksheet['id'], 1)
        self.assertEqual(empty.exception.status, 409)
        practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='nonempty-record', revision=1, answers={}, summary='내용'))
        with self.assertRaises(service.Error) as stale: materials.mark(self.owner, 'practice', worksheet['id'], 1)
        self.assertEqual(stale.exception.status, 409)
        interpretation_id = db.one('SELECT interpretation_id FROM worksheets WHERE id=?', (worksheet['id'],))['interpretation_id']
        checked = materials.mark(self.owner, 'interpretation', interpretation_id, 1)
        resources.register(self.owner, ResourceInput(request_id='raw-new-version', resource_id=raw['id'], revision=1, kind='text', name='new', content='Changed raw body'))
        self.assertEqual(materials.detail(self.owner, checked['id'])['state'], 'stale')
        with self.assertRaises(service.Error): materials.mark(self.owner, 'practice', worksheet['id'], 2)
        db.execute("UPDATE interpretations SET state='failed' WHERE id=?", (interpretation_id,))
        with self.assertRaises(service.Error) as unready: materials.status(self.owner, 'interpretation', interpretation_id, 1)
        self.assertEqual(unready.exception.status, 409)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM material_reviews')['n'], 1)

    def test_confirmation_races_with_save_and_note_archive_preserves_text(self):
        from . import materials, reference_notes, interpretations
        from .note_schema import ReferenceInput, ReferenceMetadata
        from .interpretation_schema import InterpretationInput, InterpretationDraft
        worksheet, _ = self.worksheet()
        practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='race-original', revision=0, answers={}, summary='original learner text'))
        def confirm():
            try: return materials.mark(self.owner, 'practice', worksheet['id'], 1)
            except service.Error as e: return e.status
        def edit():
            return practice_records.save(self.owner, worksheet['id'], PracticeRecordInput(request_id='race-edited', revision=1, answers={}, summary='new learner text'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.submit(confirm), pool.submit(edit)
            result, saved = first.result(), second.result()
        self.assertEqual(saved['revision'], 2)
        self.assertIsNone(materials.status(self.owner, 'practice', worksheet['id'], 2)['review'])
        if isinstance(result, dict):
            old = materials.detail(self.owner, result['id'])
            self.assertEqual(old['state'], 'stale')
            self.assertIn('original learner text', old['body'])
        else: self.assertEqual(result, 409)
        note = reference_notes.save(self.owner, ReferenceInput(id=service.uid(), revision=0, title='source note', body=test_worksheets.BODY, metadata=ReferenceMetadata()))
        resource_id = db.one('SELECT id FROM resources WHERE note_id=?', (note['id'],))['id']
        with patch.object(ai, 'available', return_value=True):
            job, _ = interpretations.begin(self.owner, InterpretationInput(request_id='note-interpretation', resource_id=resource_id, revision=1))
        with patch.object(ai, 'generate', return_value=InterpretationDraft.model_validate(test_worksheets.DOCUMENT)):
            interpretations.generate(job['id'])
        checked = materials.mark(self.owner, 'interpretation', job['id'], 1)
        reference_notes.archive(self.owner, note['id'], True)
        archived = materials.detail(self.owner, checked['id'])
        self.assertEqual(archived['state'], 'archived')
        self.assertEqual(archived['body'], checked['body'])
        self.assertEqual(materials.mark(self.owner, 'interpretation', job['id'], 1)['id'], checked['id'])

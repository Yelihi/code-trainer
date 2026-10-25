"""A selected immutable interpretation drives the existing validated coding flow."""
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch
from pydantic import ValidationError
from . import ai, db, service, resources, test_app, test_worksheets, interpretations
from .schema import GenerationInput
from .resource_schema import ResourceInput
from .sample import sample


class CodePracticeTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown
    interpretation = test_worksheets.WorksheetsTest.interpretation

    def request(self, interpretation, **changes):
        return GenerationInput(**dict(dict(request_id='code-request', source_kind='interpretation',
            interpretation_id=interpretation['id'], section_id='s1', language='javascript', difficulty='intermediate'), **changes))

    def test_pinned_section_to_existing_unit_validation_and_retained_source(self):
        from . import code_practice
        interpretation, raw = self.interpretation()
        request = self.request(interpretation)
        with patch.object(ai, 'available', return_value=True):
            job, fresh = service.begin_generation(self.owner, request)
        self.assertTrue(fresh)
        resources.register(self.owner, ResourceInput(request_id='raw-update', resource_id=raw['id'], revision=1, kind='text', name='new', content='replacement raw body'))
        context, draft = sample()
        with patch.object(ai, 'analyze', return_value=context) as analyze, patch.object(service.runner, 'pin_runtime') as pin:
            service.generate(self.owner, job['id'], request)
            text, language, difficulty = analyze.call_args.args
            self.assertIn(test_worksheets.DOCUMENT['sections'][0]['body'], text)
            self.assertNotIn('replacement raw body', text)
            self.assertEqual((language, difficulty), ('javascript', 'intermediate'))
            pin.assert_not_called()
        ready = service.generation(self.owner, job['id'])
        course = service.get_context(self.owner, ready['context_id'])
        self.assertEqual(course['difficulty'], 'intermediate')
        self.assertEqual((course['interpretation_source']['interpretation_id'], course['interpretation_source']['section_id'], course['interpretation_source']['revision']), (interpretation['id'], 's1', 1))
        unit = GenerationInput(request_id='code-unit', source_kind='context', context_id=course['id'], unit_id=context.units[0].id, language='javascript')
        with patch.object(ai, 'available', return_value=True), patch.object(service.runner, 'available', return_value=True):
            unit_job, _ = service.begin_generation(self.owner, unit)
        with patch.object(ai, 'create_set', return_value=draft), patch.object(service.runner, 'pin_runtime', return_value='fixture'), patch.object(service, 'validate_set', return_value=[{'stub': True}]) as validate:
            service.generate(self.owner, unit_job['id'], unit)
        validate.assert_called_once()
        self.assertEqual(service.generation(self.owner, unit_job['id'])['state'], 'ready')
        self.assertEqual(len(service.get_set(self.owner, service.generation(self.owner, unit_job['id'])['set_id'])['exercises']), 4)
        with patch.object(ai, 'generate') as generate:
            self.assertEqual(len(code_practice.listing(self.owner, interpretation['id'], 's1')['items']), 1)
            generate.assert_not_called()
        service.delete_context(self.owner, course['id'])
        self.assertEqual(interpretations.view(self.owner, interpretation['id'])['state'], 'ready')
        self.assertEqual(code_practice.listing(self.owner, interpretation['id'], 's1')['items'], [])
        with db.connect(write=True) as c:
            resources.migrate(c)
        self.assertEqual(db.one('SELECT COUNT(*) n FROM resources')['n'], 1)

    def test_replay_conflict_concurrency_and_failure_recovery(self):
        from . import code_practice
        interpretation, _ = self.interpretation()
        with patch.object(ai, 'available', return_value=True), ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(lambda _: service.begin_generation(self.owner, self.request(interpretation)), range(2)))
        self.assertEqual(sum(fresh for _, fresh in values), 1)
        identifier = values[0][0]['id']
        for change in [dict(language='python'), dict(difficulty='advanced'), dict(section_id='s2')]:
            with self.assertRaises(service.Error) as error:
                service.begin_generation(self.owner, self.request(interpretation, **change))
            self.assertEqual(error.exception.status, 409)
        with patch.object(ai, 'analyze', side_effect=ai.AIError('코드 실습에 적합한 내용이 부족합니다.')):
            service.generate(self.owner, identifier, self.request(interpretation))
        self.assertEqual(service.generation(self.owner, identifier)['state'], 'failed')
        with patch.object(ai, 'available', return_value=False):
            self.assertFalse(service.begin_generation(self.owner, self.request(interpretation))[1])
        with patch.object(ai, 'available', return_value=True):
            retry, fresh = service.begin_generation(self.owner, self.request(interpretation, request_id='code-retry'))
        self.assertTrue(fresh)
        self.assertNotEqual(retry['id'], identifier)
        self.assertEqual(len(code_practice.listing(self.owner, interpretation['id'], 's1')['items']), 2)

    def test_owner_readiness_and_input_boundary(self):
        from . import code_practice
        interpretation, _ = self.interpretation()
        with patch.object(ai, 'available', return_value=True):
            for action in [lambda: service.begin_generation('other', self.request(interpretation)), lambda: code_practice.listing('other', interpretation['id'], 's1')]:
                with self.assertRaises(service.Error) as denied: action()
                self.assertEqual(denied.exception.status, 404)
            with self.assertRaises(service.Error) as missing:
                service.begin_generation(self.owner, self.request(interpretation, section_id='s6'))
            self.assertEqual(missing.exception.status, 404)
            db.execute("UPDATE interpretations SET state='failed' WHERE id=?", (interpretation['id'],))
            with self.assertRaises(service.Error) as unready:
                service.begin_generation(self.owner, self.request(interpretation))
            self.assertEqual(unready.exception.status, 409)
        for change in [dict(source='client forged body'),dict(section_id=None),dict(interpretation_id=None),dict(framework='other'),dict(source_kind='text',source='raw text')]:
            with self.assertRaises(ValidationError): self.request(interpretation, **change)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/interpretations/' + interpretation['id'] + '/code?section_id=s1').status_code, 401)

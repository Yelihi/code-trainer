import json
import os
import unittest
from unittest.mock import patch
import httpx
from cryptography.fernet import Fernet
from . import ai, db, service, usage, test_app
from .schema import CurriculumDraft
from .sample import sample


class AISettingsTest(unittest.TestCase):
    tearDown = test_app.AppTest.tearDown

    def setUp(self):
        test_app.AppTest.setUp(self)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {'TRAINER_AI_ENCRYPTION_KEY': Fernet.generate_key().decode(),
                              'AI_API_KEY': 'shared-test-key', 'AI_MODEL': 'shared-model',
                              'AI_BASE_URL': 'https://provider.example/v1'}).start()
        self.endpoint = '/api/ai/settings'

    def save(self, revision=0, key='owner-private-key', model='owner-model'):
        return self.client.put(self.endpoint, json={'revision': revision, 'api_key': key, 'model': model,
                                                    'provider_url': 'https://provider.example/v1'})

    def test_encryption_owner_revision_and_explicit_disconnect(self):
        from . import ai_settings
        self.assertEqual(self.client.get(self.endpoint).json()['source'], 'environment')
        first = self.save()
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()['revision'], 1)
        self.assertNotIn('owner-private-key', first.text)
        self.assertNotIn('owner-private-key', json.dumps(db.all('SELECT * FROM ai_settings')))
        self.assertEqual(self.save().json(), first.json())
        self.assertEqual(self.save(model='other-model').status_code, 409)
        self.assertEqual(ai_settings.configuration(self.owner)['api_key'], 'owner-private-key')
        with patch.object(ai_settings.access, 'enabled', return_value=True):
            self.assertIsNone(ai_settings.configuration('another-owner'))
        self.assertEqual(self.client.request('DELETE', self.endpoint, json={'revision': 0}).status_code, 409)
        deleted = self.client.request('DELETE', self.endpoint, json={'revision': 1})
        self.assertEqual(deleted.status_code, 200, deleted.text)
        self.assertEqual(deleted.json()['source'], 'disabled')
        self.assertEqual(self.client.request('DELETE', self.endpoint, json={'revision': 1}).json(), deleted.json())
        self.assertIsNone(ai_settings.configuration(self.owner))
        self.assertFalse(ai.available(self.owner))
        self.assertFalse(self.client.get('/api/health').json()['ai'])
        self.assertEqual(db.one('SELECT api_key FROM ai_settings')['api_key'], '')
        self.assertEqual(self.client.get('/api/contexts').status_code, 200)
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get(self.endpoint).status_code, 401)
        self.assertEqual(self.save().status_code, 401)

    def test_request_snapshot_rotation_and_no_fallback_after_delete(self):
        self.assertEqual(self.save().status_code, 200)
        sent = []
        def handle(request):
            sent.append((request.headers['authorization'], json.loads(request.content)['model']))
            self.assertEqual(str(request.url), 'https://provider.example/v1/chat/completions')
            if len(sent) == 1:
                self.assertEqual(self.save(1, 'rotated-private-key', 'rotated-model').status_code, 200)
            else:
                self.assertEqual(self.client.request('DELETE', self.endpoint, json={'revision': 2}).status_code, 200)
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': sample()[0].model_dump(), 'error': ''})}}],
                                           'usage': {'prompt_tokens': 12, 'completion_tokens': 34}})
        real = httpx.Client
        token = usage.scope.set((self.owner, None))
        try:
            with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real(transport=httpx.MockTransport(handle), **kw)):
                ai.generate(CurriculumDraft, 'fixture', {})
                ai.generate(CurriculumDraft, 'fixture', {})
                with self.assertRaises(ai.AIError):
                    ai.generate(CurriculumDraft, 'fixture', {})
        finally:
            usage.scope.reset(token)
        self.assertEqual(sent, [('Bearer owner-private-key', 'owner-model'), ('Bearer rotated-private-key', 'rotated-model')])
        rows = db.all('SELECT model,settings_version,provider_url FROM ai_usage ORDER BY created_at')
        self.assertEqual([(r['model'], r['settings_version']) for r in rows], [('owner-model', 1), ('rotated-model', 2)])
        self.assertTrue(all(r['provider_url'] == 'https://provider.example/v1' for r in rows))
        self.assertNotIn('private-key', json.dumps(usage.summary(self.owner)))

    def test_invalid_inputs_missing_cipher_and_corrupted_key_fail_closed(self):
        from . import ai_settings
        self.assertEqual(self.save(key='bad\nkey').status_code, 422)
        self.assertEqual(self.save(model='bad model').status_code, 422)
        with patch.dict(os.environ, {'TRAINER_AI_ENCRYPTION_KEY': '', 'TRAINER_GITHUB_ENCRYPTION_KEY': ''}):
            self.assertEqual(self.save().status_code, 503)
        self.assertEqual(self.save().status_code, 200)
        db.execute("UPDATE ai_settings SET api_key='invalid ciphertext'")
        self.assertFalse(ai.available(self.owner))
        with self.assertRaises(ai_settings.SettingsError):
            ai_settings.configuration(self.owner)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['available'])
        self.assertNotIn('invalid ciphertext', response.text)

    def test_other_owner_and_provider_failure_never_use_another_key(self):
        from . import ai_settings
        from .ai_settings_schema import AISettingsInput
        other = service.uid()
        db.execute('INSERT INTO users VALUES (?,?,?,0)', (other, 'other-user', 'fixture-no-login'))
        self.save()
        ai_settings.save(other, AISettingsInput(revision=0, api_key='other-private-key', model='other-model',
                                              provider_url='https://provider.example/v1'))
        seen = []
        def handle(request):
            seen.append((request.headers['authorization'], json.loads(request.content)['model']))
            return httpx.Response(401, text='owner-private-key other-private-key shared-test-key')
        real = httpx.Client
        with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real(transport=httpx.MockTransport(handle), **kw)):
            for owner in (self.owner, other):
                token = usage.scope.set((owner, None))
                try:
                    with self.assertRaises(ai.AIError) as error:
                        ai.generate(CurriculumDraft, 'fixture', {})
                    self.assertNotIn('private-key', str(error.exception))
                finally:
                    usage.scope.reset(token)
        self.assertEqual(seen, [('Bearer owner-private-key', 'owner-model'), ('Bearer other-private-key', 'other-model')])
        self.assertEqual(usage.summary(self.owner)['totals']['failed_calls'], 1)
        self.assertEqual(usage.summary(other)['totals']['failed_calls'], 1)
        first = db.one('SELECT api_key FROM ai_settings WHERE owner=?', (self.owner,))['api_key']
        db.execute('UPDATE ai_settings SET api_key=? WHERE owner=?', (first, other))
        self.assertFalse(ai.available(other))
        self.assertTrue(ai.available(self.owner))

    def test_queued_interpretation_records_the_connection_actually_used(self):
        from . import resources, interpretations
        from .resource_schema import ResourceInput
        from .interpretation_schema import InterpretationInput
        from .test_interpretations import BODY, DOCUMENT
        self.save()
        raw = resources.register(self.owner, ResourceInput(request_id='ai-source', kind='text', name='fixture', content=BODY))
        job, _ = interpretations.begin(self.owner, InterpretationInput(request_id='ai-job-001', resource_id=raw['id'], revision=1))
        self.assertEqual(job['model'], 'owner-model')
        self.save(1, 'rotated-key', 'rotated-model')
        real = httpx.Client
        def handle(request):
            self.assertEqual(request.headers['authorization'], 'Bearer rotated-key')
            return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'data': DOCUMENT, 'error': ''})}}]})
        with patch.object(ai.httpx, 'Client', side_effect=lambda **kw: real(transport=httpx.MockTransport(handle), **kw)):
            interpretations.generate(job['id'])
        saved = interpretations.view(self.owner, job['id'])
        self.assertEqual((saved['state'], saved['model']), ('ready', 'rotated-model'))
        record = db.one('SELECT * FROM ai_usage WHERE generation_id=?', (job['id'],))
        self.assertEqual((record['model'], record['settings_version']), ('rotated-model', 2))


if __name__ == '__main__':
    unittest.main()

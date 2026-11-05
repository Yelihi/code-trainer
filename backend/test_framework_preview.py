import unittest
from unittest.mock import patch
from . import test_app, framework_preview


class FrameworkPreviewTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def test_render_uses_isolated_runner_and_returns_markup(self):
        result = {'status': 'ok', 'exit_code': 0, 'stdout': '{"html":"<h1>Hi</h1>","css":"h1{color:red}","client":"exports.default = App;"}', 'stderr': ''}
        with patch.object(framework_preview.runner, 'run', return_value=[result]) as run:
            response = self.client.post('/api/framework-preview', json={'framework': 'react', 'code': 'export default function App() {}'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['html'], '<h1>Hi</h1>')
        self.assertEqual(response.json()['client'], 'exports.default = App;')
        self.assertEqual(response.json()['warnings'], '')
        run.assert_called_once_with('react', 'export default function App() {}', [''])

    def test_invalid_framework_and_failed_render_are_safe(self):
        self.assertEqual(self.client.post('/api/framework-preview', json={'framework': 'svelte', 'code': 'x'}).status_code, 422)
        with patch.object(framework_preview.runner, 'run', return_value=[{'status': 'ok', 'exit_code': 1, 'stderr': 'Syntax error', 'stdout': ''}]):
            response = self.client.post('/api/framework-preview', json={'framework': 'vue', 'code': '<template />'})
        self.assertEqual(response.json()['status'], 'runtime_error')
        self.assertEqual(response.json()['error'], 'Syntax error')
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.post('/api/framework-preview', json={'framework': 'react', 'code': 'x'}).status_code, 401)

    def test_malformed_runner_output_is_rejected(self):
        with patch.object(framework_preview.runner, 'run', return_value=[{'status': 'ok', 'exit_code': 0, 'stderr': '', 'stdout': 'not json'}]):
            response = self.client.post('/api/framework-preview', json={'framework': 'react', 'code': 'x'})
        self.assertEqual(response.status_code, 422)

    def test_preview_frame_has_isolated_policy_and_requires_login(self):
        response = self.client.get('/api/framework-preview-frame')
        self.assertEqual(response.status_code, 200)
        self.assertIn("connect-src 'none'", response.headers['content-security-policy'])
        self.assertEqual(response.headers['x-frame-options'], 'SAMEORIGIN')
        self.client.post('/api/logout', json={})
        self.assertEqual(self.client.get('/api/framework-preview-frame').status_code, 401)

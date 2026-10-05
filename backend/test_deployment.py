"""Deployment contracts with real JWT signatures and mocked network/Docker boundaries."""
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from . import access, db, runner, runner_api
from .api import app

IMAGE = 'sha256:' + 'a' * 64
RESULT = {'status': 'ok', 'stdout': '42\n', 'stderr': '', 'exit_code': 0}


class DeploymentTest(unittest.TestCase):
    def test_access_identity_signature_origin_and_no_local_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {'TRAINER_MODE': 'server', 'TRAINER_DB': directory + '/test.sqlite3',
                   'TRAINER_PUBLIC_ORIGIN': 'https://trainer.example.com',
                   'TRAINER_ACCESS_DOMAIN': 'test.cloudflareaccess.com', 'TRAINER_ACCESS_AUDIENCE': 'trainer-aud',
                   'TRAINER_ACCESS_SUBJECT': 'owner-sub', 'TRAINER_ACCESS_EMAIL': 'owner@example.com',
                   'TRAINER_ACCESS_USER_ID': 'original-owner'}
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            claims = {'iss': 'https://test.cloudflareaccess.com', 'aud': 'trainer-aud', 'sub': 'owner-sub',
                      'email': 'owner@example.com', 'iat': int(time.time()), 'exp': int(time.time()) + 300}

            def token(**overrides):
                return jwt.encode({**claims, **overrides}, key, algorithm='RS256', headers={'kid': 'test'})

            with patch.dict(os.environ, env), patch.object(runner, 'remote_client'), patch.object(runner, 'cleanup'), patch.object(access, 'keys') as keys:
                keys.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
                db.initialize()
                db.execute('INSERT INTO users VALUES (?,?,?,?)', ('original-owner', 'existing', 'not-a-local-password', 1))
                with TestClient(app) as client:
                    self.assertEqual(client.get('/healthz').status_code, 200)
                    denied = client.get('/api/session', headers={'cookie': 'trainer_session=old'})
                    self.assertEqual(denied.status_code, 401)
                    self.assertEqual(denied.headers['x-trainer-auth'], 'access')
                    headers = {'x-trainer-user-jwt': token(), 'origin': env['TRAINER_PUBLIC_ORIGIN']}
                    response = client.get('/api/session', headers=headers)
                    self.assertEqual(response.json()['user']['id'], 'original-owner')
                    self.assertEqual(response.json()['auth_mode'], 'access')
                    self.assertEqual(client.post('/api/auth', json={'username': 'new', 'password': 'password123'}, headers=headers).status_code, 403)
                    self.assertEqual(client.post('/api/logout', json={}, headers={'x-trainer-user-jwt': token()}).status_code, 403)
                    self.assertEqual(client.post('/api/logout', json={}, headers={**headers, 'origin': 'https://evil.example'}).status_code, 403)
                    self.assertEqual(client.post('/api/logout', json={}, headers=headers).json()['logout_url'], '/cdn-cgi/access/logout')
                    for override in ({'aud': 'resume-agent'}, {'iss': 'https://evil.example'}, {'exp': 1}, {'nbf': int(time.time()) + 1000}):
                        self.assertEqual(client.get('/api/session', headers={'x-trainer-user-jwt': token(**override)}).status_code, 401)
                    for override in ({'email': 'stranger@example.com'}, {'sub': 'different-sub'}):
                        self.assertEqual(client.get('/api/session', headers={'x-trainer-user-jwt': token(**override)}).status_code, 403)
                    forged = jwt.encode(claims, rsa.generate_private_key(public_exponent=65537, key_size=2048), algorithm='RS256')
                    self.assertEqual(client.get('/api/session', headers={'x-trainer-user-jwt': forged}).status_code, 401)
                    self.assertEqual(client.get('/api/session', headers={'x-trainer-user-jwt': jwt.encode(claims, 'x' * 64, algorithm='HS256')}).status_code, 401)
                    self.assertEqual(client.get('/api/session', headers=[('x-trainer-user-jwt', token()), ('x-trainer-user-jwt', token())]).status_code, 401)
                    keys.return_value.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError('offline')
                    self.assertEqual(client.get('/api/session', headers=headers).status_code, 401)
                with patch.dict(os.environ, {'TRAINER_ACCESS_SUBJECT': ''}):
                    with self.assertRaises(ValueError):
                        access.validate_config()
                with patch.dict(os.environ, {'TRAINER_MODE': 'typo'}):
                    with self.assertRaises(ValueError):
                        access.enabled()

    def test_broker_rejects_arbitrary_docker_control_and_unapproved_images(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'runtimes.json'
            manifest.write_text(json.dumps([IMAGE]))
            with patch.dict(os.environ, {'TRAINER_MODE': 'local', 'TRAINER_RUNNER_URL': '', 'TRAINER_RUNTIME_MANIFEST': str(manifest)}), \
                    patch.object(runner, 'pin_runtime', return_value=IMAGE), patch.object(runner, 'cleanup'), patch.object(runner, 'run', return_value=[RESULT]) as run:
                with TestClient(runner_api.app) as client:
                    body = {'language': 'python', 'code': 'print(42)', 'inputs': [''], 'image_id': IMAGE}
                    self.assertEqual(client.get('/runtime').json()['image_id'], IMAGE)
                    response = client.post('/run', json=body)
                    self.assertEqual(response.json(), {'results': [RESULT]})
                    run.assert_called_once_with('python', 'print(42)', [''], image_id=IMAGE)
                    for override in ({'image_id': 'alpine:latest'}, {'image_id': 'sha256:' + 'b' * 64}, {'mounts': ['/']}, {'command': ['sh']}, {'language': 'shell'}, {'inputs': [''] * 9}, {'code': 'x' * 64001}):
                        self.assertEqual(client.post('/run', json={**body, **override}).status_code, 422)
                    self.assertEqual(run.call_count, 1)
                    response = client.post('/run', json={**body, 'unknown_secret': 'do-not-echo'})
                    self.assertNotIn('do-not-echo', response.text)
                    self.assertEqual(client.post('/run', content=b'x' * 512001, headers={'content-type': 'application/json'}).status_code, 413)
                    self.assertEqual(client.post('/run', content='no-json').status_code, 415)

    def test_remote_client_never_falls_back_to_local_docker(self):
        with patch.dict(os.environ, {'TRAINER_MODE': 'server'}), patch.object(runner.subprocess, 'run') as command, patch.object(runner.subprocess, 'Popen') as popen:
            with self.assertRaises(runner.Unavailable):
                runner.command(['ps'])
            runner.cleanup()
            def respond(request):
                if request.url.path == '/runtime':
                    return httpx.Response(200, json={'image_id': IMAGE})
                self.assertEqual(json.loads(request.content)['image_id'], IMAGE)
                return httpx.Response(200, json={'results': [RESULT]})
            with httpx.Client(base_url='https://runner.test', transport=httpx.MockTransport(respond)) as client, patch.object(runner, 'remote_client', return_value=client):
                self.assertTrue(runner.available())
                self.assertEqual(runner.pin_runtime(), IMAGE)
                self.assertEqual(runner.run('python', 'print(42)', [''], IMAGE), [RESULT])
            with patch.object(runner, 'remote_client', side_effect=ValueError('missing cert')):
                self.assertFalse(runner.available())
                with self.assertRaises(runner.Unavailable):
                    runner.run('python', 'print(42)', [''])
            command.assert_not_called()
            popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()

"""Trust and failure boundaries for the Mac pull deployer; no external effects."""
import hashlib
import io
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

DIRECTORY = Path(__file__).parent
sys.path.insert(0, str(DIRECTORY))
import github_deploy as github
import release
import changes


class DeploymentChecks(unittest.TestCase):
    def test_poll_waits_for_workflow_metadata_without_accepting_it(self):
        deployment = {'id': 10, 'payload': {'run_id': 42, 'run_attempt': 1}}
        responses = [[deployment], [], {'status': 'queued'}, {'jobs': []}, {'sha': 'a' * 40}]
        with tempfile.TemporaryDirectory() as directory, patch.object(github, 'api', side_effect=responses), \
                patch.object(github, 'status') as status, patch.object(release, 'deploy') as deploy:
            github.poll(directory)
            status.assert_not_called()
            deploy.assert_not_called()

    def test_only_checked_current_main_run_can_deploy(self):
        sha = 'a' * 40
        deployment = {'environment': 'production', 'sha': sha, 'ref': sha,
                      'creator': {'login': 'github-actions[bot]'}, 'payload': {'run_id': 42, 'run_attempt': 2,
                      'frontend': True, 'backend': True, 'base_sha': 'b' * 40, 'force': 'auto'}}
        run = {'repository': {'full_name': github.REPOSITORY}, 'head_repository': {'full_name': github.REPOSITORY},
               'path': github.WORKFLOW, 'head_branch': 'main', 'head_sha': sha, 'event': 'push',
               'status': 'in_progress', 'id': 42, 'run_attempt': 2}
        jobs = [{'name': 'check', 'conclusion': 'success'}, {'name': 'deploy', 'status': 'in_progress'},
                {'name': 'frontend', 'conclusion': 'success'}, {'name': 'backend', 'conclusion': 'success'}]
        self.assertTrue(github.eligible(deployment, run, jobs, sha))
        for key, value in [('event', 'pull_request'), ('head_branch', 'feature'), ('head_sha', 'b' * 40),
                           ('status', 'completed'), ('id', 41), ('run_attempt', 1), ('path', 'other.yml'),
                           ('repository', {'full_name': 'other/repo'}), ('head_repository', {'full_name': 'fork/repo'})]:
            with self.subTest(key=key):
                self.assertFalse(github.eligible(deployment, {**run, key: value}, jobs, sha))
        for key, value in [('environment', 'preview'), ('sha', 'b' * 40), ('ref', 'main'),
                           ('creator', {'login': 'someone'})]:
            self.assertFalse(github.eligible({**deployment, key: value}, run, jobs, sha))
        self.assertFalse(github.eligible(deployment, run, jobs, 'b' * 40))
        self.assertFalse(github.eligible(deployment, run, [jobs[1]], sha))
        self.assertFalse(github.eligible(deployment, run, [{'name': 'check', 'conclusion': 'failure'}, jobs[1]], sha))
        self.assertFalse(github.eligible(deployment, run, [jobs[0], {'name': 'deploy', 'status': 'completed'}], sha))
        for component in ('frontend', 'backend'):
            filtered = [job for job in jobs if job['name'] != component]
            self.assertFalse(github.eligible(deployment, run, filtered, sha))
            scoped = {**deployment, 'payload': {**deployment['payload'], component: False}}
            self.assertTrue(github.eligible(scoped, run, filtered, sha))
        bad = {**deployment, 'payload': {**deployment['payload'], 'frontend': 'false'}}
        self.assertFalse(github.eligible(bad, run, jobs, sha))

    def test_changed_paths_and_manual_scope(self):
        cases = [(['frontend/src/App.tsx'], (True, False)), (['deploy/cloudflare/worker.mjs'], (True, False)),
                 (['backend/api.py', 'requirements.txt'], (False, True)), (['deploy/Dockerfile'], (False, True)),
                 (['frontend/a.ts', 'backend/a.py'], (True, True)), (['README.md', 'deploy/README.md'], (False, False)),
                 (['.github/workflows/check.yml'], (True, True)), (['deploy/release.py'], (True, True)),
                 (['unknown-config'], (True, True)), ([], (False, False))]
        for paths, expected in cases:
            self.assertEqual(changes.classify(paths), dict(zip(('frontend', 'backend'), expected)))
        self.assertEqual(changes.classify(['backend/api.py'], 'frontend'), {'frontend': True, 'backend': True})
        self.assertEqual(changes.classify([], 'backend'), {'frontend': False, 'backend': True})
        with self.assertRaises(ValueError):
            changes.classify([], 'invalid')

    def test_mac_rejects_wrong_base_or_omitted_changes(self):
        request = {'base_sha': 'a' * 40, 'force': 'auto', 'frontend': True, 'backend': False}
        with patch.object(release, 'changed_scope', return_value={'frontend': True, 'backend': True}):
            with self.assertRaises(ValueError):
                release.selected_scope('.', 'a' * 40, 'b' * 40, request)
            with self.assertRaises(ValueError):
                release.selected_scope('.', 'c' * 40, 'b' * 40, request)

    def test_git_diff_includes_skipped_commits_and_both_sides_of_renames(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), '-c', 'user.name=Test',
                                                '-c', 'user.email=test@example.invalid', *args], text=True).strip()
            def commit():
                git('add', '.'); git('commit', '-qm', 'fixture')
                return git('rev-parse', 'HEAD')
            git('init', '-q')
            (root / 'README.md').write_text('base'); base = commit()
            (root / 'frontend').mkdir(); (root / 'frontend/a.ts').write_text('frontend'); first = commit()
            (root / 'backend').mkdir(); (root / 'backend/a.py').write_text('backend'); current = commit()
            self.assertEqual(changes.scope(root, base, current), {'frontend': True, 'backend': True})
            self.assertEqual(changes.scope(root, first, current), {'frontend': False, 'backend': True})
            git('mv', 'frontend/a.ts', 'backend/moved.py'); renamed = commit()
            self.assertEqual(changes.scope(root, current, renamed), {'frontend': True, 'backend': True})
            self.assertEqual(changes.scope(root, renamed, renamed, 'frontend'), {'frontend': True, 'backend': False})

    def test_frontend_never_touches_docker_and_backend_never_publishes_worker(self):
        for frontend, backend in [(True, False), (False, True), (True, True)]:
            with self.subTest(frontend=frontend, backend=backend), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                private = root / 'config/deployment'; private.mkdir(parents=True)
                revision, base = 'a' * 40, 'b' * 40
                checkout = root / 'release' / revision; checkout.mkdir(parents=True)
                (root / 'release' / base).mkdir()
                (root / 'release/current').symlink_to(root / 'release' / base)
                config = {'protected': {}, 'node_directory': '/node/bin'}
                for name in release.PROTECTED:
                    path = checkout / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('installed')
                    config['protected'][name] = hashlib.sha256(b'installed').hexdigest()
                (private / 'cd.json').write_text(json.dumps(config))
                (private / 'wrangler.production.json').write_text(json.dumps({'assets': {}}))
                (root / 'config/compose.env').write_text('TRAINER_APP_IMAGE=old\nTRAINER_BROKER_IMAGE=old\n')
                selected = {'frontend': frontend, 'backend': backend}
                commands = []
                def execute(args, **kwargs):
                    commands.append(args)
                def output(args):
                    if 'rev-parse' in args: return revision
                    if 'status' in args: return ''
                    return 'sha256:' + 'c' * 64
                with patch.multiple(release, ROOT=root, PRIVATE=private, CONFIG=root / 'config', ENV={}), \
                        patch.object(release, 'storage'), patch.object(release, 'run', side_effect=execute), \
                        patch.object(release, 'output', side_effect=output), \
                        patch.object(release, 'selected_scope', return_value=selected), \
                        patch.object(release, 'backup') as backup, \
                        patch.object(release.urllib.request, 'urlopen', return_value=io.BytesIO(b'{"ok":true}')):
                    release.ENV['PATH'] = '/usr/bin'
                    release.deploy(revision, lambda: True, {**selected, 'base_sha': base, 'force': 'auto'})
                self.assertEqual(any(cmd[0] == 'docker' for cmd in commands), backend)
                self.assertEqual(backup.call_count, int(backend))
                self.assertEqual(any(cmd[0] == 'npm' for cmd in commands), frontend)
                self.assertEqual(any(cmd[0] == 'node' and '--dry-run' not in cmd for cmd in commands), frontend)
                if backend:
                    first_build = next(i for i, cmd in enumerate(commands) if 'build' in cmd)
                    retained = [i for i, cmd in enumerate(commands) if 'tag' in cmd]
                    self.assertEqual(len(retained), 2)
                    self.assertTrue(all(i < first_build for i in retained))
                if frontend and backend:
                    verified = next(i for i, cmd in enumerate(commands) if cmd[0] == '/usr/bin/python3')
                    published = next(i for i, cmd in enumerate(commands) if cmd[0] == 'node' and '--dry-run' not in cmd)
                    self.assertLess(verified, published)
                components = json.loads((private / 'components.json').read_text())
                self.assertEqual(components, {'frontend': revision if frontend else base, 'backend': revision if backend else base})

    def test_backup_and_migration_failure_order(self):
        for failed, expected in [(None, ['stop', 'backup', 'switch', 'verify', 'publish']),
                                 ('stop', ['stop']), ('backup', ['stop', 'backup', 'restart']),
                                 ('switch', ['stop', 'backup', 'switch']),
                                 ('verify', ['stop', 'backup', 'switch', 'verify']),
                                 ('publish', ['stop', 'backup', 'switch', 'verify', 'publish'])]:
            calls = []
            def operation(name):
                def call():
                    calls.append(name)
                    if name == failed:
                        raise RuntimeError(name)
                return call
            args = [operation(name) for name in ('stop', 'backup', 'restart', 'switch', 'verify', 'publish')]
            if failed:
                with self.assertRaises(RuntimeError):
                    release.transition(*args)
            else:
                release.transition(*args)
            self.assertEqual(calls, expected)

    def test_protected_host_files_and_immutable_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {'protected': {}}
            for name in release.PROTECTED:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('installed')
                config['protected'][name] = hashlib.sha256(b'installed').hexdigest()
            release.validate_release(root, config)
            (root / release.PROTECTED[0]).write_text('changed')
            with self.assertRaises(ValueError):
                release.validate_release(root, config)
        image = 'sha256:' + 'a' * 64
        original = 'TRAINER_APP_IMAGE=old\nTRAINER_BROKER_IMAGE=old\nPRIVATE_SETTING=keep\n'
        result = release.replace_images(original, image, image)
        self.assertIn('PRIVATE_SETTING=keep\n', result)
        self.assertEqual(result.count(image), 2)
        for content, value in [(original, 'latest'), (original + 'TRAINER_APP_IMAGE=duplicate\n', image), ('', image)]:
            with self.assertRaises(ValueError):
                release.replace_images(content, value, image)


if __name__ == '__main__':
    unittest.main()

"""Trust and failure boundaries for the Mac pull deployer; no external effects."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

DIRECTORY = Path(__file__).parent
sys.path.insert(0, str(DIRECTORY))
import github_deploy as github
import release


class DeploymentChecks(unittest.TestCase):
    def test_only_checked_current_main_run_can_deploy(self):
        sha = 'a' * 40
        deployment = {'environment': 'production', 'sha': sha, 'ref': sha,
                      'creator': {'login': 'github-actions[bot]'}, 'payload': {'run_id': 42, 'run_attempt': 2}}
        run = {'repository': {'full_name': github.REPOSITORY}, 'head_repository': {'full_name': github.REPOSITORY},
               'path': github.WORKFLOW, 'head_branch': 'main', 'head_sha': sha, 'event': 'push',
               'status': 'in_progress', 'id': 42, 'run_attempt': 2}
        jobs = [{'name': 'check', 'conclusion': 'success'}, {'name': 'deploy', 'status': 'in_progress'}]
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

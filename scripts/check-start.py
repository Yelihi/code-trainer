"""Check first-run shell branches without installing tools or touching the running app."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    project = Path(directory)
    shutil.copy(root / 'start.sh', project / 'start.sh')
    (project / '.env').write_text('AI_API_KEY=\nAI_MODEL=\n')
    (project / 'frontend').mkdir()
    binaries = project / 'bin'
    binaries.mkdir()
    stub = f'#!{sys.executable}\n' + '''import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
with open(os.environ['START_CHECK_LOG'], 'a') as log:
    log.write(json.dumps([name, *args]) + '\\n')
if name == 'node':
    sys.exit(int(os.environ.get('OLD_NODE' if args else 'BUSY_PORT', '0')))
if name == 'uv' and '-c' in args:
    print('custom-runner:check')
if name == 'docker':
    if args[:2] == ['context', 'inspect']:
        sys.exit(1)
    if args[:2] == ['image', 'inspect']:
        sys.exit(int(os.environ.get('MISSING_IMAGE', '0')))
    if args[0] == 'version':
        sys.exit(int(os.environ.get('DOCKER_DOWN', '0')))
'''
    for tool in ('node', 'npm', 'uv', 'docker', 'sleep', 'open'):
        target = binaries / tool
        target.write_text(stub)
        target.chmod(0o700)
    log = project / 'calls.jsonl'

    def run(*args, **settings):
        log.write_text('')
        env = {**os.environ, 'PATH': str(binaries) + ':/usr/bin:/bin', 'START_CHECK_LOG': str(log), **settings}
        env.pop('DOCKER_CONTEXT', None)
        result = subprocess.run(['/bin/bash', str(project / 'start.sh'), *args], env=env, capture_output=True, text=True)
        return result, [json.loads(line) for line in log.read_text().splitlines()]

    result, calls = run(MISSING_IMAGE='1')
    assert result.returncode == 0, result.stderr
    assert ['uv', 'venv', '--python', '3.12', '.venv'] in calls
    assert ['docker', 'build', '-t', 'custom-runner:check', 'sandbox'] in calls
    assert ['npm', 'ci'] in calls and ['npm', 'run', 'build'] in calls
    assert calls[-1][-3:] == ['--no-access-log', '--workers', '1']
    result, calls = run()
    assert result.returncode == 0 and not any(c[:2] == ['docker', 'build'] for c in calls)
    result, calls = run('--setup')
    assert result.returncode == 0 and ['docker', 'build', '-t', 'custom-runner:check', 'sandbox'] in calls
    for settings, message in (({'OLD_NODE': '1'}, 'Node.js 24'), ({'BUSY_PORT': '1'}, ''), ({'DOCKER_DOWN': '1'}, 'Docker 엔진에 연결하지 못했습니다')):
        result, calls = run(**settings)
        assert result.returncode != 0 and message in result.stdout
        assert not any('-m' in c and 'uvicorn' in c for c in calls)
    (project / '.env').unlink()
    result, calls = run()
    assert result.returncode != 0 and 'cp .env.example .env' in result.stdout
    assert not any(c[0] == 'uv' for c in calls)
    result, calls = run('--help')
    assert result.returncode == 0 and not calls
    result, calls = run('--unknown')
    assert result.returncode != 0 and not calls
print('PASS: first-run image build, repeat launch, forced rebuild, prerequisite failures and help.')

with tempfile.TemporaryDirectory() as directory:
    project = Path(directory)
    (project / 'backend').mkdir()
    shutil.copy(root / 'backend/dev.sh', project / 'backend/dev.sh')
    (project / '.env').write_text('AI_API_KEY=\nAI_MODEL=\n')
    binaries = project / '.venv/bin'
    binaries.mkdir(parents=True)
    log = project / 'calls.jsonl'
    stub = f'#!{sys.executable}\n' + '''import json, os, pathlib, subprocess, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ['START_CHECK_LOG'], 'a') as log:
    log.write(json.dumps({'tool': name, 'args': sys.argv[1:], 'cwd': os.getcwd(),
        'db': os.environ.get('TRAINER_DB'), 'env': os.environ.get('UV_ENV_FILE'),
        'docker': os.environ.get('DOCKER_CONTEXT'), 'host': os.environ.get('DOCKER_HOST'),
        'config': os.environ.get('DOCKER_CONFIG'), 'mode': os.environ.get('TRAINER_MODE'),
        'runner': os.environ.get('TRAINER_RUNNER_URL'), 'image': os.environ.get('TRAINER_IMAGE'),
        'tls': os.environ.get('DOCKER_TLS_VERIFY'),
        'shared_ai': os.environ.get('AI_API_KEY') == 'test-shared-key'}) + '\\n')
if name == 'python' and sys.argv[1:] == ['-']:
    sys.exit(int(os.environ.get('BUSY_PORT', '0')))
if name == 'docker':
    if sys.argv[1] == 'info': sys.exit(int(os.environ.get('MISSING_ENGINE', '0')))
    if sys.argv[1:3] == ['image', 'inspect']: sys.exit(int(os.environ.get('MISSING_IMAGE', '0')))
    if sys.argv[1] == 'build': sys.exit(int(os.environ.get('BUILD_FAIL', '0')))
if name == 'colima': sys.exit(int(os.environ.get('COLIMA_FAIL', '0')))
if name == 'uv':
    # Simulate conflicting deployment values loaded by uv from dotenv before env runs.
    child = {**os.environ, 'TRAINER_MODE': 'server', 'TRAINER_DB': '/production.sqlite3',
             'TRAINER_RUNNER_URL': 'https://production.invalid:18443', 'TRAINER_IMAGE': 'production-image',
             'DOCKER_CONTEXT': 'colima-code-trainer-runner', 'DOCKER_HOST': 'unix:///production.sock',
             'DOCKER_CONFIG': '/production/docker', 'DOCKER_TLS_VERIFY': '1', 'AI_API_KEY': 'test-shared-key'}
    sys.exit(subprocess.call(sys.argv[3:], env=child))
'''
    for tool in ('python', 'uv', 'docker', 'colima'):
        target = binaries / tool
        target.write_text(stub)
        target.chmod(0o700)

    def run_dev(*args, cwd=None, **settings):
        log.write_text('')
        env = {**os.environ, 'PATH': str(binaries) + ':/usr/bin:/bin', 'START_CHECK_LOG': str(log)}
        for key in ('TRAINER_DB', 'UV_ENV_FILE', 'DOCKER_CONTEXT', 'BUSY_PORT'):
            env.pop(key, None)
        env.update(settings)
        result = subprocess.run(['/bin/bash', str(project / 'backend/dev.sh'), *args],
                                cwd=cwd or project / 'backend', env=env, capture_output=True, text=True)
        return result, [json.loads(line) for line in log.read_text().splitlines()]

    result, calls = run_dev(MISSING_ENGINE='1', MISSING_IMAGE='1')
    assert result.returncode == 0, result.stderr
    launch = calls[-1]
    assert launch['tool'] == 'python'
    assert launch['cwd'] == str(project.resolve())
    assert Path(launch['env']).resolve() == project.resolve() / '.env'
    assert Path(launch['db']).resolve() == project.resolve() / 'data/dev/trainer.sqlite3'
    assert launch['docker'] is None and launch['tls'] is None
    assert launch['host'] == 'unix://' + str(Path.home() / '.colima/code-trainer-dev/docker.sock')
    assert Path(launch['config']).resolve() == project.resolve() / 'data/dev/docker-cli'
    assert launch['mode'] == 'local' and launch['runner'] == ''
    assert launch['image'] == 'code-trainer-runner:dev' and launch['shared_ai']
    assert launch['args'] == ['-m', 'uvicorn', 'backend.api:app',
                             '--host', '127.0.0.1', '--port', '8011', '--no-access-log', '--reload', '--reload-dir', 'backend']
    start = next(c for c in calls if c['tool'] == 'colima')
    assert start['args'][:2] == ['start', 'code-trainer-dev'] and '--activate=false' in start['args']
    assert any(c['args'] == ['build', '-t', 'code-trainer-runner:dev', 'sandbox'] for c in calls)
    for call in (c for c in calls if c['tool'] == 'docker'):
        assert call['host'] == launch['host'] and call['config'] == launch['config'] and call['docker'] is None
    result, calls = run_dev(cwd=project, TRAINER_DB='/production.sqlite3', DOCKER_CONTEXT='colima-code-trainer-runner',
                           DOCKER_HOST='unix:///production.sock', DOCKER_CONFIG='/production/docker', COLIMA_HOME='/production/vm')
    assert result.returncode == 0
    assert calls[-1]['db'] == launch['db'] and calls[-1]['host'] == launch['host'] and calls[-1]['docker'] is None
    assert all(c['host'] == launch['host'] and c['config'] == launch['config'] and c['docker'] is None
               for c in calls if c['tool'] == 'docker')
    assert not any(c['tool'] == 'colima' or c['args'][0] == 'build' for c in calls)
    for settings in ({'MISSING_ENGINE': '1', 'COLIMA_FAIL': '1'}, {'MISSING_IMAGE': '1', 'BUILD_FAIL': '1'}):
        result, calls = run_dev(**settings)
        assert result.returncode != 0 and not any(c['tool'] == 'uv' for c in calls)
    result, calls = run_dev(BUSY_PORT='1')
    assert result.returncode != 0 and not any(c['tool'] == 'uv' for c in calls)
    (project / '.env').unlink()
    result, calls = run_dev()
    assert result.returncode != 0 and 'cp .env.example .env' in result.stderr and not calls
    (binaries / 'python').unlink()
    result, calls = run_dev()
    assert result.returncode != 0 and 'uv venv' in result.stderr and not calls
    result, calls = run_dev('--help')
    assert result.returncode == 0 and not calls
    result, calls = run_dev('--unknown')
    assert result.returncode != 0 and not calls
print('PASS: dev API, DB/logs, Docker and dotenv isolation, shared AI setting, setup failures and port guard.')

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

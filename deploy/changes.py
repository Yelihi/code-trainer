"""One path classifier shared by GitHub checks and the installed Mac deployer."""
import json
import os
from pathlib import Path
import re
import subprocess

FORCES = ('auto', 'frontend', 'backend', 'all')


def classify(paths, force='auto'):
    if force not in FORCES:
        raise ValueError('Invalid deployment scope')
    frontend, backend = force in ('frontend', 'all'), force in ('backend', 'all')
    for path in paths:
        if path.endswith('.md') or path.startswith('docs/architecture/') or path == '.github/workflows/pages.yml':
            continue
        if path.startswith(('frontend/', 'deploy/cloudflare/')):
            frontend = True
        elif path.startswith(('backend/', 'scripts/', 'sandbox/')) or path in (
                'requirements.txt', '.dockerignore', 'deploy/Dockerfile', 'deploy/requirements.txt', 'start.sh'):
            backend = True
        else:
            # Deployment plumbing, workflows and unknown paths may affect both components.
            frontend = backend = True
    return {'frontend': frontend, 'backend': backend}


def scope(checkout, base, revision, force='auto'):
    if not re.fullmatch(r'[0-9a-f]{40}', revision) or (base and not re.fullmatch(r'[0-9a-f]{40}', base)):
        raise ValueError('Expected full commit SHAs')
    if not base:
        return classify([], 'all')
    paths = subprocess.check_output(['git', '-C', str(checkout), 'diff', '--no-renames', '--name-only',
                                     '-z', base, revision]).decode().split('\0')
    return classify([path for path in paths if path], force)


def plan():
    from github_deploy import api
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    revision = os.environ['GITHUB_SHA']
    force = event.get('inputs', {}).get('scope', 'auto') if os.environ['GITHUB_EVENT_NAME'] == 'workflow_dispatch' else 'auto'
    base = ''
    if os.environ['GITHUB_EVENT_NAME'] == 'pull_request':
        base = subprocess.check_output(['git', 'merge-base', event['pull_request']['base']['sha'], revision], text=True).strip()
    else:
        for deployment in api('deployments?environment=production&per_page=100'):
            states = api(f'deployments/{deployment["id"]}/statuses?per_page=1')
            if states and states[0]['state'] == 'success':
                base = deployment['sha']
                break
    result = {**scope('.', base, revision, force), 'base_sha': base, 'force': force}
    with open(os.environ['GITHUB_OUTPUT'], 'a') as output:
        for key, value in result.items():
            output.write(f'{key}={str(value).lower() if isinstance(value, bool) else value}\n')
    print(json.dumps(result))


if __name__ == '__main__':
    plan()

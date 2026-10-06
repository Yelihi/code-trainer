"""Installed Mac deployer: checked main -> immutable images -> backup -> backend -> Worker."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.request

from host import CONFIG, ENV, ROOT, backup, storage
from changes import scope as changed_scope

APP = ['docker', '--context', 'colima-code-trainer-app']
RUNNER = ['docker', '--context', 'colima-code-trainer-runner']
PRIVATE = CONFIG / 'deployment'
PROTECTED = ('deploy/host.py', 'deploy/service-launcher.swift', 'deploy/runner-network.sb',
             'deploy/runner-lima-override.yaml', 'deploy/app.compose.yaml', 'deploy/runner.compose.yaml',
             'sandbox/Dockerfile', 'deploy/github_deploy.py', 'deploy/release.py', 'deploy/check-host.py', 'deploy/changes.py', 'deploy/monitor.py')


def run(args, **kwargs):
    print('Running:', args[0], args[1] if len(args) > 1 else '', flush=True)
    return subprocess.run(args, env=ENV, check=True, timeout=1200, **kwargs)


def output(args):
    return run(args, capture_output=True, text=True).stdout.strip()


def write_private(path, content):
    temporary = path.with_suffix(path.suffix + '.next')
    with open(os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'w') as stream:
        stream.write(content)
    os.replace(temporary, path)


def replace_images(content, app, broker):
    for key, value in [('TRAINER_APP_IMAGE', app), ('TRAINER_BROKER_IMAGE', broker)]:
        if not re.fullmatch(r'sha256:[0-9a-f]{64}', value):
            raise ValueError('Expected immutable image ID')
        pattern = rf'^{key}=.*$'
        if len(re.findall(pattern, content, re.M)) != 1:
            raise ValueError('Missing or duplicate image setting')
        content = re.sub(pattern, key + '=' + value, content, flags=re.M)
    return content


def validate_release(release, config):
    for name in PROTECTED:
        path = release / name
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != config['protected'][name]:
            raise ValueError('Host/runtime configuration requires manual installation: ' + name)


def transition(stop, save, restart_old, switch, verify, publish):
    # Only a failed pre-migration backup may restart the old app automatically.
    stop()
    try:
        save()
    except BaseException:
        restart_old()
        raise
    switch()
    verify()
    publish()


def selected_scope(checkout, base, revision, requested):
    if requested['base_sha'] != base:
        raise ValueError('GitHub and Mac deployment baselines differ; inspect before retrying')
    selected = changed_scope(checkout, base, revision, requested['force'])
    if selected != {name: requested[name] for name in ('frontend', 'backend')} or not any(selected.values()):
        raise ValueError('Requested scope does not match changes since the last successful deployment')
    return selected


def deploy(revision, still_authorized, requested):
    os.umask(0o077)
    storage()
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Expected a full commit SHA')
    config = json.loads((PRIVATE / 'cd.json').read_text())
    ENV['PATH'] = config['node_directory'] + ':' + ENV['PATH']
    ENV['NPM_CONFIG_CACHE'] = str(ROOT / 'npm-cache')
    ENV['WRANGLER_SEND_METRICS'] = 'false'
    if shutil.disk_usage(ROOT).free < 10 * 1024**3:
        raise RuntimeError('At least 10 GiB free on external SSD required')
    releases = ROOT / 'release'
    releases.mkdir(exist_ok=True, mode=0o700)
    checkout = ROOT / 'deployment-checkout'
    repo = 'https://github.com/Yelihi/code-trainer.git'
    if not checkout.exists():
        run(['git', 'clone', '--bare', repo, str(checkout)])
    run(['git', '-C', str(checkout), 'fetch', repo, 'main'])
    if output(['git', '-C', str(checkout), 'rev-parse', 'FETCH_HEAD']) != revision or not still_authorized():
        raise ValueError('Main or its workflow changed before release preparation')
    release = releases / revision
    if not release.exists():
        run(['git', '-C', str(checkout), 'worktree', 'add', '--detach', str(release), revision])
    if output(['git', '-C', str(release), 'rev-parse', 'HEAD']) != revision or output(
            ['git', '-C', str(release), 'status', '--porcelain', '--untracked-files=no']):
        raise ValueError('Release checkout has changed')
    validate_release(release, config)
    base = (releases / 'current').resolve(strict=True).name if (releases / 'current').exists() else ''
    selected = selected_scope(checkout, base, revision, requested)
    components_path = PRIVATE / 'components.json'
    components = json.loads(components_path.read_text()) if components_path.exists() else {'frontend': base, 'backend': base}
    print('Selected components:', selected, 'since', base, flush=True)
    if selected['frontend']:
        for package in ('frontend', 'deploy/cloudflare'):
            run(['npm', '--prefix', str(release / package), 'ci'])
        run(['npm', '--prefix', str(release / 'frontend'), 'run', 'build'])
        worker_config = json.loads((PRIVATE / 'wrangler.production.json').read_text())
        worker_config['main'] = str(release / 'deploy/cloudflare/worker.mjs')
        worker_config['assets']['directory'] = str(release / 'frontend/dist')
        worker_path = PRIVATE / 'wrangler.candidate.json'
        write_private(worker_path, json.dumps(worker_config, indent=2) + '\n')
        wrangler = ['node', str(release / 'deploy/cloudflare/node_modules/wrangler/bin/wrangler.js'),
                    'deploy', '--config', str(worker_path)]
        run([*wrangler, '--dry-run'])
    ids = {}
    if selected['backend']:
        # Rebuilding an existing SHA tag can evict an untagged containerd image index.
        # Preserve the running images and their exact archives BEFORE replacing tags.
        for docker, name in [(APP, 'app'), (RUNNER, 'broker')]:
            current_image = output([*docker, 'inspect', 'code-trainer-' + name, '--format', '{{.Image}}'])
            run([*docker, 'image', 'tag', current_image, 'code-trainer-' + name + ':retained-' + current_image[7:]])
            retained = ROOT / 'images' / ('retained-' + name + '-' + current_image[7:] + '.tar')
            if not retained.exists():
                run([*docker, 'image', 'save', '-o', str(retained), current_image])
        # Build in the app VM, which has Internet. The runner VM remains egress-blocked.
        for target in ('app', 'runner'):
            tag = 'code-trainer-' + target + ':' + revision
            run([*APP, 'build', '--target', target, '-f', str(release / 'deploy/Dockerfile'), '-t', tag, str(release)])
            ids[target] = output([*APP, 'image', 'inspect', tag, '--format', '{{.Id}}'])
            archive = ROOT / 'images' / (target + '-' + revision + '.tar')
            run([*APP, 'image', 'save', '-o', str(archive), ids[target]])
            if target == 'runner':
                run([*RUNNER, 'image', 'load', '-i', str(archive)])
        run([*APP, 'run', '--rm', '--network', 'none', '--entrypoint', 'python', ids['app'], '-c',
             "import pathlib,shutil,backend.api; assert not shutil.which('docker'); assert not pathlib.Path('/var/run/docker.sock').exists()"])
        compose_path = CONFIG / 'compose.env'
        previous = compose_path.read_text()
        candidate = replace_images(previous, ids['app'], ids['runner'])
        old_image = output([*APP, 'inspect', 'code-trainer-app', '--format', '{{.Image}}'])
    # Recheck after slow builds, immediately before any interruption of production.
    if not still_authorized():
        raise ValueError('Main or its workflow changed before deployment')
    if selected['backend']:
        write_private(PRIVATE / 'compose.previous.env', previous)
    state = {'sha': revision, 'scope': selected, 'base_sha': base, 'phase': 'prepared'}
    if selected['backend']:
        state.update(app_image=ids['app'], broker_image=ids['runner'])

    def record_component(name):
        components[name] = revision
        write_private(components_path, json.dumps(components, indent=2) + '\n')
        next_link = releases / ('.' + name + '-next')
        next_link.unlink(missing_ok=True)
        next_link.symlink_to(release, target_is_directory=True)
        os.replace(next_link, releases / ('current-' + name))

    def phase(name):
        state['phase'] = name
        write_private(PRIVATE / 'release-state.json', json.dumps(state, indent=2) + '\n')

    def switch():
        phase('switching-backend')
        write_private(compose_path, candidate)
        for docker, name in [(RUNNER, 'runner'), (APP, 'app')]:
            run([*docker, 'compose', '--env-file', str(compose_path), '-p', 'code-trainer-' + name,
                 '-f', str(release / ('deploy/' + name + '.compose.yaml')), 'up', '-d'])

    def verify():
        phase('checking-backend')
        for attempt in range(30):
            try:
                if json.load(urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=2)) == {'ok': True}:
                    break
            except (OSError, ValueError):
                pass
            time.sleep(2)
        else:
            run([*APP, 'stop', '--time', '120', 'code-trainer-app'])
            raise RuntimeError('New backend did not become healthy')
        try:
            run(['/usr/bin/python3', str(PRIVATE / 'check-host.py')])
        except BaseException:
            run([*APP, 'stop', '--time', '120', 'code-trainer-app'])
            raise

        record_component('backend')

    def publish():
        if not selected['frontend']:
            return
        phase('publishing-worker')
        run(wrangler)
        write_private(PRIVATE / 'wrangler.production.json', worker_path.read_text())
        record_component('frontend')

    if selected['backend']:
        phase('stopping-app')
        transition(lambda: run([*APP, 'stop', '--time', '120', 'code-trainer-app']),
                   lambda: backup(stopped_image=old_image),
                   lambda: run([*APP, 'start', 'code-trainer-app']), switch, verify, publish)
    else:
        publish()
    next_link = releases / '.current-next'
    next_link.unlink(missing_ok=True)
    next_link.symlink_to(release, target_is_directory=True)
    os.replace(next_link, releases / 'current')
    phase('complete')
    print('Deployed selected components from', revision, selected, flush=True)

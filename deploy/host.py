"""Mac host jobs. Keep this file and runner-network.sb in the private configuration directory."""
import fcntl
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import uuid

ROOT = Path('/Volumes/Storage2TB/server/code-trainer')
CONFIG = Path.home() / '.config/code-trainer'
APP_HOME = ROOT / 'vm'
RUNNER_HOME = ROOT / 'rvm'
SSH = RUNNER_HOME / '_lima/colima-code-trainer-runner/ssh.config'
ENV = {**os.environ, 'PATH': '/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin'}


def run(args, **kwargs):
    return subprocess.run(args, check=True, env=ENV, **kwargs)


def storage():
    info = plistlib.loads(run(['diskutil', 'info', '-plist', '/Volumes/Storage2TB'], capture_output=True).stdout)
    expected = (CONFIG / 'volume-uuid').read_text().strip()
    if not os.path.ismount('/Volumes/Storage2TB') or info.get('VolumeUUID') != expected or info.get('MountPoint') != '/Volumes/Storage2TB':
        raise RuntimeError('Expected external SSD is not mounted')
    if (ROOT / '.volume-uuid').read_text().strip() != expected:
        raise RuntimeError('Server storage marker does not match')


def start_runner():
    # These flags are required on EVERY boot; never run the production runner directly.
    # A previously enabled second NIC is sticky in Colima. Refuse that configuration.
    for path in (RUNNER_HOME / 'code-trainer-runner/colima.yaml', RUNNER_HOME / '_lima/colima-code-trainer-runner/colima.yaml'):
        if '  address: true' in path.read_text():
            raise RuntimeError('Runner must not have a VZ NAT or bridged interface')
    if (RUNNER_HOME / '_lima/_config/override.yaml').read_text() != Path(__file__).with_name('runner-lima-override.yaml').read_text():
        raise RuntimeError('Runner automatic port forwarding must be disabled')
    environment = {**ENV, 'COLIMA_HOME': str(RUNNER_HOME)}
    subprocess.run(['/usr/bin/sandbox-exec', '-f', str(Path(__file__).with_name('runner-network.sb')),
                    '/opt/homebrew/bin/colima', 'start', 'code-trainer-runner',
                    '--network-address=false', '--gateway-address', '192.168.7.2',
                    '--port-forwarder', 'none', '--ssh-port', '56222', '--mount', 'none',
                    '--ssh-agent=false', '--activate=false', '--binfmt=false', '--foreground'], env=environment, check=True)


def forward():
    # This process owns no Docker socket. The loopback listener carries end-to-end mTLS.
    args = ['/usr/bin/ssh', '-F', str(SSH), '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
            '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3',
            '-N', '-L', '127.0.0.1:18443:127.0.0.1:8443', 'lima-colima-code-trainer-runner']
    os.execve(args[0], args, ENV)


def backup(stopped_image=None):
    with (CONFIG / 'backup.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        repository = Path.home() / 'Library/Application Support/code-trainer-backup/restic'
        if shutil.disk_usage(repository.parent).free < 5 * 1024**3:
            raise RuntimeError('Less than 5 GiB free on backup disk')
        stage = ROOT / 'backup-staging' / ('backup-' + uuid.uuid4().hex)
        stage.mkdir(mode=0o700)
        remote = '/tmp/' + stage.name + '.sqlite3'
        docker = ['docker', '--context', 'colima-code-trainer-app']
        container = 'code-trainer-app'
        if stopped_image:
            # The old image reads the stopped app's DB; no new-code migration runs before backup.
            container = stage.name
            run([*docker, 'run', '-d', '--name', container, '--network', 'none', '--read-only',
                 '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
                 # SQLite mode=ro still needs to create WAL shared-memory bookkeeping after stop.
                 '--mount', 'type=volume,src=code-trainer-data,dst=/data',
                 '--tmpfs', '/tmp:rw,noexec,nosuid,size=256m',
                 '--entrypoint', 'sleep', stopped_image, '600'])
        try:
            run([*docker, 'exec', container, 'python', '/app/scripts/backup.py', remote])
            destination = stage / 'trainer.sqlite3'
            with open(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as out:
                run([*docker, 'exec', container, 'python', '-c',
                     'import shutil,sys; shutil.copyfileobj(open(' + repr(remote) + ',"rb"),sys.stdout.buffer)'], stdout=out)
        finally:
            if stopped_image:
                run([*docker, 'rm', '-f', container])
            else:
                run([*docker, 'exec', container, 'python', '-c',
                     'from pathlib import Path; Path(' + repr(remote) + ').unlink(missing_ok=True)'])
        restic = ['restic', '--repo', str(repository), '--password-file', str(CONFIG / 'restic-password')]
        # Stable archive paths let restic deduplicate runtime and release images.
        run([*restic, 'backup', '--tag', 'code-trainer', str(stage), str(ROOT / 'images'),
             str(ROOT / 'runtime-manifest'), str(CONFIG / 'server.env'), str(CONFIG / 'compose.env'),
             str(CONFIG / 'tls-isolated'), str(CONFIG / 'volume-uuid'), str(CONFIG / 'deployment')])
        run([*restic, 'forget', '--tag', 'code-trainer', '--group-by', 'host,tags',
             '--keep-daily', '7', '--keep-weekly', '4', '--keep-monthly', '3', '--prune'])
        shutil.rmtree(stage)  # Only this job's successfully encrypted staging copy.
        (CONFIG / 'last-backup.json').write_text(json.dumps({'snapshot': 'latest', 'status': 'ok',
                                                          'completed_at': datetime.now(timezone.utc).isoformat()}))


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('runner', 'app', 'forward', 'backup', 'check-storage'):
        raise SystemExit('Usage: host.py runner|app|forward|backup|check-storage')
    storage()
    if sys.argv[1] == 'runner':
        start_runner()
    elif sys.argv[1] == 'app':
        subprocess.run(['colima', 'start', 'code-trainer-app', '--mount', 'none',
                        '--ssh-agent=false', '--activate=false', '--foreground'], env={**ENV, 'COLIMA_HOME': str(APP_HOME)}, check=True)
    elif sys.argv[1] == 'forward':
        forward()
    elif sys.argv[1] == 'backup':
        backup()

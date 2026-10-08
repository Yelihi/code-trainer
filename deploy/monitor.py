"""Collect non-secret host facts and deliver them to the app's data volume."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile
import urllib.request

CONFIG = Path.home() / '.config/code-trainer'
ROOT = Path('/Volumes/Storage2TB/server/code-trainer')


def command(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, timeout=20, **kwargs)


def certificate(context, container, path, name):
    # Read the certificate actually mounted in the running container, never its key.
    try:
        pem = command(['docker', '--context', context, 'exec', container, 'cat', path]).stdout
        with tempfile.NamedTemporaryFile() as file:
            file.write(pem)
            file.flush()
            expiry = ssl.cert_time_to_seconds(ssl._ssl._test_decode_cert(file.name)['notAfter'])
        return {'name': name, 'expires_at': datetime.fromtimestamp(expiry, timezone.utc).isoformat(),
                'days_left': int((expiry - datetime.now(timezone.utc).timestamp()) // 86400)}
    except (OSError, ValueError, KeyError, ssl.SSLError, subprocess.SubprocessError):
        return {'name': name, 'expires_at': None, 'days_left': None}


def services():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8010/healthz', timeout=3) as response:
            api = json.load(response) == {'ok': True}
    except (OSError, ValueError):
        api = False
    try:
        probe = "from backend import runner; print('ok' if runner.available() else 'failed')"
        runner = command(['docker', '--context', 'colima-code-trainer-app', 'exec', 'code-trainer-app',
                          'python', '-c', probe]).stdout.strip() == b'ok'
    except (OSError, subprocess.SubprocessError):
        runner = False
    return {'api': api, 'runner': runner}


def collect():
    try:
        backup = json.loads((CONFIG / 'last-backup.json').read_text())
        backup_at = backup['completed_at'] if backup.get('status') == 'ok' else None
    except (OSError, ValueError, KeyError):
        backup_at = None
    return {'collected_at': datetime.now(timezone.utc).isoformat(), 'backup_at': backup_at, 'services': services(),
            'internal_free_gib': round(shutil.disk_usage(Path.home()).free / 1024**3, 2),
            'external_free_gib': round(shutil.disk_usage(ROOT).free / 1024**3, 2),
            'certificates': [certificate('colima-code-trainer-app', 'code-trainer-app', '/tls/app.crt', '앱 연결'),
                             certificate('colima-code-trainer-runner', 'code-trainer-broker', '/tls/runner.crt', '실행기 연결')],
            'checks': {'full_reboot': '미검증', 'off_device_recovery': '미준비'}}


def main():
    from host import storage
    storage()
    snapshot = collect()
    payload = json.dumps(snapshot, ensure_ascii=False).encode()
    # Keep the result on the Mac even when the app cannot accept the snapshot.
    local = CONFIG / 'monitor-status.json'
    temporary = local.with_suffix('.next')
    temporary.write_bytes(payload)
    temporary.chmod(0o600)
    os.replace(temporary, local)
    print(json.dumps({'collected_at': snapshot['collected_at'], 'services': snapshot['services']}, ensure_ascii=False), flush=True)
    # Host pushes a bounded status document; no Docker socket or new credentials in FastAPI.
    writer = "import os,sys; from pathlib import Path; p=Path('/data/operations.json'); t=p.with_suffix('.next'); t.write_bytes(sys.stdin.buffer.read(16384)); t.chmod(0o600); os.replace(t,p)"
    command(['docker', '--context', 'colima-code-trainer-app', 'exec', '-i', 'code-trainer-app', 'python', '-c', writer], input=payload)


if __name__ == '__main__':
    main()

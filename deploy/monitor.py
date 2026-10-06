"""Collect non-secret host facts and deliver them to the app's data volume."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import ssl
import subprocess
import tempfile

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


def collect():
    try:
        backup = json.loads((CONFIG / 'last-backup.json').read_text())
        backup_at = backup['completed_at'] if backup.get('status') == 'ok' else None
    except (OSError, ValueError, KeyError):
        backup_at = None
    return {'collected_at': datetime.now(timezone.utc).isoformat(), 'backup_at': backup_at,
            'internal_free_gib': round(shutil.disk_usage(Path.home()).free / 1024**3, 2),
            'external_free_gib': round(shutil.disk_usage(ROOT).free / 1024**3, 2),
            'certificates': [certificate('colima-code-trainer-app', 'code-trainer-app', '/tls/app.crt', '앱 연결'),
                             certificate('colima-code-trainer-runner', 'code-trainer-broker', '/tls/runner.crt', '실행기 연결')],
            'checks': {'full_reboot': '미검증', 'off_device_recovery': '미준비'}}


def main():
    from host import storage
    storage()
    payload = json.dumps(collect(), ensure_ascii=False).encode()
    # Host pushes a bounded status document; no Docker socket or new credentials in FastAPI.
    writer = "import os,sys; from pathlib import Path; p=Path('/data/operations.json'); t=p.with_suffix('.next'); t.write_bytes(sys.stdin.buffer.read(16384)); t.chmod(0o600); os.replace(t,p)"
    command(['docker', '--context', 'colima-code-trainer-app', 'exec', '-i', 'code-trainer-app', 'python', '-c', writer], input=payload)


if __name__ == '__main__':
    main()

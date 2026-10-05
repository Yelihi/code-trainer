"""Import a prepared directory into a NEW/EMPTY VM volume, without host folder sharing."""
import argparse
from pathlib import Path
import re
import sqlite3
import subprocess

ROLES = {
    'data': ('code-trainer-data', 10001, {'trainer.sqlite3'}),
    'app-tls': ('code-trainer-app-tls', 10001, {'app.key', 'app.crt', 'server-ca.crt'}),
    'runner-tls': ('code-trainer-runner-tls', 0, {'runner.key', 'runner.crt', 'client-ca.crt'}),
    'runtimes': ('code-trainer-runtimes', 0, {'runtimes.json'}),
}


def validate_source(source, role):
    source = Path(source).resolve()
    expected = ROLES[role][2]
    if not source.is_dir() or {p.name for p in source.iterdir()} != expected:
        raise ValueError('Source must contain exactly: ' + ', '.join(sorted(expected)))
    if any(p.is_symlink() or not p.is_file() for p in source.iterdir()):
        raise ValueError('Only regular files are allowed')
    if role == 'data':
        with sqlite3.connect((source / 'trainer.sqlite3').as_uri() + '?mode=ro', uri=True) as connection:
            if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise ValueError('Database integrity check failed')
            if not connection.execute('SELECT id FROM users LIMIT 1').fetchone():
                raise ValueError('Create the local owner before importing')
    elif role == 'runtimes':
        import json
        values = json.loads((source / 'runtimes.json').read_text())
        if not isinstance(values, list) or not values or any(not isinstance(v, str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', v) for v in values):
            raise ValueError('Runtime manifest must contain approved image IDs')
    return source


def install(context, image, role, source, volume_name=None):
    if context not in ('colima-code-trainer-app', 'colima-code-trainer-runner'):
        raise ValueError('Use one of the two dedicated production contexts')
    if (role in ('data', 'app-tls')) != (context == 'colima-code-trainer-app'):
        raise ValueError('This volume belongs in the other VM')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('Use the inspected helper image ID')
    source = validate_source(source, role)
    volume, uid, _ = ROLES[role]
    if volume_name:
        if not re.fullmatch(re.escape(volume) + r'-[a-z0-9-]+', volume_name):
            raise ValueError('A replacement volume must use the original name plus a lowercase suffix')
        volume = volume_name
    docker = ['docker', '--context', context]

    def run(*args):
        return subprocess.run([*docker, *args], check=True, capture_output=True, text=True).stdout.strip()

    run('volume', 'create', volume)
    mount = 'type=volume,src=' + volume + ',dst=/destination'
    run('run', '--rm', '--network', 'none', '--user', '0:0', '--mount', mount, '--entrypoint', 'python', image,
        '-c', "from pathlib import Path; assert not list(Path('/destination').iterdir()), 'Refusing to overwrite existing volume'")
    helper = run('create', '--network', 'none', '--user', '0:0', '--mount', mount, '--entrypoint', 'python', image,
                 '-c', f"from pathlib import Path; import os; p=Path('/destination'); [(os.chown(v,{uid},{uid}), v.chmod(0o700 if v.is_dir() else 0o600)) for v in [p,*p.iterdir()]]")
    try:
        run('cp', str(source) + '/.', helper + ':/destination')
        run('start', '-a', helper)
    finally:
        run('rm', '-f', helper)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('context')
    parser.add_argument('image')
    parser.add_argument('role', choices=ROLES)
    parser.add_argument('source', type=Path)
    parser.add_argument('--volume', help='New suffixed volume name for restore or certificate rotation')
    args = parser.parse_args()
    install(args.context, args.image, args.role, args.source, args.volume)
    print('Imported into a dedicated VM volume; existing nonempty volumes were not overwritten.')

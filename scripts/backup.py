"""Create a consistent SQLite backup without stopping the app."""
import argparse
import os
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('destination', type=Path)
args = parser.parse_args()
source = Path(os.environ.get('TRAINER_DB', 'data/trainer.sqlite3')).resolve()
if not source.exists():
    parser.error('No database exists yet')
if args.destination.exists():
    parser.error('Destination exists; choose a new backup filename')
os.close(os.open(args.destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
with sqlite3.connect(f'{source.as_uri()}?mode=ro', uri=True) as live:
    with sqlite3.connect(args.destination) as target:
        live.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise SystemExit('Backup integrity check failed; do not use this snapshot')
args.destination.chmod(0o600)
print(f'Backup saved: {args.destination}')

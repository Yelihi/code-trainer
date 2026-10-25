"""Stop only this repository's reload server on the development API port."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def output(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(f'{args[0]} 확인에 실패했습니다: {result.stderr.strip()}')
    return result.stdout.strip()


def listeners():
    return {int(pid) for pid in output('lsof', '-nP', '-t', '-iTCP:8011', '-sTCP:LISTEN').split()}


def repository(directory):
    value = output('git', '-C', str(directory), 'rev-parse', '--git-common-dir')
    if not value:
        raise RuntimeError('프로세스의 저장소를 확인하지 못했습니다.')
    return (Path(directory) / value).resolve()


def process(pid):
    command = output('ps', '-p', str(pid), '-o', 'command=')
    parent = output('ps', '-p', str(pid), '-o', 'ppid=')
    cwd = next((line[1:] for line in output('lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn').splitlines() if line.startswith('n')), '')
    return command, int(parent) if parent else 0, cwd


def reload_server(pid, repo):
    visited = set()
    while pid > 1 and pid not in visited:
        visited.add(pid)
        command, parent, cwd = process(pid)
        args = shlex.split(command)
        expected = ['-m', 'uvicorn', 'backend.api:app', '--host', '127.0.0.1', '--port', '8011',
                    '--no-access-log', '--reload', '--reload-dir', 'backend']
        if args[1:] == expected and cwd and repository(cwd) == repo:
            return pid, (command, parent, cwd)
        pid = parent
    raise RuntimeError('8011을 사용하는 프로세스가 이 저장소의 개발 서버인지 확인되지 않아 종료하지 않았습니다.')


def stop():
    pids = listeners()
    if not pids:
        print('8011 개발 서버가 실행 중이지 않습니다.')
        return
    repo = repository(ROOT)
    # Validate every listener before signalling the reload parent, including inherited sockets.
    servers = dict(reload_server(pid, repo) for pid in pids)
    for pid, identity in servers.items():
        if process(pid) != identity:
            raise RuntimeError('확인 중 프로세스가 바뀌었습니다. 다시 시도해주세요.')
    for pid in servers:
        os.kill(pid, signal.SIGTERM)
    deadline = time.monotonic() + 10
    while listeners():
        if time.monotonic() >= deadline:
            raise RuntimeError('개발 서버 종료를 10초 기다렸습니다. 강제 종료하지 않았으므로 프로세스를 확인해주세요.')
        time.sleep(.1)
    print('8011 개발 서버를 종료했습니다.')


if __name__ == '__main__':
    try:
        stop()
    except (OSError, ValueError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)

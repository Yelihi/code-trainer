"""Only source and stdin enter the container. Expected output stays on the host."""
import os
import selectors
import subprocess
import threading
import time
import uuid

IMAGE = os.environ.get('TRAINER_IMAGE', 'code-trainer-runner:v1')
LIMIT = 16384
COMPILE_SECONDS = 20
RUNTIMES = {
    'javascript': ('main.js', None, ['node', '/work/main.js']),
    'typescript': ('main.ts', ['tsc', '/work/main.ts', '--target', 'ES2022', '--module', 'commonjs', '--outDir', '/work/out', '--skipLibCheck'], ['node', '/work/out/main.js']),
    'python': ('main.py', None, ['python3', '-I', '-B', '/work/main.py']),
    'cpp': ('main.cpp', ['g++', '-std=c++20', '-O0', '/work/main.cpp', '-o', '/work/main'], ['/work/main']),
    'rust': ('main.rs', ['rustc', '--edition=2021', '/work/main.rs', '-o', '/work/main'], ['/work/main']),
}
# ponytail: one execution across the local app; use a bounded worker queue if concurrency is needed.
slot = threading.Lock()


class Unavailable(Exception):
    pass


def command(args, timeout=10):
    try:
        return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise Unavailable('Docker 실행 환경에 연결하지 못했습니다.') from error


def available():
    try:
        return command(['image', 'inspect', IMAGE], 5).returncode == 0
    except Unavailable:
        return False


def memory_limited(container):
    result = command(['exec', container, 'cat', '/sys/fs/cgroup/memory.events'])
    if result.returncode:
        # An OOM can kill the container's init process as well as the submitted process.
        result = command(['inspect', '--format', '{{.State.OOMKilled}}', container])
        return result.returncode == 0 and result.stdout.strip() == 'true'
    return any(line.startswith('oom_kill ') and int(line.split()[1]) > 0 for line in result.stdout.splitlines())


def cleanup():
    result = command(['ps', '-aq', '--filter', 'label=code-trainer=true'])
    for container in result.stdout.split():
        command(['rm', '-f', container])


def capture(args, stdin='', seconds=3):
    process = subprocess.Popen(['docker', *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = [bytearray(), bytearray()]
    status = 'ok'
    try:
        with selectors.DefaultSelector() as poll:
            pending = memoryview(stdin.encode())
            if pending:
                os.set_blocking(process.stdin.fileno(), False)
                poll.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            else:
                process.stdin.close()
            for index, pipe in enumerate((process.stdout, process.stderr)):
                os.set_blocking(pipe.fileno(), False)
                poll.register(pipe, selectors.EVENT_READ, index)
            deadline = time.monotonic() + seconds
            while poll.get_map():
                if time.monotonic() >= deadline:
                    status = 'time_limit'
                    break
                for key, _ in poll.select(min(0.1, max(0, deadline - time.monotonic()))):
                    if key.data == 'stdin':
                        try:
                            pending = pending[os.write(key.fileobj.fileno(), pending[:4096]):]
                        except BrokenPipeError:
                            pending = pending[:0]
                        if not pending:
                            poll.unregister(key.fileobj)
                            process.stdin.close()
                        continue
                    chunk = os.read(key.fileobj.fileno(), 4096)
                    if not chunk:
                        poll.unregister(key.fileobj)
                    else:
                        remaining = LIMIT - sum(map(len, output))
                        output[key.data].extend(chunk[:remaining])
                        if len(chunk) > remaining:
                            status = 'output_limit'
                            break
                if status != 'ok':
                    break
    finally:
        if process.poll() is None:
            try:
                process.wait(timeout=0.2 if status == 'ok' else 0)
            except subprocess.TimeoutExpired:
                process.kill()
        process.wait()
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()
    return {'status': status, 'stdout': output[0].decode(errors='replace'), 'stderr': output[1].decode(errors='replace'), 'exit_code': process.returncode}


def run(language, code, inputs, image_id=None):
    if not slot.acquire(timeout=1):
        raise Unavailable('실행 환경이 사용 중입니다. 잠시 후 다시 시도해주세요.')
    name = 'code-trainer-' + uuid.uuid4().hex
    created = False
    try:
        # Pin to the resolved image ID for this job, not a mutable tag.
        image = command(['image', 'inspect', '--format', '{{.Id}}', image_id or IMAGE])
        if image.returncode:
            raise Unavailable('실행 이미지를 준비해주세요: ./start.sh --setup')
        result = command(['create', '--name', name, '--label', 'code-trainer=true',
            '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--user', '65534:65534',
            '--memory', '256m', '--memory-swap', '256m', '--cpus', '1', '--pids-limit', '64',
            '--ulimit', 'nofile=128:128', '--ulimit', 'fsize=16777216:16777216',
            '--tmpfs', '/work:rw,exec,nosuid,size=64m,mode=1777',
            '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m,mode=1777',
            '--log-driver', 'none', image.stdout.strip()])
        if result.returncode:
            raise Unavailable('격리 환경을 만들지 못했습니다.')
        created = True
        if command(['start', name]).returncode:
            raise Unavailable('격리 환경을 시작하지 못했습니다.')
        filename, compiler, runtime = RUNTIMES[language]
        # docker cp rejects read-only roots even with tmpfs; stream into the private tmpfs.
        copied = capture(['exec', '-i', name, 'python3', '-c',
            'import sys; open(sys.argv[1], "w").write(sys.stdin.read())', f'/work/{filename}'], code, seconds=5)
        if copied['status'] != 'ok' or copied['exit_code']:
            raise Unavailable('코드를 격리 환경으로 전달하지 못했습니다.')
        if compiler:
            result = capture(['exec', name, *compiler], seconds=COMPILE_SECONDS)
            if result['status'] != 'ok' or result['exit_code']:
                result['status'] = 'compile_' + ('memory_limit' if memory_limited(name) else result['status'] if result['status'] != 'ok' else 'error')
                return [result]
        results = []
        for value in inputs:
            result = capture(['exec', '-i', name, *runtime], value)
            if result['status'] == 'ok' and result['exit_code']:
                result['status'] = 'memory_limit' if memory_limited(name) else 'runtime_error'
            results.append(result)
            if result['status'] in ('time_limit', 'output_limit', 'memory_limit'):
                break
        return results
    except (OSError, subprocess.SubprocessError) as error:
        raise Unavailable('실행 환경과의 연결이 중단되었습니다.') from error
    finally:
        try:
            if created:
                result = command(['rm', '-f', name])
                if result.returncode:
                    raise Unavailable('실행 환경 정리에 실패했습니다. Docker 상태를 확인해주세요.')
        finally:
            slot.release()

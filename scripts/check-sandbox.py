"""Actual Docker checks; never falls back to running submitted code on the host."""
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import runner, service
from backend.sample import sample
from backend.schema import Case

if not runner.available():
    raise SystemExit('FAIL: Docker runner unavailable. Run ./start.sh --setup first.')

programs = {
    'javascript': "console.log('42')",
    'typescript': "const n: number = 42; console.log(n)",
    'python': "print(42)",
    'cpp': '#include <iostream>\nint main(){std::cout << 42 << "\\n";}',
    'rust': 'fn main(){println!("42");}',
}
for language, code in programs.items():
    result = runner.run(language, code, [''])[0]
    assert result['status'] == 'ok' and result['stdout'].strip() == '42', (language, result)
    print('PASS compile/run:', language, flush=True)

functions = {
    'javascript': ('function twice(n) { return n * 2; }', 'console.log(twice(21));'),
    'typescript': ('function twice(n: number): number { return n * 2; }', 'console.log(twice(21));'),
    'python': ('def twice(n):\n    return n * 2', 'print(twice(21))'),
    'cpp': ('#include <iostream>\nint twice(int n) { return n * 2; }', 'int main() { std::cout << twice(21) << "\\n"; }'),
    'rust': ('fn twice(n: i32) -> i32 { n * 2 }', 'fn main() { println!("{}", twice(21)); }'),
}
for language, (solution, calls) in functions.items():
    tests = [Case(id='calls', stdin='', code=calls, expected='42', requirements=['r1'])]
    result = service.evaluate(language, solution, tests)
    assert result['status'] == 'passed', (language, result)
    print('PASS function call tests:', language, flush=True)

solution = 'function countOwnEnumerable(obj) { return Object.keys(obj).length; }'
calls = 'const plain = {a: 1, b: 2}; const nullProto = Object.create(null); nullProto.x = 1; nullProto.y = 2; console.log(countOwnEnumerable(plain)); console.log(countOwnEnumerable(nullProto));'
tests = [Case(id='own-keys', stdin='', code=calls, expected='2\n2', requirements=['r1'])]
assert service.evaluate('javascript', solution, tests)['status'] == 'passed'
duplicate = service.evaluate('javascript', solution + '\nconst plain = {};', tests)
assert duplicate['status'] == 'runtime_error' and 'has already been declared' in duplicate['stderr']
assert runner.run('javascript', 'console.log(typeof plain)', [''])[0]['stdout'].strip() == 'undefined'
print('PASS separate implementation/test setup and fresh execution state', flush=True)

for language in ('typescript', 'cpp', 'rust'):
    result = runner.run(language, 'this is not valid code @@@', [''])[0]
    assert result['status'] == 'compile_error', (language, result)
    print('PASS compile error:', language, flush=True)

for code, expected in [("while(true){}", 'time_limit'), ("while(true) console.log('x'.repeat(1000))", 'output_limit'), ("const a=[];while(true)a.push(new Array(100000).fill(1));", 'memory_limit')]:
    result = runner.run('javascript', code, [''])[0]
    assert result['status'] == expected, result
    assert len((result['stdout'] + result['stderr']).encode()) <= runner.LIMIT
    print('PASS resource limit:', expected, flush=True)

code = '''import os, socket
assert not os.path.exists('/var/run/docker.sock')
assert 'AI_API_KEY' not in os.environ
try:
    open('/etc/trainer-check', 'w')
    raise AssertionError('root writable')
except (PermissionError, OSError): pass
try:
    socket.create_connection(('1.1.1.1', 443), timeout=0.5)
    raise AssertionError('network enabled')
except OSError: pass
print('isolated')
'''
result = runner.run('python', code, [''])[0]
assert result['status'] == 'ok' and result['stdout'].strip() == 'isolated', result
print('PASS network/filesystem/environment isolation', flush=True)
processes = '''import subprocess
children=[]
try:
    for i in range(100):
        children.append(subprocess.Popen(['sleep','10'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
except BlockingIOError:
    print('process limit')
finally:
    for child in children: child.terminate()
    for child in children: child.wait()
'''
result = runner.run('python', processes, [''])[0]
assert result['status'] == 'ok' and result['stdout'].strip() == 'process limit', result
print('PASS process count limit', flush=True)
result = runner.run('cpp', '#include <utility>\nauto x=std::make_integer_sequence<int,100000000>{}; int main(){}', [''])[0]
assert result['status'] == 'compile_memory_limit', result
print('PASS compiler memory limit', flush=True)
result = runner.run('cpp', '\n'.join('#error diagnostic' for _ in range(1000)), [''])[0]
assert result['status'] == 'compile_output_limit', result
print('PASS compiler diagnostic output limit', flush=True)
with patch.object(runner, 'COMPILE_SECONDS', 0.05):
    result = runner.run('cpp', programs['cpp'], [''])[0]
assert result['status'] == 'compile_time_limit', result
print('PASS compiler timeout and termination (50ms test budget)', flush=True)
context, draft = sample()
for unit in context.units:
    for section in unit.lesson:
        if section.code:
            result = runner.run(context.language, section.code, [''])[0]
            assert result['status'] == 'ok' and service.normalized(result['stdout']) == service.normalized(section.output), (section.title, result)
print('PASS lesson examples and displayed output', flush=True)
checks = service.validate_set(context.language, draft)
assert all(c['passed'] for c in checks)
print(f'PASS baseline set: {len(checks)} validation checks', flush=True)
assert not runner.command(['ps', '-aq', '--filter', 'label=code-trainer=true']).stdout.strip()
print('PASS container cleanup', flush=True)

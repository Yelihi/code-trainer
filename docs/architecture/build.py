"""Build public reference data from tracked source ASTs, without importing the app."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True).strip()


def catalog():
    records, imports = [], {}
    files = git('ls-files', '-z').split('\0')
    for file in files:
        if not file.endswith('.py') or not file.startswith(('backend/', 'deploy/', 'scripts/')) or Path(file).name.startswith('test_'):
            continue
        tree = ast.parse((ROOT / file).read_text(), filename=file)
        module = file[:-3].replace('/', '.')
        aliases = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    aliases[a.asname or a.name] = a.name
            elif isinstance(n, ast.ImportFrom):
                prefix = '.'.join(module.split('.')[:-n.level]) if n.level else ''
                base = '.'.join(filter(None, [prefix, n.module]))
                for a in n.names:
                    aliases[a.asname or a.name] = '.'.join(filter(None, [base, a.name]))
        imports[file] = aliases

        def collect(node, parents=()):
            for n in ast.iter_child_nodes(node):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    name = '.'.join((*parents, n.name))
                    record = dict(id=f'{file}::{name}', path=file, name=name, line=n.lineno,
                                  end=n.end_lineno, calls=[], events=[])
                    for decorator in n.decorator_list:
                        record['events'].append('@' + ast.unparse(decorator))

                    def scan(child):
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                            return
                        if isinstance(child, ast.Call):
                            called = ast.unparse(child.func)
                            record['calls'].append({'name': called})
                            if called.endswith('.add_task') and child.args:
                                target = ast.unparse(child.args[0])
                                record['events'].append('BackgroundTasks → ' + target)
                                record['calls'].append({'name': target, 'kind': 'background'})
                            if called == 'diagnostics.event' and child.args:
                                record['events'].append('진단 기록 · ' + ast.unparse(child.args[0]))
                        for inner in ast.iter_child_nodes(child):
                            scan(inner)
                    for statement in n.body:
                        scan(statement)
                    record['calls'] = list({c['name']: c for c in record['calls']}.values())
                    records.append(record)
                    collect(n, (*parents, n.name))
                elif isinstance(n, ast.ClassDef):
                    collect(n, (*parents, n.name))
                else:
                    collect(n, parents)
        collect(tree)
    by_name = {r['path'][:-3].replace('/', '.') + '.' + r['name']: r['id'] for r in records}
    for r in records:
        module = r['path'][:-3].replace('/', '.')
        for call in r['calls']:
            parts = call['name'].split('.')
            imported = imports[r['path']].get(parts[0])
            candidates = []
            if imported:
                candidates.append('.'.join([imported, *parts[1:]]))
                # Operational scripts import sibling modules directly.
                candidates.append('deploy.' + candidates[-1])
            scope = r['name'].split('.')[:-1]
            for depth in range(len(scope), -1, -1):
                candidates.append('.'.join([module, *scope[:depth], call['name']]))
            target = next((by_name[c] for c in candidates if c in by_name), None)
            if target:
                call['target'] = target
    records += json.loads(subprocess.check_output(['node', str(HERE / 'scan.mjs')], cwd=ROOT, text=True))
    records.sort(key=lambda r: (r['path'], r['line']))
    ids = {r['id'] for r in records}
    assert len(ids) == len(records), 'Duplicate function identifiers'
    for r in records:
        assert all(c.get('target', r['id']) in ids for c in r['calls'])
    return dict(revision=git('rev-parse', 'HEAD'), repository='https://github.com/Yelihi/code-trainer',
                scope='추적 중인 Python·TypeScript·JavaScript 제품/운영 코드의 이름 있는 함수. 테스트·문서 도구 제외. 익명 콜백은 상위 함수의 이벤트/호출에 포함.',
                limitation='정적 참조 지도입니다. 조건별 실제 실행 순서나 동적 호출을 증명하지 않습니다. 연결된 호출만 저장소 함수로 해석됐으며, 나머지는 외부·객체 메서드·동적 호출입니다.',
                files=len({r['path'] for r in records}), functions=records)


def build(destination):
    data = catalog()
    destination.mkdir(parents=True, exist_ok=True)
    # Explicit allowlist: never publish configs, user data or the whole repository.
    for name in ('index.html', 'site.css', 'site.js', 'journeys.json', 'overview.html', 'overview.json', 'overview.receipt.json', 'overview.svg', 'verification.json'):
        shutil.copyfile(HERE / name, destination / name)
    (destination / 'catalog.json').write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n')
    (destination / '.nojekyll').touch()
    journeys = json.loads((HERE / 'journeys.json').read_text())
    ids = {r['id'] for r in data['functions']}
    for journey in journeys:
        for step in journey['steps']:
            for reference in step.get('functions', []):
                assert reference in ids, f'Unknown function: {reference}'
    receipt = json.loads((HERE / 'overview.receipt.json').read_text())
    for name, key in [('overview.html', 'artifact'), ('overview.json', 'specification')]:
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == receipt[key]['sha256']
    print(f'Built {data["files"]} modules / {len(ids)} functions / {len(journeys)} event flows into {destination}')


if __name__ == '__main__':
    build(Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / '.architecture-site'))

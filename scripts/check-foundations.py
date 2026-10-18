"""Validate every shipped lesson against real TypeScript execution in the sandbox."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import foundations, runner
from backend.foundation_catalog import CATALOG

if not runner.available():
    raise SystemExit('FAIL: isolated runner unavailable')
runtime = runner.pin_runtime()
for item in CATALOG.values():
    tests = '{\n' + item['public_tests'] + '\n}\n{\n' + item['hidden_tests'] + '\n}'
    checks = foundations.grade(item, item['reference'], tests, runtime)
    assert len(checks) == 4 + len(item['mutations']) and all(c['passed'] for c in checks), (item['id'], checks)
    assert not foundations.check(item['starter'], tests, runtime)['passed'], item['id']
    assert not foundations.check(item['reference'], item['test_starter'], runtime)['passed'], item['id']
    print('PASS foundation:', item['id'], flush=True)

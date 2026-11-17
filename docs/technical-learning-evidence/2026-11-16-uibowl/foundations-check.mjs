import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const { execFileSync } = await import('node:child_process');
const root = fileURLToPath(new URL('../../../', import.meta.url));
const lessons = JSON.parse(execFileSync(root + '.venv/bin/python', ['-c', "import json; from backend.foundation_catalog import CATALOG, public; print(json.dumps({key:{**public(item),'solution':item['reference']} for key,item in CATALOG.items()},ensure_ascii=False))"], { cwd: root, encoding: 'utf8' }));
const before = process.env.FOUNDATIONS_BEFORE === '1';
const output = fileURLToPath(new URL('./', import.meta.url));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ reducedMotion: 'reduce' });
page.setDefaultTimeout(10000);
const errors = [], unknown = [], checks = [], writes = [];
page.on('pageerror', error => errors.push(error.message));
let mode = 'explain', failed = false;
const date = '2026-11-16T00:00:00Z';
await page.route('**/api/**', async route => {
  const req = route.request(), path = new URL(req.url()).pathname.slice(4), id = path.split('/')[2];
  if (req.method() !== 'GET') {
    writes.push(path);
    if (path === '/study/visit') return route.fulfill({ json: {} });
    if (path.endsWith('/progress')) return route.fulfill({ json: { revision: 2 } });
    throw new Error('Unexpected mutation: ' + path);
  }
  if (path === '/session') return route.fulfill({ json: { user: { id: 'fixture', username: 'preview', admin: 1 }, setup_required: false, auth_mode: 'preview' } });
  if (path === '/health') return route.fulfill({ json: { ai: true, sandbox: true, languages: [] } });
  if (path === '/learning-target') return route.fulfill({ json: { target: null } });
  if (path === '/related-questions') return route.fulfill({ json: { items: [] } });
  if (path === '/foundations') return route.fulfill({ json: { items: Object.values(lessons).map(item => ({ ...item, state: 'new', can_resume: false, running: false, revision: 0 })) } });
  if (lessons[id] && path.endsWith('/solution')) return route.fulfill({ json: { code: lessons[id].solution } });
  if (lessons[id] && path === '/foundations/' + id) {
    if (failed) return route.fulfill({ status: 503, json: { detail: '단원을 불러오지 못했습니다.' } });
    const { solution, ...lesson } = lessons[id];
    const review = { id: 'review', lesson_id: id, version: lesson.version, state: 'ready', error: '', created_at: date, payload: { answers: lesson.questions.map(() => '검증용 설명') }, result: { items: lesson.questions.map(q => ({ question_id: q.id, understood: '핵심 동작을 설명했습니다.', missing: '경계 조건을 더 확인하세요.', correction: '' })), model_answers: lesson.questions.map(q => ({ id: q.id, prompt: q.prompt, answer: '검증용 기준 설명입니다.' })) } };
    return route.fulfill({ json: { ...lesson, ai_available: true, unlocked: mode !== 'explain', completed: false, progress: { revision: 1, answers: review.payload.answers, code: lesson.starter, test_code: lesson.test_starter }, review: mode === 'explain' ? null : review, attempt: mode === 'result' ? { id: 'attempt', lesson_id: id, version: lesson.version, state: 'failed', error: '', created_at: date, payload: { code: lesson.starter, test_code: lesson.test_starter.trim() }, result: { checks: [{ label: '공개 예제', passed: false, status: 'assertion_failed', detail: '검증용 결과 · 예상 값과 다릅니다.' }] } } : null } });
  }
  unknown.push(path); return route.fulfill({ status: 404, json: { detail: 'Missing fixture: ' + path } });
});
try {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const id of before ? ['gcd', 'linked-list'] : Object.keys(lessons)) {
      await page.goto('http://127.0.0.1:5173/foundations/' + id); await page.getByRole('region', { name: '개념 시각화', exact: true }).waitFor();
      await page.locator('main').evaluate(node => Promise.all(node.getAnimations().map(animation => animation.finished.catch(() => {}))));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${id}@${width}`);
      if (before || ['gcd', 'stack', 'linked-list', 'bfs'].includes(id)) await page.screenshot({ path: `${output}foundation-${before ? 'before-' : ''}${id}-${width}.png`, fullPage: true });
      checks.push(`${id}@${width}`);
    }
  }
  if (!before) {
    for (const width of [1440, 1024, 768, 390]) {
      await page.setViewportSize({ width, height: 1000 });
      for (const state of ['explain', 'implement', 'result']) {
        mode = state; await page.goto('http://127.0.0.1:5173/foundations/gcd/practice'); await page.locator('.foundation-work').waitFor();
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, state + '@' + width);
        if (width === 1440 || width === 390) await page.screenshot({ path: `${output}foundation-${state}-${width}.png`, fullPage: true });
      }
    }
    mode = 'implement'; await page.goto('http://127.0.0.1:5173/foundations/gcd/practice');
    await page.getByRole('button', { name: '참고 풀이 보기', exact: true }).click(); await page.getByText('참고 풀이', { exact: true }).waitFor();
    assert.ok(writes.some(path => path.endsWith('/progress')));
    await page.getByRole('button', { name: '테스트 작성 도움말', exact: true }).click();
    const help = page.getByRole('dialog', { name: '테스트, 이렇게 작성하세요' }); await help.waitFor();
    await page.screenshot({ path: `${output}foundation-help-390.png`, fullPage: true });
    await page.keyboard.press('Escape'); assert.equal(await help.isVisible(), false);
    await page.getByRole('button', { name: /내 말로 설명/ }).click(); await page.getByText('기준 설명 보기', { exact: true }).first().click();
    await page.getByText('검증용 기준 설명입니다.', { exact: true }).first().waitFor();
    await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
    await page.screenshot({ path: `${output}foundation-feedback-390.png`, fullPage: true });
    await page.goto('http://127.0.0.1:5173/foundations/gcd');
    const counter = page.locator('.visual-counter'); await counter.waitFor();
    const initial = await counter.innerText(); await page.getByRole('button', { name: '다음', exact: true }).click(); assert.notEqual(await counter.innerText(), initial);
    await page.getByRole('button', { name: '시각화 처음으로' }).click(); assert.equal(await counter.innerText(), initial);
    const slider = page.getByRole('slider', { name: '단계 탐색' }); await slider.focus(); await page.keyboard.press('ArrowRight'); assert.equal(await slider.getAttribute('aria-valuenow'), '1');
    await page.getByRole('button', { name: '재생', exact: true }).click(); await page.getByRole('button', { name: '일시정지', exact: true }).click();
    await page.goto('http://127.0.0.1:5173/foundations/linked-list');
    await page.getByRole('button', { name: '이중 연결 · prev + next', exact: true }).click(); assert.ok(await page.locator('.prev-field').count() > 0);
    await page.goto('http://127.0.0.1:5173/foundations/bfs'); await page.locator('.graph-options select').selectOption('G');
    await page.getByRole('region', { name: '개념 시각화', exact: true }).waitFor();
    failed = true; await page.goto('http://127.0.0.1:5173/foundations/gcd'); await page.getByRole('alert').waitFor(); failed = false;
    await page.getByRole('button', { name: '다시 불러오기', exact: true }).click(); await counter.waitFor();
    assert.deepEqual(errors, []); assert.deepEqual(unknown, []);
    await writeFile(`${output}foundation-checks.json`, JSON.stringify({ checks, practiceWidths: [1440,1024,768,390], interactions: ['reference solution', 'explanation feedback', 'next/reset', 'slider keyboard', 'play/pause', 'help dialog/Escape', 'doubly linked list', 'graph start vertex', 'failure/retry'], errors, unknown }, null, 2));
  }
  console.log(`Passed ${checks.length} concept page checks${before ? ' (before)' : ', 12 practice states and 9 interactions'}.`);
} finally { await browser.close(); }

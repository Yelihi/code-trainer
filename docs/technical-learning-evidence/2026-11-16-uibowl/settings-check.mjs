import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output = fileURLToPath(new URL('./', import.meta.url));
const before = process.env.SETTINGS_BEFORE === '1';
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ reducedMotion: 'reduce' });
page.setDefaultTimeout(10000);
const errors = [], unknown = [], checks = [];
page.on('pageerror', error => errors.push(error.message));
const date = '2026-11-16T00:00:00Z';
let failedAI = false, empty = false, state = 'normal';
const source = { id: 'source', title: '검증용 원본 · 함수와 상태의 수명', context_id: null, name: '학습 원문', kind: 'url', url: 'https://example.com/articles/functions-and-state', has_content: true, state: 'ready', created_at: date, content: '함수는 선언된 환경을 기억합니다.\n\n원문 열람 검증용 자료입니다.' };
await page.route('**/api/**', async route => {
  const request = route.request(), path = new URL(request.url()).pathname.slice(4);
  if (request.method() !== 'GET') {
    assert.equal(path, '/study/visit', 'Settings QA must not mutate data or call external services');
    return route.fulfill({ json: {} });
  }
  if (failedAI && path === '/ai/settings') return route.fulfill({ status: 503, json: { detail: '설정을 불러오지 못했습니다.' } });
  const fixtures = {
    '/session': { user: { id: 'fixture', username: 'preview', admin: 1 }, setup_required: false, auth_mode: 'preview' },
    '/health': { sandbox: true, ai: true, languages: [] },
    '/learning-target': { target: null }, '/related-questions': { items: [] },
    '/ai/settings': { revision: 1, source: state === 'off' ? 'disabled' : 'environment', model: 'example-model', provider_url: 'https://example.com/v1', saved_provider_url: '', storage_ready: true, available: true, error: '' },
    '/github/connection': { storage_ready: true, connection: state === 'off' ? null : { id: 'connection', login: 'example-user', updated_at: date } },
    '/github/default-repository': { repository: null }, '/github/shares': [],
    '/me': { learning_map: [], sets: [], attempts: [], reports: [] },
    '/me/foundations': { items: empty ? [] : [{ id: 'record', lesson_id: 'stack', version: 1, title: '검증용 · 스택 구현', created_at: date, assistance: 'hint', feedback: { items: [] } }] },
    '/me/ai-usage': { totals: { calls: 0, input_tokens: 0, output_tokens: 0, unknown_usage_calls: 0 }, items: [] },
    '/admin/reports': [],
    '/admin/operations': { available: state !== 'unavailable', stale: state === 'stale', services: { api: true, runner: false }, warnings: ['검증용 · 코드 실행기 연결을 확인하세요.'], collected_at: date, backup_at: date, internal_free_gib: 42, external_free_gib: 512, certificates: [{ name: 'example.com', days_left: 30, expires_at: date }], checks: { full_reboot: '미확인', off_device_recovery: '미확인' } },
    '/admin/sources': empty ? [] : [source], '/admin/sources/source': source,
    '/questions': { items: [], total: 0, page: 1, pages: 1 },
  };
  if (!(path in fixtures)) { unknown.push(path); return route.fulfill({ status: 404, json: { detail: 'Missing fixture ' + path } }); }
  return route.fulfill({ json: fixtures[path] });
});
const routes = [
  ['questions', '/questions', '.question-results'], ['history', '/me', '.foundation-records'],
  ['ai', '/settings/ai', '.ai-connection-form'], ['github', '/settings/github', '.github-settings-grid'],
  ['export', '/settings/records', 'a[download]'], ['operations', '/admin/operations', '.operation-facts'],
  ['sources', '/admin/sources', '.source-card'], ['source-detail', '/admin/sources/source', '.source-document'],
];
try {
  await mkdir(output, { recursive: true });
  for (const width of before ? [1440, 390] : [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const [name, path, selector] of routes) {
      await page.goto('http://127.0.0.1:5173' + path); await page.locator(selector).first().waitFor();
      await page.locator('main').evaluate(node => Promise.all(node.getAnimations().map(animation => animation.finished.catch(() => {}))));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, name + '@' + width);
      if (width === 1440 || width === 390) await page.screenshot({ path: `${output}settings-${before ? 'before-' : ''}${name}-${width}.png`, fullPage: true });
      checks.push(`${name}@${width}`);
    }
  }
  if (!before) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.goto('http://127.0.0.1:5173/settings/records');
    const menu = page.locator('.workspace-settings'), trigger = menu.locator('summary');
    await trigger.click(); await page.locator('main h1').click(); assert.equal(await menu.getAttribute('open'), null);
    await trigger.click(); await page.keyboard.press('Escape'); assert.equal(await menu.getAttribute('open'), null); assert.equal(await trigger.evaluate(node => document.activeElement === node), true);
    await trigger.click(); await menu.getByRole('link', { name: 'GitHub 연동', exact: true }).click(); await page.waitForURL('**/settings/github'); assert.equal(await menu.getAttribute('open'), null);
    await trigger.click(); await menu.getByRole('link', { name: 'GitHub 연동', exact: true }).click(); assert.equal(await menu.getAttribute('open'), null);
    failedAI = true; await page.goto('http://127.0.0.1:5173/settings/ai'); await page.getByRole('alert').waitFor(); failedAI = false;
    await page.getByRole('button', { name: '다시 불러오기', exact: true }).click(); await page.locator('.ai-connection-form').waitFor();
    empty = true; await page.goto('http://127.0.0.1:5173/admin/sources'); await page.getByText('아직 등록한 자료가 없습니다', { exact: true }).waitFor();
    await page.goto('http://127.0.0.1:5173/me'); await page.getByRole('heading', { name: '완료한 단원이 없습니다', exact: true }).waitFor();
    state = 'off'; await page.goto('http://127.0.0.1:5173/settings/ai'); await page.getByText('연결 없음', { exact: true }).waitFor();
    await page.goto('http://127.0.0.1:5173/settings/github'); await page.locator('.github-settings-grid').waitFor(); assert.equal(await page.locator('#github-repo').isDisabled(), true);
    await page.getByText('토큰 발급·권한 안내', { exact: true }).click(); await page.getByText('Issues → Read and write', { exact: true }).waitFor();
    await page.setViewportSize({ width: 390, height: 1000 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: `${output}settings-github-help-390.png`, fullPage: true });
    state = 'stale'; await page.goto('http://127.0.0.1:5173/admin/operations'); await page.locator('.operation-facts').waitFor();
    assert.equal(await page.locator('dd[data-state="ok"]').count(), 0); assert.equal(await page.locator('dd[data-state="unknown"]').count(), 2);
    state = 'unavailable'; await page.goto('http://127.0.0.1:5173/admin/operations'); await page.getByText('수집된 운영 정보가 없습니다', { exact: true }).waitFor();
    await page.locator('.workspace-settings summary').click();
    await page.screenshot({ path: `${output}settings-menu-390.png`, fullPage: true });
    assert.deepEqual(errors, []); assert.deepEqual(unknown, []);
    await writeFile(`${output}settings-checks.json`, JSON.stringify({ checks, interactions: ['outside click', 'Escape/focus return', 'route selection', 'same-route selection', 'AI failure/retry', 'empty sources/history', 'AI disconnected', 'GitHub disconnected/help', 'stale status', 'unavailable operations'], errors, unknown }, null, 2));
  }
  console.log(`Passed ${checks.length} settings page checks${before ? ' (before)' : ' and 10 interactions'}.`);
} finally { await browser.close(); }

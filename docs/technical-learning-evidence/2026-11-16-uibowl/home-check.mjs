import assert from 'node:assert/strict';
import { writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output = fileURLToPath(new URL('./', import.meta.url));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ reducedMotion: 'reduce' });
page.setDefaultTimeout(10000);
const errors = [], unknown = [], writes = [], checks = [];
page.on('pageerror', error => errors.push(error.message));
let empty = false, failSave = false, failLoad = false, aiMade = false, recommendationState = '', failRecommendation = false;
let policy = { question_age_days: 7, resurfacing_days: 7, snooze_days: 3, question_limit: 3 };
const date = '2026-11-17T00:00:00Z';
const resume = { kind: 'foundation', id: 'gcd', unit_id: 'practice', title: '검증용 · 최대공약수의 나머지 순서', href: '/foundations/gcd/practice', revision: 1, updated_at: date };
const questions = [{ key: 'question:' + 'a'.repeat(32), id: 'a'.repeat(32), title: '검증용 · 두 카운터는 왜 다른 값을 기억할까요?', href: '/questions/' + 'a'.repeat(32), created_at: '2026-11-09T00:00:00Z' }];
await page.route('**/api/**', async route => {
  const req = route.request(), path = new URL(req.url()).pathname.slice(4);
  if (req.method() !== 'GET') {
    writes.push({ path, data: req.postDataJSON() });
    if (path === '/study/visit') return route.fulfill({ json: {} });
    if (path === '/study/policy') {
      await new Promise(resolve => setTimeout(resolve, 250));
      if (failSave) return route.fulfill({ status: 503, json: { detail: '설정을 저장하지 못했습니다.' } });
      policy = req.postDataJSON(); return route.fulfill({ json: policy });
    }
    if (path === '/study/recommendations') { aiMade = true; return route.fulfill({ json: {} }); }
    throw new Error('Unexpected mutation: ' + path);
  }
  if (path === '/study/recommendations' && failRecommendation) return route.fulfill({ status: 503, json: { detail: '제안을 불러오지 못했습니다.' } });
  if (path === '/study/today' && failLoad) return route.fulfill({ status: 503, json: { detail: '학습 활동을 불러오지 못했습니다.' } });
  const fixtures = {
    '/session': { user: { id: 'fixture', username: 'preview', admin: 1 }, setup_required: false, auth_mode: 'preview' },
    '/health': { ai: true, sandbox: true, languages: [] }, '/learning-target': { target: null }, '/related-questions': { items: [] },
    '/study/today': { day: '2026-11-17', resume: empty ? [] : [resume, { ...resume, title: '검증용 · 스택의 실행 순서', id: 'stack', href: '/foundations/stack/practice' }], reviews: empty ? [] : [{ key: 'review', title: '검증용 · 상태의 소유권', href: '/reviews/material/review', due_at: date, in_progress: false }], review_count: empty ? 0 : 1, questions: empty ? [] : questions, policy },
    '/study/recommendations': { items: aiMade ? [{ key: 'ai', title: '검증용 · 호출마다 만들어지는 환경', reason: '남겨둔 카운터 질문에서 이어갈 수 있는 학습입니다.', uncertain: true, evidence: [{ id: 'question', title: questions[0].title, href: questions[0].href }], action: { href: resume.href, title: '코드로 확인' } }] : [], job: recommendationState ? { state: recommendationState, error: recommendationState === 'failed' ? '연결을 확인하고 다시 시도해주세요.' : '' } : null, stale: false, generated_at: aiMade ? date : null },
  };
  if (!(path in fixtures)) { unknown.push(path); return route.fulfill({ status: 404, json: { detail: 'Missing fixture ' + path } }); }
  return route.fulfill({ json: fixtures[path] });
});
try {
  for (const width of [1440,1024,768,390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const [name, path, selector] of [['home', '/', '.today-board'], ['policy', '/settings/questions', '.policy-rows']]) {
      await page.goto('http://127.0.0.1:5173' + path); await page.locator(selector).waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, name + '@' + width);
      if (name === 'home') {
        assert.equal(await page.locator('main details').count(), 0);
        if (width < 700) { const question = await page.getByRole('heading', { name: '다시 살펴볼 질문', exact: true }).boundingBox(), other = await page.getByRole('heading', { name: '진행 중인 다른 학습', exact: true }).boundingBox(); assert.ok(question.y < other.y); }
        assert.ok((await page.getByRole('heading', { name: '오늘의 복습', exact: true }).boundingBox()).y < 700);
        const ai = await page.locator('.home-recommendations').boundingBox(), board = await page.locator('.today-board').boundingBox(); assert.ok(ai.y >= board.y + board.height);
      }
      if (width === 1440 || width === 390) await page.screenshot({ path: `${output}home-refresh-${name}-${width}.png`, fullPage: true });
      checks.push(`${name}@${width}`);
    }
  }
  assert.equal(writes.some(write => write.path === '/study/recommendations'), false, 'Browsing must not generate AI');
  const age = page.getByLabel('처음 다시 볼 때', { exact: true });
  await age.fill('400'); await page.getByRole('button', { name: '변경 저장', exact: true }).click();
  assert.equal(writes.some(write => write.path === '/study/policy'), false, 'Invalid range must not save');
  await age.fill(''); assert.equal(await age.inputValue(), '');
  await age.fill('14'); failSave = true; await page.getByRole('button', { name: '변경 저장', exact: true }).click();
  await page.getByRole('alert').waitFor(); assert.equal(await age.inputValue(), '14');
  failSave = false; await page.getByRole('button', { name: '변경 저장', exact: true }).click(); await page.locator('button[aria-busy="true"] .button-spinner').waitFor();
  await page.getByRole('status').getByText('질문 다시보기 설정을 저장했어요.', { exact: true }).waitFor();
  assert.deepEqual(policy, { question_age_days:14, resurfacing_days:7, snooze_days:3, question_limit:3 });
  await page.getByRole('link', { name: '홈으로', exact: true }).click(); await page.getByText('14일 지난 질문부터', { exact: true }).waitFor();
  await page.getByRole('link', { name: '질문 다시보기 설정', exact: true }).click(); assert.equal(await age.inputValue(), '14');
  await page.goto('http://127.0.0.1:5173/'); await page.getByRole('button', { name: 'AI 제안 만들기', exact: true }).click(); await page.getByRole('heading', { name: '검증용 · 호출마다 만들어지는 환경' }).waitFor();
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const state of ['empty', 'running', 'failed', 'fetch-error', 'filled']) {
      aiMade = state === 'filled'; recommendationState = ['running', 'failed'].includes(state) ? state : ''; failRecommendation = state === 'fetch-error';
      await page.goto('http://127.0.0.1:5173/');
      const section = page.locator('.home-recommendations');
      await section.locator(state === 'filled' ? '.learning-row' : state === 'running' ? '.loading-state' : '.recommendation-state').waitFor();
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, state + '@' + width);
      if (state === 'running') { assert.equal(await section.locator('button[aria-busy="true"] .button-spinner').count(), 1); assert.equal(await section.getByRole('button').isDisabled(), true); }
      if (state === 'failed' || state === 'fetch-error') await section.getByRole('alert').waitFor();
      await section.screenshot({ path: `${output}recommendations-${state}-${width}.png` });
      checks.push(`recommendations-${state}@${width}`);
    }
  }
  aiMade = true; recommendationState = 'running';
  await page.goto('http://127.0.0.1:5173/'); await page.locator('.home-recommendations .learning-row').waitFor();
  assert.equal(await page.locator('.home-recommendations button[aria-busy="true"]').count(), 1, 'Keep existing suggestions while regenerating');
  aiMade = false; recommendationState = ''; failRecommendation = true;
  await page.goto('http://127.0.0.1:5173/'); await page.locator('.home-recommendations').getByRole('alert').waitFor();
  failRecommendation = false; await page.locator('.home-recommendations').getByRole('button', {name:'다시 불러오기',exact:true}).click();
  await page.getByRole('heading', {name:'남겨둔 질문, 다음 학습으로 이어가세요',exact:true}).waitFor();
  empty = true; await page.goto('http://127.0.0.1:5173/'); await page.getByRole('heading', { name: '새로운 학습을 시작하세요' }).waitFor();
  await page.screenshot({ path: `${output}home-refresh-empty-390.png`, fullPage: true });
  failLoad = true; await page.goto('http://127.0.0.1:5173/'); await page.getByRole('alert').waitFor(); assert.equal(await page.getByRole('heading', { name: '새로운 학습을 시작하세요' }).count(),0);
  failLoad = false; await page.getByRole('button', { name: '다시 불러오기', exact: true }).click(); await page.locator('.today-board').waitFor();
  assert.deepEqual(errors, []); assert.deepEqual(unknown, []);
  await writeFile(`${output}home-refresh-checks.json`,JSON.stringify({ checks, interactions: ['settings route', 'number range/empty validation', 'save failure preserves input', 'save spinner', 'save payload preserves other values', 'home reflects saved setting', 'no automatic AI', 'explicit AI', 'empty home', 'load failure/retry'], errors, unknown },null,2));
  console.log(`Passed ${checks.length} home/settings responsive checks and 10 interactions.`);
} finally { await browser.close(); }

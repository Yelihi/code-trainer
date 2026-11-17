import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
const { chromium } = await import(process.env.PLAYWRIGHT_MODULE || 'playwright');
const output = fileURLToPath(new URL('./', import.meta.url));
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ reducedMotion: 'reduce' });
page.setDefaultTimeout(10000);
const errors = [], writes = [], unhandled = [], checks = [];
page.on('pageerror', error => errors.push(error.message));
const date = '2026-11-16T09:00:00Z';
const body = '# 함수와 상태의 수명\n\n화면 검증용 예시입니다. 함수는 선언된 환경을 기억합니다.\n\n## 독립적인 환경\n\n각 호출에서 만든 변수를 별도로 보관합니다.\n\n```javascript\nfunction counter() {\n  let value = 0;\n  return () => ++value;\n}\n```\n\n외부 함수가 끝난 뒤에도 내부 함수가 변수를 참조할 수 있습니다.\n\n';
const target = { kind: 'interpretation', id: 'interpretation', unit_id: null, title: '예시 · 함수와 상태의 수명', href: '/interpretations/interpretation', revision: 1 };
const resource = { id: 'resource', note_id: null, kind: 'text', name: '예시 · 함수가 기억하는 환경', url: null, content: '최신 버전의 원문입니다.', revision: 2, state: 'ready', error: '', archived: 0, updated_at: date, versions: [{ revision: 2, created_at: date }, { revision: 1, created_at: date }], feed_pending: false };
const interpretation = { id: 'interpretation', resource_id: 'resource', revision: 1, current_revision: 2, source_name: resource.name, state: 'ready', archived: 0, error: '', created_at: date, model: 'fixture', document: { title: '예시 · 함수는 어떻게 이전 환경을 기억할까요?', summary: '함수와 선언 당시 환경을 함께 살펴봅니다. 변수가 만들어진 시점과 참조가 이어지는 범위를 직접 설명해보세요.', concepts: ['클로저', '렉시컬 환경', '상태 보존'], sections: [
  { id: 's1', title: '선언된 환경을 기억하기', body: '함수는 선언된 위치를 기준으로 외부 변수에 접근합니다.\n\n내부 함수를 반환하면 외부 함수의 실행이 끝난 뒤에도 그 환경을 참조할 수 있습니다.', prerequisites: [], source_quotes: ['함수는 선언된 환경을 기억합니다.'], examples: ['두 카운터를 만들어 각각 호출하고 값을 비교해보세요.'], extensions: ['외부에서 직접 수정하지 않는 상태를 구성할 수 있습니다.'], questions: ['외부 함수가 끝난 뒤에도 값을 읽는 이유는 무엇인가요?'] },
  { id: 's2', title: '독립적인 상태를 비교하기', body: '함수를 다시 호출하면 새로운 환경이 만들어집니다.', prerequisites: ['s1'], source_quotes: ['각 호출에서 만든 변수를 별도로 보관합니다.'], examples: [], extensions: [], questions: ['두 카운터는 서로에게 영향을 줄까요?'] }
] } };
const reference = { id: 'reference', title: '예시 · 상태의 소유권을 정하는 방법', user_body: body, targets: [target], revision: 1, updated_at: date, ai: { purpose: '공유하는 상태와 독립적인 상태를 구분합니다.', explanation: '호출마다 만들어지는 환경을 비교하며 값의 수명을 확인합니다.', conditions: '동일한 실행 맥락에서 값을 참조할 때 적용합니다.', procedure: '선언 위치를 찾고, 호출 경로를 비교합니다.', examples: body, cautions: '예시를 직접 실행하고 경계 조건을 확인하세요.', verification: '독립적인 카운터 두 개를 비교합니다.' }, ai_job: null, ai_created_at: date, ai_sources: [], stale: false, jobs: [], versions: [{ revision: 1, created_at: date }] };
const unit = { id: 's1', title: '예시 · 함수가 기억하는 환경', objective: '변수의 생성과 참조 범위를 설명합니다.', concepts: ['클로저'], prerequisites: [], rationale: '상태를 나누는 기준부터 살펴봅니다.', lesson: [{ title: '선언과 호출', body, code: 'const count = 1;', output: '1', walkthrough: '선언 시점의 환경을 확인합니다.' }], pitfalls: ['호출 위치와 선언 위치를 구분하세요.'], checkpoints: [{ question: '환경은 언제 만들어지나요?', answer: '함수 호출 시점에 만들어집니다.' }] };
const course = { id: 'course', title: '예시 · 함수와 상태', description: '선언과 호출, 상태의 수명을 코드로 확인합니다.', summary: body, language: 'javascript', difficulty: 'beginner', concepts: ['클로저'], created_at: date, completed: 1, total: 4, units: [unit], sets: [], knowledge_added_units: {} };
const policy = { question_age_days: 7, resurfacing_days: 7, snooze_days: 3, question_limit: 3 };
let question = { id: 'question', parent_id: null, depth: 0, text: '예시 · 두 카운터는 왜 다른 값을 기억할까요?', context: '같은 함수를 호출했지만 별도의 환경이 만들어집니다.', status: 'open', links: [], targets: [target], note_id: null, revision: 1, updated_at: date };
let empty = false, todayFailure = false, sourceFailure = false;
let questions = [{ key: 'question', id: 'question', title: question.text, href: '/questions/question', created_at: date }];
await page.route('**/api/**', async route => {
  const req = route.request(), url = new URL(req.url()), path = url.pathname.slice(4);
  if (req.method() !== 'GET') {
    writes.push({ path, body: req.postDataJSON() });
    if (path === '/questions/question' && req.method() === 'PUT') { await new Promise(resolve => setTimeout(resolve, 300)); question = { ...question, ...req.postDataJSON(), revision: question.revision + 1 }; return route.fulfill({ json: question }); }
    if (path === '/study/visit') return route.fulfill({ json: {} });
    if (path === '/study/choice') { questions = []; return route.fulfill({ json: {} }); }
    throw new Error('Unexpected mutation: ' + path);
  }
  if (path === '/study/today' && todayFailure) return route.fulfill({ status: 503, json: { detail: '학습 활동을 불러오지 못했습니다.' } });
  if (path === '/resources/resource/versions/1' && sourceFailure) return route.fulfill({ status: 503, json: { detail: '원문을 불러오지 못했습니다.' } });
  let data;
  if (path === '/session') data = { user: { id: 'fixture', username: 'preview', admin: 1 }, setup_required: false };
  else if (path === '/health') data = { sandbox: true, ai: true, languages: [] };
  else if (path === '/related-questions') data = { items: [] };
  else if (path === '/learning-target') data = { target };
  else if (path === '/study/today') data = { day: '2026-11-16', policy, resume: empty ? [] : [{ ...target, updated_at: date }, { ...target, id: 'course', title: '예시 · 호출 순서와 실행 결과', href: '/learn/course', updated_at: date }], reviews: empty ? [] : [{ key: 'review', title: '예시 · 비동기 요청을 다시 시도하는 조건', href: '/reviews/material/review', due_at: date, in_progress: false }, { key: 'review2', title: '예시 · 객체의 참조와 값 복사', href: '/reviews/material/review', due_at: date, in_progress: true }], review_count: empty ? 0 : 2, questions: empty ? [] : questions };
  else if (path === '/study/recommendations') data = { items: empty ? [] : [{ key: 'recommendation', title: '예시 · 상태의 수명을 코드로 확인해보세요', reason: '남겨둔 카운터 질문과 최근 클로저 학습을 연결합니다.', uncertain: true, evidence: [{ id: 'question', title: question.text, href: '/questions/question' }], action: { href: '/learn/course', title: '개념 확인' } }], job: null, stale: false, generated_at: empty ? null : date };
  else if (path === '/resources') data = { items: empty ? [] : [{ ...resource, excerpt: '화면 검증용 자료입니다. 함수가 선언된 환경과 상태의 수명을 비교합니다.' }, { ...resource, id: 'resource2', name: '예시 · 실패한 요청을 안전하게 다시 보내기', kind: 'url', excerpt: '요청 식별자와 재시도 조건을 정리합니다.' }], total: empty ? 0 : 2, page: 1, pages: 1 };
  else if (path === '/resources/resource') data = { ...resource, archived: url.searchParams.get('archived') === 'true' ? 1 : 0 };
  else if (path === '/resources/resource/versions/1') data = { revision: 1, name: resource.name, content: body, url: 'https://example.com/original-v1' };
  else if (path === '/resources/resource/versions/2') data = resource;
  else if (path === '/interpretations/interpretation') data = interpretation;
  else if (path === '/interpretations') data = { items: empty ? [] : [{ ...interpretation, title: interpretation.document.title }], total: empty ? 0 : 1, page: 1, pages: 1 };
  else if (path.startsWith('/materials/')) data = { material: { state: 'eligible', reason: '' }, review: null };
  else if (path.startsWith('/spaced-reviews/source/')) data = { review: null };
  else if (path === '/spaced-reviews/review') data = { id: 'review', kind: 'interpretation', origin_id: 'interpretation', source_revision: 1, revision: 1, due_at: date, due: true, state: 'eligible', snapshot: { title: '예시 · 비동기 요청을 다시 시도하는 조건', body, authorship: 'ai' }, responses: [] };
  else if (path === '/spaced-reviews') data = { items: [], due_count: 0 };
  else if (path === '/me/reviews' || path === '/manual-problems/reviews') data = { items: [], due_count: 0 };
  else if (path === '/technical-references') data = { items: empty ? [] : [reference], total: empty ? 0 : 1, page: 1, pages: 1 };
  else if (path === '/technical-references/reference') data = reference;
  else if (path === '/problem-books/catalog') data = { items: empty ? [] : [{ id: 'book', title: '예시 · 함수와 상태 연습', language: 'javascript', source: 'manual', href: '/problem-books/book', count: 5, solved: 2, due: 1, archived: false }] };
  else if (path === '/questions/question') data = question;
  else if (path === '/learning-targets') data = { items: [target] };
  else if (path === '/questions') data = { items: empty ? [] : [question], total: empty ? 0 : 1, page: 1, pages: 1 };
  else if (path === '/contexts') data = { items: empty ? [] : [course], total: empty ? 0 : 1, page: 1, pages: 1 };
  else if (path === '/contexts/course') data = course;
  else if (path === '/worksheets') data = { items: [], total: 0, page: 1, pages: 1 };
  else if (path === '/feed-posts') data = { items: [], total: 0, page: 1, pages: 1, feeds: [{ id: 'feed', name: 'Korean FE Article', url: 'https://example.com/technology/frontend/articles/rss/feed.xml', enabled: 1, succeeded: date, error: '' }], error: '' };
  else { unhandled.push(path); return route.fulfill({ status: 404, json: { detail: 'Missing test fixture: ' + path } }); }
  return route.fulfill({ json: data });
});
const routes = [
  ['today', '/', '.today-board'], ['library', '/library', '.reference-list'], ['source', '/library/resource', '.reading-workspace'],
  ['interpretation', '/interpretations/interpretation', '.reading-source'], ['references', '/technical-references', '.reference-document-card'],
  ['reference', '/technical-references/reference', '.reference-layout'], ['question', '/questions/question', '.question-reading'],
  ['note', '/references/new', '.reference-editor-body'], ['source-form', '/library/new/reference', '.library-register'],
  ['questions', '/questions', '.question-row'], ['reviews', '/reviews', '.review-panel'], ['courses', '/courses', '.context-card'],
  ['course', '/learn/course', '.course-unit'], ['lesson', '/learn/course/units/s1', '.lesson-article'], ['practice', '/explore/practice', '.practice-options'], ['practice-catalog', '/explore/practice/catalog', '.practice-book-list'], ['inbox', '/inbox', '.workspace-empty']
];
try {
  await mkdir(output, { recursive: true });
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    for (const [name, path, selector] of routes) {
      await page.goto('http://127.0.0.1:5173' + path);
      await page.locator(selector).first().waitFor();
      await page.locator('main').evaluate(node => Promise.all(node.getAnimations().map(animation => animation.finished.catch(() => {}))));
      assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false, `${name}: overflow at ${width}`);
      if (name === 'today') {
        const box = await page.locator('.resume-card').boundingBox();
        assert.ok(box.height < 240, `Resume too tall: ${width}`);
        assert.ok((await page.getByRole('heading', { name: '오늘의 복습', exact: true }).boundingBox()).y < 700, 'Reviews pushed below the first screen');
      }
      if (width === 1440 || width === 390) await page.screenshot({ path: `${output}${name}-${width}.png`, fullPage: true });
      checks.push(`${name}@${width}`);
    }
  }
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('http://127.0.0.1:5173/inbox');
    await page.locator('.feed-settings summary').click();
    await page.locator('.feed-add-form').waitFor();
    const summary = await page.locator('.feed-settings summary').evaluate(node => ({ border: getComputedStyle(node).borderBottomWidth, radius: getComputedStyle(node).borderRadius }));
    assert.equal(summary.border, '0px'); assert.equal(summary.radius, '0px');
    assert.equal(await page.locator('.feed-settings .disclosure-indicator').evaluate(node => getComputedStyle(node).borderWidth), '0px');
    const heading = await page.locator('.feed-source-heading').boundingBox(), url = await page.locator('.feed-source-info > a').boundingBox();
    assert.ok(url.y >= heading.y + heading.height, 'Feed URL must have its own row');
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: `${output}feed-settings-${width}.png`, fullPage: true });
    await page.goto('http://127.0.0.1:5173/explore/practice');
    await page.locator('.practice-path').first().waitFor();
    const paths = await page.locator('.practice-path').all();
    const first = await paths[0].boundingBox(), second = await paths[1].boundingBox();
    if (width > 700) { assert.equal(first.y, second.y); assert.ok(second.x >= first.x + first.width); }
    else assert.ok(second.y >= first.y + first.height);
    await paths[0].click();
    await page.waitForURL('**/explore/practice/catalog');
    await page.getByRole('link', { name: /자료구조/ }).waitFor();
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto('http://127.0.0.1:5173/questions/question');
  await page.getByRole('heading', { name: question.text, exact: true }).waitFor();
  assert.equal(await page.locator('main textarea').count(), 0);
  assert.equal(await page.getByText('AI 탐구 가이드').count(), 0);
  await page.getByRole('button', { name: '수정', exact: true }).click();
  await page.getByLabel('설명', { exact: true }).fill('수정한 맥락');
  await page.getByRole('button', { name: '변경 저장' }).click();
  await page.locator('button[aria-busy="true"] .button-spinner').waitFor();
  await page.getByRole('heading', { name: question.text, exact: true }).waitFor();
  await page.getByText('수정한 맥락', { exact: true }).waitFor();
  await page.getByRole('button', { name: '수정', exact: true }).click();
  await page.getByLabel('설명', { exact: true }).fill('취소할 맥락');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', { name: '취소', exact: true }).click();
  await page.getByText('수정한 맥락', { exact: true }).waitFor();
  for (const old of ['/problem-books', '/framework-practice', '/worksheets/retired']) {
    await page.goto('http://127.0.0.1:5173' + old);
    await page.waitForURL('**/explore/practice');
  }
  await page.goto('http://127.0.0.1:5173/technical-references/new');
  const textarea = page.getByLabel('내 설명 · 적용 경험 · 아직 궁금한 점');
  await textarea.focus();
  const focus = await textarea.evaluate(node => ({ outline: getComputedStyle(node).outlineWidth, shadow: getComputedStyle(node).boxShadow, parentShadow: getComputedStyle(node.closest('main')).boxShadow }));
  assert.equal(focus.outline, '1px'); assert.equal(focus.shadow, 'none'); assert.equal(focus.parentShadow, 'none');
  await page.screenshot({ path: `${output}focus-1440.png`, fullPage: true });
  await page.goto('http://127.0.0.1:5173/references/new');
  await page.getByRole('region', { name: '노트 본문 에디터' }).waitFor();
  assert.equal(await page.getByText('개념 지도에 추가하기').count(), 0);
  await page.getByText('출처 기록', { exact: false }).click();
  const fields = page.locator('.reference-fields'); await fields.waitFor();
  const sizes = await fields.locator('input, select').evaluateAll(nodes => nodes.map(node => ({ w: node.getBoundingClientRect().width, h: node.getBoundingClientRect().height })));
  assert.equal(new Set(sizes.map(size => Math.round(size.w))).size, 1); assert.equal(new Set(sizes.map(size => size.h)).size, 1);
  await page.screenshot({ path: `${output}metadata-1440.png`, fullPage: true });
  await page.goto('http://127.0.0.1:5173/');
  await page.getByRole('button', { name: '숨기기', exact: true }).click();
  await page.getByRole('heading', { name: '지금 다시 볼 질문이 없습니다' }).waitFor();
  assert.ok(writes.some(write => write.path === '/study/choice' && write.body.action === 'hide'));
  await page.getByRole('button', { name: '복습 시작', exact: true }).click();
  await page.waitForURL('**/reviews/material/review');
  await page.goto('http://127.0.0.1:5173/library/resource');
  await page.locator('.reading-navigation').getByRole('button', { name: /v1/ }).click();
  await page.getByRole('button', { name: '최신 본문으로' }).waitFor();
  assert.ok((await page.locator('#resource-body').innerText()).includes('당시 원문 URL'));
  assert.ok(!(await page.locator('#resource-body').innerText()).includes('최신 버전의 원문입니다.'));
  await page.getByRole('button', { name: '최신 본문으로' }).click();
  assert.ok((await page.locator('#resource-body').innerText()).includes('최신 버전의 원문입니다.'));
  sourceFailure = true;
  await page.goto('http://127.0.0.1:5173/interpretations/interpretation');
  await page.getByRole('button', { name: '원문 다시 불러오기' }).waitFor();
  sourceFailure = false;
  await page.getByRole('button', { name: '원문 다시 불러오기' }).click();
  await page.getByRole('region', { name: '원문 v1' }).waitFor();
  assert.ok(!(await page.locator('.reading-source').innerText()).includes('최신 버전의 원문입니다.'));
  await page.locator('.reading-navigation a[href="#s2"]').click();
  assert.ok((await page.locator('#s2').boundingBox()).y >= 72);
  empty = true;
  for (const [name, path] of routes.filter(([name]) => ['today', 'library', 'references', 'books', 'questions', 'courses'].includes(name))) {
    await page.goto('http://127.0.0.1:5173' + path);
    await page.locator('.workspace-empty').first().waitFor();
    if (name === 'today') await page.getByRole('heading', { name: '새로운 학습을 시작하세요' }).waitFor();
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({ path: `${output}${name}-empty.png`, fullPage: true });
  }
  todayFailure = true;
  await page.goto('http://127.0.0.1:5173/');
  await page.getByRole('alert').waitFor();
  assert.equal(await page.getByRole('heading', { name: '새로운 학습을 시작하세요' }).count(), 0, 'Error must not look like an empty account');
  todayFailure = false;
  await page.getByRole('button', { name: '다시 불러오기', exact: true }).click();
  await page.getByRole('heading', { name: '새로운 학습을 시작하세요' }).waitFor();
  assert.deepEqual(errors, []); assert.deepEqual(unhandled, []);
  assert.ok(writes.every(write => ['/study/visit', '/study/choice', '/questions/question'].includes(write.path)), 'Only authorized fixture mutations during QA');
  const report = { checks, widths: [1440, 1024, 768, 390], interactions: ['question read/edit/save/cancel', 'centered busy spinner', 'thin input focus with no panel halo', 'retired route redirects', 'metadata alignment', 'feed management border/row alignment', 'practice mode/catalog navigation', 'question hide', 'review start', 'version switch/reset', 'historical source URL', 'source error/retry', 'section anchor', 'empty collections', 'today error/retry'], errors, unhandled, writes: writes.filter(write => write.path !== '/study/visit') };
  await writeFile(`${output}checks.json`, JSON.stringify(report, null, 2) + '\n');
  console.log(`Passed ${checks.length} responsive page checks and ${report.interactions.length} interaction/state checks.`);
} finally { await browser.close(); }

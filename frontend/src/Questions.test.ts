import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

const question = { id: 'question', parent_id: null, text: '저장 결과를 어떻게 유지할까?', context: '', status: 'open', links: [], note_id: null, revision: 1, updated_at: '2026-11-12T03:00:00Z' };
const recommendation = { id: 'daily', source_kind: 'feed', source_title: '검토할 원문', source_url: 'https://example.com', text: '근거를 읽고 질문을 확인해보세요.', saved_question_id: null, state: 'ready', error: '', evidence: '원문에 있는 근거' };
const guide = { id: 'guide', state: 'ready', error: '', question_revision: 1, result: { title: '이전 가이드를 유지합니다', reading: '확인할 구절', checks: ['경계 조건 확인'], practice: '직접 비교하기', expected_output: '관찰한 결과', source_ids: [] } };

function render(Component: Parameters<typeof createElement>[0], props: object) {
  return renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Component, props)));
}

test('daily loading, generation, save and failure keep the same layout slots and action footprint', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { DailyQuestionCard } = await server.ssrLoadModule('/src/DailyQuestion.tsx');
    const defaults = { error: '', loading: false, busy: false, expanded: false, onExpand() {}, onSave() {}, onReload() {} };
    const cases = [null, ...['queued', 'running', 'ready', 'failed'].map(state => ({ day: '2026-11-12', reason: '', recommendation: { ...recommendation, state } })),
      { day: '2026-11-12', reason: '추천할 자료가 없습니다.', recommendation: null },
      { day: '2026-11-12', reason: '', recommendation: { ...recommendation, saved_question_id: 'saved' } }];
    for (const data of cases) {
      const html = render(DailyQuestionCard, { ...defaults, data, loading: !data });
      for (const slot of ['daily-question-heading', 'daily-question-date', 'daily-question-feedback', 'daily-question-source', 'daily-question-copy', 'daily-question-content', 'daily-question-actions', 'daily-question-primary', 'daily-question-source-action', 'daily-question-evidence-slot']) {
        assert.ok(html.includes(`class="${slot}"`), `${slot} is missing for ${data?.recommendation?.state ?? 'initial/empty'}`);
      }
      assert.equal((html.match(/\bdaily-question-expand\b/g) ?? []).length, 1);
    }
    const saving = render(DailyQuestionCard, { ...defaults, data: cases[3], busy: true });
    assert.match(saving, /근거를 읽고 질문을 확인해보세요/);
    assert.match(saving, /원문에 있는 근거/);
    assert.match(saving, /질문을 저장하고 있습니다/);
    assert.match(saving, /질문함에 저장/);
    assert.doesNotMatch(saving, /질문을 불러오는 중/);
    const loading = render(DailyQuestionCard, { ...defaults, data: null, loading: true });
    assert.match(loading, /질문을 불러오는 중/);
    assert.match(loading, /data-slot="skeleton"/);
  } finally { await server.close(); }
});

test('question refresh retains rows, while first load and a different query render row skeletons', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionResults } = await server.ssrLoadModule('/src/QuestionList.tsx');
    const refreshed = render(QuestionResults, { data: { items: [question], total: 1, page: 1 }, loading: true, query: '' });
    assert.match(refreshed, /aria-busy="true"/);
    assert.match(refreshed, /href="\/questions\/question"/);
    assert.match(refreshed, /저장 결과를 어떻게 유지할까/);
    assert.doesNotMatch(refreshed, /data-slot="skeleton"|아직 질문이 없습니다/);
    const initial = render(QuestionResults, { data: null, loading: true, query: '다른 검색' });
    assert.equal((initial.match(/question-row-skeleton/g) ?? []).length, 3);
    assert.doesNotMatch(initial, /href="\/questions\/question"|검색 결과가 없습니다/);
    const empty = render(QuestionResults, { data: { items: [], total: 0, page: 1 }, loading: false, query: '없음' });
    assert.match(empty, /검색 결과가 없습니다/);
  } finally { await server.close(); }
});

test('guide regeneration leaves the previous guide visible instead of replacing it with a loading message', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionGuideContent } = await server.ssrLoadModule('/src/QuestionGuide.tsx');
    const regenerating = render(QuestionGuideContent, { guide, revision: 2, pending: true });
    assert.match(regenerating, /aria-busy="true"/);
    assert.match(regenerating, /이전 가이드를 유지합니다/);
    assert.match(regenerating, /질문이 변경된 이전 가이드입니다/);
    assert.doesNotMatch(regenerating, /data-slot="skeleton"/);
    const initial = render(QuestionGuideContent, { guide: null, revision: 1, pending: true });
    assert.match(initial, /question-guide-skeleton/);
    assert.match(initial, /가이드를 준비하고 있습니다/);
  } finally { await server.close(); }
});


test('follow-up rows keep semantic nesting, detail links and ancestor context', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionRows } = await server.ssrLoadModule('/src/QuestionList.tsx');
    const html = render(QuestionRows, { items: [
      { ...question, matches_filter: false, status: 'done' },
      { ...question, id: 'child', parent_id: 'question', text: '이어서 묻기', depth: 1 },
      { ...question, id: 'leaf', parent_id: 'child', text: '한 번 더 묻기', depth: 2 },
    ] });
    assert.equal((html.match(/<ul class="question-tree">/g) ?? []).length, 3);
    assert.match(html, /href="\/questions\/child"/);
    assert.match(html, /href="\/questions\/leaf"/);
    assert.match(html, /맥락을 위한 상위 질문/);
    assert.match(html, /꼬리질문/);
    assert.ok(html.indexOf('이어서 묻기') < html.indexOf('한 번 더 묻기'));
  } finally { await server.close(); }
});


test('initial detail skeleton reserves the follow-up section before related sources', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionDetailSkeleton } = await server.ssrLoadModule('/src/QuestionSkeletons.tsx');
    const html = render(QuestionDetailSkeleton, {});
    assert.match(html, /question-follow-ups/);
    assert.match(html, /question-relation-skeleton/);
    assert.ok(html.indexOf('이어지는 질문') < html.indexOf('관련 자료'));
  } finally { await server.close(); }
});

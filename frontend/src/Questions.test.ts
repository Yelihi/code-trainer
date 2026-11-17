import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

const question = { id: 'question', parent_id: null, text: '저장 결과를 어떻게 유지할까?', context: '', status: 'open', links: [], note_id: null, revision: 1, updated_at: '2026-11-12T03:00:00Z' };
const guide = { id: 'guide', state: 'ready', error: '', question_revision: 1, result: { title: '이전 가이드를 유지합니다', reading: '확인할 구절', checks: ['경계 조건 확인'], practice: '직접 비교하기', expected_output: '관찰한 결과', source_ids: [] } };

function render(Component: Parameters<typeof createElement>[0], props: object) {
  return renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Component, props)));
}

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


test('initial question detail reserves only description and reference material', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionDetailSkeleton } = await server.ssrLoadModule('/src/QuestionSkeletons.tsx');
    const html = render(QuestionDetailSkeleton, {});
    assert.match(html, /설명/);
    assert.match(html, /참고 자료/);
    assert.doesNotMatch(html, /이어지는 질문|AI 탐구 가이드|내 언어로 정리/);
  } finally { await server.close(); }
});

test('question reading keeps saved context and reference links without downstream tools or forms', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { QuestionReading } = await server.ssrLoadModule('/src/QuestionDetail.tsx');
    const html = render(QuestionReading, { question: { ...question, context: '저장한 설명\n다음 줄', targets: [{ kind: 'resource', id: 'source', unit_id: '', title: '참고할 원문', href: '/library/source', revision: 1 }] } });
    assert.match(html, /저장한 설명\n다음 줄/);
    assert.match(html, /href="\/library\/source"/);
    assert.doesNotMatch(html, /<textarea|<input|AI 탐구 가이드|레퍼런스로 정리|이어지는 질문/);
    const { Button } = await server.ssrLoadModule('/src/components/ui/button.tsx');
    const busy = renderToStaticMarkup(createElement(Button, { loading: true }, '질문 저장'));
    assert.match(busy, /aria-busy="true"/);
    assert.match(busy, /disabled=""/);
    assert.match(busy, /button-spinner/);
    assert.match(busy, /button-loading-label">질문 저장/);
    assert.doesNotMatch(renderToStaticMarkup(createElement(Button, null, '질문 저장')), /button-spinner|aria-busy/);
  } finally { await server.close(); }
});

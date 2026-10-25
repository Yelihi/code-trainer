import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('learner preview preserves partial answers, labels authorship and escapes markup', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { PracticeRecordText } = await server.ssrLoadModule('/src/PracticeRecords.tsx');
    const html = renderToStaticMarkup(createElement(PracticeRecordText, { worksheet: { document: { questions: [{ id: 'q1' }, { id: 'q2' }] } }, content: { answers: { q1: '<script>private()</script>' }, summary: '**내 요약**' } }));
    assert.match(html, /내가 작성한 학습 기록/);
    assert.match(html, /아직 작성하지 않았습니다/);
    assert.match(html, /&lt;script&gt;/);
    assert.match(html, /<strong>내 요약<\/strong>/);
    assert.doesNotMatch(html, /<script|정답|채점/);
  } finally { await server.close(); }
});

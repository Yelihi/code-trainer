import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

test('general interpretation separates literal evidence and AI content without coding requirements', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { InterpretationDocument } = await server.ssrLoadModule('/src/Interpretations.tsx');
    const document = { title: '관찰', summary: '가설을 검토합니다.', concepts: ['관찰'], sections: [
      { id: 's1', title: '관찰 시작', body: '관찰을 기록합니다.', prerequisites: [], source_quotes: ['<script>alert(1)</script>'], examples: ['오늘의 기록'], extensions: ['비교 관찰'], questions: ['관찰과 가설의 차이는?'] },
      { id: 's2', title: '비교', body: '기록을 비교합니다.', prerequisites: ['s1'], source_quotes: ['원문 인용'], examples: [], extensions: [], questions: ['무엇이 다른가요?'] },
    ] };
    const html = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(InterpretationDocument, { document })));
    for (const text of ['AI 해석', '원문 근거', 'AI 예시', 'AI 확장', '스스로 확인할 질문']) assert.ok(html.includes(text), text);
    assert.match(html, /href="#s1"/);
    assert.match(html, /&lt;script&gt;/);
    assert.doesNotMatch(html, /<script|문제 생성|실행 언어|<textarea/);
  } finally { await server.close(); }
});

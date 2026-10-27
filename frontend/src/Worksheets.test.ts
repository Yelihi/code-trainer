import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

test('worksheet labels AI questions and links their interpretation sections without showing answers', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { WorksheetDocument } = await server.ssrLoadModule('/src/Worksheets.tsx');
    const document = { title: '관찰', questions: [{ id: 'q1', section_id: 's1', prompt: '<script>alert(1)</script> 관찰과 가설의 차이는?' }] };
    const html = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(WorksheetDocument, { document, interpretationId: 'interpretation-id' })));
    assert.match(html, /AI가 만든 질문/);
    assert.match(html, /href="\/interpretations\/interpretation-id#s1"/);
    assert.match(html, /&lt;script&gt;/);
    assert.doesNotMatch(html, /<script|정답 보기|채점|<textarea/);
  } finally { await server.close(); }
});

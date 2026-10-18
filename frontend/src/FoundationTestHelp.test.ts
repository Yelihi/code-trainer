import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('test help starts with the relevant calling convention and keeps the dialog closed', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { FoundationTestHelp } = await server.ssrLoadModule('/src/FoundationTestHelp.tsx');
    const render = (starter: string) => renderToStaticMarkup(createElement(FoundationTestHelp, { starter, example: 'assertEqual(1, 1);' }));
    const classHelp = render('class Queue {}');
    assert.match(render('function hash() {}\nclass Dictionary {}'), /aria-pressed="true">클래스 테스트/);
    const functionHelp = render('function bfs() {}');
    assert.match(classHelp, /aria-haspopup="dialog"/);
    assert.match(classHelp, /<dialog[^>]+aria-labelledby=/);
    assert.doesNotMatch(classHelp, /<dialog[^>]*\sopen/);
    assert.match(classHelp, /aria-pressed="true">클래스 테스트/);
    assert.match(classHelp, /객체를 만들고/);
    assert.match(functionHelp, /aria-pressed="true">함수 테스트/);
    assert.match(functionHelp, /반환값을 비교/);
    assert.match(classHelp, /현재 단원의 실행 예시/);
    assert.match(functionHelp, /실제로 실행되는/);
  } finally { await server.close(); }
});

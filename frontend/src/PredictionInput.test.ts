import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('prediction rows preserve saved output, blank lines and the shared answer limit', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { PredictionInput, replaceOutputLine } = await server.ssrLoadModule('/src/PredictionInput.tsx');
    const render = (answer: string, disabled = false) => renderToStaticMarkup(createElement(PredictionInput, { answer, disabled, onChange() {} }));
    const html = render('1 2\n\n  true  \n');
    assert.equal((html.match(/<input/g) ?? []).length, 4);
    assert.match(html, /value=" {2}true {2}"/);
    assert.match(html, /예상 출력 4번째 줄/);
    assert.equal((render('').match(/<input/g) ?? []).length, 1);
    assert.equal((render('a\nb', true).match(/disabled=""/g) ?? []).length, 5);
    assert.match(render('x'.repeat(3998) + '\ny'), /maxLength="1"/);
    assert.match(render('x'.repeat(4000)), /disabled="">\+ 출력 줄 추가/);

    assert.equal(replaceOutputLine('1 2\n\n  true  \n', 1, 'false'), '1 2\nfalse\n  true  \n');
    assert.equal(replaceOutputLine('first\nlast', 0, 'first\n'), 'first\n\nlast');
    assert.equal(replaceOutputLine('first\nlast', 1, 'last\n'), 'first\nlast\n');
    assert.equal(replaceOutputLine('first\nlast', 0, 'a\n\nb'), 'a\n\nb\nlast');
    assert.equal(replaceOutputLine('first\n\nlast', 1, null), 'first\nlast');
    assert.equal(replaceOutputLine('first\nlast', 0, null), 'last');
    assert.equal(replaceOutputLine('first\nlast', 1, null), 'first');
    assert.equal(replaceOutputLine('first', 0, ''), '');
  } finally {
    await server.close();
  }
});

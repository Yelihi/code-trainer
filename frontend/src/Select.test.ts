import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('shared select keeps native form, label, option and listbox semantics', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { Select } = await server.ssrLoadModule('/src/Select.tsx');
    const options = [createElement('option', { key: 'js', value: 'js' }, 'JavaScript'), createElement('option', { key: 'ts', value: 'ts' }, 'TypeScript')];
    const html = renderToStaticMarkup(createElement('label', { htmlFor: 'language' }, '연습 언어', createElement(Select, {
      id: 'language', name: 'language', defaultValue: 'ts', required: true, disabled: true, 'aria-describedby': 'language-help',
    }, ...options)));
    assert.match(html, /<label for="language">/);
    assert.match(html, /<select[^>]*id="language"[^>]*name="language"[^>]*required=""[^>]*disabled=""[^>]*aria-describedby="language-help"/);
    assert.match(html, /<option value="ts" selected="">TypeScript<\/option>/);
    assert.match(html, /class="select-chevron" aria-hidden="true"/);
    assert.doesNotMatch(html, /<button|tabindex=|role=/);
    for (const props of [{ multiple: true, defaultValue: ['js', 'ts'] }, { size: 4, defaultValue: 'js' }]) {
      const list = renderToStaticMarkup(createElement(Select, { ...props, 'aria-label': '언어 선택' }, ...options));
      assert.doesNotMatch(list, /select-chevron/);
      assert.match(list, /<select[^>]*aria-label="언어 선택"/);
    }
  } finally { await server.close(); }
});

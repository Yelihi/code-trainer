import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

test('five navigation areas preserve destination identity, current page and admin visibility', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { Navigation, PlannedFeature, PracticeEntry } = await server.ssrLoadModule('/src/Navigation.tsx');
    const render = (path: string, isAdmin = false) => renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [path] }, createElement(Navigation, { isAdmin, onNavigate() {} })));
    const html = render('/library');
    assert.deepEqual([...html.matchAll(/<nav aria-label="([^"]+)"/g)].map(match => match[1]), ['등록하기', '탐구하기', '데이터 쌓기', '응용하기', '설정']);
    assert.doesNotMatch(html, /\/admin\//);
    assert.match(render('/admin/operations', true), /href="\/admin\/operations"/);
    assert.match(render('/admin/sources/source-id', true), /href="\/admin\/sources"/);
    const cases = [
      ['/', '/explore'], ['/explore?page=2', '/explore'], ['/learn/context/units/unit', '/explore'],
      ['/create?post=123&url=https%3A%2F%2Fexample.com&title=test', '/explore'],
      ['/library/source-id/edit', '/library'], ['/library/new/reference', '/library/new/reference'],
      ['/references/new', '/references/new'], ['/references/note-id', '/library'],
      ['/foundations/arrays/practice', '/explore/practice'], ['/practice/set-id', '/explore/practice'],
      ['/reviews/set-id', '/reviews'], ['/reference-reviews/review-id', '/reviews'],
      ['/knowledge/candidates', '/knowledge/candidates'], ['/knowledge', '/knowledge'],
      ['/apply', '/apply'], ['/settings/ai', '/settings/ai'], ['/github/share', '/settings/github'],
    ];
    for (const [path, target] of cases) {
      const active = [...render(path).matchAll(/<a\b[^>]*aria-current="page"[^>]*>/g)];
      assert.equal(active.length, 1, path);
      assert.ok(active[0][0].includes(`href="${target}"`), path);
    }
    assert.doesNotMatch(render('/library-unknown'), /aria-current="page"/);
    for (const feature of ['candidates', 'inside', 'ai']) {
      const page = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(PlannedFeature, { feature })));
      assert.match(page, /준비 중/);
      assert.doesNotMatch(page, /<input|<form|<button/);
      assert.match(page, /href="\/(references|knowledge|me)"/);
    }
    const practice = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(PracticeEntry)));
    assert.match(practice, /href="\/foundations"/);
    assert.match(practice, /href="\/explore"/);
  } finally { await server.close(); }
});

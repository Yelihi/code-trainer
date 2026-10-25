import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { createServer } from 'vite';

test('five navigation areas preserve destination identity, current page and admin visibility', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { Navigation, PracticeEntry } = await server.ssrLoadModule('/src/Navigation.tsx');
    const render = (path: string, isAdmin = false) => renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [path] }, createElement(Navigation, { isAdmin, onNavigate() {} })));
    const html = render('/library');
    assert.deepEqual([...html.matchAll(/<nav aria-label="([^"]+)"/g)].map(match => match[1]), ['등록하기', '탐구하기', '데이터 쌓기', '응용하기', '설정']);
    assert.doesNotMatch(html, /\/admin\//);
    assert.match(render('/admin/operations', true), /href="\/admin\/operations"/);
    assert.match(render('/admin/sources/source-id', true), /href="\/admin\/sources"/);
    const cases = [
      ['/', '/explore'], ['/explore?page=2', '/explore'], ['/learn/context/units/unit', '/explore'],
      ['/interpretations/document-id', '/explore'],
      ['/create?post=123&url=https%3A%2F%2Fexample.com&title=test', '/explore'],
      ['/library/source-id/edit', '/library'], ['/library/new/reference', '/library/new/reference'],
      ['/references/new', '/references/new'], ['/references/note-id', '/library'],
      ['/foundations/arrays/practice', '/explore/practice'], ['/practice/set-id', '/explore/practice'],
      ['/worksheets/worksheet-id', '/explore/practice'],
      ['/reviews/material/id', '/reviews'], ['/reviews/set-id', '/reviews'], ['/reference-reviews/review-id', '/reviews'],
      ['/knowledge/candidates', '/knowledge/candidates'], ['/knowledge', '/knowledge'],
      ['/apply', '/apply'], ['/settings/ai', '/settings/ai'], ['/github/share', '/settings/github'],
    ];
    for (const [path, target] of cases) {
      const active = [...render(path).matchAll(/<a\b[^>]*aria-current="page"[^>]*>/g)];
      assert.equal(active.length, 1, path);
      assert.ok(active[0][0].includes(`href="${target}"`), path);
    }
    assert.doesNotMatch(render('/library-unknown'), /aria-current="page"/);
    assert.doesNotMatch(render('/settings/ai').match(/<a[^>]*href="\/settings\/ai"[\s\S]*?<\/a>/)?.[0] ?? '', /예정/);
    assert.doesNotMatch(render('/apply').match(/<a[^>]*href="\/apply"[\s\S]*?<\/a>/)?.[0] ?? '', /예정/);
    const practice = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Routes, null,
      createElement(Route, { element: createElement(Outlet, { context: { userId: 'fixture-owner', health: null } }) },
        createElement(Route, { path: '*', element: createElement(PracticeEntry) })))));
    assert.match(practice, /href="\/foundations"/);
    assert.match(practice, /href="\/"/);
  } finally { await server.close(); }
});

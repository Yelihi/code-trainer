import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { createServer } from 'vite';

test('three learning menus preserve current page and admin visibility', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { Navigation, PracticeEntry, PracticeCatalog } = await server.ssrLoadModule('/src/Navigation.tsx');
    const render = (path: string, isAdmin = false) => renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [path] }, createElement(Navigation, { isAdmin, onNavigate() {} })));
    const html = render('/library');
    assert.deepEqual([...html.matchAll(/<nav aria-label="([^"]+)"/g)].map(match => match[1]), ['주요 메뉴', '설정과 기록']);
    assert.doesNotMatch(html, /\/admin\//);
    assert.match(render('/admin/operations', true), /href="\/admin\/operations"/);
    assert.match(render('/admin/sources/source-id', true), /href="\/admin\/sources"/);
    const cases = [
      ['/', '/'], ['/learn/context/units/unit', '/library'], ['/practice/set-id', '/library'], ['/questions/id', '/'],
      ['/library/source-id/edit', '/library'], ['/library/new/reference', '/library'], ['/references/new', '/library'],
      ['/interpretations/id', '/library'], ['/explore?page=2', '/library'], ['/courses', '/library'], ['/explore/practice/catalog', '/library'],
      ['/problem-books', '/library'], ['/problem-books/problems/new', '/library'], ['/foundations', '/library'], ['/worksheets/id', '/library'], ['/technical-references/id', '/technical-references'], ['/reviews/material/id', '/'],
    ];
    for (const [path, target] of cases) {
      const active = [...render(path).matchAll(/<a\b[^>]*aria-current="page"[^>]*>/g)];
      assert.equal(active.length, 1, path);
      assert.ok(active[0][0].includes(`href="${target}"`), path);
    }
    assert.doesNotMatch(render('/library-unknown'), /aria-current="page"/);
    assert.doesNotMatch(render('/settings/ai').match(/<a[^>]*href="\/settings\/ai"[\s\S]*?<\/a>/)?.[0] ?? '', /예정/);
    assert.doesNotMatch(render('/apply').match(/<a[^>]*href="\/apply"[\s\S]*?<\/a>/)?.[0] ?? '', /예정/);
    const { MaterialsNavigation } = await server.ssrLoadModule('/src/WorkspaceUI.tsx');
    const materialMenu = (path: string) => renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: [path] }, createElement(MaterialsNavigation)));
    for (const path of ['/library', '/library/id', '/problem-books/problems/new', '/courses', '/foundations', '/interpretations/id']) {
      const menu = materialMenu(path);
      assert.match(menu, /aria-label="자료 메뉴"/);
      assert.doesNotMatch(menu, /href="\/problem-books"/);
      assert.equal([...menu.matchAll(/<a /g)].length, 2);
      assert.doesNotMatch(menu, /<details/);
      assert.equal([...menu.matchAll(/aria-current="page"/g)].length, 1);
    }
    assert.equal(materialMenu('/'), '');
    assert.match(materialMenu('/problem-books/id'), /<a[^>]*aria-current="page"[^>]*href="\/explore\/practice"/);
    const practice = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(Routes, null,
      createElement(Route, { element: createElement(Outlet, { context: { userId: 'fixture-owner', health: null } }) },
        createElement(Route, { path: '*', element: createElement(PracticeEntry) })))));
    assert.match(practice, /href="\/explore\/practice\/catalog"/);
    assert.doesNotMatch(practice, /href="\/foundations"/);
    const catalog = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(PracticeCatalog)));
    assert.match(catalog, /href="\/foundations"/);
    assert.match(catalog, /자료구조 · 알고리즘/);
    assert.match(practice, /href="\/courses"/);
    assert.doesNotMatch(practice, /framework-practice|질문지/);
  } finally { await server.close(); }
});

import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { createServer } from 'vite';

test('review URL selects one accessible panel and preserves loading instead of showing empty data', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const { Reviews } = await server.ssrLoadModule('/src/Reviews.tsx');
    const cases = [['materials', '자료 복습을 불러오는 중'], ['code', '코드 복습을 불러오는 중'], ['schedule', '복습 일정을 불러오는 중']];
    for (const [tab, loading] of cases) {
      const html = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: ['/reviews?tab=' + tab] }, createElement(Reviews)));
      assert.equal((html.match(/role="tab"/g) ?? []).length, 3);
      assert.equal((html.match(/aria-selected="true"/g) ?? []).length, 1);
      assert.match(html, new RegExp(loading));
      for (const [, other] of cases.filter(([key]) => key !== tab)) assert.doesNotMatch(html, new RegExp(other));
      assert.doesNotMatch(html, /복습에 추가한 자료가 없습니다|복습할 내 문제가 없습니다|복습할 코드 문제가 없습니다/);
    }
    const invalid = renderToStaticMarkup(createElement(MemoryRouter, { initialEntries: ['/reviews?tab=unknown'] }, createElement(Reviews)));
    assert.match(invalid, /자료 복습을 불러오는 중/);
  } finally { await server.close(); }
});

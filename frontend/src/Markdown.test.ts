import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('lesson markdown renders readable structure without executing embedded content', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true }, appType: 'custom' });
  try {
    const { Markdown } = await server.ssrLoadModule('/src/Markdown.tsx');
    const html = renderToStaticMarkup(createElement(Markdown, { language: 'typescript', children: [
      '## 참조 비교', '**같은 객체**와 `a === b`를 비교합니다.',
      '- 첫 번째\n- 두 번째', '> 값과 참조는 다릅니다.',
      '```ts\nconst a: number = 1;\n```', '```\nconst b = 2;\n```',
      '<script>alert(1)</script>', '<img src="x" onerror="alert(1)">',
      '[실행](javascript:alert%281%29)', '![외부 이미지](https://example.com/tracker.png)',
      '[출처](https://example.com/article)', '`<img onerror="alert(1)">`', '제네릭 표기 <T>를 유지합니다.',
    ].join('\n\n') }));
    assert.match(html, /<h3>참조 비교<\/h3>/);
    assert.match(html, /<strong>같은 객체<\/strong>/);
    assert.match(html, /<code>a === b<\/code>/);
    assert.match(html, /<ul>/);
    assert.match(html, /<blockquote>/);
    assert.equal((html.match(/class="code-snippet"/g) ?? []).length, 2);
    assert.doesNotMatch(html, /<script|<img|href="javascript:/i);
    assert.match(html, /&lt;img onerror=/);
    assert.match(html, /&lt;T&gt;를 유지합니다\./);
    assert.match(html, /href="https:\/\/example.com\/article" target="_blank" rel="noreferrer"/);
    const { codeExtensions } = await server.ssrLoadModule('/src/CodeBlock.tsx');
    const tree = codeExtensions('typescript')[0].language.parser.parse('const identity = <T>(value: T): T => value;');
    assert.doesNotMatch(tree.toString(), /⚠/, 'TypeScript generics must not be parsed as JSX');
  } finally {
    await server.close();
  }
});

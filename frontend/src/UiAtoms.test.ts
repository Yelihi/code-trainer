import assert from 'node:assert/strict';
import test from 'node:test';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { createServer } from 'vite';

test('shadcn form atoms keep labels, selected states and slider text accessible', async () => {
  const server = await createServer({ configFile: false, optimizeDeps: { noDiscovery: true }, server: { middlewareMode: true, hmr: false }, appType: 'custom' });
  try {
    const [{ Label }, { Checkbox }, { RadioGroup, RadioGroupItem }, { Slider }] = await Promise.all([
      server.ssrLoadModule('/src/components/ui/label.tsx'),
      server.ssrLoadModule('/src/components/ui/checkbox.tsx'),
      server.ssrLoadModule('/src/components/ui/radio-group.tsx'),
      server.ssrLoadModule('/src/components/ui/slider.tsx'),
    ]);
    const html = renderToStaticMarkup(createElement('form', null,
      createElement(Label, { htmlFor: 'consent' }, '동의'),
      createElement(Checkbox, { id: 'consent', checked: true }),
      createElement(RadioGroup, { name: 'review', value: 'yes' },
        createElement(RadioGroupItem, { id: 'yes', value: 'yes', 'aria-label': '스스로 설명 가능' })),
      createElement(Slider, { value: [2], min: 0, max: 5, 'aria-label': '단계 탐색', 'aria-valuetext': '3 / 6: 현재 단계' }),
    ));
    assert.match(html, /<label[^>]*for="consent"[^>]*>동의<\/label>/);
    assert.match(html, /role="checkbox"[^>]*aria-checked="true"/);
    assert.match(html, /role="radiogroup"/);
    assert.match(html, /role="radio"[^>]*aria-checked="true"/);
    assert.match(html, /role="slider"[^>]*aria-label="단계 탐색"[^>]*aria-valuetext="3 \/ 6: 현재 단계"/);
  } finally { await server.close(); }
});

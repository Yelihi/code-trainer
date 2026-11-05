import assert from 'node:assert/strict';
import test from 'node:test';
import { frameworkDocument } from './frameworkDocument.ts';

test('framework preview isolates code and keeps source out of HTML script boundaries', () => {
  const page = frameworkDocument({ html: '<h1>Hi</h1>', css: '', client: 'const text = "</script>";' }, 'window.vendor = "</script>";');
  assert.match(page, /script-src 'unsafe-inline' blob:;/);
  assert.match(page, /connect-src 'none'/);
  assert.match(page, /load\(.*window\.vendor/);
  assert.doesNotMatch(page, /const text = "<\/script>"/);
  assert.match(page, /\\u003c\/script>/);
});

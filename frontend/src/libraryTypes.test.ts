import { test } from 'node:test';
import assert from 'node:assert/strict';
import { libraryPage, readResourceFile, restoreResourceDraft } from './libraryTypes.ts';

test('a restored draft retains the replay identity and exact body but cannot cross resources', () => {
  const draft = { request_id: 'lost-response-request', kind: 'text', name: '원문', content: '  # 글\r\n', url: '', revision: 2, resource_id: 'resource-one' };
  assert.deepEqual(restoreResourceDraft(JSON.stringify(draft), 'resource-one'), draft);
  assert.equal(restoreResourceDraft(JSON.stringify(draft), 'resource-two'), null);
  for (const bad of ['{', 'null', JSON.stringify({ ...draft, revision: -1 }), JSON.stringify({ ...draft, content: {} }), JSON.stringify({ ...draft, kind: 'sample' })]) {
    assert.equal(restoreResourceDraft(bad, 'resource-one'), null);
  }
});
test('invalid and fractional URL pages never reach the API', () => {
  for (const input of [null, '', 'NaN', 'Infinity', '-1', '0', '1.5', '9007199254740992']) assert.equal(libraryPage(input), 1);
  assert.equal(libraryPage('3'), 3);
});

test('file import preserves UTF-8 text and rejects malformed, unsupported, empty and oversized input', async () => {
  const body = '  # 원문\r\n```js\nconst x = 1;\n```';
  assert.equal(await readResourceFile(new File([body], 'source.md')), body);
  for (const file of [new File(['x'], 'source.pdf'), new File([' '], 'empty.txt'),
    new File([new Uint8Array([0xff, 0xfe])], 'invalid.txt'), new File(['x'.repeat(60001)], 'long.md'),
    new File(['x'.repeat(240001)], 'huge.txt')]) await assert.rejects(readResourceFile(file));
});


test('RSA drafts cannot cross posts or leak into manual registration', () => {
  const draft = { request_id: 'rsa-response-request', feed_post_id: 'post-one', kind: 'url', name: '원문', content: '', url: 'https://example.com/original', revision: 0 };
  assert.deepEqual(restoreResourceDraft(JSON.stringify(draft), undefined, 'post-one'), draft);
  assert.equal(restoreResourceDraft(JSON.stringify(draft), undefined, 'post-two'), null);
  assert.equal(restoreResourceDraft(JSON.stringify(draft)), null);
  assert.equal(restoreResourceDraft(JSON.stringify({ ...draft, kind: 'text' }), undefined, 'post-one'), null);
  assert.equal(restoreResourceDraft(JSON.stringify({ ...draft, feed_post_id: undefined }), undefined, 'post-one'), null);
});

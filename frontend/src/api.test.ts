import assert from 'node:assert/strict';
import { test } from 'node:test';
import { api, ApiError, safeSourceUrl } from './api.ts';

test('API failures stay failures and attribution cannot execute a URL scheme', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => new Response(JSON.stringify({ detail: 'sandbox unavailable' }), { status: 503 });
    await assert.rejects(api('/health'), (error: unknown) => error instanceof ApiError && error.status === 503 && error.message === 'sandbox unavailable');
    globalThis.fetch = async () => new Response(JSON.stringify({ ok: true }), { status: 200 });
    assert.deepEqual(await api('/health'), { ok: true });
    assert.equal(safeSourceUrl('javascript:alert(1)'), undefined);
    assert.equal(safeSourceUrl('https://developer.mozilla.org/'), 'https://developer.mozilla.org/');
  } finally { globalThis.fetch = original; }
});

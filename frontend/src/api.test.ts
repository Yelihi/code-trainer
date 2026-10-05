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

test('Access expiry identifies the login flow and HTML is never accepted as API data', async () => {
  const original = globalThis.fetch;
  const events = new EventTarget();
  let authMode: unknown;
  events.addEventListener('session-expired', event => { authMode = (event as CustomEvent).detail; });
  Object.defineProperty(globalThis, 'window', { value: events, configurable: true });
  try {
    globalThis.fetch = async () => Response.json({ detail: 'expired' }, { status: 401, headers: { 'X-Trainer-Auth': 'access' } });
    await assert.rejects(api('/session'), (error: unknown) => error instanceof ApiError && error.status === 401);
    assert.equal(authMode, 'access');
    globalThis.fetch = async () => new Response('<html>Login</html>', { headers: { 'Content-Type': 'text/html' } });
    await assert.rejects(api('/session'), (error: unknown) => error instanceof ApiError && error.status === 502);
  } finally {
    globalThis.fetch = original;
    Reflect.deleteProperty(globalThis, 'window');
  }
});

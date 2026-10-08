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


test('Access expiry is handled without following login redirects or replaying a write', async () => {
  const original = globalThis.fetch;
  const events = new EventTarget();
  let expired = 0;
  events.addEventListener('session-expired', () => { expired++; });
  Object.defineProperty(globalThis, 'window', { value: events, configurable: true });
  try {
    let calls = 0;
    globalThis.fetch = async (_, init) => {
      calls++;
      assert.equal(new Headers(init?.headers).get('X-Requested-With'), 'XMLHttpRequest');
      assert.equal(init?.credentials, 'same-origin');
      assert.equal(init?.redirect, 'manual');
      return new Response('Access session expired', { status: 401 }); // Edge has no app-specific header.
    };
    await assert.rejects(api('/exercises/id/execute', 'POST', {}), (e: unknown) => e instanceof ApiError && e.status === 401);
    assert.equal(calls, 1); assert.equal(expired, 1);
    globalThis.fetch = async () => ({ type: 'opaqueredirect' }) as Response;
    await assert.rejects(api('/session'), (e: unknown) => e instanceof ApiError && e.status === 401);
    assert.equal(expired, 2);
    globalThis.fetch = async () => { throw new TypeError('Load failed'); };
    await assert.rejects(api('/health'), (e: unknown) => e instanceof ApiError && e.status === 0 && !e.message.includes('Load failed'));
    assert.equal(expired, 2); // Offline is not a login expiry.
    const controller = new AbortController(); controller.abort();
    globalThis.fetch = async () => { throw new DOMException('cancelled', 'AbortError'); };
    await assert.rejects(api('/health', 'GET', undefined, controller.signal), { name: 'AbortError' });
  } finally { globalThis.fetch = original; Reflect.deleteProperty(globalThis, 'window'); }
});

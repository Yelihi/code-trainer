const failure = (status, detail) => Response.json({ detail }, {
  status, headers: { 'Cache-Control': 'private, no-store', 'X-Trainer-Auth': 'access', 'X-Content-Type-Options': 'nosniff' },
});

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    // One production origin; previews and alternative hostnames cannot reach the API.
    if (url.origin !== env.PUBLIC_ORIGIN) return failure(403, '허용되지 않은 주소입니다.');
    const token = request.headers.get('cf-access-jwt-assertion');
    if (!token || token.length > 16384 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token)) {
      return failure(401, '이메일 인증 후 다시 접속해주세요.');
    }
    const isAPI = url.pathname === '/api' || url.pathname.startsWith('/api/');
    if (!isAPI) {
      const asset = await env.ASSETS.fetch(request);
      const response = new Response(asset.body, asset);
      response.headers.set('Cache-Control', 'private, no-store');
      response.headers.set('X-Content-Type-Options', 'nosniff');
      response.headers.set('Referrer-Policy', 'no-referrer');
      response.headers.set('X-Frame-Options', 'DENY');
      response.headers.set('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
      return response;
    }
    if (!['GET', 'HEAD'].includes(request.method) && (request.headers.get('origin') !== url.origin || request.headers.get('sec-fetch-site') === 'cross-site')) {
      return failure(403, '같은 서비스 화면에서 요청해주세요.');
    }
    if (!env.CODE_TRAINER_API) return failure(503, '서버 연결 설정이 필요합니다.');
    const target = new URL('http://127.0.0.1:8010');
    target.pathname = url.pathname;
    target.search = url.search;
    const headers = new Headers();
    for (const name of ['content-type', 'accept', 'origin', 'sec-fetch-site']) {
      if (request.headers.has(name)) headers.set(name, request.headers.get(name));
    }
    // Only Access's assertion is forwarded. The API verifies its signature/issuer/audience.
    headers.set('x-trainer-user-jwt', token);
    try {
      const upstream = await env.CODE_TRAINER_API.fetch(new Request(target, {
        method: request.method, headers, body: request.body, redirect: 'manual', signal: request.signal, duplex: 'half',
      }));
      if (upstream.status >= 300 && upstream.status < 400) {
        await upstream.body?.cancel();
        return failure(502, '서버 연결 인증을 확인해주세요.');
      }
      const outgoing = new Headers({ 'Cache-Control': 'private, no-store', 'X-Trainer-Auth': 'access', 'X-Content-Type-Options': 'nosniff' });
      for (const name of ['content-type', 'retry-after']) {
        if (upstream.headers.has(name)) outgoing.set(name, upstream.headers.get(name));
      }
      return new Response(upstream.body, { status: upstream.status, headers: outgoing });
    } catch { return failure(502, 'Mac mini 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.'); }
  },
};

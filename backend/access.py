"""Single-owner deployment authentication; identity is bound explicitly by the operator."""
import os
import re
from functools import lru_cache
from urllib.parse import urlsplit
from . import db, runner, service


def enabled():
    mode = os.environ.get('TRAINER_MODE', 'local')
    if mode not in ('local', 'server'):
        raise ValueError('TRAINER_MODE must be local or server')
    return mode == 'server'


def origin():
    return os.environ['TRAINER_PUBLIC_ORIGIN']


def validate_config():
    if not enabled():
        return
    parsed = urlsplit(origin())
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('TRAINER_PUBLIC_ORIGIN must be an HTTPS origin without a trailing slash')
    if not re.fullmatch(r'[a-z0-9-]+\.cloudflareaccess\.com', os.environ['TRAINER_ACCESS_DOMAIN']):
        raise ValueError('Invalid Cloudflare Access team domain')
    for name in ('AUDIENCE', 'SUBJECT', 'EMAIL', 'USER_ID'):
        if not os.environ.get('TRAINER_ACCESS_' + name, '').strip():
            raise ValueError('Missing TRAINER_ACCESS_' + name)
    if not db.path().is_file():
        raise ValueError('Import and verify the existing database before starting server mode')
    if not db.one('SELECT id FROM users WHERE id=?', (os.environ['TRAINER_ACCESS_USER_ID'],)):
        raise ValueError('The configured owner does not exist in the database')
    import jwt  # Missing dependencies must fail startup, never bypass authentication.
    runner.remote_client()


@lru_cache(maxsize=2)
def keys(domain):
    import jwt
    return jwt.PyJWKClient(f'https://{domain}/cdn-cgi/access/certs', timeout=5)


def user(request):
    import jwt
    tokens = request.headers.getlist('x-trainer-user-jwt')
    if len(tokens) != 1 or not tokens[0] or len(tokens[0]) > 16384:
        raise service.Error('이메일 인증 후 다시 접속해주세요.', 401)
    try:
        key = keys(os.environ['TRAINER_ACCESS_DOMAIN']).get_signing_key_from_jwt(tokens[0])
        claims = jwt.decode(tokens[0], key.key, algorithms=['RS256'],
                            issuer='https://' + os.environ['TRAINER_ACCESS_DOMAIN'],
                            audience=os.environ['TRAINER_ACCESS_AUDIENCE'],
                            options={'require': ['exp', 'iat', 'iss', 'aud', 'sub', 'email']})
        if not isinstance(claims['sub'], str) or not isinstance(claims['email'], str):
            raise jwt.InvalidTokenError()
    except (jwt.PyJWTError, OSError, ValueError):
        raise service.Error('인증이 만료되었거나 유효하지 않습니다. 다시 로그인해주세요.', 401) from None
    if claims['sub'] != os.environ['TRAINER_ACCESS_SUBJECT'] or claims['email'].strip().lower() != os.environ['TRAINER_ACCESS_EMAIL'].strip().lower():
        raise service.Error('허용된 계정만 사용할 수 있습니다.', 403)
    current = db.one('SELECT id,username,admin FROM users WHERE id=?', (os.environ['TRAINER_ACCESS_USER_ID'],))
    if not current:
        raise service.Error('연결된 계정이 없습니다.', 403)
    return current

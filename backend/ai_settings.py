"""Owner-bound secrets; a disabled personal connection never falls back to a shared key."""
import json
import os
from urllib.parse import urlsplit
from cryptography.fernet import Fernet, InvalidToken
from . import access, db


class SettingsError(Exception):
    pass


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS ai_settings (
        owner TEXT PRIMARY KEY REFERENCES users(id), revision INTEGER NOT NULL,
        api_key TEXT NOT NULL, model TEXT NOT NULL, provider_url TEXT NOT NULL, updated_at TEXT NOT NULL)''')
    for name, declaration in [('settings_version', 'INTEGER'), ('provider_url', "TEXT NOT NULL DEFAULT ''")]:
        if name not in {r['name'] for r in c.execute('PRAGMA table_info(ai_usage)')}:
            c.execute(f'ALTER TABLE ai_usage ADD COLUMN {name} {declaration}')


def cipher():
    try:
        return Fernet((os.environ.get('TRAINER_AI_ENCRYPTION_KEY') or os.environ.get('TRAINER_GITHUB_ENCRYPTION_KEY', '')).encode())
    except (ValueError, TypeError):
        raise SettingsError('서버의 AI 암호화 키 설정이 필요합니다.') from None


def provider_url():
    value = os.environ.get('AI_BASE_URL', 'https://api.openai.com/v1').rstrip('/')
    try:
        url = urlsplit(value)
        if (not url.hostname or url.username or url.password or url.query or url.fragment
                or (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ('localhost', '127.0.0.1', '::1')))):
            raise ValueError()
    except ValueError:
        raise SettingsError('서버의 AI API 주소 설정을 확인해주세요.') from None
    return value


def decrypt(row):
    try:
        value = json.loads(cipher().decrypt(row['api_key'].encode()))
        if any(value[k] != row[k] for k in ('owner', 'revision', 'model', 'provider_url')):
            raise ValueError()
        return value['api_key']
    except (InvalidToken, ValueError, KeyError, TypeError):
        raise SettingsError('저장된 AI 키를 읽을 수 없습니다. 본인의 키를 다시 등록해주세요.') from None


def configuration(owner=None):
    row = db.one('SELECT * FROM ai_settings WHERE owner=?', (owner,)) if owner else None
    if row:
        return dict(api_key=decrypt(row), model=row['model'], provider_url=row['provider_url'], revision=row['revision']) if row['api_key'] else None
    if owner and access.enabled():
        return None
    key, model = os.environ.get('AI_API_KEY'), os.environ.get('AI_MODEL')
    return dict(api_key=key, model=model, provider_url=provider_url(), revision=0) if key and model else None


def model_name(owner):
    row = db.one('SELECT model FROM ai_settings WHERE owner=?', (owner,))
    if row:
        return row['model']
    return '' if access.enabled() else os.environ.get('AI_MODEL', '')


def status(owner):
    row = db.one('SELECT * FROM ai_settings WHERE owner=?', (owner,))
    error, url, ready, available = '', '', True, False
    try:
        cipher()
    except SettingsError as e:
        ready, error = False, str(e)
    try:
        url = provider_url()
        available = configuration(owner) is not None
    except SettingsError as e:
        error = str(e)
    return {'revision': row['revision'] if row else 0,
            'source': 'personal' if row and row['api_key'] else 'disabled' if row else 'environment' if not access.enabled() and available else 'unconfigured',
            'model': row['model'] if row else model_name(owner), 'provider_url': url,
            'saved_provider_url': row['provider_url'] if row and row['api_key'] else '',
            'storage_ready': ready, 'available': available, 'error': error}


def save(owner, data):
    from . import service
    service.rate('ai-settings:' + owner, 20)
    try:
        encryption, url = cipher(), provider_url()
        if data.provider_url != url:
            raise service.Error('서버의 API 주소가 바뀌었습니다. 화면을 다시 열어 확인해주세요.', 409)
        with db.connect(write=True) as c:
            row = c.execute('SELECT * FROM ai_settings WHERE owner=?', (owner,)).fetchone()
            revision = row['revision'] if row else 0
            if row and row['api_key'] and revision in (data.revision, data.revision + 1):
                try:
                    same = (decrypt(row), row['model'], row['provider_url']) == (data.api_key, data.model, url)
                except SettingsError:
                    same = False
                if same:
                    return status(owner)
            if revision != data.revision:
                raise service.Error('다른 화면에서 AI 설정이 변경되었습니다. 최신 설정을 다시 확인해주세요.', 409)
            value = dict(owner=owner, revision=revision + 1, api_key=data.api_key, model=data.model, provider_url=url)
            encrypted = encryption.encrypt(json.dumps(value).encode()).decode()
            c.execute('INSERT OR REPLACE INTO ai_settings VALUES (?,?,?,?,?,?)',
                      (owner, revision + 1, encrypted, data.model, url, service.now()))
    except SettingsError as e:
        raise service.Error(str(e), 503) from None
    return status(owner)


def disconnect(owner, expected):
    from . import service
    with db.connect(write=True) as c:
        row = c.execute('SELECT revision,api_key FROM ai_settings WHERE owner=?', (owner,)).fetchone()
        revision = row['revision'] if row else 0
        if row and not row['api_key'] and revision in (expected, expected + 1):
            return status(owner)
        if revision != expected:
            raise service.Error('다른 화면에서 AI 설정이 변경되었습니다. 최신 설정을 다시 확인해주세요.', 409)
        c.execute("INSERT OR REPLACE INTO ai_settings VALUES (?,?,'','','',?)", (owner, revision + 1, service.now()))
    return status(owner)

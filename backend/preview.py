"""Explicit, loopback-only preview of this checkout's development database."""
import os
import secrets
from pathlib import Path
from . import access, db, service
from .schema import Credentials

PREVIEW_DB = Path(__file__).resolve().parents[1] / 'data/dev/trainer.sqlite3'


def enabled():
    return os.environ.get('TRAINER_PREVIEW') == '1'


def validate_config():
    if enabled() and (access.enabled() or db.path() != PREVIEW_DB.resolve()):
        raise ValueError('Preview requires local mode and this checkout\'s data/dev/trainer.sqlite3')


def initialize():
    if not enabled():
        return
    users = db.all('SELECT id FROM users LIMIT 2')
    if len(users) > 1:
        raise ValueError('Preview requires a single development owner')
    if not users:
        service.authenticate(Credentials(username='미리보기', password=secrets.token_urlsafe(32), admin_password='1202'))


def user(request):
    validate_config()
    forwarded = ('forwarded', 'x-forwarded-for', 'x-forwarded-host', 'cf-connecting-ip', 'cf-access-jwt-assertion', 'x-trainer-user-jwt')
    if not request.client or request.client.host not in ('127.0.0.1', '::1') or any(name in request.headers for name in forwarded):
        raise service.Error('미리보기는 이 컴퓨터의 로컬 주소에서만 사용할 수 있습니다.', 403)
    users = db.all('SELECT id,username,admin FROM users LIMIT 2')
    if len(users) != 1:
        raise service.Error('미리보기의 개발 소유자를 확인할 수 없습니다.', 503)
    return users[0]

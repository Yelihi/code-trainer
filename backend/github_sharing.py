"""Explicit, owner-scoped issue publication; reads never test permissions by writing."""
import hashlib
import json
import os
import re
from urllib.parse import urlsplit
import httpx
from cryptography.fernet import Fernet, InvalidToken
from . import db, ontology, reference_notes, service


def initialize(c):
    c.executescript('''
    CREATE TABLE IF NOT EXISTS github_connections (
      owner TEXT PRIMARY KEY REFERENCES users(id), id TEXT NOT NULL,
      user_id INTEGER NOT NULL, login TEXT NOT NULL, token TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS github_default_repositories (
      owner TEXT PRIMARY KEY REFERENCES github_connections(owner) ON DELETE CASCADE,
      connection_id TEXT NOT NULL, repo_id INTEGER NOT NULL, url TEXT NOT NULL, private INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS github_shares (
      id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id), request_id TEXT NOT NULL,
      kind TEXT NOT NULL, source_id TEXT NOT NULL, version TEXT NOT NULL,
      repo_id INTEGER NOT NULL, repo TEXT NOT NULL, private INTEGER NOT NULL,
      login TEXT NOT NULL, user_id INTEGER NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
      state TEXT NOT NULL, issue_url TEXT, error TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
      UNIQUE(owner,request_id), UNIQUE(owner,kind,source_id,version,repo_id));
    ''')


def cipher():
    try:
        return Fernet(os.environ.get('TRAINER_GITHUB_ENCRYPTION_KEY', '').encode())
    except (ValueError, TypeError):
        raise service.Error('서버의 GitHub 암호화 키 설정이 필요합니다. 관리자에게 문의해주세요.', 503) from None


def status(owner):
    row = db.one('SELECT id,login,updated_at FROM github_connections WHERE owner=?', (owner,))
    try:
        cipher()
        ready = True
    except service.Error:
        ready = False
    return {'storage_ready': ready, 'connection': row}


def credential(owner):
    row = db.one('SELECT * FROM github_connections WHERE owner=?', (owner,))
    if not row:
        raise service.Error('설정에서 GitHub 계정을 먼저 연결해주세요.', 409)
    try:
        value = json.loads(cipher().decrypt(row['token'].encode()))
        if value['owner'] != owner:
            raise ValueError()
        row['token'] = value['token']
    except (InvalidToken, ValueError, KeyError):
        raise service.Error('저장된 GitHub 연결을 읽을 수 없습니다. 토큰을 다시 연결해주세요.', 409) from None
    return row


def remote(token, method, path, body=None):
    with httpx.Client(base_url='https://api.github.com', timeout=15, follow_redirects=False, trust_env=False,
                      headers={'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                               'X-GitHub-Api-Version': '2026-03-10'}) as client:
        return client.request(method, path, json=body)


def response_error(code):
    if code == 401:
        return 'GitHub 토큰이 만료되었거나 취소되었습니다. 설정에서 다시 연결해주세요.'
    if code == 404:
        return '저장소를 찾거나 접근할 수 없습니다. 주소와 토큰의 대상 저장소를 확인해주세요.'
    if code == 403:
        return 'GitHub에서 요청을 거절했습니다. 토큰 권한·조직 승인·요청 제한을 확인해주세요.'
    if code == 429:
        return 'GitHub 요청 제한에 도달했습니다. 잠시 후 다시 확인해주세요.'
    if code in (301, 302, 307, 308):
        return '저장소 주소가 변경되었습니다. GitHub의 현재 주소를 입력해주세요.'
    if code in (400, 410, 422):
        return 'GitHub에서 이슈 요청을 거절했습니다. 이슈 사용 설정과 제목·본문을 확인해주세요.'
    return 'GitHub 응답을 확인할 수 없습니다. 잠시 후 다시 시도해주세요.'


def read(token, path):
    try:
        response = remote(token, 'GET', path)
        if response.status_code != 200:
            raise service.Error(response_error(response.status_code), 400)
        value = response.json()
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (httpx.HTTPError, ValueError):
        raise service.Error('GitHub 연결을 확인하지 못했습니다. 잠시 후 다시 시도해주세요.', 502) from None


def identity(token):
    value = read(token, '/user')
    if not isinstance(value.get('id'), int) or not re.fullmatch(r'[A-Za-z0-9-]{1,100}', value.get('login', '')):
        raise service.Error('GitHub 계정 응답을 확인하지 못했습니다.', 502)
    return value


def assert_idle(c, owner):
    if c.execute("SELECT id FROM github_shares WHERE owner=? AND state='sending'", (owner,)).fetchone():
        raise service.Error('이슈를 등록 중입니다. 완료된 뒤 연결을 변경해주세요.', 409)


def connect(owner, token):
    service.rate('github-connect:' + owner, 10)
    encryption = cipher()
    who = identity(token)
    encrypted = encryption.encrypt(service.dump({'owner': owner, 'token': token}).encode()).decode()
    with db.connect(write=True) as c:
        assert_idle(c, owner)
        c.execute('INSERT OR REPLACE INTO github_connections VALUES (?,?,?,?,?,?)',
                  (owner, service.uid(), who['id'], who['login'], encrypted, service.now()))
    return status(owner)


def disconnect(owner):
    with db.connect(write=True) as c:
        assert_idle(c, owner)
        c.execute('DELETE FROM github_connections WHERE owner=?', (owner,))
    return status(owner)


def repository_name(url):
    try:
        parsed = urlsplit(url.strip())
        path = parsed.path.rstrip('/')
        if path.endswith('.git'):
            path = path[:-4]
        if (parsed.scheme != 'https' or parsed.netloc.lower() != 'github.com' or parsed.query or parsed.fragment
                or not re.fullmatch(r'/[A-Za-z0-9][A-Za-z0-9-]{0,99}/[A-Za-z0-9_.-]{1,100}', path)
                or path.split('/')[-1] in ('.', '..')):
            raise ValueError()
        return path[1:]
    except ValueError:
        raise service.Error('https://github.com/소유자/저장소 형식의 주소를 입력해주세요.', 422) from None


def check(owner, url):
    name = repository_name(url)
    connection = credential(owner)
    who = identity(connection['token'])
    if who['id'] != connection['user_id']:
        raise service.Error('연결된 GitHub 계정이 변경되었습니다. 다시 연결해주세요.', 409)
    repo = read(connection['token'], '/repos/' + name)
    if (not isinstance(repo.get('id'), int) or not isinstance(repo.get('private'), bool)
            or repo.get('full_name', '').lower() != name.lower()):
        raise service.Error('저장소 응답이 입력한 주소와 다릅니다. 현재 주소를 확인해주세요.', 409)
    issues = repo.get('has_issues') is True
    active = repo.get('archived') is False and repo.get('disabled') is False
    return {'connection_id': connection['id'], 'login': who['login'], 'repo_id': repo['id'],
            'repo': repo['full_name'], 'url': 'https://github.com/' + repo['full_name'], 'private': repo['private'],
            'issues_enabled': issues, 'active': active, 'can_attempt': issues and active,
            'write_permission': 'unverified', 'checked_at': service.now()}


def default_repository(owner):
    value = db.one('SELECT connection_id,repo_id,url,private FROM github_default_repositories WHERE owner=?', (owner,))
    return {**value, 'private': bool(value['private'])} if value else None


def save_default(owner, data):
    service.rate('github-default:' + owner, 30)
    checked = check(owner, data.url)
    if any(checked[key] != getattr(data, key) for key in ('connection_id', 'repo_id', 'private')):
        raise service.Error('계정 또는 저장소가 변경되었습니다. 저장소를 다시 확인해주세요.', 409)
    if not checked['can_attempt']:
        raise service.Error('이슈가 비활성화되었거나 보관·제한된 저장소입니다.', 409)
    value = {key: checked[key] for key in ('connection_id', 'repo_id', 'url', 'private')}
    with db.connect(write=True) as c:
        connection = c.execute('SELECT id FROM github_connections WHERE owner=?', (owner,)).fetchone()
        if not connection or connection['id'] != data.connection_id:
            raise service.Error('GitHub 연결이 변경되었습니다. 저장소를 다시 확인해주세요.', 409)
        c.execute('INSERT OR REPLACE INTO github_default_repositories VALUES (?,?,?,?,?)',
                  (owner, value['connection_id'], value['repo_id'], value['url'], value['private']))
    return value


def preview(owner, kind, source_id):
    """Export registered IDs and evidence; never infer new concepts during sharing."""
    source_ids, concept_ids = set(), set()
    if kind == 'note':
        note = reference_notes.owned(owner, source_id)
        if note['archived']:
            raise service.Error('보관한 노트는 복원 후 공유해주세요.', 409)
        title, body = note['title'], note['body']
        version_label = '노트 v' + str(note['revision'])
        source_ids = {s['id'] for s in db.all("SELECT id FROM knowledge_sources WHERE owner=? AND kind='note' AND origin_id=? AND version=?", (owner, source_id, note['revision']))}
        metadata = {'kind': kind, 'id': source_id, 'revision': note['revision'], 'reference': note['metadata']}
    elif kind == 'concept':
        concept = db.one('SELECT * FROM knowledge_concepts WHERE owner=? AND id=?', (owner, source_id))
        if not concept:
            raise service.Error('저장된 개념을 찾을 수 없습니다.', 404)
        title, body = concept['pref_label'], concept['definition']
        concept_ids = {source_id}
        version_label = '개념 스냅샷'
        metadata = {'kind': kind, 'id': source_id}
    elif kind == 'learning':
        source = db.one("SELECT * FROM knowledge_sources WHERE owner=? AND kind='learning' AND origin_id=? AND state='active'", (owner, source_id))
        if not source:
            raise service.Error('등록된 학습 내용을 찾을 수 없습니다.', 404)
        title, body = source['title'], source['body']
        source_ids = {source['id']}
        version_label = '학습 v' + str(source['version'])
        metadata = {'kind': kind, 'id': source_id, 'version': source['version']}
    else:
        raise service.Error('공유할 자료 종류를 확인해주세요.', 422)
    if kind == 'concept':
        assertions = db.all('SELECT * FROM knowledge_assertions WHERE owner=? AND (subject=? OR object=?) ORDER BY id', (owner, source_id, source_id))
        proofs = db.all('SELECT * FROM knowledge_evidence WHERE owner=? AND (concept_id=? OR assertion_id IN (SELECT value FROM json_each(?))) ORDER BY id',
                        (owner, source_id, service.dump([a['id'] for a in assertions])))
    else:
        proofs = db.all('SELECT * FROM knowledge_evidence WHERE owner=? AND source_id IN (SELECT value FROM json_each(?)) ORDER BY id', (owner, service.dump(sorted(source_ids))))
        assertions = db.all('SELECT * FROM knowledge_assertions WHERE owner=? AND id IN (SELECT value FROM json_each(?)) ORDER BY id', (owner, service.dump([e['assertion_id'] for e in proofs])))
    concept_ids |= {e['concept_id'] for e in proofs} | {a['subject'] for a in assertions} | {a['object'] for a in assertions}
    source_ids |= {e['source_id'] for e in proofs}
    selected_sources = db.all('SELECT id,kind,origin_id,version,title,state,created_at,metadata FROM knowledge_sources WHERE owner=? AND id IN (SELECT value FROM json_each(?)) ORDER BY id', (owner, service.dump(sorted(source_ids))))
    selected_ids = service.dump(sorted(concept_ids - {None}))
    concepts = db.all('SELECT * FROM knowledge_concepts WHERE owner=? AND id IN (SELECT value FROM json_each(?)) ORDER BY id', (owner, selected_ids))
    aliases = db.all('SELECT * FROM knowledge_aliases WHERE owner=? AND concept_id IN (SELECT value FROM json_each(?)) ORDER BY concept_id,label,language', (owner, selected_ids))
    for source in selected_sources:
        source_metadata = json.loads(source['metadata'])
        source['metadata'] = source_metadata if source['kind'] == 'note' else {k: v for k, v in source_metadata.items() if k in ('scope', 'source_url')}
    # Source bodies and unrelated notes are not exported through a concept's provenance.
    manifest = {'format': 'code-trainer-ontology-v1', 'source': metadata,
                'concepts': [{k: v for k, v in c.items() if k not in ('owner', 'legacy_key')} for c in concepts],
                'aliases': [{k: v for k, v in a.items() if k != 'owner'} for a in aliases],
                'assertions': [{k: v for k, v in a.items() if k not in ('owner', 'signature')} for a in assertions],
                'evidence': [{k: v for k, v in e.items() if k != 'owner'} for e in proofs],
                'sources': selected_sources}
    labels = {c['id']: c['pref_label'] for c in concepts}
    lines = [body]
    if concepts:
        lines += ['## 연결된 개념', '\n'.join('- ' + c['pref_label'] + ' — ' + c['definition'] for c in concepts)]
    if assertions:
        lines += ['## 주장과 관계', '\n'.join('- ' + labels[a['subject']] + ' · ' + ontology.RELATIONS[a['kind']] +
                  ((' ↔ ' if a['kind'] == 'RELATED_TO' else ' → ') + labels[a['object']] if a['object'] else '') + ': ' + a['text'] +
                  (' (반박 근거 있음)' if any(e['assertion_id'] == a['id'] and e['disposition'] == 'refutes' for e in proofs) else '') for a in assertions)]
    if selected_sources:
        lines += ['## 출처', '\n'.join('- ' + s['title'] + ' · v' + str(s['version']) + ' · ' + s['state'] for s in selected_sources)]
    lines += ['## 개념 ID · 관계 · 출처 데이터', '```json\n' + json.dumps(manifest, ensure_ascii=False, indent=2) + '\n```']
    original = '\n\n'.join(lines)
    has_images = '/api/reference-images/' in original
    body = re.sub(r'!\[[^\]]*\]\([^)]*/api/reference-images/[^)]*\)', '[첨부 이미지 — GitHub에는 별도로 첨부해주세요]', original)
    body = re.sub(r'(?:https?://[^\s"<>)]*)?/api/reference-images/[a-f0-9]{32}', '[비공개 이미지 생략]', body)
    version = hashlib.sha256((title + '\n' + original).encode()).hexdigest()
    return {'kind': kind, 'id': source_id, 'version': version, 'version_label': version_label,
            'title': title[:256], 'body': body, 'has_images': has_images,
            'history': history(owner, kind, source_id)}


def history(owner, kind=None, source_id=None):
    sql = 'SELECT * FROM github_shares WHERE owner=?'
    args = [owner]
    if kind:
        sql += ' AND kind=? AND source_id=?'
        args += [kind, source_id]
    return [public(row) for row in db.all(sql + ' ORDER BY created_at DESC LIMIT 30', args)]


def public(row):
    return {**{k: v for k, v in row.items() if k not in ('owner', 'user_id', 'request_id')}, 'private': bool(row['private'])}


def publish(owner, data):
    previous = db.one('SELECT * FROM github_shares WHERE owner=? AND request_id=?', (owner, data.request_id))
    if previous:
        if (previous['kind'], previous['source_id'], previous['version'], previous['repo_id']) != (data.kind, data.id, data.version, data.repo_id):
            raise service.Error('이미 사용된 공유 요청입니다. 새 공유 화면에서 다시 확인해주세요.', 409)
        return public(previous)
    source = preview(owner, data.kind, data.id)
    if source['version'] != data.version:
        raise service.Error('원본 또는 그래프가 변경되었습니다. 새 미리보기를 열어 확인해주세요. 작성한 글은 복사해 보관할 수 있습니다.', 409)
    if '/api/reference-images/' in data.body:
        raise service.Error('비공개 이미지 주소는 GitHub에서 열 수 없습니다. 해당 주소를 제거하고 이미지를 별도로 첨부해주세요.', 422)
    service.rate('github-publish:' + owner, 10)
    checked = check(owner, data.url)
    if (checked['connection_id'] != data.connection_id or checked['repo_id'] != data.repo_id
            or checked['private'] != data.private):
        raise service.Error('계정 또는 저장소의 공개 범위가 변경되었습니다. 저장소를 다시 확인해주세요.', 409)
    if not checked['can_attempt']:
        raise service.Error('이슈가 비활성화되었거나 보관·제한된 저장소입니다.', 409)
    connection = credential(owner)
    with db.connect(write=True) as c:
        current = c.execute('SELECT id FROM github_connections WHERE owner=?', (owner,)).fetchone()
        if not current or current['id'] != data.connection_id or connection['id'] != data.connection_id:
            raise service.Error('GitHub 연결이 변경되었습니다. 저장소를 다시 확인해주세요.', 409)
        repeated = c.execute('SELECT * FROM github_shares WHERE owner=? AND request_id=?', (owner, data.request_id)).fetchone()
        if repeated:
            if (repeated['kind'], repeated['source_id'], repeated['version'], repeated['repo_id']) != (data.kind, data.id, data.version, data.repo_id):
                raise service.Error('이미 사용된 공유 요청입니다. 새 공유 화면에서 다시 확인해주세요.', 409)
            return public(dict(repeated))
        existing = c.execute('SELECT * FROM github_shares WHERE owner=? AND kind=? AND source_id=? AND version=? AND repo_id=?',
                             (owner, data.kind, data.id, data.version, data.repo_id)).fetchone()
        if existing and existing['state'] != 'failed':
            return public(dict(existing))
        share_id = existing['id'] if existing else service.uid()
        if existing:
            c.execute('DELETE FROM github_shares WHERE id=?', (share_id,))
        c.execute('''INSERT INTO github_shares
          (id,owner,request_id,kind,source_id,version,repo_id,repo,private,login,user_id,title,body,state,created_at)
          VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'sending',?)''',
          (share_id, owner, data.request_id, data.kind, data.id, data.version, data.repo_id, checked['repo'],
           data.private, checked['login'], connection['user_id'], data.title, data.body, service.now()))
    state, url, error = 'unknown', None, '등록 결과를 확인하지 못했습니다. GitHub에서 먼저 확인해주세요. 자동으로 재전송하지 않습니다.'
    try:
        response = remote(connection['token'], 'POST', '/repos/' + checked['repo'] + '/issues',
                          {'title': data.title, 'body': data.body + '\n\n<!-- code-trainer-share:' + share_id + ' -->'})
        if response.status_code == 201:
            issue = response.json()
            if isinstance(issue, dict) and isinstance(issue.get('number'), int) and issue['number'] > 0:
                state, error = 'published', ''
                url = 'https://github.com/' + checked['repo'] + '/issues/' + str(issue['number'])
        elif 400 <= response.status_code < 500:
            state, error = 'failed', response_error(response.status_code)
    except (httpx.HTTPError, ValueError):
        pass  # A timeout after POST cannot prove that GitHub did not create the issue.
    db.execute('UPDATE github_shares SET state=?,issue_url=?,error=? WHERE owner=? AND id=?', (state, url, error, owner, share_id))
    return public(db.one('SELECT * FROM github_shares WHERE owner=? AND id=?', (owner, share_id)))


def recover(owner, share_id, url):
    row = db.one('SELECT * FROM github_shares WHERE owner=? AND id=?', (owner, share_id))
    if not row:
        raise service.Error('공유 기록을 찾을 수 없습니다.', 404)
    match = re.fullmatch(r'https://github\.com/([A-Za-z0-9-]+/[A-Za-z0-9_.-]+)/issues/([1-9][0-9]{0,9})', url.strip())
    if not match or match[1].lower() != row['repo'].lower():
        raise service.Error('공유한 저장소의 이슈 주소를 입력해주세요.', 422)
    connection = credential(owner)
    repo = read(connection['token'], '/repos/' + row['repo'])
    issue = read(connection['token'], '/repos/' + row['repo'] + '/issues/' + match[2])
    if (repo.get('id') != row['repo_id'] or issue.get('user', {}).get('id') != row['user_id']
            or 'pull_request' in issue or '<!-- code-trainer-share:' + share_id + ' -->' not in (issue.get('body') or '')):
        raise service.Error('이 공유 요청으로 만든 이슈인지 확인하지 못했습니다.', 409)
    db.execute("UPDATE github_shares SET state='published',issue_url=?,error='' WHERE owner=? AND id=? AND state='unknown'",
               ('https://github.com/' + row['repo'] + '/issues/' + match[2], owner, share_id))
    return public(db.one('SELECT * FROM github_shares WHERE owner=? AND id=?', (owner, share_id)))

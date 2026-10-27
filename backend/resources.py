"""Independent raw identities; imported snapshots and references to existing notes."""
import hashlib
import json
import time
import uuid
from . import db, source
from datetime import datetime, timezone


def initialize(c):
    c.execute('''CREATE TABLE IF NOT EXISTS resources (
        id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES users(id),
        kind TEXT NOT NULL CHECK(kind IN ('source','note')), origin_id TEXT NOT NULL,
        note_id TEXT, created_at TEXT NOT NULL,
        UNIQUE(owner,kind,origin_id), UNIQUE(owner,id),
        CHECK((kind='source' AND note_id IS NULL) OR
              (kind='note' AND note_id IS NOT NULL AND note_id=origin_id)),
        FOREIGN KEY(owner,note_id) REFERENCES reference_notes(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS resource_versions (
        owner TEXT NOT NULL, resource_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision>0),
        kind TEXT NOT NULL, name TEXT NOT NULL, url TEXT, content TEXT, created_at TEXT NOT NULL,
        PRIMARY KEY(owner,resource_id,revision),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')

    c.execute('''CREATE TABLE IF NOT EXISTS resource_registrations (
        owner TEXT NOT NULL, resource_id TEXT NOT NULL, kind TEXT NOT NULL,
        name TEXT NOT NULL, url TEXT, state TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
        active_request TEXT, lease_until REAL NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
        PRIMARY KEY(owner,resource_id), UNIQUE(owner,url),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS resource_requests (
        owner TEXT NOT NULL, request_id TEXT NOT NULL, resource_id TEXT NOT NULL,
        payload_hash TEXT NOT NULL, response TEXT,
        PRIMARY KEY(owner,request_id),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS resource_feed_posts (
        owner TEXT NOT NULL, post_id TEXT NOT NULL REFERENCES feed_posts(id),
        resource_id TEXT NOT NULL, request_id TEXT NOT NULL,
        PRIMARY KEY(owner,post_id),
        FOREIGN KEY(owner,resource_id) REFERENCES resources(owner,id),
        FOREIGN KEY(owner,request_id) REFERENCES resource_requests(owner,request_id))''')


def migrate(c, context_id=None):
    """Caller owns the write transaction, including any subsequent legacy deletion."""
    query = '''SELECT d.*,g.owner,g.created_at FROM source_documents d
               JOIN generations g ON g.id=d.id'''
    params = ()
    if context_id is not None:
        query += ' WHERE d.context_id=? OR g.context_id=?'
        params = (context_id, context_id)
    # Legacy generation writers still snapshot at startup/deletion; registered raw sources use live writes.
    for source in c.execute(query, params):
        c.execute('''INSERT INTO resources(id,owner,kind,origin_id,created_at) VALUES (?,?,'source',?,?)
                     ON CONFLICT(owner,kind,origin_id) DO NOTHING''',
                  (uuid.uuid4().hex, source['owner'], source['id'], source['created_at']))
        resource_id = c.execute("SELECT id FROM resources WHERE owner=? AND kind='source' AND origin_id=?",
                                (source['owner'], source['id'])).fetchone()['id']
        if c.execute('SELECT 1 FROM resource_registrations WHERE owner=? AND resource_id=?',
                     (source['owner'], resource_id)).fetchone():
            continue
        previous = c.execute('''SELECT * FROM resource_versions WHERE owner=? AND resource_id=?
                                ORDER BY revision DESC LIMIT 1''', (source['owner'], resource_id)).fetchone()
        fields = ('kind', 'name', 'url', 'content')
        values = tuple(source[field] for field in fields)
        if previous and tuple(previous[field] for field in fields) == values:
            continue
        c.execute('''INSERT INTO resource_versions(owner,resource_id,revision,kind,name,url,content,created_at)
                     VALUES (?,?,?,?,?,?,?,?)''',
                  (source['owner'], resource_id, previous['revision'] + 1 if previous else 1,
                   *values, datetime.now(timezone.utc).isoformat()))
    if context_id is None:
        for note in c.execute('SELECT id,owner,created_at FROM reference_notes'):
            link_note(c, note['owner'], note['id'], note['created_at'])


def link_note(c, owner, note_id, created_at):
    c.execute('''INSERT INTO resources(id,owner,kind,origin_id,note_id,created_at)
                 VALUES (?,?,'note',?,?,?) ON CONFLICT(owner,kind,origin_id) DO NOTHING''',
              (uuid.uuid4().hex, owner, note_id, note_id, created_at))


# Current metadata is separate from immutable body snapshots.
CURRENT = '''SELECT r.id,r.owner,r.note_id,r.created_at,
    CASE WHEN r.kind='note' THEN 'note' ELSE COALESCE(g.kind,v.kind,'text') END AS kind,
    COALESCE(n.title,g.name,v.name,'제목 없는 자료') AS name,
    CASE WHEN r.kind='note' THEN json_extract(n.metadata,'$.url') ELSE COALESCE(g.url,v.url) END AS url,
    COALESCE(n.body,v.content) AS content, COALESCE(n.revision,v.revision,0) AS revision,
    COALESCE(n.updated_at,g.updated_at,v.created_at,r.created_at) AS updated_at,
    CASE WHEN g.state='fetching' AND g.lease_until < strftime('%s','now') THEN 'failed'
         ELSE COALESCE(g.state,CASE WHEN r.kind='note' OR v.content IS NOT NULL THEN 'ready' ELSE 'failed' END) END AS state,
    CASE WHEN g.state='fetching' AND g.lease_until < strftime('%s','now') THEN '수집이 중단되었습니다. 다시 가져오기를 눌러주세요.'
         ELSE COALESCE(g.error,'') END AS error,
    COALESCE(n.archived,0) AS archived
    FROM resources r
    LEFT JOIN resource_registrations g ON g.owner=r.owner AND g.resource_id=r.id
    LEFT JOIN reference_notes n ON n.owner=r.owner AND n.id=r.note_id
    LEFT JOIN resource_versions v ON v.owner=r.owner AND v.resource_id=r.id
        AND v.revision=(SELECT MAX(revision) FROM resource_versions WHERE owner=r.owner AND resource_id=r.id)'''


def view(owner, resource_id, c=None):
    from . import service
    if c is None:
        with db.connect() as connection:
            return view(owner, resource_id, connection)
    row = c.execute(CURRENT + ' WHERE r.owner=? AND r.id=?', (owner, resource_id)).fetchone()
    if not row:
        raise service.Error('자료를 찾을 수 없습니다.', 404)
    result = dict(row)
    if result['note_id']:
        versions = c.execute('SELECT revision,created_at FROM reference_note_versions WHERE owner=? AND note_id=? ORDER BY revision DESC', (owner, result['note_id']))
    else:
        versions = c.execute('SELECT revision,created_at FROM resource_versions WHERE owner=? AND resource_id=? ORDER BY revision DESC', (owner, resource_id))
    result['versions'] = [dict(v) for v in versions]
    result['feed_pending'] = bool(c.execute('''SELECT 1 FROM resource_feed_posts f
        LEFT JOIN feed_choices choice ON choice.owner=f.owner AND choice.post_id=f.post_id
        WHERE f.owner=? AND f.resource_id=? AND COALESCE(choice.registered,0)=0''',
        (owner, resource_id)).fetchone())
    return result


def version(owner, resource_id, revision):
    from . import service
    current = view(owner, resource_id)
    if current['note_id']:
        row = db.one('SELECT data FROM reference_note_versions WHERE owner=? AND note_id=? AND revision=?', (owner, current['note_id'], revision))
        if row:
            data = json.loads(row['data'])
            return {'revision': data['revision'], 'name': data['title'], 'content': data['body']}
    else:
        row = db.one('SELECT revision,name,content,created_at FROM resource_versions WHERE owner=? AND resource_id=? AND revision=?', (owner, resource_id, revision))
        if row:
            return row
    raise service.Error('자료 버전을 찾을 수 없습니다.', 404)


def listing(owner, query, page, kind):
    where = " WHERE owner=? AND archived=0 AND (name LIKE ? OR content LIKE ? OR url LIKE ?)"
    args = [owner, '%' + query + '%', '%' + query + '%', '%' + query + '%']
    if kind != 'all':
        where += ' AND kind=?'
        args.append(kind)
    with db.connect() as c:
        total = c.execute('WITH current AS (' + CURRENT + ') SELECT COUNT(*) FROM current' + where, args).fetchone()[0]
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        rows = c.execute('WITH current AS (' + CURRENT + ') SELECT id,note_id,name,kind,url,revision,state,error,updated_at,substr(content,1,180) AS excerpt FROM current' + where + ' ORDER BY updated_at DESC,id LIMIT 20 OFFSET ?', (*args, (page - 1) * 20))
        return {'items': [dict(r) for r in rows], 'total': total, 'page': page, 'pages': pages}


def register(owner, data):
    from . import service
    # Keep persisted pre-RSA request hashes replayable when no post was supplied.
    payload_hash = hashlib.sha256(data.model_dump_json(exclude={'feed_post_id'} if data.feed_post_id is None else set()).encode()).hexdigest()
    now = service.now()
    with db.connect(write=True) as c:
        request = c.execute('SELECT * FROM resource_requests WHERE owner=? AND request_id=?', (owner, data.request_id)).fetchone()
        if request:
            if request['payload_hash'] != payload_hash:
                raise service.Error('이미 사용한 요청 ID입니다. 새 요청으로 저장해주세요.', 409)
            if request['response']:
                return json.loads(request['response'])
            raise service.Error('이 수집 요청은 처리 중이거나 중단되었습니다. 자료 목록에서 확인 후 다시 가져와주세요.', 409)
        if data.feed_post_id:
            if not c.execute('SELECT 1 FROM feed_posts WHERE id=?', (data.feed_post_id,)).fetchone():
                raise service.Error('등록 대기 글을 찾을 수 없습니다.', 404)
            choice = c.execute('SELECT registered FROM feed_choices WHERE owner=? AND post_id=?', (owner, data.feed_post_id)).fetchone()
            if choice and choice['registered']:
                raise service.Error('이미 등록한 글입니다. 자료 보관함에서 원문을 확인해주세요.', 409)
            pending = c.execute('''SELECT g.active_request,g.lease_until FROM resource_feed_posts f
                JOIN resource_registrations g ON g.owner=f.owner AND g.resource_id=f.resource_id
                WHERE f.owner=? AND f.post_id=?''', (owner, data.feed_post_id)).fetchone()
            if pending and pending['active_request'] and pending['lease_until'] > time.time():
                raise service.Error('이미 이 글의 원문을 가져오고 있습니다. 잠시 후 확인해주세요.', 409)
        resource_id = data.resource_id
        existing = view(owner, resource_id, c) if resource_id else None
        if existing and (existing['kind'] != data.kind or existing['note_id'] or (data.kind == 'url' and existing['url'] != data.url)):
            raise service.Error('자료 종류와 원본 URL은 변경할 수 없습니다.', 409)
        if data.kind == 'url' and resource_id:
            registered = c.execute('SELECT resource_id FROM resource_registrations WHERE owner=? AND url=?', (owner, data.url)).fetchone()
            if registered and registered['resource_id'] != resource_id:
                raise service.Error('같은 URL이 다른 자료로 등록되어 있습니다. 보관함에서 해당 URL을 검색해주세요. 기존 원문은 유지됩니다.', 409)
        if data.kind == 'url' and not resource_id:
            match = c.execute('SELECT resource_id FROM resource_registrations WHERE owner=? AND url=?', (owner, data.url)).fetchone()
            if not match:
                # Adopt one legacy identity; never merge or discard other legacy copies.
                match = c.execute('''SELECT r.id AS resource_id FROM resources r JOIN resource_versions v
                    ON v.owner=r.owner AND v.resource_id=r.id WHERE r.owner=? AND v.url=? AND v.kind='url'
                    AND v.revision=(SELECT MAX(revision) FROM resource_versions WHERE owner=r.owner AND resource_id=r.id)
                    AND NOT EXISTS (SELECT 1 FROM resource_registrations g WHERE g.owner=r.owner AND g.resource_id=r.id)
                    ORDER BY r.created_at,r.id LIMIT 1''', (owner, data.url)).fetchone()
            if match:
                resource_id = match['resource_id']
                existing = view(owner, resource_id, c)
        if data.kind == 'text' and (existing['revision'] if existing else 0) != data.revision:
            raise service.Error('다른 화면에서 본문이 변경되었습니다. 작성한 내용을 보관하고 최신 버전을 확인해주세요.', 409)
        if not resource_id:
            resource_id = uuid.uuid4().hex
            c.execute("INSERT INTO resources(id,owner,kind,origin_id,created_at) VALUES (?,?,'source',?,?)", (resource_id, owner, resource_id, now))
        registration = c.execute('SELECT * FROM resource_registrations WHERE owner=? AND resource_id=?', (owner, resource_id)).fetchone()
        if registration and registration['active_request'] and registration['lease_until'] > time.time():
            raise service.Error('이미 이 자료를 가져오고 있습니다. 잠시 후 확인해주세요.', 409)
        c.execute('''INSERT INTO resource_registrations(owner,resource_id,kind,name,url,state,active_request,lease_until,updated_at)
                     VALUES (?,?,?,?,?,'fetching',?,?,?) ON CONFLICT(owner,resource_id) DO UPDATE SET
                     name=excluded.name,state='fetching',error='',active_request=excluded.active_request,
                     lease_until=excluded.lease_until,updated_at=excluded.updated_at''',
                  (owner, resource_id, data.kind, data.name, data.url or None, data.request_id, time.time() + 120, now))
        c.execute('INSERT INTO resource_requests VALUES (?,?,?,?,NULL)', (owner, data.request_id, resource_id, payload_hash))
        if data.feed_post_id:
            c.execute('''INSERT INTO resource_feed_posts VALUES (?,?,?,?)
                ON CONFLICT(owner,post_id) DO UPDATE SET resource_id=excluded.resource_id,request_id=excluded.request_id''',
                (owner, data.feed_post_id, resource_id, data.request_id))
    # Network IO must not hold the SQLite writer lock. The request token fences late results.
    content, error = data.content, ''
    if data.kind == 'url':
        try:
            content = source.fetch(data.url)
        except source.SourceError as exc:
            error = str(exc)
        except Exception:
            error = '문서를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.'
    with db.connect(write=True) as c:
        active = c.execute('SELECT active_request FROM resource_registrations WHERE owner=? AND resource_id=?', (owner, resource_id)).fetchone()
        if active['active_request'] != data.request_id:
            raise service.Error('더 최근의 수집 요청이 있습니다. 최신 자료를 확인해주세요.', 409)
        if data.feed_post_id and not c.execute('''SELECT 1 FROM resource_feed_posts
            WHERE owner=? AND post_id=? AND resource_id=? AND request_id=?''',
            (owner, data.feed_post_id, resource_id, data.request_id)).fetchone():
            raise service.Error('이 글에 더 최근의 등록 요청이 있습니다. 대기 목록에서 확인해주세요.', 409)
        previous = c.execute('SELECT * FROM resource_versions WHERE owner=? AND resource_id=? ORDER BY revision DESC LIMIT 1', (owner, resource_id)).fetchone()
        if not error and (not previous or previous['content'] != content):
            c.execute('INSERT INTO resource_versions VALUES (?,?,?,?,?,?,?,?)',
                      (owner, resource_id, previous['revision'] + 1 if previous else 1, data.kind, data.name, data.url or None, content, service.now()))
            c.execute("""UPDATE knowledge_sources SET state='stale' WHERE owner=? AND kind IN ('interpretation','practice')
                AND json_extract(metadata,'$.resource_id')=? AND state='active'""", (owner, resource_id))
        c.execute('''UPDATE resource_registrations SET state=?,error=?,active_request=NULL,lease_until=0,updated_at=?
                     WHERE owner=? AND resource_id=?''', ('failed' if error else 'ready', error, service.now(), owner, resource_id))
        if not error:
            c.execute('''INSERT INTO feed_choices(owner,post_id,registered)
                SELECT owner,post_id,1 FROM resource_feed_posts WHERE owner=? AND resource_id=?
                ON CONFLICT(owner,post_id) DO UPDATE SET registered=1''', (owner, resource_id))
        result = view(owner, resource_id, c)
        c.execute('UPDATE resource_requests SET response=? WHERE owner=? AND request_id=?', (json.dumps(result, ensure_ascii=False), owner, data.request_id))
        return result

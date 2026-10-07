"""Managed public RSS/Atom feeds; collection never invokes AI or reads email."""
import asyncio
import logging
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET
from . import db, source, service

DEFAULT_FEED = 'korean-fe-article'
CONTENT_TYPES = ('application/rss+xml', 'application/atom+xml', 'application/xml', 'text/xml')
MAX_BYTES = 2_000_000


def canonical_url(value, tracking=True):
    try:
        parts = urlsplit(value.strip())
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.port not in (None, 80, 443) or len(value) > 2000:
            return ''
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not tracking or (not k.lower().startswith('utm_') and k.lower() not in ('r', 'fbclid', 'gclid'))]
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or '/', urlencode(query), ''))
    except ValueError:
        return ''


class NoDoctype(ET.TreeBuilder):
    def doctype(self, name, pubid, system):
        raise ValueError('DTD is not supported')


def parse(body):
    if len(body) > MAX_BYTES:
        raise ValueError('Feed too large')
    root = ET.fromstring(body, parser=ET.XMLParser(target=NoDoctype()))
    atom = '{http://www.w3.org/2005/Atom}'
    if root.tag == 'rss':
        entries = root.findall('./channel/item')
    elif root.tag == atom + 'feed':
        entries = root.findall(atom + 'entry')
    else:
        raise ValueError('Not an RSS or Atom feed')
    posts = []
    for item in entries[:200]:
        is_atom = item.tag == atom + 'entry'
        prefix = atom if is_atom else ''
        def field(name):
            return item.findtext(prefix + name, '').strip()
        link = field('link')
        if is_atom:
            link = next((n.get('href', '') for n in item.findall(atom + 'link') if n.get('rel', 'alternate') == 'alternate'), '')
        url = canonical_url(link)
        title = field('title')
        if not url or not title:
            continue
        summary = source.TextParser()
        summary.feed((field('summary') or field('content')) if is_atom else
                     (field('description') or item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded', '')))
        date = field('published') or field('updated') if is_atom else field('pubDate')
        try:
            published = datetime.fromisoformat(date.replace('Z', '+00:00')) if is_atom else parsedate_to_datetime(date)
            published = published.replace(tzinfo=published.tzinfo or timezone.utc).astimezone(timezone.utc).isoformat()
        except (ValueError, TypeError, OverflowError):
            published = ''
        posts.append({'guid': (field('id') if is_atom else field('guid'))[:2000] or url,
                      'url': url, 'title': title[:300], 'summary': summary.text()[:800], 'published': published})
    return posts


def sources():
    return db.all('SELECT * FROM feed_sources ORDER BY name,id')


def save_posts(c, feed_id, posts, stamp):
    for post in posts:
        c.execute('''INSERT OR IGNORE INTO feed_posts(id,guid,url,title,summary,published,collected,feed_id)
            VALUES (?,?,?,?,?,?,?,?)''', (str(uuid.uuid4()), db.feed_guid(feed_id, post['guid']), post['url'],
            post['title'], post['summary'], post['published'], stamp, feed_id))


def add(user, name, url):
    if not user['admin']:
        raise service.Error('관리자만 출처를 추가할 수 있습니다.', 403)
    url = canonical_url(url, tracking=False)
    if not url:
        raise service.Error('공개 RSS 또는 Atom 주소를 입력해주세요.')
    if db.one('SELECT id FROM feed_sources WHERE url=?', (url,)):
        raise service.Error('이미 등록한 피드입니다.', 409)
    if len(sources()) >= 20:
        raise service.Error('출처는 최대 20개까지 등록할 수 있습니다.', 409)
    service.rate('feed-add:' + user['id'], 10, 3600)
    try:
        body, _ = source.fetch_bytes(url, CONTENT_TYPES, MAX_BYTES)
        posts = parse(body)
    except (source.SourceError, ET.ParseError, ValueError):
        raise service.Error('공개 RSS/Atom 피드를 확인하지 못했습니다. 사이트 본문 주소가 아닌 피드 주소를 입력해주세요.') from None
    stamp = datetime.now(timezone.utc).isoformat()
    with db.connect(write=True) as c:
        if c.execute('SELECT id FROM feed_sources WHERE url=?', (url,)).fetchone():
            raise service.Error('이미 등록한 피드입니다.', 409)
        if c.execute('SELECT COUNT(*) FROM feed_sources').fetchone()[0] >= 20:
            raise service.Error('출처는 최대 20개까지 등록할 수 있습니다.', 409)
        feed_id = str(uuid.uuid4())
        c.execute('INSERT INTO feed_sources(id,name,url,attempted,succeeded) VALUES (?,?,?,?,?)',
                  (feed_id, name, url, time.time(), stamp))
        save_posts(c, feed_id, posts, stamp)
    return db.one('SELECT * FROM feed_sources WHERE id=?', (feed_id,))


def set_enabled(user, feed_id, enabled):
    if not user['admin']:
        raise service.Error('관리자만 출처를 변경할 수 있습니다.', 403)
    with db.connect(write=True) as c:
        if not c.execute('SELECT id FROM feed_sources WHERE id=?', (feed_id,)).fetchone():
            raise service.Error('출처를 찾을 수 없습니다.', 404)
        c.execute('UPDATE feed_sources SET enabled=? WHERE id=?', (int(enabled), feed_id))
    return {'ok': True}


def refresh(manual=False, feed_id=DEFAULT_FEED):
    # Persist the claim before I/O; each feed has its own interval and error state.
    now = time.time()
    with db.connect(write=True) as c:
        row = c.execute('SELECT * FROM feed_sources WHERE id=?', (feed_id,)).fetchone()
        if not row:
            raise service.Error('출처를 찾을 수 없습니다.', 404)
        if not row['enabled'] or now - row['attempted'] < (60 if manual else 3600):
            return False
        url = row['url']
        c.execute('UPDATE feed_sources SET attempted=? WHERE id=?', (now, feed_id))
    try:
        body, _ = source.fetch_bytes(url, CONTENT_TYPES, MAX_BYTES)
        posts = parse(body)
        stamp = datetime.now(timezone.utc).isoformat()
        with db.connect(write=True) as c:
            # An admin may pause collection while the HTTP request is in flight.
            if not c.execute('SELECT enabled FROM feed_sources WHERE id=?', (feed_id,)).fetchone()['enabled']:
                return False
            save_posts(c, feed_id, posts, stamp)
            c.execute("UPDATE feed_sources SET succeeded=?,error='' WHERE id=?", (stamp, feed_id))
        return True
    except (source.SourceError, ET.ParseError, ValueError):
        db.execute('UPDATE feed_sources SET error=? WHERE id=?', ('피드를 가져오지 못했습니다. 기존 대기 목록은 보존됩니다. 잠시 후 다시 시도해주세요.', feed_id))
        return False


def inbox(owner, page=1, feed_id=None):
    where = '''FROM feed_posts p JOIN feed_sources f ON f.id=p.feed_id
        LEFT JOIN feed_choices c ON c.post_id=p.id AND c.owner=? WHERE COALESCE(c.registered,0)=0'''
    params = [owner]
    if feed_id:
        where += ' AND p.feed_id=?'
        params.append(feed_id)
    with db.connect() as c:
        total = c.execute('SELECT COUNT(*) ' + where, params).fetchone()[0]
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        items = [dict(row) for row in c.execute('''SELECT p.*, f.name AS feed_name, c.generation_id,
            (SELECT state FROM generations WHERE id=c.generation_id AND owner=?) AS generation_state ''' + where +
            " ORDER BY COALESCE(NULLIF(p.published,''),p.collected) DESC,p.id LIMIT 20 OFFSET ?", [owner, *params, (page-1)*20])]
    feeds = sources()
    return {'items': items, 'total': total, 'page': page, 'pages': pages, 'feeds': feeds,
            # Keep the previous response readable while frontend/backend switch versions.
            'feed_name': 'RSS', 'succeeded': max((f['succeeded'] for f in feeds if f['succeeded']), default=None),
            'error': '일부 출처의 수집에 실패했습니다. 수집 출처에서 자세한 상태를 확인해주세요.' if any(f['error'] for f in feeds) else ''}


async def poll():
    while True:
        await asyncio.sleep(30)
        try:
            selected = sources()
        except Exception:
            logging.getLogger(__name__).exception('RSS source lookup failed')
            continue
        for feed in selected:
            if not feed['enabled']:
                continue
            try:
                # Await each feed separately so shutdown can stop between requests.
                await asyncio.to_thread(refresh, feed_id=feed['id'])
            except Exception:
                logging.getLogger(__name__).exception('RSS collection failed')


async def stop(task):
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

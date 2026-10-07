"""One public newsletter feed; collection never invokes AI or reads email."""
import asyncio
import logging
import time
import uuid
from contextlib import suppress
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET
from . import db, source

FEED_URL = 'https://kofearticle.substack.com/feed'
FEED_NAME = 'Korean FE Article'
MAX_BYTES = 2_000_000


def canonical_url(value):
    try:
        parts = urlsplit(value.strip())
        if parts.scheme not in ('http', 'https') or not parts.hostname or parts.username or parts.password or parts.port not in (None, 80, 443) or len(value) > 2000:
            return ''
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
                 if not k.lower().startswith('utm_') and k.lower() not in ('r', 'fbclid', 'gclid')]
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


def refresh(manual=False):
    # Persist the claim before I/O so concurrent requests and restarts cannot flood the feed.
    now = time.time()
    with db.connect(write=True) as c:
        row = c.execute('SELECT attempted FROM feed_sync WHERE id=1').fetchone()
        if now - row['attempted'] < (60 if manual else 3600):
            return False
        c.execute("UPDATE feed_sync SET attempted=? WHERE id=1", (now,))
    try:
        body, _ = source.fetch_bytes(FEED_URL, ('application/rss+xml', 'application/atom+xml', 'application/xml', 'text/xml'), MAX_BYTES)
        posts = parse(body)
        stamp = datetime.now(timezone.utc).isoformat()
        with db.connect(write=True) as c:
            for post in posts:
                c.execute('''INSERT OR IGNORE INTO feed_posts(id,guid,url,title,summary,published,collected)
                    VALUES (?,?,?,?,?,?,?)''', (str(uuid.uuid4()), post['guid'], post['url'], post['title'], post['summary'], post['published'], stamp))
            c.execute("UPDATE feed_sync SET succeeded=?,error='' WHERE id=1", (stamp,))
        return True
    except (source.SourceError, ET.ParseError, ValueError):
        db.execute("UPDATE feed_sync SET error=? WHERE id=1", ('피드를 가져오지 못했습니다. 기존 대기 목록은 보존됩니다. 잠시 후 다시 시도해주세요.',))
        return False


def inbox(owner, page=1):
    where = 'FROM feed_posts p LEFT JOIN feed_choices c ON c.post_id=p.id AND c.owner=? WHERE COALESCE(c.registered,0)=0'
    with db.connect() as c:
        total = c.execute('SELECT COUNT(*) ' + where, (owner,)).fetchone()[0]
        pages = max(1, (total + 19) // 20)
        page = min(page, pages)
        items = [dict(row) for row in c.execute('''SELECT p.*, c.generation_id,
            (SELECT state FROM generations WHERE id=c.generation_id AND owner=?) AS generation_state ''' + where +
            ' ORDER BY COALESCE(NULLIF(p.published,\'\'),p.collected) DESC,p.id LIMIT 20 OFFSET ?', (owner, owner, (page-1)*20))]
        sync = dict(c.execute('SELECT succeeded,error FROM feed_sync WHERE id=1').fetchone())
    return {'items': items, 'total': total, 'page': page, 'pages': pages, 'feed_name': FEED_NAME, 'feed_url': FEED_URL, **sync}


async def poll():
    while True:
        await asyncio.sleep(30)
        try:
            await asyncio.to_thread(refresh)
        except Exception:
            # A transient DB/storage error must not silently kill all future collection.
            logging.getLogger(__name__).exception('RSS collection failed')


async def stop(task):
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task

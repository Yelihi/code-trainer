"""RSS safety, persisted collection, ownership and generation lifecycle."""
import asyncio
from unittest.mock import patch, MagicMock
import unittest
from . import db, feeds, service, source, test_app
from .sample import sample
from .schema import GenerationInput

RSS = b'''<?xml version="1.0"?><rss version="2.0"><channel>
<item><guid>one</guid><title>One &amp; two</title><link>https://example.com/post?utm_source=email&amp;x=1#comments</link>
<description>&lt;p&gt;A public article&lt;/p&gt;&lt;script&gt;bad()&lt;/script&gt;</description><pubDate>Wed, 07 Oct 2026 01:00:00 GMT</pubDate></item>
<item><guid>unsafe</guid><title>Unsafe</title><link>javascript:alert(1)</link></item>
</channel></rss>'''


class FeedTest(unittest.TestCase):
    setUp = test_app.AppTest.setUp
    tearDown = test_app.AppTest.tearDown

    def collect(self):
        with patch.object(source, 'fetch_bytes', return_value=(RSS, 'application/rss+xml')) as fetch:
            self.assertTrue(feeds.refresh())
        fetch.assert_called_once()
        return feeds.inbox(self.owner)['items'][0]

    def request(self, post, request_id='feed-test-001'):
        return {'request_id': request_id, 'source_kind': 'url', 'source': 'https://example.com/original', 'feed_post_id': post['id']}

    def test_parse_sanitizes_and_supports_atom(self):
        posts = feeds.parse(RSS)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['url'], 'https://example.com/post?x=1')
        self.assertEqual(posts[0]['summary'], 'A public article')
        self.assertEqual(posts[0]['title'], 'One & two')
        self.assertEqual(posts[0]['published'], '2026-10-07T01:00:00+00:00')
        atom = b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>a</id><title>Atom</title><link rel="self" href="https://example.com/feed"/><link href="https://example.com/a"/><updated>2026-10-07T00:00:00Z</updated><summary>Short text</summary></entry></feed>'
        self.assertEqual(feeds.parse(atom)[0]['url'], 'https://example.com/a')
        for url in ('javascript:alert(1)', 'https://a:b@example.com/x', 'https://example.com:999/x', 'http://[invalid'):
            self.assertEqual(feeds.canonical_url(url), '')

    def test_xml_doctype_entities_and_oversize_rejected(self):
        malicious = '<!DOCTYPE rss [<!ENTITY x "expanded">]><rss><channel><item><title>&x;</title></item></channel></rss>'
        for body in (malicious.encode(), malicious.encode('utf-16'), b'x' * (feeds.MAX_BYTES + 1), b'<html/>'):
            with self.assertRaises(ValueError):
                feeds.parse(body)

    def test_collection_deduplicates_guid_or_canonical_url_and_throttles(self):
        self.collect()
        with patch.object(source, 'fetch_bytes') as fetch:
            self.assertFalse(feeds.refresh(manual=True))
            fetch.assert_not_called()
        for payload in (RSS.replace(b'one</guid>', b'changed</guid>'), RSS.replace(b'/post?', b'/new?')):
            db.execute('UPDATE feed_sources SET attempted=0')
            with patch.object(source, 'fetch_bytes', return_value=(payload, 'application/rss+xml')):
                self.assertTrue(feeds.refresh())
        self.assertEqual(feeds.inbox(self.owner)['total'], 1)
        db.execute('UPDATE feed_sources SET attempted=0')
        with patch.object(source, 'fetch_bytes', side_effect=source.SourceError('private detail')):
            self.assertFalse(feeds.refresh())
        inbox = feeds.inbox(self.owner)
        self.assertEqual(inbox['total'], 1)
        self.assertTrue(inbox['succeeded'])
        self.assertNotIn('private detail', inbox['error'])
        self.assertTrue(inbox['error'])

    def test_success_removes_only_owners_pending_and_replay_is_idempotent(self):
        post = self.collect()
        context, _ = sample()
        body = self.request(post)
        with patch.object(service.ai, 'available', return_value=True), patch.object(source, 'fetch', return_value='Public source article text here'), patch.object(service.ai, 'analyze', return_value=context) as analyze:
            response = self.client.post('/api/generations', json=body)
            self.assertEqual(response.status_code, 202, response.text)
            self.assertEqual(self.client.post('/api/generations', json=body).json()['id'], response.json()['id'])
            self.assertEqual(analyze.call_count, 1)
        self.assertEqual(feeds.inbox(self.owner)['total'], 0)
        self.assertEqual(feeds.inbox('another-user')['total'], 1)
        with patch.object(service.ai, 'available', return_value=True):
            self.assertEqual(self.client.post('/api/generations', json=self.request(post, 'duplicate-002')).status_code, 409)
        generation = service.generation(self.owner, response.json()['id'])
        service.delete_context(self.owner, generation['context_id'])
        self.assertEqual(feeds.inbox(self.owner)['total'], 0)  # registration tombstone survives deletion
        self.assertIsNone(db.one('SELECT generation_id FROM feed_choices')['generation_id'])

    def test_failure_remains_pending_and_can_retry(self):
        post = self.collect()
        with patch.object(service.ai, 'available', return_value=True), patch.object(source, 'fetch', side_effect=source.SourceError('unavailable')):
            response = self.client.post('/api/generations', json=self.request(post))
        self.assertEqual(response.status_code, 202)
        self.assertEqual(feeds.inbox(self.owner)['items'][0]['generation_state'], 'failed')
        context, _ = sample()
        with patch.object(service.ai, 'available', return_value=True), patch.object(source, 'fetch', return_value='Public source article long enough'), patch.object(service.ai, 'analyze', return_value=context):
            self.assertEqual(self.client.post('/api/generations', json=self.request(post, 'retry-002')).status_code, 202)
        self.assertEqual(feeds.inbox(self.owner)['total'], 0)

    def test_restart_and_in_progress_do_not_remove_post(self):
        post = self.collect()
        with patch.object(service.ai, 'available', return_value=True):
            job, fresh = service.begin_generation(self.owner, GenerationInput(**self.request(post)))
            self.assertTrue(fresh)
            self.assertEqual(feeds.inbox(self.owner)['items'][0]['generation_state'], 'generating')
            with self.assertRaises(service.Error):
                service.begin_generation(self.owner, GenerationInput(**self.request(post, 'second-002')))
        service.initialize()
        self.assertEqual(feeds.inbox(self.owner)['items'][0]['generation_state'], 'failed')
        self.assertEqual(db.one('SELECT generation_id FROM feed_choices')['generation_id'], job['id'])

    def test_unknown_post_invalid_kind_pagination_and_auth(self):
        self.collect()
        with patch.object(service.ai, 'available', return_value=True):
            self.assertEqual(self.client.post('/api/generations', json=self.request({'id': 'missing'})).status_code, 404)
        self.assertEqual(self.client.post('/api/generations', json={**self.request({'id': 'missing'}), 'source_kind': 'text'}).status_code, 422)
        self.assertEqual(self.client.get('/api/feed-posts?page=999').json()['page'], 1)
        self.assertEqual(self.client.get('/api/feed-posts?page=0').status_code, 422)
        self.client.cookies.clear()
        self.assertEqual(self.client.get('/api/feed-posts').status_code, 401)
        self.assertEqual(self.client.post('/api/feed-posts/refresh', json={}).status_code, 401)

    def test_background_collector_refreshes_without_ai_and_stops(self):
        async def check():
            # One poll iteration, then cancellation at the next sleep.
            with patch.object(feeds.asyncio, 'sleep', side_effect=[None, asyncio.CancelledError]), patch.object(feeds, 'refresh') as refresh:
                with self.assertRaises(asyncio.CancelledError):
                    await feeds.poll()
                refresh.assert_called_once_with(feed_id=feeds.DEFAULT_FEED)
        asyncio.run(check())

    def test_safe_fetch_checks_redirect_destination_before_connecting(self):
        response = MagicMock(status=302)
        response.getheader.return_value = 'http://127.0.0.1/private'
        connection = MagicMock()
        connection.getresponse.return_value = response
        with patch.object(source, 'public_address', side_effect=['93.184.216.34', source.SourceError('private')]) as resolve, patch.object(source.http.client, 'HTTPConnection', return_value=connection) as connect, patch.object(source.socket, 'create_connection'):
            with self.assertRaises(source.SourceError):
                source.fetch_bytes('http://example.com/feed', ('application/xml',), 100)
        self.assertEqual(resolve.call_args_list[-1].args, ('127.0.0.1', 80))
        self.assertEqual(connect.call_count, 1)
        connection.close.assert_called_once()

    def test_safe_fetch_limits_bytes_and_preserves_document_extraction(self):
        response = MagicMock(status=200)
        response.getheader.side_effect = lambda name, default=None: {'Content-Type': 'application/xml', 'Content-Encoding': 'identity'}.get(name, default)
        response.read1.side_effect = [b'x' * 101, b'']
        connection = MagicMock()
        connection.getresponse.return_value = response
        with patch.object(source, 'public_address', return_value='93.184.216.34'), patch.object(source.http.client, 'HTTPConnection', return_value=connection), patch.object(source.socket, 'create_connection'):
            with self.assertRaises(source.SourceError):
                source.fetch_bytes('http://example.com/feed', ('application/xml',), 100)
        connection.close.assert_called_once()
        with patch.object(source, 'fetch_bytes', return_value=(b'<article><p>A public article long enough.</p><script>secret()</script></article>', 'text/html')):
            self.assertEqual(source.fetch('http://example.com/post'), 'A public article long enough.')

    def add_feed(self, name='Second blog', url='https://second.example/feed', body=None):
        payload = body if body is not None else RSS.replace(b'example.com/post', b'second.example/post')
        with patch.object(source, 'fetch_bytes', return_value=(payload, 'application/xml')):
            response = self.client.post('/api/feed-sources', json={'name': name, 'url': url})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_multiple_sources_scope_guids_filter_and_keep_url_dedup(self):
        self.collect()
        second = self.add_feed()
        inbox = self.client.get('/api/feed-posts').json()
        self.assertEqual(inbox['total'], 2)  # both publishers use GUID "one"
        self.assertEqual(len(inbox['feeds']), 2)
        filtered = self.client.get('/api/feed-posts', params={'feed_id': second['id']}).json()
        self.assertEqual(filtered['total'], 1)
        self.assertEqual(filtered['items'][0]['feed_name'], 'Second blog')
        self.assertEqual(filtered['items'][0]['url'], 'https://second.example/post?x=1')
        self.add_feed('Syndicated copy', 'https://third.example/feed', RSS)
        self.assertEqual(feeds.inbox(self.owner)['total'], 2)
        with patch.object(source, 'fetch_bytes') as fetch:
            duplicate = self.client.post('/api/feed-sources', json={'name': 'Again', 'url': 'https://second.example/feed#fragment'})
            self.assertEqual(duplicate.status_code, 409)
            fetch.assert_not_called()

    def test_sources_are_admin_managed_and_invalid_feeds_not_saved(self):
        for payload in ({'name': ' ', 'url': 'https://example.com/feed'}, {'name': 'A', 'url': 'javascript:alert(1)'}):
            self.assertIn(self.client.post('/api/feed-sources', json=payload).status_code, (400, 422))
        for response in (b'<html><body>Not a feed</body></html>', b'not xml'):
            with patch.object(source, 'fetch_bytes', return_value=(response, 'application/xml')):
                self.assertEqual(self.client.post('/api/feed-sources', json={'name': 'Wrong', 'url': 'https://example.com/feed'}).status_code, 400)
        with patch.object(source, 'public_address', side_effect=source.SourceError('private')), patch.object(source.socket, 'create_connection') as connect:
            self.assertEqual(self.client.post('/api/feed-sources', json={'name': 'Private', 'url': 'http://127.0.0.1/feed'}).status_code, 400)
            connect.assert_not_called()
        self.assertEqual(len(feeds.sources()), 1)
        db.execute('UPDATE users SET admin=0 WHERE id=?', (self.owner,))
        with patch.object(source, 'fetch_bytes') as fetch:
            self.assertEqual(self.client.post('/api/feed-sources', json={'name': 'No', 'url': 'https://example.com/feed'}).status_code, 403)
            self.assertEqual(self.client.patch('/api/feed-sources/' + feeds.DEFAULT_FEED, json={'enabled': False}).status_code, 403)
            fetch.assert_not_called()
        self.assertEqual(self.client.get('/api/feed-posts').status_code, 200)

    def test_pause_resume_preserves_posts_and_each_source_has_own_timer(self):
        self.collect()
        second = self.add_feed()
        path = '/api/feed-sources/' + second['id']
        self.assertEqual(self.client.patch(path, json={'enabled': False}).status_code, 200)
        db.execute('UPDATE feed_sources SET attempted=0')
        with patch.object(source, 'fetch_bytes') as fetch:
            self.assertFalse(feeds.refresh(manual=True, feed_id=second['id']))
            fetch.assert_not_called()
        self.assertEqual(feeds.inbox(self.owner)['total'], 2)
        db.initialize()
        self.assertEqual(db.one('SELECT enabled FROM feed_sources WHERE id=?', (second['id'],))['enabled'], 0)
        self.assertEqual(self.client.patch(path, json={'enabled': True}).status_code, 200)
        with patch.object(source, 'fetch_bytes', side_effect=source.SourceError('bad feed')):
            self.assertFalse(feeds.refresh(feed_id=feeds.DEFAULT_FEED))
        with patch.object(source, 'fetch_bytes', return_value=(RSS, 'application/xml')):
            self.assertTrue(feeds.refresh(feed_id=second['id']))
        self.assertTrue(db.one('SELECT error FROM feed_sources WHERE id=?', (feeds.DEFAULT_FEED,))['error'])
        self.assertEqual(db.one('SELECT error FROM feed_sources WHERE id=?', (second['id'],))['error'], '')
        self.assertEqual(self.client.post('/api/feed-sources/missing/refresh', json={}).status_code, 404)
        self.assertEqual(self.client.patch('/api/feed-sources/missing', json={'enabled': False}).status_code, 404)

    def test_previous_database_migration_keeps_posts_choices_and_sync(self):
        post = self.collect()
        with db.connect(write=True) as c:
            c.execute('INSERT INTO feed_choices(owner,post_id,registered) VALUES (?,?,1)', (self.owner, post['id']))
            c.execute('UPDATE feed_posts SET guid=?', ('one',))
            c.execute('DROP INDEX posts_feed')
            c.execute('ALTER TABLE feed_posts DROP COLUMN feed_id')
            c.execute('DROP TABLE feed_sources')
            c.execute("UPDATE feed_sync SET attempted=123,succeeded='2026-10-07T00:00:00+00:00'")
        db.initialize()
        self.assertEqual(feeds.inbox(self.owner)['total'], 0)
        self.assertEqual(feeds.inbox('someone-else')['items'][0]['id'], post['id'])
        self.assertEqual(feeds.sources()[0]['attempted'], 123)
        self.assertEqual(feeds.sources()[0]['succeeded'], '2026-10-07T00:00:00+00:00')
        guid = db.one('SELECT guid FROM feed_posts')['guid']
        db.initialize()
        self.assertEqual(db.one('SELECT guid FROM feed_posts')['guid'], guid)
        with patch.object(source, 'fetch_bytes', return_value=(RSS, 'application/xml')):
            self.assertTrue(feeds.refresh())
        self.assertEqual(db.one('SELECT COUNT(*) AS n FROM feed_posts')['n'], 1)

    def test_poll_continues_after_one_feed_failure_and_source_limit(self):
        second = self.add_feed()
        async def check():
            with patch.object(feeds.asyncio, 'sleep', side_effect=[None, asyncio.CancelledError]), patch.object(feeds, 'refresh', side_effect=[RuntimeError('test'), True]) as refresh, patch.object(feeds.logging.getLogger(feeds.__name__), 'exception'):
                with self.assertRaises(asyncio.CancelledError):
                    await feeds.poll()
                self.assertEqual({call.kwargs['feed_id'] for call in refresh.call_args_list}, {feeds.DEFAULT_FEED, second['id']})
        asyncio.run(check())
        with db.connect(write=True) as c:
            for i in range(18):
                c.execute('INSERT INTO feed_sources(id,name,url) VALUES (?,?,?)', (f'source-{i}', 'Extra', f'https://extra.example/{i}'))
        with patch.object(source, 'fetch_bytes') as fetch:
            self.assertEqual(self.client.post('/api/feed-sources', json={'name': 'Over limit', 'url': 'https://another.example/feed'}).status_code, 409)
            fetch.assert_not_called()

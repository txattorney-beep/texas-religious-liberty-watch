from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

from scripts import sync_news, build_pages

NOW = datetime(2026, 11, 11, 21, 0, tzinfo=timezone.utc)


def feed_xml(title='Religious freedom in Texas', description='Article text must not be copied.', published='Wed, 11 Nov 2026 18:00:00 GMT', link='https://example.com/story'):
    return '<rss><channel><item><title>' + escape(title + ' - Test Publisher') + '</title><link>' + escape(link) + '</link><pubDate>' + published + '</pubDate><source>Test Publisher</source><description>' + escape(description) + '</description></item></channel></rss>'


class NewsTests(unittest.TestCase):
    def test_deduplication_preserves_both_scopes_without_article_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            data = sync_news.sync(Path(directory), NOW, lambda feed: feed_xml('U.S. Supreme Court reviews religious freedom in Texas'))
            self.assertEqual(len(data['items']), 1)
            self.assertEqual(data['items'][0]['scopes'], ['National', 'Texas'])
            self.assertNotIn('Article text must not be copied', json.dumps(data))

    def test_feed_failure_preserves_previous_records_and_reports_partial_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync_news.sync(root, NOW, lambda feed: feed_xml(feed['scope'] + ' original nationwide religious freedom story'))
            def partial(feed):
                if feed['id'] == 'texas':
                    raise RuntimeError('Temporary failure')
                return feed_xml('New nationwide religious freedom headline')
            data = sync_news.sync(root, NOW, partial)
            self.assertEqual(data['status'], 'partial')
            self.assertIn('Texas original nationwide religious freedom story', [item['title'] for item in data['items']])
            self.assertIn('New nationwide religious freedom headline', [item['title'] for item in data['items']])

    def test_total_failure_does_not_claim_new_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sync_news.sync(root, NOW, lambda feed: feed_xml())
            later = NOW.replace(hour=22)
            def fail(feed):
                raise RuntimeError('Unavailable')
            after = sync_news.sync(root, later, fail)
            self.assertEqual(after['status'], 'stale')
            self.assertEqual(after['updatedAt'], before['updatedAt'])
            self.assertEqual(after['items'], before['items'])

    def test_first_run_failure_does_not_publish_empty_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def fail(feed):
                raise RuntimeError('Unavailable')
            with self.assertRaises(RuntimeError):
                sync_news.sync(root, NOW, fail)
            self.assertFalse((root / 'dist/data/news.json').exists())

    def test_invalid_stale_future_and_unsafe_entries_are_rejected(self):
        feed = sync_news.FEEDS[0]
        for xml in [feed_xml(published='bad date'), feed_xml(published='Mon, 01 Sep 2025 18:00:00 GMT'), feed_xml(published='Wed, 11 Nov 2027 18:00:00 GMT'), feed_xml(link='javascript:alert(1)')]:
            self.assertEqual(sync_news.parse_feed(xml, feed, NOW), [])
        with self.assertRaises(ValueError):
            sync_news.parse_feed('<html>Error</html>', feed, NOW)

    def test_untrusted_headline_and_publisher_are_escaped(self):
        item = {'title':'<script>alert(1)</script>', 'url':'https://example.com/" onclick="bad', 'publisher':'<img src=x onerror=bad>', 'publishedAt':NOW.isoformat(), 'scopes':['Texas']}
        html = build_pages.news_card(item)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertIn('&lt;script&gt;', html)

    def test_pages_are_crawlable_scoped_and_have_unique_canonical_metadata(self):
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'dist/data').mkdir(parents=True)
            for name in ['index.html','app.js']:
                shutil.copy(source / 'dist' / name, root / 'dist' / name)
            sync_news.sync(root, NOW, lambda feed: feed_xml(feed['scope'] + ' religious liberty'))
            build_pages.build(root)
            once = (root / 'dist/index.html').read_text()
            build_pages.build(root)
            self.assertEqual(once, (root / 'dist/index.html').read_text())
            for path in ['news/index.html','news/texas/index.html','news/national/index.html','about/index.html','religious-liberty/index.html','sponsor/index.html']:
                html = (root / 'dist' / path).read_text()
                self.assertEqual(html.count('rel="canonical"'), 1)
                self.assertNotIn('<script src="app.js"', html)
                self.assertNotIn('Free hosting setup', html)
                for graph in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html):
                    json.loads(graph)
            texas = (root / 'dist/news/texas/index.html').read_text()
            self.assertIn('Texas religious liberty', texas)
            self.assertNotIn('National religious liberty</a>', texas)
            urls = ET.parse(root / 'dist/sitemap.xml').getroot()
            self.assertEqual(len(urls), 8)

    def test_scope_is_evidence_based_not_inherited_from_search(self):
        cases = [
            ('Florida mosque controversy sparks fight over development and religious freedom', []),
            ("Colorado universal preschool religious discrimination dispute", []),
            ('Religious Freedom Trails: Six Sacred Sites in Philadelphia', []),
            ('Federal court hears Maine religious freedom dispute', []),
            ('Texas Supreme Court considers religious liberty', ['Texas']),
            ('Colorado Supreme Court considers religious liberty', []),
            ('Supreme Court of Colorado considers religious liberty', []),
            ('India Supreme Court considers religious freedom', []),
            ('Supreme Court hears Colorado religious discrimination case', ['National']),
            ('U.S. Supreme Court reviews Texas religious freedom law', ['National', 'Texas']),
            ('Fifth Circuit hears religious freedom appeal', ['Texas']),
            ('5th Circuit protects free exercise', ['Texas']),
            ('Former McKinney mayor says religious freedom is fragile', ['Texas']),
            ('Congress considers nationwide religious liberty protections', ['National']),
            ('Church challenges federal policy on religious freedom', ['National']),
        ]
        for title, expected in cases:
            for feed in sync_news.FEEDS[:2]:
                with self.subTest(title=title, feed=feed['id']):
                    items = sync_news.parse_feed(feed_xml(title), feed, NOW)
                    self.assertEqual(items[0]['scopes'] if items else [], expected)

    def test_description_can_supply_evidence_but_publisher_cannot(self):
        feed = sync_news.FEEDS[0]
        xml = feed_xml('Court hears religious freedom dispute', description='Fifth Circuit considers school dispute')
        self.assertEqual(sync_news.parse_feed(xml, feed, NOW)[0]['scopes'], ['Texas'])
        xml = feed_xml('Florida mosque dispute', description='Florida mosque dispute Texas Tribune').replace('Test Publisher', 'Texas Tribune')
        self.assertEqual(sync_news.parse_feed(xml, feed, NOW), [])

    def test_legacy_mislabels_are_not_resurrected_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / 'dist/data/news.json'
            output.parent.mkdir(parents=True)
            titles = ['Florida mosque controversy', 'Texas religious freedom',
                      'Supreme Court hears Colorado religious discrimination case']
            items = [{'id': str(i), 'title': title, 'url': 'https://example.com/' + str(i),
                      'publisher': 'Test', 'publishedAt': NOW.isoformat(),
                      'scopes': ['Texas'], 'feedIds': ['texas']} for i, title in enumerate(titles)]
            output.write_text(json.dumps({'items': items, 'updatedAt': NOW.isoformat()}))
            def fail(feed):
                raise RuntimeError('offline')
            data = sync_news.sync(root, NOW, fail)
            by_title = {item['title']: item['scopes'] for item in data['items']}
            self.assertNotIn(titles[0], by_title)
            self.assertEqual(by_title[titles[1]], ['Texas'])
            self.assertEqual(by_title[titles[2]], ['National'])
            self.assertEqual(data['status'], 'stale')

    def test_valid_but_irrelevant_feed_does_not_restore_previous_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync_news.sync(root, NOW, lambda feed: feed_xml())
            data = sync_news.sync(root, NOW, lambda feed: feed_xml('Florida mosque dispute'))
            self.assertEqual(data['items'], [])
            self.assertEqual(data['status'], 'ok')

    def test_courthouse_rss_requires_topic_geography_and_publisher_domain(self):
        feed = next(f for f in sync_news.FEEDS if f['id'] == 'cns-texas-rss')
        def rss(title, link='https://www.courthousenews.com/story/'):
            return feed_xml(title=title, link=link).replace('<source>Test Publisher</source>', '')
        items = sync_news.parse_feed(rss('Texas court hears religious freedom dispute'), feed, NOW)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['publisher'], 'Courthouse News Service')
        for title, link in [
            ('Florida court hears religious freedom dispute', 'https://www.courthousenews.com/story/'),
            ('Texas court hears contract dispute', 'https://www.courthousenews.com/story/'),
            ('Texas court hears religious freedom dispute', 'https://example.com/story/'),
        ]:
            self.assertEqual(sync_news.parse_feed(rss(title, link), feed, NOW), [])


if __name__ == '__main__':
    unittest.main()

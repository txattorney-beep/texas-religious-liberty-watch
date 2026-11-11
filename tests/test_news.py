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


def feed_xml(title='Religious freedom in Texas', published='Wed, 11 Nov 2026 18:00:00 GMT', link='https://example.com/story'):
    return '<rss><channel><item><title>' + escape(title + ' - Test Publisher') + '</title><link>' + escape(link) + '</link><pubDate>' + published + '</pubDate><source>Test Publisher</source><description>Article text must not be copied.</description></item></channel></rss>'


class NewsTests(unittest.TestCase):
    def test_deduplication_preserves_both_scopes_without_article_bodies(self):
        with tempfile.TemporaryDirectory() as directory:
            data = sync_news.sync(Path(directory), NOW, lambda feed: feed_xml())
            self.assertEqual(len(data['items']), 1)
            self.assertEqual(data['items'][0]['scopes'], ['National', 'Texas'])
            self.assertNotIn('Article text must not be copied', json.dumps(data))

    def test_feed_failure_preserves_previous_records_and_reports_partial_status(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sync_news.sync(root, NOW, lambda feed: feed_xml(feed['scope'] + ' original'))
            def partial(feed):
                if feed['id'] == 'texas':
                    raise RuntimeError('Temporary failure')
                return feed_xml('New national headline')
            data = sync_news.sync(root, NOW, partial)
            self.assertEqual(data['status'], 'partial')
            self.assertIn('Texas original', [item['title'] for item in data['items']])
            self.assertIn('New national headline', [item['title'] for item in data['items']])

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
            for path in ['news/index.html','news/texas/index.html','news/national/index.html','about/index.html','religious-liberty/index.html']:
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
            self.assertEqual(len(urls), 6)


if __name__ == '__main__':
    unittest.main()

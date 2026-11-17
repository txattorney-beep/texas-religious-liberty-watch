import json
from pathlib import Path
import tempfile
import unittest
from scripts.guest_pages import load_guests, guest_strip, guest_pages


def fixture(**changes):
    data = {'slug': 'test-essay', 'title': 'A test essay', 'author': 'Test Writer', 'date': '2026-11-17', 'kind': 'Opinion', 'dek': 'Short description', 'body': ['First paragraph.', 'Second paragraph.'], 'authorBio': 'Test biography.', 'published': True}
    data.update(changes)
    return data


def shell(home, title, description, path, content):
    from html import escape
    return '<html><head><meta name="author" content="Eric A. Hudson"><meta property="og:type" content="website"><link rel="canonical" href="https://texasreligiouslibertywatch.org' + path + '"><title>' + escape(title) + '</title><script type="application/ld+json">{}</script></head><body>' + content + '</body></html>'


class GuestTests(unittest.TestCase):
    def load(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'content').mkdir()
            (root / 'content/guests.json').write_text(json.dumps(rows))
            return load_guests(root)

    def test_empty_strip_and_drafts_hidden(self):
        self.assertEqual(guest_strip([]), '')
        self.assertEqual(self.load([fixture(published=False)]), [])
        pages = guest_pages('', shell, [])
        self.assertEqual(list(pages), ['/voices/'])
        self.assertNotIn('test-essay', pages['/voices/'])

    def test_bad_slug_and_duplicate_rejected(self):
        for slug in ('../oops', 'Wrong Case', 'hello/there', '', '-test'):
            with self.assertRaises(ValueError):
                self.load([fixture(slug=slug)])
        with self.assertRaises(ValueError):
            self.load([fixture(), fixture()])

    def test_schema_strict(self):
        for bad in ({'published': 'false'}, {'body': []}, {'kind': 'Advertorial'}, {'date': '2026-02-30'}, {'author': ''}, {'featured': 'yes'}):
            with self.assertRaises(ValueError):
                self.load([fixture(**bad)])

    def test_featured_and_three_item_limit(self):
        rows = [fixture(slug='one', date='2026-11-17'), fixture(slug='two', date='2026-11-16', featured=True), fixture(slug='three'), fixture(slug='four')]
        loaded = self.load(rows)
        self.assertEqual(loaded[0]['slug'], 'two')
        strip = guest_strip(loaded)
        self.assertEqual(strip.count('class="guest-card'), 3)
        self.assertIn('guest-featured', strip)

    def test_injection_escaped_and_author_metadata(self):
        article = fixture(title='<script>alert(1)</script>', author='Writer " & <b>', body=['<img src=x onerror=alert(1)>'], authorBio='</script><script>bad()</script>')
        page = guest_pages('', shell, self.load([article]))['/voices/test-essay/']
        self.assertNotIn('<img src=x', page)
        self.assertNotIn('<script>bad()', page)
        self.assertIn('&lt;img', page)
        self.assertIn('content="Writer &quot; &amp; &lt;b&gt;"', page)
        self.assertIn('content="article"', page)
        self.assertNotIn('content="Eric A. Hudson"', page)
        self.assertIn('https://texasreligiouslibertywatch.org/voices/test-essay/', page)
        self.assertIn('"name": "Writer \\" & <b>"'.replace('<', '\\u003c'), page)

    def test_reporting_schema(self):
        page = guest_pages('', shell, self.load([fixture(kind='Reporting')]))['/voices/test-essay/']
        self.assertIn('"@type": "NewsArticle"', page)
        self.assertIn('By Test Writer', page)


if __name__ == '__main__':
    unittest.main()

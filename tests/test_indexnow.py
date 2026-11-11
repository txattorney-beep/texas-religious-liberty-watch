import json
from pathlib import Path
import tempfile
import unittest
from urllib.error import HTTPError
from scripts.submit_indexnow import run


class Response:
    def __init__(self, body=b'', status=200): self.body, self.status = body, status
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self): return self.body


class IndexNowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'dist/data').mkdir(parents=True)
        (self.root/'search').mkdir()
        self.key = 'a' * 32
        (self.root/'search/indexnow.json').write_text(json.dumps({'host':'example.org','keyFile':self.key+'.txt'}))
        (self.root/'dist'/f'{self.key}.txt').write_text(self.key)
        (self.root/'dist/index.html').write_text('<h1>Tracker</h1>')
        (self.root/'dist/data/bills.json').write_text('{"bills":[]}')
        (self.root/'dist/sitemap.xml').write_text('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>https://example.org/</loc></url></urlset>')
        self.calls = []

    def open(self, req, **kwargs):
        self.calls.append(req)
        return Response(self.key.encode()) if req.get_method() == 'GET' else Response(status=202)

    def test_receipt_saves_state_and_unchanged_pages_are_not_resent(self):
        self.assertEqual(run(self.root, opener=self.open), 1)
        self.assertEqual(run(self.root, opener=self.open), 0)
        self.assertEqual(len(self.calls), 2)
        (self.root/'dist/data/bills.json').write_text('{"bills":[{"id":"HB236"}]}')
        self.assertEqual(run(self.root, opener=self.open), 1)
        self.assertEqual(json.loads(self.calls[-1].data)['urlList'], ['https://example.org/'])

    def test_rejected_submission_leaves_state_for_retry(self):
        def reject(req, **kwargs):
            if req.get_method() == 'POST': raise HTTPError(req.full_url, 429, 'Too many requests', {}, None)
            return Response(self.key.encode())
        with self.assertRaises(HTTPError): run(self.root, opener=reject)
        self.assertFalse((self.root/'search/indexnow-state.json').exists())

    def test_wrong_host_is_rejected_before_network(self):
        p=self.root/'dist/sitemap.xml';p.write_text(p.read_text().replace('example.org','other.example'))
        with self.assertRaises(ValueError): run(self.root, opener=self.open)
        self.assertEqual(self.calls, [])

import json
from pathlib import Path
import struct
import unittest
from urllib.parse import urlsplit
from scripts.app_pages import app_pages
from scripts.build_pages import shell

ROOT=Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def test_app_contains_only_90r_navigation_and_retains_tracker(self):
        pages=app_pages((ROOT/'dist/index.html').read_text(),shell)
        app=pages['/90r/']
        for route in ['/news/','/rulings/','/hearings/']:
            self.assertNotIn('href="'+route+'"',app)
        for token in ['id="bill-list"','id="bill-dialog"','data-view="watchlist"','data-app="90r"','src="/app.js']:
            self.assertIn(token,app)
        self.assertNotIn('class="discovery-panel"',app)

    def test_install_page_is_within_app_and_does_not_run_tracker_script(self):
        page=app_pages((ROOT/'dist/index.html').read_text(),shell)['/90r/install/']
        self.assertIn('href="/90r/#watchlist"',page)
        self.assertIn('Safari',page)
        self.assertIn('href="#android"',page)
        self.assertIn('id="android"',page)
        self.assertIn('Chrome',page)
        self.assertIn('id="app-connection"',page)
        self.assertNotIn('src="app.js',page)
        self.assertNotIn('src="/app.js"',page)
        self.assertEqual(page.count('rel="canonical"'),1)

    def test_manifest_scope_shortcuts_and_icon_sizes(self):
        manifest=json.loads((ROOT/'dist/90r/manifest.webmanifest').read_text())
        self.assertEqual(manifest['scope'],'/90r/')
        self.assertEqual(manifest['start_url'],'/90r/')
        self.assertEqual(manifest['display'],'standalone')
        for shortcut in manifest['shortcuts']:
            self.assertTrue(urlsplit(shortcut['url']).path.startswith('/90r/'))
        self.assertTrue({'192x192','512x512'}<={i['sizes'] for i in manifest['icons']})
        for icon in manifest['icons']:
            raw=(ROOT/'dist'/icon['src'].lstrip('/')).read_bytes()
            self.assertEqual(raw[:8],b'\x89PNG\r\n\x1a\n')
            width,height=struct.unpack('>II',raw[16:24])
            self.assertEqual(f'{width}x{height}',icon['sizes'])
        apple=(ROOT/'dist/90r/icons/apple-touch-icon.png').read_bytes()
        self.assertEqual(struct.unpack('>II',apple[16:24]),(180,180))


if __name__=='__main__':unittest.main()

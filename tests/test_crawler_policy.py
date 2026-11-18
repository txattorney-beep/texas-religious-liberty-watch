"""Guard public discovery without restricting readers or AI search."""
from pathlib import Path
import unittest
from urllib.robotparser import RobotFileParser
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://texasreligiouslibertywatch.org"
BOTS = ("Googlebot", "Bingbot", "DuckDuckBot", "Applebot", "OAI-SearchBot")

class CrawlerPolicyTests(unittest.TestCase):
    def test_canonical_sitemap_and_public_pages_remain_crawlable(self):
        robots = RobotFileParser()
        robots.parse((ROOT / "dist/robots.txt").read_text().splitlines())
        self.assertIn(ORIGIN + "/sitemap.xml", robots.site_maps() or [])
        urls = [e.text for e in ET.parse(ROOT / "dist/sitemap.xml").findall(
            ".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        self.assertTrue(urls)
        for url in urls:
            self.assertTrue(url.startswith(ORIGIN + "/"), url)
            for bot in BOTS:
                self.assertTrue(robots.can_fetch(bot, url), (bot, url))
        for path in ("/app.js", "/styles.css", "/data/bills.json", "/data/news.json"):
            for bot in BOTS:
                self.assertTrue(robots.can_fetch(bot, ORIGIN + path), (bot, path))

    def test_source_downloads_not_advertised_to_crawlers(self):
        robots = RobotFileParser()
        robots.parse((ROOT / "dist/robots.txt").read_text().splitlines())
        for bot in BOTS:
            self.assertFalse(robots.can_fetch(bot, ORIGIN + "/downloads/source.zip"))

if __name__ == "__main__":
    unittest.main()

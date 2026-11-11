#!/usr/bin/env python3
"""Refresh attributed news headlines without copying article bodies or requiring an API key."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
TERMS = '("religious liberty" OR "religious freedom" OR "free exercise" OR "religious discrimination" OR "church-state")'
FEEDS = [
    {'id': 'texas', 'scope': 'Texas', 'label': 'Texas religious liberty news',
     'query': TERMS + ' (Texas OR "Fifth Circuit" OR "5th Circuit") when:30d'},
    {'id': 'national', 'scope': 'National', 'label': 'United States religious liberty news',
     'query': TERMS + ' ("United States" OR U.S. OR "U.S. Supreme Court" OR Congress OR federal) when:30d'},
]
for feed in FEEDS:
    feed['url'] = 'https://news.google.com/rss/search?' + urlencode({'q': feed['query'], 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})


def clean(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', '', unescape(text or ''))).strip()


def parse_feed(xml, feed, now):
    root = ET.fromstring(xml)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Expected a valid RSS channel.')
    articles = []
    for item in root.findall('./channel/item'):
        title, link = clean(item.findtext('title')), (item.findtext('link') or '').strip()
        source_element = item.find('source')
        publisher = clean(source_element.text) if source_element is not None else ''
        if not title or not publisher or urlsplit(link).scheme not in ('http', 'https'):
            continue
        try:
            published = parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
        except (ValueError, TypeError, AttributeError):
            continue
        if not now - timedelta(days=30) <= published <= now + timedelta(hours=6):
            continue
        suffix = ' - ' + publisher
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
        # Keep the national feed focused on domestic coverage when a headline is explicitly foreign.
        if feed['scope'] == 'National' and re.search(r'\b(India|Pakistan|Nigeria|China|Chinese|Beijing|Russia|Iran|Afghanistan|Bangladesh)\b', title, re.I) and not re.search(r'\b(U\.?S\.?|United States|American|Congress|Texas|Trump|Biden|State Department)\b', title, re.I):
            continue
        key = re.sub(r'\W+', '', title.casefold())
        articles.append({'id': hashlib.sha256(key.encode()).hexdigest()[:16], 'title': title,
                         'url': link, 'publisher': publisher, 'publishedAt': published.isoformat(),
                         'scopes': [feed['scope']], 'feedIds': [feed['id']]})
    return articles


def fetch_feed(feed):
    result = subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                             '--max-time', '30', '--retry', '2', '--retry-delay', '1',
                             '--user-agent', 'TexasReligiousLibertyWatch/1.0 (+https://texasreligiouslibertywatch.org)',
                             feed['url']], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:250] or 'Feed request failed.')
    return result.stdout


def sync(root=ROOT, now=None, fetch=fetch_feed):
    now = now or datetime.now(timezone.utc)
    output = root / 'dist/data/news.json'
    previous = json.loads(output.read_text()) if output.exists() else {'items': [], 'sources': []}
    results, sources = [], []
    with ThreadPoolExecutor(max_workers=len(FEEDS)) as pool:
        futures = {feed['id']: pool.submit(fetch, feed) for feed in FEEDS}
        for feed in FEEDS:
            prior_source = next((s for s in previous.get('sources', []) if s['id'] == feed['id']), {})
            source = {**feed, 'checkedAt': now.isoformat()}
            try:
                items = parse_feed(futures[feed['id']].result(), feed, now)
                # An unexpectedly empty result is treated as a retrieval failure when a prior feed exists.
                if not items and any(feed['id'] in item['feedIds'] for item in previous['items']):
                    raise ValueError('No current items returned; retaining the prior feed snapshot.')
                source.update(status='ok', lastSuccessAt=now.isoformat(), count=len(items))
            except Exception as error:
                source.update(status='error', lastSuccessAt=prior_source.get('lastSuccessAt'), error=str(error)[:250])
                items = [{**item, 'scopes': [feed['scope']], 'feedIds': [feed['id']]} for item in previous['items']
                         if feed['id'] in item['feedIds'] and datetime.fromisoformat(item['publishedAt']) >= now - timedelta(days=30)]
                source['count'] = len(items)
                print(f'::warning::{feed["label"]}: {error}')
            results.extend(items)
            sources.append(source)
    deduped = {}
    for item in results:
        if item['id'] in deduped:
            existing = deduped[item['id']]
            existing['scopes'] = sorted(set(existing['scopes'] + item['scopes']))
            existing['feedIds'] = sorted(set(existing['feedIds'] + item['feedIds']))
        else:
            deduped[item['id']] = item
    any_success = any(source['status'] == 'ok' for source in sources)
    data = {'updatedAt': now.isoformat() if any_success else previous.get('updatedAt'),
            'checkedAt': now.isoformat(), 'status': 'ok' if all(s['status'] == 'ok' for s in sources) else 'partial' if any_success else 'stale',
            'sources': sources, 'items': sorted(deduped.values(), key=lambda item: item['publishedAt'], reverse=True)[:160]}
    if not any_success and not previous['items']:
        raise RuntimeError('No news feed succeeded and no previous snapshot is available.')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(output)
    print(f'News refresh: {len(data["items"])} unique headlines, status {data["status"]}.')
    return data


if __name__ == '__main__':
    sync()

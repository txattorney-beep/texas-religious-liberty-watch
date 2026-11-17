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

# Use the publisher's own RSS feed; search-engine results can include court PDFs
# and unrelated state stories. Only attributed, relevant headlines are retained.
FEEDS.extend([
    {'id': 'cns-texas-rss', 'scope': 'Texas', 'label': 'Courthouse News Service: Texas and Fifth Circuit',
     'url': 'https://www.courthousenews.com/feed/', 'publisher': 'Courthouse News Service',
     'screen': 'Texas/Fifth Circuit or national evidence required'},
    {'id': 'cns-national-rss', 'scope': 'National', 'label': 'Courthouse News Service: national religious liberty',
     'url': 'https://www.courthousenews.com/feed/', 'publisher': 'Courthouse News Service',
     'screen': 'Texas/Fifth Circuit or national evidence required'},
])


def clean(text):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', '', unescape(text or ''))).strip()


# Feed queries discover candidates, not geographic relevance. Both Google and
# publisher feeds use the same positive-evidence screen. Do not use publisher
# names/URLs as evidence: a Texas publisher may report on another state.
SCOPE_VERSION = 1
TEXAS = r"\b(Texas|Texan|Houston|Dallas|Austin|San Antonio|El Paso|Fort Worth|McKinney|Plano|Frisco|Waco|Lubbock|Amarillo|Corpus Christi|Brownsville|Fifth Circuit|5th Circuit|Paxton|TEFA|EPIC City)\b"
NATIONAL = r"\b(U\.?S\.? Supreme Court|United States Supreme Court|SCOTUS|Congress|congressional|U\.?S\.? Senate|Senate confirmation|nationwide|across (?:the )?(?:nation|America|United States)|federal (?:policy|law|rule|regulation)|White House|State Department|IRS|EEOC|U\.?S\.? (?:companies|religious freedom rankings))\b"
# A bare Supreme Court normally means SCOTUS only when it is not explicitly a
# state/foreign court. State supreme courts must not become national by accident.
COURT_PLACES = r"state|Texas|Florida|Colorado|Louisiana|Mississippi|Alabama|Alaska|Arizona|Arkansas|California|Connecticut|Delaware|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Maine|Maryland|Massachusetts|Michigan|Minnesota|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming|India|Pakistan|Canada|Israel"
OTHER_COURT = r"\b(?:" + COURT_PLACES + r")(?:'s|’s)? Supreme Court\b"


def classify_scopes(title, description=''):
    """Return supported scopes; ambiguous/local out-of-area candidates are omitted.

    RSS summaries are screening input only, never published as article text.
    This is a conservative metadata screen, not a full-article legal review.
    """
    context = title + ' ' + description
    scopes = []
    if re.search(TEXAS, context, re.I):
        scopes.append('Texas')
    national = re.search(NATIONAL, context, re.I)
    without_state_courts = re.sub(OTHER_COURT, '', context, flags=re.I)
    # Also handle the formal 'Supreme Court of [state/country]' form.
    without_state_courts = re.sub(r'\bSupreme Court of (?:' + COURT_PLACES + r')\b', '', without_state_courts, flags=re.I)
    if national or re.search(r'\bSupreme Court\b', without_state_courts, re.I):
        scopes.append('National')
    return sorted(scopes)


def retained_items(previous, feed, now):
    """Re-screen legacy snapshots so an outage cannot restore old mislabels."""
    retained = []
    for item in previous['items']:
        if feed['id'] not in item['feedIds']:
            continue
        try:
            published = datetime.fromisoformat(item['publishedAt'])
            if not now - timedelta(days=30) <= published <= now + timedelta(hours=6):
                continue
        except (ValueError, TypeError):
            continue
        scopes = (item['scopes'] if item.get('scopeVersion') == SCOPE_VERSION
                  else classify_scopes(item['title']))
        if scopes:
            retained.append({**item, 'scopes': scopes, 'scopeVersion': SCOPE_VERSION,
                             'feedIds': [feed['id']]})
    return retained


def parse_feed(xml, feed, now):
    root = ET.fromstring(xml)
    if root.tag != 'rss' or root.find('channel') is None:
        raise ValueError('Expected a valid RSS channel.')
    articles = []
    for item in root.findall('./channel/item'):
        title, link = clean(item.findtext('title')), (item.findtext('link') or '').strip()
        source_element = item.find('source')
        publisher = clean(source_element.text) if source_element is not None else feed.get('publisher', '')
        if feed.get('publisher'):
            context = title + ' ' + clean(item.findtext('description'))
            if not re.search(r'\b(religio\w*|free exercise|church.state|faith|worship)\b', context, re.I):
                continue
            host = urlsplit(link).hostname or ''
            if host != 'courthousenews.com' and not host.endswith('.courthousenews.com'):
                continue
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
        description = clean(item.findtext('description'))
        # Google descriptions often append the publisher to the headline.
        description = description.replace(publisher, '').strip()
        scopes = classify_scopes(title, description)
        if not scopes:
            continue
        key = re.sub(r'\W+', '', title.casefold())
        articles.append({'id': hashlib.sha256(key.encode()).hexdigest()[:16], 'title': title,
                         'url': link, 'publisher': publisher, 'publishedAt': published.isoformat(),
                         'scopes': scopes, 'scopeVersion': SCOPE_VERSION, 'feedIds': [feed['id']]})
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
                xml = futures[feed['id']].result()
                items = parse_feed(xml, feed, now)
                # An unexpectedly empty result is treated as a retrieval failure when a prior feed exists.
                if not ET.fromstring(xml).findall('./channel/item') and retained_items(previous, feed, now):
                    raise ValueError('No current items returned; retaining the prior feed snapshot.')
                source.update(status='ok', lastSuccessAt=now.isoformat(), count=len(items))
            except Exception as error:
                source.update(status='error', lastSuccessAt=prior_source.get('lastSuccessAt'), error=str(error)[:250])
                items = retained_items(previous, feed, now)
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

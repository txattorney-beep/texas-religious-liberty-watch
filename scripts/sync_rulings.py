#!/usr/bin/env python3
"""Public opinion-feed monitoring. Search excerpts never become reviewed holdings."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from html import unescape
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urlencode, urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
TERMS = '("religious liberty" OR "religious freedom" OR "free exercise" OR RLUIPA OR RFRA OR "church autonomy" OR "ecclesiastical abstention" OR "religious accommodation" OR "religious discrimination" OR "Establishment Clause" OR "ministerial exception")'
FEEDS = [
    ('scotus', 'U.S. Supreme Court', 'scotus'),
    ('fifth', 'Fifth Circuit', 'ca5'),
    ('tx-federal', 'Texas federal district courts', 'txed txnd txsd txwd'),
    ('la-ms-federal', 'Louisiana & Mississippi federal district courts', 'laed lamd lawd msnd mssd'),
    ('tx-state', 'Texas state courts', 'tex texapp'),
    ('la-state', 'Louisiana state courts', 'la lactapp'),
    ('ms-state', 'Mississippi state courts', 'miss missctapp'),
]
NS = {'a': 'http://www.w3.org/2005/Atom'}


def clean(value):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]*>', ' ', value or ''))).strip()


def scope(court):
    value = court.casefold()
    if value in ('supreme court of the united states', 'united states supreme court', 'supreme court'):
        return 'U.S. Supreme Court', 'National'
    if 'court of appeals for the fifth circuit' in value or 'united states court of appeals, fifth circuit' in value:
        return 'Fifth Circuit', 'Regional'
    for state in ('Texas', 'Louisiana', 'Mississippi'):
        if state.casefold() in value and ('court' in value or 'district' in value):
            # District Court of Appeal is a state court; U.S. district feeds say District Court, ... District of ...
            federal = 'district court' in value and ('district of' in value or 'united states' in value or 'u.s.' in value)
            return ('Federal district' if federal else 'State court'), state
    return None


def in_window(value, start, end):
    try:
        day = datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        return start <= day <= end
    except (ValueError, TypeError):
        return False


def parse_feed(raw, feed, start, end):
    root = ET.fromstring(raw)
    if root.tag != '{http://www.w3.org/2005/Atom}feed':
        raise ValueError('Expected CourtListener Atom opinion feed.')
    items = []
    entries = root.findall('a:entry', NS)
    for entry in entries:
        name = clean(entry.findtext('a:title', '', NS))
        court = clean(entry.findtext('a:author/a:name', '', NS))
        jurisdiction = scope(court)
        published = entry.findtext('a:published', '', NS)
        link = next((node.get('href', '') for node in entry.findall('a:link', NS) if node.get('rel', 'alternate') == 'alternate'), '')
        parts = urlsplit(link)
        if not name or not jurisdiction or not in_window(published, start, end):
            continue
        if parts.scheme != 'https' or parts.hostname not in ('www.courtlistener.com', 'courtlistener.com') or not parts.path.startswith('/opinion/'):
            continue
        # Defensive scope check even when a provider ignores a query parameter.
        group, state = jurisdiction
        expected = feed['id']
        if expected == 'scotus' and group != 'U.S. Supreme Court': continue
        if expected == 'fifth' and group != 'Fifth Circuit': continue
        if expected.endswith('-state') and (group != 'State court' or state != {'tx-state':'Texas','la-state':'Louisiana','ms-state':'Mississippi'}[expected]): continue
        if expected.endswith('-federal') and (group != 'Federal district' or state not in (['Texas'] if expected == 'tx-federal' else ['Louisiana','Mississippi'])): continue
        excerpt = clean(entry.findtext('a:summary', '', NS)).removesuffix('Original document').strip()
        # Bound excerpts and mark them as search-result text, never as a statement of the holding.
        excerpt = ' '.join(excerpt.split()[:65])
        canonical = 'https://www.courtlistener.com' + parts.path
        items.append({'id':'cl-' + hashlib.sha256(canonical.encode()).hexdigest()[:16], 'name':name,
                      'court':court, 'group':group, 'state':state, 'date':published[:10],
                      'sourceUrl':canonical, 'sourceLabel':'CourtListener opinion', 'excerpt':excerpt,
                      'reviewState':'Opinion match', 'feedIds':[feed['id']]})
    return items, len(entries)


def fetch_feed(feed):
    result = subprocess.run(['curl','--fail','--location','--silent','--show-error','--max-time','35',
                             '--retry','1','--user-agent','TexasReligiousLibertyWatch/1.0 (+https://texasreligiouslibertywatch.org)',feed['url']],
                            capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[:200] or 'Feed request failed')
    return result.stdout


def key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def curated_match(item, records):
    return any(item['date'] == record['date'] and item['group'] == record['group'] and
               key(item['name']) in {key(name) for name in [record['name'], *record.get('matchNames', [])]}
               for record in records)


def sync(root=ROOT, now=None, fetch=fetch_feed):
    now = now or datetime.now(timezone.utc)
    end = now.astimezone(ZoneInfo('America/Chicago')).date()
    start = end - timedelta(days=180)
    output = root / 'dist/data/rulings.json'
    prior = json.loads(output.read_text()) if output.exists() else {'matches':[], 'sources':[]}
    editorial = json.loads((root / 'court_editorial.json').read_text())
    reviewed = [{**record, 'reviewState':'Source checked'} for record in editorial['rulings'] if in_window(record['date'], start, end)]
    excluded = set(editorial.get('excludedUrls', []))
    feeds = []
    for ident, label, courts in FEEDS:
        query = TERMS + f' dateFiled:[{start} TO {end}]'
        url = 'https://www.courtlistener.com/feed/search/?' + urlencode({'q':query, 'court':courts, 'order_by':'dateFiled desc', 'type':'o'})
        feeds.append({'id':ident,'label':label,'url':url})
    sources, collected = [], []
    # Retain discovered records inside the rolling window, even when they roll off the RSS result limit.
    for item in prior.get('matches', []):
        if in_window(item['date'], start, end): collected.append(item)
    with ThreadPoolExecutor(max_workers=3) as pool:
        pending = {feed['id']:pool.submit(fetch, feed) for feed in feeds}
        for feed in feeds:
            previous = next((s for s in prior.get('sources',[]) if s['id']==feed['id']), {})
            source = {**feed, 'checkedAt':now.isoformat()}
            try:
                items, count = parse_feed(pending[feed['id']].result(), feed, start, end)
                collected.extend({**item, 'firstSeenAt':now.isoformat()} for item in items)
                source.update(status='ok', lastSuccessAt=now.isoformat(), count=len(items), returnedCount=count,
                              possiblyLimited=count>=20)
            except Exception as error:
                source.update(status='error', lastSuccessAt=previous.get('lastSuccessAt'), error=str(error)[:220])
                print(f'::warning::{feed["label"]}: {error}')
            sources.append(source)
    deduped = {}
    for item in collected:
        if item['sourceUrl'] in excluded or curated_match(item, reviewed): continue
        if item['id'] in deduped:
            item['firstSeenAt'] = deduped[item['id']]['firstSeenAt']
            item['feedIds'] = sorted(set(item['feedIds'] + deduped[item['id']]['feedIds']))
        deduped[item['id']] = item
    success = sum(s['status']=='ok' for s in sources)
    result = {'version':1,'windowStart':start.isoformat(),'windowEnd':end.isoformat(),'windowDays':180,
              'checkedAt':now.isoformat(),'updatedAt':now.isoformat() if success else prior.get('updatedAt'),
              'status':'ok' if success==len(sources) else 'partial' if success else 'stale',
              'editorialCheckedAt':editorial['checkedAt'], 'sources':sources,
              'rulings':sorted(reviewed,key=lambda r:r['date'],reverse=True),
              'matches':sorted(deduped.values(),key=lambda r:r['date'],reverse=True)}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(f'Court watch: {len(reviewed)} source-checked rulings; {len(deduped)} opinion matches; {result["status"]}.')
    return result


if __name__ == '__main__':
    sync()

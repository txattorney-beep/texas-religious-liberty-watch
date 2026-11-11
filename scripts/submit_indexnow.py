#!/usr/bin/env python3
"""Notify IndexNow after publishing new or changed public pages."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = 'https://api.indexnow.org/indexnow'


def snapshot(root, host):
    result = {}
    tree = ET.parse(root / 'dist/sitemap.xml')
    for element in tree.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
        url = element.text
        parts = urlsplit(url)
        if parts.scheme != 'https' or parts.netloc != host or parts.query or parts.fragment:
            raise ValueError('Sitemap contains an unexpected URL.')
        if '..' in parts.path.split('/'):
            raise ValueError('Sitemap contains an unsafe path.')
        path = root / 'dist' / parts.path.strip('/') / 'index.html'
        digest = hashlib.sha256(path.read_bytes())
        # These two pages load the bill snapshot through JavaScript.
        if parts.path in ('/', '/90r/'):
            digest.update((root / 'dist/data/bills.json').read_bytes())
        result[url] = digest.hexdigest()
    return result


def run(root=ROOT, dry_run=False, opener=urlopen):
    config = json.loads((root / 'search/indexnow.json').read_text())
    host, key_file = config['host'], config['keyFile']
    if not re.fullmatch(r'[a-z0-9.-]+', host) or not re.fullmatch(r'[a-f0-9]{32}\.txt', key_file):
        raise ValueError('Invalid IndexNow host or key file.')
    key = (root / 'dist' / key_file).read_text().strip()
    if key_file != key + '.txt':
        raise ValueError('IndexNow key file content does not match its name.')
    state_path = root / 'search/indexnow-state.json'
    previous = json.loads(state_path.read_text()).get('pages', {}) if state_path.exists() else {}
    current = snapshot(root, host)
    changed = [url for url, digest in current.items() if previous.get(url) != digest]
    if not changed:
        print('IndexNow: no changed pages to submit.')
        return 0
    if len(changed) > 10000:
        raise ValueError('IndexNow batch exceeds 10,000 URLs.')
    if dry_run:
        print(json.dumps({'changedUrls': changed}, indent=2))
        return len(changed)
    key_url = f'https://{host}/{key_file}'
    with opener(Request(key_url, headers={'Cache-Control': 'no-cache'}), timeout=30) as response:
        if response.read().decode().strip() != key:
            raise ValueError('Published IndexNow key does not match. Retry after deployment.')
    payload = {'host': host, 'key': key, 'keyLocation': key_url, 'urlList': changed}
    request = Request(ENDPOINT, data=json.dumps(payload).encode(),
                      headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    with opener(request, timeout=45) as response:
        status = response.status
        if status not in (200, 202):
            raise RuntimeError(f'IndexNow returned HTTP {status}.')
    state_path.write_text(json.dumps({'submittedAt': datetime.now(timezone.utc).isoformat(),
                                     'httpStatus': status, 'submittedUrls': changed,
                                     'pages': current}, indent=2) + '\n')
    print(f'IndexNow received {len(changed)} URLs (HTTP {status}). Receipt does not guarantee indexing.')
    print('\n'.join(changed))
    return len(changed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    try:
        run(dry_run=args.dry_run)
    except Exception as error:
        print(f'IndexNow submission failed: {error}', file=sys.stderr)
        sys.exit(1)

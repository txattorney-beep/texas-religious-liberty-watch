#!/usr/bin/env python3
"""Create a portable source archive without Site identity or local state."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist/downloads/texas-liberty-watch-starter.zip'
out.parent.mkdir(parents=True,exist_ok=True)
included=['dist/index.html','dist/styles.css','dist/app.js','dist/favicon.svg','dist/data/bills.json','editorial.json','README.md','.gitignore','.github/workflows/publish.yml','scripts/sync_tlo.py','scripts/package_starter.py','tests/test_sync.py']
included += ['dist/hearings.js','dist/data/hearings.json','scripts/sync_hearings.py','scripts/hearing_pages.py','tests/test_hearings.py','dist/news.css','dist/news.js','dist/data/news.json','dist/robots.txt','dist/sitemap.xml','scripts/sync_news.py','scripts/build_pages.py','tests/test_news.py']
included += ['court_editorial.json','dist/rulings.js','dist/data/rulings.json','scripts/sync_rulings.py','scripts/ruling_pages.py','tests/test_rulings.py']
included += ['dist/mobile.css','scripts/app_pages.py','tests/test_app.py','tests/pwa.test.cjs']
included += ['scripts/submit_indexnow.py','tests/test_indexnow.py','search/indexnow.json']
import json
included += ['dist/' + json.loads((ROOT/'search/indexnow.json').read_text())['keyFile']]
included += [str(path.relative_to(ROOT)) for path in (ROOT/'dist/90r').rglob('*') if path.is_file()]
for folder in ('dist/news','dist/about','dist/religious-liberty','dist/hearings','dist/rulings'):
    included += [str(path.relative_to(ROOT)) for path in (ROOT/folder).rglob('*.html')]
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for name in included: archive.write(ROOT/name, name)
print(f'Created {out.name} ({out.stat().st_size:,} bytes)')



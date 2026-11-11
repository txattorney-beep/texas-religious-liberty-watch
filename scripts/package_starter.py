#!/usr/bin/env python3
"""Create a portable source archive without Site identity or local state."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'dist/downloads/texas-liberty-watch-starter.zip'
out.parent.mkdir(parents=True,exist_ok=True)
included=['dist/index.html','dist/styles.css','dist/app.js','dist/favicon.svg','dist/data/bills.json','editorial.json','README.md','.gitignore','.github/workflows/publish.yml','scripts/sync_tlo.py','scripts/package_starter.py','tests/test_sync.py']
with ZipFile(out,'w',ZIP_DEFLATED) as archive:
    for name in included: archive.write(ROOT/name, name)
print(f'Created {out.name} ({out.stat().st_size:,} bytes)')

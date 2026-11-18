"""Central-time refresh windows, isolated collectors, and public snapshot checks."""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]
CENTRAL=ZoneInfo('America/Chicago')
FEEDS={'bills':['sync_tlo.py','--text'],'news':['sync_news.py'],'hearings':['sync_hearings.py'],'rulings':['sync_rulings.py']}
def latest_window(now):
 local=now.astimezone(CENTRAL)
 windows=[local.replace(hour=h,minute=30,second=0,microsecond=0) for h in (7,16)]
 return max([w for w in windows if w<=local] or [windows[-1]-dt.timedelta(days=1)])
def due(health,now):
 for name in FEEDS:
  if name=='bills' and now.astimezone(CENTRAL).date()>dt.date(2027,5,31):continue
  item=health.get('feeds',{}).get(name,{})
  try:
   if item.get('status')!='ok' or dt.datetime.fromisoformat(item['lastSuccessAt'])<latest_window(now):return True
  except (KeyError,ValueError,TypeError):return True
 return False
def load(path,default=None):
 return json.loads(path.read_text()) if path.exists() else (default or {})
def refresh():
 path=ROOT/'dist/data/refresh-health.json'; old=load(path); now=dt.datetime.now(dt.timezone.utc)
 feeds={}
 for name,args in FEEDS.items():
  data_path=ROOT/f'dist/data/{name}.json'; previous=load(data_path)
  if name=='bills' and now.astimezone(CENTRAL).date()>dt.date(2027,5,31):
   feeds[name]={'status':'archived','lastSuccessAt':previous.get('updatedAt')};continue
  error=None
  try:
   result=subprocess.run([sys.executable,str(ROOT/'scripts'/args[0]),*args[1:]],timeout=480)
   if result.returncode:error=f'Collector exited {result.returncode}'
  except subprocess.TimeoutExpired:error='Collector timed out'
  data=load(data_path)
  status='stale' if error else data.get('status','ok')
  if name=='bills' and any(b.get('textFetchError') for b in data.get('bills',[])):status='partial'
  if error:
   data_path.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n');data=previous
  feeds[name]={'status':status,'checkedAt':dt.datetime.now(dt.timezone.utc).isoformat(),'snapshotAt':data.get('checkedAt',data.get('updatedAt')),'lastSuccessAt':data.get('updatedAt') if status=='ok' else old.get('feeds',{}).get(name,{}).get('lastSuccessAt'),'error':error}
  if status not in ('ok','archived'):print(f'::warning::{name}: {status}; last good records retained')
 path.write_text(json.dumps({'checkedAt':now.isoformat(),'feeds':feeds},indent=2)+'\n')
def verify():
 expected={name:load(ROOT/f'dist/data/{name}.json') for name in FEEDS}
 health=load(ROOT/'dist/data/refresh-health.json')
 def get(path):
  request=urllib.request.Request('https://texasreligiouslibertywatch.org'+path,headers={'Cache-Control':'no-cache','User-Agent':'LibertyWatch-publication-check'})
  with urllib.request.urlopen(request,timeout=30) as r:return r.read().decode()
 for attempt in range(25):
  try:
   for name,data in expected.items():
    live=json.loads(get(f'/data/{name}.json'))
    if live!=data:raise ValueError(name+' live data does not match publication')
   if json.loads(get('/data/refresh-health.json'))!=health:raise ValueError('Live health status is outdated')
   for page in ['/','/news/','/hearings/','/courts/']:
    if '/refresh-status.js' not in get(page):raise ValueError(page+' missing refresh status')
   break
  except Exception as e:
   if attempt==24:raise
   print('Waiting for public edition:',e,flush=True);time.sleep(20)
 failed=[n for n,s in health['feeds'].items() if s['status'] not in ('ok','archived')]
 if failed:raise RuntimeError('Published accurately labeled partial results: '+', '.join(failed))
 print('Verified all four public snapshots, pages, and source health')
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'verify'
 if command=='gate':
  refresh_needed=os.environ.get('GITHUB_EVENT_NAME')!='schedule' or due(load(ROOT/'dist/data/refresh-health.json'),dt.datetime.now(dt.timezone.utc))
  with open(os.environ['GITHUB_OUTPUT'],'a') as out:out.write(f"refresh={str(refresh_needed).lower()}\n")
 elif command=='refresh':refresh()
 else:verify()

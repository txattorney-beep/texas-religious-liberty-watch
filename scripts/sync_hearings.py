#!/usr/bin/env python3
"""Match official 90R committee notices to tracked bills; retain revisions and cancellations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import hashlib
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
SESSION = '90R'
BASE = 'https://capitol.texas.gov'
SOURCES = [
    {'id':'house-rss','label':'House upcoming meeting feed','kind':'rss','url':BASE+'/MyTLO/RSS/RSS.aspx?Type=upcomingmeetingshouse'},
    {'id':'senate-rss','label':'Senate upcoming meeting feed','kind':'rss','url':BASE+'/MyTLO/RSS/RSS.aspx?Type=upcomingmeetingssenate'},
    *[{'id':name+'-list','label':name.title()+' upcoming meeting notices','kind':'html','url':BASE+'/Committees/MeetingsUpcoming.aspx?Chamber='+chamber} for name,chamber in [('house','H'),('senate','S'),('joint','J')]],
]
BILL = re.compile(r'\b(HJR|SJR|HCR|SCR|HB|SB|HR|SR)\s*0*(\d+)\b', re.I)


class NoticeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.links, self.hidden = [], [], 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script','style'):
            self.hidden += 1
        if tag == 'a':
            href = dict(attrs).get('href')
            if href:
                self.links.append(href)
        if tag in ('p','tr','td','div','br'):
            self.parts.append(' ')
    def handle_endtag(self, tag):
        if tag in ('script','style'):
            self.hidden = max(0, self.hidden-1)
        if tag in ('p','tr','td','div'):
            self.parts.append(' ')
    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
    @property
    def text(self):
        return ' '.join(' '.join(self.parts).split())


def fetch(url):
    result = subprocess.run(['curl','--fail','--silent','--show-error','--location','--max-time','25','--retry','1',url], capture_output=True, check=True)
    try:
        return result.stdout.decode('utf-8-sig')
    except UnicodeDecodeError:
        return result.stdout.decode('cp1252', errors='replace')


def notice_url(value, session=SESSION):
    url = urljoin(BASE, unescape(value).strip())
    parts = urlsplit(url)
    if parts.hostname != 'capitol.texas.gov' or parts.scheme not in ('https','http'):
        return None
    match = re.fullmatch(r'/tlodocs/'+re.escape(session)+r'/schedules/(?:html|pdf)/(C\d+)\.(?:htm|pdf)', parts.path, re.I)
    if not match:
        return None
    return BASE+'/tlodocs/'+session+'/schedules/html/'+match[1].upper()+'.HTM'


def discover(raw, source, session=SESSION):
    links = []
    if source['kind'] == 'rss':
        root = ET.fromstring(raw)
        channel = root.find('channel')
        if root.tag != 'rss' or channel is None or 'committee meetings' not in (channel.findtext('title') or '').lower():
            raise ValueError('Expected the official committee-meetings RSS channel.')
        for item in channel.findall('item'):
            for tag in ('link','guid'):
                if item.findtext(tag):
                    links.append(item.findtext(tag))
            parser = NoticeHTML(); parser.feed(item.findtext('description') or '')
            links.extend(parser.links)
    else:
        parser = NoticeHTML(); parser.feed(raw)
        if 'committee meetings' not in parser.text.lower():
            raise ValueError('Expected the official committee-meetings page.')
        links.extend(parser.links)
    return sorted({url for link in links if (url := notice_url(link, session))})


def bill_ids(text):
    return sorted({kind.upper()+str(int(number)) for kind,number in BILL.findall(text)})


def parse_notice(raw, url, now, session=SESSION):
    url = notice_url(url, session)
    if not url:
        raise ValueError('Notice does not belong to the monitored session.')
    parser = NoticeHTML(); parser.feed(raw)
    text = parser.text
    if not re.search(r'NOTICE OF (?:PUBLIC HEARING|FORMAL MEETING|WORK SESSION|MEETING)', text, re.I):
        raise ValueError('Expected an official hearing or meeting notice.')
    header = re.search(r'COMMITTEE:\s*(.*?)\s*TIME\s*&\s*DATE:\s*(.*?)\s*PLACE:\s*(.*?)\s*CHAIR:', text, re.I)
    if not header:
        raise ValueError('Committee, date, or location fields could not be read.')
    committee, time_date, location = (value.strip() for value in header.groups())
    date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})', time_date, re.I)
    date_inferred = False
    if date_match:
        meeting_date = datetime.strptime(' '.join(date_match.groups()), '%B %d %Y').date().isoformat()
    else:
        # Some canceled notices replace the date field with "Meeting Cancelled".
        encoded = re.search(r'/C\d{3}(\d{8})\d+\.HTM$', url)
        if not encoded:
            raise ValueError('Notice has no readable meeting date.')
        meeting_date = datetime.strptime(encoded[1], '%Y%m%d').date().isoformat()
        date_inferred = True
    deleted = re.split(r'Bills deleted after last posting\s*:', text, maxsplit=1, flags=re.I)
    active = bill_ids(deleted[0])
    removed = bill_ids(re.split(r'NOTICE OF ASSISTANCE|See Committee Coordinator', deleted[1], flags=re.I)[0]) if len(deleted)>1 else []
    active = sorted(set(active)-set(removed))
    # Only an explicit notice cancellation is a cancellation; disappearance is not.
    canceled = bool(re.search(r'\b(?:MEETING|HEARING)\s+(?:HAS BEEN\s+|IS\s+)?CANCEL[LE]*D\b|\*\*\s*CANCEL[LE]*D\s*\*\*', text, re.I))
    chamber = 'House' if 'HOUSE OF REPRESENTATIVES' in text else 'Senate' if re.search(r'\bSENATE\b', text) else 'Joint'
    relevant_text = text[text.upper().find('NOTICE OF '):]
    return {'id':url.rsplit('/',1)[-1].split('.')[0], 'session':session, 'committee':committee,
            'chamber':chamber, 'date':meeting_date, 'timeAndDate':time_date, 'dateFromFilename':date_inferred,
            'location':location, 'status':'Canceled' if canceled else 'Scheduled',
            'noticeUrl':url, 'pdfUrl':url.replace('/html/','/pdf/').replace('.HTM','.PDF'),
            'billIds':active, 'removedBillIds':removed, 'revised':bool(re.search(r'\*\*\s*REVISION\s*\*\*', text, re.I)),
            'textHash':hashlib.sha256(relevant_text.encode()).hexdigest(), 'lastVerifiedAt':now.isoformat()}


def merge_notice(current, previous, tracked, now):
    old = previous or {}
    removed = set(current['removedBillIds']) | (set(old.get('billIds',[]))-set(current['billIds']))
    current['removedBillIds'] = sorted(removed-set(current['billIds']))
    current['relatedBills'] = sorted((set(current['billIds']) | removed | set(old.get('relatedBills',[]))) & tracked)
    current['firstSeenAt'] = old.get('firstSeenAt', now.isoformat())
    current['changes'] = list(old.get('changes',[]))
    changed = old and current['textHash'] != old.get('textHash')
    current['lastChangedAt'] = now.isoformat() if changed or not old else old.get('lastChangedAt',old['firstSeenAt'])
    if not old:
        current['changes'].append({'at':now.isoformat(),'kind':'Notice first detected','detail':'Matched '+', '.join(current['relatedBills'])})
    elif changed:
        details=[]
        for key,label in [('status','Status'),('timeAndDate','Time/date'),('location','Location')]:
            if current[key] != old.get(key):
                details.append(label+': '+str(old.get(key,'Not recorded'))+' → '+current[key])
        added = set(current['billIds'])-set(old.get('billIds',[]))
        dropped = set(old.get('billIds',[]))-set(current['billIds'])
        if added & tracked: details.append('Tracked bills added: '+', '.join(sorted(added & tracked)))
        if dropped & tracked: details.append('Tracked bills removed: '+', '.join(sorted(dropped & tracked)))
        current['changes'].append({'at':now.isoformat(),'kind':'Cancellation detected' if current['status']=='Canceled' else 'Notice changed','detail':'; '.join(details) or 'The official notice text changed. Read the current notice.'})
    current['changes'] = current['changes'][-30:]
    return current


def sync(root=ROOT, now=None, get=fetch):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('America/Chicago')).date()
    bills = json.loads((root/'dist/data/bills.json').read_text())
    if bills.get('session') != SESSION:
        raise ValueError('Bill snapshot session mismatch.')
    tracked = {bill['id'] for bill in bills['bills']}
    output = root/'dist/data/hearings.json'
    previous = json.loads(output.read_text()) if output.exists() else {'events':[], 'sources':[]}
    if previous.get('session',SESSION) != SESSION:
        raise ValueError('Hearing snapshot session mismatch.')
    old_events = {event['noticeUrl']:event for event in previous['events']}
    discovered, sources = set(), []
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {source['id']:pool.submit(get,source['url']) for source in SOURCES}
        for source in SOURCES:
            state = {**source,'checkedAt':now.isoformat()}
            try:
                urls = discover(tasks[source['id']].result(),source)
                discovered.update(urls)
                state.update(status='ok',noticeCount=len(urls))
            except Exception as error:
                state.update(status='error',error=str(error)[:200])
                print(f'::warning::{source["label"]}: {error}')
            sources.append(state)
    if len(discovered)>1000:
        raise ValueError('Unexpected notice count; previous snapshot preserved.')
    recent_cutoff = (today-timedelta(days=7)).isoformat()
    revisit = {url for url,event in old_events.items() if event['date']>=recent_cutoff}
    events = {url:dict(event) for url,event in old_events.items()}
    failures=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = {url:pool.submit(get,url) for url in sorted(discovered|revisit)}
        for url,task in tasks.items():
            try:
                event = parse_notice(task.result(),url,now)
                event = merge_notice(event,old_events.get(url),tracked,now)
                event['listedInUpcoming'] = url in discovered if all(s['status']=='ok' for s in sources) else None
                if event['relatedBills']:
                    events[url] = event
            except Exception as error:
                failures.append({'url':url,'error':str(error)[:160]})
                if url in events:
                    events[url]['retrievalError'] = str(error)[:160]
                    events[url]['lastAttemptedAt'] = now.isoformat()
    success = any(source['status']=='ok' for source in sources)
    data = {'session':SESSION,'updatedAt':now.isoformat() if success else previous.get('updatedAt'),
            'checkedAt':now.isoformat(),'status':'ok' if all(s['status']=='ok' for s in sources) and not failures else 'partial' if success else 'stale',
            'trackedBillCount':len(tracked),'discoveredNoticeCount':len(discovered),'sources':sources,'noticeErrors':failures,
            'events':sorted(events.values(),key=lambda event:(event['date'],event['committee'],event['id']))}
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temporary.replace(output)
    print(f'Hearing watch: {len(discovered)} current 90R notices; {len(events)} notices matched/retained; status {data["status"]}.')
    return data


if __name__ == '__main__':
    sync()

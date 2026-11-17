"""Headline-first editorial front page; source data remains independent."""
from html import escape as E
from datetime import datetime
import re
from zoneinfo import ZoneInfo

def section(item):
    if re.search(r'\b(?:fifth|5th)\s+circuit\b', item['title'], re.I):
        return 'Fifth Circuit'
    return 'Texas' if 'Texas' in item['scopes'] else 'National'

def card(item, lead=False):
    date = datetime.fromisoformat(item['publishedAt']).astimezone(ZoneInfo('America/Chicago')).strftime('%b %d, %Y')
    tag = 'h2' if lead else 'h3'
    cls = 'wire-lead' if lead else 'wire-item'
    search = E(item['title'] + ' ' + item['publisher'], quote=True)
    return f'<article class="{cls}" data-news-title="{search}"><p class="wire-meta">{E(item["publisher"])} · <time datetime="{E(item["publishedAt"],quote=True)}">{date}</time></p><{tag}><a href="{E(item["url"],quote=True)}" target="_blank" rel="noopener noreferrer">{E(item["title"])}</a></{tag}></article>'

def wire_content(data, guests='', scope=None):
    items = sorted([x for x in data['items'] if not scope or scope in x['scopes']], key=lambda x:x['publishedAt'], reverse=True)
    lead = next((x for x in items if section(x)=='Texas'), items[0] if items else None)
    columns=[]
    for name in ['Texas','Fifth Circuit','National']:
        if scope=='National' and name!='National': continue
        if scope=='Texas' and name=='National': continue
        entries=[x for x in items if section(x)==name and x!=lead]
        columns.append(f'<section class="wire-column"><h2>{name}</h2>'+(''.join(card(x) for x in entries) or '<p class="wire-empty">No additional current headlines in this section.</p>')+'</section>')
    checked=datetime.fromisoformat(data['updatedAt']).astimezone(ZoneInfo('America/Chicago')).strftime('%b %d, %Y · %I:%M %p %Z') if data.get('updatedAt') else 'Awaiting refresh'
    status='<p class="news-warning">Some sources could not be refreshed. Previously collected headlines retain their original dates.</p>' if data.get('status')!='ok' else ''
    heading=E(f'{scope} religious liberty news' if scope else 'Religious liberty. In focus.')
    return f'''<section class="wire-intro"><p class="eyebrow">TEXAS · THE FIFTH CIRCUIT · THE NATION</p><h1>{heading}</h1><p>Every faith. Equal liberty.</p></section>
<nav class="wire-nav" aria-label="Editorial navigation"><a href="/">Front page</a><a href="/news/">News</a><a href="/voices/">Guest voices</a><a href="/#tracker">Bill tracker</a><a href="/rulings/">Court rulings</a><a href="/hearings/">Hearings</a><a href="/about/">About</a><a href="/sponsor/">Advertising</a></nav>
<p class="wire-edition">Updated {checked} · Morning & afternoon editions</p>{status}<p id="news-stale" class="news-warning" data-updated="{E(data.get('updatedAt') or '',quote=True)}" hidden>This news snapshot is more than 36 hours old. A refresh is due.</p>
<form id="news-search-form" class="wire-search" role="search"><label class="sr-only" for="news-search">Search headlines and publishers</label><input id="news-search" type="search" placeholder="Search headlines and publishers…"><button type="submit">Search</button></form><p id="news-count" class="wire-count" aria-live="polite">{len(items)} headlines from the past 30 days</p>
{card(lead,True) if lead else '<p>No current headlines. Check the official sources below.</p>'}{guests}
<div class="wire-columns">{''.join(columns)}</div><p id="news-empty" hidden>No headlines match that search.</p>
<div class="wire-tools"><div><h2>Follow the law behind the headlines.</h2><p>Track proposals, read court rulings, and check upcoming hearings.</p></div><a href="/#tracker">90R bill tracker →</a><a href="/rulings/">Court rulings →</a><a href="/hearings/">Hearings & notices →</a></div>
<details class="wire-method"><summary>Sources & editorial standards</summary><p>Headlines link to their original publishers. Inclusion is not endorsement. Automated screening uses available headline and feed metadata, not a full-article review. Texas and Fifth Circuit coverage is separated from national coverage; ambiguous stories can be omitted. Guest contributions are separately edited and labeled as opinion, analysis, or reporting. Official court and legislative records control.</p><ul>{''.join('<li>'+E(s['label'])+': '+('Checked successfully' if s['status']=='ok' else 'Refresh unavailable; prior records retained')+'</li>' for s in data.get('sources',[]))}</ul></details>
<script src="/news.js?v=wire-20261117" defer></script>'''

#!/usr/bin/env python3
"""Build crawlable news, profile, and topic pages from the published snapshot."""
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
try:
    from .hearing_pages import hearing_page
    from .ruling_pages import ruling_page
    from .app_pages import app_pages
except ImportError:
    from hearing_pages import hearing_page
    from ruling_pages import ruling_page
    from app_pages import app_pages

ROOT = Path(__file__).resolve().parents[1]
SITE = 'https://texasreligiouslibertywatch.org'
AUTHOR = 'Eric A. Hudson'
PERSON = {'@type': 'Person', '@id': SITE + '/about/#eric-hudson', 'name': AUTHOR, 'url': SITE + '/about/', 'jobTitle': 'Litigation Partner', 'worksFor': {'@type': 'Organization', 'name': 'Arambula Terrazas PLLC', 'url': 'https://www.atlawpllc.com/'}, 'sameAs': ['https://www.linkedin.com/in/txattorney', 'https://www.atlawpllc.com/eric-hudson']}

def shell(home, title, description, path, content, article=None):
    home = re.sub(r'<!-- SEARCH META -->.*?<!-- /SEARCH META -->', '', home, flags=re.S)
    page = home.replace('href="styles.css?', 'href="/styles.css?').replace('href="favicon.svg"', 'href="/favicon.svg"')
    page = re.sub(r'<title>.*?</title>', '<title>' + escape(title) + ' | Texas Religious Liberty Watch</title>', page)
    page = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="' + escape(description, quote=True) + '">', page)
    canonical = SITE + path
    seo = f'<link rel="canonical" href="{canonical}">\n<meta property="og:title" content="{escape(title, quote=True)}">\n<meta property="og:description" content="{escape(description, quote=True)}">\n<meta property="og:url" content="{canonical}">\n<meta property="og:type" content="{"article" if article else "website"}">\n'
    if article:
        seo += f'<meta property="article:published_time" content="{article["date"]}">\n<meta property="article:author" content="{AUTHOR}">\n'
    graph = {'@context':'https://schema.org', '@type':'CollectionPage' if path.startswith(('/news/','/rulings/','/hearings/')) else 'WebPage', 'name': title, 'description':description, 'url':canonical, 'publisher':PERSON}
    seo += '<script type="application/ld+json">' + json.dumps(graph).replace('<', '\\u003c') + '</script>\n'
    page = page.replace('</head>', seo + '</head>')
    if not path.startswith('/news/'):
        page = page.replace('class="nav-item active" aria-current="page" href="/news/"', 'class="nav-item" href="/news/"')
    page = page.replace('<body>', '<body class="news-page">').replace('Skip to legislation', 'Skip to content')
    page = page.replace('href="#tracker"', 'href="/#tracker"')
    page = re.sub(r'<script src="app\.js(?:\?[^"]*)?" defer></script>', '', page)
    page = re.sub(r'<dialog id="bill-dialog".*?</dialog>', '', page, flags=re.S)
    page = re.sub(r'<div id="toast".*?</div>', '', page)
    page = re.sub(r'<span class="nav-count".*?</span>', '', page)
    page = page.replace('class="nav-item active"', 'class="nav-item"')
    if path.startswith('/hearings/'):
        page = page.replace('class="nav-item" href="/hearings/"', 'class="nav-item active" aria-current="page" href="/hearings/"')
    if path.startswith('/rulings/'):
        page = page.replace('class="nav-item" href="/rulings/"', 'class="nav-item active" aria-current="page" href="/rulings/"')
    if path.startswith('/news/'):
        page = page.replace('class="nav-item" href="/news/"', 'class="nav-item active" aria-current="page" href="/news/"')
    page = re.sub(r'<button([^>]*?)data-view="([a-z]+)"([^>]*)>(.*?)</button>',
                  lambda m: f'<a{m[1]}href="/#{m[2]}"{m[3]}>{m[4]}</a>', page, flags=re.S)
    page = page.replace('id="session-phase">90R · Prefiling', 'id="session-phase">90R · 2027')
    main = re.search(r'<main id="main" tabindex="-1">(.*?)</main>', page, flags=re.S)
    if not main:
        raise ValueError('Main website layout was not found.')
    footer = main.group(1)[main.group(1).index('<div class="contact-strip">'):]
    return page[:main.start(1)] + '\n' + content + '\n' + footer + page[main.end(1):]


def central_date(value, full=False):
    moment = datetime.fromisoformat(value).astimezone(ZoneInfo('America/Chicago'))
    return moment.strftime('%b %d, %Y · %I:%M %p %Z' if full else '%b %d, %Y').replace(' 0', ' ')


def news_card(item):
    scopes = ''.join('<span class="news-badge">' + escape(scope) + '</span>' for scope in item['scopes'])
    search = escape(item['title'] + ' ' + item['publisher'], quote=True)
    return f'<article class="news-card" data-news-title="{search}"><div class="news-meta">{scopes}<time datetime="{escape(item["publishedAt"], quote=True)}">{central_date(item["publishedAt"])}</time></div><h2><a href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">{escape(item["title"])}</a></h2><div class="news-source"><span>{escape(item["publisher"])}</span><a href="{escape(item["url"], quote=True)}" target="_blank" rel="noopener noreferrer">Read at source ↗</a></div></article>'


def news_page(home, data, scope=None):
    items = [item for item in data['items'] if not scope or scope in item['scopes']]
    title = f'{scope} religious liberty news' if scope else 'Religious liberty in the news.'
    description = 'Daily headlines on religious freedom, constitutional rights, and church-state issues in Texas and across the United States.'
    path = '/news/' + (scope.lower() + '/' if scope else '')
    checked = central_date(data['updatedAt'], True) if data['updatedAt'] else 'No successful refresh yet'
    tabs = ''.join(f'<a href="/news/{value.lower() + "/" if value else ""}" class="news-tab {"selected" if value == scope else ""}" {"aria-current=\"page\"" if value == scope else ""}>{label}</a>' for value, label in [(None, 'All coverage'), ('Texas', 'Texas'), ('National', 'National')])
    status = '<p class="news-warning">One or more feeds could not be refreshed.  Previously retrieved headlines are retained; see source status below.</p>' if data['status'] != 'ok' else ''
    source_details = ''.join(f'<li><a href="{escape(source["url"], quote=True)}" target="_blank" rel="noopener">{escape(source["label"])} RSS ↗</a><span>{"Checked successfully" if source["status"] == "ok" else "Refresh unavailable; previous data retained"}</span></li>' for source in data['sources'])
    cards = ''.join(news_card(item) for item in items) or '<p class="content-card">No headlines are available in this view yet.</p>'
    content = f'''<section class="news-hero"><div><p class="eyebrow">TEXAS & THE NATION · DAILY NEWS WATCH</p><h1>{escape(title)}</h1><p>{description}</p></div><span class="news-hero-mark" aria-hidden="true">✦</span></section>
<div class="news-freshness"><span class="source-dot"></span><span>Last refreshed {checked}</span><span>·</span><span>Scheduled daily</span></div>{status}<p id="news-stale" class="news-warning" data-updated="{escape(data['updatedAt'] or '', quote=True)}" hidden>This news snapshot is more than 36 hours old.  A refresh is due.</p>
<div class="news-layout"><div><div class="news-tools"><nav aria-label="News coverage" class="news-tabs">{tabs}</nav><form id="news-search-form" class="search simple-search section-search" role="search"><label class="sr-only" for="news-search">Search news</label><input id="news-search" type="search" placeholder="Search headlines or publishers" autocomplete="off"><button type="submit" aria-label="Search news"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"></circle><path d="m16 16 5 5"></path></svg></button></form></div><p id="news-count" class="news-count" aria-live="polite">{len(items)} headlines from the past 30 days</p><div class="news-list">{cards}</div><p id="news-empty" class="content-card" hidden>No headlines match that search.  Try another term or publisher.</p></div>
<aside class="news-aside"><section class="contact-card"><p class="eyebrow">FOLLOW THE TEXAS LEGISLATURE</p><h2>Go beyond the headline.</h2><p>Find the proposals, official bill text, and legislative history behind the debate.</p><a class="button news-gold" href="/#tracker">Open the 90R tracker →</a></section><section class="rail-card"><p class="eyebrow">A WIDER VIEW</p><h3>Religious liberty, across faiths.</h3><p>Coverage of religious exercise, equal treatment, conscience, schools, and governmental action.</p><a class="text-button" href="/religious-liberty/">Explore the issues →</a></section><section class="rail-card"><p class="eyebrow">FROM ERIC A. HUDSON</p><h3>A lawyer’s lens on the law.</h3><p>Litigation partner at Arambula Terrazas PLLC in Austin, Texas.</p><a class="text-button" href="/about/">About Eric →</a><a class="text-button" href="https://www.linkedin.com/in/txattorney" target="_blank" rel="noopener">Follow on LinkedIn ↗</a></section></aside></div>
<section class="news-method content-card"><h2>About this news watch</h2><p>Headlines are collected automatically from Google News RSS searches and link to the original coverage through Google News.  The publisher and reported publication date appear with every headline.  Results may include reporting, opinion, and advocacy releases.  Inclusion does not mean Eric Hudson has reviewed or endorsed a story.</p><p>Texas results match Texas or Fifth Circuit search terms.  National results match United States, federal, or congressional terms, including U.S. policy affecting religious freedom abroad.  Search matches can be imperfect, and this is not an exhaustive news archive.  Article bodies are not copied.  The rolling feed covers the past 30 days.</p><details><summary>Feed sources & update status</summary><ul>{source_details}</ul><p>News checks run daily, including weekends, and continue after the 90R legislative monitoring window ends.  A failed feed retains its previous available records.</p></details></section><script src="/news.js?v=section-search-20261112" defer></script>'''
    return path, shell(home, title.rstrip('.'), description, path, content)


def build(root=ROOT):
    home_path = root / 'dist/index.html'
    home = home_path.read_text()
    data = json.loads((root / 'dist/data/news.json').read_text())
    pages = dict(news_page(home, data, scope) for scope in (None, 'Texas', 'National'))
    if (root / 'dist/90r/manifest.webmanifest').exists():
        pages.update(app_pages(home, shell))
    hearing_path = root / 'dist/data/hearings.json'
    if hearing_path.exists():
        hearings = json.loads(hearing_path.read_text())
        pages['/hearings/'] = hearing_page(home, hearings, shell)
    ruling_path = root / 'dist/data/rulings.json'
    if ruling_path.exists():
        rulings = json.loads(ruling_path.read_text())
        pages['/rulings/'] = ruling_page(home, rulings, shell)
    resource_content = '''<section class="news-hero"><div><p class="eyebrow">THE ISSUES & THE SOURCES</p><h1>Religious liberty in Texas<br>and the United States.</h1><p>A starting point for following religious freedom, constitutional rights, legislation, and the public debate.</p></div></section><div class="resource-layout"><article class="content-card resource-copy"><h2>What this site follows</h2><p>Religious liberty questions reach beyond worship services.  They arise in education, public benefits, professional licensing, employment, land use, and the treatment of religious institutions.  Texas Religious Liberty Watch brings together official legislative records and daily news coverage to make those developments easier to follow.</p><p>The focus extends across faiths.  A proposed law affecting one religious community can raise questions relevant to others.  The tracker identifies measures for closer examination; inclusion does not express support or opposition.</p><h2>Texas legislation and state law</h2><p>The bill tracker covers the 90th Regular Session of the Texas Legislature.  It includes potentially relevant bills and proposed constitutional amendments, links to official text and history, and a personal watchlist.  A filed proposal is not an enacted law.  Review labels distinguish screened captions from reviewed text.</p><p>For the underlying Texas legal sources, start with <a href="https://tcss.legis.texas.gov/resources/CN/htm/CN.1.htm#1.6" target="_blank" rel="noopener">Texas Constitution article I, section 6</a>, and the <a href="https://tcss.legis.texas.gov/resources/CP/htm/CP.110.htm" target="_blank" rel="noopener">Texas Religious Freedom Restoration Act, Civil Practice and Remedies Code chapter 110</a>.  The official text is the source to consult when evaluating a particular provision.</p><h2>National developments</h2><p>The First Amendment addresses both the free exercise of religion and governmental establishment of religion.  Federal litigation and national policy debates can affect how religious liberty questions arise in Texas.  The <a href="https://www.archives.gov/founding-docs/bill-of-rights-transcript" target="_blank" rel="noopener">National Archives’ Bill of Rights transcript</a> provides the constitutional text.</p><p>Our news watch gathers Texas and national headlines with publisher attribution and links to the coverage.  Reporting, opinion, advocacy, proposed legislation, and court decisions are different kinds of sources.  Read the underlying text and relevant decisions before drawing conclusions about legal effect.</p><h2>Follow an issue from source to discussion</h2><ol><li>Find a proposal in the bill tracker and read its official text.</li><li>Save it to your browser’s watchlist and add private working notes.</li><li>Use the news watch to follow related reporting and public debate.</li><li>Check the linked official record for current legislative action.</li></ol></article><aside class="news-aside"><section class="contact-card"><p class="eyebrow">EXPLORE THE SITE</p><h2>Keep the sources close.</h2><a class="text-button light" href="/#tracker">Texas 90R bill tracker →</a><a class="text-button light" href="/news/texas/">Texas religious liberty news →</a><a class="text-button light" href="/news/national/">National religious liberty news →</a><a class="text-button light" href="/about/">About Eric Hudson →</a></section></aside></div>'''
    pages['/religious-liberty/'] = shell(home, 'Religious liberty in Texas and the United States', 'Follow religious liberty in Texas and nationally through official legislative sources, a 90R bill tracker, and daily religious freedom news.', '/religious-liberty/', resource_content)
    app = (root / 'dist/app.js').read_text()
    biography = re.search(r'function about\(\) \{\s+return `(.*?)`;\s*\}', app, re.S)
    if not biography:
        raise ValueError('The existing verified biography was not found.')
    about = '<section class="intro"><div><p class="eyebrow">ABOUT THE EDITOR</p><h1>Eric A. Hudson</h1><p>Commercial trial lawyer.  Constitutional advocate.</p></div></section><div style="height:24px"></div>' + biography.group(1)
    pages['/about/'] = shell(home, 'Eric A. Hudson, Texas litigation attorney', 'Eric A. Hudson is an Austin litigation partner at Arambula Terrazas PLLC and the creator of Texas Religious Liberty Watch.', '/about/', about)
    person_markup = {'@context':'https://schema.org', '@type':'ProfilePage', 'mainEntity':PERSON}
    pages['/about/'] = pages['/about/'].replace('</head>', '<script type="application/ld+json">' + json.dumps(person_markup) + '</script></head>')
    for path, html in pages.items():
        destination = root / 'dist' / path.strip('/') / 'index.html'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html)
    home = re.sub(r'<!-- SEARCH META -->.*?<!-- /SEARCH META -->\s*', '', home, flags=re.S)
    graph = {'@context':'https://schema.org', '@type':'WebSite', 'name':'Texas Religious Liberty Watch', 'url':SITE + '/', 'description':'Texas 90R religious liberty bill tracking and daily Texas and national religious freedom news.', 'inLanguage':'en-US', 'publisher':PERSON}
    search_meta = '<!-- SEARCH META -->\n<link rel="canonical" href="' + SITE + '/">\n<meta name="robots" content="index,follow,max-image-preview:large">\n<meta property="og:title" content="Texas Religious Liberty Watch | Bills & Daily News">\n<meta property="og:description" content="Religious liberty in Texas: a 90R bill tracker, daily state and national news, and official sources.">\n<meta property="og:url" content="' + SITE + '/">\n<meta property="og:type" content="website">\n<script type="application/ld+json">' + json.dumps(graph) + '</script>\n<!-- /SEARCH META -->\n'
    home = home.replace('</head>', search_meta + '</head>')
    home_path.write_text(home)
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    sitemap = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for path in ['/', *pages]:
        url = ET.SubElement(sitemap, 'url')
        ET.SubElement(url, 'loc').text = SITE + path
        if path.startswith('/news/') and data['updatedAt']:
            ET.SubElement(url, 'lastmod').text = data['updatedAt']
    ET.ElementTree(sitemap).write(root / 'dist/sitemap.xml', encoding='utf-8', xml_declaration=True)
    (root / 'dist/robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /downloads/\n\nUser-agent: OAI-SearchBot\nAllow: /\nDisallow: /downloads/\n\nSitemap: ' + SITE + '/sitemap.xml\n')
    print(f'Built {len(pages)} crawlable pages, metadata, robots.txt, and sitemap.xml.')


if __name__ == '__main__':
    build()



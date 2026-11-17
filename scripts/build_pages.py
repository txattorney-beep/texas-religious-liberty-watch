#!/usr/bin/env python3
"""Build crawlable news, profile, and topic pages from the published snapshot."""
from datetime import datetime
from html import escape
import json
from pathlib import Path
import re
import shutil
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo
try:
    from .wire_pages import wire_content
    from .guest_pages import load_guests, guest_strip, guest_pages
    from .hearing_pages import hearing_page
    from .ruling_pages import ruling_page
    from .app_pages import app_pages
except ImportError:
    from wire_pages import wire_content
    from guest_pages import load_guests, guest_strip, guest_pages
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
    page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + escape(title) + ' | Texas Religious Liberty Watch</title>', page)
    page = re.sub(r'<meta name="description"[^>]*>', lambda _: '<meta name="description" content="' + escape(description, quote=True) + '">', page)
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


def news_page(home, data, scope=None, guests=''):
    title = f'{scope} religious liberty news' if scope else 'Religious liberty in the news'
    description = 'Daily religious liberty headlines from Texas, the Fifth Circuit, and the nation.'
    path = '/news/' + (scope.lower() + '/' if scope else '')
    return path, shell(home, title, description, path, wire_content(data, guests, scope))


def build(root=ROOT):
    home_path = root / 'dist/index.html'
    home = home_path.read_text()
    home = re.sub(r'<!-- WIRE FRONT START -->.*?<!-- WIRE FRONT END -->', '', home, flags=re.S)
    home = home.replace('<div id="legislative-desk" hidden>', '').replace('<!-- LEGISLATIVE DESK END --></div>', '')
    home = re.sub(r'<script src="/frontpage.js[^"]*" defer></script>', '', home)
    home = re.sub(r'<link rel="stylesheet" href="/wire.css[^"]*">', '', home)
    home = home.replace('</head>', '<link rel="stylesheet" href="/wire.css?v=20261117"></head>')
    home = home.replace('href="#tracker" class="brand"', 'href="/" class="brand"')
    if 'href="/voices/"' not in home:
        home = home.replace('<nav aria-label="Main navigation">', '<nav aria-label="Main navigation"><a class="nav-item" href="/">Front page</a><a class="nav-item" href="/voices/">Guest Voices</a>')
    home = home.replace('> Sponsor</a>', '> Advertising</a>').replace('>Sponsorship inquiries</a>', '>Advertising inquiries</a>')
    guests = load_guests(root)

    if 'href="/sponsor/"' not in home:
        menu_end = home.index('</nav>', home.index('<nav aria-label="Main navigation">'))
        home = home[:menu_end] + '  <a class="nav-item" href="/sponsor/"><span aria-hidden="true">10</span> Sponsor</a>\n  ' + home[menu_end:]
        home = home.replace('LinkedIn →</a></div></div>', 'LinkedIn →</a><a href="/sponsor/">Sponsorship inquiries</a></div></div>', 1)
    data = json.loads((root / 'dist/data/news.json').read_text())
    pages = dict(news_page(home, data, scope, guest_strip(guests)) for scope in (None, 'Texas', 'National'))
    pages.update(guest_pages(home, shell, guests))
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
    sponsorship = (
        '<section class="intro"><div><h1>Advertise on Texas Religious Liberty Watch</h1>'
        '<p>Reach readers who follow religious liberty legislation, court rulings, and news.</p></div></section>'
        '<section class="content-card"><p>Contact Eric Hudson for advertising details, available placements, and rates.</p>'
        '<p><a class="button primary" href="mailto:txattorney@gmail.com?subject=Texas%20Religious%20Liberty%20Watch%20sponsorship%20inquiry">'
        'Email Eric about advertising</a></p></section>'
    )
    sponsor_page = shell(home, 'Advertising', 'Inquire about advertising opportunities on Texas Religious Liberty Watch.', '/sponsor/', sponsorship)
    pages['/sponsor/'] = re.sub(r'<a href="mailto:[^"]+">[^<]*</a>(?=<a href="https://www.linkedin.com/)', '', sponsor_page).replace('>ehudson@atlawpllc.com<', '>Email about copyright<')
    voices_dir = root / 'dist/voices'
    if voices_dir.exists():
        shutil.rmtree(voices_dir)  # Rebuilt from authoritative approved manuscripts.
    for path, html in pages.items():
        destination = root / 'dist' / path.strip('/') / 'index.html'
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(html)
    home = re.sub(r'<!-- SEARCH META -->.*?<!-- /SEARCH META -->\s*', '', home, flags=re.S)
    graph = {'@context':'https://schema.org', '@type':'WebSite', 'name':'Texas Religious Liberty Watch', 'url':SITE + '/', 'description':'Texas 90R religious liberty bill tracking and daily Texas and national religious freedom news.', 'inLanguage':'en-US', 'publisher':PERSON}
    search_meta = '<!-- SEARCH META -->\n<link rel="canonical" href="' + SITE + '/">\n<meta name="robots" content="index,follow,max-image-preview:large">\n<meta property="og:title" content="Texas Religious Liberty Watch | Bills & Daily News">\n<meta property="og:description" content="Religious liberty in Texas: a 90R bill tracker, daily state and national news, and official sources.">\n<meta property="og:url" content="' + SITE + '/">\n<meta property="og:type" content="website">\n<script type="application/ld+json">' + json.dumps(graph) + '</script>\n<!-- /SEARCH META -->\n'
    home = re.sub(
        r'<title>.*?</title>',
        '<title>Texas Religious Liberty Watch | 90R Bill Tracker and News</title>',
        home,
    )
    home = home.replace('</head>', search_meta + '</head>')
    front = '<!-- WIRE FRONT START --><div id="wire-front">' + wire_content(data, guest_strip(guests)) + '</div><!-- WIRE FRONT END -->'
    home = home.replace('<main id="main" tabindex="-1">', '<main id="main" tabindex="-1">' + front + '<div id="legislative-desk" hidden>')
    home = home.replace('<div class="contact-strip">', '<!-- LEGISLATIVE DESK END --></div><div class="contact-strip">', 1)
    home = home.replace('</head>', '<script src="/frontpage.js?v=20261117" defer></script></head>')
    home_path.write_text(home)
    ET.register_namespace('', 'http://www.sitemaps.org/schemas/sitemap/0.9')
    sitemap = ET.Element('{http://www.sitemaps.org/schemas/sitemap/0.9}urlset')
    for path in ['/', *pages]:
        if path == '/90r/':
            continue  # The installable tracker uses the homepage as its canonical URL.
        url = ET.SubElement(sitemap, 'url')
        ET.SubElement(url, 'loc').text = SITE + path
        if path.startswith('/news/') and data['updatedAt']:
            ET.SubElement(url, 'lastmod').text = data['updatedAt']
    ET.ElementTree(sitemap).write(root / 'dist/sitemap.xml', encoding='utf-8', xml_declaration=True)
    (root / 'dist/robots.txt').write_text('User-agent: *\nAllow: /\nDisallow: /downloads/\n\nUser-agent: OAI-SearchBot\nAllow: /\nDisallow: /downloads/\n\nSitemap: ' + SITE + '/sitemap.xml\n')
    # Idempotent: generated pages inherit the homepage head before this pass.
    for document in (root / 'dist').rglob('*.html'):
        if 'downloads' in document.parts:
            continue
        content = document.read_text()
        content = re.sub(r'<link rel="stylesheet" href="/share\.css(?:\?[^"]*)?">', '', content)
        content = re.sub(r'<script src="/share\.js(?:\?[^"]*)?" defer></script>', '', content)
        content = content.replace('</head>', '<link rel="stylesheet" href="/share.css?v=20261115-compact"><script src="/share.js?v=20261115-compact" defer></script></head>')
        document.write_text(content)
    print(f'Built {len(pages)} crawlable pages, metadata, robots.txt, and sitemap.xml.')


if __name__ == '__main__':
    build()




def build_search_pages():
    from html.parser import HTMLParser
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(); self.parts = []
        def handle_data(self, text):
            self.parts.append(text)
    pages = []
    for path, title in [('about/', 'About Eric A. Hudson'), ('religious-liberty/', 'Religious liberty: issues and sources'), ('90r/install/', 'Install the 90R tracker')]:
        html = (ROOT / 'dist' / path / 'index.html').read_text()
        content = re.search(r'<main[^>]*>(.*?)<div class="contact-strip">', html, re.S).group(1)
        parser = Text(); parser.feed(content)
        pages.append({'title': title, 'url': '/' + path, 'text': ' '.join(' '.join(parser.parts).split())})
    for article in load_guests(ROOT):
        pages.append({'title': article['title'], 'url': '/voices/' + article['slug'] + '/', 'text': article['author'] + ' ' + article['kind'] + ' ' + article['dek'] + ' ' + ' '.join(article['body'])})
    (ROOT / 'dist/data/pages.json').write_text(json.dumps({'pages': pages}, ensure_ascii=False) + '\n')

if __name__ == '__main__':
    build_search_pages()

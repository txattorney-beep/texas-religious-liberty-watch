"""Validated, hand-approved original contributions, separate from automated news."""
from datetime import date
from html import escape
import json
from pathlib import Path
import re

SITE = 'https://texasreligiouslibertywatch.org'
KINDS = {'Opinion', 'Reporting', 'Analysis'}


def load_guests(root):
    """Load approved articles only; fail the build on malformed editorial data."""
    path = Path(root) / 'content/guests.json'
    if not path.exists():
        return []
    rows = json.loads(path.read_text())
    if not isinstance(rows, list):
        raise ValueError('Guest contributions must be a JSON array.')
    seen = set()
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError('Each guest contribution must be an object.')
        if type(item.get('published')) is not bool:
            raise ValueError('Guest published must be an explicit boolean.')
        slug = item.get('slug', '')
        if not isinstance(slug, str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or len(slug) > 120:
            raise ValueError('Guest slug must contain lowercase words separated by hyphens.')
        if slug in seen:
            raise ValueError('Duplicate guest slug: ' + slug)
        seen.add(slug)
        for key in ('title', 'author', 'date', 'kind', 'dek', 'authorBio'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'Guest {slug}: {key} must be nonempty text.')
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', item['date']):
            raise ValueError('Guest date must use YYYY-MM-DD.')
        date.fromisoformat(item['date'])
        if item['kind'] not in KINDS:
            raise ValueError('Guest kind must be Opinion, Reporting, or Analysis.')
        if not isinstance(item.get('body'), list) or not item['body'] or any(not isinstance(p, str) or not p.strip() for p in item['body']):
            raise ValueError('Guest body must be a nonempty list of text paragraphs.')
        if 'featured' in item and type(item['featured']) is not bool:
            raise ValueError('Guest featured must be a boolean.')
    # A deliberate featured flag controls the leading slot; otherwise newest first.
    return sorted((x for x in rows if x['published']), key=lambda x: (x.get('featured', False), x['date']), reverse=True)


def article_url(item):
    return '/voices/' + item['slug'] + '/'


def card(item, featured=False):
    return ('<article class="guest-card' + (' guest-featured' if featured else '') + '">'
            '<p class="guest-kind">' + escape(item['kind']) + '</p>'
            '<h3><a href="' + article_url(item) + '">' + escape(item['title']) + '</a></h3>'
            '<p class="guest-byline">By ' + escape(item['author']) + ' · <time datetime="' + escape(item['date'], quote=True) + '">' + escape(item['date']) + '</time></p>'
            + ('<p class="guest-dek">' + escape(item['dek']) + '</p>' if featured else '') + '</article>')


def guest_strip(articles):
    if not articles:
        return ''
    return ('<section class="guest-voices" aria-labelledby="guest-heading"><div class="guest-heading">'
            '<h2 id="guest-heading">Guest Voices</h2><a href="/voices/">All contributions →</a></div>'
            '<div class="guest-grid">' + card(articles[0], True) + '<div class="guest-secondary">'
            + ''.join(card(a) for a in articles[1:3]) + '</div></div></section>')


def guest_pages(home, shell, articles):
    """Return /voices/ archive and individual pages; caller adds them to the sitemap."""
    intro = '<section class="voices-intro"><p class="eyebrow">ORIGINAL CONTRIBUTIONS</p><h1>Guest Voices</h1><p>Reporting, analysis, and opinion from contributing writers.</p></section>'
    entries = ''.join(card(a, True) for a in articles)
    content = intro + ('<div class="guest-archive">' + entries + '</div>' if articles else '<p class="guest-empty">Guest contributions will appear here when published.</p>')
    pages = {'/voices/': shell(home, 'Guest Voices', 'Original guest reporting, analysis, and opinion on religious liberty.', '/voices/', content)}
    for item in articles:
        path = article_url(item)
        content = ('<article class="guest-article"><header><a class="guest-back" href="/voices/">← Guest Voices</a>'
                   '<p class="guest-kind">' + escape(item['kind']) + '</p><h1>' + escape(item['title']) + '</h1>'
                   '<p class="guest-dek">' + escape(item['dek']) + '</p><p class="guest-byline">By ' + escape(item['author'])
                   + ' · <time datetime="' + escape(item['date'], quote=True) + '">' + escape(item['date']) + '</time></p></header>'
                   '<div class="guest-body">' + ''.join('<p>' + escape(p) + '</p>' for p in item['body']) + '</div>'
                   '<footer class="guest-author"><h2>About the author</h2><p>' + escape(item['authorBio']) + '</p>'
                   '<p class="guest-disclaimer">Guest contributions reflect their authors’ views and are not legal advice.</p></footer></article>')
        page = shell(home, item['title'], item['dek'], path, content)
        page = re.sub(r'<meta name="author"[^>]*>', lambda _: '<meta name="author" content="' + escape(item['author'], quote=True) + '">', page)
        page = page.replace('<meta property="og:type" content="website">', '<meta property="og:type" content="article">')
        # Replace generic shell metadata rather than adding a competing author or graph.
        page = re.sub(r'<script type="application/ld\+json">.*?</script>', '', page, flags=re.S)
        schema = {'@context': 'https://schema.org', '@type': 'NewsArticle' if item['kind'] == 'Reporting' else 'Article',
                  'headline': item['title'], 'description': item['dek'], 'datePublished': item['date'],
                  'author': {'@type': 'Person', 'name': item['author']}, 'articleSection': item['kind'],
                  'publisher': {'@type': 'Organization', 'name': 'Texas Religious Liberty Watch', 'url': SITE + '/'},
                  'mainEntityOfPage': SITE + path, 'url': SITE + path}
        meta = '<meta property="article:author" content="' + escape(item['author'], quote=True) + '"><meta property="article:published_time" content="' + item['date'] + '">'
        meta += '<script type="application/ld+json">' + json.dumps(schema, ensure_ascii=False).replace('<', '\\u003c') + '</script>'
        pages[path] = page.replace('</head>', meta + '</head>')
    return pages

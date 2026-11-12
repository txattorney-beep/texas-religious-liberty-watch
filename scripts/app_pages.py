"""Build the installable 90R tracker separately from the wider Liberty Watch site."""
import re

SITE = 'https://texasreligiouslibertywatch.org'


def app_home(home):
    page = re.sub(r'<!-- SEARCH META -->.*?<!-- /SEARCH META -->', '', home, flags=re.S)
    page = re.sub(r'<a class="nav-item" href="/(?:news|rulings|hearings)/">.*?</a>', '', page)
    page = re.sub(r'<section class="discovery-panel">.*?</section>', '', page, flags=re.S)
    page = page.replace('<a href="/news/">News watch →</a>', '<span>90R tracker app</span>')
    page = page.replace('<body>', '<body data-app="90r">')
    page = page.replace('href="styles.css?', 'href="/styles.css?').replace('href="favicon.svg"','href="/favicon.svg"')
    page = re.sub(r'<title>.*?</title>', '<title>Texas 90R Liberty Tracker</title>', page)
    page = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="The Texas 90R religious liberty bill tracker and personal watchlists, ready for your iPhone or Android home screen.">', page)
    head = '''<link rel="manifest" href="/90r/manifest.webmanifest">
<link rel="apple-touch-icon" sizes="180x180" href="/90r/icons/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="90R Watch">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<script src="/90r/pwa.js" defer></script>
'''
    page = page.replace('</head>', head+'</head>')
    banner = '<div id="app-connection" class="app-status" role="status" hidden><span>Connection unavailable.  Showing saved content, which may be out of date.</span><button type="button" data-app-refresh>Refresh</button></div><div id="app-update" class="app-status" role="status" hidden><span>A new app version is ready.</span><button type="button" id="app-update-button">Update app</button></div>'
    page = page.replace('<main id="main" tabindex="-1">', '<main id="main" tabindex="-1">'+banner)
    return page


def app_pages(home, shell):
    base = app_home(home)
    app = base.replace('<script src="app.js', '<script src="/app.js')
    app = app.replace('</head>', '<link rel="canonical" href="'+SITE+'/90r/">\n</head>')
    install_content = '''<section class="news-hero install-hero"><div><p class="eyebrow">THE 90R TRACKER · IPHONE & ANDROID</p><h1>The 90th.<br>In your pocket.</h1><p>Add the Texas 90R Liberty Tracker to your home screen.  Follow bills and keep a personal watchlist with one tap.</p></div><img class="install-icon" src="/90r/icons/icon-192.png" alt="90R Watch app icon" width="112" height="112"></section>
<section class="install-action content-card"><div><h2>Your legislative desk, on your phone.</h2><p>The app contains the 90R bill tracker and your personal watchlist.  News and court-ruling sections remain on the full website.</p><p class="install-status" id="install-status" role="status">Choose your phone below to add the app.  No account or app-store purchase is needed.</p><div class="install-buttons"><button type="button" class="button primary" data-install-button hidden>Install 90R app ↓</button><a class="button primary" href="/90r/">Open 90R tracker →</a><a class="button" href="#iphone">iPhone instructions</a><a class="button" href="#android">Android instructions</a></div></div><span class="install-tag">90R<br><small>2027 SESSION</small></span></section>
<div class="install-grid"><section class="content-card install-steps" id="iphone"><p class="eyebrow">APPLE IPHONE & IPAD</p><h2>Add it with Safari.</h2><ol><li>Open this page in <strong>Safari</strong>.</li><li>Tap <strong>Share</strong>.  On some versions, open the More menu first.</li><li>Choose <strong>Add to Home Screen</strong>.  Scroll through the actions if needed.</li><li>If shown, turn on <strong>Open as Web App</strong>, then tap <strong>Add</strong>.</li></ol><p>Look for the maroon-and-gold <strong>90R Watch</strong> icon on your home screen.</p></section><section class="content-card install-steps" id="android"><p class="eyebrow">ANDROID</p><h2>Add it with Chrome.</h2><ol><li>Open this page in <strong>Chrome</strong>.</li><li>If the <strong>Install 90R app</strong> button appears above, tap it and confirm.</li><li>In Chrome, you can also open the menu and choose <strong>Install app</strong> or <strong>Add to Home screen</strong>.</li></ol><p>Menu wording varies by browser version.  Open the link in your browser if you arrived through LinkedIn, Facebook, or another app.</p></section></div>
<section class="content-card install-details"><h2>The same tracker.  A simpler way to open it.</h2><div class="install-grid"><div><h3>Daily published updates</h3><p>The website’s daily bill checks feed this app.  Connect to the internet and refresh to load the latest published snapshot.  The app does not need a separate subscription.</p><h3>Saved content when offline</h3><p>After an online visit finishes preparing the app, the saved tracker can open without a connection.  A notice identifies saved content.  Check its snapshot date; official bill records and hearing links need an internet connection.</p></div><div><h3>Your watchlist stays yours</h3><p>Saved bills and notes stay on your device.  Browser and installed-app storage may differ, and they do not sync across phones.  Use <strong>Sources → Download personal backup</strong>, then restore that backup in the app if you need to transfer them.</p><h3>Use the mobile website anytime</h3><p>Installation is optional.  The <a href="/" target="_blank" rel="noopener">full mobile website ↗</a> includes news, hearings, and court rulings alongside the tracker.  This app stays focused on the 90th Regular Session.</p></div></div><p class="install-footnote">This is an installable web app, distributed directly from this website.  No Apple App Store, Google Play, or Galaxy Store listing is required.  It does not send push notifications.</p></section>'''
    install = shell(base, 'Install the Texas 90R tracker on iPhone or Android', 'Add the free Texas 90R religious liberty bill tracker and personal watchlist to your iPhone or Android home screen.', '/90r/install/', install_content)
    banners = base.split('<main id="main" tabindex="-1">',1)[1].split('<section class="intro">',1)[0]
    install = install.replace('<main id="main" tabindex="-1">','<main id="main" tabindex="-1">'+banners)
    install = install.replace('<body data-app="90r">','<body data-app="90r" class="news-page">')
    install = install.replace('class="nav-item" href="/90r/install/"', 'class="nav-item active" aria-current="page" href="/90r/install/"')
    # shell() roots SPA links to /; within the app keep those views under /90r/.
    install = install.replace('href="/#', 'href="/90r/#')
    return {'/90r/':app, '/90r/install/':install}

# Texas Religious Liberty Watch · 90R

A portable static website for religious-liberty bill monitoring across faiths in the 90th Texas Legislature. No paid API, database, or JavaScript build tooling is required.

**Live website:** [Texas Religious Liberty Watch](https://texasreligiouslibertywatch.org/). [90R phone app](https://texasreligiouslibertywatch.org/90r/). [Sitemap](https://texasreligiouslibertywatch.org/sitemap.xml).

## Search notifications

After each successful deployment, `scripts/submit_indexnow.py` notifies IndexNow about newly published or changed sitemap pages. Bing and other participating search engines share these notifications. Google Search Console verification, sitemap submission, and URL Inspection remain separate account steps; IndexNow does not complete them or guarantee indexing.

The script verifies the published ownership file before submitting, includes bill data when checking the JavaScript tracker for changes, and stores the HTTP receipt and fingerprints in `search/indexnow-state.json` only after HTTP 200 or 202. HTTP 202 means key validation is pending. Failed requests do not prevent site deployment and remain eligible for the next publication. Use `python scripts/submit_indexnow.py --dry-run` to inspect pending URLs without sending them.

For a copied deployment, replace the host and key file in `search/indexnow.json`, generate a new 32-character hexadecimal key, and publish the matching root text file on your own domain before enabling notifications. Remove any copied submission-state file. The key is for IndexNow ownership verification only; it grants no access to GitHub, Cloudflare, or the search-console accounts.

The initial November 11, 2026 snapshot screens 1,378 official captions, retains 30 potentially relevant measures, and includes nine summaries of identified introduced bill texts. This is a caption-based review queue, not a complete full-text census. All bill records link to Texas Legislature Online.

## Daily religious liberty news

The public news watch is at https://texasreligiouslibertywatch.org/news/, with separate Texas and national views. Headlines are collected daily from Google News RSS searches, attributed to their publishers, deduplicated, and linked through to the source. Article bodies and automated legal summaries are not published. Coverage includes reporting, opinion, and advocacy releases. Search matches are provisional and not endorsements.

The same active GitHub Actions workflow refreshes news every day at 13:37 UTC, including weekends. News continues after May 31, 2027; only the 90R bill-fetching window ends then. Failed feeds retain available prior records and show their status. The page warns when the snapshot is older than 36 hours. A bill-source outage no longer prevents news publication.

To change the news searches, edit `FEEDS` and `TERMS` in `scripts/sync_news.py`. Manual refresh: Actions → Publish and update 90R tracker → Run workflow. No news API key or paid service is required. This uses public RSS endpoints, whose availability can change.

`python scripts/sync_news.py` refreshes the snapshot. `python scripts/build_pages.py` generates crawlable news pages, a static author profile, a religious-liberty resource page, canonical metadata, structured data, robots.txt, and sitemap.xml. Source records are in `dist/data/news.json`. There is no personal article-publishing section at present.

Search discovery status (November 11, 2026): Google Search Console domain ownership is verified through the Cloudflare DNS TXT record. Google has successfully read `https://texasreligiouslibertywatch.org/sitemap.xml` and discovered all 10 submitted pages. Preserve the verification TXT record. Bing Webmaster Tools account verification remains pending. Sitemap processing is distinct from page indexing; account-side URL Inspection requests are separate from deployment. Google and AI search inclusion and rankings are not guaranteed. OAI-SearchBot and standard search crawlers are permitted. No special AI markup or keyword stuffing is used.

The site uses Loyola University New Orleans' published maroon (#660000) and gold (#F4AA00) palette. It does not use the university's logo or claim university affiliation.

## Hearings and notices

`/hearings/` matches official House, Senate, and joint-committee 90R notices to tracked bills. It preserves conditional meeting times, links HTML and PDF notices, records detected revisions, marks explicit cancellations and agenda removals, and retains history. Disappearance from an upcoming list never establishes cancellation. Search by bill or committee, filter to your browser watchlist, and export CSV. Bill details link directly to a bill-filtered hearing view.

The daily workflow runs `python scripts/sync_hearings.py`. It checks official upcoming-meeting RSS and HTML lists and rechecks previously matched current notices. Failures retain earlier details and show warnings. Only committee notices are ingested; floor calendars, witness lists, minutes, and testimony deadlines are not separately tracked. This is daily monitoring, not a real-time alert service. No matching 90R notices were available at initial setup on November 11, 2026.

## Court rulings

`/rulings/` contains a source-checked initial collection covering May 15 through November 11, 2026, and a rolling 180-day view. The scope is the U.S. Supreme Court, Fifth Circuit, federal district courts in Texas/Louisiana/Mississippi, and those states' indexed state-court opinions. Each checked case includes a blurb, date, docket, court, issue tags, posture, and source link. Procedural orders and related civil-remedies cases are labeled. This is a researched starting collection, not an exhaustive docket inventory or citator.

`python scripts/sync_rulings.py` checks seven public CourtListener opinion feeds daily, without a key or paid service. New keyword matches appear automatically in a separate **Opinion matches** view with short source excerpts. They are not automatically represented as holdings, verified religious-liberty cases, or Eric Hudson's reviewed analysis. Feed limits and missing trial/emergency orders affect coverage. A successful feed check does not establish that every prior case remains good law. Failed feeds preserve discovered records within the rolling window. News, hearings, and court feeds continue after the bill-refresh window ends.

To review a new case, read the actual opinion and relevant later orders, then add it to `court_editorial.json` using an existing entry's fields. Include the exact opinion date, court/group/state, docket, source URL, summary, posture note, topics, and `checkedAt`. `matchNames` contains exact alternative feed captions for the same ruling/date, so a reviewed entry replaces its feed match. Add irrelevant search-result URLs to `excludedUrls`. These editorial records remain in source control as the public rolling view advances. Re-run the court updater and page builder. Do not infer a holding from a search excerpt. Review later appeals or stays separately; the aggregator is not an automated citator.

## Publish for free on GitHub Pages

1. Create a **public** repository in a free GitHub account.
2. Unzip the starter and upload its contents at the repository root. Preserve the `.github/workflows/publish.yml` file. A browser upload may hide dot-folders; the Git method below avoids that problem.
3. Open **Settings → Pages**. Select **GitHub Actions** under Build and deployment.
4. If organization or account policy restricts writes, open **Settings → Actions → General → Workflow permissions**, select read/write permissions, and save. Branch protections may require adjustment or a pull-request update workflow.
5. Open **Actions → Publish and update 90R tracker → Run workflow**. The successful deployment provides the `https://YOUR-ACCOUNT.github.io/YOUR-REPOSITORY/` address.
6. Confirm the live snapshot date and the workflow result in Actions. Scheduled checks run at **13:37 UTC daily**, equivalent to 7:37 a.m. CST / 8:37 a.m. CDT. Automated bill checks stop after May 31, 2027; news, court, and hearing checks continue. The site remains available afterward.

Git alternative, from the extracted folder after creating an empty repository:

```bash
git init
git add .
git commit -m "Create 90R religious liberty tracker"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

Authenticate through GitHub's supported browser/credential flow. Do not put tokens in the website or data files.

GitHub Pages and standard Actions runners are free for public repositories. Scheduled workflows may be delayed. GitHub can disable a scheduled workflow after 60 days without repository activity; inspect Actions if data stops updating. The site flags a snapshot older than 36 hours. A free host-provided domain avoids domain-registration costs.

Provider documentation:
- https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site
- https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule

## Cloudflare Pages alternative

Connect the same GitHub repository to Cloudflare Pages, select no framework, set build command `python3 scripts/package_starter.py` (or `exit 0` if you do not need the downloadable starter), and output directory `dist`. Cloudflare provides a free `pages.dev` address.

For this route, remove the `deploy` job and both the `actions/configure-pages` and `actions/upload-pages-artifact` steps from `.github/workflows/publish.yml`. Keep the `prepare` job and its updater, validation, and commit steps. The commit triggers a Cloudflare rebuild. A manual static upload alone does not activate the update workflow.

Free Cloudflare Pages currently permits 500 builds per month. Daily builds fit comfortably within that limit. Static asset requests are free; this project uses no Pages Functions. A custom domain is optional and separate.
- https://developers.cloudflare.com/pages/platform/limits/
- https://developers.cloudflare.com/pages/functions/pricing/
- https://developers.cloudflare.com/pages/framework-guides/deploy-anything/

## Update and review

Run manually with Python 3.10+ and curl installed:

```bash
python scripts/sync_tlo.py --text
python -m unittest discover -s tests
python scripts/sync_news.py
python scripts/sync_hearings.py
python scripts/sync_rulings.py
python scripts/build_pages.py
python scripts/package_starter.py
```

The updater reads both 90R filed-legislation reports. It validates the session and expected record counts, screens captions using topic rules, retains previously tracked measures, and refreshes the latest available HTML text for tracked measures. A missing/incomplete report fails the update and preserves the previous snapshot. Individual text-fetch failures are recorded per bill. Histories, amendments, votes, and fiscal notes remain available through official links. Committee hearings and notices are separately monitored as described above.

`dist/data/bills.json` is generated. Edit `editorial.json` to add a reviewed summary, include a measure the rules missed, or exclude an irrelevant broad match. Add `"include": true` for a manually chosen bill or `"exclude": true` to remove a match. Keep every factual summary tied to a specific official text URL, section references, review date, and SHA-256 of the normalized text. The updater removes summaries when the latest text differs from the reviewed URL/hash, including changes made under the same URL. Do not mark a caption-only match as text reviewed.

Example review fields (use real reviewed content and the actual hash):

```json
{
  "HB236": {
    "include": true,
    "title": "Muslim Heritage Day",
    "topics": ["Faith communities"],
    "summary": "Your source-checked summary.",
    "relevance": "Your separately identified relevance assessment.",
    "sections": "Section 1",
    "reviewState": "Text reviewed",
    "reviewVersion": "Introduced version",
    "reviewedAt": "2026-11-11T18:00:00+00:00",
    "reviewedTextUrl": "https://capitol.texas.gov/tlodocs/90R/billtext/html/HB00236I.htm",
    "reviewedTextHash": "REPLACE_WITH_ACTUAL_HASH"
  }
}
```

To compute a review hash, use `hashlib.sha256(clean(fetch(url)).encode()).hexdigest()` from `scripts/sync_tlo.py`. Fetch and read the text before recording a review. The keyword screen is intentionally broad and can miss substantive provisions absent from captions. New unreviewed measures carry official captions, not machine-generated legal conclusions. Review the queue regularly.

## Phone website and installable 90R app

The full website is responsive for phone browsers. `/90r/` is a separate, installable **90R-only** tracker with the existing bill list, personal watchlist, activity, sources, and author information. It excludes news and court pages from the app navigation. Linked hearing notices open separately on the website. `/90r/install/`, linked as **Install 90R app** across the site, has instructions for Safari on iPhone and Chrome on Android. iOS uses Share → Add to Home Screen; compatible Android browsers also expose a native install prompt.

The manifest's identity, launch URL, shortcuts, and scope are confined to `/90r/`. The service worker is `/90r/sw.js` with `/90r/` scope. The normal website does not register it. The app reads the same `/data/bills.json`; no separate bill updater, account, API key, app-store listing, or payment is required. Device installation still requires the visitor's confirmation.

The worker caches only the 90R app pages, shared visual/code assets, and the bill snapshot. All intercepted requests try the network first with browser-cache bypass; successful responses replace the saved copy. Offline or server-error fallbacks preserve the last snapshot and display a saved-content notice. External official records, news, court data, and hearing pages are not cached by the app. Offline availability depends on a successful initial online visit and retained browser storage. Existing watchlist storage is preserved; iOS/browser/installed-app storage may differ, so use the existing backup/restore controls to transfer notes when needed. There is no cross-device sync or push notification service.

For future app-code changes, bump `CACHE_NAME` in `dist/90r/sw.js` if the offline asset set changes. The new worker waits and presents an **Update app** button before reloading an existing session. Daily data does not require a new worker version because data is network-first. New snapshots load on an online page load or refresh, rather than a phone background job. Extend the app archive policy deliberately after sine die.

Validation: `python -m unittest discover -s tests` and `node --test tests/pwa.test.cjs`. Rebuild the static pages with `python scripts/build_pages.py`. PNG icons include 192px, 512px, a maskable 512px image, and a 180px Apple touch icon derived from the existing maroon-and-gold star.

## Personal watchlists

Stars and notes live only in browser `localStorage`, not on the server. They do not synchronize between devices. Use **Sources & method → Download personal backup / Restore personal backup** to transfer them. CSV export includes the filtered records and personal notes. No email subscriptions or server-side watchlist storage are included. Aggregate Cloudflare Web Analytics is described below.

## Preview locally

```bash
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. Opening `index.html` directly with a `file:` URL may prevent JSON loading. In ChatGPT Sites development, use its managed preview instead of this command.

## Files

- `dist/`: deployable static website and current data.
- `scripts/sync_tlo.py`: official-source fetch, validation, screening, and text-change detection.
- `editorial.json`: curated summaries and inclusion/exclusion decisions.
- `.github/workflows/publish.yml`: daily refresh and GitHub Pages publishing.
- `scripts/package_starter.py`: portable ZIP without hosting identity or credentials.
- `tests/test_sync.py`: safeguards for data integrity and review invalidation.

Calendar: prefiling November 9, 2026; opening January 12, 2027. March 12 and May 31 are the 60th and 140th days; filing exceptions and adopted session rules matter. Sources: https://tlc.texas.gov/docs/legref/Dates-of-Interest.pdf and https://tcss.legis.texas.gov/resources/CN/htm/CN.3.htm.


# Visitor analytics

Cloudflare Web Analytics is enabled for `texasreligiouslibertywatch.org` through a public beacon in `dist/index.html`. The shared page builder carries it into the news, hearing, court, information, and 90R app pages. Do not add a second beacon or enable automatic injection in addition to this manual setup.

Eric can access the private reports by signing into the existing Cloudflare account and opening **Web Analytics**, then **texasreligiouslibertywatch.org**. Reports include visits, page views, referring domains, countries, device types, and performance. Use the `/90r/` path filter for the app entry point; it includes browser visits to that URL as well as installed-app use, so it is not an installation count. Tracker hash views are not a reliable bill-level usage report.

Collection starts when the beacon is deployed; it cannot recover earlier visits. Blocked scripts, offline visits, and browser restrictions can cause undercounting. Reports do not identify visitors by name or email, and the site does not send watchlists or personal notes to analytics. The public beacon identifier is not a Cloudflare login or API credential. Cloudflare currently provides a six-month reporting window.


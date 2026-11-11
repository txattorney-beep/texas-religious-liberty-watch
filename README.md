# Texas Religious Liberty Watch · 90R

A portable static website for religious-liberty bill monitoring across faiths in the 90th Texas Legislature. No paid API, database, or JavaScript build tooling is required.

The initial November 11, 2026 snapshot screens 1,378 official captions, retains 30 potentially relevant measures, and includes nine summaries of identified introduced bill texts. This is a caption-based review queue, not a complete full-text census. All bill records link to Texas Legislature Online.

## Publish for free on GitHub Pages

1. Create a **public** repository in a free GitHub account.
2. Unzip the starter and upload its contents at the repository root. Preserve the `.github/workflows/publish.yml` file. A browser upload may hide dot-folders; the Git method below avoids that problem.
3. Open **Settings → Pages**. Select **GitHub Actions** under Build and deployment.
4. If organization or account policy restricts writes, open **Settings → Actions → General → Workflow permissions**, select read/write permissions, and save. Branch protections may require adjustment or a pull-request update workflow.
5. Open **Actions → Publish and update 90R tracker → Run workflow**. The successful deployment provides the `https://YOUR-ACCOUNT.github.io/YOUR-REPOSITORY/` address.
6. Confirm the live snapshot date and the workflow result in Actions. Scheduled checks run at **13:37 UTC daily**, equivalent to 7:37 a.m. CST / 8:37 a.m. CDT. Automated source checks stop after May 31, 2027. The site remains available afterward.

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
python scripts/package_starter.py
```

The updater reads both 90R filed-legislation reports. It validates the session and expected record counts, screens captions using topic rules, retains previously tracked measures, and refreshes the latest available HTML text for tracked measures. A missing/incomplete report fails the update and preserves the previous snapshot. Individual text-fetch failures are recorded per bill. Histories, hearings, amendments, votes, and fiscal notes remain available through the official links; they are not all separately ingested.

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

## Personal watchlists

Stars and notes live only in browser `localStorage`, not on the server. They do not synchronize between devices. Use **Sources & method → Download personal backup / Restore personal backup** to transfer them. CSV export includes the filtered records and personal notes. No email subscriptions, analytics, or third-party trackers are included.

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

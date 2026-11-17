# Publishing guest contributions

The editorial source is `content/guests.json`, separate from automatically refreshed headlines. It starts empty. No sample articles are published.

Each object requires:
- `slug`: unique lowercase URL words separated by hyphens; changing it changes the URL.
- `title`, `author`, `dek` (short summary), and `authorBio`: nonempty plain text.
- `date`: publication date in `YYYY-MM-DD` form.
- `kind`: exactly `Opinion`, `Reporting`, or `Analysis`.
- `body`: a list of nonempty plain-text paragraphs. HTML is escaped, not interpreted.
- `published`: explicit boolean. Only `true` appears publicly. Set it only after editorial approval and permission to publish the manuscript and byline.
- `featured`: optional boolean. Featured pieces appear before other contributions; publication date breaks ties. Without a featured piece, the newest article leads.

Run `python scripts/build_pages.py` and the test suite after changes. The first approved contribution occupies the large guest slot and the next two use smaller slots. With no published contributions, the homepage/news guest strip is absent, not filled with placeholders. The archive remains at `/voices/`; individual articles have stable `/voices/<slug>/` URLs, canonical/Open Graph metadata, and author-specific structured data. Existing site share buttons use each article URL.

The builder should replace the generated `/voices/` directory before writing these pages so withdrawn drafts do not leave stale pages behind. Do not place manual files there. Automated refreshes must never modify this editorial JSON. Republishing or withdrawing content does not guarantee removal from third-party caches.

Treat draft content as confidential: this is a public source repository. Keep unpublished manuscripts outside the repository until authorized for public disclosure; `published: false` prevents site display, not public access to repository contents. No scheduled publication or automatic approval is implemented.

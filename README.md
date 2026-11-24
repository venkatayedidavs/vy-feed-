# Job Feed

Daily list of new jobs from LinkedIn job alerts, published with GitHub Pages.

- `data/jobs.json` holds every job. Each job has: `id` (LinkedIn job id, used to remove duplicates), `title`, `company`, `location`, `workplace`, `url`, `date_found` (YYYY-MM-DD), `search_location` (which alert found it), `notes`.
- `index.html` shows the jobs grouped by date, newest first, with a text filter and a location filter.
- A scheduled Claude run at about 10:00 Europe/Stockholm reads that day's LinkedIn alert emails, removes duplicates by job id, applies the search preferences, appends new jobs and commits.

The page holds job details only, nothing personal. `robots.txt` and a noindex tag ask search engines not to list it.

## Daily run

1. Search Gmail for `from:jobalerts-noreply@linkedin.com newer_than:2d`.
2. Save each email as one JSON line `{"id","date","subject","plaintextBody"}` in a scratch folder outside the repo (raw emails hold tracking tokens and are never committed).
3. `python3 scripts/parse_alerts.py <scratch folder>` keeps product titles (PM, PO, product lead, head of product) in Skåne, Gothenburg, the Copenhagen area, or remote in Sweden/Denmark, skips job ids already in `data/jobs.json`, and appends the rest.
4. Commit and push `data/jobs.json`.

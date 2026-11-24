# Job Feed

Daily list of new jobs from LinkedIn job alerts, published with GitHub Pages.

- `data/jobs.json` holds every job. Each job has: `id` (LinkedIn job id, used to remove duplicates), `title`, `company`, `location`, `workplace`, `url`, `date_found` (YYYY-MM-DD), `search_location` (which alert found it), `notes`.
- `index.html` shows the jobs grouped by date, newest first, with a text filter and a location filter.
- A scheduled Claude run at 20:00 Europe/Stockholm reads that day's LinkedIn alert emails, removes duplicates by job id, applies the search preferences, appends new jobs and commits.

The page holds job details only, nothing personal. `robots.txt` and a noindex tag ask search engines not to list it.

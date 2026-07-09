# Recruiting Tracker Scraper - Charlotte + Raleigh (v1)

Two independent scripts, built to run on YOUR machine or a cloud runner (not in
Claude's sandbox, which only has network access to coding infrastructure like
GitHub/PyPI - it can't reach company websites or news feeds).

## What's here

- `directory_scraper.py` - scrapes public firm "team/roster" pages to keep the
  broker directory tab fresh. **Currently only Cushman & Wakefield has a working
  roster URL configured** - see "Known gaps" below.
- `news_monitor.py` - pulls OFFICIAL, publisher-sanctioned RSS feeds from Connect
  CRE and GlobeSt, flags articles mentioning both a Charlotte/Raleigh-area keyword
  and one of our tracked firms, and writes them to a CSV for you to review by eye.
  It does **not** auto-write deals into the workbook - extracting exact broker
  names/dollar amounts from article text reliably needs a human reading the
  actual article, not just a script matching keywords.
- `config/firms.py` - per-firm scrape targets/selectors for the directory scraper.
- `config/news_sources.py` - RSS feed URLs + keyword lists for the news monitor.

## Setup

```bash
cd scraper
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Running

```bash
python3 directory_scraper.py    # -> output/directory_scrape_<date>.csv
python3 news_monitor.py         # -> output/news_candidates_<date>.csv
```

Review both CSVs, then manually add anything confirmed into the workbook (same
process we've been doing by hand - this just narrows down what to look at instead
of you re-searching from scratch every time).

## Known gaps (be aware before relying on this)

1. **Only Cushman & Wakefield has a working directory-scrape URL.** CBRE,
   Newmark, and Walker & Dunlop don't appear to publish a single stable "team
   roster" page for their Carolinas Multifamily groups - their bios are
   individually indexed with no reliable list page to crawl. For those three,
   rely on the news monitor to catch "X joins firm's Charlotte office" articles
   instead. If you find an actual roster URL for any of them, add it to
   `config/firms.py` following the Cushman & Wakefield entry as a template.
2. **Selectors will break when a site redesigns its page.** If a firm suddenly
   returns 0 people, that's the signal to go look at the page and update the
   CSS selectors in `config/firms.py` - it's not a sign the firm has no brokers.
3. **The news monitor surfaces candidates, it doesn't extract deal data.** By
   design - see the docstring in `news_monitor.py` for why.

## Scheduling it to run automatically (cloud - recommended)

Since this needs to keep running after you're gone, the sturdiest option is a
scheduled cloud job rather than anyone's personal laptop. A GitHub Actions
workflow is the simplest version of that - it runs on GitHub's servers on a
timer, no server of your own to maintain.

**The workflow file is already included** at `.github/workflows/daily_scan.yml` -
you don't need to write anything, just follow the steps below to get it running.

### Step-by-step setup

1. **Create a GitHub account** if you don't have one: https://github.com/signup
2. **Create a new repository**:
   - Click the "+" in the top right → "New repository"
   - Name it something like `cre-recruiting-scraper`
   - Set it to **Private** (this is your working data/scripts, keep it private)
   - Don't check any of the "Initialize with..." boxes
   - Click "Create repository"
3. **Upload this `scraper` folder's contents to that repo.** Easiest way with no command-line tools:
   - On the new repo's page, click "uploading an existing file"
   - Drag in every file and folder from this `scraper` folder, **including the
     hidden `.github` folder** (if your file browser hides it, show hidden
     files first - on Windows: File Explorer → View → check "Hidden items")
   - Commit the files
4. **Check it worked**: click the "Actions" tab at the top of the repo. You
   should see "Daily CRE Scan" listed as a workflow. It'll run automatically
   at 9am ET daily, but to test it right away:
   - Click "Daily CRE Scan" in the left sidebar
   - Click the "Run workflow" dropdown on the right → "Run workflow" button
   - Refresh after a minute or two - you'll see a run appear
5. **Get the results**: click into a completed run, scroll to "Artifacts" at
   the bottom - there's a zip with that day's CSVs. Download it to review.

That's it - no server, no laptop staying on, keeps running whether or not
you're still on the team.

### A note on limitations
- The `continue-on-error: true` lines mean if one script fails (e.g. a firm's
  page changes structure), the workflow still completes and uploads whatever
  it did get, instead of the whole run failing silently. Check the run logs
  (click into a run, then into a step) if a CSV looks empty - that's where
  you'll see the actual error.
- Artifacts expire after 90 days on GitHub's free tier. If you want a
  permanent history instead of rolling 90 days, a further improvement would be
  having the workflow commit the CSVs into the repo itself rather than just
  uploading them as artifacts - happy to add that if useful.

## Scheduling it locally (simpler, less durable)

- **Windows:** Task Scheduler -> create a basic task -> action = "Start a program"
  -> program = path to `venv\Scripts\python.exe` -> arguments = path to the
  script -> trigger = daily.
- **Mac/Linux:** `crontab -e` and add a line like:
  `0 9 * * * cd /path/to/scraper && venv/bin/python directory_scraper.py`

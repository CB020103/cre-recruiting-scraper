"""
Per-firm scrape config for the broker directory scraper.

Each entry defines ONE page to scrape (usually a team/roster page) and the CSS
selectors needed to pull each person's name/title/bio-link off that page.

IMPORTANT: Every commercial site's HTML is different and WILL change over time.
The selectors below were hand-checked against the live pages as of the date noted,
but you should expect to re-check/update selectors every few months when a scrape
suddenly returns 0 results - that almost always means the site redesigned its page,
not that the firm has no brokers.

Only add firms/pages here that are PUBLIC marketing pages (team rosters, bio pages).
Do not point this at LoopNet, Crexi, or any site whose Terms of Service prohibit
scraping - this tool is intentionally scoped to firms' own public websites only.
"""

FIRMS = [
    {
        "firm": "Cushman & Wakefield",
        "market": "Charlotte + Raleigh",
        "url": "https://multifamily.cushwake.com/Offices/Charlotte/Team",
        "checked": "2026-07",
        # Confirmed via browser inspection: each person is an <h2> like
        #   <h2>Jordan McCarley <span class="title">Executive Vice Chair</span></h2>
        # Name and title are NOT separate elements - title is nested inside the
        # same h2 as the name. person_selector finds each h2; title_selector is
        # relative to that h2; name = h2's full text with the title text removed
        # (see directory_scraper.py for the extraction logic this requires).
        "person_selector": "h2",
        "title_selector": ".title",
        "link_selector": None,  # no per-person bio URL found - "view" just expands bio inline via JS
        "notes": "Sunbelt Multifamily Advisory Group Charlotte roster page",
    },
    {
        "firm": "CBRE",
        "market": "Charlotte + Raleigh",
        "url": None,  # No single roster page found - CBRE profiles are individually indexed.
        "checked": "2026-07",
        "notes": (
            "CBRE does not appear to have one stable 'team roster' URL for Carolinas "
            "Multifamily - individual bio pages (e.g. /people/john-phoenix) exist but "
            "there's no reliable list page to crawl from. Recommend covering CBRE via "
            "the news monitor (press releases on new hires) rather than a page scrape, "
            "until/unless a team roster URL is confirmed."
        ),
    },
    {
        "firm": "Newmark",
        "market": "Charlotte + Raleigh",
        "url": None,
        "checked": "2026-07",
        "notes": (
            "Same situation as CBRE - no confirmed public roster page for the Carolinas "
            "Multifamily team found. Cover via news monitor for now."
        ),
    },
    {
        "firm": "Walker & Dunlop",
        "market": "Charlotte + Raleigh",
        "url": None,
        "checked": "2026-07",
        "notes": "No confirmed roster page found. Cover via news monitor for now.",
    },
]

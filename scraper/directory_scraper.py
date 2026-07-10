"""
directory_scraper.py

Scrapes each firm's public team/roster page (as configured in config/firms.py)
and writes a CSV of brokers found: name, company, title, city, market, source_url,
scraped_date.

This ONLY targets pages firms publish publicly to be found (team/bio pages) - it
does not touch LoopNet, Crexi, or any paywalled/ToS-restricted source.

Usage:
    python directory_scraper.py

Output:
    output/directory_scrape_<YYYY-MM-DD>.csv

Requirements:
    pip install requests beautifulsoup4
"""

import csv
import sys
import time
from datetime import date, datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from config.firms import FIRMS
from config.manual_candidates import MANUAL_CANDIDATES

HEADERS = {
    # A normal browser UA - identify honestly, don't try to look like something we're not.
    "User-Agent": (
        "Mozilla/5.0 (compatible; RecruitingResearchBot/1.0; "
        "+internal-use-only, contact: yourteam@yourcompany.com)"
    )
}
TIMEOUT = 15
DELAY_BETWEEN_REQUESTS_SEC = 3  # be a polite, low-volume crawler


def scrape_firm(firm_config: dict) -> list[dict]:
    url = firm_config.get("url")
    if not url:
        print(f"[skip] {firm_config['firm']}: no roster URL configured "
              f"({firm_config.get('notes', '')})")
        return []

    print(f"[fetch] {firm_config['firm']}: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[error] {firm_config['firm']}: request failed - {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    people = soup.select(firm_config["person_selector"])

    if not people:
        print(f"[warn] {firm_config['firm']}: 0 people found with selector "
              f"'{firm_config['person_selector']}' - the page structure may have "
              f"changed. Selectors were last checked {firm_config.get('checked')}.")
        return []

    rows = []
    for person in people:
        title_el = person.select_one(firm_config["title_selector"]) if firm_config.get("title_selector") else None
        title = title_el.get_text(strip=True) if title_el else None

        if "name_selector" in firm_config:
            # Name and title live in separate elements within the person block.
            name_el = person.select_one(firm_config["name_selector"])
            name = name_el.get_text(strip=True) if name_el else None
        else:
            # Name and title share one element (e.g. <h2>Name <span class="title">Title</span></h2>).
            # Take the full text and strip out the title portion to isolate the name.
            full_text = person.get_text(" ", strip=True)
            name = full_text.replace(title, "").strip() if title else full_text

        link_selector = firm_config.get("link_selector")
        link_el = person.select_one(link_selector) if link_selector else None
        bio_link = link_el.get("href") if link_el and link_el.has_attr("href") else None

        if bio_link and bio_link.startswith("/"):
            # relative link - stitch to domain
            from urllib.parse import urljoin
            bio_link = urljoin(url, bio_link)

        junk_names = {
            "register now",
            "loading...",
            "communication error",
            "cushman & wakefield multifamily advisory group charlotte office",
        }

        if not name or name.strip().lower() in junk_names:
            continue

        rows.append({
            "name": name,
            "company": firm_config["firm"],
            "title": title or "",
            "city": "",  # city usually isn't on the roster page; fill in manually or via bio page
            "market": firm_config["market"],
            "website": bio_link or url,
            "source_url": url,
            "scraped_date": date.today().isoformat(),
        })

    print(f"[ok] {firm_config['firm']}: found {len(rows)} people")
    return rows


def main():
    all_rows = list(MANUAL_CANDIDATES)
    print(f"[manual] loaded {len(MANUAL_CANDIDATES)} verified recruiting candidates")

    for firm_config in FIRMS:
        all_rows.extend(scrape_firm(firm_config))
        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)

    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"directory_scrape_{date.today().isoformat()}.csv"

    fieldnames = ["name", "company", "title", "city", "market", "website",
                  "source_url", "scraped_date"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\nWrote {len(all_rows)} rows to {out_path}")
    if not all_rows:
        print("No rows scraped - check that at least one firm in config/firms.py "
              "has a working 'url' and correct selectors.")


if __name__ == "__main__":
    main()


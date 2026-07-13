"""Create a market-specific broker recruiting directory.

Combines:
1. Verified manual candidates
2. Public firm roster pages configured in config/firms.py

Usage:
    python directory_scraper.py
    python directory_scraper.py --market charlotte-raleigh
    python directory_scraper.py --market atlanta
"""

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))

from config.firms import FIRMS
from config.manual_candidates import MANUAL_CANDIDATES
from config.markets import (
    DEFAULT_MARKET,
    MARKETS,
    candidate_matches_market,
    get_market,
)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RecruitingResearchBot/1.0; "
        "+internal-use-only)"
    )
}

TIMEOUT = 15
DELAY_BETWEEN_REQUESTS_SEC = 3

JUNK_NAMES = {
    "register now",
    "loading",
    "loading...",
    "communication error",
    "cushman & wakefield multifamily advisory group charlotte office",
}

EXCLUDED_TITLE_KEYWORDS = {
    "analyst",
    "financial analyst",
    "research analyst",
    "marketing",
    "transaction specialist",
    "transaction coordinator",
    "coordinator",
    "client services",
    "administrative",
    "operations",
}


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Build a market-specific CRE broker recruiting directory."
    )

    parser.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        choices=sorted(MARKETS),
        help="Market slug to process.",
    )

    return parser.parse_args()


def is_valid_broker(name, title):
    name_lower = str(name or "").strip().lower()
    title_lower = str(title or "").strip().lower()

    if not name_lower:
        return False

    if name_lower in JUNK_NAMES:
        return False

    if any(
        keyword in title_lower
        for keyword in EXCLUDED_TITLE_KEYWORDS
    ):
        return False

    return True


def firm_matches_market(firm_config, market_slug):
    firm_market = str(
        firm_config.get("market", "")
    ).strip().lower()

    market_config = get_market(market_slug)

    valid_aliases = {
        value.lower()
        for value in market_config["aliases"]
    }

    return firm_market in valid_aliases


def scrape_firm(firm_config):
    url = firm_config.get("url")

    if not url:
        print(
            f"[skip] {firm_config['firm']}: "
            "no roster URL configured"
        )
        return []

    print(f"[fetch] {firm_config['firm']}: {url}")

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

    except requests.RequestException as error:
        print(
            f"[error] {firm_config['firm']}: "
            f"request failed - {error}"
        )
        return []

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    people = soup.select(
        firm_config["person_selector"]
    )

    if not people:
        print(
            f"[warn] {firm_config['firm']}: "
            "0 people found"
        )
        return []

    rows = []

    for person in people:
        title_element = None

        if firm_config.get("title_selector"):
            title_element = person.select_one(
                firm_config["title_selector"]
            )

        title = (
            title_element.get_text(" ", strip=True)
            if title_element
            else ""
        )

        if firm_config.get("name_selector"):
            name_element = person.select_one(
                firm_config["name_selector"]
            )

            name = (
                name_element.get_text(" ", strip=True)
                if name_element
                else ""
            )

        else:
            full_text = person.get_text(
                " ",
                strip=True,
            )

            name = (
                full_text.replace(title, "").strip()
                if title
                else full_text
            )

        if not is_valid_broker(name, title):
            continue

        link_selector = firm_config.get(
            "link_selector"
        )

        link_element = (
            person.select_one(link_selector)
            if link_selector
            else None
        )

        bio_link = (
            link_element.get("href")
            if link_element
            and link_element.has_attr("href")
            else None
        )

        if bio_link:
            bio_link = urljoin(url, bio_link)

        rows.append({
            "name": name,
            "company": firm_config["firm"],
            "title": title,
            "city": firm_config.get("city", ""),
            "market": firm_config["market"],
            "website": bio_link or url,
            "source_url": url,
            "source_type": "live_roster",
            "scraped_date": date.today().isoformat(),
        })

    print(
        f"[ok] {firm_config['firm']}: "
        f"found {len(rows)} brokers"
    )

    return rows


def deduplicate_rows(rows):
    deduplicated = {}

    for row in rows:
        key = (
            str(row.get("name", "")).strip().lower(),
            str(row.get("company", "")).strip().lower(),
        )

        if key not in deduplicated:
            deduplicated[key] = row
            continue

        existing = deduplicated[key]

        for field, value in row.items():
            if value and not existing.get(field):
                existing[field] = value

    return list(deduplicated.values())


def main():
    args = parse_arguments()
    market_slug = args.market
    market_config = get_market(market_slug)

    print(
        f"[market] building directory for "
        f"{market_config['display_name']}"
    )

    manual_rows = [
        dict(candidate, source_type="manual_verified")
        for candidate in MANUAL_CANDIDATES
        if candidate_matches_market(
            candidate,
            market_slug,
        )
    ]

    print(
        f"[manual] loaded {len(manual_rows)} "
        "verified candidates"
    )

    all_rows = list(manual_rows)

    for firm_config in FIRMS:
        if not firm_matches_market(
            firm_config,
            market_slug,
        ):
            continue

        all_rows.extend(
            scrape_firm(firm_config)
        )

        time.sleep(
            DELAY_BETWEEN_REQUESTS_SEC
        )

    all_rows = deduplicate_rows(all_rows)

    all_rows.sort(
        key=lambda row: (
            str(row.get("company", "")),
            str(row.get("name", "")),
        )
    )

    output_directory = (
        Path(__file__).parent / "output"
    )

    output_directory.mkdir(
        exist_ok=True
    )

    output_path = (
        output_directory
        / (
            f"directory_scrape_"
            f"{market_slug}_"
            f"{date.today().isoformat()}.csv"
        )
    )

    fieldnames = [
        "name",
        "company",
        "title",
        "city",
        "market",
        "website",
        "source_url",
        "source_type",
        "scraped_date",
    ]

    with output_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(all_rows)

    print()
    print(
        f"Wrote {len(all_rows)} rows "
        f"to {output_path}"
    )


if __name__ == "__main__":
    main()

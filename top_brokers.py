"""Find the top broker at each firm, plus 1-2 people right behind them.

Deliberately simple: ranks by TITLE SENIORITY ONLY (Vice Chair > Managing
Director > Director > Associate, etc.). No deal volume, no scoring math, no
priority letters - just "who's most senior at this firm, and who's next."

Usage:
    python top_brokers.py                       # runs ALL markets (default)
    python top_brokers.py --market atlanta       # just one market
    python top_brokers.py --market charlotte-raleigh
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
from config.markets import MARKETS, candidate_matches_market, get_market

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RecruitingResearchBot/1.0; +internal-use-only)"
    )
}
TIMEOUT = 15
DELAY_BETWEEN_REQUESTS_SEC = 3

RUNNERS_UP_PER_FIRM = 3

JUNK_NAMES = {
    "register now", "loading", "loading...", "communication error",
}

EXCLUDED_TITLE_KEYWORDS = {
    "analyst", "financial analyst", "research analyst", "marketing",
    "transaction specialist", "transaction coordinator", "coordinator",
    "client services", "administrative", "operations", "graphic designer",
}

TITLE_TIERS = [
    ["executive vice chair", "vice chair", "vice chairman", "president"],
    ["executive managing director", "senior managing director", "managing partner"],
    ["managing director"],
    ["senior director", "senior vice president"],
    ["director", "vice president"],
    ["senior associate"],
    ["associate"],
]


def title_tier(title):
    title_lower = str(title or "").strip().lower()
    for tier_index, phrases in enumerate(TITLE_TIERS):
        if any(phrase in title_lower for phrase in phrases):
            return tier_index
    return len(TITLE_TIERS)


def is_valid_broker(name, title):
    name_lower = str(name or "").strip().lower()
    title_lower = str(title or "").strip().lower()
    if not name_lower or name_lower in JUNK_NAMES:
        return False
    if any(keyword in title_lower for keyword in EXCLUDED_TITLE_KEYWORDS):
        return False
    return True


def firm_matches_market(firm_config, market_slug):
    firm_market = str(firm_config.get("market", "")).strip().lower()
    market_config = get_market(market_slug)
    valid_aliases = {value.lower() for value in market_config["aliases"]}
    return firm_market in valid_aliases


def scrape_firm(firm_config):
    url = firm_config.get("url")
    if not url:
        print(f"[skip] {firm_config['firm']}: no roster URL configured")
        return []

    print(f"[fetch] {firm_config['firm']}: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"[error] {firm_config['firm']}: request failed - {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    people = soup.select(firm_config["person_selector"])
    if not people:
        print(f"[warn] {firm_config['firm']}: 0 people found - page structure may have changed")
        return []

    rows = []
    for person in people:
        title_element = person.select_one(firm_config["title_selector"]) if firm_config.get("title_selector") else None
        title = title_element.get_text(" ", strip=True) if title_element else ""

        if firm_config.get("name_selector"):
            name_element = person.select_one(firm_config["name_selector"])
            name = name_element.get_text(" ", strip=True) if name_element else ""
        else:
            full_text = person.get_text(" ", strip=True)
            name = full_text.replace(title, "").strip() if title else full_text

        if not is_valid_broker(name, title):
            continue

        link_selector = firm_config.get("link_selector")
        link_element = person.select_one(link_selector) if link_selector else None
        bio_link = link_element.get("href") if link_element and link_element.has_attr("href") else None
        if bio_link:
            bio_link = urljoin(url, bio_link)

        rows.append({
            "name": name,
            "company": firm_config["firm"],
            "title": title,
            "city": firm_config.get("city", ""),
            "market": firm_config["market"],
            "website": bio_link or url,
        })

    print(f"[ok] {firm_config['firm']}: found {len(rows)} brokers")
    return rows


def deduplicate(rows):
    seen = {}
    for row in rows:
        key = (row.get("name", "").strip().lower(), row.get("company", "").strip().lower())
        if key not in seen:
            seen[key] = row
    return list(seen.values())


def process_market(market_slug):
    """Build the top-broker list for one market. Returns the output rows
    (each tagged with which market it's for) and prints a readable summary."""
    market_config = get_market(market_slug)
    print(f"\n[market] {market_config['display_name']}")

    manual_rows = [
        dict(candidate) for candidate in MANUAL_CANDIDATES
        if candidate_matches_market(candidate, market_slug)
    ]

    all_rows = list(manual_rows)
    for firm_config in FIRMS:
        if not firm_matches_market(firm_config, market_slug):
            continue
        all_rows.extend(scrape_firm(firm_config))
        time.sleep(DELAY_BETWEEN_REQUESTS_SEC)

    all_rows = deduplicate(all_rows)

    by_company = {}
    for row in all_rows:
        by_company.setdefault(row["company"], []).append(row)

    output_rows = []
    for company in sorted(by_company):
        people = sorted(by_company[company], key=lambda r: title_tier(r.get("title")))
        top_group = people[: 1 + RUNNERS_UP_PER_FIRM]

        print(f"\n{company}")
        for rank, person in enumerate(top_group, start=1):
            label = "TOP" if rank == 1 else f"#{rank}"
            print(f"  [{label}] {person['name']} - {person.get('title', '')}")
            output_rows.append({
                "market": market_config["display_name"],
                "company": company,
                "rank": rank,
                "name": person["name"],
                "title": person.get("title", ""),
                "city": person.get("city", ""),
                "website": person.get("website", ""),
            })

    return output_rows


def parse_arguments():
    parser = argparse.ArgumentParser(description="Find the top broker(s) at each firm, across one or all markets.")
    parser.add_argument(
        "--market",
        default="all",
        choices=sorted(MARKETS) + ["all"],
        help="A specific market slug, or 'all' (default) to run every market in one pass.",
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    markets_to_run = sorted(MARKETS) if args.market == "all" else [args.market]

    all_output_rows = []
    for market_slug in markets_to_run:
        all_output_rows.extend(process_market(market_slug))

    print(f"\n{'=' * 70}")

    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    if args.market == "all":
        output_path = output_dir / f"top_brokers_ALL_MARKETS_{date.today().isoformat()}.csv"
    else:
        output_path = output_dir / f"top_brokers_{args.market}_{date.today().isoformat()}.csv"

    fieldnames = ["market", "company", "rank", "name", "title", "city", "website"]
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_output_rows)

    print(f"\nWrote {len(all_output_rows)} rows across {len(markets_to_run)} market(s) to {output_path}")


if __name__ == "__main__":
    main()

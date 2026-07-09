"""
news_monitor.py

Pulls official RSS feeds (Connect CRE, GlobeSt - see config/news_sources.py) and
flags articles that mention BOTH our target market (Charlotte/Raleigh area) AND
one of our tracked companies. Writes results to a CSV for human review.

This deliberately does NOT try to auto-extract broker names/deal sizes from
article text - free-text extraction like that is unreliable (wrong names, wrong
numbers) and a bad thing to feed into a workbook silently. Instead this script
surfaces the *candidate* articles; a person skims the headline/link and manually
adds the real deal + broker name to the CharRal RCA tab, same as we've been doing
by hand. That's a deliberate design choice, not a limitation to "fix" later -
accuracy here matters more than full automation.

Usage:
    python news_monitor.py

Output:
    output/news_candidates_<YYYY-MM-DD>.csv

Requirements:
    pip install feedparser
"""

import csv
import re
import sys
from datetime import date
from pathlib import Path

import feedparser
import requests

sys.path.insert(0, str(Path(__file__).parent))
from config.news_sources import RSS_FEEDS, MARKET_KEYWORDS, TARGET_COMPANIES

# Some feed hosts (feedblitz in particular) are pickier about requests that
# don't look like they're coming from a browser/known feed reader.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; RecruitingNewsMonitor/1.0; "
        "+internal-use-only, contact: yourteam@yourcompany.com)"
    )
}


def fetch_feed(url: str):
    """
    Fetch a feed URL ourselves (rather than letting feedparser fetch it) so we
    can clean up known publisher bugs before parsing. Some feeds (e.g. GlobeSt's
    feedblitz feeds) append stray content after the closing </rss> tag, which
    trips up strict XML parsing with "junk after document element".
    """
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=15)
    resp.raise_for_status()
    text = resp.text

    # If there's a closing </rss> or </feed> tag, truncate everything after it -
    # anything past that point isn't part of the actual feed document.
    for closing_tag in ("</rss>", "</feed>"):
        idx = text.rfind(closing_tag)
        if idx != -1:
            text = text[: idx + len(closing_tag)]
            break

    return feedparser.parse(text)


def article_is_relevant(text: str, market_prefiltered: bool) -> tuple[bool, list[str], list[str]]:
    text_lower = text.lower()
    matched_markets = [kw for kw in MARKET_KEYWORDS if kw in text_lower]
    matched_companies = [c for c in TARGET_COMPANIES if c.lower() in text_lower]

    if market_prefiltered:
        # The feed itself is already scoped to this market - only need a company match.
        is_relevant = bool(matched_companies)
    else:
        is_relevant = bool(matched_markets) and bool(matched_companies)

    return is_relevant, matched_markets, matched_companies


def main():
    rows = []

    for feed_config in RSS_FEEDS:
        print(f"[fetch] {feed_config['source']}: {feed_config['url']}")
        try:
            parsed = fetch_feed(feed_config["url"])
        except requests.RequestException as e:
            print(f"[error] {feed_config['source']}: request failed - {e}")
            continue

        if parsed.bozo and not parsed.entries:
            print(f"[error] {feed_config['source']}: could not parse feed "
                  f"({parsed.bozo_exception})")
            continue

        if not parsed.entries:
            print(f"[ok] {feed_config['source']}: feed parsed fine but has 0 "
                  f"articles right now (nothing wrong on our end - just empty)")
            continue

        print(f"[ok] {feed_config['source']}: {len(parsed.entries)} articles fetched")

        for entry in parsed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")
            published = entry.get("published", "")

            combined_text = f"{title} {summary}"
            relevant, markets, companies = article_is_relevant(
                combined_text, feed_config.get("market_prefiltered", False)
            )

            if relevant:
                rows.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "matched_markets": ", ".join(markets),
                    "matched_companies": ", ".join(companies),
                    "feed_source": feed_config["source"],
                    "checked_date": date.today().isoformat(),
                })

    out_dir = Path(__file__).parent / "output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"news_candidates_{date.today().isoformat()}.csv"

    fieldnames = ["title", "link", "published", "matched_markets",
                  "matched_companies", "feed_source", "checked_date"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} candidate articles to {out_path}")
    print("Review these manually and add confirmed deals to the CharRal RCA tab - "
          "this script intentionally does not auto-populate the workbook.")


if __name__ == "__main__":
    main()

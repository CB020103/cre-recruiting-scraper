"""Rank recruiting candidates within a selected market.

The score is designed to prioritize verified performance rather than title.

Usage:
    python score_candidates.py
    python score_candidates.py --market charlotte-raleigh
    python score_candidates.py --market atlanta
"""

import argparse
import csv
from datetime import date
from pathlib import Path

from config.markets import (
    DEFAULT_MARKET,
    MARKETS,
)


def clean(value):
    return str(value or "").strip()


def parse_number(value):
    text = clean(value)

    if not text:
        return 0.0

    text = (
        text
        .replace("$", "")
        .replace(",", "")
        .replace("+", "")
    )

    multiplier = 1

    if text.lower().endswith("b"):
        multiplier = 1_000_000_000
        text = text[:-1]

    elif text.lower().endswith("m"):
        multiplier = 1_000_000
        text = text[:-1]

    try:
        return float(text) * multiplier

    except ValueError:
        return 0.0


def title_score(title):
    """Titles vary heavily by firm, so this is deliberately low-weight."""

    title_lower = clean(title).lower()

    senior_phrases = [
        "executive vice chair",
        "executive vice chairman",
        "vice chair",
        "vice chairman",
        "executive managing director",
        "senior managing director",
        "managing director",
        "principal",
        "partner",
        "president",
    ]

    midlevel_phrases = [
        "senior director",
        "director",
        "senior vice president",
        "vice president",
    ]

    emerging_phrases = [
        "senior associate",
        "associate",
    ]

    if any(
        phrase in title_lower
        for phrase in senior_phrases
    ):
        return 5

    if any(
        phrase in title_lower
        for phrase in midlevel_phrases
    ):
        return 3

    if any(
        phrase in title_lower
        for phrase in emerging_phrases
    ):
        return 1

    return 0


def market_specialty_score(row):
    combined = " ".join([
        clean(row.get("title")),
        clean(row.get("market")),
        clean(row.get("website")),
        clean(row.get("source_url")),
    ]).lower()

    score = 0

    if "multifamily" in combined:
        score += 10

    elif "multi-housing" in combined:
        score += 10

    elif "capital markets" in combined:
        score += 7

    elif "investment sales" in combined:
        score += 7

    if clean(row.get("city")):
        score += 5

    return min(score, 15)


def volume_score(row):
    volume = parse_number(
        row.get("verified_volume_usd")
        or row.get("known_volume")
    )

    if volume >= 10_000_000_000:
        return 40

    if volume >= 5_000_000_000:
        return 36

    if volume >= 2_000_000_000:
        return 32

    if volume >= 1_000_000_000:
        return 28

    if volume >= 500_000_000:
        return 22

    if volume >= 250_000_000:
        return 16

    if volume >= 100_000_000:
        return 10

    if volume > 0:
        return 5

    return 0


def transaction_count_score(row):
    count = parse_number(
        row.get("verified_deal_count")
    )

    if count >= 100:
        return 15

    if count >= 50:
        return 12

    if count >= 20:
        return 9

    if count >= 10:
        return 6

    if count > 0:
        return 3

    return 0


def recent_activity_score(row):
    recent_count = parse_number(
        row.get("recent_deal_count")
    )

    if recent_count >= 10:
        return 20

    if recent_count >= 5:
        return 16

    if recent_count >= 3:
        return 12

    if recent_count >= 1:
        return 6

    return 0


def institutional_score(row):
    value = clean(
        row.get("institutional_experience")
    ).lower()

    if value in {
        "yes",
        "true",
        "high",
        "institutional",
    }:
        return 5

    return 0


def confidence_label(row):
    performance_fields = [
        clean(row.get("verified_volume_usd")),
        clean(row.get("verified_deal_count")),
        clean(row.get("recent_deal_count")),
        clean(row.get("performance_source")),
    ]

    evidence_count = sum(
        bool(value)
        for value in performance_fields
    )

    if evidence_count >= 3:
        return "High"

    if evidence_count >= 1:
        return "Medium"

    return "Low"


def priority_label(score, confidence):
    if score >= 75 and confidence == "High":
        return "A"

    if score >= 55:
        return "B"

    if score >= 35:
        return "C"

    return "Research"


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--market",
        default=DEFAULT_MARKET,
        choices=sorted(MARKETS),
    )

    return parser.parse_args()


def main():
    args = parse_arguments()
    today = date.today().isoformat()
    base_directory = Path(__file__).parent

    input_path = (
        base_directory
        / "output"
        / (
            f"directory_scrape_"
            f"{args.market}_"
            f"{today}.csv"
        )
    )

    output_path = (
        base_directory
        / "output"
        / (
            f"ranked_candidates_"
            f"{args.market}_"
            f"{today}.csv"
        )
    )

    if not input_path.exists():
        raise FileNotFoundError(
            f"Could not find {input_path}. "
            "Run directory_scraper.py first."
        )

    with input_path.open(
        newline="",
        encoding="utf-8-sig",
    ) as file:
        rows = list(csv.DictReader(file))

    ranked_rows = []

    for row in rows:
        title_points = title_score(
            row.get("title")
        )

        market_points = market_specialty_score(
            row
        )

        volume_points = volume_score(
            row
        )

        deal_count_points = (
            transaction_count_score(row)
        )

        recent_points = (
            recent_activity_score(row)
        )

        institutional_points = (
            institutional_score(row)
        )

        performance_points = (
            volume_points
            + deal_count_points
            + recent_points
            + institutional_points
        )

        total_score = (
            title_points
            + market_points
            + performance_points
        )

        confidence = confidence_label(row)

        row["title_score"] = title_points
        row["market_specialty_score"] = market_points
        row["volume_score"] = volume_points
        row["transaction_count_score"] = deal_count_points
        row["recent_activity_score"] = recent_points
        row["institutional_score"] = institutional_points
        row["performance_score"] = performance_points
        row["recruiting_score"] = total_score
        row["confidence"] = confidence
        row["priority"] = priority_label(
            total_score,
            confidence,
        )

        ranked_rows.append(row)

    ranked_rows.sort(
        key=lambda row: (
            -int(row["recruiting_score"]),
            clean(row.get("company")),
            clean(row.get("name")),
        )
    )

    if not ranked_rows:
        print("No candidates found.")
        return

    fieldnames = list(
        ranked_rows[0].keys()
    )

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
        writer.writerows(ranked_rows)

    print(
        f"Wrote {len(ranked_rows)} "
        f"ranked candidates to {output_path}"
    )

    print()
    print("Top recruiting candidates:")

    for row in ranked_rows[:10]:
        print(
            f"{int(row['recruiting_score']):>3} | "
            f"Priority {row['priority']} | "
            f"{row['name']} | "
            f"{row['company']} | "
            f"{row['title']}"
        )


if __name__ == "__main__":
    main()

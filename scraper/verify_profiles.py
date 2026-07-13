"""Re-check official broker profiles and extract reviewable performance evidence.

Reads known brokers from config/manual_candidates.py, visits each official profile,
verifies name/company/title, detects possible performance metrics, and writes a CSV.
It never silently overwrites candidate records.

Usage:
    python verify_profiles.py --market charlotte-raleigh

Setup:
    pip install requests beautifulsoup4 playwright
    python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import csv
import html
import re
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from config.manual_candidates import MANUAL_CANDIDATES
from config.markets import DEFAULT_MARKET, MARKETS, candidate_matches_market

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0 Safari/537.36"
    )
}
REQUEST_TIMEOUT = 20
DELAY_SECONDS = 1.5

CAREER_CONTEXT = re.compile(
    r"\b(career|since joining|since \d{4}|throughout (?:his|her|their) career|"
    r"has (?:completed|closed|sold|brokered|executed)|has been involved|"
    r"totaling|totalling|aggregate|cumulative|to date)\b",
    re.IGNORECASE,
)

VOLUME_CONTEXT = re.compile(
    r"\b(transaction volume|sales volume|brokerage sales|brokerage volume|"
    r"aggregate transaction volume|total transaction volume|transactions? valued|"
    r"in transactions?|in sales|of transactions?|of sales)\b",
    re.IGNORECASE,
)

DEAL_CONTEXT = re.compile(
    r"\b(transactions?|deals?|sales)\b",
    re.IGNORECASE,
)

UNIT_CONTEXT = re.compile(
    r"\b(apartment units?|multifamily units?|multi-housing units?|units? sold|units? transacted)\b",
    re.IGNORECASE,
)

PROPERTY_SPECIFIC_CONTEXT = re.compile(
    r"\b(property|community|asset|portfolio|development|acquisition|disposition|"
    r"sale of|financing for|loan|refinancing|recapitalization)\b",
    re.IGNORECASE,
)

MONEY_PATTERN = re.compile(
    r"(?:more than|over|approximately|approx\.?|in excess of|nearly)?\s*"
    r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*(billion|million|bn|mm|b|m)\b",
    re.IGNORECASE,
)
COUNT_PATTERN = re.compile(
    r"(?:more than|over|approximately|nearly)?\s*([0-9][0-9,]*)\s*\+?\s*"
    r"(transactions?|deals?)\b",
    re.IGNORECASE,
)
UNITS_PATTERN = re.compile(
    r"(?:more than|over|approximately|nearly)?\s*([0-9][0-9,]*)\s*\+?\s*"
    r"(?:apartment\s+|multifamily\s+|multi-housing\s+)?units?\b",
    re.IGNORECASE,
)


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).casefold()).strip()


def parse_money(number: str, suffix: str) -> int:
    value = float(number)
    multiplier = 1_000_000_000 if suffix.casefold() in {"billion", "bn", "b"} else 1_000_000
    return int(value * multiplier)


def sentence_windows(text: str) -> list[str]:
    """Split profile text into reviewable sentence-like windows."""
    chunks = re.split(r"(?<=[.!?])\s+|\s*[|•]\s*", text)
    return [clean(chunk) for chunk in chunks if len(clean(chunk)) >= 20]


def confidence_from_score(score: int) -> str:
    if score >= 9:
        return "High"
    if score >= 6:
        return "Medium"
    return "Low"


def money_candidate_score(sentence: str) -> int:
    score = 0
    if VOLUME_CONTEXT.search(sentence):
        score += 6
    if CAREER_CONTEXT.search(sentence):
        score += 4
    if re.search(r"\b(multifamily|multi-housing|investment sales|brokerage)\b", sentence, re.I):
        score += 2
    if re.search(r"\b(more than|over|in excess of|approximately|nearly)\b", sentence, re.I):
        score += 1
    if PROPERTY_SPECIFIC_CONTEXT.search(sentence) and not VOLUME_CONTEXT.search(sentence):
        score -= 6
    if re.search(r"\b(largest|single|one transaction|one deal)\b", sentence, re.I):
        score -= 4
    return score


def count_candidate_score(sentence: str) -> int:
    score = 3 if DEAL_CONTEXT.search(sentence) else 0
    if CAREER_CONTEXT.search(sentence):
        score += 4
    if re.search(r"\b(more than|over|in excess of|approximately|nearly)\b", sentence, re.I):
        score += 1
    if re.search(r"\b(multifamily|multi-housing|investment sales|brokerage)\b", sentence, re.I):
        score += 2
    if PROPERTY_SPECIFIC_CONTEXT.search(sentence) and not CAREER_CONTEXT.search(sentence):
        score -= 4
    return score


def unit_candidate_score(sentence: str) -> int:
    score = 4 if UNIT_CONTEXT.search(sentence) else 0
    if CAREER_CONTEXT.search(sentence):
        score += 4
    if re.search(r"\b(more than|over|in excess of|approximately|nearly)\b", sentence, re.I):
        score += 1
    if re.search(r"\b(multifamily|multi-housing|apartment)\b", sentence, re.I):
        score += 2
    if PROPERTY_SPECIFIC_CONTEXT.search(sentence) and not CAREER_CONTEXT.search(sentence):
        score -= 4
    return score


def best_metric_candidate(candidates: list[tuple[int, int, str]], minimum_score: int):
    """Choose strongest context first, then the larger value as a tiebreaker."""
    valid = [candidate for candidate in candidates if candidate[0] >= minimum_score]
    if not valid:
        return None, 0, ""
    score, value, evidence = max(valid, key=lambda item: (item[0], item[1]))
    return value, score, evidence


def extract_metrics(text: str) -> dict[str, Any]:
    money_candidates: list[tuple[int, int, str]] = []
    deal_candidates: list[tuple[int, int, str]] = []
    unit_candidates: list[tuple[int, int, str]] = []

    for sentence in sentence_windows(text):
        for match in MONEY_PATTERN.finditer(sentence):
            money_candidates.append((
                money_candidate_score(sentence),
                parse_money(match.group(1), match.group(2)),
                sentence[:700],
            ))

        for match in COUNT_PATTERN.finditer(sentence):
            deal_candidates.append((
                count_candidate_score(sentence),
                int(match.group(1).replace(",", "")),
                sentence[:700],
            ))

        for match in UNITS_PATTERN.finditer(sentence):
            unit_candidates.append((
                unit_candidate_score(sentence),
                int(match.group(1).replace(",", "")),
                sentence[:700],
            ))

    volume, volume_score, volume_evidence = best_metric_candidate(money_candidates, 6)
    deals, deals_score, deals_evidence = best_metric_candidate(deal_candidates, 6)
    units, units_score, units_evidence = best_metric_candidate(unit_candidates, 7)

    accepted_scores = [score for value, score in ((volume, volume_score), (deals, deals_score), (units, units_score)) if value is not None]
    overall_confidence = (
        "High" if accepted_scores and min(accepted_scores) >= 9
        else "Medium" if accepted_scores
        else "Low"
    )

    return {
        "detected_volume_usd": volume or "",
        "volume_confidence": confidence_from_score(volume_score) if volume else "Low",
        "volume_evidence": volume_evidence,
        "detected_deal_count": deals or "",
        "deal_count_confidence": confidence_from_score(deals_score) if deals else "Low",
        "deal_count_evidence": deals_evidence,
        "detected_units": units or "",
        "units_confidence": confidence_from_score(units_score) if units else "Low",
        "units_evidence": units_evidence,
        "extraction_confidence": overall_confidence,
        "evidence_snippet": " | ".join(
            evidence for evidence in (volume_evidence, deals_evidence, units_evidence) if evidence
        )[:1800],
    }


def html_to_text(raw_html: str) -> tuple[str, str]:
    soup = BeautifulSoup(raw_html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()
    title = clean(soup.title.get_text(" ", strip=True) if soup.title else "")
    body = clean(html.unescape(soup.get_text(" ", strip=True)))
    return title, body


def fetch_requests(url: str) -> dict[str, Any]:
    try:
        response = requests.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        response.raise_for_status()
        title, body = html_to_text(response.text)
        if len(body) < 250:
            raise ValueError("Page returned too little readable text")
        return {"method": "requests", "status": response.status_code, "final_url": response.url,
                "title": title, "body": body, "error": ""}
    except Exception as exc:
        return {"method": "requests", "status": "", "final_url": url,
                "title": "", "body": "", "error": clean(exc)}


def fetch_playwright(url: str) -> dict[str, Any]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {"method": "playwright", "status": "", "final_url": url,
                "title": "", "body": "", "error": "Playwright is not installed"}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=REQUEST_HEADERS["User-Agent"], viewport={"width": 1440, "height": 1000})
            response = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)
            title = clean(page.title())
            body = clean(page.locator("body").inner_text(timeout=15000))
            final_url = page.url
            status = response.status if response else ""
            browser.close()
        if len(body) < 250:
            raise ValueError("Browser returned too little readable text")
        return {"method": "playwright", "status": status, "final_url": final_url,
                "title": title, "body": body, "error": ""}
    except Exception as exc:
        return {"method": "playwright", "status": "", "final_url": url,
                "title": "", "body": "", "error": clean(exc)}


def fetch_profile(url: str) -> dict[str, Any]:
    first = fetch_requests(url)
    if first["body"]:
        return first
    second = fetch_playwright(url)
    if second["body"]:
        second["error"] = first["error"]
        return second
    second["error"] = " | ".join(x for x in (first["error"], second["error"]) if x)
    return second


def token_in_text(value: str, text: str) -> bool:
    needle = normalized(value)
    return bool(needle and needle in normalized(text))


def company_matches(company: str, text: str, final_url: str) -> bool:
    aliases = {
        "cushman & wakefield": ["cushman wakefield", "cushwake"],
        "newmark": ["newmark", "nmrk"],
        "jll": ["jll", "jones lang lasalle"],
        "cbre": ["cbre"],
        "walker & dunlop": ["walker dunlop", "walkerdunlop"],
    }
    combined = normalized(f"{text} {urlparse(final_url).netloc}")
    return any(normalized(alias) in combined for alias in aliases.get(company.casefold(), [company]))


def verify_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    profile_url = clean(candidate.get("website") or candidate.get("source_url"))
    result = fetch_profile(profile_url)
    text = result["body"]

    name_found = token_in_text(clean(candidate.get("name")), text)
    company_found = company_matches(clean(candidate.get("company")), text, result["final_url"]) if text else False
    title_found = token_in_text(clean(candidate.get("title")), text)

    if not text:
        status = "Fetch Failed"
    elif name_found and company_found:
        status = "Verified"
    elif name_found:
        status = "Needs Review - Company Not Confirmed"
    else:
        status = "Needs Review - Name Not Found"

    flags = []
    if text and not company_found:
        flags.append("company_not_confirmed")
    if text and not title_found:
        flags.append("seed_title_not_found")
    if result["final_url"] and result["final_url"] != profile_url:
        flags.append("url_redirected")

    metrics = extract_metrics(text) if text else {
        "detected_volume_usd": "",
        "volume_confidence": "Low",
        "volume_evidence": "",
        "detected_deal_count": "",
        "deal_count_confidence": "Low",
        "deal_count_evidence": "",
        "detected_units": "",
        "units_confidence": "Low",
        "units_evidence": "",
        "extraction_confidence": "Low",
        "evidence_snippet": "",
    }

    return {
        "name": clean(candidate.get("name")),
        "company": clean(candidate.get("company")),
        "seed_title": clean(candidate.get("title")),
        "seed_city": clean(candidate.get("city")),
        "market": clean(candidate.get("market")),
        "profile_url": profile_url,
        "final_url": result["final_url"],
        "verification_status": status,
        "profile_active": "Yes" if bool(text) else "No",
        "name_found": "Yes" if name_found else "No",
        "company_found": "Yes" if company_found else "No",
        "seed_title_found": "Yes" if title_found else "No",
        "change_detected": "Yes" if flags else "No",
        "change_flags": ", ".join(flags),
        "fetch_method": result["method"],
        "http_status": result["status"],
        "page_title": result["title"],
        **metrics,
        "verified_date": date.today().isoformat(),
        "fetch_error": result["error"],
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify and enrich official CRE broker profiles")
    parser.add_argument("--market", default=DEFAULT_MARKET, choices=sorted(MARKETS))
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()
    candidates = [c for c in MANUAL_CANDIDATES if candidate_matches_market(c, args.market)]
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"verified_profiles_{args.market}_{date.today().isoformat()}.csv"

    rows = []
    print(f"[market] {args.market}")
    print(f"[verify] checking {len(candidates)} official profiles")

    for index, candidate in enumerate(candidates, start=1):
        print(f"[{index}/{len(candidates)}] {candidate['name']} — {candidate['company']}")
        row = verify_candidate(candidate)
        rows.append(row)
        print(f"    {row['verification_status']} via {row['fetch_method']} | "
              f"volume={row['detected_volume_usd'] or 'none'} | deals={row['detected_deal_count'] or 'none'}")
        time.sleep(DELAY_SECONDS)

    fieldnames = list(rows[0].keys()) if rows else []
    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    verified = sum(r["verification_status"] == "Verified" for r in rows)
    review = sum(r["verification_status"].startswith("Needs Review") for r in rows)
    failed = sum(r["verification_status"] == "Fetch Failed" for r in rows)
    print(f"\nWrote {len(rows)} rows to {output_path}")
    print(f"Verified: {verified} | Needs review: {review} | Fetch failed: {failed}")
    print("Detected figures remain review candidates until approved for scoring.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

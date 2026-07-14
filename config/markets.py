"""Market definitions for the CRE recruiting platform."""

MARKETS = {
    "charlotte-raleigh": {
        "display_name": "Charlotte + Raleigh",
        "aliases": [
            "Charlotte + Raleigh",
            "Charlotte",
            "Raleigh",
            "Raleigh-Durham",
        ],
        "cities": [
            "Charlotte",
            "Raleigh",
            "Durham",
            "Raleigh-Durham",
            "Cary",
            "Chapel Hill",
        ],
        "keywords": [
            "charlotte",
            "raleigh",
            "durham",
            "research triangle",
            "north carolina",
            "carolinas",
        ],
    },

    "atlanta": {
        "display_name": "Atlanta",
        "aliases": ["Atlanta"],
        "cities": ["Atlanta"],
        "keywords": [
            "atlanta",
            "georgia",
        ],
    },

    "florida": {
        "display_name": "Florida",
        "aliases": ["Florida"],
        "cities": [
            "Miami",
            "Fort Lauderdale",
            "West Palm Beach",
            "Orlando",
            "Tampa",
            "Jacksonville",
        ],
        "keywords": [
            "florida",
            "miami",
            "fort lauderdale",
            "west palm beach",
            "orlando",
            "tampa",
            "jacksonville",
            "south florida",
        ],
    },

    "richmond": {
        "display_name": "Richmond",
        "aliases": ["Richmond"],
        "cities": ["Richmond"],
        "keywords": [
            "richmond",
            "virginia",
        ],
    },

    "dmv": {
        "display_name": "DMV",
        "aliases": ["DMV", "Washington DC"],
        "cities": [
            "Washington",
            "Washington, DC",
            "Bethesda",
            "Arlington",
            "Alexandria",
            "Tysons",
        ],
        "keywords": [
            "washington dc",
            "washington, dc",
            "district of columbia",
            "maryland",
            "northern virginia",
            "arlington",
            "alexandria",
            "bethesda",
            "tysons",
        ],
    },

    "boston": {
        "display_name": "Boston",
        "aliases": ["Boston"],
        "cities": ["Boston", "Cambridge"],
        "keywords": [
            "boston",
            "cambridge",
            "massachusetts",
            "greater boston",
        ],
    },

    "nashville": {
        "display_name": "Nashville",
        "aliases": ["Nashville"],
        "cities": ["Nashville", "Brentwood", "Murfreesboro", "Antioch"],
        "keywords": [
            "nashville",
            "brentwood",
            "tennessee",
            "murfreesboro",
        ],
    },
}


DEFAULT_MARKET = "charlotte-raleigh"


def get_market(market_slug):
    if market_slug not in MARKETS:
        valid = ", ".join(sorted(MARKETS))
        raise ValueError(
            f"Unknown market '{market_slug}'. Valid markets: {valid}"
        )

    return MARKETS[market_slug]


def candidate_matches_market(candidate, market_slug):
    market_config = get_market(market_slug)

    candidate_market = str(candidate.get("market", "")).strip().lower()
    candidate_city = str(candidate.get("city", "")).strip().lower()

    aliases = {
        value.lower()
        for value in market_config["aliases"]
    }

    cities = {
        value.lower()
        for value in market_config["cities"]
    }

    return (
        candidate_market in aliases
        or candidate_city in cities
    )

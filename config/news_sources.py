"""
Config for the news monitor - official RSS feeds only (no scraping, no ToS issues).

Connect CRE explicitly publishes these feeds for exactly this kind of consumption
(their RSS directory page even invites it: https://www.connectcre.com/rss-info/).
GlobeSt does the same via their public feed list: https://www.globest.com/rss/
"""

RSS_FEEDS = [
    {
        "source": "Connect CRE - Carolinas",
        "url": "https://www.connectcre.com/feed?story-market=carolinas",
        # This feed is already scoped to the Carolinas by Connect CRE itself,
        # so we don't need to ALSO require a city keyword match - that was
        # throwing away legitimate articles that just said "Carolinas" or
        # named a metro without repeating "Charlotte"/"Raleigh" verbatim.
        "market_prefiltered": True,
    },
    {
        "source": "Connect CRE - Apartments (national)",
        "url": "https://www.connectcre.com/feed?property-sector=apartments",
        "market_prefiltered": False,  # national feed - still need the city check
    },
    {
        "source": "GlobeSt - Multifamily",
        "url": "https://feeds.feedblitz.com/globest/multifamily",  # https, not http
        "market_prefiltered": False,
    },
    {
        "source": "GlobeSt - Southeast",
        "url": "https://feeds.feedblitz.com/globest/southeast",  # https, not http
        "market_prefiltered": False,  # regional but broader than just Charlotte/Raleigh
    },
]

# Market keywords - an article must mention at least one of these to be relevant
# to the Charlotte + Raleigh market (the national feeds above are noisy otherwise).
MARKET_KEYWORDS = [
    "charlotte", "raleigh", "durham", "chapel hill", "cary", "fuquay-varina",
    "carolinas", "north carolina", "research triangle", "rdu",
]

# Companies we're tracking for this market (keep in sync with the workbook).
# NOTE: Northmarq intentionally excluded - that's us, not a recruiting target.
TARGET_COMPANIES = [
    "CBRE", "Newmark", "Walker & Dunlop", "Cushman & Wakefield", "Colliers",
    "JLL", "Marcus & Millichap", "Institutional Property Advisors", "IPA",
    "Berkadia", "Capstone",
]

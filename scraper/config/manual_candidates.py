"""Manually verified high-priority recruiting candidates.

Use this for firms whose public websites block automated requests or do not
provide a stable roster page. Every entry should be supported by an official
company profile or another reliable public source.
"""

from datetime import date


MANUAL_CANDIDATES = [
    {
        "name": "Dean Smith",
        "company": "Newmark",
        "title": "Vice Chairman, Multifamily Capital Markets",
        "city": "Charlotte",
        "market": "Charlotte + Raleigh",
        "website": "https://www.nmrk.com/people/dean-smith",
        "source_url": "https://www.nmrk.com/people/dean-smith",
        "scraped_date": date.today().isoformat(),
    },
    {
        "name": "John Heimburger",
        "company": "Newmark",
        "title": "Vice Chairman, Multifamily Capital Markets",
        "city": "Charlotte",
        "market": "Charlotte + Raleigh",
        "website": "https://www.nmrk.com/people/john-heimburger",
        "source_url": "https://www.nmrk.com/people/john-heimburger",
        "scraped_date": date.today().isoformat(),
    },
    {
        "name": "Jason Kon",
        "company": "Newmark",
        "title": "Senior Managing Director, Multifamily Capital Markets",
        "city": "Charlotte",
        "market": "Charlotte + Raleigh",
        "website": "https://www.nmrk.com/people/jason-kon",
        "source_url": "https://www.nmrk.com/people/jason-kon",
        "scraped_date": date.today().isoformat(),
    },
    {
        "name": "Sean Wood",
        "company": "Newmark",
        "title": "Vice Chairman, Multifamily Capital Markets",
        "city": "Raleigh-Durham",
        "market": "Charlotte + Raleigh",
        "website": "https://www.nmrk.com/people/sean-wood",
        "source_url": "https://www.nmrk.com/people/sean-wood",
        "scraped_date": date.today().isoformat(),
    },
    {
        "name": "John Munroe",
        "company": "Newmark",
        "title": "Senior Managing Director, Multifamily Capital Markets",
        "city": "Raleigh-Durham",
        "market": "Charlotte + Raleigh",
        "website": "https://www.nmrk.com/people/john-munroe",
        "source_url": "https://www.nmrk.com/people/john-munroe",
        "scraped_date": date.today().isoformat(),
    },
]

"""Census Bureau population estimates by county and state (latest vintage).

Used only as a denominator: Library tickets per 100,000 residents by state and
by feeder metro, so big metros stop looking strong just for being big. The
Population Estimates Program flat file needs no API key (the ACS API now
does). Updated once a year; the URL names the vintage, so bump
`population.url` when the next one posts (usually March).

Output: data/population.csv (level, state_fips, county_fips, state, county, year, population)
"""
from __future__ import annotations

import io
import sys

import pandas as pd
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

ABBR = {"Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS", "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK", "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY"}


def main() -> int:
    url = CONFIG.get("population", {})["url"]
    r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.BytesIO(r.content), encoding="latin-1", dtype={"STATE": str, "COUNTY": str})
    popcol = sorted(c for c in df.columns if c.startswith("POPESTIMATE") and c[-4:].isdigit())[-1]
    year = int(popcol[-4:])
    out = pd.DataFrame({
        "level": df["SUMLEV"].map({40: "state", 50: "county"}),
        "state_fips": df["STATE"], "county_fips": df["STATE"] + df["COUNTY"],
        "state": df["STNAME"].map(ABBR), "county": df["CTYNAME"].str.replace(r" (County|Parish|Borough|Census Area|Municipality|city)$", "", regex=True),
        "year": year, "population": df[popcol].astype(int),
    })
    out = out[out["level"].notna() & out["state"].notna()]
    if out.empty:
        print("no population rows", file=sys.stderr)
        return 1
    write_csv(out, "population.csv")
    update_manifest("population", latest=str(year), rows=len(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Census Bureau Monthly State Retail Sales (experimental): year-over-year
percent change in retail sales by state and 3-digit NAICS, ~2-month lag.
Published as growth rates only (no dollar levels). Kept for ND, the
neighbouring states and the U.S. as a statewide retail control next to the
corridor tax series. NAICS 447 (gasoline stations) and 445 (grocery) are the
travel-sensitive lines; there is no food-services (722) line in this product.

Output: data/census_msrs_yoy.csv (state, naics, year, month, yoy_pct)
"""
from __future__ import annotations

import io
import sys

import pandas as pd
import requests

from common import USER_AGENT, update_manifest, write_csv

URL = "https://www.census.gov/retail/mrts/www/statedata/state_retail_yy.csv"
STATES = ["ND", "SD", "MT", "MN", "WY", "USA"]
NAICS = {"TOTAL": "Total retail", "445": "Food & beverage stores", "447": "Gasoline stations", "452": "General merchandise", "453": "Miscellaneous store retailers", "441": "Motor vehicle & parts", "448": "Clothing"}


def main() -> int:
    r = requests.get(URL, headers={"User-Agent": USER_AGENT + " Mozilla/5.0"}, timeout=120)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    df["stateabbr"] = df["stateabbr"].str.strip()
    df["naics"] = df["naics"].str.strip()
    df = df[df["stateabbr"].isin(STATES) & df["naics"].isin(NAICS)]
    long = df.melt(id_vars=["stateabbr", "naics"], value_vars=[c for c in df.columns if c.startswith("yy")], var_name="period", value_name="yoy_pct")
    long["yoy_pct"] = pd.to_numeric(long["yoy_pct"].str.strip().replace({"(S)": None, "S": None}), errors="coerce")
    long = long.dropna(subset=["yoy_pct"])
    long["year"] = long["period"].str[2:6].astype(int)
    long["month"] = long["period"].str[6:8].astype(int)
    long["sector"] = long["naics"].map(NAICS)
    out = long.rename(columns={"stateabbr": "state"})[["state", "naics", "sector", "year", "month", "yoy_pct"]].sort_values(["state", "naics", "year", "month"])
    write_csv(out, "census_msrs_yoy.csv")
    latest = out.sort_values(["year", "month"]).iloc[-1]
    update_manifest("census_msrs", latest=f"{int(latest.year)}-{int(latest.month):02d}", states=STATES)
    return 0


if __name__ == "__main__":
    sys.exit(main())

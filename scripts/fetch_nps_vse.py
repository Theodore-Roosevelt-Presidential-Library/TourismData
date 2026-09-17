"""NPS Visitor Spending Effects (VSE): annual economic contribution of park
visitors to the gateway region, per park, from the IRMA VSE web API that
powers nps.gov's VSE data visualization (https://irmaservices.nps.gov/vseapi/,
Swagger at /swagger/v1/swagger.json). Each park-year returns visitor
spending, jobs, labor income, value added and economic output by sector
(lodging, restaurants, gas, groceries, retail, recreation, transportation,
camping, secondary effects), plus visits and party-days.

Parks come from `nps_parks` in config. Years from `vse_since` (default 2012)
to the latest that responds (the API returns 500 for a year not yet
published; the report usually lands in late spring for the prior year).

Output: data/nps_vse_annual.csv (park, year, category, sector, value)
"""
from __future__ import annotations

import sys
import time
from datetime import date

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

API = "https://irmaservices.nps.gov/vseapi/"
HEADERS = {"User-Agent": USER_AGENT, "Accept": "application/json"}


def park_year(code: str, year: int) -> list[dict] | None:
    r = requests.get(API + f"park-result/{code}/getResults", params={"year": year}, headers=HEADERS, timeout=90)
    if r.status_code == 500:
        return None
    r.raise_for_status()
    d = r.json().get("data") or {}
    rows = []
    for c in d.get("categories", []):
        for s in c.get("sectors", []):
            rows.append({"park": code, "year": year, "category": c["category"], "sector": s.get("sector_name") or "Total", "value": float(s["value"]) if s.get("value") is not None else None})
    return rows


def main() -> int:
    since = int(CONFIG.get("vse_since", 2012))
    out = DATA / "nps_vse_annual.csv"
    existing = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["park", "year", "category", "sector", "value"])
    frames, latest = [], {}
    for park in CONFIG["nps_parks"]:
        code = park["code"]
        have = set(existing[existing["park"] == code]["year"].unique())
        for y in range(since, date.today().year + 1):
            # Re-pull the two most recent published years (they get revised); skip older ones we already have.
            if y in have and y < max(have) - 1:
                continue
            try:
                rows = park_year(code, y)
            except Exception as e:  # noqa: BLE001
                print(f"{code} {y}: {e}", file=sys.stderr)
                continue
            if rows is None:
                continue
            if rows:
                frames.append(pd.DataFrame(rows))
                latest[code] = y
            time.sleep(0.3)
        print(f"{code}: through {latest.get(code, max(have) if have else None)}")
    if not frames and not len(existing):
        return 1
    df = pd.concat([existing, *frames]).drop_duplicates(["park", "year", "category", "sector"], keep="last").sort_values(["park", "year", "category", "sector"])
    write_csv(df, "nps_vse_annual.csv")
    update_manifest("nps_vse", latest_year={k: int(v) for k, v in latest.items()}, parks=len(CONFIG["nps_parks"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

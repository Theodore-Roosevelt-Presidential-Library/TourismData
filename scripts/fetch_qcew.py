"""Pull county employment in tourism-facing sectors from BLS QCEW.

The QCEW open-data slices need no API key:
  https://data.bls.gov/cew/data/api/{year}/{qtr}/area/{area_fips}.csv

For each configured county we keep private-ownership rows for:
  1026  Leisure and hospitality (supersector)  - always disclosed for our counties
  72    Accommodation and food services         - suppressed for Billings (too few employers)
  721   Accommodation
  722   Food services and drinking places
  10    Total, all industries

Employment is the monthly count of jobs (month1/2/3 of the quarter); wages
are quarterly totals. About a five-month lag after quarter end.

Output: data/qcew_county_quarterly.csv
        (county, fips, industry_code, industry, year, quarter, establishments,
         emp_month1, emp_month2, emp_month3, avg_employment, total_wages, suppressed)
"""
from __future__ import annotations

import io
import sys
import time

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

URL = "https://data.bls.gov/cew/data/api/{year}/{qtr}/area/{fips}.csv"
INDUSTRIES = {"10": "Total, all industries", "1026": "Leisure and hospitality", "72": "Accommodation and food services", "721": "Accommodation", "722": "Food services and drinking places"}


def main() -> int:
    counties = CONFIG.get("qcew_counties", {})
    since = int(CONFIG.get("qcew_since", 2015))
    path = DATA / "qcew_county_quarterly.csv"
    existing = pd.read_csv(path, dtype={"fips": str, "industry_code": str}) if path.exists() else pd.DataFrame()
    have = set(zip(existing["fips"], existing["year"], existing["quarter"])) if len(existing) else set()
    today = pd.Timestamp.today()
    rows, missing = [], []
    for fips, county in counties.items():
        for year in range(since, today.year + 1):
            for qtr in (1, 2, 3, 4):
                if (fips, year, qtr) in have:
                    continue
                if pd.Timestamp(year=year, month=3 * qtr, day=1) + pd.DateOffset(months=6) > today:
                    continue  # not yet published
                try:
                    r = requests.get(URL.format(year=year, qtr=qtr, fips=fips), headers={"User-Agent": USER_AGENT}, timeout=60)
                    if r.status_code != 200:
                        missing.append(f"{fips}-{year}Q{qtr}")
                        continue
                    df = pd.read_csv(io.StringIO(r.text), dtype={"industry_code": str, "disclosure_code": str})
                    df = df[(df["own_code"] == 5) & (df["industry_code"].isin(INDUSTRIES))]
                    for _, x in df.iterrows():
                        supp = str(x.get("disclosure_code", "")).strip() == "N"
                        rows.append(
                            {
                                "county": county, "fips": fips, "industry_code": x["industry_code"], "industry": INDUSTRIES[x["industry_code"]],
                                "year": year, "quarter": qtr, "establishments": int(x["qtrly_estabs"]),
                                "emp_month1": None if supp else int(x["month1_emplvl"]), "emp_month2": None if supp else int(x["month2_emplvl"]), "emp_month3": None if supp else int(x["month3_emplvl"]),
                                "avg_employment": None if supp else round((x["month1_emplvl"] + x["month2_emplvl"] + x["month3_emplvl"]) / 3, 1),
                                "total_wages": None if supp else int(x["total_qtrly_wages"]), "suppressed": supp,
                            }
                        )
                except Exception as e:  # noqa: BLE001
                    print(f"FAILED {county} {year}Q{qtr}: {e}", file=sys.stderr)
                    missing.append(f"{fips}-{year}Q{qtr}")
                time.sleep(0.3)
        print(f"{county}: done")
    df = pd.concat([existing, pd.DataFrame(rows)]) if rows else existing
    if not len(df):
        return 1
    df = df.drop_duplicates(["fips", "industry_code", "year", "quarter"], keep="last").sort_values(["county", "industry_code", "year", "quarter"])
    write_csv(df, "qcew_county_quarterly.csv")
    last = df.sort_values(["year", "quarter"]).iloc[-1]
    update_manifest("qcew_county_quarterly", rows=len(df), latest_quarter=f"{int(last.year)} Q{int(last.quarter)}", missing=missing[-10:])
    return 0


if __name__ == "__main__":
    sys.exit(main())

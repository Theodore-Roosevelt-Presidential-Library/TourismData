"""BLS Current Employment Statistics (state and metro): monthly payroll jobs
in leisure & hospitality and its accommodation-and-food-services and
arts/recreation components, North Dakota statewide and the Bismarck MSA.
Not seasonally adjusted (so the seasonal chart pattern applies), ~1-month
lag, latest month preliminary. The statewide benchmark for the county QCEW
and LAUS series. Same flat-file source and user-agent rule as LAUS.

Output: data/ces_monthly.csv (area, series, year, month, jobs_thousands, prelim)
"""
from __future__ import annotations

import io
import sys

import pandas as pd
import requests

from common import CONFIG, update_manifest, write_csv
from fetch_laus import HEADERS

URL = "https://download.bls.gov/pub/time.series/sm/sm.data.35.NorthDakota"
SERIES = {
    "SMU38000007000000001": ("North Dakota", "Leisure & hospitality"),
    "SMU38000007072000001": ("North Dakota", "Accommodation & food services"),
    "SMU38000007071000001": ("North Dakota", "Arts, entertainment & recreation"),
    "SMU38000007072100001": ("North Dakota", "Accommodation"),
    "SMU38000007072200001": ("North Dakota", "Food services & drinking places"),
    "SMU38000000000000001": ("North Dakota", "Total nonfarm"),
    "SMU38139007000000001": ("Bismarck MSA", "Leisure & hospitality"),
    "SMU38139007072000001": ("Bismarck MSA", "Accommodation & food services"),
}


def main() -> int:
    since = int(CONFIG.get("laus_since", 2015))
    r = requests.get(URL, headers=HEADERS, timeout=300)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["series_id"] = df["series_id"].str.strip()
    df = df[df["series_id"].isin(SERIES) & df["period"].str.startswith("M") & (df["period"] != "M13")].copy()
    df["year"] = df["year"].astype(int)
    df = df[df["year"] >= since]
    df["month"] = df["period"].str[1:].astype(int)
    df["jobs_thousands"] = pd.to_numeric(df["value"], errors="coerce")
    df["prelim"] = df["footnote_codes"].fillna("").str.contains("P")
    df["area"] = df["series_id"].map(lambda s: SERIES[s][0])
    df["series"] = df["series_id"].map(lambda s: SERIES[s][1])
    out = df[["area", "series", "year", "month", "jobs_thousands", "prelim"]].sort_values(["area", "series", "year", "month"])
    if out.empty:
        print("no CES rows", file=sys.stderr)
        return 1
    write_csv(out, "ces_monthly.csv")
    latest = out.sort_values(["year", "month"]).iloc[-1]
    update_manifest("ces", latest=f"{int(latest.year)}-{int(latest.month):02d}", series=len(SERIES))
    return 0


if __name__ == "__main__":
    sys.exit(main())

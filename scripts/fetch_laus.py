"""BLS Local Area Unemployment Statistics (LAUS): monthly county labor force.

Job Service ND publishes the same numbers, but BLS's flat file is the clean
source: county employment, labor force and unemployment rate, monthly, about
one month after the reference month (vs ~5 months for QCEW). Counties come
from `qcew_counties` in config. We read the North Dakota slice of the LAUS
time-series database (`la.data.41.NorthDakota`, ~7 MB, refreshed with each
release) rather than the public API, whose unregistered daily quota is
shared per IP and easily exhausted.

LAUS county employment is a household-survey model estimate (residents who
are employed), not jobs at establishments, so it is a read on the local
labor market rather than a count of tourism jobs; QCEW remains the
industry-level series.

Output: data/laus_counties_monthly.csv
        (fips, county, year, month, employment, labor_force, unemployment_rate, prelim)
"""
from __future__ import annotations

import io
import os
import sys

import pandas as pd
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

URL = "https://download.bls.gov/pub/time.series/la/la.data.41.NorthDakota"
MEASURES = {"05": "employment", "06": "labor_force", "03": "unemployment_rate"}
# download.bls.gov's access policy requires a browser-style user agent that carries a contact
# e-mail; requests without one get 403. Set BLS_CONTACT to a monitored address.
CONTACT = os.environ.get("BLS_CONTACT", "tourismdata@trlibrary.com")  # BLS rejects noreply-style addresses
HEADERS = {"User-Agent": f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36 (TRPL-TourismData; {CONTACT})"}


def main() -> int:
    counties: dict[str, str] = CONFIG.get("qcew_counties", {})
    since = int(CONFIG.get("laus_since", 2015))
    r = requests.get(URL, headers=HEADERS, timeout=300)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), sep="\t", dtype=str)
    df.columns = [c.strip() for c in df.columns]
    df["series_id"] = df["series_id"].str.strip()
    want = {f"LAUCN{f}00000000{m}": (f, meas) for f in counties for m, meas in MEASURES.items()}
    df = df[df["series_id"].isin(want)].copy()
    df = df[df["period"].str.startswith("M") & (df["period"] != "M13")]
    df["year"] = df["year"].astype(int)
    df = df[df["year"] >= since]
    df["month"] = df["period"].str[1:].astype(int)
    df["fips"] = df["series_id"].map(lambda s: want[s][0])
    df["measure"] = df["series_id"].map(lambda s: want[s][1])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["prelim"] = df["footnote_codes"].fillna("").str.contains("P")
    wide = df.pivot_table(index=["fips", "year", "month"], columns="measure", values="value").reset_index()
    prelim = df[df["measure"] == "employment"].set_index(["fips", "year", "month"])["prelim"]
    wide["prelim"] = [bool(prelim.get((f, y, m), False)) for f, y, m in zip(wide["fips"], wide["year"], wide["month"])]
    wide["county"] = wide["fips"].map(counties)
    wide = wide[["fips", "county", "year", "month", "employment", "labor_force", "unemployment_rate", "prelim"]].sort_values(["county", "year", "month"])
    if wide.empty:
        print("no LAUS rows matched", file=sys.stderr)
        return 1
    write_csv(wide, "laus_counties_monthly.csv")
    latest = wide.sort_values(["year", "month"]).iloc[-1]
    update_manifest("laus", counties=len(counties), latest=f"{int(latest.year)}-{int(latest.month):02d}", rows=len(wide))
    return 0


if __name__ == "__main__":
    sys.exit(main())

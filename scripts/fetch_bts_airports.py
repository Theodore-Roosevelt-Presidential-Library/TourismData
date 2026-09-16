"""Pull annual airport enplanements from the BTS geodata T-100 feature service.

This is an ANNUAL snapshot (currently CY2024 only). Monthly T-100 segment data
exists but only through the TranStats download form, which has no stable API.
TODO: script the TranStats form (Table_ID=311) or switch to the FAA CY
enplanement spreadsheets if monthly detail is needed.

Output: data/bts_airports_annual.csv (airport, year, enplanements, passengers, departures)
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

URL = (
    "https://services.arcgis.com/xOi1kZaI0eWDREZv/arcgis/rest/services/"
    "T100_Domestic_Market_and_Segment_Data/FeatureServer/1/query"
)


def main() -> int:
    codes = ",".join(f"'{c}'" for c in CONFIG["bts_airports"])
    r = requests.get(
        URL,
        params={
            "where": f"origin IN ({codes})",
            "outFields": "year,origin,enplanements,passengers,departures",
            "returnGeometry": "false",
            "f": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=90,
    )
    r.raise_for_status()
    feats = r.json().get("features", [])
    if not feats:
        print("no airport rows returned", file=sys.stderr)
        return 1
    df = pd.DataFrame([f["attributes"] for f in feats]).rename(columns={"origin": "airport"})
    df = df[["airport", "year", "enplanements", "passengers", "departures"]].sort_values(["airport", "year"])
    write_csv(df, "bts_airports_annual.csv")
    update_manifest("bts_airports_annual", rows=len(df), years=sorted(df["year"].unique().tolist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

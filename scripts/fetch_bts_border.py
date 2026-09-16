"""Pull monthly land-border crossing counts from BTS (Socrata dataset keg4-3bc2).

Port-level monthly counts for every U.S.-Canada land port. We keep ND and MT
ports and the personal-vehicle / bus measures. BTS says roughly a six-month
lag; in practice the feed has run 1-2 months behind.

Output: data/bts_border_monthly.csv (port, state, port_code, date, measure, value)
"""
from __future__ import annotations

import sys

import pandas as pd
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

URL = "https://data.bts.gov/resource/keg4-3bc2.json"


def main() -> int:
    cfg = CONFIG["bts_border"]
    states = ",".join(f"'{s}'" for s in cfg["states"])
    measures = ",".join(f"'{m}'" for m in cfg["measures"])
    where = f"state in({states}) AND measure in({measures}) AND date >= '{cfg['since']}T00:00:00'"
    rows, offset, page = [], 0, 5000
    while True:
        r = requests.get(
            URL,
            params={"$where": where, "$limit": page, "$offset": offset, "$order": "date,port_name"},
            headers={"User-Agent": USER_AGENT},
            timeout=90,
        )
        r.raise_for_status()
        batch = r.json()
        rows.extend(batch)
        if len(batch) < page:
            break
        offset += page
    if not rows:
        print("no border rows returned", file=sys.stderr)
        return 1
    df = pd.DataFrame(rows)[["port_name", "state", "port_code", "date", "measure", "value"]]
    df = df.rename(columns={"port_name": "port"})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-01")
    df["value"] = df["value"].astype(int)
    df = df.sort_values(["state", "port", "measure", "date"])
    write_csv(df, "bts_border_monthly.csv")
    update_manifest("bts_border_monthly", rows=len(df), latest_month=df["date"].max()[:7])
    return 0


if __name__ == "__main__":
    sys.exit(main())

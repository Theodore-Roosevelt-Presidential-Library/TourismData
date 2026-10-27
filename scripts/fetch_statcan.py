"""Statistics Canada frontier counts for the prairie provinces (table 24-10-0053-01).

"International travellers entering or returning to Canada, by type of
transportation and traveller type", monthly by province of entry. We keep
Saskatchewan, Manitoba and Alberta (the provinces whose ports face North
Dakota and Montana) and two series:

  * Canadian residents returning from the U.S. by automobile — the Canadian-side
    mirror of the BTS border card: how many prairie Canadians drove south and
    came home that month (all travellers and the overnight subset).
  * U.S. residents entering Canada by automobile — the reverse flow, for context.

Read through StatCan's Web Data Service, no key needed. About a two-month lag.

Output: data/statcan_frontier_monthly.csv (province, series, traveller_type, year, month, value)
"""
from __future__ import annotations

import sys
from datetime import date

import pandas as pd
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

WDS = "https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods"


def main() -> int:
    cfg = CONFIG.get("statcan", {})
    pid = int(cfg.get("table", 24100053))
    since = int(cfg.get("since", 2015))
    n = (date.today().year - since + 1) * 12
    req, meta = [], []
    for geo, prov in cfg["provinces"].items():
        for ser, label in cfg["series"].items():
            for typ, tlabel in cfg["types"].items():
                req.append({"productId": pid, "coordinate": f"{geo}.{ser}.{typ}.0.0.0.0.0.0.0", "latestN": n})
                meta.append((prov, label, tlabel))
    r = requests.post(WDS, json=req, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    rows = []
    for (prov, label, tlabel), x in zip(meta, r.json()):
        if x.get("status") != "SUCCESS":
            print(f"FAILED {prov} {label} {tlabel}: {x.get('object')}", file=sys.stderr)
            continue
        for p in x["object"]["vectorDataPoint"]:
            if p.get("value") is None:
                continue
            y, m = int(p["refPer"][:4]), int(p["refPer"][5:7])
            if y >= since:
                rows.append({"province": prov, "series": label, "traveller_type": tlabel, "year": y, "month": m, "value": int(p["value"])})
    if not rows:
        return 1
    df = pd.DataFrame(rows).sort_values(["province", "series", "traveller_type", "year", "month"])
    write_csv(df, "statcan_frontier_monthly.csv")
    last = df.sort_values(["year", "month"]).iloc[-1]
    update_manifest("statcan", latest=f"{int(last.year)}-{int(last.month):02d}", rows=len(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())

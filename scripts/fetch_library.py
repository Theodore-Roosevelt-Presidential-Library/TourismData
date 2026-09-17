"""Library admissions and visitor origin, from the TRPL Marketing Dashboard's
published ACME extract.

We do NOT call ACME here. The Dashboard repo
(Theodore-Roosevelt-Presidential-Library/Dashboard) already runs the ACME
Reporting API nightly and commits `data/latest/acme.json` with daily
series back two years. This script reads that file from one of:

  1. DASHBOARD_LOCAL   - path to a local clone (e.g. ~/Documents/GitHub/Dashboard)
  2. DASHBOARD_TOKEN   - a GitHub token with read access to the private
                         Dashboard repo; the file is read via the contents API

and writes tidy CSVs. `visitors` = checked-in scans (the Dashboard's
authoritative attendance); `tickets` = tickets sold. The Dashboard records
which source produced `visitors` in `visitors_source`; anything other than
"checked_in" is carried into the manifest and shown on the page.

Outputs: data/library_daily.csv
           (date, visitors, tickets, revenue, orders, tickets_online, tickets_pos,
            general_admission, walk_up, other)
         data/library_origin_states.csv (as_of, state, visitors, share)
"""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests

from common import USER_AGENT, update_manifest, write_csv

REPO = "Theodore-Roosevelt-Presidential-Library/Dashboard"
PATH = "data/latest/acme.json"


def load() -> dict:
    local = os.environ.get("DASHBOARD_LOCAL")
    if local and (Path(local) / PATH).exists():
        return json.loads((Path(local) / PATH).read_text())
    token = os.environ.get("DASHBOARD_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("set DASHBOARD_LOCAL (path to a Dashboard clone) or DASHBOARD_TOKEN (GitHub token with read access)")
    r = requests.get(
        f"https://api.github.com/repos/{REPO}/contents/{PATH}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": USER_AGENT},
        timeout=120,
    )
    r.raise_for_status()
    j = r.json()
    if j.get("encoding") == "base64":
        return json.loads(base64.b64decode(j["content"]))
    # Files over 1 MB come back without content; use download_url
    return requests.get(j["download_url"], headers={"Authorization": f"Bearer {token}", "User-Agent": USER_AGENT}, timeout=120).json()


def main() -> int:
    d = load()
    daily = d.get("daily", {})
    dates = daily.get("dates", [])
    if not dates:
        print("no daily series in acme.json", file=sys.stderr)
        return 1
    cat = d.get("daily_by_category", {})
    df = pd.DataFrame(
        {
            "date": dates,
            "visitors": daily.get("visitors", [None] * len(dates)),
            "tickets": daily.get("tickets", [None] * len(dates)),
            "revenue": daily.get("revenue", [None] * len(dates)),
            "orders": daily.get("orders", [None] * len(dates)),
            "tickets_online": daily.get("tickets_online", [None] * len(dates)),
            "tickets_pos": daily.get("tickets_pos", [None] * len(dates)),
            "general_admission": cat.get("general_admission", [None] * len(dates)),
            "walk_up": cat.get("walk_up", [None] * len(dates)),
            "other": cat.get("other", [None] * len(dates)),
        }
    )
    write_csv(df, "library_daily.csv")
    states = d.get("top_states") or (d.get("geo") or {}).get("top_states") or []
    if states:
        tot = sum(s.get("visitors", 0) for s in states) or 1
        sdf = pd.DataFrame([{"as_of": d.get("as_of"), "state": s["state"], "visitors": int(s.get("visitors", 0)), "share": round(s.get("visitors", 0) / tot, 4)} for s in states])
        write_csv(sdf, "library_origin_states.csv")
    update_manifest(
        "library",
        as_of=d.get("as_of"),
        visitors_source=d.get("visitors_source"),
        visitors_ytd=d.get("visitors_ytd"),
        tickets_ytd=d.get("tickets_ytd"),
        first_date=dates[0],
        last_date=dates[-1],
    )
    print(f"library: {dates[0]} .. {dates[-1]}, visitors_source={d.get('visitors_source')}, visitors_ytd={d.get('visitors_ytd')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

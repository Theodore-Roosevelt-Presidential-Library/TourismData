"""International (overseas) visitor arrivals by first intended U.S. state — NTTO I-94.

The National Travel and Tourism Office (Commerce Dept.) publishes a monthly
"Summary & Analysis" workbook from I-94 / ADIS arrivals. Table G.1 gives
arrivals by the state of the visitor's FIRST INTENDED ADDRESS, by world region
of residence (Western Europe, Asia, ... Total Overseas, Mexico excluding land).
Canada and Mexican land arrivals are not in it — the border and StatCan cards
cover the Canadian market.

The program page links only the last few months; older workbooks stay online
at /sites/default/files/<upload YYYY-MM>/<Final|FINAL|Preliminary>_SummaryAnalysis_COR_<Month>_<YYYY>.xlsx,
so missing months are found by trying the likely upload folders. A preliminary
month is replaced when its final file appears.

Caveat printed on the table itself: the first intended address understates
states visited later in a trip — a European landing in Denver and driving to
Medora counts for Colorado. Read North Dakota's numbers as a floor and the
trend as the signal.

Output: data/ntto_i94_state_monthly.csv
        (year, month, state, region, arrivals, status)  status = final | preliminary
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
from datetime import date

import pandas as pd
import requests

from common import CONFIG, DATA, update_manifest, write_csv

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TRPL-TourismData"}
BASE = "https://www.trade.gov/sites/default/files/"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
LINK = re.compile(r'href="([^"]*?(Final|FINAL|final|Preliminary|preliminary)_SummaryAnalysis_COR_([A-Za-z]+)_(\d{4})[^"]*\.xlsx)"')


def page_links(page: str) -> dict[tuple[int, int], tuple[str, str]]:
    out = {}
    for href, kind, mon, yr in LINK.findall(requests.get(page, headers=HEADERS, timeout=60).text):
        if mon.capitalize() not in MONTHS:
            continue
        key = (int(yr), MONTHS.index(mon.capitalize()) + 1)
        status = "final" if kind.lower() == "final" else "preliminary"
        url = href if href.startswith("http") else "https://www.trade.gov" + href
        if key not in out or status == "final":
            out[key] = (url, status)
    return out


def guess(y: int, m: int) -> tuple[str, str] | None:
    for status, prefixes in (("final", ("FINAL", "Final", "final")), ("preliminary", ("Preliminary",))):
        for k in (1, 2, 3, 4, 5):
            uy, um = (y, m + k) if m + k <= 12 else (y + 1, m + k - 12)
            for pre in prefixes:
                url = f"{BASE}{uy}-{um:02d}/{pre}_SummaryAnalysis_COR_{MONTHS[m - 1]}_{y}.xlsx"
                try:
                    if requests.head(url, headers=HEADERS, timeout=30, allow_redirects=True).status_code == 200:
                        return url, status
                except requests.RequestException:
                    pass
    return None


def parse(content: bytes, y: int, m: int, status: str) -> list[dict]:
    raw = pd.read_excel(io.BytesIO(content), sheet_name="Table G", header=None)
    hdr = next(i for i in range(12) if "State" in str(raw.iloc[i, 0]))
    regions = [re.sub(r"\s+", " ", str(v)).strip() for v in raw.iloc[hdr, 1:]]
    rows = []
    for i in range(hdr + 1, len(raw)):
        state = str(raw.iloc[i, 0]).strip()
        if not state or state == "nan" or state.startswith("*"):
            continue
        for j, reg in enumerate(regions, start=1):
            if reg == "nan":
                continue
            v = pd.to_numeric(raw.iloc[i, j], errors="coerce")
            if pd.notna(v):
                rows.append({"year": y, "month": m, "state": state, "region": reg, "arrivals": int(v), "status": status})
    return rows


def main() -> int:
    cfg = CONFIG.get("ntto", {})
    since = int(cfg.get("since", 2019))
    path = DATA / "ntto_i94_state_monthly.csv"
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
    final = set(zip(existing[existing["status"] == "final"]["year"], existing[existing["status"] == "final"]["month"])) if len(existing) else set()
    links = page_links(cfg["page"])
    miss_path = DATA / "ntto_missing.json"
    known_missing = set(json.loads(miss_path.read_text())) if miss_path.exists() else set()
    today = date.today()
    rows, got, missing = [], [], []
    budget = int(os.environ.get("NTTO_MAX_MONTHS", "999"))
    for y in range(since, today.year + 1):
        for m in range(1, 13):
            if (y, m) >= (today.year, today.month) or (y, m) in final or len(got) >= budget:
                continue
            key = f"{y}-{m:02d}"
            # months not found before are re-probed only on the 1st, so the daily run stays fast
            if key in known_missing and today.day != 1 and (y, m) not in links:
                missing.append(key)
                continue
            hit = links.get((y, m)) or guess(y, m)
            if not hit:
                missing.append(key)
                continue
            url, status = hit
            try:
                r = requests.get(url, headers=HEADERS, timeout=120)
                r.raise_for_status()
                rr = parse(r.content, y, m, status)
                rows.extend(rr)
                got.append(f"{y}-{m:02d}:{status[0]}")
                print(f"NTTO {y}-{m:02d} ({status}): {len(rr)} rows")
            except Exception as e:  # noqa: BLE001
                print(f"FAILED NTTO {y}-{m:02d}: {e}", file=sys.stderr)
            time.sleep(0.5)
    miss_path.write_text(json.dumps(sorted(missing)) + "\n")
    df = pd.concat([existing, pd.DataFrame(rows)]) if rows else existing
    if not len(df):
        return 1
    df["rank"] = (df["status"] == "final").astype(int)
    df = df.sort_values("rank").drop_duplicates(["year", "month", "state", "region"], keep="last").drop(columns="rank")
    df = df.sort_values(["year", "month", "state", "region"])
    write_csv(df, "ntto_i94_state_monthly.csv")
    last = df.sort_values(["year", "month"]).iloc[-1]
    update_manifest("ntto", latest=f"{int(last.year)}-{int(last.month):02d}", added=got[-12:], not_found=missing[-12:])
    return 0


if __name__ == "__main__":
    sys.exit(main())

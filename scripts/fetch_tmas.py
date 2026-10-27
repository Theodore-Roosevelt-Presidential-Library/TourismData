"""FHWA TMAS continuous-count station data for the NDDOT counters near Medora.

NDDOT's permanent counters report hourly volumes to FHWA's Travel Monitoring
Analysis System. FHWA publishes the raw files once a year, in one monthly zip
per month (all states, ~28 MB each, posted the following March), at
https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/. That gives daily
and hourly traffic at station 279 (I-94, 7.8 mi west of US 85 — the Medora
exit) by direction, which NDDOT's monthly PDFs do not: day-of-week and
holiday patterns, peak hours, and a daily baseline for the summers before
the Library opened. It does not close the current-year gap (2026 arrives in
March 2027); the NDDOT PDF fetcher still covers that.

Stations are configured per state in `tmas.stations` (ND, plus the I-94, US 85
and I-90 counters across the Montana, South Dakota and Wyoming lines). ND
stations keep their bare three-digit id ("279") for continuity; the others are
written as "MT-131", "SD-110" and so on. `data/tmas_scanned.json` records which
stations each month's zip has already been searched for, so adding a station
re-downloads only the months it has not been looked for in, and a station that
simply did not report in a month is not retried forever. TMAS_MAX_MONTHS caps
how many zips one run downloads (the first backfill of a new station is ~2.5 GB).

Output: data/tmas_daily.csv (station, date, year, month, day, dow, direction,
        vehicles, h00..h23)  — direction letters from the TMAS codes (N/E/S/W)
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import time
import zipfile
from datetime import date

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

BASE = "https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/"
MON = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}
DIR = {"1": "N", "3": "E", "5": "S", "7": "W"}


def month_zip(year: int, month: int) -> bytes | None:
    for name in (f"{year}/{MON[month - 1]}_{year}_ccs_data.zip", f"{year}/{MON[month - 1]}_{year}_tmas.zip"):
        for attempt in range(3):
            try:
                r = requests.get(BASE + name, headers=HEADERS, timeout=600)
                break
            except requests.exceptions.ConnectionError:
                if attempt == 2:
                    raise
                time.sleep(5)
        if r.ok and r.content[:2] == b"PK":
            return r.content
    return None


def _records(lines: list[str]):
    """Yield dicts with station, dir, lane, year, month, day, dow, hours for the three TMAS layouts:
    fixed-width TMG (through 2021), headerless pipe (2022-2024), and headed pipe (2025+)."""
    if not lines:
        return
    if lines[0].lower().startswith("record_type"):
        hdr = [h.strip().title() if h.lower().startswith("hour") else h.strip() for h in lines[0].split("|")]
        hdr = [{"Record_Type": "Record_Type"}.get(h, h) for h in hdr]
        # normalise the names we use, case-insensitively
        norm = {h.lower(): h for h in hdr}
        def col(d, key):
            return d.get(norm.get(key.lower(), key))
        for l in lines[1:]:
            f = l.split("|")
            if len(f) < len(hdr):
                continue
            d = dict(zip(hdr, f))
            try:
                yield {"state": col(d, "State_Code"), "station": col(d, "Station_Id"), "dir": col(d, "Travel_Dir"), "lane": col(d, "Travel_Lane"), "year": (lambda y: y + 2000 if y < 100 else y)(int(col(d, "Year_Record"))), "month": int(col(d, "Month_Record")), "day": int(col(d, "Day_Record")), "dow": int(col(d, "Day_of_Week")), "hours": [int(col(d, f"Hour_{h:02d}") or 0) for h in range(24)]}
            except (TypeError, ValueError):
                continue
    elif "|" in lines[0]:
        for l in lines:
            f = l.split("|")
            if len(f) < 34 or not f[6].isdigit():
                continue
            yr = int(f[6])
            yield {"state": f[1], "station": f[3], "dir": f[4], "lane": f[5], "year": yr + 2000 if yr < 100 else yr, "month": int(f[7]), "day": int(f[8]), "dow": int(f[9]), "hours": [int(x or 0) for x in f[10:34]]}
    else:
        for l in lines:
            if len(l) < 21 + 24 * 5 or l[0] != "3":
                continue
            yr = int(l[13:15])
            # 2020 files carry a one-character restrictions flag at position 20 before the 24 five-digit hours;
            # 2019 files do not. Both are 141 wide, so detect by plausibility: a misaligned read yields values
            # that are all multiples of ten.
            def hours_from(start):
                return [int(l[start + 5 * h : start + 5 + 5 * h] or 0) for h in range(24)]
            h21 = hours_from(21)
            hours = hours_from(20) if sum(v % 10 == 0 for v in h21) >= 22 and sum(v % 10 == 0 for v in hours_from(20)) < 22 else h21
            yield {"state": l[1:3], "station": l[5:11], "dir": l[11], "lane": l[12], "year": 2000 + yr, "month": int(l[15:17]), "day": int(l[17:19]), "dow": int(l[19]), "hours": hours}


STATE_CODES = {"ND": "38", "MT": "30", "SD": "46", "WY": "56"}


def station_key(state: str, station: str) -> str:
    return station[-3:] if state == "ND" else f"{state}-{station[-3:]}"


def parse(zip_bytes: bytes, stations: dict[str, set[str]]) -> pd.DataFrame:
    """stations: {"ND": {"000279", ...}, "MT": {...}}"""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    rows = []
    for st, ids in stations.items():
        name = next((n for n in z.namelist() if n.split("/")[-1].upper().startswith(st) and not n.upper().endswith(".STA")), None)
        if not name:
            continue
        lines = z.read(name).decode("latin-1").splitlines()
        for r in _records(lines):
            if r["state"] != STATE_CODES[st] or r["station"] not in ids:
                continue
            rows.append({"station": station_key(st, r["station"]), "year": r["year"], "month": r["month"], "day": r["day"], "dow": r["dow"], "direction": DIR.get(r["dir"], r["dir"]), "lane": r["lane"], **{f"h{h:02d}": v for h, v in enumerate(r["hours"])}})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    hcols = [f"h{h:02d}" for h in range(24)]
    g = df.groupby(["station", "year", "month", "day", "dow", "direction"], as_index=False)[hcols].sum()
    g["vehicles"] = g[hcols].sum(axis=1)
    g["date"] = pd.to_datetime(g[["year", "month", "day"]], errors="coerce").dt.strftime("%Y-%m-%d")
    g = g[g["date"].notna()]
    return g[["station", "date", "year", "month", "day", "dow", "direction", "vehicles", *hcols]]


def main() -> int:
    cfg = CONFIG.get("tmas", {})
    raw = cfg.get("stations", {"ND": {"000279": ""}})
    if isinstance(raw, list):  # old config shape: ND station ids
        raw = {"ND": {s: "" for s in raw}}
    stations = {st: {s.zfill(6) for s in ids} for st, ids in raw.items()}
    wanted = {station_key(st, s) for st, ids in stations.items() for s in ids}
    since = int(cfg.get("since", 2019))
    max_months = int(os.environ.get("TMAS_MAX_MONTHS", "999"))
    out = DATA / "tmas_daily.csv"
    log_path = DATA / "tmas_scanned.json"
    existing = pd.read_csv(out, dtype={"station": str}) if out.exists() else pd.DataFrame()
    scanned: dict[str, list[str]] = json.loads(log_path.read_text()) if log_path.exists() else {}
    if not scanned and len(existing):
        # first run with the scan log: months already in the CSV were searched for the original ND stations
        for (y, m), g in existing.groupby(["year", "month"]):
            scanned[f"{int(y)}-{int(m):02d}"] = sorted({"279", "221"} | set(g["station"].astype(str)))
    today = date.today()
    frames, got, missing = [], [], []
    fetched = 0
    for y in range(since, today.year + 1):
        for m in range(1, 13):
            key = f"{y}-{m:02d}"
            if (y, m) >= (today.year, today.month) or wanted <= set(scanned.get(key, [])):
                continue
            if fetched >= max_months:
                break
            try:
                b = month_zip(y, m)
            except Exception as e:  # noqa: BLE001
                print(f"TMAS {key}: {e}", file=sys.stderr)
                continue
            if b is None:
                missing.append(key)
                continue
            fetched += 1
            need = {st: {s for s in ids if station_key(st, s) not in scanned.get(key, [])} for st, ids in stations.items()}
            df = parse(b, {st: ids for st, ids in need.items() if ids})
            scanned[key] = sorted(set(scanned.get(key, [])) | wanted)
            if len(df):
                frames.append(df)
                got.append(key)
                print(f"TMAS {key}: {len(df)} station-days ({', '.join(sorted(df['station'].unique()))})")
            else:
                print(f"TMAS {key}: none of the new stations reported")
    allv = pd.concat([existing, *frames]) if frames else existing
    if not len(allv):
        print("no TMAS rows", file=sys.stderr)
        return 1
    allv["station"] = allv["station"].astype(str)
    allv = allv.drop_duplicates(["station", "date", "direction"]).sort_values(["station", "date", "direction"])
    write_csv(allv, "tmas_daily.csv")
    log_path.write_text(json.dumps(dict(sorted(scanned.items())), indent=0) + "\n")
    update_manifest("tmas", months_added=got, not_posted=missing[-6:], latest=str(allv["date"].max()), stations=sorted({str(s) for s in allv["station"].unique()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

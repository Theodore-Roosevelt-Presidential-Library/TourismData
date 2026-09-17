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

Only the configured stations' rows are kept; each monthly zip is downloaded
once and never again (months already in the CSV are skipped).

Output: data/tmas_daily.csv (station, date, year, month, day, dow, direction,
        vehicles, h00..h23)  — direction 3 = eastbound, 7 = westbound (TMAS codes)
"""
from __future__ import annotations

import io
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


def parse(zip_bytes: bytes, stations: set[str], state_code: str = "38") -> pd.DataFrame:
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    name = next((n for n in z.namelist() if n.split("/")[-1].upper().startswith("ND")), None)
    if not name:
        return pd.DataFrame()
    lines = z.read(name).decode("latin-1").splitlines()
    rows = []
    for r in _records(lines):
        if r["state"] != state_code or r["station"] not in stations:
            continue
        rows.append({"station": r["station"][-3:], "year": r["year"], "month": r["month"], "day": r["day"], "dow": r["dow"], "direction": DIR.get(r["dir"], r["dir"]), "lane": r["lane"], **{f"h{h:02d}": v for h, v in enumerate(r["hours"])}})
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
    stations = {s.zfill(6) for s in cfg.get("stations", ["000279"])}
    since = int(cfg.get("since", 2019))
    out = DATA / "tmas_daily.csv"
    existing = pd.read_csv(out, dtype={"station": str}) if out.exists() else pd.DataFrame()
    have = set(zip(existing["year"], existing["month"])) if len(existing) else set()
    today = date.today()
    frames, got, missing = [], [], []
    for y in range(since, today.year + 1):
        for m in range(1, 13):
            if (y, m) in have or (y, m) >= (today.year, today.month):
                continue
            try:
                b = month_zip(y, m)
            except Exception as e:  # noqa: BLE001
                print(f"TMAS {y}-{m:02d}: {e}", file=sys.stderr)
                continue
            if b is None:
                missing.append(f"{y}-{m:02d}")
                continue
            df = parse(b, stations)
            if len(df):
                frames.append(df)
                got.append(f"{y}-{m:02d}")
                print(f"TMAS {y}-{m:02d}: {len(df)} station-days")
    allv = pd.concat([existing, *frames]) if frames else existing
    if not len(allv):
        print("no TMAS rows", file=sys.stderr)
        return 1
    allv = allv.drop_duplicates(["station", "date", "direction"]).sort_values(["station", "date", "direction"])
    write_csv(allv, "tmas_daily.csv")
    update_manifest("tmas", months_added=got, not_posted=missing[-6:], latest=str(allv["date"].max()), stations=sorted({str(s) for s in allv["station"].unique()}))
    return 0


if __name__ == "__main__":
    sys.exit(main())

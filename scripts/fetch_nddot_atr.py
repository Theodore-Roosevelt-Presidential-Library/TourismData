"""Parse NDDOT's monthly "Automatic Traffic Data" PDF reports for the
permanent counters (ATRs) around Medora.

NDDOT posts one PDF per month at
  https://www.dot.nd.gov/sites/www/files/documents/maps/traffic/reports/e_report_{Month}{Year}.pdf
Each report's "Monthly Volume Comparison by FC" pages list, per station, the
month's average daily traffic (MADT) for the report year AND the prior year,
plus weekday (Mon-Thu) and weekend (Sat-Sun) averages. So every report yields
two years for its month. Part 2 of each PDF repeats the tables for trucks
only; those pages are skipped.

Stations (config "nddot_stations"):
  00279 Painted Canyon  I-94, 7.8 mi W of US 85 (Medora exit corridor)
  00221 Fairfield       US 85, 5.1 mi N of I-94 (north approach)
  00223 New Salem       I-94 west of Bismarck (eastern corridor control)
  00291 (Slope)         US 12 - appears in truck tables; included if present

Months already in the CSV are not re-fetched. A month that returns 404 is
skipped (NDDOT posts irregularly; 2026 reports were not yet posted when this
was written).

Output: data/nddot_atr_monthly.csv
        (station, name, route, county, year, month, madt, weekday_adt,
         weekend_adt, days_monitored, report)
"""
from __future__ import annotations

import io
import re
import sys
import time

import pandas as pd
import pdfplumber
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

BASE = "https://www.dot.nd.gov/sites/www/files/documents/maps/traffic/reports/e_report_{month}{year}.pdf"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
NUM = r"-?[\d,]+"


def parse_report(content: bytes, stations: dict[str, dict], year: int, month: int, report: str) -> list[dict]:
    rows = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            head = "\n".join(text.splitlines()[:3])
            if "Monthly Volume Comparison" not in head or "Truck" in head:
                continue
            for line in text.splitlines():
                m = re.match(r"^(\d{5})\s+\d\s+[RU]\s+(\S+)\s+(.+?)\s+[A-Z][a-z]{2}\s+(.*)$", line)
                if not m or m.group(1) not in stations:
                    continue
                sid, route, county, rest = m.groups()
                nums = [n for n in re.findall(r"(-?[\d,]+(?:\.\d+)?%?)", rest)]
                vals = [n for n in nums if not n.endswith("%")]
                # Expected: prev, cur, prevWD, curWD, prevWE, curWE, daysPrev, daysCur (percent columns removed)
                if len(vals) < 8:
                    continue
                v = [float(x.replace(",", "")) for x in vals[:8]]
                for yr, idx in ((year - 1, 0), (year, 1)):
                    rows.append(
                        {
                            "station": sid,
                            "name": stations[sid]["name"],
                            "route": stations[sid].get("route", route),
                            "county": county.strip(),
                            "year": yr,
                            "month": month,
                            "madt": int(v[idx]),
                            "weekday_adt": int(v[2 + idx]),
                            "weekend_adt": int(v[4 + idx]),
                            "days_monitored": int(v[6 + idx]),
                            "report": report,
                        }
                    )
    return rows


def main() -> int:
    stations = CONFIG.get("nddot_stations", {})
    if not stations:
        print("no nddot_stations configured", file=sys.stderr)
        return 1
    since = pd.Timestamp(CONFIG.get("nddot_since", "2025-01-01"))
    path = DATA / "nddot_atr_monthly.csv"
    existing = pd.read_csv(path, dtype={"station": str}) if path.exists() else pd.DataFrame()
    done = set(existing["report"].unique()) if len(existing) else set()
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    rows, fetched, missing = [], [], []
    d = since
    today = pd.Timestamp.today()
    while d <= today:
        report = f"{MONTHS[d.month - 1]}{d.year}"
        if report not in done:
            url = BASE.format(month=MONTHS[d.month - 1], year=d.year)
            try:
                r = s.get(url, timeout=120)
                if r.status_code == 200 and r.content[:4] == b"%PDF":
                    got = parse_report(r.content, stations, d.year, d.month, report)
                    rows.extend(got)
                    fetched.append(report)
                    print(f"{report}: {len(got)} station-year rows")
                else:
                    missing.append(report)
            except Exception as e:  # noqa: BLE001
                print(f"FAILED {report}: {e}", file=sys.stderr)
                missing.append(report)
            time.sleep(1)
        d = d + pd.offsets.MonthBegin(1)
    df = pd.concat([existing, pd.DataFrame(rows)]) if rows else existing
    if df is None or not len(df):
        print("no NDDOT rows", file=sys.stderr)
        return 1
    # A month can appear twice (as "current" in one report and "prior" in the next year's); keep the current-year read
    df["_cur"] = df.apply(lambda r: 1 if str(r["year"]) in r["report"] else 0, axis=1)
    df = df.sort_values(["station", "year", "month", "_cur"]).drop_duplicates(["station", "year", "month"], keep="last").drop(columns="_cur")
    write_csv(df, "nddot_atr_monthly.csv")
    latest = df.sort_values(["year", "month"]).iloc[-1]
    update_manifest("nddot_atr_monthly", rows=len(df), latest_month=f"{int(latest.year)}-{int(latest.month):02d}", fetched=fetched, missing_reports=missing[-12:])
    return 0


if __name__ == "__main__":
    sys.exit(main())

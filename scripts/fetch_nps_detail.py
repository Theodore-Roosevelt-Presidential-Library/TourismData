"""TRNP detail from NPS IRMA STATS, beyond the monthly recreation-visit total.

Three park-specific SSRS reports, exported the same way as fetch_nps.py:

  * "Traffic Counts": the Painted Canyon rest-area vehicle counter by month,
    2014–present (counted May–October only). Painted Canyon is the I-94
    overlook 7 miles east of Medora — the one TRNP counter closest to the
    Library's traffic.
  * "Monthly Public Use": the latest posted month's public-use statistics by
    location — South Unit visits, North Unit visits, Painted Canyon visits,
    Medora walk-ins, campers by unit, bus passengers — with year-to-date.
    IRMA only publishes the latest month (its Year/Month parameters are
    SSRS form fields, not URL parameters), so this fetcher keeps every
    month it sees; the by-location monthly history accumulates from the
    first run onward and the YTD column gives the current year to date.
  * "Overnight Stays": annual overnight stays by type (tent, RV,
    backcountry, miscellaneous), 1979–last calendar year.

Outputs: data/nps_thro_painted_canyon_traffic.csv (year, month, vehicles)
         data/nps_thro_public_use_monthly.csv   (year, month, location, value, ytd)
         data/nps_thro_overnight_annual.csv     (year, category, stays)
"""
from __future__ import annotations

import csv
import html
import io
import re
import sys
import time
import urllib.parse

import pandas as pd
import requests

from common import DATA, USER_AGENT, update_manifest, write_csv

PARK = "THRO"
BASE = "https://irma.nps.gov/Stats/SSRSReports/Park Specific Reports/"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def export_csv(report: str, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        try:
            page = s.get(BASE.replace(" ", "%20") + urllib.parse.quote(report) + f"?Park={PARK}", timeout=60)
            page.raise_for_status()
            m = re.search(r'src="(/Stats/MvcReportViewer[^"]+)"', page.text)
            if not m:
                raise RuntimeError("no viewer iframe")
            frame = s.get("https://irma.nps.gov" + html.unescape(m.group(1)), timeout=90)
            m = re.search(r'ExportUrlBase":"([^"]+)"', frame.text)
            if not m:
                raise RuntimeError("no ExportUrlBase")
            out = s.get("https://irma.nps.gov" + m.group(1).encode().decode("unicode_escape") + "CSV", timeout=120)
            out.raise_for_status()
            return out.content.decode("utf-8-sig")
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{report}: {last}")


def num(s: str) -> int | None:
    s = (s or "").strip().replace(",", "")
    return int(float(s)) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def traffic(text: str) -> pd.DataFrame:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) > 14 and "PAINTED CANYON" in r[0].upper() and r[1].strip().isdigit():
            y = int(r[1])
            for i, _ in enumerate(MONTHS, start=2):
                v = num(r[i]) if i < len(r) else None
                if v is not None and v > 0:
                    rows.append({"year": y, "month": i - 1, "vehicles": v})
    return pd.DataFrame(rows).sort_values(["year", "month"])


def public_use(text: str) -> tuple[pd.DataFrame, dict]:
    head = {}
    rows = []
    reader = list(csv.reader(io.StringIO(text)))
    for i, r in enumerate(reader):
        if r and r[0] == "ParkName" and i + 1 < len(reader):
            v = reader[i + 1]
            my = v[1]  # e.g. 8/2026
            mo, yr = (int(x) for x in my.split("/"))
            head = {"year": yr, "month": mo, "rec_visits": num(v[4]), "rec_visits_prev_year": num(v[31]), "ytd_rec_visits": num(v[37]), "ytd_rec_visits_prev_year": num(v[38])}
        if r and r[0] == "Field38":
            for v in reader[i + 1 :]:
                if len(v) >= 3 and v[0].strip():
                    rows.append({"year": head["year"], "month": head["month"], "location": v[0].strip(), "value": num(v[1]), "ytd": num(v[2])})
    return pd.DataFrame(rows), head


def overnight(text: str) -> pd.DataFrame:
    rows = []
    for r in csv.reader(io.StringIO(text)):
        if len(r) >= 15 and r[0] == "Concessioner Lodging Overnights" and r[1].strip().isdigit():
            y = int(r[1])
            pairs = [("Concessioner lodging", r[2]), ("Concessioner camping", r[4]), ("Tent", r[6]), ("RV", r[8]), ("Backcountry", r[10]), ("Miscellaneous", r[12]), ("Non-recreation", r[14])]
            for cat, v in pairs:
                rows.append({"year": y, "category": cat, "stays": num(v) or 0})
    return pd.DataFrame(rows)


def main() -> int:
    ok = {}
    try:
        t = traffic(export_csv("Traffic Counts"))
        write_csv(t, "nps_thro_painted_canyon_traffic.csv")
        ok["painted_canyon_latest"] = f"{int(t.year.max())}-{int(t[t.year == t.year.max()].month.max()):02d}"
    except Exception as e:  # noqa: BLE001
        print(f"traffic counts failed: {e}", file=sys.stderr)
    try:
        pu, head = public_use(export_csv("Monthly Public Use"))
        p = DATA / "nps_thro_public_use_monthly.csv"
        prev = pd.read_csv(p) if p.exists() else pd.DataFrame(columns=pu.columns)
        allv = pd.concat([prev[~((prev["year"] == head["year"]) & (prev["month"] == head["month"]))], pu]).sort_values(["year", "month", "location"])
        write_csv(allv, "nps_thro_public_use_monthly.csv")
        ok["public_use_latest"] = f"{head['year']}-{head['month']:02d}"
        ok["public_use_months"] = int(len(allv.groupby(["year", "month"])))
        ok["rec_visits_latest"] = head
    except Exception as e:  # noqa: BLE001
        print(f"monthly public use failed: {e}", file=sys.stderr)
    try:
        o = overnight(export_csv("Overnight Stays (1979 - Last Calendar Year)"))
        write_csv(o, "nps_thro_overnight_annual.csv")
        ok["overnight_latest_year"] = int(o.year.max())
    except Exception as e:  # noqa: BLE001
        print(f"overnight stays failed: {e}", file=sys.stderr)
    if not ok:
        return 1
    update_manifest("nps_detail", **ok)
    return 0


if __name__ == "__main__":
    sys.exit(main())

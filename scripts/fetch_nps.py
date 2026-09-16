"""Pull monthly recreation visits for each configured park from NPS IRMA STATS.

IRMA has no public API. The "Recreation Visitors By Month" SSRS report can be
exported as CSV once a report session exists, so each park takes three requests:

  1. GET the report page  -> iframe src with a session _id
  2. GET the iframe page  -> ExportUrlBase (session + control id)
  3. GET ExportUrlBase + "CSV"

The report includes the current year through the last posted month (NPS posts
preliminary counts around the 15th of the following month).

Output: data/nps_monthly.csv  (park, park_name, role, state, year, month, visits)
"""
from __future__ import annotations

import csv
import html
import io
import re
import sys
import time

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

REPORT = (
    "https://irma.nps.gov/Stats/SSRSReports/Park%20Specific%20Reports/"
    "Recreation%20Visitors%20By%20Month%20(1979%20-%20Last%20Calendar%20Year)?Park={code}"
)
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


def fetch_park_csv(code: str, retries: int = 3) -> str:
    last_err: Exception | None = None
    for attempt in range(retries):
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        try:
            page = s.get(REPORT.format(code=code), timeout=60)
            page.raise_for_status()
            m = re.search(r'src="(/Stats/MvcReportViewer[^"]+)"', page.text)
            if not m:
                raise RuntimeError("no report viewer iframe")
            frame = s.get("https://irma.nps.gov" + html.unescape(m.group(1)), timeout=90)
            frame.raise_for_status()
            m = re.search(r'ExportUrlBase":"([^"]+)"', frame.text)
            if not m:
                raise RuntimeError("no ExportUrlBase in viewer")
            export = m.group(1).encode().decode("unicode_escape")
            out = s.get("https://irma.nps.gov" + export + "CSV", timeout=120)
            out.raise_for_status()
            text = out.content.decode("utf-8-sig")
            if "Year,JAN" not in text:
                raise RuntimeError("export did not return the monthly table")
            return text
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"{code}: {last_err}")


def parse(text: str, park: dict) -> list[dict]:
    rows = []
    reader = csv.reader(io.StringIO(text))
    in_table = False
    for r in reader:
        if r and r[0] == "Year":
            in_table = True
            continue
        if not in_table or not r or not r[0].strip().isdigit():
            continue
        year = int(r[0])
        for i, mon in enumerate(MONTHS, start=1):
            cell = r[i].strip() if i < len(r) else ""
            if cell == "":
                continue  # month not yet posted
            rows.append(
                {
                    "park": park["code"],
                    "park_name": park["name"],
                    "role": park["role"],
                    "state": park["state"],
                    "year": year,
                    "month": i,
                    "visits": int(cell.replace(",", "")),
                }
            )
    return rows


def main() -> int:
    all_rows: list[dict] = []
    failures: list[str] = []
    for park in CONFIG["nps_parks"]:
        try:
            rows = parse(fetch_park_csv(park["code"]), park)
            print(f"{park['code']}: {len(rows)} park-months, latest {max((r['year'], r['month']) for r in rows)}")
            all_rows.extend(rows)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {park['code']}: {e}", file=sys.stderr)
            failures.append(park["code"])
        time.sleep(1)

    if not all_rows:
        print("no NPS data fetched; leaving existing file untouched", file=sys.stderr)
        return 1

    df = pd.DataFrame(all_rows).sort_values(["park", "year", "month"])
    # Keep previously fetched parks if one failed this run
    prev_path = DATA / "nps_monthly.csv"
    if failures and prev_path.exists():
        prev = pd.read_csv(prev_path)
        df = pd.concat([df, prev[prev["park"].isin(failures)]]).sort_values(["park", "year", "month"])
    write_csv(df, "nps_monthly.csv")
    latest = df.groupby("park").apply(lambda g: f"{g.year.max()}-{g[g.year == g.year.max()].month.max():02d}").to_dict()
    update_manifest("nps_monthly", parks=len(CONFIG["nps_parks"]), failed=failures, latest_month=latest)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())

"""South Dakota tourism tax by county, monthly (SD Department of Revenue).

South Dakota levies a 1.5% state tourism tax on lodging, campgrounds,
amusements, visitor-oriented retail and similar businesses. Each month DOR
posts a "Tourism Tax by County" PDF (`MMYYcounty-tourism.pdf`) listing, for
every county, taxable sales by tourism business classification (Hotels &
Motels, Trailer Parks & Campsites, Amusement & Recreation, Gift Shops ...).
The links sit on DOR's historical statistical-reports page under hashed
`/media/<id>/` paths, so they are discovered from that page each run.

Two things to know when reading it:
  * The month is the month RETURNS WERE FILED. Monthly filers file by the
    20th of the following month, so "Returns filed: July" is mostly June
    sales. The CSV keeps the filing month; the dashboard labels it as such.
  * Classifications with fewer than three licensees in a county are folded
    into an undisclosed "Other" line (N/A), and there is no county total.
    County sums here are therefore of DISCLOSED lines only — a floor, and
    one that can jump when a classification crosses the three-licensee
    threshold. Hotels & Motels (7011) is disclosed in every county that
    matters and is the like-for-like lodging series.

Needs poppler's `pdftotext` (installed in the workflow).

Output: data/sd_tourism_tax_monthly.csv
        (year, month, county, sic, category, taxable_sales, tax_due)
        The state total is written as county "State total", sic "TOTAL".
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}
LINK = re.compile(r'href="([^"]*/(\d{2})(\d{2})county-tourism\.pdf)"', re.I)
LINE = re.compile(r"^\s{2,}(\d{3,4})\s+(.+?)\s{2,}([\d,]+\.\d\d)\s+([\d,]+\.\d\d)\s*$")
COUNTY = re.compile(r"^\s{2,}([A-Z][A-Za-z .']+?) County\s*$")
TOTAL = re.compile(r"Total for State\s+([\d,]+\.\d\d)\s+([\d,]+\.\d\d)")
FILED = re.compile(r"Returns Filed:\s+([A-Za-z]+)\s+(\d{4})", re.I)
MONTHS = {m: i for i, m in enumerate(["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}


def discover(index: str) -> dict[tuple[int, int], str]:
    html = requests.get(index, headers=HEADERS, timeout=60).text
    out = {}
    for href, mm, yy in LINK.findall(html):
        m, y = int(mm), 2000 + int(yy)
        if 1 <= m <= 12:
            out[(y, m)] = href if href.startswith("http") else "https://dor.sd.gov" + href
    return out


def parse(text: str, year: int, month: int) -> list[dict]:
    m = FILED.search(text)
    if m and m.group(1).lower() in MONTHS:
        year, month = int(m.group(2)), MONTHS[m.group(1).lower()]
    rows, county = [], None
    for line in text.splitlines():
        c = COUNTY.match(line)
        if c:
            county = c.group(1).strip()
            continue
        x = LINE.match(line)
        if x and county:
            rows.append({"year": year, "month": month, "county": county, "sic": x.group(1), "category": x.group(2).strip(),
                         "taxable_sales": float(x.group(3).replace(",", "")), "tax_due": float(x.group(4).replace(",", ""))})
    t = TOTAL.search(text)
    if t:
        rows.append({"year": year, "month": month, "county": "State total", "sic": "TOTAL", "category": "All tourism classifications",
                     "taxable_sales": float(t.group(1).replace(",", "")), "tax_due": float(t.group(2).replace(",", ""))})
    return rows


def main() -> int:
    cfg = CONFIG.get("sd_tourism", {})
    since = int(cfg.get("since", 2019))
    links = discover(cfg["index"])
    path = DATA / "sd_tourism_tax_monthly.csv"
    existing = pd.read_csv(path, dtype={"sic": str}) if path.exists() else pd.DataFrame()
    have = set(zip(existing["year"], existing["month"])) if len(existing) else set()
    latest_have = max(have) if have else None
    rows, failed = [], []
    budget, done = int(os.environ.get("SD_MAX_MONTHS", "999")), 0
    for (y, m), url in sorted(links.items()):
        if done >= budget:
            break
        # re-read the newest month we hold in case DOR re-posted it; skip older months already stored
        if y < since or ((y, m) in have and (y, m) != latest_have):
            continue
        try:
            pdf = requests.get(url, headers=HEADERS, timeout=120)
            pdf.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
                f.write(pdf.content)
                f.flush()
                text = subprocess.run(["pdftotext", "-layout", f.name, "-"], capture_output=True, text=True, check=True).stdout
            r = parse(text, y, m)
            if not r:
                raise RuntimeError("no rows parsed")
            rows.extend(r)
            done += 1
            print(f"SD tourism {y}-{m:02d}: {len(r)} rows")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED SD tourism {y}-{m:02d}: {e}", file=sys.stderr)
            failed.append(f"{y}-{m:02d}")
        time.sleep(0.5)
    df = pd.concat([existing, pd.DataFrame(rows)]) if rows else existing
    if not len(df):
        return 1
    df = df.drop_duplicates(["year", "month", "county", "sic", "category"], keep="last").sort_values(["year", "month", "county", "sic"])
    write_csv(df, "sd_tourism_tax_monthly.csv")
    last = df.sort_values(["year", "month"]).iloc[-1]
    update_manifest("sd_tourism", latest=f"{int(last.year)}-{int(last.month):02d}", months=int(len(df.groupby(["year", "month"]))), failed=failed[-6:])
    return 0


if __name__ == "__main__":
    sys.exit(main())

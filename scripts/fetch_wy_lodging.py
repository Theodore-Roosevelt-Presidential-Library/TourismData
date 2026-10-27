"""Wyoming lodging tax collections by county, by state fiscal year.

The Economic Analysis Division (ai.wyo.gov) posts a "Lodging Tax Collections
by County and Municipality" workbook with each annual Sales, Use, and Lodging
Tax Revenue Report. Each edition carries three fiscal years (July–June), so
the fetcher accumulates editions; the newest edition wins on overlapping years.
The link is a Google Drive download that changes per edition and is found by
its link text on the division's page.

Two columns per year: total lodging taxes (state 5% plus any local option) and
the statewide 3% portion. Local rates differ by county and change by vote, so
the 3% column is the like-for-like measure of lodging receipts across counties
and years (receipts ≈ 3% taxes ÷ 0.03).

Output: data/wy_lodging_tax_annual.csv (county, fiscal_year, total_taxes, state_3pct_taxes)
"""
from __future__ import annotations

import html
import io
import re
import sys

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}


def find_link(page: str) -> str:
    t = requests.get(page, headers=HEADERS, timeout=60).text
    for href, label in re.findall(r'href="([^"]+)"[^>]*>(.*?)</a>', t, re.S):
        if re.search(r"Lodging Tax Collections by County", re.sub("<[^>]+>", "", label), re.I):
            return html.unescape(href)
    raise RuntimeError("lodging-by-county link not found")


def parse(content: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(content), header=None)
    hdr = next(i for i in range(10) if str(raw.iloc[i, 0]).strip().upper() == "COUNTY")
    years = {}
    for j, v in enumerate(raw.iloc[hdr]):
        m = re.search(r"FY\s*(\d{4})", str(v))
        if m:
            years[int(m.group(1))] = j
    rows = []
    for i in range(hdr + 2, len(raw)):
        name = str(raw.iloc[i, 0]).strip()
        if not name or name == "nan" or name.upper().startswith(("SOURCE", "NOTE", "*")):
            continue
        for fy, j in years.items():
            tot, s3 = pd.to_numeric(raw.iloc[i, j], errors="coerce"), pd.to_numeric(raw.iloc[i, j + 1], errors="coerce")
            if pd.notna(tot) or pd.notna(s3):
                rows.append({"county": name.upper(), "fiscal_year": fy, "total_taxes": None if pd.isna(tot) else float(tot), "state_3pct_taxes": None if pd.isna(s3) else float(s3)})
    return pd.DataFrame(rows)


def main() -> int:
    cfg = CONFIG.get("wy_lodging", {})
    url = find_link(cfg["page"])
    r = requests.get(url, headers=HEADERS, timeout=120)
    r.raise_for_status()
    new = parse(r.content)
    if new.empty:
        print("no rows parsed", file=sys.stderr)
        return 1
    path = DATA / "wy_lodging_tax_annual.csv"
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
    df = pd.concat([existing, new]).drop_duplicates(["county", "fiscal_year"], keep="last").sort_values(["county", "fiscal_year"])
    write_csv(df, "wy_lodging_tax_annual.csv")
    update_manifest("wy_lodging", latest=f"FY{int(df['fiscal_year'].max())}", link=url)
    return 0


if __name__ == "__main__":
    sys.exit(main())

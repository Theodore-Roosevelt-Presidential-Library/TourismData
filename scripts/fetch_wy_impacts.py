"""Parse Wyoming county travel impacts from the Dean Runyan Associates PDF
published by the Wyoming Office of Tourism.

Each county has a "Direct Travel Impact Summary" page with an 11-year table
(e.g. 2015-2025). The PDF URL changes every year; list the current one in
config/sources.json under "wy_impacts_pdfs". Older editions can be listed too
and are merged (later editions win on overlapping years).

Output: data/wy_county_travel_impacts_annual.csv
        (county, year, visitor_spend_m, other_spend_m, total_spend_m,
         earnings_m, employment, local_tax_m, state_tax_m, total_tax_m, edition)
"""
from __future__ import annotations

import io
import re
import sys

import pandas as pd
import pdfplumber
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

ROWS = {
    "Visitor": "visitor_spend_m",
    "Other travel*": "other_spend_m",
    "Total": None,  # appears twice (spending, tax); handled positionally
    "Earnings": "earnings_m",
    "Employment": "employment",
    "Local": "local_tax_m",
    "State": "state_tax_m",
}


def num(s: str) -> float:
    return float(s.replace(",", ""))


def parse_pdf(content: bytes, edition: int) -> list[dict]:
    out = []
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if len(lines) < 3 or not lines[0].endswith(" County") or lines[1] != "Direct Travel Impact Summary":
                continue
            county = lines[0].replace(" County", "")
            years = None
            vals: dict[str, list[float]] = {}
            total_seen = 0
            for l in lines:
                m = re.match(r"^((?:\d{4}\s+)+)\d{2}-\d{2}$", l.replace("% Chg.", "").strip())
                if years is None and re.match(r"^(\d{4}\s+){5,}", l):
                    years = [int(y) for y in re.findall(r"\b(\d{4})\b", l) if 1990 < int(y) < 2100]
                    continue
                for label, key in ROWS.items():
                    if l.startswith(label + " ") and years:
                        nums = re.findall(r"-?[\d,]+\.?\d*(?=\s|$)", l[len(label):])
                        nums = [n for n in nums if "%" not in n][: len(years)]
                        if len(nums) != len(years):
                            continue
                        if label == "Total":
                            total_seen += 1
                            key = "total_spend_m" if total_seen == 1 else "total_tax_m"
                        vals[key] = [num(n) for n in nums]
                        break
            if years and "visitor_spend_m" in vals:
                for i, y in enumerate(years):
                    rec = {"county": county, "year": y, "edition": edition}
                    for k, arr in vals.items():
                        rec[k] = arr[i]
                    out.append(rec)
    return out


def main() -> int:
    rows = []
    for item in CONFIG.get("wy_impacts_pdfs", []):
        r = requests.get(item["url"], headers={"User-Agent": USER_AGENT}, timeout=180)
        r.raise_for_status()
        got = parse_pdf(r.content, item["edition"])
        print(f"edition {item['edition']}: {len(got)} county-years")
        rows.extend(got)
    if not rows:
        print("no Wyoming rows parsed", file=sys.stderr)
        return 1
    df = pd.DataFrame(rows).sort_values(["county", "year", "edition"])
    df = df.drop_duplicates(["county", "year"], keep="last")
    cols = ["county", "year", "visitor_spend_m", "other_spend_m", "total_spend_m", "earnings_m", "employment", "local_tax_m", "state_tax_m", "total_tax_m", "edition"]
    df = df[[c for c in cols if c in df.columns]]
    write_csv(df, "wy_county_travel_impacts_annual.csv")
    update_manifest("wy_county_travel_impacts", rows=len(df), counties=df["county"].nunique(), years=[int(df.year.min()), int(df.year.max())])
    return 0


if __name__ == "__main__":
    sys.exit(main())

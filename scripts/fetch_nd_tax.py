"""Pull quarterly taxable sales and purchases by county from the ND Office of
State Tax Commissioner.

The Commissioner publishes one Excel workbook with every quarter since 2019 Q1
(County Overview / County Detail / City / Industry sheets). County totals are
the Medora proxy: Billings County is mostly Medora commerce. Medora itself is
below the top-200 city cutoff, and county-by-industry is only in the PDF.

Output: data/nd_taxable_sales_quarterly.csv
        (county, year, quarter, taxable_sales, taxable_purchases, total)
"""
from __future__ import annotations

import io
import re
import sys

import pandas as pd
import requests

from common import USER_AGENT, update_manifest, write_csv

URL = "https://www.tax.nd.gov/sites/default/files/documents/Data/taxable-sales-and-purchases-excel.xlsx"


def main() -> int:
    r = requests.get(URL, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    raw = pd.read_excel(io.BytesIO(r.content), sheet_name="County Detail", header=None)
    quarters = raw.iloc[0].tolist()  # "2026 Q2" in every third column
    kinds = raw.iloc[1].tolist()  # Taxable Sales / Taxable Purchases / Total
    rows = []
    for _, rec in raw.iloc[2:].iterrows():
        county = str(rec.iloc[0]).strip()
        if not county or county.lower() in ("nan", "total", "state total"):
            continue
        cur_q = None
        vals: dict[str, float] = {}
        for j in range(1, len(rec)):
            if isinstance(quarters[j], str) and re.match(r"\d{4} Q[1-4]", quarters[j]):
                cur_q = quarters[j]
            kind = str(kinds[j]).strip().lower()
            if cur_q and kind in ("taxable sales", "taxable purchases", "total"):
                vals[(cur_q, kind)] = rec.iloc[j]
        for q in sorted({k[0] for k in vals}):
            y, qn = q.split(" Q")
            rows.append(
                {
                    "county": re.sub(r"^Mc(\w)", lambda m: "Mc" + m.group(1).upper(), county.title()),
                    "year": int(y),
                    "quarter": int(qn),
                    "taxable_sales": vals.get((q, "taxable sales")),
                    "taxable_purchases": vals.get((q, "taxable purchases")),
                    "total": vals.get((q, "total")),
                }
            )
    if not rows:
        print("no ND tax rows parsed", file=sys.stderr)
        return 1
    df = pd.DataFrame(rows).dropna(subset=["total"]).sort_values(["county", "year", "quarter"])
    write_csv(df, "nd_taxable_sales_quarterly.csv")
    latest = df.sort_values(["year", "quarter"]).iloc[-1]
    update_manifest("nd_taxable_sales_quarterly", rows=len(df), counties=df["county"].nunique(), latest_quarter=f"{latest.year} Q{latest.quarter}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

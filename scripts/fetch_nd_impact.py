"""ND Commerce / Tourism Economics annual "Economic Impact of Tourism in
North Dakota" — county visitor spending (5-year timeline) and county
tourism jobs / income for the report year.

Report PDFs are discovered from the Commerce research page (links titled
"<year> Economic Impact"); `nd_impact_pdfs` in config can add editions by
hand. Later editions win on overlapping years (they revise). Annual only —
this is the county-level comparable to Wyoming's Dean Runyan table.

The sector tables (lodging, food & beverage, retail, recreation, transport,
plus state & local tax revenue) are printed rotated, which pdfplumber cannot
read; they are parsed with poppler's `pdftotext -layout` when it is
installed (apt: poppler-utils) and skipped otherwise.

Outputs: data/nd_tourism_impact_county_spending.csv (county, year, spending_musd, edition)
         data/nd_tourism_impact_county_sectors.csv (county, year, lodging, food_beverage, retail,
             recreation, transport, total, growth_pct, tax_revenue_musd, edition)
         data/nd_tourism_impact_county_jobs.csv (county, year, direct_jobs, total_jobs,
             share_of_state_pct, share_of_county_employment_pct, direct_income_musd, total_income_musd)
"""
from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
import tempfile

import pandas as pd
import pdfplumber
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

RESEARCH = "https://www.commerce.nd.gov/tourism-marketing/research-and-reports"
HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}


def discover() -> dict[int, str]:
    out = {}
    try:
        html = requests.get(RESEARCH, headers=HEADERS, timeout=60).text
    except Exception as e:  # noqa: BLE001
        print(f"research page: {e}", file=sys.stderr)
        return out
    for m in re.finditer(r'href="([^"]+\.pdf)"[^>]*>\s*(\d{4})\s+Economic Impact', html, re.I):
        out[int(m.group(2))] = m.group(1)
    for m in re.finditer(r'(\d{4})\s+Economic Impact\s*</a>', html):
        pass
    return out


SECTOR_ROW = re.compile(r"((?:North Dakota|State Total|[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)? County))\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+\$([\d,.]+)\s+(-?[\d.]+)%(?:\s+\$([\d,.]+))?")


def parse_sectors(pdf_bytes: bytes, edition: int) -> pd.DataFrame:
    """County x sector tables via pdftotext -layout (rotated pages). Two counties per printed line."""
    if not shutil.which("pdftotext"):
        print("pdftotext not installed; skipping sector tables", file=sys.stderr)
        return pd.DataFrame()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(pdf_bytes)
        path = f.name
    try:
        txt = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True, text=True, timeout=120).stdout
    finally:
        import os
        os.unlink(path)
    rows, year = [], None
    for line in txt.splitlines():
        m = re.search(r"Annual [Vv]isitor [Ss]pending (?:\(|\u2013 |- )?(\d{4})", line)
        if m:
            year = int(m.group(1))
            continue
        if year is None:
            continue
        for mm in SECTOR_ROW.finditer(line):
            f = lambda s: float(s.replace(",", "")) if s else None  # noqa: E731
            rows.append({"county": mm.group(1).replace(" County", "").replace("State Total", "North Dakota"), "year": year, "lodging": f(mm.group(2)), "food_beverage": f(mm.group(3)), "retail": f(mm.group(4)),
                         "recreation": f(mm.group(5)), "transport": f(mm.group(6)), "total": f(mm.group(7)), "growth_pct": f(mm.group(8)), "tax_revenue_musd": f(mm.group(9)), "edition": edition})
    return pd.DataFrame(rows).drop_duplicates(["county", "year"]) if rows else pd.DataFrame()


def parse(pdf_bytes: bytes, edition: int):
    spend, jobs = [], []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            if "Annual Visitor Spending" in t:
                hdr = re.search(r"County\s+((?:\d{4}\s+){3,})", t)
                years = [int(y) for y in hdr.group(1).split()] if hdr else []
                for m in re.finditer(r"((?:North Dakota|[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)? County))\s+((?:\$[\d,]+\.\d\s+){%d})" % len(years), t):
                    vals = [float(v.replace("$", "").replace(",", "")) for v in m.group(2).split()]
                    for y, v in zip(years, vals):
                        spend.append({"county": m.group(1).replace(" County", ""), "year": y, "spending_musd": v, "edition": edition})
            if "Tourism Impacts" in t and "Personal Income" in t:
                ym = re.search(r"Tourism Impacts \((\d{4})\)", t)
                year = int(ym.group(1)) if ym else edition
                for m in re.finditer(r"((?:North Dakota|[A-Z][A-Za-z]+(?: [A-Z][A-Za-z]+)? County))\s+([\d,]+)\s+([\d,]+)\s+([\d.]+)%\s+([\d.]+)%\s+\$([\d,]+\.?\d*)\s+\$([\d,]+\.?\d*)", t):
                    f = lambda s: float(s.replace(",", ""))  # noqa: E731
                    jobs.append({"county": m.group(1).replace(" County", ""), "year": year, "direct_jobs": int(f(m.group(2))), "total_jobs": int(f(m.group(3))),
                                 "share_of_state_pct": f(m.group(4)), "share_of_county_employment_pct": f(m.group(5)),
                                 "direct_income_musd": f(m.group(6)), "total_income_musd": f(m.group(7)), "edition": edition})
    return pd.DataFrame(spend).drop_duplicates(["county", "year"]), pd.DataFrame(jobs).drop_duplicates(["county", "year"])


def main() -> int:
    pdfs = {int(k): v for k, v in CONFIG.get("nd_impact_pdfs", {}).items()}
    pdfs.update(discover())
    if not pdfs:
        print("no ND impact PDFs found", file=sys.stderr)
        return 1
    S, J, X = [], [], []
    for ed in sorted(pdfs):
        try:
            r = requests.get(pdfs[ed], headers=HEADERS, timeout=180)
            r.raise_for_status()
            s, j = parse(r.content, ed)
            x = parse_sectors(r.content, ed)
            print(f"{ed} edition: {len(s)} spending rows, {len(j)} jobs rows, {len(x)} sector rows")
            S.append(s)
            J.append(j)
            if len(x):
                X.append(x)
        except Exception as e:  # noqa: BLE001
            print(f"{ed} edition failed: {e}", file=sys.stderr)
    if not S:
        return 1
    spend = pd.concat(S).sort_values("edition").drop_duplicates(["county", "year"], keep="last").sort_values(["county", "year"])
    jobs = pd.concat(J).sort_values("edition").drop_duplicates(["county", "year"], keep="last").sort_values(["county", "year"])
    write_csv(spend, "nd_tourism_impact_county_spending.csv")
    write_csv(jobs, "nd_tourism_impact_county_jobs.csv")
    if X:
        allx = pd.concat(X).sort_values("edition")
        sect = allx.drop_duplicates(["county", "year"], keep="last").set_index(["county", "year"])
        # Later editions revise the spending figures but only print tax revenue for their own year; keep any edition's tax figure.
        tax = allx.dropna(subset=["tax_revenue_musd"]).drop_duplicates(["county", "year"], keep="last").set_index(["county", "year"])["tax_revenue_musd"]
        sect["tax_revenue_musd"] = tax.reindex(sect.index)
        sect = sect.reset_index().sort_values(["county", "year"])
        write_csv(sect, "nd_tourism_impact_county_sectors.csv")
    update_manifest("nd_impact", editions=sorted(pdfs), years=f"{int(spend.year.min())}–{int(spend.year.max())}", counties=int(spend.county.nunique()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""ND Commerce / Tourism Economics annual "Economic Impact of Tourism in
North Dakota" — county visitor spending (5-year timeline) and county
tourism jobs / income for the report year.

Report PDFs are discovered from the Commerce research page (links titled
"<year> Economic Impact"); `nd_impact_pdfs` in config can add editions by
hand. Later editions win on overlapping years (they revise). Annual only —
this is the county-level comparable to Wyoming's Dean Runyan table.

Outputs: data/nd_tourism_impact_county_spending.csv (county, year, spending_musd, edition)
         data/nd_tourism_impact_county_jobs.csv (county, year, direct_jobs, total_jobs,
             share_of_state_pct, share_of_county_employment_pct, direct_income_musd, total_income_musd)
"""
from __future__ import annotations

import io
import re
import sys

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
    S, J = [], []
    for ed in sorted(pdfs):
        try:
            r = requests.get(pdfs[ed], headers=HEADERS, timeout=180)
            r.raise_for_status()
            s, j = parse(r.content, ed)
            print(f"{ed} edition: {len(s)} spending rows, {len(j)} jobs rows")
            S.append(s)
            J.append(j)
        except Exception as e:  # noqa: BLE001
            print(f"{ed} edition failed: {e}", file=sys.stderr)
    if not S:
        return 1
    spend = pd.concat(S).sort_values("edition").drop_duplicates(["county", "year"], keep="last").sort_values(["county", "year"])
    jobs = pd.concat(J).sort_values("edition").drop_duplicates(["county", "year"], keep="last").sort_values(["county", "year"])
    write_csv(spend, "nd_tourism_impact_county_spending.csv")
    write_csv(jobs, "nd_tourism_impact_county_jobs.csv")
    update_manifest("nd_impact", editions=sorted(pdfs), years=f"{int(spend.year.min())}–{int(spend.year.max())}", counties=int(spend.county.nunique()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

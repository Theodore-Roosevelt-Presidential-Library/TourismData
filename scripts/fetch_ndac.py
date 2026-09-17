"""ND Aeronautics Commission monthly airline passenger boardings.

NDAC posts a news release every month (~3 weeks after month-end) with a PDF
"Airline Boarding Report" attached. Page 1 of the PDF is that calendar
month's boardings for all eight ND commercial-service airports across the
last ten years, so twelve recent PDFs (one per calendar month) rebuild a
full ten-year monthly history. This is the fastest airport series available:
BTS T-100 lags about three months, NDAC about three weeks.

aero.nd.gov serves the wrong intermediate certificate, so plain TLS
verification fails. We fetch the leaf's AIA issuer certificate from Sectigo
and verify against certifi + that issuer; verification is never disabled.

Output: data/ndac_boardings.csv (year, month, airport, code, boardings)
"""
from __future__ import annotations

import io
import os
import re
import ssl
import sys
import tempfile
from datetime import date

import certifi
import pandas as pd
import pdfplumber
import requests

from common import DATA, USER_AGENT, update_manifest, write_csv

BASE = "https://aero.nd.gov"
ARCHIVE = BASE + "/news/news-archive/"
ISSUER_URL = "http://crt.sectigo.com/SectigoPublicServerAuthenticationCAOVR36.crt"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
CODES = {"Bismarck": "BIS", "Devils Lake": "DVL", "Dickinson": "DIK", "Fargo": "FAR", "Grand Forks": "GFK", "Jamestown": "JMS", "Minot": "MOT", "Williston": "ISN"}
HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    ca = tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False)
    base_bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("SSL_CERT_FILE") or certifi.where()
    ca.write(open(base_bundle).read())
    try:
        der = requests.get(ISSUER_URL, timeout=30).content
        ca.write("\n" + ssl.DER_cert_to_PEM_cert(der))
    except Exception as e:  # noqa: BLE001
        print(f"issuer cert fetch failed ({e}); trying default trust", file=sys.stderr)
    ca.close()
    # requests lets REQUESTS_CA_BUNDLE override Session.verify, so pass verify explicitly per call.
    s.verify = ca.name
    orig = s.request
    s.request = lambda method, url, **kw: orig(method, url, **{**kw, "verify": kw.get("verify") or ca.name})
    return s


def pdf_urls(month: int, year: int) -> list[str]:
    """Known filename variants. December's table is inside the calendar-year report."""
    names = [MONTHS[month - 1]] + (["Calendar_Year"] if month == 12 else [])
    return [f"{BASE}/image/cache/NDAC_{n}_{year}{sep}Airline_Boarding_Report.pdf" for n in names for sep in ("_", "_-_")]


def discover_pdfs(s: requests.Session, pages: int = 6) -> dict[tuple[int, int], str]:
    """Crawl the news archive for release pages, then their PDF links."""
    found: dict[tuple[int, int], str] = {}
    for off in range(0, pages * 10, 10):
        try:
            html = s.get(ARCHIVE, params={"offset": off, "limit": 10}, timeout=60).text
        except Exception as e:  # noqa: BLE001
            print(f"archive offset {off}: {e}", file=sys.stderr)
            break
        for slug in set(re.findall(r'href="(/news/news-archive/[^"?]+/)"', html)):
            try:
                page = s.get(BASE + slug, timeout=60).text
            except Exception:  # noqa: BLE001
                continue
            m = re.search(r'href="([^"]*NDAC_(Calendar_Year|[A-Za-z]+)_(\d{4})_(?:-_)?Airline_Boarding_Report\.pdf)"', page)
            if m and (m.group(2) in MONTHS or m.group(2) == "Calendar_Year"):
                mo = 12 if m.group(2) == "Calendar_Year" else MONTHS.index(m.group(2)) + 1
                found.setdefault((int(m.group(3)), mo), BASE + m.group(1) if m.group(1).startswith("/") else m.group(1))
    return found


def parse(pdf_bytes: bytes, month: int) -> pd.DataFrame:
    """Find the '<Month> Boardings Comparison' page and read its 10-year table."""
    mname = MONTHS[month - 1]
    text = None
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for p in pdf.pages:
            t = p.extract_text() or ""
            if re.search(rf"^{mname} Boardings Comparison", t, re.M):
                text = t
                break
    if text is None:
        raise ValueError(f"no '{mname} Boardings Comparison' page")
    pairs = re.findall(rf"{mname} (\d{{4}})", text)
    if len(pairs) < 3:  # header split over two lines: "December December ... / 2025 2024 ..."
        yl = re.search(r"^((?:\d{4}\s+){3,})", text, re.M)
        pairs = yl.group(1).split() if yl else []
    if len(pairs) < 3:
        raise ValueError("no year header")
    cols = [(mname, y) for y in pairs]
    rows = []
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Za-z ]+?)\s+((?:[\d,]+\s+){%d})" % len(cols), line)
        if not m or m.group(1).strip() not in CODES:
            continue
        vals = [int(v.replace(",", "")) for v in m.group(2).split()]
        for (mon, yr), v in zip(cols, vals):
            rows.append({"year": int(yr), "month": MONTHS.index(mon) + 1, "airport": m.group(1).strip(), "code": CODES[m.group(1).strip()], "boardings": v})
    if len({r["airport"] for r in rows}) < 8:
        raise ValueError(f"only {len({r['airport'] for r in rows})} airports parsed")
    return pd.DataFrame(rows)


def main() -> int:
    s = session()
    out = DATA / "ndac_boardings.csv"
    existing = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["year", "month", "airport", "code", "boardings"])
    today = date.today()
    discovered = None
    frames, got = [], []

    def fetch_report(y: int, mo: int):
        nonlocal discovered
        for u in pdf_urls(mo, y):
            try:
                r = s.get(u, timeout=90)
                if r.ok and r.content[:4] == b"%PDF":
                    return r.content
            except Exception:  # noqa: BLE001
                pass
        if discovered is None:
            discovered = discover_pdfs(s)
        u = discovered.get((y, mo))
        if u:
            r = s.get(u, timeout=90)
            if r.ok and r.content[:4] == b"%PDF":
                return r.content
        return None

    # For each calendar month, take the newest report that exists (each report carries ten years of that month).
    for mo in range(1, 13):
        for y in (today.year, today.year - 1, today.year - 2):
            if (y, mo) >= (today.year, today.month):
                continue
            if len(existing) and ((existing["year"] == y) & (existing["month"] == mo)).any():
                break  # newest available report for this month already ingested
            content = fetch_report(y, mo)
            if content is None:
                print(f"NDAC {y}-{mo:02d}: not posted (or broken link)", file=sys.stderr)
                continue
            try:
                df = parse(content, mo)
            except Exception as e:  # noqa: BLE001
                print(f"NDAC {y}-{mo:02d}: parse failed: {e}", file=sys.stderr)
                continue
            frames.append(df)
            got.append(f"{y}-{mo:02d}")
            print(f"NDAC {y}-{mo:02d}: {len(df)} rows ({df.year.min()}–{df.year.max()})")
            break
    if frames:
        new = pd.concat(frames)
        allv = pd.concat([existing, new]).drop_duplicates(["year", "month", "code"], keep="last")
    else:
        allv = existing
    allv = allv.sort_values(["code", "year", "month"])
    write_csv(allv, "ndac_boardings.csv")
    update_manifest("ndac", reports_ingested=got, months=int(len(allv.groupby(["year", "month"]))), latest=f"{int(allv.year.max())}-{int(allv[allv.year == allv.year.max()].month.max()):02d}" if len(allv) else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Airport passenger traffic for the regional airports, two sources:

1. BTS T-100 Domestic Market (U.S. carriers) via the TranStats download form:
   monthly passengers by origin airport, ~3-month lag. TranStats filters by
   origin STATE, so we download one zip per (state, year) for the states
   that host our airports and keep the configured airports.
   Only the current and previous year are re-downloaded each run; older
   years are kept from the existing CSV.

2. FAA Calendar-Year enplanements (annual, 2005-present, preliminary for the
   latest year). Long history, one row per airport per year.

Outputs: data/airports_monthly.csv (airport, year, month, passengers)
         data/airports_annual.csv  (airport, year, enplanements, source)
"""
from __future__ import annotations

import io
import re
import sys
import time
import zipfile

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

TRANSTATS = "https://www.transtats.bts.gov/DL_SelectFields.aspx?gnoyr_VQ=FIL&QO_fu146_anzr=Nv4%20Pn44vr45"
FAA_INDEX = "https://www.faa.gov/airports/planning_capacity/passenger_allcargo_stats/passenger"
FAA_PREV = FAA_INDEX + "/previous_years"
STATE_NAMES = {"ND": "North Dakota", "SD": "South Dakota", "MT": "Montana", "MN": "Minnesota", "WY": "Wyoming"}


def transtats_year(session: requests.Session, state: str, year: int) -> pd.DataFrame:
    soup = BeautifulSoup(session.get(TRANSTATS, timeout=120).text, "html.parser")
    data = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden") if i.get("name")}
    data.update({"cboGeography": STATE_NAMES[state], "cboYear": str(year), "cboPeriod": "All", "chkDownloadZip": "on", "btnDownload": "Download"})
    for f in ("PASSENGERS", "ORIGIN", "DEST", "YEAR", "MONTH"):
        data[f] = "on"
    r = session.post(TRANSTATS, data=data, timeout=300)
    r.raise_for_status()
    if r.content[:2] != b"PK":
        raise RuntimeError(f"TranStats did not return a zip for {state} {year}")
    z = zipfile.ZipFile(io.BytesIO(r.content))
    name = [n for n in z.namelist() if n.startswith("T_")][0]
    df = pd.read_csv(z.open(name))
    df.columns = [c.upper() for c in df.columns]
    return df


def fetch_monthly(airports: dict[str, str]) -> pd.DataFrame:
    cur = pd.Timestamp.today().year
    prev_path = DATA / "airports_monthly.csv"
    existing = pd.read_csv(prev_path) if prev_path.exists() else pd.DataFrame(columns=["airport", "year", "month", "passengers"])
    years = [cur, cur - 1] if len(existing) else list(range(int(CONFIG.get("airports_since", 2019)), cur + 1))
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    frames = []
    for state in sorted(set(airports.values())):
        codes = [a for a, st in airports.items() if st == state]
        for y in years:
            try:
                df = transtats_year(s, state, y)
                df = df[df["ORIGIN"].isin(codes)]
                g = df.groupby(["ORIGIN", "YEAR", "MONTH"])["PASSENGERS"].sum().reset_index()
                g.columns = ["airport", "year", "month", "passengers"]
                frames.append(g)
                print(f"T-100 {state} {y}: {len(g)} airport-months")
            except Exception as e:  # noqa: BLE001
                print(f"FAILED T-100 {state} {y}: {e}", file=sys.stderr)
            time.sleep(2)
    new = pd.concat(frames) if frames else pd.DataFrame(columns=existing.columns)
    keep = existing[~existing["year"].isin(years)] if len(existing) else existing
    out = pd.concat([keep, new]).drop_duplicates(["airport", "year", "month"], keep="last")
    out["passengers"] = out["passengers"].astype(int)
    return out.sort_values(["airport", "year", "month"])


def fetch_annual(airports: dict[str, str]) -> pd.DataFrame:
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    links = {}
    for page in (FAA_INDEX, FAA_PREV):
        html = s.get(page, timeout=60).text
        hrefs = re.findall(r'href="([^"]+\.xlsx?)"', html)
        # Some years (2021-2023) link to an HTML landing page that holds the xlsx link
        for sub in re.findall(r'href="(/airports/planning_capacity/passenger_allcargo_stats/passenger/cy\d\d_commercial_service_enplanements)"', html):
            try:
                hrefs += re.findall(r'href="([^"]+\.xlsx?)"', s.get("https://www.faa.gov" + sub, timeout=60).text)
            except Exception as e:  # noqa: BLE001
                print(f"FAILED FAA landing {sub}: {e}", file=sys.stderr)
        for href in hrefs:
            low = href.lower().rsplit("/", 1)[-1]  # filename only; the path contains "allcargo"
            if "enplan" not in low or "cargo" in low or "npcs" in low or "primary" in low:
                continue
            if "commercial" in low or "cs_enplan" in low or "all" in low:
                m = re.search(r"cy[-_]?(\d{2,4})", low)
                if not m:
                    continue
                yy = int(m.group(1))
                year = yy if yy > 1999 else 2000 + yy
                # prefer commercial-service file; fall back to all-enplanements
                rank = 0 if ("commercial" in low or "cs_enplan" in low) else 1
                if year not in links or rank < links[year][0]:
                    links[year] = (rank, "https://www.faa.gov" + href if href.startswith("/") else href)
    rows = []
    for year, (_, url) in sorted(links.items()):
        try:
            raw = pd.read_excel(io.BytesIO(s.get(url, timeout=120).content), header=None)
            hdr = next(i for i in range(15) if any("locid" in str(x).lower() for x in raw.iloc[i]))
            df = raw.iloc[hdr + 1 :].copy()
            df.columns = [str(c).strip() for c in raw.iloc[hdr]]
            loc = next(c for c in df.columns if c.lower() == "locid")
            col = next(c for c in df.columns if "enplanement" in c.lower() and str(year)[2:] in c.replace(" ", ""))
            d = df[df[loc].isin(airports)][[loc, col]]
            for _, r in d.iterrows():
                if pd.notna(r[col]):
                    rows.append({"airport": r[loc], "year": year, "enplanements": int(r[col]), "source": "FAA CY" + str(year)})
            print(f"FAA CY{year}: {len(d)} airports")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED FAA CY{year}: {e}", file=sys.stderr)
        time.sleep(1)
    return pd.DataFrame(rows).sort_values(["airport", "year"])


def main() -> int:
    airports = CONFIG.get("airports", {"DIK": "ND", "BIS": "ND", "FAR": "ND", "MOT": "ND", "BIL": "MT", "RAP": "SD"})
    monthly = fetch_monthly(airports)
    if len(monthly):
        write_csv(monthly, "airports_monthly.csv")
    annual = fetch_annual(airports)
    if len(annual):
        write_csv(annual, "airports_annual.csv")
    latest = monthly.sort_values(["year", "month"]).iloc[-1] if len(monthly) else None
    update_manifest(
        "airports",
        monthly_latest=f"{int(latest.year)}-{int(latest.month):02d}" if latest is not None else None,
        annual_years=[int(annual.year.min()), int(annual.year.max())] if len(annual) else None,
    )
    return 0 if len(monthly) or len(annual) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Pull monthly local-tax distributions to ND cities from the State Treasurer's
Historical Distribution Search (apps.nd.gov/stn/inquiry).

The Tax Commissioner's statistical workbook stops at the county (Medora is
suppressed from the city tables), but the Treasurer publishes every payment
it makes to a city: City Sales Tax and City/County Occupancy (lodging) tax,
by payment date. That is the only public town-level series for Medora, and
it covers the corridor towns too.

Timing: a payment dated the 20th-ish of month M is the state's distribution
of returns filed in month M-1 for sales in month M-2 (monthly filers), plus
whatever quarterly/annual filers remitted. So compare payment months
year-over-year rather than reading a single month as one sales month, and
expect lumps (e.g. the November payment carries Q3 quarterly filers).

The site is an ASP.NET WebForms page: GET for the viewstate, then POST the
form. Cities and distribution types come from config/sources.json.

Output: data/nd_city_tax_distributions_monthly.csv
        (city, county, dist_type, payment_date, year, month, amount)
"""
from __future__ import annotations

import sys
import time

import pandas as pd
import requests
from bs4 import BeautifulSoup

from common import CONFIG, USER_AGENT, update_manifest, write_csv

URL = "https://apps.nd.gov/stn/inquiry/search.aspx?searchtype=city"
PFX = "ctl00$ContentPlaceHolder1$"
DIST_LABELS = {"CITY SALES": "City Sales Tax", "OCCUPANCY": "City/County Occupancy", "REST/LODG": "City/County Restaurant & Lodging"}


def search(session: requests.Session, city: str, dist: str, begin: str, end: str) -> list[dict]:
    soup = BeautifulSoup(session.get(URL, timeout=60).text, "html.parser")
    data = {i["name"]: i.get("value", "") for i in soup.find_all("input", type="hidden")}
    data.update(
        {
            PFX + "ddlCityName": city,
            PFX + "ddlCityDistType": dist,
            PFX + "txtCityBeginDate": begin,
            PFX + "txtCityEndDate": end,
            PFX + "btnSearch": "Search",
        }
    )
    r = session.post(URL, data=data, timeout=120)
    r.raise_for_status()
    out = []
    for table in BeautifulSoup(r.text, "html.parser").find_all("table"):
        for tr in table.find_all("tr"):
            cells = [c.get_text(strip=True) for c in tr.find_all("td")]
            if len(cells) == 7 and cells[0][:1].isdigit():
                d = pd.to_datetime(cells[0], format="%m/%d/%Y")
                out.append(
                    {
                        "city": cells[2],
                        "county": cells[1].replace(" County", ""),
                        "dist_type": cells[5],
                        "payment_date": d.strftime("%Y-%m-%d"),
                        "year": d.year,
                        "month": d.month,
                        "amount": float(cells[6].replace(",", "")),
                    }
                )
    return out


def main() -> int:
    cfg = CONFIG.get("nd_treasurer", {})
    cities = cfg.get("cities", ["Medora"])
    dists = cfg.get("dist_types", ["CITY SALES", "OCCUPANCY"])
    begin = cfg.get("since", "01/01/2019")
    end = pd.Timestamp.today().strftime("%m/%d/%Y")
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    rows, failures = [], []
    for city in cities:
        for dist in dists:
            try:
                got = search(s, city, dist, begin, end)
                print(f"{city} / {DIST_LABELS.get(dist, dist)}: {len(got)} payments")
                rows.extend(got)
            except Exception as e:  # noqa: BLE001
                print(f"FAILED {city} / {dist}: {e}", file=sys.stderr)
                failures.append(f"{city}/{dist}")
            time.sleep(0.5)
    if not rows:
        print("no treasurer rows fetched", file=sys.stderr)
        return 1
    df = pd.DataFrame(rows).drop_duplicates().sort_values(["city", "dist_type", "payment_date"])
    write_csv(df, "nd_city_tax_distributions_monthly.csv")
    update_manifest("nd_city_tax_distributions", rows=len(df), cities=sorted(df["city"].unique().tolist()), latest_payment=df["payment_date"].max(), failed=failures)
    return 0 if not failures else 2


if __name__ == "__main__":
    sys.exit(main())

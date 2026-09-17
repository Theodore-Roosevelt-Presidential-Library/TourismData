"""Daily air quality at Theodore Roosevelt NP (Painted Canyon Visitor Center
monitor, AQS 38-007-0002) — the wildfire-smoke control for summer visitation.

Two sources stitched together:
  * EPA AQS pre-generated "daily AQI by county" files (one zip per year,
    https://aqs.epa.gov/aqsweb/airdata/) for Billings County — the
    validated history, 2015 to the last processed quarter.
  * AirNow's public daily files (https://files.airnowtech.org/airnow/YYYY/
    YYYYMMDD/daily_data_v2.dat) for the site, to fill from the end of the
    AQS data to yesterday — preliminary, not yet validated.

Daily AQI is the maximum of the pollutant AQIs (PM2.5 24-hr and ozone 8-hr
are the ones that matter here); PM2.5 concentration is kept as the smoke
signal. Days with AQI >= 101 ("unhealthy for sensitive groups") are the
"smoke days" the dashboard counts.

Output: data/air_quality_daily.csv (date, aqi, category, main_pollutant, pm25, source)
"""
from __future__ import annotations

import io
import sys
import zipfile
from datetime import date, timedelta

import pandas as pd
import requests

from common import DATA, USER_AGENT, update_manifest, write_csv

AQS = "https://aqs.epa.gov/aqsweb/airdata/daily_aqi_by_county_{y}.zip"
AIRNOW = "https://files.airnowtech.org/airnow/{y}/{ymd}/daily_data_v2.dat"
SITE = "380070002"
COUNTY = ("North Dakota", "Billings")
HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}
CATS = [(50, "Good"), (100, "Moderate"), (150, "Unhealthy for Sensitive Groups"), (200, "Unhealthy"), (300, "Very Unhealthy"), (10_000, "Hazardous")]


def category(aqi: float) -> str:
    return next(c for lim, c in CATS if aqi <= lim)


def aqs_year(y: int) -> pd.DataFrame:
    r = requests.get(AQS.format(y=y), headers=HEADERS, timeout=300)
    if r.status_code == 404:
        return pd.DataFrame()
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    df = pd.read_csv(z.open(z.namelist()[0]))
    df = df[(df["State Name"] == COUNTY[0]) & (df["county Name"] == COUNTY[1])]
    return pd.DataFrame({"date": df["Date"], "aqi": df["AQI"], "category": df["Category"], "main_pollutant": df["Defining Parameter"], "pm25": None, "source": "aqs"})


def airnow_day(d: date) -> dict | None:
    r = requests.get(AIRNOW.format(y=d.year, ymd=d.strftime("%Y%m%d")), headers=HEADERS, timeout=120)
    if not r.ok:
        return None
    best, pm25 = None, None
    for line in r.text.splitlines():
        f = line.split("|")
        if len(f) < 10 or f[1] != SITE:
            continue
        param, val, aqi = f[3], f[5], f[8]
        try:
            aqi_v = float(aqi)
        except ValueError:
            continue
        if param.startswith("PM2.5"):
            pm25 = float(val) if val not in ("", "-999") else None
        if aqi_v >= 0 and (best is None or aqi_v > best[0]):
            best = (aqi_v, param)
    if best is None:
        return None
    return {"date": d.isoformat(), "aqi": best[0], "category": category(best[0]), "main_pollutant": best[1], "pm25": pm25, "source": "airnow"}


def main() -> int:
    out = DATA / "air_quality_daily.csv"
    existing = pd.read_csv(out) if out.exists() else pd.DataFrame(columns=["date", "aqi", "category", "main_pollutant", "pm25", "source"])
    today = date.today()
    frames = []
    # AQS: years not fully validated yet get re-pulled (current and previous year).
    done_years = set(int(str(d)[:4]) for d in existing[existing["source"] == "aqs"]["date"]) if len(existing) else set()
    for y in range(2015, today.year + 1):
        if y in done_years and y < today.year - 1:
            continue
        try:
            df = aqs_year(y)
            if len(df):
                frames.append(df)
                print(f"AQS {y}: {len(df)} days")
        except Exception as e:  # noqa: BLE001
            print(f"AQS {y}: {e}", file=sys.stderr)
    aqs = pd.concat([existing[existing["source"] == "aqs"], *frames]).drop_duplicates("date", keep="last") if frames else existing[existing["source"] == "aqs"]
    last_aqs = pd.to_datetime(aqs["date"]).max().date() if len(aqs) else date(today.year, 1, 1)
    # AirNow: from the day after AQS ends to yesterday (keep prior AirNow rows only beyond AQS coverage).
    an_prev = existing[(existing["source"] == "airnow") & (pd.to_datetime(existing["date"]).dt.date > last_aqs)] if len(existing) else existing.iloc[0:0]
    have = set(an_prev["date"])
    rows = []
    d = last_aqs + timedelta(days=1)
    while d < today:
        if d.isoformat() not in have or d >= today - timedelta(days=3):
            try:
                r = airnow_day(d)
                if r:
                    rows.append(r)
            except Exception as e:  # noqa: BLE001
                print(f"AirNow {d}: {e}", file=sys.stderr)
        d += timedelta(days=1)
    an = pd.concat([an_prev, pd.DataFrame(rows)]).drop_duplicates("date", keep="last") if rows else an_prev
    allv = pd.concat([aqs, an]).sort_values("date")
    allv["date"] = pd.to_datetime(allv["date"]).dt.strftime("%Y-%m-%d")
    write_csv(allv, "air_quality_daily.csv")
    update_manifest("air_quality", aqs_through=str(last_aqs), latest=str(allv["date"].max()), airnow_days=int(len(an)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

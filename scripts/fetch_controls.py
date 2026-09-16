"""Control series that explain visitation noise, all keyless public feeds:

  * Weather at Dickinson (NOAA GHCN-Daily station USW00024012) via the NCEI
    Access API: daily precipitation and max temperature -> monthly rain days
    (PRCP >= 0.10 in), mean TMAX, days >= 90F.
  * Midwest (PADD 2) weekly regular gasoline price from EIA's history XLS
    -> monthly average.
  * CAD/USD from FRED (DEXCAUS, USD per CAD inverted to CAD per USD) ->
    monthly average.
  * North Dakota oil: monthly production and rig count from the ND
    Industrial Commission's yearly "Monthly Statistical Update" PDF. The
    corridor towns west of Dickinson ride the oil cycle, so this separates
    oil from tourism in their tax numbers.

Output: data/controls_monthly.csv
        (year, month, rain_days, tmax_mean_f, hot_days_90f, gas_midwest_usd,
         cad_per_usd, nd_oil_bbl_per_day, nd_rig_count)
"""
from __future__ import annotations

import io
import re
import sys

import pandas as pd
import pdfplumber
import requests

from common import CONFIG, USER_AGENT, update_manifest, write_csv

NOAA = "https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations={station}&startDate={start}&endDate={end}&dataTypes=PRCP,TMAX&format=csv&units=standard"
EIA = "https://www.eia.gov/dnav/pet/hist_xls/EMM_EPMR_PTE_R20_DPGw.xls"  # Midwest regular, weekly
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXCAUS"
NDIC = "https://www.dmr.nd.gov/oilgas/stats/{year}monthlystats.pdf"
MON = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def weather(station: str, since: str) -> pd.DataFrame:
    end = pd.Timestamp.today().strftime("%Y-%m-%d")
    r = requests.get(NOAA.format(station=station, start=since, end=end), headers={"User-Agent": USER_AGENT}, timeout=180)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text))
    d["DATE"] = pd.to_datetime(d["DATE"])
    d["year"], d["month"] = d["DATE"].dt.year, d["DATE"].dt.month
    d["PRCP"] = pd.to_numeric(d["PRCP"], errors="coerce")
    d["TMAX"] = pd.to_numeric(d["TMAX"], errors="coerce")
    g = d.groupby(["year", "month"]).agg(rain_days=("PRCP", lambda s: int((s >= 0.10).sum())), tmax_mean_f=("TMAX", "mean"), hot_days_90f=("TMAX", lambda s: int((s >= 90).sum())), obs_days=("DATE", "count")).reset_index()
    g["tmax_mean_f"] = g["tmax_mean_f"].round(1)
    return g[g["obs_days"] >= 20].drop(columns="obs_days")


def gas() -> pd.DataFrame:
    r = requests.get(EIA, headers={"User-Agent": USER_AGENT}, timeout=120)
    r.raise_for_status()
    d = pd.read_excel(io.BytesIO(r.content), sheet_name="Data 1", header=2)
    d.columns = ["date", "price"]
    d["date"] = pd.to_datetime(d["date"])
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    return d.groupby(["year", "month"])["price"].mean().round(3).reset_index().rename(columns={"price": "gas_midwest_usd"})


def cad() -> pd.DataFrame:
    d = pd.read_csv(FRED)
    d.columns = ["date", "rate"]
    d["rate"] = pd.to_numeric(d["rate"], errors="coerce")
    d["date"] = pd.to_datetime(d["date"])
    d["year"], d["month"] = d["date"].dt.year, d["date"].dt.month
    return d.groupby(["year", "month"])["rate"].mean().round(4).reset_index().rename(columns={"rate": "cad_per_usd"})


def nd_oil(since_year: int) -> pd.DataFrame:
    rows = []
    for year in range(since_year, pd.Timestamp.today().year + 1):
        try:
            r = requests.get(NDIC.format(year=year), headers={"User-Agent": USER_AGENT}, timeout=60)
            if r.status_code != 200:
                continue
            with pdfplumber.open(io.BytesIO(r.content)) as pdf:
                text = pdf.pages[0].extract_text() or ""
            for line in text.splitlines():
                m = re.match(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+(.*)$", line)
                if not m:
                    continue
                rest = m.group(5).split()
                rig = int(rest[-1]) if rest and rest[-1].isdigit() else None
                rows.append({"year": year, "month": MON[m.group(1)], "nd_oil_bbl_per_day": int(m.group(4).replace(",", "")), "nd_rig_count": rig})
        except Exception as e:  # noqa: BLE001
            print(f"NDIC {year}: {e}", file=sys.stderr)
    return pd.DataFrame(rows)


def main() -> int:
    cfg = CONFIG.get("controls", {})
    since = cfg.get("since", "2015-01-01")
    frames = []
    for name, fn in (("weather", lambda: weather(cfg.get("noaa_station", "USW00024012"), since)), ("gas", gas), ("cad", cad), ("nd_oil", lambda: nd_oil(int(since[:4])))):
        try:
            f = fn()
            print(f"{name}: {len(f)} months")
            frames.append(f)
        except Exception as e:  # noqa: BLE001
            print(f"FAILED {name}: {e}", file=sys.stderr)
    if not frames:
        return 1
    out = frames[0]
    for f in frames[1:]:
        out = out.merge(f, on=["year", "month"], how="outer")
    out = out[out["year"] >= int(since[:4])].sort_values(["year", "month"])
    write_csv(out, "controls_monthly.csv")
    update_manifest("controls_monthly", rows=len(out), columns=[c for c in out.columns if c not in ("year", "month")])
    return 0


if __name__ == "__main__":
    sys.exit(main())

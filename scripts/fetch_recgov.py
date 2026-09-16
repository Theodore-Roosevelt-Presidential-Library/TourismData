"""Aggregate Recreation.gov reservations for the campgrounds in and around
Medora from the RIDB historical reservation files.

Recreation.gov publishes one ~500 MB zip per fiscal year (Oct-Sep) at
https://ridb.recreation.gov/downloads/reservations{FY}.zip with every
reservation on the platform, including customer ZIP. We stream the CSV,
keep North Dakota facilities plus anything under Theodore Roosevelt NP or
the Dakota Prairie Grasslands, and write only AGGREGATES:

  * monthly arrivals per facility (reservations, nights, people, revenue)
  * origin state shares per facility per calendar year (from customer ZIP)

Raw rows are discarded. Fiscal years already present in the outputs are not
re-downloaded; the current fiscal year's file appears after the FY closes
(the FY2025 file was posted in early 2026), so this feed is annual.

Outputs: data/recgov_monthly.csv
           (facility, park, agency, year, month, reservations, nights, people, revenue)
         data/recgov_origin_annual.csv
           (facility, year, state, reservations, share)
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

URL = "https://ridb.recreation.gov/downloads/reservations{fy}.zip"
COLS = ["agency", "parentlocation", "park", "facilityid", "facilitystate", "customerzip", "startdate", "nights", "numberofpeople", "totalpaid"]


def zip_to_state(z: str) -> str | None:
    try:
        import zipcodes  # noqa: PLC0415

        z = str(z).strip()[:5]
        if len(z) < 5:
            return None
        m = zipcodes.matching(z)
        return m[0]["state"] if m else None
    except Exception:  # noqa: BLE001
        return None


def process_fy(fy: int, facilities_match: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    tmp = Path(tempfile.mkdtemp(prefix="recgov_"))
    try:
        zpath = tmp / f"res{fy}.zip"
        with requests.get(URL.format(fy=fy), headers={"User-Agent": USER_AGENT}, stream=True, timeout=1800) as r:
            r.raise_for_status()
            with open(zpath, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
        z = zipfile.ZipFile(zpath)
        keep = []
        with z.open(z.namelist()[0]) as fh:
            for chunk in pd.read_csv(fh, usecols=COLS, chunksize=500_000, dtype=str):
                m = chunk[
                    (chunk["facilitystate"] == "ND")
                    | chunk["park"].fillna("").str.contains(facilities_match, case=False, regex=True)
                    | chunk["parentlocation"].fillna("").str.contains(facilities_match, case=False, regex=True)
                ]
                keep.append(m)
        df = pd.concat(keep)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    df = df[df["park"].fillna("").str.contains("Campground|Camp|Group Site", case=False)]
    df["start"] = pd.to_datetime(df["startdate"], errors="coerce")
    df = df.dropna(subset=["start"])
    for c in ("nights", "numberofpeople", "totalpaid"):
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    df["year"] = df["start"].dt.year
    df["month"] = df["start"].dt.month
    monthly = (
        df.groupby(["park", "parentlocation", "agency", "year", "month"])
        .agg(reservations=("startdate", "size"), nights=("nights", "sum"), people=("numberofpeople", "sum"), revenue=("totalpaid", "sum"))
        .reset_index()
        .rename(columns={"park": "facility", "parentlocation": "park"})
    )
    monthly["fy"] = fy
    df["state"] = df["customerzip"].map(zip_to_state)
    org = df.dropna(subset=["state"]).groupby(["park", "year", "state"]).size().reset_index(name="reservations").rename(columns={"park": "facility"})
    org["share"] = (org["reservations"] / org.groupby(["facility", "year"])["reservations"].transform("sum")).round(4)
    org["fy"] = fy
    return monthly, org


def main() -> int:
    cfg = CONFIG.get("recgov", {})
    fys = cfg.get("fiscal_years", [2023, 2024, 2025])
    match = cfg.get("match", "Theodore Roosevelt|Dakota Prairie|Little Missouri")
    mp, op = DATA / "recgov_monthly.csv", DATA / "recgov_origin_annual.csv"
    monthly = pd.read_csv(mp) if mp.exists() else pd.DataFrame()
    origin = pd.read_csv(op) if op.exists() else pd.DataFrame()
    done = set(monthly["fy"].unique()) if len(monthly) else set()
    for fy in fys:
        if fy in done:
            continue
        try:
            m, o = process_fy(fy, match)
            print(f"FY{fy}: {len(m)} facility-months, {m.reservations.sum()} reservations")
            monthly = pd.concat([monthly, m])
            origin = pd.concat([origin, o])
        except Exception as e:  # noqa: BLE001
            print(f"FAILED FY{fy}: {e}", file=sys.stderr)
    if not len(monthly):
        return 1
    # Facility names drifted ("Cottonwood Campground" vs "Cottonwood Campground (ND)"); normalize
    for frame in (monthly, origin):
        frame["facility"] = frame["facility"].str.replace(r"\s*\(ND\)$", "", regex=True).str.strip()
    # A calendar month can appear in two FY files (Oct-Dec); sum them
    monthly = monthly.groupby(["facility", "park", "agency", "year", "month"], as_index=False).agg(
        reservations=("reservations", "sum"), nights=("nights", "sum"), people=("people", "sum"), revenue=("revenue", "sum"), fy=("fy", "max")
    )
    origin = origin.groupby(["facility", "year", "state"], as_index=False).agg(reservations=("reservations", "sum"), fy=("fy", "max"))
    origin["share"] = (origin["reservations"] / origin.groupby(["facility", "year"])["reservations"].transform("sum")).round(4)
    write_csv(monthly.sort_values(["facility", "year", "month"]), "recgov_monthly.csv")
    write_csv(origin.sort_values(["facility", "year", "reservations"], ascending=[True, True, False]), "recgov_origin_annual.csv")
    update_manifest("recgov", fiscal_years=sorted(int(x) for x in monthly["fy"].unique()), facilities=sorted(monthly["facility"].unique().tolist()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

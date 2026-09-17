"""BTS Airline Origin and Destination Survey (DB1B): where people who fly
into the region's airports actually start their trips.

DB1B is a 10% sample of airline tickets, quarterly. The Coupon file lists
every flight segment of each sampled itinerary; the Ticket file carries the
itinerary's true origin (the traveler's home airport). Joining the two —
itineraries with a coupon landing at BIS, DIK, FAR or MOT, and a ticket
origin somewhere else — gives inbound visitors by home airport, which the
market-level file cannot (a Denver resident's DEN→BIS and a Bismarck
resident's return DEN→BIS look identical there).

Files are BTS's prezipped quarterly archives (~250 MB Coupon + ~100 MB
Ticket per quarter; the custom-download form returns 404 for this table).
Each quarter is downloaded once; only aggregates (origin airport × arrival
airport × quarter, sampled passengers ×10) are stored. Quarters from
`db1b.since` in config; BTS posts a quarter roughly six months after it ends.

Output: data/db1b_inbound_quarterly.csv (year, quarter, dest, origin, origin_state,
        origin_city_market_id, passengers_sampled, passengers_est, round_trip_share)
"""
from __future__ import annotations

import io
import sys
import time
import zipfile
from datetime import date

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

PREZIP = "https://transtats.bts.gov/PREZIP/Origin_and_Destination_Survey_{kind}_{y}_{q}.zip"
HEADERS = {"User-Agent": USER_AGENT + " Mozilla/5.0"}


def get_zip(kind: str, y: int, q: int) -> bytes | None:
    for attempt in range(3):
        try:
            r = requests.get(PREZIP.format(kind=kind, y=y, q=q), headers=HEADERS, timeout=1800)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.content
        except requests.exceptions.ConnectionError:
            if attempt == 2:
                raise
            time.sleep(10)
    return None


def read_zip_csv(zip_bytes: bytes, usecols: list[str], chunksize: int = 2_000_000):
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
    with z.open(name) as f:
        yield from pd.read_csv(f, usecols=usecols, dtype=str, chunksize=chunksize)


def quarter(y: int, q: int, dests: set[str]) -> pd.DataFrame | None:
    cz = get_zip("DB1BCoupon", y, q)
    if cz is None:
        return None
    parts = [ch[ch["Dest"].isin(dests)] for ch in read_zip_csv(cz, ["ItinID", "Dest"])]
    coup = pd.concat(parts).drop_duplicates() if parts else pd.DataFrame(columns=["ItinID", "Dest"])
    del cz, parts
    tz = get_zip("DB1BTicket", y, q)
    if tz is None:
        return None
    want = set(coup["ItinID"])
    parts = [ch[ch["ItinID"].isin(want) & ~ch["Origin"].isin(dests)] for ch in read_zip_csv(tz, ["ItinID", "Origin", "OriginState", "OriginCityMarketID", "RoundTrip", "Passengers"])]
    tick = pd.concat(parts) if parts else pd.DataFrame()
    del tz, parts
    cols = ["year", "quarter", "dest", "origin", "origin_state", "origin_city_market_id", "passengers_sampled", "passengers_est", "round_trip_share"]
    if tick.empty:
        return pd.DataFrame(columns=cols)
    tick["Passengers"] = pd.to_numeric(tick["Passengers"], errors="coerce").fillna(0)
    tick["rt"] = (pd.to_numeric(tick["RoundTrip"], errors="coerce").fillna(0) > 0) * tick["Passengers"]
    m = coup.merge(tick, on="ItinID")
    g = m.groupby(["Dest", "Origin", "OriginState", "OriginCityMarketID"], as_index=False).agg(passengers_sampled=("Passengers", "sum"), rt=("rt", "sum"))
    g["year"], g["quarter"] = y, q
    g["passengers_est"] = (g["passengers_sampled"] * 10).round().astype(int)
    g["round_trip_share"] = (g["rt"] / g["passengers_sampled"]).round(3)
    g["passengers_sampled"] = g["passengers_sampled"].round(1)
    return g.rename(columns={"Dest": "dest", "Origin": "origin", "OriginState": "origin_state", "OriginCityMarketID": "origin_city_market_id"})[cols]


def main() -> int:
    cfg = CONFIG.get("db1b", {})
    dests = set(cfg.get("airports", ["BIS", "DIK"]))
    since = int(cfg.get("since", 2023))
    out = DATA / "db1b_inbound_quarterly.csv"
    existing = pd.read_csv(out) if out.exists() else pd.DataFrame()
    have = set(zip(existing["year"], existing["quarter"])) if len(existing) else set()
    today = date.today()
    frames, got, missing = [], [], []
    for y in range(since, today.year + 1):
        for q in range(1, 5):
            if (y, q) in have or (y, q) > (today.year, (today.month - 1) // 3 + 1):
                continue
            try:
                df = quarter(y, q, dests)
            except Exception as e:  # noqa: BLE001
                print(f"DB1B {y}Q{q}: {e}", file=sys.stderr)
                continue
            if df is None:
                missing.append(f"{y}Q{q}")
                continue
            frames.append(df)
            got.append(f"{y}Q{q}")
            print(f"DB1B {y}Q{q}: {int(df.passengers_est.sum()):,} est. inbound passengers to {sorted(dests)}", flush=True)
            # Save after every quarter: each one is a ~350 MB download and a run can be cut short.
            allv = pd.concat([existing, *frames]).sort_values(["year", "quarter", "dest", "passengers_est"], ascending=[True, True, True, False])
            write_csv(allv, "db1b_inbound_quarterly.csv")
    allv = pd.concat([existing, *frames]) if frames else existing
    if not len(allv):
        print("no DB1B rows", file=sys.stderr)
        return 1
    allv = allv.sort_values(["year", "quarter", "dest", "passengers_est"], ascending=[True, True, True, False])
    write_csv(allv, "db1b_inbound_quarterly.csv")
    update_manifest("db1b", quarters_added=got, not_posted=missing[-4:], latest=f"{int(allv.year.max())}Q{int(allv[allv.year == allv.year.max()].quarter.max())}", airports=sorted(dests))
    return 0


if __name__ == "__main__":
    sys.exit(main())

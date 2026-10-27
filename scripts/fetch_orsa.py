"""BEA Outdoor Recreation Satellite Account, by state (annual).

Table 1 of BEA's state ORSA workbook: outdoor recreation value added,
employment and compensation for every state, each with its share of the
state total. One consistent measure of how much of each state's economy is
outdoor recreation — ND next to SD, MT, WY and MN. Each edition covers one
year and is released in the fall (the 2024 edition slipped to March 2026);
editions accumulate here. The current workbook is found on BEA's ORSA page
(`*-state.xlsx`); `orsa.extra_urls` pins earlier editions.

Output: data/orsa_state_annual.csv
        (year, state, value_added_k, value_added_share_pct, employment, employment_share_pct,
         compensation_k, compensation_share_pct)
"""
from __future__ import annotations

import io
import re
import sys

import pandas as pd
import requests

from common import CONFIG, DATA, update_manifest, write_csv

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) TRPL-TourismData"}
COLS = ["value_added_k", "value_added_share_pct", "employment", "employment_share_pct", "compensation_k", "compensation_share_pct"]


def parse(content: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(content), sheet_name=0, header=None)
    year = int(re.search(r"(\d{4})\s*$", str(raw.iloc[0, 0]).strip()).group(1))
    rows = []
    for i in range(2, len(raw)):
        name = re.sub(r"\d+$", "", str(raw.iloc[i, 0]).strip()).strip()
        vals = [pd.to_numeric(raw.iloc[i, j], errors="coerce") for j in range(1, 7)]
        if not name or name == "nan" or pd.isna(vals[0]):
            continue
        rows.append({"year": year, "state": name, **{c: float(v) if pd.notna(v) else None for c, v in zip(COLS, vals)}})
    return pd.DataFrame(rows)


def main() -> int:
    cfg = CONFIG.get("orsa", {})
    urls = list(cfg.get("extra_urls", []))
    page = requests.get(cfg["page"], headers=HEADERS, timeout=60).text
    urls += ["https://www.bea.gov" + h if h.startswith("/") else h for h in re.findall(r'href="([^"]+-state\.xlsx)"', page)]
    frames = []
    for u in dict.fromkeys(urls):
        try:
            r = requests.get(u, headers=HEADERS, timeout=120)
            r.raise_for_status()
            df = parse(r.content)
            frames.append(df)
            print(f"ORSA {df['year'].iloc[0]}: {len(df)} rows from {u}")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED ORSA {u}: {e}", file=sys.stderr)
    path = DATA / "orsa_state_annual.csv"
    existing = pd.read_csv(path) if path.exists() else pd.DataFrame()
    df = pd.concat([existing, *frames]) if frames else existing
    if not len(df):
        return 1
    df = df.drop_duplicates(["year", "state"], keep="last").sort_values(["state", "year"])
    write_csv(df, "orsa_state_annual.csv")
    update_manifest("orsa", latest=str(int(df["year"].max())), years=sorted(int(y) for y in df["year"].unique()))
    return 0


if __name__ == "__main__":
    sys.exit(main())

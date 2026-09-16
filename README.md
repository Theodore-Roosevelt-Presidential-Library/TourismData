# TourismData

Gathers regional visitation indicators around the Theodore Roosevelt Presidential Library and publishes a dashboard on GitHub Pages.

**Dashboard:** https://theodore-roosevelt-presidential-library.github.io/TourismData/

## What it tracks

| Feed | Source | Grain | Script |
|---|---|---|---|
| Recreation visits, 8 NPS units (TRNP + regional comparison parks) | NPS IRMA STATS, "Recreation Visitors By Month" report | Monthly, 1979–present | `scripts/fetch_nps.py` |
| Inbound land-border crossings, ND and MT ports | BTS Border Crossing Entry Data (Socrata `keg4-3bc2`) | Monthly by port, 2019–present | `scripts/fetch_bts_border.py` |
| Airport enplanements (DIK, BIS, BIL, RAP, FAR, MOT) | BTS T-100 via USDOT geodata service | Annual snapshot | `scripts/fetch_bts_airports.py` |

Parks and ports are configured in `config/sources.json`. The Library's opening date (2026-07-04) drives the "since opening" comparisons.

## How it runs

`.github/workflows/update-data.yml` runs on the 16th of each month (NPS posts the prior month around the 15th), on manual dispatch, and on pushes that touch the scripts or page. It fetches each feed, rebuilds `docs/data/dashboard.json`, commits any changed data, and deploys `docs/` to GitHub Pages.

Each fetcher is independent: if one source is down the others still refresh, and `data/manifest.json` records what was fetched when.

## Run locally

```bash
pip install -r requirements.txt
python scripts/fetch_nps.py
python scripts/fetch_bts_border.py
python scripts/fetch_bts_airports.py
python scripts/build.py
python -m http.server -d docs 8000   # open http://localhost:8000
```

## Data notes

- NPS monthly figures are preliminary until the annual close in Q1. A current-year month posted as `0` is treated as not yet reported.
- Little Bighorn Battlefield's 2025 counts look like a counter outage (July 2025 = 7,631 vs 25,896 in 2024). The dashboard flags parks whose prior-year peak season is under half of the year before and excludes them from the control-park median.
- BTS border data is reported at the port level; Pembina and Portal carry most ND traffic.
- The airport feed is annual only. Monthly T-100 detail lives behind the BTS TranStats download form (no stable API) and is a to-do.

## Roadmap

- NPS sub-unit detail (South Unit, Painted Canyon) if a per-location report can be exported the same way.
- ND Tax Commissioner quarterly taxable sales (accommodation and food services, Billings/Stark/Burleigh counties).
- Monthly airport enplanements via TranStats.
- Phase 2: Library admissions (Altru SKY API) and GA4, joined by date to compute capture rate (admissions ÷ TRNP South Unit visits) and new-market share.

Planning doc: *Visitor Impact Data Plan* (Claude doc) and `TRPL / Visitor Impact Data Plan — source inventory` in Outline.

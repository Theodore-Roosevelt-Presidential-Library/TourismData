# TourismData

Gathers regional visitation indicators around the Theodore Roosevelt Presidential Library and publishes a dashboard on GitHub Pages.

**Dashboard:** https://theodore-roosevelt-presidential-library.github.io/TourismData/

## What it tracks

| Feed | Source | Grain | Script |
|---|---|---|---|
| Recreation visits, 8 NPS units (TRNP + regional comparison parks) | NPS IRMA STATS, "Recreation Visitors By Month" report | Monthly, 1979–present | `scripts/fetch_nps.py` |
| Inbound land-border crossings, ND and MT ports | BTS Border Crossing Entry Data (Socrata `keg4-3bc2`) | Monthly by port, 2019–present | `scripts/fetch_bts_border.py` |
| Airport passengers (DIK, BIS, FAR, MOT, BIL, RAP) | BTS T-100 Domestic Market via the TranStats download form (monthly) + FAA calendar-year enplanements (annual) | Monthly 2019–present (~3-mo lag); annual 2005–present | `scripts/fetch_airports.py` |
| I-94 and US 85 traffic near Medora (NDDOT permanent counters 279, 221, 223) | NDDOT monthly "Automatic Traffic Data" PDF reports | Monthly average daily traffic, weekday/weekend, 2024–present | `scripts/fetch_nddot_atr.py` |
| Taxable sales and purchases, all ND counties + statewide industry sectors | ND Office of State Tax Commissioner, statistical-report workbook | Quarterly, 2019–present | `scripts/fetch_nd_tax.py` |
| City sales tax and occupancy (lodging) tax paid to Medora, Beach, Belfield, Dickinson, Watford City, Killdeer, Bowman | ND State Treasurer, Historical Distribution Search | Monthly payments, 2019–present | `scripts/fetch_nd_treasurer.py` |
| Montana nonresident visitation + survey shares (entry point, origin state) | ITRR (Univ. of Montana) Tableau Public workbook, embedded Hyper extracts | Monthly 1991–present; survey quarterly 2021–present | `scripts/fetch_mt_itrr.py` |
| Wyoming county travel impacts (spend, earnings, jobs, tax) | Dean Runyan Associates PDF for the Wyoming Office of Tourism | Annual, 2015–present | `scripts/fetch_wy_impacts.py` |

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
- Little Bighorn Battlefield's 2025 counts look like a counter outage (July 2025 = 7,631 vs 25,896 in 2024). The dashboard flags parks whose year-over-year change exceeds 100% and excludes them from the control-park median.
- BTS border data is reported at the port level; Pembina and Portal carry most ND traffic.
- ND taxable sales: Billings County total is the county-level Medora proxy. Medora is suppressed from the Commissioner's city tables (towns far smaller than Medora appear, so this is confidentiality, not size). Industry sectors are statewide only; county × industry is in the Commissioner's Power BI report and available on request.
- ND Treasurer distributions are the town-level series. A payment in month M is mostly sales from month M-2 (monthly filers), and quarterly filers land in the Sep–Nov payments, so compare year-to-date or same payment month, never a single month as a sales month. Cities and distribution types are in `nd_treasurer` in `config/sources.json`.
- MT ITRR: the workbook contains respondent-level survey rows. Only weighted aggregates (quarter × entry point, quarter × origin state) are written to the repo; respondent data is discarded after aggregation. "Wibaux/Beach" is the I-94 entry from North Dakota.
- WY: the PDF URL changes each edition; add the new one to `wy_impacts_pdfs` in `config/sources.json`. Later editions win on overlapping years.
- Not scriptable (probed 2026-09-16, re-checked with a real remote browser): South Dakota's Monthly Travel Indicators (Tourism Economics Symphony Tableau returns "Page unavailable" outside the sdvisit.com embed) and Wyoming's travelstats.com dashboard (Tableau Public with data access disabled). ND Commerce's monthly indicators are on the same Symphony platform with no public view; partner access is the path. The Tax Commissioner's Power BI report was paged through in full: it is the same tables as the Excel workbook, with no county × industry view. The ND GIS Hub domain (gishubdata.nd.gov) no longer resolves.
- Airports: TranStats is a WebForms page (viewstate POST, one zip per state-year). Only the current and prior year are re-downloaded each run. FAA files for 2021–2023 sit behind HTML landing pages; the fetcher follows them.
- NDDOT: reports are posted irregularly at `e_report_{Month}{Year}.pdf`; each carries the month for the report year and the prior year. Months that 404 are retried next run. No 2026 reports had been posted as of 2026-09-16.

## Roadmap

- NPS sub-unit detail (South Unit, Painted Canyon) if a per-location report can be exported the same way.
- ND county-by-industry (accommodation and food services): request from the Tax Commissioner's research staff.
- SD Monthly Travel Indicators, if Travel South Dakota will share an extract.
- NDDOT ATR hourly/directional data for station 279 by request to NDDOT Planning (the PDFs give daily averages only).
- Phase 2: Library admissions (Altru SKY API) and GA4, joined by date to compute capture rate (admissions ÷ TRNP South Unit visits) and new-market share.

Planning doc: *Visitor Impact Data Plan* (Claude doc) and `TRPL / Visitor Impact Data Plan — source inventory` in Outline.

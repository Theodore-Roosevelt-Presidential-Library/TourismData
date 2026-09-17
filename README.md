# TourismData

Gathers regional visitation indicators around the Theodore Roosevelt Presidential Library and publishes a dashboard on GitHub Pages.

**Dashboard:** https://theodore-roosevelt-presidential-library.github.io/TourismData/

## What it tracks

| Feed | Source | Grain | Script |
|---|---|---|---|
| Library attendance (checked-in scans) and tickets by day and event; visitor origin by buyer ZIP → state | ACME Ticketing reporting API, direct (TicketAnalytics collection + "E: Event Sales by Zip Code") | Daily, Jun 2026–present; origin monthly | `scripts/fetch_acme.py` |
| Fallback: the Marketing Dashboard repo's nightly ACME extract | `Dashboard/data/latest/acme.json` (private repo) | Daily, Sep 2024–present | `scripts/fetch_library.py` |
| Recreation visits, 8 NPS units (TRNP + regional comparison parks) | NPS IRMA STATS, "Recreation Visitors By Month" report | Monthly, 1979–present | `scripts/fetch_nps.py` |
| TRNP detail: Painted Canyon rest-area vehicle counter; public use by location (South Unit, North Unit, Painted Canyon, Medora walk-ins, campers); overnight stays by type | NPS IRMA STATS "Traffic Counts", "Monthly Public Use", "Overnight Stays" reports | Monthly 1992–present (May–Oct); latest month + YTD, accumulating; annual 1979–present | `scripts/fetch_nps_detail.py` |
| TRNP visitor spending, jobs, labor income, output in the gateway region, by sector (+ the 7 comparison parks) | NPS Visitor Spending Effects web API (`irmaservices.nps.gov/vseapi`) | Annual, 2012–present | `scripts/fetch_nps_vse.py` |
| Inbound land-border crossings, ND and MT ports | BTS Border Crossing Entry Data (Socrata `keg4-3bc2`) | Monthly by port, 2019–present | `scripts/fetch_bts_border.py` |
| Airport passengers (DIK, BIS, FAR, MOT, BIL, RAP) | BTS T-100 Domestic Market via the TranStats download form (monthly) + FAA calendar-year enplanements (annual) | Monthly 2019–present (~3-mo lag); annual 2005–present | `scripts/fetch_airports.py` |
| Airline passenger boardings, all 8 ND commercial airports (BIS, DIK, FAR, GFK, MOT, ISN, JMS, DVL) | ND Aeronautics Commission monthly boarding-report PDFs (each carries ten years of that month) | Monthly 2016–present (~3-week lag) | `scripts/fetch_ndac.py` |
| I-94 and US 85 traffic near Medora (NDDOT permanent counters 279, 221, 223) | NDDOT monthly "Automatic Traffic Data" PDF reports | Monthly average daily traffic, weekday/weekend, 2024–present | `scripts/fetch_nddot_atr.py` |
| Hourly/daily traffic at NDDOT counters 279 (I-94 at Medora) and 221 (US 85), by direction | FHWA TMAS continuous-count station files (one ~28 MB zip per month, all states; only our stations kept) | Daily with 24 hourly columns, 2019–last full year (posted each March) | `scripts/fetch_tmas.py` |
| Inbound air travelers to BIS, DIK, FAR, MOT by home airport and state | BTS DB1B Origin & Destination Survey, prezipped Coupon + Ticket files joined on itinerary (~350 MB per quarter; aggregates only stored) | Quarterly, 2023–present (~6-mo lag) | `scripts/fetch_db1b.py` |
| Taxable sales and purchases, all ND counties + statewide industry sectors | ND Office of State Tax Commissioner, statistical-report workbook | Quarterly, 2019–present | `scripts/fetch_nd_tax.py` |
| City sales tax, occupancy (lodging) tax, and city lodging-and-restaurant tax paid to Medora, Beach, Belfield, Dickinson, Watford City, Killdeer, Bowman | ND State Treasurer, Historical Distribution Search | Monthly payments, 2019–present | `scripts/fetch_nd_treasurer.py` |
| Montana nonresident visitation + survey shares (entry point, origin state) | ITRR (Univ. of Montana) Tableau Public workbook, embedded Hyper extracts | Monthly 1991–present; survey quarterly 2021–present | `scripts/fetch_mt_itrr.py` |
| Wyoming county travel impacts (spend, earnings, jobs, tax) | Dean Runyan Associates PDF for the Wyoming Office of Tourism | Annual, 2015–present | `scripts/fetch_wy_impacts.py` |
| County employment in leisure & hospitality and accommodation & food (Billings, Stark, Golden Valley, McKenzie, Dunn, Slope, Bowman) | BLS QCEW open-data CSV slices | Quarterly, 2015–present (~5-mo lag) | `scripts/fetch_qcew.py` |
| Employed residents, labor force, unemployment rate — same seven counties | BLS LAUS North Dakota time-series file | Monthly, 2015–present (~1-mo lag; latest month preliminary) | `scripts/fetch_laus.py` |
| Visitor spending by county (5-yr timeline) and tourism jobs/income, all 53 ND counties | Tourism Economics "Economic Impact of Tourism in North Dakota" PDFs for ND Commerce | Annual, 2020–present | `scripts/fetch_nd_impact.py` |
| Campground reservations and origin state — Cottonwood (TRNP), Buffalo Gap, CCC (USFS) | Recreation.gov RIDB historical reservation files (~500 MB per fiscal year; aggregates only are stored) | Monthly arrivals + annual origin, FY2020–present | `scripts/fetch_recgov.py` |
| ND and Bismarck MSA leisure & hospitality payroll jobs (and splits), NSA | BLS CES North Dakota time-series file | Monthly, 2015–present (~1-mo lag) | `scripts/fetch_ces.py` |
| Retail sales year-over-year by sector, ND / neighbours / U.S. | Census Monthly State Retail Sales (experimental; growth rates only) | Monthly, 2019–present (~2-mo lag) | `scripts/fetch_census_msrs.py` |
| Daily AQI and PM2.5 at TRNP's Painted Canyon monitor — summer smoke days | EPA AQS daily-AQI-by-county files (validated) + AirNow daily files (preliminary, to yesterday) | Daily, 2015–present | `scripts/fetch_airquality.py` |
| Wikipedia pageviews (Library, Medora, TRNP, TR articles) and Google Trends | Wikimedia REST API; pytrends (unofficial) | Monthly from 2015; weekly from 2019 | `scripts/fetch_interest.py` |
| Controls: Dickinson weather (rain days, highs), Midwest gas price, CAD/USD, ND oil production and rig count | NOAA NCEI, EIA, FRED, ND Industrial Commission PDFs | Monthly, 2015–present | `scripts/fetch_controls.py` |

Parks and ports are configured in `config/sources.json`. The Library's opening date (2026-07-04) drives the "since opening" comparisons.

## How it runs

`.github/workflows/update-data.yml` runs on the 16th of each month (NPS posts the prior month around the 15th), on manual dispatch, and on pushes that touch the scripts or page. It fetches each feed, rebuilds `docs/data/dashboard.json`, commits any changed data, and deploys `docs/` to GitHub Pages.

Each fetcher is independent: if one source is down the others still refresh, and `data/manifest.json` records what was fetched when.

## Run locally

```bash
pip install -r requirements.txt
python scripts/fetch_nps.py
python scripts/fetch_bts_border.py
python scripts/fetch_airports.py
python scripts/fetch_ndac.py
python scripts/build.py
python -m http.server -d docs 8000   # open http://localhost:8000
```

## Data notes

- **Attendance vs tickets.** ACME has two collections that disagree. `TicketAnalytics` (`CheckedInCount`, `TicketQuantity`) reconciles with the "PE: Tickets Checked In" report and is what this repo publishes as attendance. `Transactions` rows sum to roughly 1.7× the TicketAnalytics ticket count for the same events (combos and multi-line orders) and must not be used for counts. The Dashboard's `data/latest/acme.json` snapshot from 2026-09-04 carried Transactions-based "visitors"; the direct pull replaces it. Requires `ACME_API_KEY` (and `ACME_API_BASE` if not the default) in Actions secrets; the report-definition IDs are not secrets. The check-in query is sent as our own `queryExpression` grouped `DayMonthYear` so a Backoffice edit can't change it.
- Attendance counts admission events only — General Admission, Flex Tickets, Walk-Up (`acme.admission_events` in config) — the same definition as the TicketingWidgets Sell-Out Monitor, so the two sites reconcile. Tour and program scans (Highlights, Deep-Dive, Architecture, Badlands, Member tours, public programs) are reported in a separate table because most of those visitors also hold an admission ticket. June preview days are before the opening date and excluded from "since opening".
- Origin: ZIP counts are aggregated to state (`zipcodes`), with Canadian postal codes as "Canada". Only ticket counts per ZIP are stored — no customer records. "New-market share" = tickets from outside ND, MN, SD, MT.
- Origin geography (`origin_geo` in `build.py`): each ZIP's centroid from `zipcodes` gives straight-line (haversine) miles from Medora, bucketed 0–50 / 50–150 / 150–300 / 300–600 / 600+; straight-line runs ~15–20% under road miles. Feeder metros come from a hand-kept (state, county) → metro map in `build.py` (`METROS`); counties not in the map roll up to the state table only. The US map plots the top 2,500 ZIPs by tickets; Canadian buyers are excluded from the map and bands.
- Library fallback: the private `Dashboard` repo, which runs ACME's Reporting API nightly. Locally, set `DASHBOARD_LOCAL` to a clone; in Actions, the `DASHBOARD_TOKEN` secret must be a GitHub token with read access to that repo's contents. `visitors` is checked-in scans and `tickets` is tickets sold — they are different quantities; the Dashboard records which one produced `visitors` in `visitors_source`, and the page shows it when it is anything but `checked_in`. Capture rate = Library monthly attendance ÷ TRNP monthly recreation visits.

- NPS monthly figures are preliminary until the annual close in Q1. A current-year month posted as `0` is treated as not yet reported.
- Little Bighorn Battlefield's 2025 counts look like a counter outage (July 2025 = 7,631 vs 25,896 in 2024). The dashboard flags parks whose year-over-year change exceeds 100% and excludes them from the control-park median.
- BTS border data is reported at the port level; Pembina and Portal carry most ND traffic.
- ND taxable sales: Billings County total is the county-level Medora proxy. Medora is suppressed from the Commissioner's city tables (towns far smaller than Medora appear, so this is confidentiality, not size). Industry sectors are statewide only; county × industry is in the Commissioner's Power BI report and available on request.
- ND Treasurer distributions are the town-level series. A payment in month M is mostly sales from month M-2 (monthly filers), and quarterly filers land in the Sep–Nov payments, so compare year-to-date or same payment month, never a single month as a sales month. Cities and distribution types are in `nd_treasurer` in `config/sources.json`.
- MT ITRR: the workbook contains respondent-level survey rows. Only weighted aggregates (quarter × entry point, quarter × origin state) are written to the repo; respondent data is discarded after aggregation. "Wibaux/Beach" is the I-94 entry from North Dakota.
- WY: the PDF URL changes each edition; add the new one to `wy_impacts_pdfs` in `config/sources.json`. Later editions win on overlapping years.
- Not scriptable (probed 2026-09-16, re-checked with a real remote browser): South Dakota's Monthly Travel Indicators (Tourism Economics Symphony Tableau returns "Page unavailable" outside the sdvisit.com embed) and Wyoming's travelstats.com dashboard (Tableau Public with data access disabled). ND Commerce's monthly indicators are on the same Symphony platform with no public view; partner access is the path. The Tax Commissioner's Power BI report was paged through in full: it is the same tables as the Excel workbook, with no county × industry view. The ND GIS Hub domain (gishubdata.nd.gov) no longer resolves.
- NPS detail: IRMA's "Monthly Public Use" report has Year/Month parameters only as SSRS form fields (URL parameters are ignored), so it returns the latest posted month; the fetcher keeps every month it sees, and the by-location monthly history builds from the first run. The "Summary of Visitor Use by Month and Year" report has the same limitation (current year only). The Query Builder reports are ASP.NET multi-select forms and were not automated.
- FHWA TMAS comes in three layouts: fixed-width TMG records through 2020 (2019 has no restrictions column at position 20, 2020 does; both are 141 wide, so the parser picks the alignment whose hourly values are not all multiples of ten), headerless pipe-delimited 2021–2024, and a headed pipe file from 2025. Two-digit years appear in some files. Station 279 is missing one direction for Jul–Sep 2019 and Aug–Sep 2024 and most of June 2023; daily totals use only days with both directions.
- DB1B: the TranStats custom-download form returns 404 for this table, so the prezipped archives are used. Inbound = itineraries with a coupon landing at one of our airports whose ticket origin is not one of them; the market-level file cannot separate a Denver resident flying to Bismarck from a Bismarck resident flying home. Sample counts ×10; small origins are noisy. First run downloads ~4 GB; later runs only new quarters.
- VSE: the API returns HTTP 500 for a year not yet published; the report for year N lands around May of N+1. "Jobs" and "spending" here are for the gateway region (~60 miles), so TRNP's figures overlap heavily with Billings County's in the ND Commerce study, which uses a different model.
- Air quality: AirNow's daily files are preliminary and occasionally revised; AQS validated values replace them as each quarter is processed. AQI ≥ 101 is the smoke-day threshold on the dashboard.
- NDAC boardings: aero.nd.gov serves the wrong intermediate certificate, so the fetcher downloads the leaf's issuer certificate from Sectigo (AIA) and verifies against certifi plus that issuer — verification is never disabled. December's table lives in the "Calendar Year" report. The January–March 2026 PDF links on NDAC's site were 404 when this was built; the fetcher retries them each run and falls back to the prior year's report for that month (which still carries ten years of history), so those months show only through 2025 until NDAC fixes the links. Boardings are enplanements (departing passengers), all carriers, so they run slightly above BTS T-100's U.S.-carrier figure.
- LAUS: `download.bls.gov` refuses requests whose user agent lacks a contact e-mail; set the `BLS_CONTACT` repository variable to a monitored address (the default is a placeholder on the Library's domain). County employment is a household-survey model estimate — people, all industries — not establishment jobs; QCEW remains the tourism-sector series. October 2025 is missing at the source (federal shutdown).
- ND Commerce impact: the county tables are on pages 20 and 23 of the annual PDF; new editions are discovered from the Commerce research page (links titled "<year> Economic Impact"), and `nd_impact_pdfs` in config pins known ones. Later editions revise earlier years and win on overlap.
- Lodging & restaurant tax: only Dickinson, Watford City and Bowman levy it among the corridor towns (Medora does not); it is in the same Treasurer search as the other distribution types (`REST/LODG`).
- Motor-fuel gallons were looked for and are not available monthly: the Tax Commissioner publishes no fuel statistics, FHWA's monthly motor-fuel reports stop at December 2023 on its site, and EIA's prime-supplier state volumes ended in 2022. The NDDOT counter plus the EIA gas-price control stand in.
- Airports: TranStats is a WebForms page (viewstate POST, one zip per state-year). Only the current and prior year are re-downloaded each run. FAA files for 2021–2023 sit behind HTML landing pages; the fetcher follows them.
- NDDOT: reports are posted irregularly at `e_report_{Month}{Year}.pdf`; each carries the month for the report year and the prior year. Months that 404 are retried next run. No 2026 reports had been posted as of 2026-09-16.

- QCEW suppresses Billings County's accommodation & food line (NAICS 72) for confidentiality; the leisure & hospitality supersector (1026) is disclosed and is what the dashboard charts.
- Recreation.gov: campgrounds sell out in July–August, so reservation counts are a floor on demand; the origin-state mix is the useful part. FY2019's file has a different schema and is skipped.
- Google Trends is an unofficial endpoint; a failed run keeps the prior CSV.

## Roadmap

- NPS sub-unit detail (South Unit, Painted Canyon) if a per-location report can be exported the same way.
- ND county-by-industry (accommodation and food services): request from the Tax Commissioner's research staff.
- SD Monthly Travel Indicators, if Travel South Dakota will share an extract.
- NDDOT ATR hourly/directional data for station 279 by request to NDDOT Planning (the PDFs give daily averages only).
- GA4 web demand by DMA (the Dashboard already pulls it) as a leading indicator next to Wikipedia and Trends; new-market share from ticketing ZIPs once the Dashboard exposes ZIP-level origin.

Planning doc: *Visitor Impact Data Plan* (Claude doc) and `TRPL / Visitor Impact Data Plan — source inventory` in Outline.

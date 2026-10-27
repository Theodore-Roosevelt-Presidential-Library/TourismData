# TourismData

Gathers regional visitation indicators around the Theodore Roosevelt Presidential Library and publishes a dashboard on GitHub Pages.

**Dashboard:** https://theodore-roosevelt-presidential-library.github.io/TourismData/

## How the page is organized

The dashboard is one page in seven sections, with a sticky section menu and a "What moved" strip under the headline tiles (the newest reading of each headline series against a year earlier, newest first):

1. **The Library** — attendance, origin by state and month, drive distance, ZIP map, feeder metros, tickets per 100,000 residents by state and metro, Canadian buyers by province.
2. **The park and Medora** — TRNP visits, Painted Canyon, public use by location, overnight stays, park visitor spending, campgrounds.
3. **Getting here** — I-94 and US 85 near Medora, summer traffic at counters across the Montana, South Dakota and Wyoming lines, airports (ND plus Billings, Rapid City, Gillette, Sheridan), air-traveler origins, the Canadian border.
4. **The local economy** — Medora and corridor-town taxes, county taxable sales, the ND Commerce visitor-spending study, tourism jobs.
5. **The region** — a state-by-state summary table (park visits, a visitor-spending signal, traffic entering, overseas visitors, outdoor-recreation share of the economy for ND, MT, SD, WY and Canada), the comparison parks, then one group per state: Montana (ITRR), South Dakota (tourism tax), Wyoming (Dean Runyan, lodging tax), Canada (Statistics Canada), overseas visitors (NTTO I-94), BEA outdoor recreation, and gateway-county jobs across the state lines.
6. **Demand and context** — Wikipedia, Google Trends, smoke days, retail sales, weather, gas, exchange rate, oil.
7. **Sources** — every feed, its cadence, lag, latest period and script, generated from `config/catalog.json`.

Code layout: `docs/index.html` is the shell (styles, header, menu). `docs/js/core.js` holds the shared helpers (card placement, freshness badges, the seasonal and ranked-change charts); each section is its own file (`docs/js/sec-*.js`) that registers a render function; `docs/js/main.js` loads `dashboard.json` and runs them in order. To add a card: compute its block in `scripts/build.py`, draw it in the right `sec-*.js`, and list its id under the feed in `config/catalog.json` (that is what gives it its freshness line).

## What it tracks

Generated from `config/catalog.json` by `scripts/build.py` — edit the catalog, not this table.

<!-- catalog:start -->
| Section | Feed | Source | Grain | Lag | Script |
|---|---|---|---|---|---|
| The Library | Library attendance and visitor origin | ACME Ticketing reporting API (TicketAnalytics + Event Sales by Zip Code) | Daily | Same day | `scripts/fetch_acme.py` |
| The Library | Population by state and county (per-capita denominators) | [Census Bureau Population Estimates, county totals](https://www.census.gov/programs-surveys/popest.html) | Annual | ~3 months | `scripts/fetch_population.py` |
| The Library | Library attendance fallback (Marketing Dashboard extract) | Dashboard repo nightly ACME extract | Daily | 1 day | `scripts/fetch_library.py` |
| The park and Medora | Recreation visits, 12 NPS units | [NPS IRMA STATS, Recreation Visitors By Month](https://irma.nps.gov/Stats/) | Monthly | ~6 weeks | `scripts/fetch_nps.py` |
| The park and Medora | TRNP detail: Painted Canyon counter, public use by location, overnight stays | [NPS IRMA STATS park reports](https://irma.nps.gov/Stats/) | Monthly / annual | ~6 weeks | `scripts/fetch_nps_detail.py` |
| The park and Medora | Park visitor spending, jobs and output | [NPS Visitor Spending Effects API](https://www.nps.gov/subjects/socialscience/vse.htm) | Annual | ~5 months | `scripts/fetch_nps_vse.py` |
| The park and Medora | Campground reservations and camper origin | [Recreation.gov RIDB historical reservations](https://ridb.recreation.gov/download) | Monthly / annual | ~3 months after fiscal year | `scripts/fetch_recgov.py` |
| Getting here | I-94 and US 85 near Medora, monthly averages | [NDDOT Automatic Traffic Data reports](https://www.dot.nd.gov/) | Monthly | Irregular | `scripts/fetch_nddot_atr.py` |
| Getting here | Hourly counters: I-94 at Medora and Wibaux, US 85 at Buffalo and Belle Fourche, I-90 at the WY–SD line | [FHWA TMAS continuous-count station files](https://www.fhwa.dot.gov/policyinformation/tables/tmasdata/) | Daily / hourly | Posted each March for the prior year | `scripts/fetch_tmas.py` |
| Getting here | Airport passengers (DIK, BIS, FAR, MOT, XWA, BIL, RAP, GCC, SHR) | [BTS T-100 Domestic Market; FAA calendar-year enplanements](https://www.transtats.bts.gov/) | Monthly / annual | ~3 months | `scripts/fetch_airports.py` |
| Getting here | Boardings at all eight ND commercial airports | [ND Aeronautics Commission monthly boarding reports](https://aero.nd.gov/) | Monthly | ~3 weeks | `scripts/fetch_ndac.py` |
| Getting here | Where inbound air travelers start their trips | [BTS DB1B Origin & Destination Survey (10% ticket sample)](https://www.transtats.bts.gov/) | Quarterly | ~6 months | `scripts/fetch_db1b.py` |
| Getting here | Land-border crossings into ND and MT | [BTS Border Crossing Entry Data](https://data.bts.gov/Research-and-Statistics/Border-Crossing-Entry-Data/keg4-3bc2) | Monthly | ~1 month | `scripts/fetch_bts_border.py` |
| The local economy | City sales, occupancy and lodging & restaurant tax paid to Medora and corridor towns | [ND State Treasurer distribution search](https://www.treasurer.nd.gov/) | Monthly | ~2 months | `scripts/fetch_nd_treasurer.py` |
| The local economy | Taxable sales by ND county and statewide industry | [ND Office of State Tax Commissioner](https://www.tax.nd.gov/) | Quarterly | ~5 months | `scripts/fetch_nd_tax.py` |
| The local economy | Visitor spending and tourism jobs, all ND counties | [Tourism Economics for ND Commerce](https://www.commerce.nd.gov/) | Annual | ~9 months | `scripts/fetch_nd_impact.py` |
| The local economy | Leisure & hospitality jobs: ND corridor counties plus Montana and South Dakota gateway counties | [BLS QCEW](https://www.bls.gov/cew/) | Quarterly | ~5 months | `scripts/fetch_qcew.py` |
| The local economy | Employed residents and unemployment, same counties | [BLS LAUS](https://www.bls.gov/lau/) | Monthly | ~1 month | `scripts/fetch_laus.py` |
| The local economy | ND and Bismarck leisure & hospitality payroll jobs | [BLS CES](https://www.bls.gov/sae/) | Monthly | ~1 month | `scripts/fetch_ces.py` |
| The region | Montana nonresident visitation and survey shares | [ITRR, University of Montana](https://itrr.umt.edu/) | Monthly / quarterly | Annual update | `scripts/fetch_mt_itrr.py` |
| The region | South Dakota tourism tax by county and business type | [SD Department of Revenue, Tourism Tax by County](https://dor.sd.gov/businesses/taxes/sales-use-tax/historical-tax-statistical-reports/) | Monthly (filing month) | ~6 weeks | `scripts/fetch_sd_tourism.py` |
| The region | Wyoming county travel impacts | [Dean Runyan Associates for the Wyoming Office of Tourism](https://travelwyoming.com/industry/research) | Annual | ~6 months | `scripts/fetch_wy_impacts.py` |
| The region | Wyoming lodging tax by county | [Wyoming Economic Analysis Division](https://ai.wyo.gov/divisions/economic-analysis/revenue/sales-and-use) | Annual (fiscal year) | ~5 months | `scripts/fetch_wy_lodging.py` |
| The region | Overseas visitor arrivals by first intended state | [National Travel and Tourism Office (Commerce), I-94 Summary & Analysis, Table G](https://www.trade.gov/i-94-arrivals-program) | Monthly | ~1 month (preliminary), ~2 months (final) | `scripts/fetch_ntto.py` |
| The region | Canadians returning by car through Saskatchewan, Manitoba and Alberta ports | [Statistics Canada table 24-10-0053-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2410005301) | Monthly | ~2 months | `scripts/fetch_statcan.py` |
| The region | Outdoor recreation share of each state's economy | [BEA Outdoor Recreation Satellite Account](https://www.bea.gov/data/special-topics/outdoor-recreation) | Annual | ~12–15 months | `scripts/fetch_orsa.py` |
| Demand and context | Wikipedia pageviews and Google Trends | Wikimedia REST API; Google Trends (unofficial) | Monthly / weekly | Days | `scripts/fetch_interest.py` |
| Demand and context | Smoke days at Painted Canyon | [EPA AQS + AirNow](https://www.epa.gov/aqs) | Daily | 1 day (preliminary) | `scripts/fetch_airquality.py` |
| Demand and context | Retail sales year-over-year, ND and neighbors | [Census Monthly State Retail Sales (experimental)](https://www.census.gov/retail/state_retail_sales.html) | Monthly | ~2 months | `scripts/fetch_census_msrs.py` |
| Demand and context | Weather, gas price, exchange rate, ND oil | NOAA NCEI, EIA, FRED, ND Industrial Commission | Monthly | ~1 month | `scripts/fetch_controls.py` |
<!-- catalog:end -->

Parks and ports are configured in `config/sources.json`. The Library's opening date (2026-07-04) drives the "since opening" comparisons.

## How it runs

`.github/workflows/update-data.yml` runs daily at 11:00 UTC and again on the 1st of each month (NPS posts the prior month around the 15th, which the daily run picks up), on manual dispatch, and on pushes that touch the scripts or page. It fetches each feed, rebuilds `docs/data/dashboard.json`, commits any changed data, and deploys `docs/` to GitHub Pages.

Each fetcher is independent: if one source is down the others still refresh, and `data/manifest.json` records what was fetched when.

## Run locally

```bash
pip install -r requirements.txt
python scripts/fetch_nps.py
python scripts/fetch_bts_border.py
python scripts/fetch_airports.py
python scripts/fetch_ndac.py
python scripts/fetch_sd_tourism.py   # needs poppler (pdftotext)
python scripts/build.py
python -m http.server -d docs 8000   # open http://localhost:8000
```

## Data notes

- **Attendance vs tickets.** ACME has two collections that disagree. `TicketAnalytics` (`CheckedInCount`, `TicketQuantity`) reconciles with the "PE: Tickets Checked In" report and is what this repo publishes as attendance. `Transactions` rows sum to roughly 1.7× the TicketAnalytics ticket count for the same events (combos and multi-line orders) and must not be used for counts. The Dashboard's `data/latest/acme.json` snapshot from 2026-09-04 carried Transactions-based "visitors"; the direct pull replaces it. Requires `ACME_API_KEY` (and `ACME_API_BASE` if not the default) in Actions secrets; the report-definition IDs are not secrets. The check-in query is sent as our own `queryExpression` grouped `DayMonthYear` so a Backoffice edit can't change it.
- Attendance counts admission events only — General Admission, Flex Tickets, Walk-Up (`acme.admission_events` in config) — the same definition as the TicketingWidgets Sell-Out Monitor, so the two sites reconcile. Tour and program scans (Highlights, Deep-Dive, Architecture, Badlands, Member tours, public programs) are reported in a separate table because most of those visitors also hold an admission ticket. June preview days are before the opening date and excluded from "since opening".
- Origin: ZIP counts are aggregated to state (`zipcodes`), with Canadian postal codes as "Canada". Only ticket counts per ZIP are stored — no customer records. "New-market share" = tickets from outside North Dakota and the region (`origin_region_states` in config: MN, SD, MT, WI, IA — the Sell-Out Monitor's grouping). `origin_geo.monthly_tiers` and `monthly_points` give the ND / region / rest-of-U.S. / international split and the map frames month by month since opening; the page shows them as a stacked bar and a slider on the map. Every card carries a "Data pulled … · latest …" line from `data/manifest.json`.
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
- ND Commerce impact: the county timeline and jobs tables are on pages 20 and 23 of the annual PDF; the county × sector tables (lodging, F&B, retail, recreation, transport, state & local tax) are printed rotated and are read with poppler's `pdftotext -layout` (installed in the workflow; skipped locally if absent). The standalone "County Tables" PDF for the 2023 study (`141070.pdf`) supplies 2022–2023 sectors; new editions are discovered from the Commerce research page (links titled "<year> Economic Impact"), and `nd_impact_pdfs` in config pins known ones. Later editions revise earlier years and win on overlap.
- Lodging & restaurant tax: only Dickinson, Watford City and Bowman levy it among the corridor towns (Medora does not); it is in the same Treasurer search as the other distribution types (`REST/LODG`).
- Motor-fuel gallons were looked for and are not available monthly: the Tax Commissioner publishes no fuel statistics, FHWA's monthly motor-fuel reports stop at December 2023 on its site, and EIA's prime-supplier state volumes ended in 2022. The NDDOT counter plus the EIA gas-price control stand in.
- Airports: TranStats is a WebForms page (viewstate POST, one zip per state-year). Only the current and prior year are re-downloaded each run. FAA files for 2021–2023 sit behind HTML landing pages; the fetcher follows them.
- NDDOT: reports are posted irregularly at `e_report_{Month}{Year}.pdf`; each carries the month for the report year and the prior year. Months that 404 are retried next run. No 2026 reports had been posted as of 2026-09-16.

- QCEW suppresses Billings County's accommodation & food line (NAICS 72) for confidentiality; the leisure & hospitality supersector (1026) is disclosed and is what the dashboard charts.
- Recreation.gov: campgrounds sell out in July–August, so reservation counts are a floor on demand; the origin-state mix is the useful part. FY2019's file has a different schema and is skipped.
- Google Trends is an unofficial endpoint; a failed run keeps the prior CSV.

- **Regional traffic counters (TMAS).** `tmas.stations` is keyed by state. ND stations keep their bare id ("279"); others are written "MT-131", "SD-110", "WY-047". `data/tmas_scanned.json` records which stations each month's zip has been searched for, so adding a station downloads only the months it hasn't been looked for in (~2.5 GB for a full 2019+ backfill; `TMAS_MAX_MONTHS` caps one run). Montana reports I-94 at Wibaux (131) and Bad Route (103) in alternating years; South Dakota 110 (US 85 at Buffalo) reports zeros in 2019–20, which the build drops.
- **Park flags.** A park is flagged, and left out of the control median and the state summary, if last summer fell below half the summer before (a counter outage, e.g. Little Bighorn 2025) or if this year to date is more than 40% off last year (a new counter or count method, e.g. Bighorn Canyon's 2026 winter months at four times their usual level).
- **South Dakota tourism tax.** Monthly "Tourism Tax by County" PDFs, discovered on DOR's historical statistical-reports page (hashed `/media/<id>/MMYYcounty-tourism.pdf` paths). The month is the FILING month (July filings are mostly June business). Classifications with fewer than three licensees are folded into an undisclosed "Other", and there is no county total, so county sums are a floor; Hotels & Motels (SIC 7011) is the like-for-like lodging line. The state total is complete. Series starts 2020.
- **Wyoming lodging tax.** Annual by state fiscal year (July–June), three years per edition, editions accumulate. The 3% column is the statewide portion and comparable across counties; receipts ≈ 3% taxes ÷ 0.03. The "WYOMING" row is the state total.
- **Statistics Canada** table 24-10-0053-01 through the Web Data Service (no key): Saskatchewan, Manitoba and Alberta; Canadians returning from the U.S. by automobile and U.S. residents entering by automobile; all travellers and overnight.
- **NTTO I-94 (overseas arrivals by first intended state).** Table G of the monthly Summary & Analysis workbook. Only the last few months are linked from the program page; older workbooks are found by trying `/sites/default/files/<upload YYYY-MM>/<FINAL|Final|Preliminary>_SummaryAnalysis_COR_<Month>_<YYYY>.xlsx`. Preliminary months are replaced when the final file appears. Months not found are cached in `data/ntto_missing.json` and re-probed only on the 1st. Workbooks before 2022 use other names, so the series starts January 2022. First intended address understates states visited later in a trip.
- **BEA outdoor recreation (ORSA).** Table 1 of the state workbook, one year per edition; editions accumulate (`orsa.extra_urls` pins the 2023 edition).
- **Population.** Census Population Estimates county file (the ACS API now needs a key). Bump `population.url` when the next vintage posts each March.
- **Not automated.** Montana's lodging facility use tax by region/CVB (the Office of Tourism's report PDFs were taken down; ask Montana Commerce), and TSA checkpoint throughput by airport (the FOIA reading room returns 403 to scripts). The South Dakota and Wyoming travel dashboards remain unscriptable as noted above.

## Roadmap

- ND county-by-industry (accommodation and food services): request from the Tax Commissioner's research staff.
- SD Monthly Travel Indicators, if Travel South Dakota will share an extract.
- Montana lodging tax by tourism region: request from Montana Department of Commerce, Office of Tourism.
- NDDOT ATR hourly/directional data for station 279 by request to NDDOT Planning (the PDFs give daily averages only).
- GA4 web demand by DMA (the Dashboard already pulls it) as a leading indicator next to Wikipedia and Trends.
- DB1B for Billings and Rapid City (changes the "inbound" definition, so as a separate table).

Planning doc: *Visitor Impact Data Plan* (Claude doc) and `TRPL / Visitor Impact Data Plan — source inventory` in Outline.

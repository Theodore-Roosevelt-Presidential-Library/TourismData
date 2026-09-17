"""Turn data/*.csv into docs/data/dashboard.json for the static site.

Everything the page draws is precomputed here so index.html stays simple and
the numbers on the page are reproducible from the CSVs in data/.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

from common import CONFIG, DATA, ROOT, now_iso

DOCS_DATA = ROOT / "docs" / "data"
BAND_YEARS = [2019, 2022, 2023, 2024, 2025]  # pre-opening band; 2020-21 excluded (pandemic)
OPENING = pd.Timestamp(CONFIG["opening_date"])
MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_nps() -> pd.DataFrame:
    df = pd.read_csv(DATA / "nps_monthly.csv")
    # Drop trailing zero months in the current year (NPS posts 0 as a placeholder)
    cur = df["year"].max()
    keep = []
    for park, g in df.groupby("park"):
        g = g.sort_values(["year", "month"])
        gy = g[g["year"] == cur]
        while len(gy) and gy.iloc[-1]["visits"] == 0:
            gy = gy.iloc[:-1]
        keep.append(pd.concat([g[g["year"] < cur], gy]))
    return pd.concat(keep).reset_index(drop=True)


def pct(a: float, b: float) -> float | None:
    return None if not b else round((a - b) / b * 100, 1)


def park_block(df: pd.DataFrame, park: dict, latest_month: int, cur: int) -> dict:
    g = df[df["park"] == park["code"]]
    by = {y: g[g["year"] == y].set_index("month")["visits"].to_dict() for y in g["year"].unique()}
    prev = cur - 1
    open_m = OPENING.month  # July
    # Compare only months this park has posted in the current year
    park_latest = int(g[g["year"] == cur]["month"].max()) if cur in by else 0
    latest_month = min(latest_month, park_latest)
    post_months = list(range(open_m, latest_month + 1)) if latest_month >= open_m else []
    ytd_months = list(range(1, latest_month + 1))

    def s(y, months):
        return sum(by.get(y, {}).get(m, 0) for m in months)

    band = []
    for m in range(1, 13):
        vals = [by[y][m] for y in BAND_YEARS if y in by and m in by[y]]
        band.append({"month": m, "min": min(vals), "max": max(vals), "mean": round(sum(vals) / len(vals))} if vals else None)

    # Counter-outage flag: prior-year peak season (Jun-Sep) under half of the year before
    peak = range(6, 10)
    flag = bool(s(prev, peak) and s(prev - 1, peak) and s(prev, peak) < 0.5 * s(prev - 1, peak))

    return {
        "code": park["code"],
        "name": park["name"],
        "role": park["role"],
        "state": park["state"],
        "flag": flag,
        "latest_month": int(g[g["year"] == cur]["month"].max()) if cur in by else None,
        "years": {str(y): [by[y].get(m) for m in range(1, 13)] for y in sorted(by) if y >= 2015},
        "band": band,
        "kpi": {
            "latest": {"month": latest_month, "cur": by.get(cur, {}).get(latest_month), "prev": by.get(prev, {}).get(latest_month)},
            "post_opening": {"months": post_months, "cur": s(cur, post_months), "prev": s(prev, post_months), "pct": pct(s(cur, post_months), s(prev, post_months))},
            "ytd": {"months": ytd_months, "cur": s(cur, ytd_months), "prev": s(prev, ytd_months), "pct": pct(s(cur, ytd_months), s(prev, ytd_months))},
            "annual": {str(y): s(y, range(1, 13)) for y in range(2019, cur)},
        },
        "yoy_pct": [pct(by.get(cur, {}).get(m, 0), by.get(prev, {}).get(m, 0)) if m <= latest_month else None for m in range(1, 13)],
    }


def border_block() -> dict:
    df = pd.read_csv(DATA / "bts_border_monthly.csv")
    pv = df[df["measure"] == "Personal Vehicles"].copy()
    pv["year"] = pv["date"].str[:4].astype(int)
    pv["month"] = pv["date"].str[5:7].astype(int)
    out = {"latest_month": df["date"].max()[:7], "states": {}}
    for state, g in pv.groupby("state"):
        tot = g.groupby(["year", "month"])["value"].sum().reset_index()
        shaped = seasonal(tot, "month", "value", 12, BAND_YEARS)
        years = shaped["years"]
        top = g.groupby("port")["value"].sum().sort_values(ascending=False).head(4).index.tolist()
        ports = {}
        for p in top:
            gp = g[g["port"] == p].groupby(["year", "month"])["value"].sum()
            ports[p] = {str(y): [int(gp.get((y, m), 0)) or None for m in range(1, 13)] for y in sorted(g["year"].unique()) if y >= 2024}
        out["states"][state] = {"years": years, "band": shaped["band"], "band_years": shaped["band_years"], "top_ports": ports}
    return out


def seasonal(df: pd.DataFrame, period_col: str, value_col: str, nper: int, band_years: list[int], min_year: int = 2015) -> dict:
    """Shape a (year, period, value) frame into {years: {y: [..]}, band: [{min,max}...]}."""
    years = {}
    for y, g in df.groupby("year"):
        if y < min_year:
            continue
        m = g.set_index(period_col)[value_col].to_dict()
        years[str(int(y))] = [(None if m.get(i) is None else float(m[i])) for i in range(1, nper + 1)]
    band = []
    for i in range(nper):
        vals = [years[str(y)][i] for y in band_years if str(y) in years and years[str(y)][i] is not None]
        band.append({"min": min(vals), "max": max(vals)} if vals else None)
    return {"years": years, "band": band, "band_years": [y for y in band_years if str(y) in years]}


def nd_tax_block() -> dict:
    p = DATA / "nd_taxable_sales_quarterly.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {"latest_quarter": None, "counties": {}}
    last = df.sort_values(["year", "quarter"]).iloc[-1]
    out["latest_quarter"] = f"{int(last.year)} Q{int(last.quarter)}"
    for c in CONFIG.get("nd_focus_counties", []):
        g = df[df["county"] == c].sort_values(["year", "quarter"])
        if g.empty:
            continue
        out["counties"][c] = seasonal(g, "quarter", "total", 4, BAND_YEARS)
    ip = DATA / "nd_taxable_sales_industry_quarterly.csv"
    if ip.exists():
        ind = pd.read_csv(ip)
        out["industries"] = {}
        for name in ("Accommodation & Food Services", "Arts, Entertainment & Recreation", "Retail Trade"):
            g = ind[ind["industry"] == name].sort_values(["year", "quarter"])
            if not g.empty:
                out["industries"][name] = seasonal(g, "quarter", "total", 4, BAND_YEARS)
    return out


def nd_city_block() -> dict:
    p = DATA / "nd_city_tax_distributions_monthly.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    cur = int(df["year"].max())
    latest_m = int(df[df["year"] == cur]["month"].max())
    out = {"current_year": cur, "latest_month": latest_m, "latest_payment": df["payment_date"].max(), "cities": {}, "ytd": []}
    for city, g in df.groupby("city"):
        block = {"county": g["county"].iloc[0]}
        for dist, gd in g.groupby("dist_type"):
            key = "sales" if "Sales" in dist else "occupancy"
            m = gd.groupby(["year", "month"])["amount"].sum().reset_index()
            block[key] = seasonal(m, "month", "amount", 12, BAND_YEARS)
        out["cities"][city] = block
        row = {"city": city, "county": block["county"]}
        for key in ("sales", "occupancy"):
            if key in block:
                yc = block[key]["years"].get(str(cur), [])
                yp = block[key]["years"].get(str(cur - 1), [])
                c = sum(v for v in yc[:latest_m] if v)
                pv = sum(v for v in yp[:latest_m] if v)
                row[key + "_ytd_cur"] = round(c)
                row[key + "_ytd_prev"] = round(pv)
                row[key + "_ytd_pct"] = pct(c, pv)
        out["ytd"].append(row)
    return out


def mt_block() -> dict:
    p = DATA / "mt_nonresident_visitation_monthly.csv"
    if not p.exists():
        return {}
    v = pd.read_csv(p)
    v = v[v["year"] >= 2015].sort_values(["year", "month"])
    mt_cur = int(v["year"].max())
    mt_band = [y for y in range(mt_cur - 6, mt_cur) if y not in (2020, 2021)]
    out = {
        "visitation": seasonal(v, "month", "visits", 12, mt_band),
        "current_year": mt_cur,
        "latest_month": f"{int(v.iloc[-1].year)}-{int(v.iloc[-1].month):02d}",
    }
    sp = DATA / "mt_nonresident_survey_shares.csv"
    if sp.exists():
        s = pd.read_csv(sp)
        def series(dim, value):
            g = s[(s["dimension"] == dim) & (s["value"] == value)].sort_values(["year", "quarter"]).copy()
            g["pct"] = g["share"] * 100
            sy = int(g["year"].max())
            return seasonal(g, "quarter", "pct", 4, [y for y in range(sy - 4, sy)], min_year=2015) | {"current_year": sy}
        out["i94_from_nd"] = series("entry_point", "Wibaux/Beach")
        out["origin_nd"] = series("origin", "North Dakota")
        top = s[(s["dimension"] == "origin") & (s["year"] == s["year"].max())].groupby("value")["weighted_visitors"].sum().sort_values(ascending=False).head(10)
        tot = s[(s["dimension"] == "origin") & (s["year"] == s["year"].max())]["weighted_visitors"].sum()
        out["top_origins_latest_year"] = {"year": int(s["year"].max()), "rows": [{"origin": k, "share": round(v / tot * 100, 1)} for k, v in top.items()]}
    return out


def wy_block() -> dict:
    p = DATA / "wy_county_travel_impacts_annual.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    out = {"counties": {}}
    for c in CONFIG.get("wy_focus_counties", []):
        g = df[df["county"] == c].sort_values("year")
        if g.empty:
            continue
        base = g[g["year"] == 2019]["visitor_spend_m"]
        base = float(base.iloc[0]) if len(base) else None
        out["counties"][c] = {
            "years": [int(y) for y in g["year"]],
            "visitor_spend_m": [float(x) for x in g["visitor_spend_m"]],
            "index_2019": [round(float(x) / base * 100, 1) if base else None for x in g["visitor_spend_m"]],
            "employment": [int(x) for x in g["employment"]],
        }
    return out


def nd_counties_block() -> dict:
    """Corridor counties: year-to-date (quarters posted so far) taxable sales vs prior year."""
    p = DATA / "nd_taxable_sales_quarterly.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p)
    cur = int(df["year"].max())
    lq = int(df[df["year"] == cur]["quarter"].max())
    rows = []
    for c in CONFIG.get("nd_focus_counties", []):
        g = df[df["county"] == c]
        yc = g[(g["year"] == cur) & (g["quarter"] <= lq)]["total"].sum()
        yp = g[(g["year"] == cur - 1) & (g["quarter"] <= lq)]["total"].sum()
        if yp:
            rows.append({"county": c, "cur": int(yc), "prev": int(yp), "pct": pct(yc, yp)})
    return {"current_year": cur, "latest_quarter": lq, "ytd": rows}


def qcew_block() -> dict:
    p = DATA / "qcew_county_quarterly.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype={"industry_code": str})
    lh = df[(df["industry_code"] == "1026") & df["avg_employment"].notna()]
    cur = int(lh["year"].max())
    lq = int(lh[lh["year"] == cur]["quarter"].max())
    out = {"current_year": cur, "latest_quarter": lq, "counties": {}, "latest": []}
    for c, g in lh.groupby("county"):
        out["counties"][c] = seasonal(g, "quarter", "avg_employment", 4, [y for y in BAND_YEARS if y < cur])
        a = g[(g["year"] == cur) & (g["quarter"] == lq)]["avg_employment"]
        b = g[(g["year"] == cur - 1) & (g["quarter"] == lq)]["avg_employment"]
        if len(a) and len(b):
            out["latest"].append({"county": c, "cur": float(a.iloc[0]), "prev": float(b.iloc[0]), "pct": pct(float(a.iloc[0]), float(b.iloc[0]))})
    return out


def recgov_block() -> dict:
    p = DATA / "recgov_monthly.csv"
    if not p.exists():
        return {}
    m = pd.read_csv(p)
    cur = int(m["year"].max())
    out = {"current_year": cur, "facilities": {}, "origin": {}}
    for f in ("Cottonwood Campground", "Buffalo Gap Campground", "CCC Campground"):
        g = m[m["facility"] == f]
        if len(g):
            out["facilities"][f] = seasonal(g, "month", "reservations", 12, [y for y in range(cur - 4, cur)])
    op = DATA / "recgov_origin_annual.csv"
    if op.exists():
        o = pd.read_csv(op)
        o = o[(o["facility"] == "Cottonwood Campground") & (o["year"] == o["year"].max())].sort_values("reservations", ascending=False).head(12)
        out["origin"] = {"facility": "Cottonwood Campground", "year": int(o["year"].max()) if len(o) else None, "rows": [{"state": r.state, "share": round(float(r.share) * 100, 1), "n": int(r.reservations)} for r in o.itertuples()]}
    return out


def interest_block() -> dict:
    out = {}
    wp = DATA / "wiki_pageviews_monthly.csv"
    if wp.exists():
        w = pd.read_csv(wp)
        cur = int(w["year"].max())
        out["wiki"] = {"current_year": cur, "articles": {a: seasonal(g, "month", "views", 12, BAND_YEARS) for a, g in w.groupby("article")}}
    tp = DATA / "google_trends_weekly.csv"
    if tp.exists():
        t = pd.read_csv(tp)
        weekly = t[t["geo"] == "US"]
        out["trends"] = {
            "terms": {term: {"weeks": g["week"].tolist(), "interest": g["interest"].tolist()} for term, g in weekly.groupby("term")},
            "by_state": [{"state": r.geo, "interest": int(r.interest)} for r in t[t["week"] == "last-12m"].sort_values("interest", ascending=False).head(12).itertuples()],
            "primary_term": CONFIG.get("trends_terms", [""])[0],
        }
    return out


def controls_block() -> dict:
    p = DATA / "controls_monthly.csv"
    if not p.exists():
        return {}
    c = pd.read_csv(p)
    cur = int(c["year"].max())
    cols = [x for x in c.columns if x not in ("year", "month")]
    def yr(y):
        g = c[c["year"] == y].set_index("month")
        return {col: [None if (m not in g.index or pd.isna(g.loc[m, col])) else float(g.loc[m, col]) for m in range(1, 13)] for col in cols}
    return {"current_year": cur, "columns": cols, "years": {str(cur): yr(cur), str(cur - 1): yr(cur - 1)}}


def library_block(nps: pd.DataFrame, cur: int) -> dict:
    manifest_all = json.loads((DATA / "manifest.json").read_text())
    ck = DATA / "acme_checkins_daily.csv"
    if ck.exists():
        # Direct ACME pull: TicketAnalytics scans are the authoritative attendance
        c = pd.read_csv(ck)
        d = c.groupby("date", as_index=False).agg(visitors=("checked_in", "sum"), tickets=("tickets", "sum"))
        d["revenue"] = 0.0
        manifest = {"as_of": manifest_all.get("acme", {}).get("checkins_last"), "visitors_source": "checked_in (TicketAnalytics, direct)"}
    else:
        p = DATA / "library_daily.csv"
        if not p.exists():
            return {}
        d = pd.read_csv(p)
        manifest = manifest_all.get("library", {})
    d["date"] = pd.to_datetime(d["date"])
    opening = OPENING
    since = d[(d["date"] >= opening) & (d["date"] < pd.Timestamp.today().normalize())].copy()  # complete days only
    since["ma7"] = since["visitors"].rolling(7, min_periods=1).mean().round()
    monthly = d[d["date"].dt.year == cur].groupby(d["date"].dt.month).agg(visitors=("visitors", "sum"), tickets=("tickets", "sum"), revenue=("revenue", "sum")).reset_index().rename(columns={"date": "month"})
    thro = nps[(nps["park"] == "THRO") & (nps["year"] == cur)].set_index("month")["visits"].to_dict()
    cap = []
    for r in monthly.itertuples():
        m = int(r.month)
        if m >= opening.month and thro.get(m) and r.visitors:
            cap.append({"month": m, "library": int(r.visitors), "trnp": int(thro[m]), "capture_pct": round(r.visitors / thro[m] * 100, 1)})
    last_full = since[since["date"] <= d["date"].max()]
    out = {
        "as_of": manifest.get("as_of"),
        "visitors_source": manifest.get("visitors_source"),
        "first_date": str(d["date"].min().date()),
        "daily_since_opening": {"dates": [x.strftime("%Y-%m-%d") for x in since["date"]], "visitors": [int(v) for v in since["visitors"]], "ma7": [int(v) for v in since["ma7"]], "tickets": [int(v) for v in since["tickets"]]},
        "since_opening": {"visitors": int(since["visitors"].sum()), "tickets": int(since["tickets"].sum()), "revenue": round(float(since["revenue"].sum()), 2), "days": int(len(since))},
        "monthly": [{"month": int(r.month), "visitors": int(r.visitors), "tickets": int(r.tickets), "revenue": round(float(r.revenue), 2)} for r in monthly.itertuples()],
        "capture": cap,
        "peak_day": {"date": str(since.loc[since["visitors"].idxmax(), "date"].date()), "visitors": int(since["visitors"].max())} if len(since) else None,
    }
    om = DATA / "acme_origin_monthly.csv"
    if om.exists():
        o = pd.read_csv(om)
        o = o[(o["year"] * 100 + o["month"]) >= opening.year * 100 + opening.month]
        tot = o["tickets"].sum()
        g = o.groupby("state")["tickets"].sum().sort_values(ascending=False)
        core = {"ND", "MN", "SD", "MT"}
        out["origin"] = {
            "as_of": manifest.get("as_of"), "basis": "tickets by buyer ZIP, all channels, since opening",
            "rows": [{"state": k, "visitors": int(v), "share": round(v / tot * 100, 1)} for k, v in g.head(15).items()],
            "new_market_share": round(float(g[~g.index.isin(core)].sum() / tot * 100), 1) if tot else None,
            "canada_share": round(float(g.get("Canada", 0) / tot * 100), 1) if tot else None,
        }
    else:
        op = DATA / "library_origin_states.csv"
        if op.exists():
            o = pd.read_csv(op)
            out["origin"] = {"as_of": str(o["as_of"].iloc[0]), "basis": "GA online purchases, YTD (Dashboard extract)", "rows": [{"state": r.state, "visitors": int(r.visitors), "share": round(float(r.share) * 100, 1)} for r in o.itertuples()]}
    return out


MEDORA = (46.914, -103.524)
METROS = {  # (state, county) -> metro label; counties not listed fall back to the ZIP's city
    ("MN", "Hennepin"): "Minneapolis–St. Paul", ("MN", "Ramsey"): "Minneapolis–St. Paul", ("MN", "Dakota"): "Minneapolis–St. Paul", ("MN", "Anoka"): "Minneapolis–St. Paul", ("MN", "Washington"): "Minneapolis–St. Paul", ("MN", "Scott"): "Minneapolis–St. Paul", ("MN", "Carver"): "Minneapolis–St. Paul", ("MN", "Wright"): "Minneapolis–St. Paul",
    ("ND", "Cass"): "Fargo–Moorhead", ("MN", "Clay"): "Fargo–Moorhead", ("ND", "Burleigh"): "Bismarck–Mandan", ("ND", "Morton"): "Bismarck–Mandan", ("ND", "Stark"): "Dickinson", ("ND", "Ward"): "Minot", ("ND", "Williams"): "Williston", ("ND", "Grand Forks"): "Grand Forks", ("MN", "Polk"): "Grand Forks", ("ND", "McKenzie"): "Watford City", ("ND", "Billings"): "Medora / Billings Co.",
    ("MT", "Yellowstone"): "Billings MT", ("MT", "Dawson"): "Glendive", ("MT", "Richland"): "Sidney MT", ("MT", "Cascade"): "Great Falls", ("MT", "Gallatin"): "Bozeman", ("MT", "Missoula"): "Missoula",
    ("SD", "Pennington"): "Rapid City", ("SD", "Minnehaha"): "Sioux Falls", ("SD", "Lincoln"): "Sioux Falls", ("SD", "Lawrence"): "Spearfish–Deadwood",
    ("NE", "Douglas"): "Omaha", ("NE", "Sarpy"): "Omaha", ("NE", "Lancaster"): "Lincoln NE",
    ("CO", "Denver"): "Denver", ("CO", "Arapahoe"): "Denver", ("CO", "Jefferson"): "Denver", ("CO", "Adams"): "Denver", ("CO", "Douglas"): "Denver", ("CO", "Boulder"): "Denver", ("CO", "El Paso"): "Colorado Springs",
    ("IL", "Cook"): "Chicago", ("IL", "Dupage"): "Chicago", ("IL", "Lake"): "Chicago", ("IL", "Will"): "Chicago", ("IL", "Kane"): "Chicago",
    ("WI", "Milwaukee"): "Milwaukee", ("WI", "Waukesha"): "Milwaukee", ("WI", "Dane"): "Madison",
    ("WA", "King"): "Seattle", ("WA", "Snohomish"): "Seattle", ("WA", "Pierce"): "Seattle", ("WA", "Spokane"): "Spokane",
    ("TX", "Dallas"): "Dallas–Fort Worth", ("TX", "Tarrant"): "Dallas–Fort Worth", ("TX", "Collin"): "Dallas–Fort Worth", ("TX", "Denton"): "Dallas–Fort Worth", ("TX", "Harris"): "Houston", ("TX", "Travis"): "Austin", ("TX", "Bexar"): "San Antonio",
    ("AZ", "Maricopa"): "Phoenix", ("AZ", "Pima"): "Tucson", ("UT", "Salt Lake"): "Salt Lake City", ("ID", "Ada"): "Boise",
    ("MO", "St. Louis"): "St. Louis", ("MO", "Jackson"): "Kansas City", ("KS", "Johnson"): "Kansas City", ("IA", "Polk"): "Des Moines",
    ("CA", "Los Angeles"): "Los Angeles", ("CA", "Orange"): "Los Angeles", ("CA", "San Diego"): "San Diego", ("CA", "Santa Clara"): "Bay Area", ("CA", "Alameda"): "Bay Area", ("CA", "San Francisco"): "Bay Area", ("CA", "Contra Costa"): "Bay Area", ("CA", "San Mateo"): "Bay Area", ("CA", "Sacramento"): "Sacramento",
    ("OR", "Multnomah"): "Portland", ("OR", "Washington"): "Portland", ("OR", "Clackamas"): "Portland",
    ("FL", "Miami-Dade"): "Miami", ("FL", "Hillsborough"): "Tampa", ("FL", "Orange"): "Orlando", ("GA", "Fulton"): "Atlanta", ("NC", "Wake"): "Raleigh", ("NC", "Mecklenburg"): "Charlotte",
    ("VA", "Fairfax"): "Washington DC", ("MD", "Montgomery"): "Washington DC", ("DC", "District Of Columbia"): "Washington DC", ("PA", "Philadelphia"): "Philadelphia", ("PA", "Allegheny"): "Pittsburgh", ("NY", "New York"): "New York City", ("NY", "Kings"): "New York City", ("NY", "Queens"): "New York City", ("MA", "Middlesex"): "Boston", ("MA", "Suffolk"): "Boston",
    ("OH", "Franklin"): "Columbus", ("OH", "Cuyahoga"): "Cleveland", ("OH", "Hamilton"): "Cincinnati", ("MI", "Wayne"): "Detroit", ("MI", "Oakland"): "Detroit", ("IN", "Marion"): "Indianapolis", ("TN", "Davidson"): "Nashville", ("NV", "Clark"): "Las Vegas",
}
BANDS = [(0, 50, "0–50 mi"), (50, 150, "50–150 mi"), (150, 300, "150–300 mi"), (300, 600, "300–600 mi"), (600, 100000, "600+ mi")]


def origin_geo_block() -> dict:
    """Drive-radius bands, feeder metros, and map points from ticket ZIPs since opening."""
    p = DATA / "acme_origin_zip.csv"
    if not p.exists():
        return {}
    import math
    import re

    try:
        import zipcodes  # noqa: PLC0415
    except ImportError:
        return {}

    def hav(a, b):
        r = 3958.8
        la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
        h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
        return 2 * r * math.asin(math.sqrt(h))

    z = pd.read_csv(p, dtype={"zip": str})
    rows = []
    for r in z.itertuples():
        zz = str(r.zip).strip()
        m = zipcodes.matching(zz) if re.fullmatch(r"\d{5}", zz) else []
        if m and m[0].get("lat"):
            lat, lon = float(m[0]["lat"]), float(m[0]["long"])
            county = m[0]["county"].replace(" County", "").replace(" Parish", "")
            rows.append({"zip": zz, "tickets": int(r.tickets), "state": m[0]["state"], "city": m[0]["city"].title(), "county": county, "lat": lat, "lon": lon, "miles": round(hav(MEDORA, (lat, lon)))})
        else:
            rows.append({"zip": zz, "tickets": int(r.tickets), "state": r.state, "city": None, "county": None, "lat": None, "lon": None, "miles": None})
    g = pd.DataFrame(rows)
    tot = int(g["tickets"].sum())
    geo = g.dropna(subset=["miles"])
    bands = []
    for lo, hi, label in BANDS:
        t = int(geo[(geo["miles"] >= lo) & (geo["miles"] < hi)]["tickets"].sum())
        bands.append({"band": label, "tickets": t, "share": round(t / tot * 100, 1)})
    geo = geo.copy()
    geo["metro"] = [METROS.get((s, c)) or f"{ci}, {s}" for s, c, ci in zip(geo["state"], geo["county"], geo["city"])]
    metros = geo.groupby("metro").agg(tickets=("tickets", "sum"), miles=("miles", "median"), state=("state", "first")).sort_values("tickets", ascending=False).head(30)
    feeders = [{"metro": k, "tickets": int(v.tickets), "share": round(v.tickets / tot * 100, 1), "miles": int(v.miles)} for k, v in metros.iterrows()]
    pts = geo.sort_values("tickets", ascending=False).head(2500)
    points = {"lat": [round(x, 3) for x in pts["lat"]], "lon": [round(x, 3) for x in pts["lon"]], "tickets": [int(x) for x in pts["tickets"]], "label": [f"{c}, {s} {z}" for c, s, z in zip(pts["city"], pts["state"], pts["zip"])]}
    return {"total_tickets": tot, "geocoded_share": round(float(geo["tickets"].sum()) / tot * 100, 1), "bands": bands, "feeders": feeders, "points": points, "medora": {"lat": MEDORA[0], "lon": MEDORA[1]}}


def airports_block() -> dict:
    out = {}
    mp = DATA / "airports_monthly.csv"
    if mp.exists():
        m = pd.read_csv(mp)
        cur = int(m["year"].max())
        lm = int(m[m["year"] == cur]["month"].max())
        out.update({"current_year": cur, "latest_month": lm, "monthly": {}, "ytd": []})
        for ap, g in m.groupby("airport"):
            out["monthly"][ap] = seasonal(g, "month", "passengers", 12, BAND_YEARS)
            yc = g[(g["year"] == cur) & (g["month"] <= lm)]["passengers"].sum()
            yp = g[(g["year"] == cur - 1) & (g["month"] <= lm)]["passengers"].sum()
            out["ytd"].append({"airport": ap, "cur": int(yc), "prev": int(yp), "pct": pct(yc, yp)})
    ap = DATA / "airports_annual.csv"
    if ap.exists():
        a = pd.read_csv(ap)
        out["annual"] = {air: {"years": [int(y) for y in g["year"]], "enplanements": [int(x) for x in g["enplanements"]]} for air, g in a.sort_values("year").groupby("airport")}
    return out


def nddot_block() -> dict:
    p = DATA / "nddot_atr_monthly.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype={"station": str})
    cur = int(df["year"].max())
    out = {"current_year": cur, "stations": {}}
    for sid, g in df.groupby("station"):
        out["stations"][sid] = {
            "name": g["name"].iloc[0],
            "route": g["route"].iloc[0],
            "madt": seasonal(g, "month", "madt", 12, [y for y in BAND_YEARS if y < cur - 1]),
            "weekend": seasonal(g, "month", "weekend_adt", 12, [y for y in BAND_YEARS if y < cur - 1]),
        }
    return out


def main() -> None:
    nps = load_nps()
    cur = int(nps["year"].max())
    thro_latest = int(nps[(nps["park"] == "THRO") & (nps["year"] == cur)]["month"].max())
    parks = [park_block(nps, p, thro_latest, cur) for p in CONFIG["nps_parks"]]
    manifest = json.loads((DATA / "manifest.json").read_text())
    out = {
        "built_at": now_iso(),
        "opening_date": CONFIG["opening_date"],
        "current_year": cur,
        "latest_month": thro_latest,
        "latest_month_label": f"{MONTH_ABBR[thro_latest - 1]} {cur}",
        "band_years": BAND_YEARS,
        "manifest": manifest,
        "parks": parks,
        "library": library_block(nps, cur),
        "origin_geo": origin_geo_block(),
        "border": border_block(),
        "airports": airports_block(),
        "nddot": nddot_block(),
        "nd_counties": nd_counties_block(),
        "qcew": qcew_block(),
        "recgov": recgov_block(),
        "interest": interest_block(),
        "controls": controls_block(),
        "nd_tax": nd_tax_block(),
        "nd_city": nd_city_block(),
        "mt": mt_block(),
        "wy": wy_block(),
    }
    DOCS_DATA.mkdir(parents=True, exist_ok=True)
    (DOCS_DATA / "dashboard.json").write_text(json.dumps(out, separators=(",", ":")) + "\n")
    for f in DATA.glob("*.csv"):
        shutil.copy(f, DOCS_DATA / f.name)
    shutil.copy(DATA / "manifest.json", DOCS_DATA / "manifest.json")
    print(f"built docs/data/dashboard.json ({cur}-{thro_latest:02d}); parks={len(parks)}")


if __name__ == "__main__":
    main()

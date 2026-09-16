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


def airports_block() -> list[dict]:
    df = pd.read_csv(DATA / "bts_airports_annual.csv")
    return df.sort_values("enplanements", ascending=False).to_dict("records")


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
        "border": border_block(),
        "airports": airports_block(),
        "nd_tax": nd_tax_block(),
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

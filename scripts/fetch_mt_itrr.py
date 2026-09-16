"""Pull Montana nonresident visitation from the ITRR (University of Montana)
Tableau Public workbook.

ITRR publishes its dashboard on Tableau Public with downloads enabled, and the
packaged workbook (.twbx) carries its data as Hyper extracts:

  * tbl_nonresidentvisitation  - monthly nonresident visits, 1991-present
  * the nonresident survey     - respondent-level rows with survey weights,
                                 origin state, Montana entry point, etc.

We keep the monthly series as-is and publish only WEIGHTED AGGREGATES of the
survey (by quarter x entry point, and by quarter x origin state). Respondent
rows are never written to the repo. "Wibaux/Beach" is the I-94 entry from
North Dakota, which makes it the corridor read for Medora.

Outputs: data/mt_nonresident_visitation_monthly.csv (year, month, visits)
         data/mt_nonresident_survey_shares.csv
             (year, quarter, dimension, value, weighted_visitors, share)
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

from common import USER_AGENT, update_manifest, write_csv

WORKBOOK_URL = "https://public.tableau.com/workbooks/ITRRDashboard.twb"


def read_hyper_tables(path: Path) -> dict[str, pd.DataFrame]:
    from tableauhyperapi import Connection, HyperProcess, Telemetry

    out = {}
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(hp.endpoint, str(path)) as c:
            for schema in c.catalog.get_schema_names():
                for t in c.catalog.get_table_names(schema):
                    cols = [str(col.name).strip('"') for col in c.catalog.get_table_definition(t).columns]
                    rows = c.execute_list_query(f"SELECT * FROM {t}")
                    out[str(t)] = pd.DataFrame(rows, columns=cols)
    return out


def main() -> int:
    r = requests.get(WORKBOOK_URL, headers={"User-Agent": USER_AGENT}, timeout=180)
    r.raise_for_status()
    tmp = Path(tempfile.mkdtemp(prefix="itrr_"))
    try:
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            z.extractall(tmp)
        visitation = None
        survey = None
        for hyper in tmp.rglob("*.hyper"):
            for name, df in read_hyper_tables(hyper).items():
                cols = set(df.columns)
                if {"year", "month", "visits"} <= cols and len(df) > 100:
                    visitation = df[["year", "month", "visits"]].astype(int)
                elif {"feweight", "feentryp", "feResidence", "Year", "QuarterFE"} <= cols:
                    survey = df
        if visitation is None:
            print("monthly visitation table not found in workbook", file=sys.stderr)
            return 1
        visitation = visitation.sort_values(["year", "month"])
        write_csv(visitation, "mt_nonresident_visitation_monthly.csv")

        shares = []
        if survey is not None:
            s = survey.rename(columns={"Year": "year", "QuarterFE": "quarter"}).copy()
            s["quarter"] = s["quarter"].astype(str).str.replace("Q", "").astype(int)
            for dim, col in (("entry_point", "feentryp"), ("origin", "feResidence")):
                g = s.dropna(subset=[col]).groupby(["year", "quarter", col])["feweight"].sum().reset_index()
                tot = g.groupby(["year", "quarter"])["feweight"].transform("sum")
                g["share"] = (g["feweight"] / tot).round(4)
                g = g.rename(columns={col: "value", "feweight": "weighted_visitors"})
                g["dimension"] = dim
                g["weighted_visitors"] = g["weighted_visitors"].round(1)
                shares.append(g[["year", "quarter", "dimension", "value", "weighted_visitors", "share"]])
        if shares:
            sh = pd.concat(shares).sort_values(["dimension", "year", "quarter", "share"], ascending=[True, True, True, False])
            write_csv(sh, "mt_nonresident_survey_shares.csv")
        latest = visitation.iloc[-1]
        update_manifest(
            "mt_itrr",
            visitation_latest=f"{int(latest.year)}-{int(latest.month):02d}",
            survey_years=sorted(int(y) for y in survey["Year"].unique()) if survey is not None else [],
            survey_n=int(len(survey)) if survey is not None else 0,
        )
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

"""Leading indicators of demand: Wikipedia pageviews and Google Trends.

Wikipedia: the official Wikimedia REST API, monthly user pageviews per
article, from July 2015. No key. Articles in config "wiki_articles".

Google Trends: via the unofficial pytrends library, weekly interest 0-100
for the configured terms, US and by state. Google rate-limits and changes
this endpoint; failures are logged and the previous file is kept.

Outputs: data/wiki_pageviews_monthly.csv (article, year, month, views)
         data/google_trends_weekly.csv   (term, week, geo, interest)
"""
from __future__ import annotations

import sys
import time

import pandas as pd
import requests

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

WIKI = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{article}/monthly/20150701/{end}"


def wiki() -> pd.DataFrame:
    end = pd.Timestamp.today().strftime("%Y%m%d")
    rows = []
    for a in CONFIG.get("wiki_articles", []):
        r = None
        for attempt in range(4):
            r = requests.get(WIKI.format(article=a, end=end), headers={"User-Agent": USER_AGENT}, timeout=60)
            if r.status_code != 429:
                break
            time.sleep(3 * (attempt + 1))
        if r.status_code != 200:
            print(f"wiki {a}: HTTP {r.status_code}", file=sys.stderr)
            continue
        for it in r.json().get("items", []):
            rows.append({"article": a, "year": int(it["timestamp"][:4]), "month": int(it["timestamp"][4:6]), "views": int(it["views"])})
        time.sleep(0.5)
    return pd.DataFrame(rows)


def trends() -> pd.DataFrame:
    try:
        from pytrends.request import TrendReq  # noqa: PLC0415
    except ImportError:
        print("pytrends not installed; skipping Google Trends", file=sys.stderr)
        return pd.DataFrame()
    terms = CONFIG.get("trends_terms", [])
    if not terms:
        return pd.DataFrame()
    rows = []
    try:
        pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30))
        pt.build_payload(terms[:5], timeframe="2019-01-01 " + pd.Timestamp.today().strftime("%Y-%m-%d"), geo="US")
        iot = pt.interest_over_time()
        for term in terms[:5]:
            if term in iot:
                for d, v in iot[term].items():
                    rows.append({"term": term, "week": d.strftime("%Y-%m-%d"), "geo": "US", "interest": int(v)})
        time.sleep(2)
        # by state, last 12 months, for the primary term
        pt.build_payload([terms[0]], timeframe="today 12-m", geo="US")
        by_state = pt.interest_by_region(resolution="REGION", inc_low_vol=True)
        for state, v in by_state[terms[0]].items():
            rows.append({"term": terms[0], "week": "last-12m", "geo": state, "interest": int(v)})
    except Exception as e:  # noqa: BLE001
        print(f"Google Trends failed: {e}", file=sys.stderr)
    return pd.DataFrame(rows)


def main() -> int:
    w = wiki()
    if len(w):
        write_csv(w.sort_values(["article", "year", "month"]), "wiki_pageviews_monthly.csv")
    t = trends()
    if len(t):
        write_csv(t, "google_trends_weekly.csv")
    update_manifest("interest", wiki_articles=int(w["article"].nunique()) if len(w) else 0, wiki_latest=f"{int(w.year.max())}-{int(w[w.year == w.year.max()].month.max()):02d}" if len(w) else None, trends_rows=len(t))
    return 0 if len(w) else 1


if __name__ == "__main__":
    sys.exit(main())

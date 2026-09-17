"""Pull Library attendance and visitor origin directly from ACME Ticketing's
reporting API (the same report-based API the Marketing Dashboard uses).

Two reports, both run as our own queryExpression so a Backoffice edit cannot
change what gets published:

  1. TicketAnalytics: tickets and checked-in scans per event per calendar
     day (grouped DayMonthYear -- never "Day", which returns day-of-month).
     CheckedInCount is the authoritative attendance figure; TicketQuantity
     is tickets sold. They are different things and are never substituted.
  2. Transactions "Event Sales by Zip Code" (definition 69010be2...):
     tickets by event x buyer ZIP, by event date. We aggregate ZIPs to
     state (and "Canada" / "Other") and keep ZIP-level ticket counts only
     for the aggregate origin map; no customer records are stored.

Requires ACME_API_KEY (and optionally ACME_API_BASE). Start date from
config "acme": {"since": "2026-06-01"}. Existing months are re-pulled for
the current and previous month only.

Outputs: data/acme_checkins_daily.csv  (date, event, tickets, checked_in)
         data/acme_origin_monthly.csv  (year, month, state, tickets)
         data/acme_origin_zip.csv      (zip, state, tickets)  -- since opening
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

import pandas as pd

from common import CONFIG, DATA, USER_AGENT, update_manifest, write_csv

ZIP_REPORT = "69010be2c3ff1045b9e1e7cb"  # E: Event Sales by Zip Code (Transactions)
CHECKIN_REPORT = "6a7657edee915a1f0bfef650"  # PE: Tickets Checked In (TicketAnalytics) -- used as the async job handle


def _base() -> str:
    return os.environ.get("ACME_API_BASE", "https://api.acmeticketing.com").rstrip("/")


def _api(method: str, path: str, payload: dict | None = None, timeout: int = 90) -> dict:
    headers = {"x-acme-api-key": os.environ["ACME_API_KEY"], "Accept": "application/json", "User-Agent": USER_AGENT}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(_base() + path, data=data, headers=headers, method=method)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:
                time.sleep(30)
                continue
            raise RuntimeError(f"{method} {path} -> HTTP {e.code}: {e.read().decode(errors='replace')[:300]}") from e
    raise RuntimeError("unreachable")


def run_report(report_id: str, query: dict, date_field: str, start: date, end: date) -> dict[str, list]:
    payload = {
        "reportUuid": report_id,
        "queryExpression": query,
        "dateRangeField": date_field,
        "startDate": start.strftime("%Y-%m-%dT00:00:00-0000"),
        "endDate": end.strftime("%Y-%m-%dT23:59:59-0000"),
    }
    iid = _api("POST", "/v2/b2b/async/report", payload)["id"]
    deadline = time.time() + 300
    while time.time() < deadline:
        s = str(_api("GET", f"/v2/b2b/async/report/{iid}").get("status", "")).lower()
        if s in ("complete", "completed", "success"):
            break
        if s in ("failed", "error", "cancelled"):
            raise RuntimeError(f"report {report_id} failed")
        time.sleep(5)
    res = _api("GET", f"/v2/b2b/async/report/json/{iid}")
    return {f["fieldName"]: f.get("values") or [] for f in res.get("resultFieldList", [])}


CHECKIN_QUERY = {
    "collectionName": "TicketAnalytics",
    "findQueries": [],
    "findFields": [{"fieldName": f, "include": True} for f in ("EventStartTime", "EventName", "TicketQuantity", "CheckedInCount")],
    "sortFields": [],
    "groupFields": [{"fieldName": "EventStartTime", "groupFunction": "DayMonthYear"}, {"fieldName": "EventName", "groupFunction": None}],
    "summaryFields": [{"fieldName": "TicketQuantity", "summaryFunction": "Sum"}, {"fieldName": "CheckedInCount", "summaryFunction": "Sum"}],
    "countFields": [],
    "limit": 0,
}


def zip_state(z: str) -> str:
    z = str(z or "").strip().upper()
    if re.match(r"^[A-Z]\d[A-Z]", z):
        return "Canada"
    m = re.match(r"^(\d{5})", z)
    if not m:
        return "Other/Unknown"
    try:
        import zipcodes  # noqa: PLC0415

        hit = zipcodes.matching(m.group(1))
        return hit[0]["state"] if hit else "Other/Unknown"
    except Exception:  # noqa: BLE001
        return "Other/Unknown"


def month_ranges(since: date, today: date):
    d = date(since.year, since.month, 1)
    while d <= today:
        nxt = date(d.year + (d.month == 12), (d.month % 12) + 1, 1)
        yield d, min(nxt - pd.Timedelta(days=1), today)
        d = nxt


def main() -> int:
    if not os.environ.get("ACME_API_KEY"):
        print("ACME_API_KEY not set", file=sys.stderr)
        return 1
    cfg = CONFIG.get("acme", {})
    since = date.fromisoformat(cfg.get("since", "2026-06-01"))
    today = date.today()

    # 1. Check-ins by day x event (one call; TicketAnalytics is small)
    cols = run_report(CHECKIN_REPORT, CHECKIN_QUERY, "EventStartTime", since, today)
    ck = pd.DataFrame({"date": cols.get("EventStartTime", []), "event": cols.get("EventName", []), "tickets": cols.get("TicketQuantity", []), "checked_in": cols.get("CheckedInCount", [])})
    ck["date"] = pd.to_datetime(ck["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    bad = int(ck["date"].isna().sum())
    ck = ck.dropna(subset=["date"])
    for c in ("tickets", "checked_in"):
        ck[c] = pd.to_numeric(ck[c], errors="coerce").fillna(0).astype(int)
    ck = ck[~ck["event"].str.lower().isin(["test event", "test"])].sort_values(["date", "event"])
    write_csv(ck, "acme_checkins_daily.csv")

    # 2. Origin by ZIP, month by month (current + previous month refreshed; older kept)
    op = DATA / "acme_origin_zip_monthly.csv"
    existing = pd.read_csv(op, dtype={"zip": str}) if op.exists() else pd.DataFrame(columns=["year", "month", "zip", "tickets"])
    zdef = _api("GET", f"/v2/b2b/analytics/report/definitions/{ZIP_REPORT}")
    zq = zdef["queryExpression"]
    frames = []
    for start, end in month_ranges(since, today):
        ym = (start.year, start.month)
        refresh = (ym >= (today.year, today.month)) or (ym == ((today.replace(day=1) - pd.Timedelta(days=1)).year, (today.replace(day=1) - pd.Timedelta(days=1)).month))
        if not refresh and len(existing) and ((existing["year"] == start.year) & (existing["month"] == start.month)).any():
            continue
        try:
            c = run_report(ZIP_REPORT, zq, "EventStartTime", start, end)
            df = pd.DataFrame({"zip": c.get("ZipCode", []), "tickets": c.get("Quantity", [])})
            df["tickets"] = pd.to_numeric(df["tickets"], errors="coerce").fillna(0).astype(int)
            df["zip"] = df["zip"].astype(str).str.strip().str.upper().str.replace(r"^(\d{5}).*$", r"\1", regex=True)
            g = df.groupby("zip", as_index=False)["tickets"].sum()
            g["year"], g["month"] = start.year, start.month
            frames.append(g)
            print(f"origin {start:%Y-%m}: {len(g)} ZIPs, {g.tickets.sum()} tickets")
        except Exception as e:  # noqa: BLE001
            print(f"FAILED origin {start:%Y-%m}: {e}", file=sys.stderr)
        time.sleep(1)
    if frames:
        new = pd.concat(frames)
        keep = existing[~existing.set_index(["year", "month"]).index.isin(new.set_index(["year", "month"]).index)] if len(existing) else existing
        zm = pd.concat([keep, new])
    else:
        zm = existing
    zm = zm[["year", "month", "zip", "tickets"]].sort_values(["year", "month", "zip"])
    write_csv(zm, "acme_origin_zip_monthly.csv")
    zm["state"] = zm["zip"].map(zip_state)
    st = zm.groupby(["year", "month", "state"], as_index=False)["tickets"].sum().sort_values(["year", "month", "tickets"], ascending=[True, True, False])
    write_csv(st, "acme_origin_monthly.csv")
    opening = pd.Timestamp(CONFIG["opening_date"])
    zo = zm[(zm["year"] * 100 + zm["month"]) >= opening.year * 100 + opening.month]
    zc = zo.groupby("zip", as_index=False)["tickets"].sum()
    zc["state"] = zc["zip"].map(zip_state)
    write_csv(zc.sort_values("tickets", ascending=False), "acme_origin_zip.csv")

    update_manifest(
        "acme",
        checkins_first=ck["date"].min() if len(ck) else None,
        checkins_last=ck["date"].max() if len(ck) else None,
        checkins_unparseable_dates=bad,
        checked_in_since_opening=int(ck[ck["date"] >= opening.strftime("%Y-%m-%d")]["checked_in"].sum()) if len(ck) else 0,
        origin_months=int(len(zm.groupby(["year", "month"]))),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

// Getting here: roads, airports, air-traveler origins, the Canadian border.
SECTIONS.travel = function (X) {
  const { d, cur } = X;

  group("Roads", "Interstate 94 is the front door: most Library visitors arrive on it. US 85 brings the Black Hills traffic north.");
  if (d.nddot && d.nddot.stations && d.nddot.stations["00279"]) {
    const st = d.nddot.stations["00279"], ny = d.nddot.current_year;
    card("c10", "I-94 traffic at Medora (NDDOT counter 279, Painted Canyon), average daily vehicles by month",
      `Month average daily traffic on I-94 7.8 miles west of US 85, both directions, from NDDOT's monthly Automatic Traffic Data reports. ${ny} against ${ny - 1}. NDDOT had not posted ${ny + 1} reports when this was built; they are picked up automatically when they appear. Weekend averages are in the table.`);
    seasonalChart("c10", MON, st.madt, ny, Object.assign({ periodName: "Month" }, ny === cur ? { openingIndex: 6 } : {}));
    const wk = st.weekend.years;
    table("c10", ["Month", `MADT ${ny - 1}`, `MADT ${ny}`, "Change", `Weekend ${ny - 1}`, `Weekend ${ny}`], MON.map((m, i) => {
      const a = st.madt.years[String(ny)]?.[i], b = st.madt.years[String(ny - 1)]?.[i];
      return [m, fmt(b), fmt(a), a != null && b ? pctTxt((a - b) / b * 100) : "–", fmt(wk[String(ny - 1)]?.[i]), fmt(wk[String(ny)]?.[i])];
    }));
  }

  const TC = d.tmas_corridor;
  if (TC && TC.stations && Object.keys(TC.stations).length) {
    const ids = Object.keys(TC.stations);
    card("ctm", "Summer traffic across the state lines: average daily vehicles, June–September",
      `Permanent counters on the routes into Medora and the neighboring gateways, from the hourly files each state reports to FHWA: I-94 at Medora and at Wibaux just over the Montana line, I-94 at Bad Route between Glendive and Miles City, US 85 at Buffalo and Belle Fourche in South Dakota (the Black Hills road north), and I-90 at the Wyoming–South Dakota line. Both directions, days with both directions counted; a summer with fewer than 60 good days is left blank (Medora and Wibaux lost directions in August–September 2024). FHWA posts each year the following March, so ${TC.years.at(-1) + 1} arrives in March ${TC.years.at(-1) + 2}.`);
    Plotly.newPlot("ctm", ids.map((s, i) => ({ x: TC.years, y: TC.stations[s].adt, mode: "lines+markers", name: TC.stations[s].label, connectgaps: false,
      line: { color: css(s === "279" ? "--s1" : SLOT[(i + 1) % 8]), width: s === "279" ? 3 : 1.8 }, marker: { size: 6, line: { color: css("--surface"), width: 2 } }, hovertemplate: "%{y:,}" })),
      baseLayout({ legend: { orientation: "h", y: -0.2, x: 0 }, margin: { l: 56, r: 16, t: 8, b: 110 }, height: 440, xaxis: { dtick: 1, gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") } }, yaxis: { gridcolor: css("--grid"), zeroline: false, tickfont: { color: css("--muted") }, rangemode: "tozero", tickformat: ",~s" } }), PCONF);
    table("ctm", ["Counter", ...TC.years.map(String)], ids.map(s => [TC.stations[s].label, ...TC.stations[s].adt.map(v => v == null ? "–" : fmt(v))]));
  }

  if (d.tmas && d.tmas.dow && Object.keys(d.tmas.dow).length) {
    const T = d.tmas, yrs = Object.keys(T.dow).slice(-4);
    card("c10b", "I-94 at Medora: average daily traffic by day of week, June–September",
      `The same NDDOT counter (279), from the hourly records North Dakota files with FHWA — which show what the monthly PDFs cannot: the weekly rhythm of summer traffic. FHWA posts each year in the following March, so this is the pre-opening baseline through ${T.years.at(-1)}; ${T.years.at(-1) + 1} arrives in March ${T.years.at(-1) + 2}. Both directions, days with both directions reported. July 4 week vs the rest of July is in the table.`);
    Plotly.newPlot("c10b", yrs.map((y, i) => ({
      type: "bar", name: y, x: T.dow_names, y: T.dow[y], marker: { color: i === yrs.length - 1 ? css("--s1") : css(["--s3", "--s4", "--gray-mark"][i] || "--gray-mark") }, hovertemplate: "%{x} " + y + ": %{y:,}<extra></extra>",
    })), baseLayout({ barmode: "group", bargap: 0.25, hovermode: "closest", yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, tickformat: ",~s", rangemode: "tozero" } }), PCONF);
    table("c10b", ["Year", "July 1–7 avg", "Rest of July avg", "Difference"], T.july4.slice().reverse().map(r => [r.year, r.july4_week, r.rest_of_july, pctTxt((r.july4_week - r.rest_of_july) / r.rest_of_july * 100)]));
  }

  group("Air", "Dickinson is the Library's airport; Bismarck is the practical gateway for most fly-drive visitors. Billings, Rapid City, Gillette and Sheridan complete the ring a road-tripper might fly into.");
  if (d.airports && d.airports.monthly) {
    const A = d.airports, ay = A.current_year, alm = A.latest_month;
    card("c9", `Regional airports: passengers, Jan–${MON[alm - 1]} ${ay} vs ${ay - 1}`,
      `Year-to-date departing passengers by airport (BTS T-100, U.S. carriers, ~3-month lag). Dickinson (DIK) is highlighted. North Dakota: DIK, BIS, MOT, XWA (Williston), FAR. Neighbors: BIL (Billings), RAP (Rapid City), GCC (Gillette), SHR (Sheridan).`);
    const rk = changeBars("c9", A.ytd.map(r => ({ label: r.airport, pct: r.pct, cur: r.cur, prev: r.prev, hi: r.airport === "DIK" })), { left: 60 });
    table("c9", ["Airport", `YTD ${ay}`, `YTD ${ay - 1}`, "Change"], rk.slice().reverse().map(r => [r.label, r.cur, r.prev, pctTxt(r.pct)]));

    const N = d.ndac;
    for (const [code, label] of [["BIS", "Bismarck (BIS)"], ["DIK", "Dickinson (DIK)"]]) {
      if (N && N.airports && N.airports[code]) {
        const s = N.airports[code], ny = N.current_year, nlm = N.latest_month;
        card("c9" + code, `${label} passenger boardings, monthly`,
          `${ny} against ${ny - 1} and the ${s.band_years[0]}–${s.band_years.at(-1)} range, through ${MON[nlm - 1]} ${ny}. Source: ND Aeronautics Commission monthly boarding reports (all carriers, ~3-week lag). ${N.months_reported.length < nlm ? `NDAC's ${ny} reports for ${N.months_reported.length ? "Jan–" + MON[N.months_reported[0] - 2] : ""} were not retrievable from its site.` : ""} Other ND airports in the table.`);
        seasonalChart("c9" + code, MON, s, ny, { periodName: "Month", openingIndex: 6 });
        const mr = N.months_reported;
        appendTable("c9" + code, `All ND commercial airports, ${MON[mr[0] - 1]}–${MON[mr.at(-1) - 1]} ${ny} vs ${ny - 1} (NDAC)`, ["Airport", String(ny), String(ny - 1), "Change"],
          N.ytd.slice().sort((a, b) => b.pct - a.pct).map(r => [`${r.name} (${r.airport})`, r.cur, r.prev, pctTxt(r.pct)]));
      }
    }
    if (A.annual) {
      const codes = Object.keys(A.annual);
      const yrs = [...new Set(codes.flatMap(c => A.annual[c].years))].sort();
      box("cfaa", "Regional airports, annual enplanements (FAA)",
        `<p class="note">FAA calendar-year enplanements at commercial-service airports; the latest year is preliminary. Long-run context for the monthly chart above.</p>` +
        tableHtml(["Year", ...codes], yrs.slice().reverse().map(y => [y, ...codes.map(c => { const i = A.annual[c].years.indexOf(y); return i >= 0 ? A.annual[c].enplanements[i] : "–"; })])));
    }
  }

  if (d.db1b && d.db1b.dests && Object.keys(d.db1b.dests).length) {
    const B = d.db1b;
    const dests = ["BIS", "DIK", "FAR", "MOT"].filter(k => B.dests[k]);
    box("cdb1b", "Where air travelers into the region start their trips",
      `<p class="note">BTS Origin and Destination Survey (a 10% sample of airline tickets, scaled ×10): itineraries that land at each airport, by the traveler's home airport, excluding trips that start at the region's own airports. Rolling four quarters, ${B.quarters[0]}–${B.quarters.at(-1)}; BTS posts a quarter about six months after it ends. The air-travel counterpart to the feeder-market table in the Library section. Read Mesa (AZA), Las Vegas and Sanford (SFB) with care: those are Allegiant leisure routes, and North Dakotans who winter in Arizona show up as Arizona-origin travelers.</p>
      <div class="grid2">${dests.map(k => `<div><p class="note"><b>${k}</b> — ${fmt(B.dests[k].total)} inbound passengers</p>${tableHtml(["Home airport", "Share", "Pax"], B.dests[k].origins.slice(0, 10).map(o => [`${o.origin} (${o.state})`, o.share.toFixed(1) + "%", o.passengers]))}</div>`).join("")}</div>
      <p class="note">By home state, all four airports: ${B.by_state.slice(0, 8).map(s => `${s.state} ${s.share.toFixed(1)}%`).join(" · ")}. Summer quarter (Q3) inbound to BIS + DIK: ${Object.entries(B.q3_trend).map(([y, v]) => `${y} ${fmt(v)}`).join(" · ")}.</p>`);
  }

  group("The Canadian border", "Inbound crossings at North Dakota's ports. The Canadian-side count of prairie residents driving home is in the Region section.");
  const nd = d.border.states["North Dakota"];
  card("c4", "Canadian visitors: personal vehicles entering North Dakota",
    `Monthly inbound personal-vehicle crossings at all ND land ports (Pembina and Portal are the largest), ${cur} against ${cur - 1} and the ${nd.band_years[0]}–${nd.band_years.at(-1)} range. Context for the Canadian market, not a Library indicator. Source: BTS Border Crossing Entry Data, through ${d.border.latest_month}.`);
  seasonalChart("c4", MON, nd, cur, { periodName: "Month", openingIndex: 6 });
};

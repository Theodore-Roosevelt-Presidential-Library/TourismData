// The park and Medora: TRNP visits, Painted Canyon, overnight stays, park spending, campgrounds.
SECTIONS.park = function (X) {
  const { d, thro, cur, prev } = X;

  card("c1", "Theodore Roosevelt NP, monthly recreation visits",
    `${cur} against the pre-opening range (${d.band_years.join(", ")}; 2020–21 excluded). Shaded band = min to max of those years. Source: NPS IRMA STATS. How TRNP compares with the other parks in the region is in the Region section.`);
  const bandMin = thro.band.map(b => b ? b.min : null), bandMax = thro.band.map(b => b ? b.max : null);
  Plotly.newPlot("c1", [
    { x: MON, y: bandMax, mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: MON, y: bandMin, mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: css("--band"), name: "Pre-opening range", hoverinfo: "skip" },
    { x: MON, y: thro.years[String(prev)], mode: "lines", name: String(prev), line: { color: css("--gray-mark"), width: 2 }, hovertemplate: "%{y:,}" },
    { x: MON, y: thro.years[String(cur)], mode: "lines+markers", name: String(cur), line: { color: css("--s1"), width: 2.5 }, marker: { size: 8, line: { color: css("--surface"), width: 2 } }, hovertemplate: "%{y:,}" },
  ], baseLayout({
    shapes: [{ type: "line", x0: 6, x1: 6, xref: "x", y0: 0, y1: 1, yref: "paper", line: { color: css("--axis"), width: 1 } }],
    annotations: [{ x: 6, y: 1, xref: "x", yref: "paper", text: "Library opens", showarrow: false, xanchor: "left", yanchor: "top", xshift: 6, font: { size: 12, color: css("--muted") } }],
  }), PCONF);
  table("c1", ["Month", String(prev), String(cur), "Change", "Band min", "Band max"], MON.map((m, i) => {
    const a = thro.years[String(cur)][i], b = thro.years[String(prev)][i];
    return [m, b, a, a != null && b ? pctTxt((a - b) / b * 100) : "–", bandMin[i], bandMax[i]];
  }));

  if (d.nps_detail && d.nps_detail.painted_canyon) {
    const PC = d.nps_detail.painted_canyon, py = PC.current_year;
    card("cpc", "Painted Canyon rest area: vehicles counted, monthly",
      `TRNP's traffic counter at the Painted Canyon overlook off I-94, 7 miles east of Medora — the park entrance most visitors pass, counted May–October. ${py} against ${py - 1} and the ${PC.band_years[0]}–${PC.band_years.at(-1)} range. Source: NPS IRMA "Traffic Counts" report. TRNP by location (South Unit, North Unit, Painted Canyon, campers) and overnight stays are in the table.`);
    seasonalChart("cpc", MON, PC, py, { periodName: "Month", openingIndex: 6 });
    const PU = d.nps_detail.public_use;
    if (PU && PU.rows.length) {
      appendTable("cpc", `TRNP public use by location, ${MON[PU.month - 1]} ${PU.year} and year to date (NPS "Monthly Public Use"; IRMA publishes only the latest month, so this table grows one month per run — ${PU.history_months} month${PU.history_months === 1 ? "" : "s"} kept so far)`,
        ["Location", `${MON[PU.month - 1]} ${PU.year}`, `Jan–${MON[PU.month - 1]} ${PU.year}`], PU.rows.map(r => [r.location, r.month, r.ytd]));
    }
    const ON = d.nps_detail.overnight;
    if (ON) {
      const cats = Object.keys(ON.categories);
      appendTable("cpc", `TRNP overnight stays by year (NPS "Overnight Stays"; through ${ON.years.at(-1)})`, ["Year", ...cats, "Total"],
        ON.years.map((y, i) => [y, ...cats.map(c => ON.categories[c][i]), cats.reduce((a, c) => a + ON.categories[c][i], 0)]).reverse());
    }
  }

  if (d.vse && d.vse.parks && d.vse.parks.THRO) {
    const V = d.vse.parks.THRO;
    card("c7c", "Theodore Roosevelt NP visitor spending in the gateway region, annual",
      `NPS Visitor Spending Effects: what non-local park visitors spend within about 60 miles of the park, with the jobs that spending supports (bars = spending, line = jobs). ${V.years.at(-1)}: $${(V.spending.at(-1) / 1e6).toFixed(1)}M and ${fmt(V.jobs.at(-1))} jobs from ${fmt(V.visits.at(-1))} visits. The ${V.years.at(-1) + 1} edition, the first with the Library open, lands next spring. Spending by sector in the table. Source: NPS IRMA VSE API.`);
    Plotly.newPlot("c7c", [
      { type: "bar", name: "Visitor spending", x: V.years, y: V.spending, marker: { color: css("--s1") }, hovertemplate: "$%{y:,.0f}<extra>spending</extra>" },
      { type: "scatter", mode: "lines+markers", name: "Jobs supported", x: V.years, y: V.jobs, yaxis: "y2", line: { color: css("--s2"), width: 2 }, marker: { size: 6, line: { color: css("--surface"), width: 2 } }, hovertemplate: "%{y:,} jobs<extra></extra>" },
    ], baseLayout({ bargap: 0.3, margin: { l: 56, r: 56, t: 8, b: 44 }, yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, tickprefix: "$", tickformat: ",~s", rangemode: "tozero" },
      yaxis2: { overlaying: "y", side: "right", showgrid: false, tickfont: { color: css("--muted") }, rangemode: "tozero", title: { text: "jobs", font: { size: 11, color: css("--muted") } } }, xaxis: { dtick: 1, gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") } } }), PCONF);
    const SL = V.sectors_latest;
    table("c7c", ["Year", "Visits", "Visitor spending", "Jobs", "Labor income", "Economic output"], V.years.map((y, i) => [y, V.visits[i], money(V.spending[i]), V.jobs[i], money(V.labor_income[i]), money(V.output[i])]).reverse());
    const tot = SL.rows.reduce((a, r) => a + r.value, 0);
    appendTable("c7c", `Visitor spending by sector, ${SL.year}`, ["Sector", "Spending", "Share"], SL.rows.map(r => [r.sector, money(r.value), (r.value / tot * 100).toFixed(1) + "%"]));
  }

  if (d.recgov && d.recgov.facilities && d.recgov.facilities["Cottonwood Campground"]) {
    const R = d.recgov, ry = R.current_year;
    for (const [f, label] of [["Cottonwood Campground", "Cottonwood Campground (TRNP South Unit)"], ["Buffalo Gap Campground", "Buffalo Gap Campground (USFS, west of Medora)"]]) {
      if (!R.facilities[f]) continue;
      card("c12" + f.slice(0, 3), `${label}: reservations by arrival month`,
        `Reservations starting each month, from Recreation.gov's public reservation history. ${ry} against ${ry - 1} and the ${R.facilities[f].band_years[0]}–${R.facilities[f].band_years.at(-1)} range. Campgrounds sell out in July–August, so this is a floor on demand, not a measure of it; the origin mix is the real value.`);
      seasonalChart("c12" + f.slice(0, 3), MON, R.facilities[f], ry, { periodName: "Arrival month" });
    }
    if (R.origin && R.origin.rows.length) {
      box("ccamp", `Where Cottonwood campers come from, ${R.origin.year}`,
        `<p class="note">Share of reservations by customer ZIP state — a check on the Library's own origin mix at the top of the page.</p>` +
        tableHtml(["State", "Share", "Reservations"], R.origin.rows.map(r => [r.state, r.share.toFixed(1) + "%", r.n])));
    }
  }
};

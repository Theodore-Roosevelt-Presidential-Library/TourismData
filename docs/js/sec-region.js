// The region: North Dakota next to Montana, South Dakota, Wyoming, Canada and overseas markets.
SECTIONS.region = function (X) {
  const { d, cur, prev, anomalous } = X;

  // ---- State summary: the same five measures for every state
  if (d.state_summary && d.state_summary.length) {
    const cell = (c) => {
      if (!c) return `<td class="na">–</td>`;
      const v = c.unit === "$" ? moneyShort(c.value) : c.unit === "%" ? c.value.toFixed(1) + "%" : c.unit === "/day" ? fmt(c.value) + "/day" : fmt(c.value);
      return `<td><b>${v}</b>${c.pct != null ? " " + pctSpan(c.pct) : ""}<div class="sub2">${c.period}${c.note ? " · " + c.note : ""}</div></td>`;
    };
    const head = ["", "Park visits, year to date", "Visitor-spending signal", "Traffic entering", "Overseas visitors, YTD", "Outdoor recreation, share of economy"];
    box("cr0", "The region at a glance",
      `<p class="note">Each state on the same five measures, with the change from the same period a year earlier. The sources differ by state — Medora's occupancy tax, South Dakota's tourism tax, Wyoming's statewide lodging tax, Montana's nonresident-visitor estimate (Montana does not publish lodging tax by region) — so compare the direction and size of the changes across rows, not the levels. Traffic is the summer average at the counter nearest each gateway (FHWA, posted a year behind); Canada's row is Saskatchewan and Manitoba residents driving home from the U.S. Overseas visitors count arrivals naming the state as their first U.S. address. Park visits exclude flagged parks (counter outages or count changes).</p>
      <div class="scroll"><table class="summary"><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead><tbody>
      ${d.state_summary.map(r => `<tr><td><b>${r.state}</b></td>${cell(r.parks)}${cell(r.lodging)}${cell(r.traffic)}${cell(r.overseas)}${cell(r.outdoor)}</tr>`).join("")}</tbody></table></div>`);
  }

  // ---- Comparison parks
  group("Comparison parks", "Is TRNP moving with the region or ahead of it? Twelve National Park Service units across the four states, Theodore Roosevelt NP included, on the same months.");
  const k = X.thro.kpi, months = k.post_opening.months;
  const label = `Jul–${MON[months.at(-1) - 1]} ${cur} vs ${prev}`;
  const flagNames = [...anomalous].map(c => d.parks.find(p => p.code === c).name);
  card("c2", `Change since opening, by park (${label})`,
    `Recreation visits in the months since July 4, each park against the same months of ${prev}. Parks that have not posted the latest month compare only the months they have.` +
    (anomalous.size ? ` <span class="flag">flag</span> ${flagNames.join(", ")}: counts look discontinuous (a counter outage or a change in how the park counts) and are excluded from the control median and the state summary.` : ""));
  const ranked = [...d.parks].filter(p => p.kpi.post_opening.pct != null).sort((a, b) => a.kpi.post_opening.pct - b.kpi.post_opening.pct);
  Plotly.newPlot("c2", [{
    type: "bar", orientation: "h",
    y: ranked.map(p => p.name + (anomalous.has(p.code) ? " ⚑" : "")), x: ranked.map(p => p.kpi.post_opening.pct),
    marker: { color: ranked.map(p => p.code === "THRO" ? css("--s1") : css("--gray-mark")) },
    text: ranked.map(p => pctTxt(p.kpi.post_opening.pct)), textposition: "outside", textfont: { color: css("--ink-2") },
    cliponaxis: false, hovertemplate: "%{y}<br>%{x:+.1f}%<extra></extra>",
  }], baseLayout({
    hovermode: "closest", margin: { l: 210, r: 60, t: 8, b: 40 }, showlegend: false, bargap: 0.35, height: Math.max(340, 34 * ranked.length + 60),
    xaxis: { ticksuffix: "%", gridcolor: css("--grid"), zeroline: true, zerolinecolor: css("--axis"), tickfont: { color: css("--muted") },
      range: [Math.min(0, ...ranked.map(p => p.kpi.post_opening.pct)) * 1.9 - 4, Math.max(0, ...ranked.map(p => p.kpi.post_opening.pct)) * 1.18 + 4] },
    yaxis: { tickfont: { color: css("--ink-2") }, automargin: true },
  }), PCONF);
  table("c2", ["Park", "State", `${label.split(" vs ")[0]}`, `Same months ${prev}`, "Change"], ranked.slice().reverse().map(p => [p.name, p.state, p.kpi.post_opening.cur, p.kpi.post_opening.prev, pctTxt(p.kpi.post_opening.pct)]));

  card("c3", `Monthly change vs ${prev}, by park (Apr–Oct)`,
    `Year-over-year change in recreation visits for each ${cur} season month. Winter months are omitted: a few hundred visits swing the percentage wildly. Theodore Roosevelt NP in blue; the others are the regional comparison set.` + (anomalous.size ? ` Flagged parks omitted.` : ""));
  const c3parks = d.parks.filter(p => !anomalous.has(p.code));
  const SEASON = [3, 4, 5, 6, 7, 8, 9];
  Plotly.newPlot("c3", c3parks.map((p, i) => ({
    x: SEASON.map(m => MON[m]), y: SEASON.map(m => p.yoy_pct[m]), mode: "lines+markers", name: p.name,
    line: { color: css(SLOT[i % 8]), width: p.code === "THRO" ? 3 : 1.5 }, marker: { size: p.code === "THRO" ? 8 : 6, line: { color: css("--surface"), width: 2 } }, hovertemplate: "%{y:+.1f}%",
  })), baseLayout({
    yaxis: { ticksuffix: "%", gridcolor: css("--grid"), zeroline: true, zerolinecolor: css("--axis"), tickfont: { color: css("--muted") } },
    legend: { orientation: "h", y: -0.22, x: 0 }, margin: { l: 56, r: 16, t: 8, b: 110 }, height: 440,
  }), PCONF);
  table("c3", ["Month", ...c3parks.map(p => p.code)], SEASON.map(i => [MON[i], ...c3parks.map(p => p.yoy_pct[i] == null ? "–" : pctTxt(p.yoy_pct[i]))]));

  // ---- Montana
  group("Montana", "I-94 runs straight from Glendive and Billings to Medora. Montana's university survey tracks who enters from North Dakota.");
  if (d.mt && d.mt.i94_from_nd) {
    const s6 = d.mt.i94_from_nd, y6 = s6.current_year;
    const ndRank = d.mt.top_origins_latest_year.rows.findIndex(r => r.origin === "North Dakota") + 1;
    card("c6", "Montana nonresident visitors entering via I-94 from North Dakota",
      `Share of Montana's nonresident visitors who entered at Wibaux/Beach, by quarter, weighted: ${y6} against ${y6 - 1} and the ${s6.band_years[0]}–${s6.band_years.at(-1)} range. Source: ITRR Nonresident Travel Survey, University of Montana. North Dakota residents were ${d.mt.origin_nd.years[String(y6)].filter(v => v != null).reduce((a, v, _, arr) => a + v / arr.length, 0).toFixed(1)}% of Montana's nonresident visitors in ${y6}, ranking #${ndRank} among origin states.`);
    seasonalChart("c6", QTR, s6, y6, { periodName: "Quarter", hover: "%{y:.1f}%", fmt: pct1, yaxis: { ticksuffix: "%", tickformat: ".1f" } });
  }
  if (d.mt && d.mt.visitation) {
    const v7 = d.mt.visitation, y7 = d.mt.current_year;
    card("c7", "Montana nonresident visitation, monthly",
      `ITRR's estimate of nonresident visitors to Montana: ${y7} against ${y7 - 1} and the ${v7.band_years[0]}–${v7.band_years.at(-1)} range. Updated with each survey release.`);
    seasonalChart("c7", MON, v7, y7, { periodName: "Month" });
  }

  // ---- South Dakota
  group("South Dakota", "The Black Hills are the big draw next door, and US 85 links them to Medora.");
  const SD = d.sd_tourism;
  if (SD && SD.state) {
    const sy = SD.current_year, ml = SD.months;
    card("csd", "South Dakota tourism-taxable sales, statewide, by filing month",
      `Sales subject to South Dakota's 1.5% state tourism tax (lodging, campgrounds, amusements, visitor retail) from the Department of Revenue's monthly county report. Months are when RETURNS WERE FILED, so the July filing is mostly June business. ${sy} against ${sy - 1} and the ${SD.state.band_years[0]}–${SD.state.band_years.at(-1)} range. Jan–${MON[ml.at(-1) - 1]} filings: ${moneyShort(SD.state_ytd.cur)}, ${pctTxt(SD.state_ytd.pct)}. The table has the Black Hills and northwest counties: Hotels & Motels is the like-for-like lodging line; the "disclosed" total leaves out business types with fewer than three licensees, so it is a floor.`);
    seasonalChart("csd", MON, SD.state, sy, { periodName: "Filing month", hover: "$%{y:,.0f}", fmt: moneyShort, yaxis: { tickprefix: "$" } });
    appendTable("csd", `Year to date, Jan–${MON[ml.at(-1) - 1]} ${sy} filings vs ${sy - 1}`, ["County", "Hotels & motels", "Change", "All disclosed tourism lines", "Change"],
      SD.ytd.map(r => [r.county, moneyShort(r.hotels_cur), pctTxt(r.hotels_pct), moneyShort(r.disclosed_cur), pctTxt(r.disclosed_pct)]));
    if (SD.black_hills_hotels) {
      const bh = SD.black_hills_hotels;
      appendTable("csd", "Black Hills hotels & motels (Pennington, Lawrence, Custer, Fall River, Meade), by filing month", ["Month", String(sy - 1), String(sy), "Change"],
        MON.map((m, i) => { const a = bh.years[String(sy)]?.[i], b = bh.years[String(sy - 1)]?.[i]; return [m, moneyShort(b), moneyShort(a), a != null && b ? pctTxt((a - b) / b * 100) : "–"]; }));
    }
  }

  // ---- Wyoming
  group("Wyoming", "Devils Tower and the I-90 corridor; Campbell and Crook counties are the Wyoming side of the Black Hills.");
  if (d.wy && d.wy.counties && Object.keys(d.wy.counties).length) {
    const names = Object.keys(d.wy.counties);
    card("c8", "Wyoming gateway counties: visitor spending, 2019 = 100",
      `Direct visitor spending by county, indexed to 2019 so counties of different size share one axis (Park County is ~15× Crook). Crook = Devils Tower; Park = Cody and Yellowstone's east gate. Source: Dean Runyan Associates for the Wyoming Office of Tourism, nominal dollars.`);
    Plotly.newPlot("c8", names.map((n, i) => ({
      x: d.wy.counties[n].years, y: d.wy.counties[n].index_2019, mode: "lines+markers", name: n,
      line: { color: css(SLOT[i]), width: 2 }, marker: { size: 6, line: { color: css("--surface"), width: 2 } },
      customdata: d.wy.counties[n].visitor_spend_m, hovertemplate: "%{y:.1f} ($%{customdata:.1f}M)",
    })), baseLayout({ yaxis: { gridcolor: css("--grid"), zeroline: false, tickfont: { color: css("--muted") } }, xaxis: { dtick: 1, gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") } } }), PCONF);
    const yrs8 = d.wy.counties[names[0]].years;
    table("c8", ["Year", ...names.map(n => n + " ($M)")], yrs8.map((y, i) => [y, ...names.map(n => d.wy.counties[n].visitor_spend_m[i].toFixed(1))]).reverse());
  }
  const WL = d.wy_lodging;
  if (WL && WL.rows && WL.rows.length) {
    const fy = WL.fiscal_year;
    card("cwyl", `Wyoming lodging tax by county, FY${fy} vs FY${fy - 1}`,
      `The statewide 3% portion of Wyoming's lodging tax, by county, for the state fiscal year ending June ${fy}. Local option rates differ by county, so the 3% portion is the like-for-like measure; lodging receipts are about 33 times it (shown in the table). Annual and about five months behind, but it updates the Dean Runyan spending study above, which comes out less often.`);
    changeBars("cwyl", WL.rows.map(r => ({ label: r.county, pct: r.pct, curTxt: money(r.cur), prevTxt: money(r.prev), hi: r.county === "Statewide" })), { left: 110 });
    table("cwyl", ["County", `3% tax FY${fy}`, `FY${fy - 1}`, "Change", `Implied lodging receipts FY${fy}`], WL.rows.map(r => [r.county, money(r.cur), money(r.prev), pctTxt(r.pct), moneyShort(r.receipts_cur)]));
  }

  // ---- Canada
  group("Canada", "Saskatchewan and Manitoba are the Library's closest international markets.");
  const SC = d.statcan;
  if (SC && SC.sk_mb) {
    const cy = SC.current_year;
    card("ccan", "Saskatchewan and Manitoba residents driving home from the U.S., monthly",
      `Statistics Canada's count of Canadian residents re-entering by automobile at Saskatchewan and Manitoba ports — the prairie market that drives south to North Dakota and Montana. This is the Canadian side of the border card in Getting Here. ${cy} against ${cy - 1} and the 2017–19 plus 2023–25 range (the pandemic years are left out). Jan–${MON[SC.latest_month - 1]}: ${fmt(SC.sk_mb_ytd.cur)}, ${pctTxt(SC.sk_mb_ytd.pct)}. Alberta, overnight trips, and Americans driving into Canada are in the table.`);
    seasonalChart("ccan", MON, SC.sk_mb, cy, { periodName: "Month", bandName: "2017–19, 2023–25 range" });
    appendTable("ccan", `Jan–${MON[SC.latest_month - 1]} ${cy} vs ${cy - 1}, by province of entry`, ["Province", "Series", "Trips", String(cy), String(cy - 1), "Change"],
      SC.ytd.map(r => [r.province, r.series, r.type === "overnight" ? "Overnight" : "All", r.cur, r.prev, pctTxt(r.pct)]));
  }

  // ---- Overseas visitors (NTTO)
  group("Overseas visitors", "International arrivals from outside North America, from the Commerce Department's I-94 program.");
  const NT = d.ntto;
  if (NT && NT.states && NT.states["North Dakota"]) {
    const ny = NT.current_year, nd = NT.states["North Dakota"];
    const ndY = NT.ytd.find(r => r.state === "North Dakota"), usY = NT.ytd.find(r => r.state === "United States");
    card("cntto", "Overseas visitors naming North Dakota as their first U.S. stop, monthly",
      `Arrivals from overseas (excluding Canada and Mexican land crossings) whose first intended U.S. address is in North Dakota, from the National Travel and Tourism Office's monthly I-94 Summary & Analysis. ${ny} against ${ny - 1} and the 2022–25 range.${NT.preliminary.length ? ` ${NT.preliminary.map(p => MON[+p.slice(5) - 1] + " " + p.slice(0, 4)).join(" and ")} ${NT.preliminary.length > 1 ? "are" : "is"} preliminary.` : ""} The first address undercounts states visited later in a trip — a German couple landing in Denver and driving to Medora counts for Colorado — so read this as a floor and watch the trend. Jan–${MON[NT.latest_month - 1]}: North Dakota ${pctTxt(ndY.pct)}, all U.S. ${pctTxt(usY.pct)}. The neighbors, and where North Dakota's overseas visitors live, are in the table.`);
    seasonalChart("cntto", MON, nd, ny, { periodName: "Month", openingIndex: 6 });
    appendTable("cntto", `Jan–${MON[NT.latest_month - 1]} ${ny} vs ${ny - 1}`, ["State", String(ny), String(ny - 1), "Change", "Share of U.S. arrivals"], NT.ytd.map(r => [r.state, r.cur, r.prev, pctTxt(r.pct), r.share_of_us_pct != null ? r.share_of_us_pct.toFixed(2) + "%" : "–"]));
    const R = NT.nd_regions;
    appendTable("cntto", `North Dakota's overseas visitors by world region, ${MON[+R.from.slice(5) - 1]} ${R.from.slice(0, 4)}–${MON[+R.to.slice(5) - 1]} ${R.to.slice(0, 4)}`, ["Region of residence", "Arrivals", "Share"], R.rows.map(r => [r.region.replace(/\n/g, " "), r.arrivals, pct1(r.share)]));
  }

  // ---- Outdoor recreation economy (BEA)
  const OR = d.orsa;
  if (OR && OR.rows && OR.rows.length) {
    group("The outdoor economy", "How much of each state's economy is outdoor recreation, on one national yardstick.");
    card("corsa", `Outdoor recreation as a share of each state's economy, ${OR.year}`,
      `BEA's Outdoor Recreation Satellite Account: outdoor recreation value added as a percent of state GDP, ${OR.year} (rank among ${OR.n_states} states in the table, with jobs). It counts everything from guided trips and lodging to boat and RV sales, so it is a measure of each state's outdoor economy rather than of tourism alone. Released once a year.`);
    Plotly.newPlot("corsa", [{ type: "bar", x: OR.rows.map(r => r.state), y: OR.rows.map(r => r.va_share), marker: { color: OR.rows.map(r => r.state === "North Dakota" ? css("--s1") : css("--gray-mark")) },
      text: OR.rows.map(r => r.va_share.toFixed(1) + "%"), textposition: "outside", textfont: { color: css("--ink-2") }, hovertemplate: "%{x}: %{y:.1f}% of GDP<extra></extra>" }],
      baseLayout({ showlegend: false, hovermode: "closest", bargap: 0.35, yaxis: { ticksuffix: "%", gridcolor: css("--grid"), zeroline: false, tickfont: { color: css("--muted") }, rangemode: "tozero", range: [0, Math.max(...OR.rows.map(r => r.va_share)) * 1.2] } }), PCONF);
    table("corsa", ["State", "Value added", "Share of GDP", "Rank", "Jobs", "Share of jobs", "Value added growth"], OR.rows.map(r => [r.state, moneyShort(r.value_added_k * 1000), pct1(r.va_share), r.rank ?? "–", r.employment, pct1(r.emp_share), pctTxt(r.va_growth)]));
  }

  // ---- Gateway county jobs across state lines
  const GJ = d.gateway_jobs;
  if (GJ && GJ.rows && GJ.rows.length) {
    group("Gateway counties", "Leisure and hospitality jobs in the counties along the routes into Medora, on both sides of the state lines.");
    card("cgj", `Leisure & hospitality jobs, ${GJ.year} Q${GJ.quarter} vs a year earlier`,
      `BLS QCEW, the same series as the Billings County chart in the Local Economy section, for the North Dakota corridor counties and their Montana and South Dakota neighbors: Wibaux, Dawson (Glendive), Fallon (Baker) and Custer (Miles City) in Montana; Harding (Buffalo), Butte (Belle Fourche) and Lawrence (Spearfish–Deadwood) in South Dakota. If Billings County grows faster than the counties across the line, that's local, not regional. Counties whose figures are withheld for confidentiality are not shown.`);
    const rk = changeBars("cgj", GJ.rows.map(r => ({ label: r.county + (r.state === "ND" ? "" : ""), pct: r.pct, cur: r.cur, prev: r.prev, hi: r.county === "Billings" })), { left: 120 });
    table("cgj", ["County", "State", String(GJ.year), String(GJ.year - 1), "Change"], GJ.rows.map(r => [r.county, r.state, r.cur, r.prev, pctTxt(r.pct)]));
  }
};

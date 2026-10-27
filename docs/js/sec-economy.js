// The local economy: Medora and corridor taxes, county sales, visitor spending studies, jobs.
SECTIONS.economy = function (X) {
  const { d, cur, prev } = X;

  group("Medora and the corridor towns", "What the State Treasurer pays each town from its own taxes: the only public money series at the town level.");
  if (d.nd_city && d.nd_city.cities && d.nd_city.cities.Medora) {
    const nc = d.nd_city, ycur = nc.current_year, lm = nc.latest_month, med = nc.cities.Medora;
    const lagNote = `Payments lag sales by about two months and quarterly filers land in the fall payments, so read year-to-date and same-month comparisons, not single months. Source: ND State Treasurer distribution search, payments through ${nc.latest_payment}.`;
    card("c5c", "Medora city sales tax, monthly payments to the city",
      `What the State Treasurer paid the City of Medora each month from its local sales tax, ${ycur} against ${ycur - 1} and the ${med.sales.band_years[0]}–${med.sales.band_years.at(-1)} range. ${lagNote}`);
    seasonalChart("c5c", MON, med.sales, ycur, { periodName: "Payment month", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" }, openingIndex: 6 });
    if (med.occupancy) {
      card("c5d", "Medora occupancy (lodging) tax, monthly payments to the city",
        `City/County Occupancy tax distributed to Medora: the lodging read. ${ycur} against ${ycur - 1} and the ${med.occupancy.band_years[0]}–${med.occupancy.band_years.at(-1)} range. ${lagNote}`);
      seasonalChart("c5d", MON, med.occupancy, ycur, { periodName: "Payment month", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" }, openingIndex: 6 });
    }
    card("c5e", `Corridor towns: city sales tax paid, Jan–${MON[lm - 1]} ${ycur} vs ${ycur - 1}`,
      `Year-to-date change in city sales tax distributions for the towns on the routes into Medora. Medora highlighted. Dickinson and Watford City are large oil-and-retail economies, so their swings are mostly not tourism. Occupancy and lodging & restaurant tax changes are in the table.`);
    const rk = changeBars("c5e", nc.ytd.map(r => ({ label: `${r.city} (${r.county} Co.)`, pct: r.sales_ytd_pct, curTxt: money(r.sales_ytd_cur), prevTxt: money(r.sales_ytd_prev), hi: r.city === "Medora", r })), { left: 200 });
    table("c5e", ["Town", `Sales tax YTD ${ycur}`, `YTD ${ycur - 1}`, "Change", `Occupancy YTD ${ycur}`, `YTD ${ycur - 1}`, "Change", `Lodging & restaurant YTD ${ycur}`, `YTD ${ycur - 1}`, "Change"],
      rk.slice().reverse().map(({ r }) => [`${r.city} (${r.county})`, money(r.sales_ytd_cur), money(r.sales_ytd_prev), pctTxt(r.sales_ytd_pct), money(r.occupancy_ytd_cur), money(r.occupancy_ytd_prev), pctTxt(r.occupancy_ytd_pct), r.lodging_restaurant_ytd_cur != null ? money(r.lodging_restaurant_ytd_cur) : "–", r.lodging_restaurant_ytd_prev != null ? money(r.lodging_restaurant_ytd_prev) : "–", r.lodging_restaurant_ytd_pct != null ? pctTxt(r.lodging_restaurant_ytd_pct) : "–"]));
    const dik = nc.cities.Dickinson;
    if (dik && dik.lodging_restaurant) {
      card("c5h", "Dickinson lodging & restaurant tax, monthly payments to the city",
        `Dickinson's 1% city lodging-and-restaurant tax: the closest thing to a monthly restaurant-demand series for the Library's nearest full-service town (35 miles east). ${ycur} against ${ycur - 1} and the ${dik.lodging_restaurant.band_years[0]}–${dik.lodging_restaurant.band_years.at(-1)} range. Medora levies no such tax. ${lagNote}`);
      seasonalChart("c5h", MON, dik.lodging_restaurant, ycur, { periodName: "Payment month", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" }, openingIndex: 6 });
    }
  }

  group("County sales", "Quarterly taxable sales from the Tax Commissioner. Billings County is mostly Medora commerce.");
  if (d.nd_tax && d.nd_tax.counties && d.nd_tax.counties.Billings) {
    const b = d.nd_tax.counties.Billings;
    card("c5", "Billings County taxable sales and purchases, by quarter",
      `Reported to the ND Tax Commissioner. Billings County is mostly Medora commerce, so this is the closest public proxy for visitor spending in town. ${cur} against ${prev} and the ${b.band_years[0]}–${b.band_years.at(-1)} range. Q3 (Jul–Sep) is the first post-opening quarter and posts in December. Through ${d.nd_tax.latest_quarter}.`);
    seasonalChart("c5", QTR, b, cur, { periodName: "Quarter", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" }, openingIndex: 2 });
  }
  if (d.nd_counties && d.nd_counties.ytd && d.nd_counties.ytd.length) {
    const C = d.nd_counties, cy = C.current_year;
    card("c5f", `Corridor counties: taxable sales and purchases, Q1–Q${C.latest_quarter} ${cy} vs ${cy - 1}`,
      `Year-to-date change by county from the Tax Commissioner's quarterly workbook. Billings highlighted. McKenzie, Dunn, and Bowman are oil counties, so their moves track rig activity more than visitors (see the controls in the last section). Q3 — the first full post-opening quarter — posts in December.`);
    const rk = changeBars("c5f", C.ytd.map(r => ({ label: r.county, pct: r.pct, curTxt: money(r.cur), prevTxt: money(r.prev), hi: r.county === "Billings", r })), { left: 120 });
    table("c5f", ["County", `YTD ${cy}`, `YTD ${cy - 1}`, "Change"], rk.slice().reverse().map(({ r }) => [r.county, money(r.cur), money(r.prev), pctTxt(r.pct)]));
    if (d.nd_tax.counties.Stark) {
      card("c5g", "Stark County (Dickinson) taxable sales and purchases, by quarter",
        `The corridor's largest economy and the Library's nearest full-service town. ${cur} against ${prev} and the ${d.nd_tax.counties.Stark.band_years[0]}–${d.nd_tax.counties.Stark.band_years.at(-1)} range.`);
      seasonalChart("c5g", QTR, d.nd_tax.counties.Stark, cur, { periodName: "Quarter", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" }, openingIndex: 2 });
    }
  }
  if (d.nd_tax && d.nd_tax.industries && d.nd_tax.industries["Accommodation & Food Services"]) {
    const a = d.nd_tax.industries["Accommodation & Food Services"];
    card("c5b", "North Dakota accommodation and food services taxable sales, statewide by quarter",
      `The tourism-facing sector line from the same Tax Commissioner workbook. Statewide only: the Commissioner does not publish county × industry, so this is the state trend the Billings County total sits inside. ${cur} against ${prev} and the ${a.band_years[0]}–${a.band_years.at(-1)} range.`);
    seasonalChart("c5b", QTR, a, cur, { periodName: "Quarter", hover: "$%{y:,.0f}", fmt: money, yaxis: { tickprefix: "$" } });
  }

  group("Visitor spending studies", "Annual modelled estimates. The Library's first season lands in next year's editions.");
  if (d.nd_impact && d.nd_impact.spending && d.nd_impact.spending.Billings) {
    const I = d.nd_impact, cnames = Object.keys(I.spending).filter(c => c !== "North Dakota");
    const base = c => { const i = I.years.indexOf(2021); return I.spending[c][i] || I.spending[c].find(v => v != null); };
    card("c7b", `North Dakota corridor counties: visitor spending, ${I.years[0]}–${I.latest_year}`,
      `Annual visitor spending by county from Tourism Economics' study for ND Commerce, indexed to 2021 = 100 so counties of different size share one axis (Stark is ~5× Billings). Billings County is Medora. The Library's first season lands in the ${I.latest_year + 1} edition. Dollar values and tourism-jobs share in the table. Statewide ${I.latest_year}: $${(I.spending["North Dakota"].at(-1) / 1000).toFixed(2)}B.`);
    Plotly.newPlot("c7b", cnames.map((n, i) => ({
      x: I.years, y: I.spending[n].map(v => v != null ? v / base(n) * 100 : null), mode: "lines+markers", name: n,
      line: { color: css(SLOT[i % SLOT.length]), width: n === "Billings" ? 3 : 2 }, marker: { size: 6, line: { color: css("--surface"), width: 2 } },
      customdata: I.spending[n], hovertemplate: "%{y:.1f} ($%{customdata:.1f}M)",
    })), baseLayout({ yaxis: { gridcolor: css("--grid"), zeroline: false, tickfont: { color: css("--muted") } }, xaxis: { dtick: 1, gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") } } }), PCONF);
    table("c7b", ["County", ...I.years.map(y => y + " ($M)"), `Tourism jobs ${I.latest_year}`, "Share of county jobs"], Object.keys(I.spending).map(c => [c, ...I.spending[c].map(v => v != null ? v.toFixed(1) : "–"), I.jobs[c] ? fmt(I.jobs[c].total_jobs) : "–", I.jobs[c] ? I.jobs[c].share_of_county_employment_pct.toFixed(1) + "%" : "–"]));
  }
  if (d.nd_impact && d.nd_impact.sectors && d.nd_impact.sectors.Billings) {
    const SB = d.nd_impact.sectors.Billings, SN = d.nd_impact.sectors["North Dakota"];
    const secs = [["lodging", "Lodging", "--s1"], ["food_beverage", "Food & beverage", "--s3"], ["retail", "Retail", "--s4"], ["recreation", "Recreation", "--s5"], ["transport", "Transport", "--s7"]];
    const ly = SB.years.at(-1), li = SB.years.length - 1;
    card("c7b2", `Billings County visitor spending by sector, ${SB.years[0]}–${ly}`,
      `Tourism Economics' county tables for ND Commerce, in millions: what visitors to Billings County spend on lodging, food and drink, retail, recreation and getting around. ${ly}: $${SB.total[li].toFixed(1)}M, of which lodging $${SB.lodging[li].toFixed(1)}M and food & beverage $${SB.food_beverage[li].toFixed(1)}M${SB.tax_revenue_musd[li] != null ? `; $${SB.tax_revenue_musd[li].toFixed(1)}M in state and local tax revenue` : ""}. The Library's first season lands in the ${ly + 1} tables. Statewide and growth rates in the table.`);
    Plotly.newPlot("c7b2", secs.map(([k, name, col]) => ({ type: "bar", name, x: SB.years, y: SB[k], marker: { color: css(col) }, hovertemplate: name + ": $%{y:.1f}M<extra></extra>" })),
      baseLayout({ barmode: "stack", bargap: 0.35, hovermode: "x unified", yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, tickprefix: "$", ticksuffix: "M" }, xaxis: { dtick: 1, gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") } } }), PCONF);
    const m1 = v => v == null ? "–" : "$" + v.toFixed(1) + "M";
    table("c7b2", ["Year", "Lodging", "Food & bev.", "Retail", "Recreation", "Transport", "Total", "Growth", "State & local tax", "ND total", "ND growth"],
      SB.years.map((y, i) => { const j = SN ? SN.years.indexOf(y) : -1; return [y, m1(SB.lodging[i]), m1(SB.food_beverage[i]), m1(SB.retail[i]), m1(SB.recreation[i]), m1(SB.transport[i]), m1(SB.total[i]), pctTxt(SB.growth_pct[i]), m1(SB.tax_revenue_musd[i]), j >= 0 ? "$" + (SN.total[j] / 1000).toFixed(2) + "B" : "–", j >= 0 ? pctTxt(SN.growth_pct[j]) : "–"]; }).reverse());
  }

  group("Jobs", "Tourism-sector jobs in Billings County, with the fast monthly labor read and the statewide benchmark. The Montana and South Dakota gateway counties are compared in the Region section.");
  if (d.qcew && d.qcew.counties && d.qcew.counties.Billings) {
    const Q = d.qcew, qy = Q.current_year;
    card("c11", "Billings County leisure and hospitality jobs, by quarter",
      `Average monthly employment in leisure and hospitality (hotels, restaurants, recreation) from BLS QCEW. This is the county-level tourism-sector series the tax data cannot give: about a five-month lag, through ${qy} Q${Q.latest_quarter}. ${qy} against ${qy - 1} and the ${Q.counties.Billings.band_years[0]}–${Q.counties.Billings.band_years.at(-1)} range. Other counties in the table.`);
    seasonalChart("c11", QTR, Q.counties.Billings, qy, Object.assign({ periodName: "Quarter", hover: "%{y:,.0f} jobs" }, qy === cur ? { openingIndex: 2 } : {}));
    appendTable("c11", `Latest quarter (${qy} Q${Q.latest_quarter}) by county`, ["County", String(qy), String(qy - 1), "Change"], Q.latest.slice().sort((a, b) => b.pct - a.pct).map(r => [r.county, r.cur, r.prev, pctTxt(r.pct)]));
  }
  if (d.laus && d.laus.counties && d.laus.counties.Billings) {
    const Lu = d.laus, ly = Lu.current_year, llm = Lu.latest_month;
    card("c11b", "Billings County residents employed, monthly",
      `BLS Local Area Unemployment Statistics: employed residents of Billings County by month, about a one-month lag (through ${MON[llm - 1]} ${ly}; the latest month is preliminary). It is all industries and counts people, not jobs, so it moves with the summer hiring season rather than with any one sector — the fast companion to the quarterly tourism-jobs chart above. ${ly} against ${ly - 1} and the ${Lu.counties.Billings.band_years[0]}–${Lu.counties.Billings.band_years.at(-1)} range. Other counties, including the Montana and South Dakota gateway counties, in the table.`);
    seasonalChart("c11b", MON, Lu.counties.Billings, ly, Object.assign({ periodName: "Month", hover: "%{y:,.0f} employed" }, ly === cur ? { openingIndex: 6 } : {}));
    appendTable("c11b", `${MON[llm - 1]} ${ly} by county`, ["County", `Employed ${ly}`, String(ly - 1), "Change", "Unemployment rate"], Lu.latest.slice().sort((a, b) => b.pct - a.pct).map(r => [r.county, r.cur, r.prev, pctTxt(r.pct), r.unemployment_rate.toFixed(1) + "%"]));
  }
  if (d.ces && d.ces.series && d.ces.series["North Dakota — Leisure & hospitality"]) {
    const C = d.ces, cy = C.current_year, key = "North Dakota — Leisure & hospitality", s = C.series[key];
    card("c11c", "North Dakota leisure & hospitality payroll jobs, monthly (thousands)",
      `Statewide payroll employment in leisure and hospitality from BLS Current Employment Statistics, not seasonally adjusted, through ${MON[C.latest_month - 1]} ${cy} (latest month preliminary). The benchmark for the Billings County series above: if the county outruns the state, that is local. ${cy} against ${cy - 1} and the ${s.band_years[0]}–${s.band_years.at(-1)} range. Bismarck MSA and the accommodation / food-service splits are in the table.`);
    seasonalChart("c11c", MON, s, cy, Object.assign({ periodName: "Month", hover: "%{y:.1f}k", fmt: v => v == null ? "–" : v.toFixed(1) + "k" }, cy === cur ? { openingIndex: 6 } : {}));
    const others = Object.keys(C.series).filter(k => k !== key);
    appendTable("c11c", `${MON[C.latest_month - 1]} ${cy} vs ${MON[C.latest_month - 1]} ${cy - 1}, thousands of jobs`, ["Series", String(cy - 1), String(cy), "Change"], others.map(k => { const a = C.series[k].years[String(cy)]?.[C.latest_month - 1], b = C.series[k].years[String(cy - 1)]?.[C.latest_month - 1]; return [k, b != null ? b.toFixed(1) : "–", a != null ? a.toFixed(1) : "–", a != null && b ? pctTxt((a - b) / b * 100) : "–"]; }));
  }
};

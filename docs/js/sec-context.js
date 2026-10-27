// Demand and context: search and Wikipedia interest, smoke, retail, controls. Then the Sources section.
SECTIONS.context = function (X) {
  const { d, cur } = X;

  group("Interest", "Leading indicators: people look before they go.");
  if (d.interest && d.interest.wiki && d.interest.wiki.articles["Theodore_Roosevelt_Presidential_Library"]) {
    const W = d.interest.wiki, wy = W.current_year, wa = W.articles["Theodore_Roosevelt_Presidential_Library"];
    card("c13", "Wikipedia pageviews: Theodore Roosevelt Presidential Library article, monthly",
      `A public leading indicator of interest. ${wy} against ${wy - 1} and the ${wa.band_years[0]}–${wa.band_years.at(-1)} range. The current month is partial. Source: Wikimedia pageviews API.`);
    seasonalChart("c13", MON, wa, wy, { periodName: "Month", openingIndex: 6 });
    if (W.articles["Medora,_North_Dakota"]) {
      card("c13m", "Wikipedia pageviews: Medora, North Dakota article, monthly", `${wy} against ${wy - 1} and the historical range.`);
      seasonalChart("c13m", MON, W.articles["Medora,_North_Dakota"], wy, { periodName: "Month", openingIndex: 6 });
    }
  }
  if (d.interest && d.interest.trends && d.interest.trends.terms) {
    const T = d.interest.trends, names = Object.keys(T.terms);
    card("c14", "Google search interest, weekly (U.S.)",
      `Google Trends index (100 = the peak week across these terms). Unofficial endpoint; treat as directional. Top states for "${T.primary_term}" over the last 12 months are in the table.`);
    Plotly.newPlot("c14", names.map((n, i) => ({ x: T.terms[n].weeks, y: T.terms[n].interest, mode: "lines", name: n, line: { color: css(SLOT[i]), width: n === T.primary_term ? 2.5 : 1.5 }, hovertemplate: "%{y}" })),
      baseLayout({ yaxis: { gridcolor: css("--grid"), zeroline: false, tickfont: { color: css("--muted") }, rangemode: "tozero" }, legend: { orientation: "h", y: -0.22, x: 0 }, margin: { l: 40, r: 16, t: 8, b: 70 } }), PCONF);
    table("c14", ["State", "Interest"], T.by_state.map(r => [r.state, r.interest]));
  }

  group("Conditions", "The things that move visitation that aren't the Library. Read a month's park or tax number against these before crediting or blaming the Library.");
  if (d.air_quality && d.air_quality.summer && d.air_quality.summer.length) {
    const AQ = d.air_quality, yrs = AQ.summer.map(s => String(s.year));
    card("c15", "Smoke days at Theodore Roosevelt NP, June–September",
      `Days with an Air Quality Index of 101 or worse ("unhealthy for sensitive groups" and up) at the Painted Canyon Visitor Center monitor — nearly always wildfire smoke in summer. The one weather-type variable that keeps people off Badlands trails. EPA AQS validated data where processed, AirNow preliminary daily values after that (through ${AQ.latest}). Monthly counts in the table.`);
    Plotly.newPlot("c15", [{ type: "bar", x: yrs, y: AQ.summer.map(s => s.usg_days), marker: { color: yrs.map(y => +y === cur ? css("--s1") : css("--gray-mark")) }, text: AQ.summer.map(s => s.usg_days), textposition: "outside", textfont: { color: css("--ink-2") }, customdata: AQ.summer.map(s => [s.max_aqi, s.moderate_days]), hovertemplate: "%{x}: %{y} smoke days<br>peak AQI %{customdata[0]}, %{customdata[1]} days moderate or worse<extra></extra>" }],
      baseLayout({ bargap: 0.35, hovermode: "closest", showlegend: false, yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, rangemode: "tozero", range: [0, Math.max(...AQ.summer.map(s => s.usg_days)) * 1.25 + 1] } }), PCONF);
    const my = Object.keys(AQ.monthly);
    table("c15", ["Month", ...my], MON.map((m, i) => [m, ...my.map(y => AQ.monthly[y][i] == null ? "–" : AQ.monthly[y][i])]));
  }
  if (d.msrs && d.msrs.rows && d.msrs.rows.length) {
    const M = d.msrs;
    const nd = M.rows.filter(r => r.state === "ND"), us = M.rows.filter(r => r.state === "USA");
    const periods = nd.length ? nd[0].periods : [];
    const row = (r, label) => `<tr><td>${label}</td>${r.yoy.map(v => `<td class="${v >= 0 ? "up" : "down"}">${pctTxt(v)}</td>`).join("")}</tr>`;
    box("cmsrs", "North Dakota retail sales, year-over-year change by month",
      `<p class="note">Census Bureau Monthly State Retail Sales (experimental), through ${MON[M.latest_month - 1]} ${M.current_year}; growth rates only, no dollar levels. A statewide check on whether the corridor's sales-tax gains are local or just North Dakota's retail cycle. Gasoline stations move with pump prices. U.S. total shown for comparison.</p>
      <div class="scroll"><table><thead><tr><th>Sector</th>${periods.map(p => `<th>${MON[+p.slice(5) - 1]} ${p.slice(2, 4)}</th>`).join("")}</tr></thead><tbody>${nd.map(r => row(r, "ND — " + r.sector)).join("")}${us.filter(r => r.sector === "Total retail").map(r => row(r, "U.S. — Total retail")).join("")}</tbody></table></div>`);
  }
  if (d.controls && d.controls.years) {
    const K = d.controls, ky = K.current_year, Y = K.years;
    const labels = { rain_days: "Rain days (≥0.10 in)", tmax_mean_f: "Mean high °F", hot_days_90f: "Days ≥ 90°F", gas_midwest_usd: "Midwest gas $/gal", cad_per_usd: "CAD per USD", nd_oil_bbl_per_day: "ND oil bbl/day", nd_rig_count: "ND rig count" };
    const f = (c, v) => v == null ? "–" : (c === "cad_per_usd" ? v.toFixed(3) : c === "gas_midwest_usd" ? "$" + v.toFixed(2) : c === "nd_oil_bbl_per_day" ? fmt(v / 1000) + "k" : fmt(v));
    box("cctl", `Controls: weather, gas, exchange rate, oil — ${ky} vs ${ky - 1}`,
      `<p class="note">Weather is Dickinson (NOAA GHCN-Daily). Gas is EIA Midwest regular. CAD per USD from FRED. Oil from the ND Industrial Commission.</p>
      <div class="scroll"><table><thead><tr><th>Month</th>${K.columns.map(c => `<th>${labels[c] || c}<br><span style="font-weight:400">${ky - 1} / ${ky}</span></th>`).join("")}</tr></thead><tbody>
      ${MON.map((m, i) => `<tr><td>${m}</td>${K.columns.map(c => `<td>${f(c, Y[String(ky - 1)][c][i])} / <b>${f(c, Y[String(ky)][c][i])}</b></td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
  }
};

SECTIONS.sources = function (X) {
  const { d } = X, C = d.catalog || { feeds: [], sections: [] };
  const titles = Object.fromEntries(C.sections.map(s => [s.id, s.title]));
  const rows = C.feeds.map(f => {
    const m = MANIFEST[f.key];
    return `<tr><td>${f.name}<div class="sub2">${titles[f.section] || ""}</div></td><td>${f.url ? `<a href="${f.url}" rel="noopener">${f.source}</a>` : f.source}</td><td>${f.grain}</td><td>${f.lag}</td><td>${throughLabel(m) || "–"}<div class="sub2">${m ? "pulled " + fmtDate(m.fetched_at) : "not fetched yet"}</div></td><td><code>${f.script}</code></td></tr>`;
  }).join("");
  box("csrc", "Every feed on this page",
    `<p class="note">The page refreshes every morning; each feed updates on its own schedule, shown here and on each card. Raw CSVs for every feed are in <a href="https://github.com/Theodore-Roosevelt-Presidential-Library/TourismData/tree/main/data" rel="noopener">the repo’s data folder</a> and the full build is <a href="data/dashboard.json">dashboard.json</a>.</p>
    <div class="scroll"><table class="sources"><thead><tr><th>Feed</th><th>Source</th><th>Grain</th><th>Lag</th><th>Latest</th><th>Script</th></tr></thead><tbody>${rows}</tbody></table></div>
    ${C.not_scriptable && C.not_scriptable.length ? `<p class="note"><b>Looked for but not automated:</b> ${C.not_scriptable.map(n => `${n.name} (${n.why})`).join("; ")}.</p>` : ""}`);
};

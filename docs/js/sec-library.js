// The Library: attendance, origin, distance, feeder markets, reach per capita.
SECTIONS.library = function (X) {
  const { d } = X, L = d.library, G = d.origin_geo;

  if (L && L.daily_since_opening && L.daily_since_opening.dates.length) {
    const D = L.daily_since_opening;
    const srcNote = String(L.visitors_source).startsWith("checked_in") ? "Attendance = checked-in scans on admission tickets (General Admission, Flex, Walk-Up) from ACME's TicketAnalytics collection — the same definition as the Sell-Out Monitor, so the two sites agree apart from timing. Tickets sold run higher; the gap is no-shows and unscanned entries. Tour and program scans are listed separately in the table, not added to attendance." : `Attendance source in this snapshot: "${L.visitors_source}" — reconcile against the PE: Tickets Checked In report before quoting.`;
    card("c0", "Library attendance, daily since opening",
      `Bars = daily checked-in attendance, line = 7-day average. ${srcNote} Peak day: ${L.peak_day ? MON[+L.peak_day.date.slice(5, 7) - 1] + " " + +L.peak_day.date.slice(8) + " (" + fmt(L.peak_day.visitors) + ")" : "–"}. Capture rate by month is in the table.`);
    Plotly.newPlot("c0", [
      { x: D.dates, y: D.visitors, type: "bar", name: "Daily attendance", marker: { color: css("--band").replace("0.14", "0.55").replace("0.18", "0.6") }, hovertemplate: "%{y:,}" },
      { x: D.dates, y: D.ma7, mode: "lines", name: "7-day average", line: { color: css("--s1"), width: 2.5 }, hovertemplate: "%{y:,}" },
    ], baseLayout({ bargap: 0.15, xaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), tickfont: { color: css("--muted") }, tickformat: "%b %d" } }), PCONF);
    table("c0", ["Month", "Library attendance", "TRNP recreation visits", "Capture rate"], (L.capture || []).map(r => [MON[r.month - 1], r.library, r.trnp, r.capture_pct.toFixed(1) + "%"]));
    if (L.programs && L.programs.length) {
      appendTable("c0", "Tours and programs since opening (scans on non-admission events; most of these visitors also hold an admission ticket)", ["Event", "Tickets", "Checked in"], L.programs.map(r => [r.event, r.tickets, r.checked_in]));
    }
    if (L.origin && L.origin.rows.length) {
      box("corigin", `Where Library visitors come from (through ${L.origin.as_of})`,
        `<p class="note">${L.origin.basis}. ${L.origin.new_market_share != null ? `<b>${L.origin.new_market_share.toFixed(1)}%</b> of tickets came from outside North Dakota and the region (${(G && G.region_states || ["MN","SD","MT","WI","IA"]).join(", ")}) — the "new-market share" metric; Canada ${L.origin.canada_share.toFixed(1)}%.` : ""} Per-capita reach by state and the Canadian provinces are further down this section.</p>` +
        tableHtml(["State", "Share", "Visitors"], L.origin.rows.slice(0, 12).map(r => [r.state, r.share.toFixed(1) + "%", r.visitors])));
    }
  }

  if (G && G.monthly_tiers && G.monthly_tiers.length) {
    const T = G.monthly_tiers, reg = (G.region_states || []).join(", ");
    const mlab = m => MON[+m.slice(5) - 1] + " " + m.slice(0, 4), p1 = n => n == null ? "–" : n.toFixed(1) + "%";
    const tiers = [["nd_pct", "North Dakota", "--s1"], ["region_pct", `Region (${reg})`, "--s3"], ["us_pct", "Rest of U.S.", "--s4"], ["canada_pct", "Canada", "--s2"], ["other_intl_pct", "Other international", "--s5"]];
    card("cg0", "Where tickets come from, month by month",
      `Share of tickets by buyer ZIP each month since opening: North Dakota, the surrounding region (${reg} — the same grouping the Sell-Out Monitor uses), the rest of the U.S., and international. Shares are of tickets with a mappable ZIP (${G.tiers ? G.tiers.unknown.toLocaleString() : "–"} could not be placed). Since opening: ND ${G.tiers.nd_pct}%, region ${G.tiers.region_pct}%, rest of U.S. ${G.tiers.us_pct}%, international ${(G.tiers.canada_pct + G.tiers.other_intl_pct).toFixed(1)}%. The current month is partial.`);
    Plotly.newPlot("cg0", tiers.map(([k, name, col]) => ({
      type: "bar", name, x: T.map(r => mlab(r.month)), y: T.map(r => r[k]), marker: { color: css(col) },
      customdata: T.map(r => r[k.replace("_pct", "")]), hovertemplate: name + ": %{y:.1f}% (%{customdata:,} tickets)<extra></extra>",
    })), baseLayout({ barmode: "stack", bargap: 0.3, hovermode: "x unified", yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, ticksuffix: "%", range: [0, 100] } }), PCONF);
    table("cg0", ["Month", "Tickets", "North Dakota", "Region", "Rest of U.S.", "Canada", "Other intl."], T.map(r => [mlab(r.month), r.tickets, p1(r.nd_pct), p1(r.region_pct), p1(r.us_pct), p1(r.canada_pct), p1(r.other_intl_pct)]));
  }

  if (G && G.bands && G.bands.length) {
    const asOf = L && L.origin ? L.origin.as_of : d.latest_month_label;
    card("cg1", "How far Library visitors travel",
      `Tickets since opening by straight-line distance from Medora to the buyer's ZIP (through ${asOf}). Straight-line miles run about 15–20% under road miles, so the 0–50 band is roughly a one-hour drive and 300–600 is a full day. ${G.geocoded_share.toFixed(1)}% of ${fmt(G.total_tickets)} tickets had a mappable ZIP; the rest are Canadian postal codes, blanks, or typos.`);
    Plotly.newPlot("cg1", [{
      x: G.bands.map(b => b.band), y: G.bands.map(b => b.share), type: "bar", name: "Share of tickets",
      marker: { color: css("--s1") }, text: G.bands.map(b => b.share.toFixed(1) + "%"), textposition: "outside", textfont: { color: css("--ink-2") },
      customdata: G.bands.map(b => b.tickets), hovertemplate: "%{x}: %{y:.1f}% (%{customdata:,} tickets)<extra></extra>",
    }], baseLayout({ showlegend: false, bargap: 0.3, hovermode: "closest", yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, ticksuffix: "%", range: [0, Math.max(...G.bands.map(b => b.share)) * 1.18] } }), PCONF);
    table("cg1", ["Distance from Medora", "Tickets", "Share"], G.bands.map(b => [b.band, b.tickets, b.share.toFixed(1) + "%"]));

    if (G.points && G.points.lat && G.points.lat.length) {
      const hasFrames = G.monthly_points && G.monthly_points.length > 1;
      card("cg2", "Where tickets were bought, by ZIP",
        `Each bubble is a buyer ZIP, sized by tickets (top ${fmt(G.points.lat.length)} ZIPs shown for the whole period, top 1,200 per month). Hover for the place name. Canadian buyers are not on the map.${hasFrames ? " Drag the slider to step through the months; bubble sizes are scaled within each view, so compare where, not how many." : ""}`);
      const frames = [{ ...G.points, month: "all", title: "Since opening" }, ...(hasFrames ? G.monthly_points.map(f => ({ ...f, title: MON[+f.month.slice(5) - 1] + " " + f.month.slice(0, 4) })) : [])];
      const mapTraces = f => { const maxT = Math.max(...f.tickets); return [
        { type: "scattergeo", lat: f.lat, lon: f.lon, mode: "markers", name: "ZIP",
          text: f.label, customdata: f.tickets, hovertemplate: "%{text}<br>%{customdata:,} tickets<extra></extra>",
          marker: { size: f.tickets.map(t => 3 + 26 * Math.sqrt(t / maxT)), color: css("--s1"), opacity: 0.45, line: { width: 0 } } },
        { type: "scattergeo", lat: [G.medora.lat], lon: [G.medora.lon], mode: "markers", name: "Medora",
          hovertemplate: "Medora, ND<extra></extra>", marker: { size: 12, color: css("--s2"), symbol: "star", line: { width: 1, color: css("--surface") } } },
      ]; };
      const mapLayout = baseLayout({ showlegend: false, hovermode: "closest", margin: { l: 0, r: 0, t: 0, b: 0 }, height: 520,
        geo: { scope: "usa", bgcolor: css("--surface"), showland: true, landcolor: css("--grid"), showlakes: true, lakecolor: css("--surface"),
               subunitcolor: css("--axis"), countrycolor: css("--axis"), showcountries: false, showframe: false } });
      Plotly.newPlot("cg2", mapTraces(frames[0]), mapLayout, PCONF);
      if (hasFrames) {
        const plot = document.getElementById("cg2");
        const ctl = document.createElement("div");
        ctl.className = "slider";
        ctl.innerHTML = `<label>Period: <b id="cg2-lab">${frames[0].title}</b></label><input type="range" id="cg2-rng" min="0" max="${frames.length - 1}" value="0" step="1" aria-label="Month"><span class="ticks">${frames.map(f => `<span>${f.title.replace(" 20", " ’")}</span>`).join("")}</span>`;
        plot.insertAdjacentElement("afterend", ctl);
        ctl.querySelector("input").addEventListener("input", e => {
          const f = frames[+e.target.value];
          document.getElementById("cg2-lab").textContent = f.title + (f.month === "all" ? "" : ` — ${fmt(f.tickets.reduce((a, b) => a + b, 0))} mapped tickets`);
          Plotly.react("cg2", mapTraces(f), mapLayout, PCONF);
        });
      }
      table("cg2", ["Metro", "Tickets", "Share", "Miles from Medora"], (G.feeders || []).map(f => [f.metro, f.tickets, f.share.toFixed(1) + "%", f.miles]));
    }

    if (G.feeders && G.feeders.length) {
      box("cfeed", "Feeder markets",
        `<p class="note">Tickets since opening grouped by the buyer ZIP's county, mapped to its metro area. The right-hand column is straight-line distance from Medora. Metros outside the list are in the state table above; per-capita reach is in the next card.</p>` +
        tableHtml(["Metro", "Share", "Tickets", "Miles"], G.feeders.slice(0, 20).map(f => [f.metro, f.share.toFixed(1) + "%", f.tickets, f.miles])));
    }
  }

  // ---- Reach per capita and Canadian provinces
  const R = d.reach;
  if (R && R.states && R.states.rows.length) {
    const rows = R.states.rows.filter(r => r.tickets >= 25).slice(0, 15);
    card("cg3", "Reach: tickets per 100,000 residents",
      `Tickets since opening divided by each state's population (Census ${R.states.pop_year} estimates), so a small state close by and a big state far away can be compared fairly. States with fewer than 25 tickets are left off the chart. Feeder metros on the same basis, and Canadian buyers by province (from the first letter of the postal code), are in the table.`);
    Plotly.newPlot("cg3", [{ type: "bar", orientation: "h", y: rows.map(r => r.state).reverse(), x: rows.map(r => r.per_100k).reverse(),
      marker: { color: rows.map(r => r.state === "ND" ? css("--s1") : css("--gray-mark")).reverse() }, text: rows.map(r => r.per_100k.toFixed(0)).reverse(), textposition: "outside", textfont: { color: css("--ink-2") }, cliponaxis: false,
      customdata: rows.map(r => r.tickets).reverse(), hovertemplate: "%{y}: %{x:.1f} per 100k (%{customdata:,} tickets)<extra></extra>" }],
      baseLayout({ hovermode: "closest", showlegend: false, bargap: 0.3, margin: { l: 50, r: 50, t: 8, b: 40 }, height: 460, xaxis: { type: "log", gridcolor: css("--grid"), tickfont: { color: css("--muted") }, title: { text: "tickets per 100,000 residents (log scale)", font: { size: 11, color: css("--muted") } } } }), PCONF);
    table("cg3", ["State", "Tickets", "Population", "Per 100k"], R.states.rows.slice(0, 30).map(r => [r.state, r.tickets, r.population, r.per_100k.toFixed(1)]));
    if (R.metros && R.metros.length) appendTable("cg3", "Feeder metros, tickets per 100,000 residents (metros mapped to their counties)", ["Metro", "Tickets", "Population", "Per 100k", "Miles"], R.metros.map(r => [r.metro, r.tickets, r.population, r.per_100k.toFixed(1), r.miles]));
    if (R.provinces && R.provinces.rows.length) appendTable("cg3", `Canadian tickets by province since opening (${fmt(R.provinces.total)} tickets)`, ["Province", "Tickets", "Share"], R.provinces.rows.map(r => [r.province, r.tickets, pct1(r.share)]));
  }
};

// Shared helpers for the TRPL Visitor Trends page. Loaded first; section files (sec-*.js) register
// a render function in SECTIONS and main.js runs them in order.
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const QTR = ["Q1", "Q2", "Q3", "Q4"];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const fmt = (n) => n == null ? "–" : Math.round(n).toLocaleString("en-US");
const pctTxt = (p) => p == null ? "–" : (p > 0 ? "+" : "") + p.toFixed(1) + "%";
const pctSpan = (p) => p == null ? "–" : `<span class="${p >= 0 ? "up" : "down"}">${pctTxt(p)}</span>`;
const money = (n) => n == null ? "–" : "$" + Math.round(n).toLocaleString("en-US");
const moneyShort = (n) => n == null ? "–" : Math.abs(n) >= 1e9 ? "$" + (n / 1e9).toFixed(2) + "B" : Math.abs(n) >= 1e6 ? "$" + (n / 1e6).toFixed(1) + "M" : Math.abs(n) >= 1e4 ? "$" + Math.round(n / 1e3) + "k" : money(n);
const pct1 = (n) => n == null ? "–" : n.toFixed(1) + "%";
const SLOT = ["--s1","--s2","--s3","--s4","--s5","--s6","--s7","--s8"];
const PCONF = { displayModeBar: false, responsive: true };
const SECTIONS = {};   // id -> render(X)

function baseLayout(extra) {
  return Object.assign({
    paper_bgcolor: css("--surface"), plot_bgcolor: css("--surface"),
    font: { family: 'system-ui, -apple-system, "Segoe UI", sans-serif', size: 12.5, color: css("--ink-2") },
    margin: { l: 56, r: 16, t: 8, b: 44 }, hovermode: "x unified",
    hoverlabel: { bgcolor: css("--surface"), bordercolor: css("--axis"), font: { color: css("--ink") } },
    legend: { orientation: "h", y: -0.18, x: 0, font: { color: css("--ink-2") } },
    xaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") } },
    yaxis: { gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, tickformat: ",~s" },
  }, extra || {});
}

// ---- Catalog: which feed each card draws on, its cadence and lag
let MANIFEST = {}, FEEDS = {}, CARD_FEED = {};
function loadCatalog(d) {
  MANIFEST = d.manifest || {};
  for (const f of (d.catalog && d.catalog.feeds) || []) {
    FEEDS[f.key] = f;
    for (const c of f.cards || []) CARD_FEED[c] = f.key;
  }
}
const fmtDate = s => { if (!s) return null; const dt = new Date(s.length === 10 ? s + "T12:00:00" : s); return isNaN(dt) ? s : dt.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };
function throughLabel(m) {
  if (!m) return "";
  const through = m.checkins_last || m.latest || m.public_use_latest || m.latest_quarter || (typeof m.latest_month === "string" ? m.latest_month : m.latest_month && m.latest_month.THRO) || (m.latest_year && (m.latest_year.THRO || Object.values(m.latest_year)[0])) || m.monthly_latest || m.year || null;
  if (through == null) return "";
  const t = String(through);
  return /^\d{4}-\d{2}$/.test(t) ? `${MON[+t.slice(5) - 1]} ${t.slice(0, 4)}` : /^\d{4}-\d{2}-\d{2}$/.test(t) ? fmtDate(t) : t;
}
function freshness(key) {
  const m = MANIFEST[key], f = FEEDS[key];
  if (!m && !f) return "";
  const thr = throughLabel(m);
  const badge = f ? `<span class="badge">${f.grain}</span><span class="badge muted">Lag: ${f.lag.charAt(0).toLowerCase() + f.lag.slice(1)}</span>` : "";
  return `<p class="fresh">${badge}${m ? `Pulled ${fmtDate(m.fetched_at)}` : ""}${thr ? ` · latest ${thr}` : ""}</p>`;
}

// ---- Placement: cards go into the current section (S.sec), under the current group heading if any
const S = { sec: null };
function sectionEl() { return document.querySelector(`#sec-${S.sec} .cards`); }
function group(title, blurb) {
  const h = document.createElement("div");
  h.className = "group";
  h.innerHTML = `<h3>${title}</h3>${blurb ? `<p>${blurb}</p>` : ""}`;
  sectionEl().appendChild(h);
}
function card(id, title, note) {
  const el = document.createElement("article");
  el.className = "card";
  el.id = "card-" + id;
  el.innerHTML = `<div class="bar"><h2>${title}</h2><button class="toggle" data-for="${id}">Table</button></div>
    ${freshness(CARD_FEED[id])}<p class="note">${note}</p><div class="plot" id="${id}"></div><div class="tbl hidden" id="${id}-tbl"></div>`;
  sectionEl().appendChild(el);
  el.querySelector(".toggle").addEventListener("click", (e) => {
    const p = el.querySelector(".plot"), t = el.querySelector(".tbl");
    const showTbl = t.classList.contains("hidden");
    t.classList.toggle("hidden", !showTbl); p.classList.toggle("hidden", showTbl);
    e.target.textContent = showTbl ? "Chart" : "Table";
    if (!showTbl) Plotly.Plots.resize(p);
  });
  return el;
}
// A table-only card
function box(id, title, html) {
  const el = document.createElement("article");
  el.className = "card";
  el.id = "card-" + id;
  el.innerHTML = `<h2>${title}</h2>${freshness(CARD_FEED[id])}${html}`;
  sectionEl().appendChild(el);
  return el;
}
function table(id, head, rows) {
  document.getElementById(id + "-tbl").innerHTML = tableHtml(head, rows);
}
function tableHtml(head, rows) {
  return `<div class="scroll"><table><thead><tr>${head.map(h => `<th>${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(r => `<tr>${r.map((c, i) => `<td>${i ? (typeof c === "number" ? fmt(c) : (c ?? "–")) : c}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}
function appendTable(id, note, head, rows) {
  document.getElementById(id + "-tbl").innerHTML += `<p class="note">${note}</p>` + tableHtml(head, rows);
}

// ---- Shared chart: current year vs prior year vs historical band
function seasonalChart(id, xLabels, shaped, cur, opts) {
  opts = opts || {};
  const prev = cur - 1;
  const bandMin = shaped.band.map(b => b ? b.min : null), bandMax = shaped.band.map(b => b ? b.max : null);
  const yc = shaped.years[String(cur)] || [], yp = shaped.years[String(prev)] || [];
  const hover = opts.hover || "%{y:,}";
  const hasBand = shaped.band_years && shaped.band_years.length && bandMax.some(v => v != null);
  const traces = [
    ...(hasBand ? [
    { x: xLabels, y: bandMax, mode: "lines", line: { width: 0 }, hoverinfo: "skip", showlegend: false },
    { x: xLabels, y: bandMin, mode: "lines", line: { width: 0 }, fill: "tonexty", fillcolor: css("--band"), name: opts.bandName || `${shaped.band_years[0]}–${shaped.band_years.at(-1)} range`, hoverinfo: "skip" }] : []),
    { x: xLabels, y: yp, mode: "lines", name: String(prev), line: { color: css("--gray-mark"), width: 2 }, hovertemplate: hover },
    { x: xLabels, y: yc, mode: "lines+markers", name: String(cur), line: { color: css("--s1"), width: 2.5 }, marker: { size: 8, line: { color: css("--surface"), width: 2 } }, hovertemplate: hover },
  ];
  const layout = baseLayout({ yaxis: Object.assign({ gridcolor: css("--grid"), linecolor: css("--axis"), zeroline: false, tickfont: { color: css("--muted") }, tickformat: ",~s", rangemode: "tozero" }, opts.yaxis || {}) });
  if (opts.openingIndex != null) {
    layout.shapes = [{ type: "line", x0: opts.openingIndex, x1: opts.openingIndex, xref: "x", y0: 0, y1: 1, yref: "paper", line: { color: css("--axis"), width: 1 } }];
    layout.annotations = [{ x: opts.openingIndex, y: 1, xref: "x", yref: "paper", text: "Library opens", showarrow: false, xanchor: "left", yanchor: "top", xshift: 6, font: { size: 12, color: css("--muted") } }];
  }
  Plotly.newPlot(id, traces, layout, PCONF);
  const f = opts.fmt || fmt;
  table(id, [opts.periodName || "Period", String(prev), String(cur), "Change", "Range min", "Range max"], xLabels.map((l, i) => {
    const a = yc[i], b = yp[i];
    return [l, f(b), f(a), a != null && b ? pctTxt((a - b) / b * 100) : "–", f(bandMin[i]), f(bandMax[i])];
  }));
}

// ---- Shared chart: ranked horizontal bars of percent change, one item highlighted
function changeBars(id, items, opts) {
  opts = opts || {};
  const rk = items.filter(r => r.pct != null).sort((a, b) => a.pct - b.pct);
  Plotly.newPlot(id, [{
    type: "bar", orientation: "h", y: rk.map(r => r.label), x: rk.map(r => r.pct),
    marker: { color: rk.map(r => r.hi ? css("--s1") : css("--gray-mark")) },
    text: rk.map(r => pctTxt(r.pct)), textposition: "outside", textfont: { color: css("--ink-2") }, cliponaxis: false,
    customdata: rk.map(r => [r.curTxt ?? fmt(r.cur), r.prevTxt ?? fmt(r.prev)]), hovertemplate: "%{y}<br>%{x:+.1f}%<br>%{customdata[0]} vs %{customdata[1]}<extra></extra>",
  }], baseLayout({
    hovermode: "closest", margin: { l: opts.left || 160, r: 60, t: 8, b: 40 }, showlegend: false, bargap: 0.35, height: Math.max(220, 46 * rk.length + 80),
    xaxis: { ticksuffix: "%", gridcolor: css("--grid"), zeroline: true, zerolinecolor: css("--axis"), tickfont: { color: css("--muted") },
      range: [Math.min(0, ...rk.map(r => r.pct)) * 1.9 - 4, Math.max(0, ...rk.map(r => r.pct)) * 1.18 + 4] },
    yaxis: { tickfont: { color: css("--ink-2") }, automargin: true },
  }), PCONF);
  return rk;
}

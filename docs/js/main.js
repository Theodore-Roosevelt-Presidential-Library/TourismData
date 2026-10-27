// Loads dashboard.json, builds the header, the "what moved" strip and the section menu, then renders each section.
async function main() {
  const d = await (await fetch("data/dashboard.json")).json();
  loadCatalog(d);
  const thro = d.parks.find(p => p.code === "THRO");
  const anomalous = new Set(d.parks.filter(p => p.flag).map(p => p.code));
  const cleanControls = d.parks.filter(p => p.role === "control" && !anomalous.has(p.code));
  const ctrlPct = cleanControls.map(p => p.kpi.post_opening.pct).filter(v => v != null).sort((a, b) => a - b);
  const ctrlMedian = ctrlPct.length ? ctrlPct[Math.floor(ctrlPct.length / 2)] : null;
  const cur = d.current_year, prev = cur - 1, k = thro.kpi;
  const X = { d, thro, anomalous, cleanControls, ctrlMedian, cur, prev };

  // ---- Header
  const builtTxt = new Date(d.built_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
  const L = d.library;
  const libTxt = L && L.as_of ? `Library attendance through <b>${new Date(L.as_of + "T12:00:00").toLocaleDateString("en-US", { month: "short", day: "numeric" })}</b>` : "";
  document.getElementById("subtitle").innerHTML =
    `Visitation around the Library, which opened <b>July 4, ${cur}</b>, and across the region. Updated <b>${builtTxt}</b>${libTxt ? "; " + libTxt : ""}; National Park Service counts through <b>${d.latest_month_label}</b>. Every card shows how often its source updates and how far behind it runs.`;
  const capLatest = L && L.capture && L.capture.length ? L.capture.at(-1) : null;
  const tiles = [
    ...(L && L.since_opening ? [
      ["Library attendance since opening", fmt(L.since_opening.visitors), `${L.since_opening.days} days through ${L.as_of}`],
      ["Capture rate, " + (capLatest ? MON[capLatest.month - 1] : "–"), capLatest ? capLatest.capture_pct.toFixed(0) + "%" : "–", capLatest ? `Library ÷ TRNP visits (${fmt(capLatest.library)} ÷ ${fmt(capLatest.trnp)})` : "needs NPS month"],
    ] : []),
    ["TRNP, " + MON[k.latest.month - 1] + " " + cur, fmt(k.latest.cur), `${pctSpan(k.latest.prev ? (k.latest.cur - k.latest.prev) / k.latest.prev * 100 : null)} vs ${MON[k.latest.month - 1]} ${prev}`],
    ["TRNP since opening (Jul–" + MON[k.post_opening.months.at(-1) - 1] + ")", fmt(k.post_opening.cur), `${pctSpan(k.post_opening.pct)} vs same months ${prev}`],
    ["TRNP year to date", fmt(k.ytd.cur), `${pctSpan(k.ytd.pct)} vs Jan–${MON[k.ytd.months.at(-1) - 1]} ${prev}`],
    ["Control parks, same months", pctTxt(ctrlMedian), `median of ${cleanControls.length} regional parks vs ${prev}`],
  ];
  document.getElementById("tiles").innerHTML = tiles.map(([kk, v, dd]) => `<div class="tile"><div class="k">${kk}</div><div class="v">${v}</div><div class="d">${dd}</div></div>`).join("");

  // ---- What moved: newest reading of each headline series
  if (d.movers && d.movers.length) {
    const titles = Object.fromEntries((d.catalog.sections || []).map(s => [s.id, s.title]));
    document.getElementById("movers").innerHTML = `<h2>What moved</h2><p class="note">The newest reading of each headline series against the same period a year earlier, most recent first.</p><ul>${d.movers.map(m =>
      `<li><a href="#sec-${m.section}"><span class="mv-pct ${m.pct >= 0 ? "up" : "down"}">${pctTxt(m.pct)}</span><span class="mv-label">${m.label}</span><span class="mv-meta">${m.unit === "$" ? moneyShort(m.value) : fmt(m.value)} · ${m.period} · ${titles[m.section] || ""}</span></a></li>`).join("")}</ul>`;
  }

  // ---- Sections and menu
  const secs = (d.catalog && d.catalog.sections) || [];
  document.getElementById("nav").innerHTML = secs.map(s => `<a href="#sec-${s.id}" data-sec="${s.id}">${s.title}</a>`).join("");
  const main = document.getElementById("main");
  for (const s of secs) {
    const el = document.createElement("section");
    el.className = "sec"; el.id = "sec-" + s.id;
    el.innerHTML = `<header class="sec-head"><h2>${s.title}</h2><p>${s.blurb}</p></header><div class="cards"></div>`;
    main.appendChild(el);
  }
  for (const s of secs) {
    if (!SECTIONS[s.id]) continue;
    S.sec = s.id;
    try { SECTIONS[s.id](X); } catch (e) { console.error(`section ${s.id}:`, e); sectionEl().insertAdjacentHTML("beforeend", `<p class="note">This section could not be drawn: ${e.message}</p>`); }
  }

  // Highlight the menu item for the section in view
  const links = [...document.querySelectorAll("#nav a")];
  const io = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) links.forEach(a => a.classList.toggle("on", a.dataset.sec === e.target.id.slice(4))); }), { rootMargin: "-45% 0px -50% 0px" });
  document.querySelectorAll("section.sec").forEach(s => io.observe(s));
  if (location.hash) document.querySelector(location.hash)?.scrollIntoView();

  document.getElementById("footer").innerHTML = `Built ${d.built_at.replace("T", " ").slice(0, 16)} UTC from ${Object.keys(FEEDS).length} feeds (see Sources). NPS monthly counts are preliminary until the annual close. Theodore Roosevelt Presidential Library.`;
}
main().catch(e => { document.getElementById("subtitle").textContent = "Could not load data: " + e; console.error(e); });

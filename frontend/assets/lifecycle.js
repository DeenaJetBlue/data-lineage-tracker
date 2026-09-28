// Page 2: one table's file lifecycle. Every configured source is checked in
// parallel and its card fills in as soon as its own answer arrives.

import {
  api, fmtClock, h, icon, initChrome, metricParts, pill, renderValue, showDemoBanner, showFatal, STATUS,
} from "./common.js";

const tableName = new URLSearchParams(location.search).get("table");
const main = document.getElementById("main");
const entries = new Map(); // source key -> { source, el, result, pending, open, touched }
const stages = [];         // { cls, el, index }
let refreshButton;
let checkedLine;

const SEVERITY = ["failed", "error", "warning", "running", "success"];
const NUMERIC = new Set(["number", "compact", "bytes"]);

async function start() {
  initChrome();
  if (!tableName) {
    location.replace("index.html");
    return;
  }
  document.title = `${tableName} · File Lifecycle`;
  let config;
  try {
    config = await api(`/api/tables/${encodeURIComponent(tableName)}`);
  } catch (err) {
    showFatal(main, `Could not load ${tableName}`, err.message);
    return;
  }
  showDemoBanner(config.demo_mode);
  render(config);
  refreshAll();
}

// ---------- Layout ----------

function render(config) {
  refreshButton = h("button", { class: "btn", type: "button", onclick: refreshAll }, icon("refresh"), "Refresh all");
  checkedLine = h("p", { class: "title-meta", "aria-live": "polite" });

  const strip = h("nav", { class: "stages", "aria-label": "Lifecycle stages" });
  config.classes.forEach((cls, index) => {
    if (index) strip.append(h("span", { class: "stage-arrow", "aria-hidden": "true" }, icon("arrow-right")));
    const el = h("a", { class: "stage", href: `#stage-${index + 1}` });
    strip.append(el);
    stages.push({ cls, el, index });
  });

  main.replaceChildren(
    h("a", { class: "crumbs", href: `index.html?table=${encodeURIComponent(config.name)}` }, icon("arrow-left"), "All tables"),
    h("div", { class: "title-row" },
      h("div", null,
        h("p", { class: "eyebrow", text: "File lifecycle" }),
        h("h1", { text: config.name }),
        checkedLine),
      refreshButton),
    strip,
    ...config.classes.map(renderSection));
  update();
}

function renderSection(cls, index) {
  const cards = h("div", { class: "cards", "data-count": cls.sources.length });
  for (const source of cls.sources) {
    const el = h("article", { class: cls.sources.length === 1 ? "card card-wide" : "card", "aria-label": source.label });
    const entry = { source, el, result: null, pending: false, open: new Set(), touched: new Set() };
    entries.set(source.key, entry);
    cards.append(el);
    paint(entry);
  }
  const id = `stage-${index + 1}`;
  return h("section", { class: "class-section", id, "aria-labelledby": `${id}-title` },
    h("div", { class: "section-head" },
      h("h2", { id: `${id}-title` }, h("span", { class: "step", text: index + 1 }), cls.name),
      h("p", { text: cls.description })),
    cards);
}

// ---------- Checking ----------

function refreshAll() {
  for (const entry of entries.values()) {
    if (entry.source.configured) refreshOne(entry);
  }
}

async function refreshOne(entry) {
  if (entry.pending) return;
  entry.pending = true;
  paint(entry);
  update();
  try {
    entry.result = await api(`/api/tables/${encodeURIComponent(tableName)}/sources/${entry.source.key}`);
  } catch (err) {
    entry.result = {
      status: "error",
      status_label: "Couldn't check",
      summary: "The tracker's API did not answer.",
      error: err.message,
      config: entry.source.params,
      checked_at: new Date().toISOString(),
    };
  }
  entry.pending = false;
  paint(entry);
  update();
}

// ---------- Cards ----------

function paint(entry) {
  const { source, result, pending, el } = entry;
  if (!source.configured) {
    el.dataset.tone = "not_configured";
    el.replaceChildren(
      header(source, pill("Not configured", "not_configured")),
      h("div", { class: "card-content" },
        h("p", { class: "card-summary", text: `${tableName} has no ${source.name} rows in the config table.` })));
    return;
  }

  const checking = pending || !result;
  el.dataset.tone = result ? result.status : "checking"; // keep the last colour while refreshing
  el.classList.toggle("is-refreshing", pending && Boolean(result));
  el.setAttribute("aria-busy", String(checking));
  const label = checking ? STATUS.checking.label : result.status_label || STATUS[result.status]?.label;
  el.replaceChildren(
    header(source, pill(label, checking ? "checking" : result.status)),
    result ? content(entry) : skeleton(),
    footer(entry));
}

function header(source, statusPill) {
  return h("header", { class: "card-head" },
    h("div", null,
      h("h3", { class: "card-title", text: source.label }),
      h("p", { class: "card-sub", text: source.subtitle })),
    statusPill);
}

function content(entry) {
  const r = entry.result;
  const metrics = r.metrics || [];
  const details = r.details || [];
  return h("div", { class: "card-content" },
    r.summary ? h("p", { class: "card-summary", text: r.summary }) : null,
    r.error
      ? h("div", { class: "callout", role: "alert" },
          h("p", { text: r.error }),
          r.hint ? h("p", { class: "callout-hint", text: r.hint }) : null)
      : null,
    metrics.length ? h("div", { class: "metrics" }, metrics.map(metric)) : null,
    details.length
      ? h("dl", { class: "details" }, details.map((d) => [
          h("dt", { text: d.label }),
          h("dd", null, renderValue(d.value, d.format)),
        ]))
      : null,
    (r.tables || []).map((t) => drawer(entry, t.title, dataTable(t), t.open)),
    drawer(entry, "Configuration", configuration(entry)),
    r.raw != null ? drawer(entry, "Raw response", h("pre", { class: "raw", text: JSON.stringify(r.raw, null, 2) })) : null);
}

function metric(m) {
  const parts = metricParts(m);
  return h("div", { class: "metric" },
    h("span", { class: "metric-label", text: m.label }),
    h("span", { class: "metric-value", title: parts.title || null, text: parts.value }),
    parts.caption ? h("span", { class: "metric-caption", text: parts.caption }) : null);
}

// A collapsible section that stays open or closed across refreshes.
function drawer(entry, title, body, openByDefault = false) {
  const key = title.replace(/\s*\(.*\)$/, ""); // "Recent files (10)" -> "Recent files"
  const open = entry.touched.has(key) ? entry.open.has(key) : openByDefault;
  const el = h("details", { class: "drawer", open },
    h("summary", { text: title }),
    h("div", { class: "drawer-body" }, body));
  el.addEventListener("toggle", () => {
    // Creating an open <details> fires one toggle too; only a change from that state is the user's.
    if (!entry.touched.has(key) && el.open === open) return;
    entry.touched.add(key);
    if (el.open) entry.open.add(key);
    else entry.open.delete(key);
  });
  return el;
}

function dataTable(t) {
  if (!t.rows.length) return h("p", { class: "muted", text: "No rows." });
  const cellClass = (format) => (NUMERIC.has(format) ? "num" : ["pill", "datetime"].includes(format) ? "nowrap" : null);
  return h("div", { class: "table-wrap" },
    h("table", null,
      h("thead", null, h("tr", null, t.columns.map((c) => h("th", { class: cellClass(c.format), text: c.label })))),
      h("tbody", null, t.rows.map((row) => h("tr", null,
        t.columns.map((c) => h("td", { class: cellClass(c.format) }, renderValue(row[c.key], c.format, true))))))));
}

function configuration(entry) {
  const params = Object.entries(entry.result?.config || entry.source.params || {});
  return h("div", null,
    params.length
      ? h("dl", { class: "params" }, params.map(([key, value]) => [
          h("dt", { text: key }),
          h("dd", null, h("code", { text: value || "—" })),
        ]))
      : h("p", { class: "muted", text: "No parameters set - defaults apply." }),
    h("p", { class: "config-note", text: `Source "${entry.source.name}" in the config table · same calls as ${entry.source.test_script}` }));
}

function footer(entry) {
  const r = entry.result;
  let meta = "Checking…";
  if (r && !entry.pending) {
    meta = `Checked ${fmtClock(r.checked_at)}`;
    if (r.elapsed_ms != null) meta += ` · ${r.elapsed_ms < 1000 ? `${r.elapsed_ms} ms` : `${(r.elapsed_ms / 1000).toFixed(1)} s`}`;
    if (r.demo) meta += " · sample data";
  }
  return h("footer", { class: "card-foot" },
    h("span", { text: meta }),
    h("button", {
      class: "icon-btn",
      type: "button",
      title: `Refresh ${entry.source.label}`,
      "aria-label": `Refresh ${entry.source.label}`,
      disabled: entry.pending,
      onclick: () => refreshOne(entry),
    }, icon(entry.pending ? "spinner" : "refresh")));
}

function skeleton() {
  return h("div", { class: "card-content", "aria-hidden": "true" },
    h("span", { class: "skeleton skeleton-long" }),
    h("div", { class: "skeleton-metrics" }, h("span", { class: "skeleton" }), h("span", { class: "skeleton" }), h("span", { class: "skeleton" })),
    h("span", { class: "skeleton skeleton-short" }));
}

// ---------- Stage strip and page status ----------

function update() {
  const configured = [...entries.values()].filter((e) => e.source.configured);
  const waiting = configured.filter((e) => e.pending || !e.result).length;
  refreshButton.disabled = waiting > 0;
  if (waiting) {
    checkedLine.textContent = `Checking ${waiting} of ${configured.length} sources…`;
  } else {
    const latest = configured.map((e) => e.result.checked_at).sort().pop();
    checkedLine.textContent = latest
      ? `${configured.length} sources checked · last at ${fmtClock(latest)}`
      : "No sources configured for this table.";
  }
  for (const stage of stages) paintStage(stage);
}

function paintStage({ cls, el, index }) {
  const list = cls.sources.map((s) => entries.get(s.key)).filter((e) => e && e.source.configured);
  const { tone, label, line } = aggregate(list);
  el.dataset.tone = tone;
  el.setAttribute("aria-label", `${cls.name}: ${label}. ${line}`);
  el.replaceChildren(
    h("div", { class: "stage-top" },
      h("span", { class: "stage-name" }, h("span", { class: "step", text: index + 1 }), cls.name),
      pill(label, tone, true)),
    h("span", { class: "stage-line", text: line }));
}

function aggregate(list) {
  if (!list.length) return { tone: "not_configured", label: "Not configured", line: "No sources configured for this table." };
  const waiting = list.filter((e) => e.pending || !e.result).length;
  if (waiting) return { tone: "checking", label: STATUS.checking.label, line: `${list.length - waiting} of ${list.length} checked` };

  if (list.length === 1) {
    const r = list[0].result;
    return { tone: r.status, label: r.status_label || STATUS[r.status].label, line: r.error || r.summary };
  }
  const counts = {};
  for (const e of list) counts[e.result.status] = (counts[e.result.status] || 0) + 1;
  const worst = SEVERITY.find((s) => counts[s]) || "not_configured";
  const words = { success: "OK", running: "running", warning: "warning", failed: "failed", error: "couldn't check" };
  const line = SEVERITY.filter((s) => counts[s])
    .map((s) => `${counts[s]} ${words[s]}${s === "warning" && counts[s] > 1 ? "s" : ""}`)
    .join(" · ");
  return { tone: worst, label: worst === "success" ? "All healthy" : STATUS[worst].label, line };
}

start();

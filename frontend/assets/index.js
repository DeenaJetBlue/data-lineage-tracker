// Page 1: choose a table and preview its config-table entry, grouped by class.

import { api, h, initChrome, showDemoBanner, showFatal } from "./common.js";

const select = document.getElementById("table-select");
const trackLink = document.getElementById("track-link");
const preview = document.getElementById("config-preview");
let latestRequest = 0; // arrowing through the dropdown fires overlapping requests; only the last one may render

async function main() {
  initChrome();
  let data;
  try {
    data = await api("/api/tables");
  } catch (err) {
    showFatal(document.getElementById("main"), "Could not load the config table", err.message);
    return;
  }
  showDemoBanner(data.demo_mode);

  const count = data.tables.length;
  document.getElementById("table-count").textContent =
    `${count} table${count === 1 ? "" : "s"} in ${data.config_table}`;
  if (!count) {
    select.replaceChildren(h("option", { text: "No tables configured" }));
    preview.replaceChildren(h("p", { class: "muted", text: `Add rows to ${data.config_table} to get started.` }));
    return;
  }

  select.replaceChildren(...data.tables.map((t) => h("option", { value: t.name, text: t.name })));
  const requested = new URLSearchParams(location.search).get("table");
  if (data.tables.some((t) => t.name === requested)) select.value = requested;
  select.disabled = false;
  select.addEventListener("change", () => showTable(select.value));
  showTable(select.value);
}

async function showTable(name) {
  const request = ++latestRequest;
  trackLink.href = `lifecycle.html?table=${encodeURIComponent(name)}`;
  trackLink.removeAttribute("aria-disabled");
  history.replaceState(null, "", `?table=${encodeURIComponent(name)}`);
  preview.setAttribute("aria-busy", "true");
  let content;
  try {
    const table = await api(`/api/tables/${encodeURIComponent(name)}`);
    if (request !== latestRequest) return;
    document.getElementById("config-sub").textContent = `${table.name} · ${table.config_table}`;
    content = [renderClasses(table), renderRows(table)];
  } catch (err) {
    if (request !== latestRequest) return;
    content = [h("div", { class: "callout" }, h("p", { text: err.message }))];
  }
  preview.replaceChildren(...content);
  preview.removeAttribute("aria-busy");
}

function renderClasses(table) {
  return h("div", { class: "class-grid" }, table.classes.map((cls, index) =>
    h("section", { class: "class-col", "aria-label": cls.name },
      h("header", null,
        h("h3", null, h("span", { class: "step", text: index + 1 }), cls.name),
        h("p", { text: cls.description })),
      cls.sources.map(renderSource))));
}

function renderSource(source) {
  const params = Object.entries(source.params || {});
  return h("div", { class: source.configured ? "src" : "src src-off" },
    h("div", { class: "src-head" },
      h("span", { class: "src-name", text: source.label }),
      h("span", { class: "src-sub", text: source.configured ? source.subtitle : "Not configured" })),
    source.configured && params.length
      ? h("dl", { class: "params" }, params.map(([key, value]) => [
          h("dt", { text: key }),
          h("dd", null, h("code", { text: value || "—" })),
        ]))
      : null,
    source.configured && !params.length
      ? h("p", { class: "src-sub", text: "Uses defaults (no parameters set)" })
      : null);
}

// The same entry exactly as it appears in the CSV, for anyone editing the file.
function renderRows(table) {
  const columns = ["Class", "Source", "Parameter", "Value"];
  return h("details", { class: "drawer rows-drawer" },
    h("summary", { text: `Rows in ${table.config_table} (${table.rows.length})` }),
    h("div", { class: "drawer-body table-wrap" },
      h("table", null,
        h("thead", null, h("tr", null, h("th", { text: "Table_Name" }), columns.map((c) => h("th", { text: c })))),
        h("tbody", null, table.rows.map((row) => h("tr", null,
          h("td", null, h("code", { text: table.name })),
          h("td", { class: "nowrap", text: row.class }),
          h("td", { class: "nowrap", text: row.source }),
          h("td", null, h("code", { text: row.parameter })),
          h("td", null, h("code", { text: row.value || "—" }))))))));
}

main();

// Shared by both pages: API calls, a small element builder, value formatting,
// status pills and the page chrome (theme toggle, sample-data banner).
// Everything from the API is inserted as text - never as HTML.

export async function api(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  let body = null;
  try {
    body = await response.json();
  } catch {
    // not JSON (e.g. a proxy error page)
  }
  if (!response.ok) {
    const detail = body && body.detail ? body.detail : `${response.status} ${response.statusText}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return body;
}

export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value == null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "text") el.textContent = value;
    else if (key.startsWith("on")) el.addEventListener(key.slice(2), value);
    else el.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

// ---------- Icons (20x20 stroke glyphs) ----------

const ICONS = {
  check: ["M5.5 10.5l3 3 6-6.5"],
  x: ["M6.5 6.5l7 7", "M13.5 6.5l-7 7"],
  alert: ["M10 3.8l7 12.4H3z", "M10 8.6v3.2", "M10 14.3v.01"],
  error: ["M16.5 10a6.5 6.5 0 1 1-13 0a6.5 6.5 0 1 1 13 0z", "M10 6.8v3.8", "M10 13.3v.01"],
  clock: ["M16.5 10a6.5 6.5 0 1 1-13 0a6.5 6.5 0 1 1 13 0z", "M10 6.5V10l2.4 1.6"],
  minus: ["M6 10h8"],
  spinner: ["M10 3.5a6.5 6.5 0 1 1-6.5 6.5"],
  refresh: ["M15.8 8.2A6 6 0 0 0 4.9 6.4", "M4.5 3.3v3.4h3.4", "M4.2 11.8a6 6 0 0 0 10.9 1.8", "M15.5 16.7v-3.4h-3.4"],
  "arrow-left": ["M15.5 10h-11", "M9 5.5L4.5 10 9 14.5"],
  "arrow-right": ["M4.5 10h11", "M11 5.5l4.5 4.5-4.5 4.5"],
  external: ["M8.5 5H5v10h10v-3.5", "M11.5 4.5h4v4", "M15.5 4.5L9 11"],
  sun: ["M13.2 10a3.2 3.2 0 1 1-6.4 0a3.2 3.2 0 1 1 6.4 0z",
        "M10 2.8v1.4M10 15.8v1.4M2.8 10h1.4M15.8 10h1.4M4.9 4.9l1 1M14.1 14.1l1 1M4.9 15.1l1-1M14.1 5.9l1-1"],
  moon: ["M15.8 12.3A6.4 6.4 0 0 1 7.7 4.2a6.4 6.4 0 1 0 8.1 8.1z"],
};

export function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 20 20");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "currentColor");
  svg.setAttribute("stroke-width", "1.8");
  svg.setAttribute("stroke-linecap", "round");
  svg.setAttribute("stroke-linejoin", "round");
  svg.setAttribute("aria-hidden", "true");
  if (name === "spinner") svg.classList.add("spin");
  for (const d of ICONS[name] || []) {
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    svg.append(path);
  }
  return svg;
}

// ---------- Status ----------

export const STATUS = {
  success: { label: "Healthy", icon: "check" },
  running: { label: "Running", icon: "clock" },
  warning: { label: "Needs a look", icon: "alert" },
  failed: { label: "Failed", icon: "x" },
  error: { label: "Couldn't check", icon: "error" },
  not_configured: { label: "Not configured", icon: "minus" },
  checking: { label: "Checking…", icon: "spinner" },
};

export function pill(text, tone, small = false) {
  const meta = STATUS[tone] || STATUS.not_configured;
  return h("span", { class: small ? "pill pill-sm" : "pill", "data-tone": tone, title: meta.label },
    icon(meta.icon), h("span", { text: text || meta.label }));
}

// ---------- Formatting ----------

const numberFormat = new Intl.NumberFormat();
const compactFormat = new Intl.NumberFormat(undefined, { notation: "compact", maximumFractionDigits: 1 });
const relativeFormat = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
const HAS_ZONE = /([zZ]|[+-]\d{2}:?\d{2})$/;

export const fmtNumber = (value) => numberFormat.format(Number(value));
export const fmtCompact = (value) => compactFormat.format(Number(value));

export function fmtBytes(bytes) {
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = Number(bytes);
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return unit === 0 ? `${value} B` : `${value.toFixed(value < 10 ? 1 : 0)} ${units[unit]}`;
}

export function relativeTime(date) {
  const seconds = (date.getTime() - Date.now()) / 1000;
  if (Math.abs(seconds) < 45) return "just now";
  const steps = [["minute", 60], ["hour", 3600], ["day", 86400], ["month", 2629800], ["year", 31557600]];
  let [unit, size] = steps[0];
  for (const [name, length] of steps) if (Math.abs(seconds) >= length) [unit, size] = [name, length];
  return relativeFormat.format(Math.round(seconds / size), unit);
}

function shortDate(date, timeZone) {
  const opts = { month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone };
  const year = timeZone === "UTC" ? date.getUTCFullYear() : date.getFullYear();
  if (year !== new Date().getFullYear()) opts.year = "numeric";
  return date.toLocaleString(undefined, opts);
}

// Timestamps with a zone are shown in the viewer's local time plus "x ago".
// Timestamps without one (MOVEit reports server-local time) are shown as-is.
export function describeDate(value) {
  const text = String(value);
  if (HAS_ZONE.test(text)) {
    const date = new Date(text);
    if (Number.isNaN(date.getTime())) return { short: text, full: text };
    return {
      short: shortDate(date),
      full: date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "long" }),
      relative: relativeTime(date),
      iso: date.toISOString(),
    };
  }
  const m = text.match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})(?::(\d{2}))?/);
  if (!m) return { short: text, full: text };
  const date = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +(m[6] || 0)));
  return { short: shortDate(date, "UTC"), full: `${text} (server time - no time zone reported)`, naive: true };
}

function dateNode(value, compact) {
  const d = describeDate(value);
  if (compact) {
    const title = [d.full, d.relative].filter(Boolean).join(" · ");
    return h("time", { datetime: d.iso || null, title, text: d.short });
  }
  return h("span", null,
    h("time", { datetime: d.iso || null, title: d.full, text: d.short }),
    d.relative ? h("span", { class: "rel", text: ` · ${d.relative}` }) : null,
    d.naive ? h("span", { class: "rel", text: " · server time" }) : null);
}

function safeHref(href) {
  return /^https?:\/\//i.test(String(href || "")) ? href : null;
}

// `compact` (table cells): dates show just the time, with "x ago" in the tooltip.
export function renderValue(value, format, compact = false) {
  if (value == null || value === "") return h("span", { class: "muted", text: "—" });
  switch (format) {
    case "number":
      return document.createTextNode(fmtNumber(value));
    case "compact":
      return h("span", { title: fmtNumber(value), text: fmtCompact(value) });
    case "bytes":
      return h("span", { title: `${fmtNumber(value)} bytes`, text: fmtBytes(value) });
    case "datetime":
      return dateNode(value, compact);
    case "code":
      return h("code", { text: String(value) });
    case "pill":
      return pill(value.text, value.tone, true);
    case "link": {
      const href = safeHref(value.href);
      return href
        ? h("a", { class: "ext-link", href, target: "_blank", rel: "noopener noreferrer" }, value.text, icon("external"))
        : document.createTextNode(value.text || "");
    }
    case "json":
      if (typeof value !== "object") return h("code", { text: String(value) });
      return h("details", { class: "json" },
        h("summary", { text: Array.isArray(value) ? `JSON · ${value.length} items` : `JSON · ${Object.keys(value).length} keys` }),
        h("pre", { text: JSON.stringify(value, null, 2) }));
    default:
      return document.createTextNode(String(value));
  }
}

// The text of a stat tile: dates read as "3 hours ago" with the time underneath.
export function metricParts(metric) {
  const { value, format } = metric;
  if (format === "datetime") {
    const d = describeDate(value);
    if (d.relative) return { value: d.relative, caption: d.short, title: d.full };
    return { value: d.short, caption: d.naive ? "server time" : null, title: d.full };
  }
  if (format === "number") return { value: fmtNumber(value) };
  if (format === "compact") return { value: fmtCompact(value), title: fmtNumber(value) };
  if (format === "bytes") return { value: fmtBytes(value), title: `${fmtNumber(value)} bytes` };
  return { value: String(value) };
}

export function fmtClock(iso) {
  return new Date(iso).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit", second: "2-digit" });
}

// ---------- Page chrome ----------

const THEME_KEY = "lineage-theme";

function storedTheme() {
  try {
    return localStorage.getItem(THEME_KEY);
  } catch {
    return null;
  }
}

export function initChrome() {
  const root = document.documentElement;
  const saved = storedTheme();
  if (saved === "light" || saved === "dark") root.dataset.theme = saved;

  const button = document.querySelector(".theme-toggle");
  if (!button) return;
  const isDark = () => (root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light")) === "dark";
  const paint = () => {
    button.replaceChildren(icon(isDark() ? "sun" : "moon"));
    button.setAttribute("aria-label", isDark() ? "Switch to light theme" : "Switch to dark theme");
    button.title = button.getAttribute("aria-label");
  };
  button.addEventListener("click", () => {
    root.dataset.theme = isDark() ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, root.dataset.theme);
    } catch {
      // storage unavailable (private window): the choice lasts for this page only
    }
    paint();
  });
  paint();
}

export function showDemoBanner(demo) {
  const banner = document.querySelector(".demo-banner");
  if (!banner || !demo) return;
  banner.replaceChildren(
    icon("alert"),
    h("span", null,
      h("strong", { text: "Sample data. " }),
      "These cards show captured example responses, not live systems. Start with ",
      h("code", { text: "python run.py" }),
      " (without --demo) for live status."));
  banner.hidden = false;
}

export function showFatal(container, title, message) {
  container.replaceChildren(
    h("div", { class: "fatal" },
      h("div", { class: "callout" },
        h("p", null, h("strong", { text: title })),
        h("p", { class: "callout-hint", text: message }))));
}

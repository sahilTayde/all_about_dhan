/**
 * Visible copy never leaks raw engine codes. The code stays on title= for the desk.
 * Paper only. No invented numbers.
 */

export const CUSTOMER_UNDERLYINGS = Object.freeze(["NIFTY", "SENSEX"]);

const PLAIN = Object.freeze({
  DATA_INSUFFICIENT: "Waiting for live price",
  DI: "Waiting for live price",
  UNKNOWN: "Waiting for live price",
  "N/A": "Waiting for live price",
  NA: "Waiting for live price",
  "—": "Waiting for live price",
  "-": "Waiting for live price",
  NO_PROMOTE: "Paper only — not a live book",
  "STATIC FIXTURE": "Waiting for live price",
  "static fixture": "Waiting for live price",
  STATIC_FIXTURE: "Waiting for live price",
});

const MIX_NAMES = Object.freeze({
  "MIX-DEFAULT-BUY": "Desk default buy",
  "MIX-ML-LOGIT": "Logit observer",
  "MIX-ML-LOGIT-XR": "Logit + XR observer",
  "MIX-ML-GREEKS": "Greeks observer",
  "MIX-TV-EP-024": "TV-EP lab",
  "MIX-FORM-FOLLOWS": "Form-follows",
  "MIX-SYNTH-A": "Synth A",
  "MIX-SYNTH-B": "Synth B",
});

export function indexTabs(list) {
  const src = Array.isArray(list) && list.length ? list : CUSTOMER_UNDERLYINGS;
  const keep = src.map((u) => String(u || "").toUpperCase()).filter((u) => CUSTOMER_UNDERLYINGS.includes(u));
  return keep.length ? [...new Set(keep)] : [...CUSTOMER_UNDERLYINGS];
}

export function isRawCode(value) {
  if (value == null || value === "") return true;
  const s = String(value).trim();
  const u = s.toUpperCase();
  if (PLAIN[s] || PLAIN[u]) return true;
  if (u.startsWith("MIX-")) return true;
  if (u === "NO_PROMOTE" || u.includes("DATA_INSUFFICIENT")) return true;
  return false;
}

export function plainCode(value, fallback = "Waiting for live price") {
  if (value == null || value === "") return { text: fallback, code: "DATA_INSUFFICIENT" };
  const s = String(value).trim();
  if (!s) return { text: fallback, code: "DATA_INSUFFICIENT" };
  if (PLAIN[s]) return { text: PLAIN[s], code: s };
  const u = s.toUpperCase();
  if (PLAIN[u]) return { text: PLAIN[u], code: s };
  if (MIX_NAMES[s] || MIX_NAMES[u]) return { text: MIX_NAMES[s] || MIX_NAMES[u], code: s };
  if (u.startsWith("MIX-")) return { text: s.replace(/^MIX-/, "").replace(/-/g, " ").toLowerCase(), code: s };
  return { text: s, code: null };
}

export function plainText(value, fallback) {
  return plainCode(value, fallback).text;
}

/** IST clock with a CT tooltip. Never invent a time. */
export function formatIst(ist, { seconds = false } = {}) {
  if (!ist) return { text: "—", title: undefined, ms: null, raw: null };
  const raw = String(ist);
  const m = raw.match(/T(\d{2}:\d{2})(?::(\d{2}))?/);
  const hhmm = m ? (seconds && m[2] ? `${m[1]}:${m[2]}` : m[1]) : raw;
  const ms = Date.parse(raw);
  let ct = null;
  if (Number.isFinite(ms)) {
    ct = new Intl.DateTimeFormat("en-GB", {
      timeZone: "America/Chicago",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
    }).format(ms);
  }
  return { text: `${hhmm} IST`, title: ct ? `CT ${ct}` : undefined, ms: Number.isFinite(ms) ? ms : null, raw };
}

export function replayAlerts(alerts, replay) {
  if (!replay) return alerts || [];
  return (alerts || []).filter((a) => {
    const blob = `${a.source || ""} ${a.id || ""} ${a.title || ""}`.toLowerCase();
    if (blob.includes("recorder") || blob.includes("feed") || blob.includes("health monitor")) return false;
    return true;
  });
}

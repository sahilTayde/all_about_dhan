/**
 * Plain view-model for the redesigned desk pages. Reads only fields the API already sends
 * (apps/api/src/api/ui_feed.py board + days; research rows from desk_ml/research_rules.py).
 * Rules below are the quant desk lead's limits (12 Oct 2026), not market data.
 */

export const RULES = Object.freeze({
  maxTradesPerDay: 3,
  maxOpen: 2,
  maxLosersPerDay: 2,
  dayLossInr: -25000,
  dayLossInrR01: -15000, // R01 / B3a slots
  lots: 10,
  qty: { NIFTY: 650, SENSEX: 200 },
  holdMin: 20,
});

export const STRATEGIES = Object.freeze([
  { id: "R01_PDIV_5_ALL_H20", name: "Premium divergence", state: "LIVE" },
  { id: "R01_B3A_VOL", name: "Premium divergence · high vol", state: "LIVE" },
  { id: "R02_MOM_3_0.0005_ALL_H20", name: "Momentum", state: "SHADOW", note: "parked from 11:50 IST" },
  { id: "B2", name: "B2", state: "SHADOW" },
  { id: "MIX-DEFAULT-BUY", name: "Old MIX book", state: "OFF" },
]);

const STRAT_BY_ID = Object.fromEntries(STRATEGIES.map((s) => [s.id, s]));
export const strategyName = (id) => STRAT_BY_ID[id]?.name || id || "—";
export const strategyState = (id) => STRAT_BY_ID[id]?.state || (String(id || "").startsWith("MIX") ? "OFF" : "SHADOW");

/** Exit reasons and price flags in plain words, with a colour tone. */
const REASONS = {
  TIME: { text: "Time exit (20 min)", tone: "ok" },
  TIME_H20: { text: "Time exit (20 min)", tone: "ok" },
  TARGET: { text: "Target hit", tone: "ok" },
  STOP: { text: "Stop hit", tone: "bad" },
  STOP_DAY_LOSS: { text: "Day loss limit hit", tone: "bad" },
  COVER_LONG_UNWIND: { text: "Long unwind exit", tone: "warn" },
  EXIT_SHIFTED: { text: "Exit moved to nearest priced minute", tone: "warn" },
  EXIT_EARLY_NO_QUOTE: { text: "Exited early: no quote at 20 min", tone: "warn" },
  EXIT_LATE_NO_QUOTE: { text: "Exited late: no quote at 20 min", tone: "warn" },
  EXIT_NO_QUOTE_AT_ENTRY_PX: { text: "No exit quote: booked at entry price", tone: "bad" },
  GUARD_BLOCKED: { text: "Blocked by guard", tone: "muted" },
  BLOCKED_OPPOSITE_SIDE: { text: "Blocked: opposite side", tone: "muted" },
};

export function reasonInfo(code) {
  const c = String(code || "").toUpperCase();
  return REASONS[c] || { text: c ? c.replace(/_/g, " ").toLowerCase() : "—", tone: "muted" };
}

export function flagsOf(t) {
  const f = t?.price_flags;
  if (Array.isArray(f)) return f.filter(Boolean);
  if (typeof f === "string") return f.split(",").map((x) => x.trim()).filter(Boolean);
  return [];
}

export const num = (v) => (v == null || v === "" || !Number.isFinite(Number(v)) ? null : Number(v));

export function inr(n, { signed = true } = {}) {
  const v = num(n);
  if (v == null) return "—";
  const s = Math.abs(Math.round(v)).toLocaleString("en-IN");
  return `${v < 0 ? "−" : signed && v > 0 ? "+" : ""}₹${s}`;
}

export const tone = (n) => (num(n) == null ? "" : num(n) >= 0 ? "is-up" : "is-down");

export function hhmm(ist) {
  const m = String(ist || "").match(/T(\d{2}:\d{2})/);
  return m ? m[1] : null;
}

export function addMin(hm, mins) {
  const m = String(hm || "").match(/^(\d{2}):(\d{2})$/);
  if (!m) return null;
  const t = Number(m[1]) * 60 + Number(m[2]) + mins;
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
}

export const isResearch = (t) => t?.research_rule === true || /^R\d|^B\d/.test(String(t?.book_id || ""));
export const strikeOf = (t) => num(t?.held_strike) ?? num(t?.atm_strike);

/** Exit rule text: research H20 slots exit on time, MIX uses stop/target. */
export function exitRule(t) {
  const source = String(t?.source_config || t?.book_id || "");
  const h20 = isResearch(t) || /H20/.test(source);
  if (h20) {
    const entry = t?.entry_min || hhmm(t?.opened_ist);
    const at = t?.spec_exit_min || addMin(entry, RULES.holdMin);
    return { kind: "time", text: `Exit: time 20 min${at ? ` · at ${at} IST` : ""}`, at };
  }
  if (num(t?.stop) != null || num(t?.target) != null) {
    return { kind: "levels", text: `Stop ${num(t.stop) ?? "—"} · Target ${num(t.target) ?? "—"}` };
  }
  return { kind: "none", text: "Exit rule not sent by the desk" };
}

export function netOf(t) {
  const realised = num(t?.realized_pnl_inr);
  if (realised != null) return realised;
  const u = num(t?.unrealized_pnl_inr ?? t?.unrealised_pnl_inr);
  if (u != null) return u;
  const e = num(t?.entry), l = num(t?.last_ltp), q = num(t?.qty);
  return e != null && l != null && q != null ? (l - e) * q : null;
}

export function sessionTrades(board) {
  const day = board?.session_ist_date;
  const onDay = (t) => !day || String(t.opened_ist || t.closed_ist || "").startsWith(day);
  const open = (board?.open_trades || []).filter(onDay);
  const closed = (board?.closed_trades || []).filter(onDay);
  return { day, open, closed };
}

/** Books for the session: research vs MIX, each with trades, charges and net, plus the day total. */
export function deskDay(snap) {
  const board = snap?.board || null;
  const { day, open, closed } = sessionTrades(board);
  const dayRow = (snap?.days || []).find((x) => x.day === day) || null;
  const sum = (rows, k) => rows.reduce((s, t) => s + (num(k(t)) || 0), 0);
  const group = (pred) => {
    const c = closed.filter(pred);
    const o = open.filter(pred);
    return {
      trades: c.length + o.length,
      open: o.length,
      wins: c.filter((t) => (num(t.realized_pnl_inr) || 0) > 0).length,
      charges: sum(c, (t) => t.charges_inr),
      net: sum(c, (t) => t.realized_pnl_inr),
    };
  };
  const research = group(isResearch);
  const mix = group((t) => !isResearch(t));
  const isLive = (t) => strategyState(t.book_id) === "LIVE";
  const live = group(isLive);
  const losers = closed.filter((t) => isLive(t) && (num(t.realized_pnl_inr) || 0) < 0).length;
  return {
    day,
    open,
    closed,
    research,
    live,
    mix,
    total: dayRow ? { net: num(dayRow.net), charges: num(dayRow.charges), n: dayRow.n, fromFeed: true } : { net: research.net + mix.net, charges: research.charges + mix.charges, n: closed.length, fromFeed: false },
    byBook: dayRow?.by_book || null,
    losers,
    guardBlocked: board?.research_rules?.guard_blocked || board?.guard_blocked || [],
  };
}

/** Desk status light from the limits. */
export function statusLight(dd, conn, offline) {
  if (offline || conn === "offline") return { tone: "red", text: "No live data: the API is not answering" };
  if (dd.live.net <= RULES.dayLossInr) return { tone: "red", text: "Day stopped: loss limit reached" };
  if (dd.losers >= RULES.maxLosersPerDay) return { tone: "red", text: "Day stopped: 2 losing trades" };
  if (dd.open.length) return { tone: "green", text: `${dd.open.length} trade${dd.open.length > 1 ? "s" : ""} open` };
  if (conn === "polling") return { tone: "amber", text: "Live push dropped: updating every 2 s" };
  return { tone: "amber", text: "Flat: waiting for a signal" };
}

export function ageSec(iso, now = Date.now()) {
  const t = Date.parse(iso || "");
  return Number.isFinite(t) ? Math.max(0, Math.round((now - t) / 1000)) : null;
}

export function fmtAge(sec) {
  if (sec == null) return "age unknown";
  if (sec < 90) return `${sec}s ago`;
  if (sec < 5400) return `${Math.round(sec / 60)} min ago`;
  if (sec < 172800) return `${Math.round(sec / 3600)} h ago`;
  return `${Math.round(sec / 86400)} days ago`;
}

/** Alerts with age; `fresh` hides anything older than a day. */
export function agedAlerts(alerts, { maxAgeSec = null } = {}) {
  return (alerts || [])
    .map((a) => ({ ...a, age: ageSec(a.ts || a.since) }))
    .filter((a) => maxAgeSec == null || (a.age != null && a.age <= maxAgeSec));
}

export function tradeCsv(rows) {
  const head = ["opened_ist", "closed_ist", "strategy", "underlying", "side", "strike", "entry", "exit", "charges_inr", "net_inr", "exit_reason", "flags"];
  const lines = [head.join(",")].concat(
    (rows || []).map((t) =>
      [t.opened_ist, t.closed_ist, t.book_id, t.underlying, t.side, strikeOf(t), t.entry, t.exit, t.charges_inr, t.realized_pnl_inr, t.exit_reason, flagsOf(t).join("|")]
        .map((v) => JSON.stringify(v ?? ""))
        .join(","),
    ),
  );
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "paper-trades.csv";
  a.click();
}

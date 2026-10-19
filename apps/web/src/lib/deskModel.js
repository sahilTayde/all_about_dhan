/**
 * Plain view-model for the redesigned desk pages. Reads only fields the API already sends
 * (apps/api/src/api/ui_feed.py board + days; research rows from desk_ml/research_rules.py).
 * Rules below are the quant desk lead's limits (12 Oct 2026), not market data.
 */
import { trailText } from "./pxExits.js"; // text only (live stop wording); no shadow number reaches any total here

export const RULES = Object.freeze({
  maxOpen: 2,
  maxLosersPerDay: 2,
  dayLossInr: -25000,
  dayLossInrR01: -15000, // R01 / B3a slots
  lots: 10,
  qty: { NIFTY: 650, SENSEX: 200 },
  holdMin: 20,
});

export const STRATEGIES = Object.freeze([
  { id: "R01_PDIV_5_ALL_H20", name: "Price-divergence buy" },
  { id: "R01_B3A_VOL", name: "Divergence + volume" },
  { id: "R02_MOM_3_0.0005_ALL_H20", name: "Momentum" },
  { id: "B2", name: "B2" },
  { id: "MIX-DEFAULT-BUY", name: "Old MIX book" },
]);

/** desk_status (research_rules.py) in plain words. Rows without it (before the restart) count as traded. */
export const DESK_STATUS = Object.freeze({
  TRADED: { text: "traded", tone: "ok" },
  SHADOW_PARKED: { text: "shadow only", tone: "muted" },
  BLOCKED_OPPOSITE_SIDE: { text: "blocked: opposite side", tone: "warn" },
  DUP_SAME_CONTRACT: { text: "duplicate, not counted", tone: "muted" },
  RISK_BLOCKED: { text: "blocked: risk limit", tone: "bad" },
  RISK_DAY_STOP: { text: "blocked: risk limit", tone: "bad" },
  RISK_CAP_OPEN: { text: "blocked: risk limit", tone: "bad" },
  RISK_CAP_TRADES: { text: "blocked: risk limit", tone: "bad" },
});
export function deskStatusOf(t, fallback = "TRADED") {
  const s = String(t?.desk_status || t?.guard || "").toUpperCase();
  return DESK_STATUS[s] ? s : fallback;
}
export const deskStatusText = (t, fb) => DESK_STATUS[deskStatusOf(t, fb)].text;
export const isOpenRow = (t) => (t?.status ? /OPEN/.test(String(t.status)) : t?.closed_ts == null);

/** Lists the backend puts beside the desk trades (all optional). */
export function researchLists(board) {
  const rr = board?.research_rules || {};
  const parked = rr.shadow_parked || {};
  return {
    blocked: Array.isArray(rr.guard_blocked) ? rr.guard_blocked : [],
    riskBlocked: Array.isArray(rr.risk_blocked) ? rr.risk_blocked : [],
    dups: Array.isArray(rr.dup_same_contract) ? rr.dup_same_contract : [],
    parked: [...(parked.open || []), ...(parked.closed || [])],
    parkedIds: parked.rule_ids || [],
    parkedNote: parked.note || null,
  };
}

/** Minutes left until an IST HH:MM today (negative once passed). */
export function minsUntil(hm, now = new Date()) {
  const m = String(hm || "").match(/^(\d{2}):(\d{2})$/);
  if (!m) return null;
  const ist = new Date(now.getTime() + (330 + now.getTimezoneOffset()) * 60000);
  return (Number(m[1]) * 60 + Number(m[2])) - (ist.getHours() * 60 + ist.getMinutes() + ist.getSeconds() / 60);
}

export function pctOf(entry, now) {
  const e = num(entry), n = num(now);
  return e && n != null ? ((n - e) / e) * 100 : null;
}
export const pctText = (p) => (p == null ? "—" : `${p >= 0 ? "+" : "−"}${Math.abs(p).toFixed(1)}%`);

const STRAT_BY_ID = Object.fromEntries(STRATEGIES.map((s) => [s.id, s]));
export const strategyName = (id) => STRAT_BY_ID[id]?.name || id || "—";

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
export function exitRule(t, live = null) {
  const source = String(t?.source_config || t?.book_id || "");
  // 2026-10-19: PAPER_EXTRA (PX_*) rows have no timer: show premium stop/target/trail from the runner, never a fake 20-min countdown.
  const px = /^PX_/.test(String(t?.rule_id || t?.book_id || "")) || /PAPER_EXTRA/i.test(source);
  if (px) {
    const st = num(t?.stop_px ?? t?.stop), tg = num(t?.target_px ?? t?.target);
    if (st == null && tg == null) return { kind: "none", text: "Stop/target not sent (PRICE_EXIT missing)" };
    // 2026-10-19 desk-exit-labels: trail text comes from data only. `live` = live pricer state from /research/px-exits
    // (stop_floor / trail_gap / hw); else the runner's own trail text; else '—'. No hard-coded fallback.
    const trail = live && num(live.live_stop) != null ? trailText(live) : t?.trail || "—";
    return { kind: "levels", text: `Stop ${st ?? "—"} · Target ${tg ?? "—"} · Trail: ${trail} · 15:15 safety close`, at: null, liveStop: live ? num(live.live_stop) : null };
  }
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
  // desk P&L counts traded rows only (desk_status TRADED, shadow false); old rows have no desk_status
  const isLive = (t) => deskStatusOf(t) === "TRADED" && t.shadow !== true || (!t.desk_status && isResearch(t) && /^R01/.test(String(t.book_id)));
  const live = group(isLive);
  const deskToday = group((t) => isResearch(t) && isLive(t)); // fallback Today: desk-traded research rows only
  const losers = closed.filter((t) => isLive(t) && (num(t.realized_pnl_inr) || 0) < 0).length;
  return {
    day,
    open,
    closed,
    research,
    live,
    mix,
    total: dayRow ? { net: num(dayRow.net), charges: num(dayRow.charges), n: dayRow.n, wins: dayRow.wins, fromFeed: true } : { net: deskToday.net, charges: deskToday.charges, n: deskToday.trades - deskToday.open, wins: deskToday.wins, fromFeed: false } /* desk-traded rows only, same as feed days[].net; mix/shadow never in Today */,
    byBook: dayRow?.by_book || null,
    losers,
    guardBlocked: researchLists(board).blocked,
    lists: researchLists(board),
    risk: board?.risk && typeof board.risk === "object" ? board.risk : null,
  };
}

/** Desk status light from the limits. */
export function statusLight(dd, conn, offline) {
  if (offline || conn === "offline") return { tone: "red", text: "No live data: the API is not answering" };
  // halt state comes only from the engine (optional board.risk); never computed from rows here
  if (dd.risk?.halted_reason) return { tone: "red", text: haltText(dd.risk.halted_reason) };
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

export const CHARGES_LABEL = "Dhan rates ×1.5";

/** Three health dots: market data, paper loop, website data fresh (age of board.as_of_ist). */
export function healthDots(snap, conn) {
  const h = snap?.health || [];
  const pick = (id) => h.find((x) => x.id === id);
  const md = pick("data"), loop = pick("paper");
  const boardAge = ageSec(snap?.board?.as_of_ist);
  const toneOf = (x) => (!x ? "grey" : x.tone === "green" ? "green" : x.tone === "red" ? "red" : "amber");
  return [
    { id: "data", label: "Market data", tone: toneOf(md), detail: md?.detail || "—" },
    { id: "loop", label: "Paper loop", tone: toneOf(loop), detail: loop?.detail || "—" },
    { id: "web", label: "Website data", tone: conn === "offline" || snap?.offline ? "red" : boardAge == null ? "grey" : boardAge > 300 ? "amber" : "green", detail: boardAge == null ? "—" : `updated ${fmtAge(boardAge)}` },
  ];
}

/** Age of each feed we can see; stale = older than 5 min. */
export function feedAges(snap) {
  const rows = [
    { name: "Desk board", iso: snap?.board?.as_of_ist },
    { name: "Market tape", iso: snap?.tape_last_ist },
  ];
  for (const h of snap?.health || []) rows.push({ name: h.name, sec: h.age_s, detail: h.detail });
  return rows.map((r) => {
    const sec = r.sec != null ? Number(r.sec) : ageSec(r.iso);
    return { ...r, sec, stale: sec != null && sec > 300 };
  });
}

export function clockPair(iso) {
  const t = Date.parse(iso || "");
  if (!Number.isFinite(t)) return "—";
  const f = (tz) => new Intl.DateTimeFormat("en-GB", { timeZone: tz, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(t));
  return `${f("Asia/Kolkata")} IST / ${f("America/Chicago")} CT`;
}

const FAMILY_WHY = {
  PDIV: "Option premium moved against the index (price divergence)",
  MOM: "Index kept moving one way (momentum)",
};
/** Why the desk took it, in plain words, from family + market_type (+ B3A volume filter). */
export function signalWhy(t) {
  if (t?.why) return `${t.why}. Bought ${String(t?.side).toUpperCase() === "CE" ? "a call" : "a put"}.`;   // 2026-10-19: per-trade reason from paper_extra
  const fam = String(t?.family || "").toUpperCase();
  const base = FAMILY_WHY[fam] || (/MIX/.test(String(t?.book_id || "")) ? "Old MIX desk pick (reason not sent per trade)" : null);
  if (!base) return "—";
  const vol = /B3A/.test(String(t?.source_config || t?.book_id || "")) ? ", with high volume" : "";
  const mkt = t?.market_type ? `; market ${t.market_type}` : "";
  return `${base}${vol}${mkt}. Bought ${String(t?.side).toUpperCase() === "CE" ? "a call" : "a put"}.`;
}

/** Profit for today / last 5 sessions / all time from feed days + account. */
export function periodNets(snap) {
  const days = snap?.days || [];
  const sorted = [...days].sort((a, b) => b.day.localeCompare(a.day));
  return {
    week: sorted.slice(0, 5).reduce((s, d) => s + (num(d.net) || 0), 0),
    weekTrades: sorted.slice(0, 5).reduce((s, d) => s + (num(d.n) || 0), 0),
    total: num(snap?.account?.net_inr),
    totalTrades: days.reduce((s, d) => s + (num(d.n) || 0), 0),
    capital: num(snap?.account?.equity_inr),
    start: num(snap?.account?.starting_capital_inr),
  };
}

export const HALT_TEXT = Object.freeze({
  RISK_DAY_STOP: "day stopped: loss limit",
  RISK_CAP_OPEN: "max open trades reached",
  RISK_CAP_TRADES: "trade cap reached",
});
export const haltText = (r) => (r ? HALT_TEXT[String(r).toUpperCase()] || String(r).replace(/_/g, " ").toLowerCase() : null);

/** Engine risk state (board.risk, optional). Every field may be missing. */
export function riskView(risk) {
  if (!risk || typeof risk !== "object") return null;
  const n = (k) => num(risk[k]);
  return {
    trades: n("trades_today"),
    maxTrades: n("max_trades"),
    open: n("open_now"),
    maxOpen: n("max_open"),
    losers: n("losers_today"),
    dayNet: n("day_net_inr"),
    dayStop: risk.day_stop_hit === true,
    groupNet: n("rr_group_net_inr"),
    groupStop: risk.rr_group_stop_hit === true,
    halted: risk.halted_reason || null,
    haltedText: haltText(risk.halted_reason),
  };
}

/** Park times the backend uses (research_rules.py PARK_FROM_IST); fires at/after it are shadow. */
const PARK_FROM = { "R02_MOM_3_0.0005_ALL_H20": { "2026-10-12": "11:50" } };

/**
 * Status for a desk row: the backend desk_status when present; otherwise (feed before the restart)
 * the same rules the backend applies: a fire after the park time is shadow; a second strategy on the
 * same contract (underlying + side + strike + entry time) was a real repeat-buy position and counts.
 */
export function classifyDeskRows(rows, day) {
  const seen = new Map();
  return [...rows]
    .sort((a, b) => (num(a.opened_ts) || 0) - (num(b.opened_ts) || 0))
    .map((r) => {
      if (r.desk_status) return { r, code: String(r.desk_status).toUpperCase(), basis: "desk_status" };
      const park = PARK_FROM[r.book_id]?.[day];
      const t = r.entry_min || hhmm(r.opened_ist);
      if (park && t && t >= park) return { r, code: "SHADOW_PARKED", basis: `entry ${t} after park ${park}` };
      const key = [r.underlying, r.side, strikeOf(r), r.opened_ts].join("|");
      // no desk_status: a same-contract copy was a real held position (repeat-buy bug, since fixed) and counts
      if (seen.has(key)) return { r: { ...r, repeat_of: seen.get(key) }, code: "TRADED", repeatBug: true, basis: `same contract and time as ${seen.get(key)}` };
      seen.set(key, r.trade_id);
      return { r, code: "TRADED", basis: "no desk_status (feed before restart)" };
    });
}

/** Today's research desk total: TRADED rows only, closed, after charges. */
export function researchToday(dd) {
  const rows = [...dd.open, ...dd.closed].filter((t) => t.research_rule || t.desk_status);
  const cls = classifyDeskRows(rows, dd.day);
  const traded = cls.filter((c) => c.code === "TRADED");
  const closed = traded.filter((c) => c.r.closed_ts != null || /CLOSED/.test(String(c.r.status)));
  const sum = (list, k) => list.reduce((x, c) => x + (num(c.r[k]) || 0), 0);
  const notCounted = cls.filter((c) => c.code !== "TRADED");
  return {
    cls,
    n: traded.length,
    open: traded.length - closed.length,
    wins: closed.filter((c) => (num(c.r.realized_pnl_inr) || 0) > 0).length,
    net: sum(closed, "realized_pnl_inr"),
    charges: sum(closed, "charges_inr"),
    notCounted: notCounted.length,
    notCountedNet: sum(notCounted.filter((c) => c.r.closed_ts != null), "realized_pnl_inr"),
  };
}

/**
 * Stop / target / time exit exactly as the desk sends them. Never computed.
 * Feed fields: stop, target (paper_scalp / ui_feed board rows), spec_exit_min (time-exit rows),
 * background test: stop_px / target_px / exit_ist (only when present).
 */
export function levelsOf(t) {
  const entry = num(t?.entry ?? t?.entry_px);
  const stop = num(t?.stop ?? t?.stop_px);
  const target = num(t?.target ?? t?.target_px);
  const timeExit = hhmm(t?.spec_exit_min) || (typeof t?.spec_exit_min === "string" ? t.spec_exit_min : null);
  return { entry, stop, target, stopPct: pctOf(entry, stop), targetPct: pctOf(entry, target), timeExit };
}

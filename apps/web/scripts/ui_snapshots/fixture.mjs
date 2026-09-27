// Synthetic paper board for UI snapshots. Invented numbers on a fake past session.
// Not market data, not a replay, not a fill. Safe for a public repo.

const DAY = "2026-01-15";
const IST_OFFSET = "+05:30";
const BASE_TS = Date.parse(`${DAY}T09:30:00${IST_OFFSET}`) / 1000;

function ist(ts) {
  const d = new Date((ts + 5.5 * 3600) * 1000);
  return `${d.toISOString().slice(0, 19)}${IST_OFFSET}`;
}

const EXITS = ["STOP", "TARGET", "CANCEL_AGAINST", "COVER_LONG_UNWIND", "TIME", "STOP", "CANCEL_NO_PROGRESS"];
const LONG_WHY =
  "SYNTH buy {side} ITM strike {strike} (ITM_100); bin={side} regime=TREND last3=none; impulse_note=pause_wait_continuation; " +
  "path stop {stop} → target {target} (premium points; strict first TARGET); overlay=CE+PE+strength; " +
  "why_now={side}: synthetic fixture reason that is deliberately long so the notes column would wrap for many lines; PAPER only. NO_PROMOTE.";

function trade(i) {
  const und = i % 4 === 3 ? "BANKNIFTY" : "NIFTY";
  const side = i % 2 ? "PE" : "CE";
  const spot = und === "NIFTY" ? 20000 + i * 17.35 : 45000 + i * 41.2;
  const step = und === "NIFTY" ? 50 : 100;
  const strike = Math.round(spot / step) * step + (side === "CE" ? -step * 2 : step * 2);
  const entry = 120 + ((i * 37) % 90) + 0.25;
  const reason = EXITS[i % EXITS.length];
  const move = reason === "TARGET" ? 11 : reason === "STOP" ? -9.5 : reason === "TIME" ? 1.4 : -3.2;
  const exit = +(entry + move).toFixed(2);
  const lotSize = und === "NIFTY" ? 50 : 15;
  const lots = 4 + (i % 5);
  const qty = lotSize * lots;
  const gross = +(move * qty).toFixed(2);
  const charges = +(60 + qty * 0.05).toFixed(2);
  const opened = BASE_TS + i * 1380;
  const closed = opened + 240 + (i % 3) * 120;
  const stop = +(entry * 0.94).toFixed(2);
  const target = +(entry * 1.06).toFixed(2);
  return {
    book_id: "MIX-DEFAULT-BUY",
    model_names: ["MIX-SYNTH-A", "MIX-SYNTH-B"],
    underlying: und,
    side,
    trade_id: `synth-${String(i).padStart(2, "0")}-${und}-${side}`,
    status: reason.startsWith("CANCEL") ? "CLOSED_CANCEL" : "CLOSED",
    target_step: 0,
    entry,
    limit_price: entry,
    exit,
    stop,
    target,
    atm_strike: strike,
    spot_at_entry: +spot.toFixed(2),
    exit_reason: reason,
    realized_pnl: move,
    gross_pnl_inr: gross,
    charges_inr: charges,
    realized_pnl_inr: +(gross - charges).toFixed(2),
    lot_size: lotSize,
    lots,
    qty,
    notional_inr: +(entry * qty).toFixed(2),
    index_regime: i % 3 ? "TREND" : "CHOP",
    justification: LONG_WHY.replaceAll("{side}", side)
      .replace("{strike}", String(strike))
      .replace("{stop}", String(stop))
      .replace("{target}", String(target)),
    opened_ts: opened,
    closed_ts: closed,
    last_updated_ts: closed,
    opened_ist: ist(opened),
    closed_ist: ist(closed),
    last_updated_ist: ist(closed),
    target_hit: reason === "TARGET",
    result: reason === "TARGET" ? "SUCCESS" : "LOSS",
    filled: true,
  };
}

const closed = Array.from({ length: 15 }, (_, i) => trade(i)).reverse();
const tapeLastTs = BASE_TS + 15 * 1380 + 300;
const openEntry = 140.5;
const open = [
  {
    ...trade(15),
    trade_id: "synth-open-NIFTY-PE",
    underlying: "NIFTY",
    side: "PE",
    atm_strike: 20350,
    justification: "SYNTH buy PE ITM strike 20350 (ITM_100); why_now=PE: synthetic open ticket for the layout check; PAPER only. NO_PROMOTE.",
    status: "OPEN",
    exit: null,
    exit_reason: null,
    target_hit: false,
    result: null,
    realized_pnl: null,
    realized_pnl_inr: null,
    entry: openEntry,
    limit_price: openEntry,
    last_ltp: 138.2,
    stop: 132.07,
    target: 148.93,
    qty: 250,
    lots: 5,
    lot_size: 50,
    seen_high: 143.1,
    seen_low: 136.4,
    trail_step: 0,
    idx_at_open: 20260.4,
    spot_at_entry: 20260.4,
    closed_ts: null,
    closed_ist: null,
    last_updated_ts: tapeLastTs - 4,
    last_updated_ist: ist(tapeLastTs - 4),
  },
];

const net = closed.reduce((s, t) => s + t.realized_pnl_inr, 0);
const regime = (index, direction) => ({
  regime: "TREND",
  direction,
  er: 0.42,
  realized_vol: 0.00018,
  iv: 12.4,
  range_over_atr: 3.1,
  vwap: index - 3.5,
  ema: index - 1.2,
  ema_len: 21,
  proxy_poc: index - 6,
  sr_near: { name: "pdh", px: index + 22, kind: "R" },
  itm_bin: { side: "PE", index },
});

export const board = {
  ok: true,
  job: "ML_PAPER_SCALP",
  title: "SYNTHETIC FIXTURE",
  live_session: true,
  session_ist_date: DAY,
  // Written long after the session (a replay): the page must show tape time, not this.
  as_of_ist: "2026-02-01T04:04:00+05:30",
  starting_desk_inr: 500000,
  overall_pnl_inr: net,
  win_rate_net_pct: 20,
  source: "dual-tape",
  steps: {
    NIFTY: { status: "REPLAY_OK", span_ist: { first: ist(BASE_TS), last: ist(tapeLastTs) } },
    BANKNIFTY: { status: "REPLAY_OK", span_ist: { first: ist(BASE_TS), last: ist(tapeLastTs - 60) } },
  },
  last_index_regime: { NIFTY: regime(20999.95, "UP"), BANKNIFTY: regime(45999.9, "DOWN") },
  capital_plan: { desk_capital_inr: 500000 },
  today: { net_pnl_inr: net, starting_desk_inr: 500000 },
  book_rank: [
    { book_id: "MIX-DEFAULT-BUY", kind: "dealer", n_filled: 15, win_rate_net_pct: 20, sum_pnl_inr: net, sum_charges_inr: 1500 },
    { book_id: "MIX-ML-LOGIT", kind: "ml", n_filled: 0, win_rate_net_pct: null, sum_pnl_inr: 0, sum_charges_inr: 0 },
  ],
  seen_not_taken: {
    skipped_latest: [
      // SENSEX is OFF in the founder book: the hold reason must not quote it.
      { underlying: "SENSEX", side: "PE", reason: "NO_NEW_AFTER_1516", why: "No NEW after 15:16 IST (synthetic).", action: "SKIP", book_id: "MIX-DEFAULT-BUY" },
      { underlying: "NIFTY", side: "CE", reason: "CANCEL_AGAINST", why: "Overlay cancelled the CE after the thesis broke (synthetic).", action: "CANCEL", book_id: "MIX-DEFAULT-BUY", last_updated_ist: ist(BASE_TS + 900) },
    ],
    cancelled: [],
  },
  model_signals: {
    latest: [
      { source: "synth-a", side: "CE", vs_picker: "MATCH", underlying: "NIFTY", ts: BASE_TS + 14 * 1380, desk_opened: true },
    ],
  },
  closed_trades: closed,
  open_trades: open,
  orders: "REFUSED",
  promote: false,
};

export const exam = {
  ok: true,
  job: "sod-exam",
  as_of_ist: `${DAY}T15:45:00${IST_OFFSET}`,
  overall_honesty: "CLEAN",
  headline: "Synthetic exam fixture. Not a grade of any real day.",
  contract: { id: "SOD_FILL_CONTRACT_V1" },
  days: [
    {
      day: DAY,
      honesty: "CLEAN",
      session_kind: "NORMAL",
      n_sod_closed: 15,
      n_peeked_slices: 0,
      n_fill_contract_fail: 0,
      tape_note: "Synthetic tape note.",
      story: `${DAY}: synthetic story.`,
      spills: Array.from({ length: 6 }, (_, i) => ({
        underlying: "NIFTY",
        side: i % 2 ? "PE" : "CE",
        room: i % 3 ? "booking" : "none",
        code: i % 3 ? "CANCEL_AGAINST" : "WIN_OR_FLAT",
        plain: "Synthetic spill row. Do not retune from one day.",
      })),
    },
  ],
  stories: [],
  watch_next: ["synthetic watch-next line"],
  orders: "REFUSED",
  promote: false,
};

export const founderStatus = {
  ok: false,
  mode: "PAPER",
  next_action: "Paper market-hours process is not running",
  issues: ["Paper market-hours process is not running", "Ops monitor is not running — agent board will go stale"],
  agents: [
    { id: "paper-loop", name: "Paper market-hours", alive: false, tone: "red", detail: "not running" },
    { id: "ops-monitor", name: "Ops monitor", alive: false, tone: "red", detail: "monitor down" },
  ],
  services: [
    { id: "api", name: "FastAPI :8000", tone: "green", detail: "fixture" },
    { id: "dhan-chain", name: "Dhan live-chain", tone: "red", detail: "credentials missing — fixtures" },
  ],
  orders: "REFUSED",
  promote: false,
};

export const founderBook = { ok: true, trade_underlyings: ["NIFTY"], indices: {} };

// ---------- snapshot + endpoints the pages read (same shapes as apps/api/src/api/ui_feed.py) ----------

const REASONS = ["STOP", "TARGET", "CANCEL_AGAINST", "TIME"];

function pastDays(n) {
  const out = [];
  const d = new Date(`${DAY}T00:00:00Z`);
  while (out.length < n) {
    d.setUTCDate(d.getUTCDate() - 1);
    if (d.getUTCDay() % 6) out.push(d.toISOString().slice(0, 10));
  }
  return out;
}

function summary(day, i) {
  const n = 6 + ((i * 5) % 9);
  const wins = Math.max(1, Math.round(n * (0.2 + ((i * 7) % 5) / 12)));
  const net = Math.round((wins * 2600 - (n - wins) * 1900) * (i % 3 ? 1 : 0.6));
  const charges = n * 140;
  return {
    day,
    n,
    wins,
    gross: net + charges,
    charges,
    net,
    by_book: {
      "MIX-DEFAULT-BUY": { n, wins, net },
      "MIX-ML-LOGIT": { n: Math.max(1, n - 3), wins: Math.max(0, wins - 1), net: Math.round(net * 0.7) },
    },
    by_reason: splitByReason(n, wins, net + charges, charges),
  };
}

// Per-reason gross / charges / net that add up exactly to the day's totals (P&L-by-stage must sum to net).
function splitByReason(n, wins, gross, charges) {
  const counts = { TARGET: wins, STOP: Math.ceil((n - wins) / 3), CANCEL_AGAINST: Math.floor((n - wins) / 3) };
  counts.TIME = n - counts.TARGET - counts.STOP - counts.CANCEL_AGAINST;
  const targetGross = wins * 2600;
  const rest = gross - targetGross;
  const losers = n - wins || 1;
  const out = {};
  let left = rest;
  const keys = Object.keys(counts).filter((k) => counts[k] > 0);
  keys.forEach((k, j) => {
    const g = k === "TARGET" ? targetGross : j === keys.length - 1 ? left : Math.round((rest * counts[k]) / losers);
    if (k !== "TARGET") left -= g;
    const c = counts[k] * 140;
    out[k] = { n: counts[k], gross: g, charges: c, net: g - c };
  });
  return out;
}

const todayRows = closed.filter((t) => t.filled !== false);
const today = {
  day: DAY,
  n: todayRows.length,
  wins: todayRows.filter((t) => t.realized_pnl_inr > 0).length,
  gross: todayRows.reduce((s, t) => s + t.gross_pnl_inr, 0),
  charges: todayRows.reduce((s, t) => s + t.charges_inr, 0),
  net: Math.round(net * 100) / 100,
  by_book: { "MIX-DEFAULT-BUY": { n: todayRows.length, wins: 3, net } },
  by_reason: {},
};
for (const t of todayRows) {
  const r = (today.by_reason[t.exit_reason] ||= { n: 0, gross: 0, charges: 0, net: 0 });
  r.n += 1;
  r.gross += t.gross_pnl_inr;
  r.charges += t.charges_inr;
  r.net += t.realized_pnl_inr;
}
export const days = [today, ...pastDays(14).map(summary)];
const allNet = days.reduce((s, d) => s + d.net, 0);

export function snapshot(nowIso = "2026-02-01T10:00:00+05:30") {
  return {
    ok: true,
    as_of: nowIso,
    board,
    exam,
    tape_last_ist: ist(tapeLastTs),
    founder: { ok: false, mode: "PAPER", issues: founderStatus.issues, next_action: founderStatus.next_action, agents: founderStatus.agents, started_at_ist: ist(tapeLastTs - 600) },
    founder_book: { source: "file", index_status: { NIFTY: "START", BANKNIFTY: "STOP", SENSEX: "STOP" } },
    health: [
      { id: "api", name: "API", tone: "green", detail: "answering this request", age_s: 0 },
      { id: "paper", name: "Paper loop", tone: "red", detail: "not running", age_s: null },
      { id: "broker", name: "Broker (paper)", tone: "green", detail: "paper broker · orders refused · no live connection" },
      { id: "data", name: "Market data", tone: "amber", detail: "slow · last tape tick 95s ago", age_s: 95 },
      { id: "risk", name: "Risk / halt", tone: "green", detail: "no halt, no vetoed entry today" },
      { id: "db", name: "Database", tone: "grey", detail: "no ledger.sqlite yet (event path off)" },
      { id: "llm", name: "LLM", tone: "grey", detail: "off / rules-only" },
      { id: "news", name: "News", tone: "green", detail: "last news file 40 min ago" },
      { id: "queue", name: "Queue", tone: "grey", detail: "memory event bus in the paper process (no external queue to probe)" },
      { id: "heartbeat", name: "Last heartbeat", tone: "amber", detail: "board written 95s ago", age_s: 95 },
      { id: "monitor", name: "Health monitor", tone: "grey", detail: "not running (python -m health)" },
    ],
    alerts: [
      { id: "restart:synth-open", severity: "CRITICAL", title: "Restart during an open trade", detail: "NIFTY PE opened before the paper loop restarted (synthetic)", ts: nowIso, source: "paper" },
      { id: "h:synth:recorder", severity: "WARNING", title: "recorder alert", detail: "last update 1.6 min ago (synthetic)", ts: nowIso, source: "health monitor" },
    ],
    risk_halt: null,
    days,
    account: {
      starting_capital_inr: 500000,
      gross_inr: days.reduce((s, d) => s + d.gross, 0),
      charges_inr: days.reduce((s, d) => s + d.charges, 0),
      net_inr: allNet,
      equity_inr: 500000 + allNet,
      n_days: days.length,
      first_day: days.at(-1).day,
      last_day: DAY,
      funds_editable: false,
      funds_note: "Add funds / minimum capital need an engine-side setting. Coming in the controls PR.",
    },
    orders: "REFUSED",
    promote: false,
  };
}

export function dayHistory(day) {
  if (day === DAY) return { day, days: days.map((d) => d.day), trades: closed };
  const i = days.findIndex((d) => d.day === day);
  const s = days[i];
  if (!s) return { day, days: [], trades: [] };
  const trades = Array.from({ length: s.n }, (_, k) => {
    const t = trade(k + i);
    const shift = Date.parse(`${day}T00:00:00Z`) / 1000 - Date.parse(`${DAY}T00:00:00Z`) / 1000;
    // model-log rows carry no close time: the Out column must read "—", not "open"
    return { ...t, trade_id: `synth-${day}-${k}`, opened_ts: t.opened_ts + shift, opened_ist: ist(t.opened_ts + shift), closed_ist: null, closed_ts: null, last_updated_ist: null, spot_at_entry: k % 3 ? t.spot_at_entry : null, source: "model_log (live)" };
  });
  return { day, days: days.map((d) => d.day), trades };
}

export function trace(tradeId) {
  const t = [...open, ...closed].find((x) => x.trade_id === tradeId) || dayHistory(days[1].day).trades.find((x) => x.trade_id === tradeId);
  if (!t) return { ok: false, trade_id: tradeId, reason: "trade not found in board, model log or ledger", steps: [] };
  const none = (id, title, why = null) => ({ id, title, status: "NO_DATA", decided: null, why, fields: {}, source: null });
  return {
    ok: true,
    trade_id: tradeId,
    underlying: t.underlying,
    side: t.side,
    steps: [
      { id: "data", title: "Data", status: "OK", decided: `${t.underlying} spot ${t.spot_at_entry}`, why: "itm_bin confirm (synthetic)", fields: { regime: t.index_regime, "spot source": "trade record" }, source: "trade record" },
      { id: "analysts", title: "Analysts", status: "OK", decided: "agreed: MIX-SYNTH-A, MIX-SYNTH-B", why: null, fields: { "agreeing models": t.model_names }, source: "trade record" },
      { id: "boss", title: "Boss", status: "OK", decided: `BUY ${t.side} via ${t.book_id}`, why: `${t.side}: synthetic reason`, fields: {}, source: "trade record" },
      none("risk", "Risk", "No risk-engine record for this paper trade (event path not writing a ledger)."),
      { id: "desk", title: "Desk", status: "OK", decided: `${t.atm_strike} ${t.side} limit ${t.entry}`, why: "strike from ITM_100", fields: { stop: t.stop, target: t.target, lots: t.lots }, source: "trade record + model log" },
      { id: "broker", title: "Broker", status: "PAPER", decided: "Paper only — no broker order", why: "Paper mode: execution refused by design", fields: { execution: "refused" }, source: "trade record" },
      t.exit == null
        ? { id: "fill", title: "Fill", status: "OK", decided: `filled @ ${t.entry}`, why: "open", fields: { opened: t.opened_ist }, source: "trade record" }
        : { id: "fill", title: "Fill", status: "OK", decided: `filled @ ${t.entry}`, why: t.exit_reason, fields: { opened: t.opened_ist, closed: t.closed_ist, exit: t.exit, "net ₹": t.realized_pnl_inr }, source: "trade record" },
    ],
  };
}

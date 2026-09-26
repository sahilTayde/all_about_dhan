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
    side: "PE",
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
    closed_ts: null,
    closed_ist: null,
    last_updated_ts: tapeLastTs - 4,
    last_updated_ist: ist(tapeLastTs - 4),
  },
];

const net = closed.reduce((s, t) => s + t.realized_pnl_inr, 0);
const regime = (index) => ({ regime: "TREND", direction: "UP", vwap: index - 3, itm_bin: { side: "PE", index } });

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
  last_index_regime: { NIFTY: regime(20999.95), BANKNIFTY: regime(45999.9) },
  today: { net_pnl_inr: net, starting_desk_inr: 500000 },
  book_rank: [
    { book_id: "MIX-DEFAULT-BUY", kind: "dealer", n_filled: 15, win_rate_net_pct: 20, sum_pnl_inr: net, sum_charges_inr: 1500 },
    { book_id: "MIX-ML-LOGIT", kind: "ml", n_filled: 0, win_rate_net_pct: null, sum_pnl_inr: 0, sum_charges_inr: 0 },
  ],
  seen_not_taken: {
    skipped_latest: [
      { underlying: "NIFTY", side: "CE", reason: "CANCEL_AGAINST", action: "CANCEL", book_id: "MIX-DEFAULT-BUY", last_updated_ist: ist(BASE_TS + 900) },
    ],
    cancelled: [],
  },
  model_signals: { latest: [] },
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

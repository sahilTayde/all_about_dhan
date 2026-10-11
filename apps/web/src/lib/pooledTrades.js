/**
 * Founder pooled 1× V2 bid/ask fills (Sep 29–Oct 9). Dates and prices stay
 * on the source row. Never relabel a fill onto another day. Strike is absent
 * in this tape — leave it empty. Current NIFTY paper slot is 10 lots / qty 650.
 */
import { canonicalSlotId } from "./strategyBoard.js";
import { estRoundTripCharges } from "./paperBoard.js";

export const NIFTY_LOT = 65;
export const SLOT_LOTS = 10;
export const SLOT_QTY = 650;

export const CARD_WIN = Object.freeze({ date: "2026-10-01", in: "10:10", side: "PE" });
export const CARD_LOSS = Object.freeze({ date: "2026-10-09", in: "12:55", side: "CE" });

export function parsePooledCsv(text) {
  const lines = String(text || "")
    .trim()
    .split(/\r?\n/)
    .filter(Boolean);
  const header = (lines.shift() || "").split(",");
  return lines.map((line) => {
    const cols = line.split(",");
    const row = Object.fromEntries(header.map((k, i) => [k, cols[i]]));
    return {
      date: row.date,
      rule: row.rule,
      und: String(row.und || "").toUpperCase(),
      side: String(row.side || "").toUpperCase(),
      in: row.in,
      out: row.out,
      lots: Number(row.lots),
      ask_in: Number(row.ask_in),
      bid_out: Number(row.bid_out),
      net: Number(row.net),
      cap: Number(row.cap),
    };
  });
}

export function findPooledRow(rows, { date, in: hhmm, side, und = "NIFTY" } = {}) {
  return (
    (rows || []).find(
      (r) => r.date === date && r.in === hhmm && r.side === side && r.und === und,
    ) || null
  );
}

function ist(day, hhmm) {
  return `${day}T${hhmm}:00+05:30`;
}

function ts(day, hhmm) {
  return Date.parse(ist(day, hhmm)) / 1000;
}

function whyFor(side) {
  return side === "CE"
    ? "The index was rising, so the desk bought a call."
    : "The index was falling, so the desk bought a put.";
}

function explain(row, qty) {
  const bought = row.side === "CE" ? "call" : "put";
  const why = row.side === "CE" ? "the index was rising" : "the index was falling";
  const e = Number(row.ask_in).toFixed(2);
  const x = Number(row.bid_out).toFixed(2);
  const moved = row.bid_out > row.ask_in ? "rose" : "fell";
  return (
    `The desk bought the ${row.und} ${bought} because ${why}. ` +
    `Premium ${moved} from ${e} to ${x} at qty ${qty}, and the ticket closed at time exit.`
  );
}

/** Card row at the current 10-lot NIFTY slot. Prices and the IST date stay on the source fill. */
export function pooledRowToTrade(row, { qty = SLOT_QTY } = {}) {
  if (!row) return null;
  const lots = qty / NIFTY_LOT;
  const entry = row.ask_in;
  const exitPx = row.bid_out;
  const pts = exitPx - entry;
  const gross = Math.round(pts * qty * 100) / 100;
  const recordedQty = Number(row.lots) * NIFTY_LOT;
  let net;
  let charges;
  if (recordedQty === qty) {
    net = row.net;
    charges = Math.round((gross - net) * 100) / 100;
  } else {
    charges = estRoundTripCharges(entry, exitPx, qty);
    net = Math.round((gross - charges) * 100) / 100;
  }
  const sid = canonicalSlotId(row.rule);
  const opened = ist(row.date, row.in);
  const closed = ist(row.date, row.out);
  const won = net > 0;
  return {
    trade_id: `pooled-${row.date}-${sid}-${row.und}-${row.side}-${String(row.in).replace(":", "")}`,
    book_id: sid,
    strategy_id: sid,
    rule: row.rule,
    journal_tag: "SLOT-CONTROL",
    underlying: row.und,
    side: row.side,
    status: "CLOSED",
    exit_reason: "TIME",
    sl_hit: false,
    target_hit: false,
    filled: true,
    entry,
    limit_price: entry,
    exit: exitPx,
    last_ltp: exitPx,
    seen_high: Math.max(entry, exitPx),
    seen_low: Math.min(entry, exitPx),
    lots,
    lot_size: NIFTY_LOT,
    qty,
    source_lots: row.lots,
    source_net: row.net,
    gross_pnl_inr: gross,
    charges_inr: charges,
    realized_pnl_inr: net,
    opened_ist: opened,
    closed_ist: closed,
    opened_ts: ts(row.date, row.in),
    closed_ts: ts(row.date, row.out),
    last_updated_ist: closed,
    why_plain: whyFor(row.side),
    llm_explanation: explain(row, qty),
    market_type: row.side === "CE" ? "trend up" : "trend down",
    source: "pooled_trades_1x.csv",
    paper_slot: true,
    shadow: false,
    promote: false,
    execution: "refused",
    result: won ? "SUCCESS" : "LOSS",
  };
}

export function cardTrades(rows, { qty = SLOT_QTY } = {}) {
  return {
    win: pooledRowToTrade(findPooledRow(rows, CARD_WIN), { qty }),
    loss: pooledRowToTrade(findPooledRow(rows, CARD_LOSS), { qty }),
  };
}

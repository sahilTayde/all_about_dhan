#!/usr/bin/env node
import assert from "node:assert/strict";
import {
  PAPER_SLOT_IDS,
  avgWinLoss,
  buildStrategyCards,
  equityCurve,
  maxDrawdown,
  slotBadge,
  sortStrategyCards,
  todayTimeline,
  winVsRandom,
} from "../src/lib/strategyBoard.js";

assert.equal(PAPER_SLOT_IDS.length, 5);
assert.equal(slotBadge({ nFilled: 2, openCount: 1, shadow: false }), "TRADE");
assert.equal(slotBadge({ nFilled: 4, openCount: 0, shadow: false }), "WATCH");
assert.equal(slotBadge({ nFilled: 0, openCount: 0, shadow: true }), "WATCH");
assert.equal(slotBadge({ nFilled: 0, openCount: 0, shadow: false }), "DROP");
assert.equal(winVsRandom({ win_rate_net_pct: 40, random_win_pct: 32 }), 8);
assert.equal(winVsRandom({ win_rate_net_pct: 40 }), null);

const curve = equityCurve([
  { closed_ts: 2, realized_pnl_inr: 100 },
  { closed_ts: 1, realized_pnl_inr: -40 },
  { closed_ts: 3, realized_pnl_inr: -20 },
]);
assert.deepEqual(curve.map((p) => p.v), [-40, 60, 40]);
assert.equal(maxDrawdown(curve), 20);
assert.equal(maxDrawdown([]), null);

const avg = avgWinLoss([
  { realized_pnl_inr: 100 },
  { realized_pnl_inr: 50 },
  { realized_pnl_inr: -30 },
]);
assert.equal(avg.avgWin, 75);
assert.equal(avg.avgLoss, -30);

const board = {
  session_ist_date: "2026-01-15",
  book_rank: [
    { book_id: "MIX-DEFAULT-BUY", kind: "DESK", n_filled: 2, n_wins: 1, sum_pnl_inr: 60, win_rate_net_pct: 50 },
  ],
  closed_trades: [
    { book_id: "MIX-DEFAULT-BUY", trade_id: "a", realized_pnl_inr: 100, closed_ts: 10, closed_ist: "2026-01-15T10:00:00+05:30", opened_ist: "2026-01-15T09:40:00+05:30" },
    { book_id: "MIX-DEFAULT-BUY", trade_id: "b", realized_pnl_inr: -40, closed_ts: 20, closed_ist: "2026-01-15T11:00:00+05:30", opened_ist: "2026-01-15T10:40:00+05:30" },
    { book_id: "MIX-DEFAULT-BUY", trade_id: "c", realized_pnl_inr: 12, closed_ts: 30, closed_ist: "2026-01-15T12:00:00+05:30", opened_ist: "2026-01-15T11:40:00+05:30", shadow: true },
  ],
  open_trades: [{ book_id: "MIX-DEFAULT-BUY", trade_id: "open", status: "OPEN" }],
};
const cards = buildStrategyCards(board, { uniqueClosed: board.closed_trades, uniqueOpen: board.open_trades });
assert.ok(cards.length >= 6);
const desk = cards.find((c) => c.id === "MIX-DEFAULT-BUY");
const shadow = cards.find((c) => c.id === "MIX-DEFAULT-BUY·SHADOW");
assert.equal(desk.badge, "TRADE");
assert.equal(desk.nFilled, 2);
assert.equal(shadow.shadow, true);
assert.equal(shadow.badge, "WATCH");
assert.equal(shadow.nFilled, 1);
const empty = cards.find((c) => c.id === "MIX-ML-LOGIT");
assert.equal(empty.badge, "DROP");
assert.equal(empty.winPct, null);

const byName = sortStrategyCards(cards, "name", "asc");
assert.ok(String(byName[0].bookId) <= String(byName[1].bookId));
const tape = todayTimeline(board.open_trades, board.closed_trades, "2026-01-15");
assert.ok(tape.length >= 3);

console.log("PASS strategy_board_unit slots + shadow + empty + sort");

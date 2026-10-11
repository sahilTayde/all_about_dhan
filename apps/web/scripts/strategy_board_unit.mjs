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
import { pathProgress, pnlPct } from "../src/lib/paperBoard.js";

assert.equal(PAPER_SLOT_IDS.length, 5);
assert.equal(slotBadge({ nFilled: 2, net: 60, vsRandom: 8 }), "WATCH");
assert.equal(slotBadge({ nFilled: 30, net: 100, vsRandom: 8 }), "TRADE");
assert.equal(slotBadge({ nFilled: 30, net: -40, vsRandom: 2 }), "DROP");
assert.equal(slotBadge({ nFilled: 30, net: 100, vsRandom: null }), "WATCH");
assert.equal(slotBadge({ nFilled: 0 }), "WATCH");
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

const prog = pathProgress(140, 145, 132, 150);
assert.ok(prog && prog.coveredPct > 0);
assert.equal(pnlPct(100, 110), 10);

const SLOT = "R01_PDIV_5_ALL_H20";
const board = {
  session_ist_date: "2026-01-15",
  shadow_scoreboard: { [SLOT]: { random_win_pct: 30 } },
  book_rank: [
    { book_id: SLOT, kind: "PAPER", n_filled: 2, n_wins: 1, sum_pnl_inr: 60, win_rate_net_pct: 50, random_win_pct: 30 },
  ],
  closed_trades: [
    { strategy_id: SLOT, book_id: "MIX-DEFAULT-BUY", trade_id: "a", realized_pnl_inr: 100, closed_ts: 10, closed_ist: "2026-01-15T10:00:00+05:30", opened_ist: "2026-01-15T09:40:00+05:30" },
    { strategy_id: SLOT, book_id: "MIX-DEFAULT-BUY", trade_id: "b", realized_pnl_inr: -40, closed_ts: 20, closed_ist: "2026-01-15T11:00:00+05:30", opened_ist: "2026-01-15T10:40:00+05:30" },
    { strategy_id: SLOT, book_id: "MIX-DEFAULT-BUY", trade_id: "c", realized_pnl_inr: 12, closed_ts: 30, closed_ist: "2026-01-15T12:00:00+05:30", opened_ist: "2026-01-15T11:40:00+05:30", shadow: true },
  ],
  open_trades: [{ strategy_id: SLOT, book_id: "MIX-DEFAULT-BUY", trade_id: "open", status: "OPEN" }],
};
const cards = buildStrategyCards(board, { uniqueClosed: board.closed_trades, uniqueOpen: board.open_trades });
assert.equal(cards.length, 10);
assert.equal(PAPER_SLOT_IDS[0], SLOT);
const desk = cards.find((c) => c.id === SLOT);
const shadow = cards.find((c) => c.id === `${SLOT}·SHADOW`);
assert.equal(desk.name, "Premium divergence");
assert.equal(desk.bookId, SLOT);
assert.equal(desk.badge, "WATCH");
assert.equal(desk.nFilled, 2);
assert.ok(desk.vsRandom != null);
assert.equal(shadow.shadow, true);
assert.equal(shadow.name, "Premium divergence · shadow");
assert.equal(shadow.badge, "WATCH");
assert.equal(shadow.nFilled, 1);
const empty = cards.find((c) => c.id === "R07_MOM3_TREND");
assert.equal(empty.name, "Momentum");
assert.equal(empty.badge, "WATCH");
assert.equal(empty.winPct, null);
assert.ok(cards.every((c) => !String(c.name).startsWith("MIX-")));

const byName = sortStrategyCards(cards, "name", "asc");
assert.ok(String(byName[0].name) <= String(byName[1].name));
const tape = todayTimeline(board.open_trades, board.closed_trades, "2026-01-15");
assert.ok(tape.length >= 3);

console.log("PASS strategy_board_unit slots + shadow + empty + sort");

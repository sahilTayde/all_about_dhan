import assert from "node:assert/strict";
import {
  closedStateLabel,
  pathInfo,
  plainWhy,
  ticketState,
  tradeNow,
} from "../src/lib/paperBoard.js";
import { strategyName } from "../src/lib/tradePipeline.js";

const stopHit = {
  trade_id: "t-stop",
  underlying: "NIFTY",
  side: "PE",
  atm_strike: 23300,
  strategy_id: "R01_PDIV_5_ALL_H20",
  book_id: "MIX-DEFAULT-BUY",
  books: ["MIX-DEFAULT-BUY"],
  status: "CLOSED",
  exit_reason: "STOP",
  sl_hit: true,
  entry: 167.3,
  exit: 157.26,
  stop: 157.26,
  target: 177.3,
  lots: 10,
  lot_size: 65,
  qty: 650,
  realized_pnl_inr: -6800.12,
  seen_high: 167.3,
  seen_low: 157.26,
  opened_ist: "2026-10-09T10:20:00+05:30",
  closed_ist: "2026-10-09T10:28:00+05:30",
  opened_ts: Date.parse("2026-10-09T10:20:00+05:30") / 1000,
  justification:
    "NIFTY buy PE ITM strike 23300.0 (ITM_100); why_now=PE: dump / PE bin / PE short-cover (CE still allowed when CE strength prints); PAPER only.",
};

assert.equal(strategyName(stopHit), "Premium divergence");
assert.equal(closedStateLabel(stopHit), "Closed: stop hit");
assert.equal(ticketState(stopHit).label, "Closed: stop hit");
assert.ok(!/CANCEL|MIX-|DEAD/i.test(ticketState(stopHit).label));
assert.equal(plainWhy(stopHit), "The index was falling, so the desk bought a put.");
assert.ok(!/bin|dump|short-cover|MIX-/i.test(plainWhy(stopHit)));

const n = tradeNow(stopHit);
assert.equal(n.closed, true);
assert.equal(n.qty, 650);
assert.equal(n.ltp, 157.26);
assert.ok(Math.abs(n.pts - (157.26 - 167.3)) < 1e-9);
assert.equal(n.netInr, -6800.12);
assert.equal(n.inr, -6800.12);
assert.equal(n.mfe, 0);
assert.ok(n.mae < 0);

const path = pathInfo(stopHit);
assert.equal(path.closed, true);
assert.equal(path.markLabel, "exit");
assert.equal(path.last, 157.26);

assert.equal(closedStateLabel({ exit_reason: "TARGET", target_hit: true, exit: 180 }), "Closed: target hit");
assert.equal(closedStateLabel({ exit_reason: "TIME", exit: 170 }), "Closed: time exit");
assert.equal(closedStateLabel({ exit_reason: "CANCEL_AGAINST", status: "CLOSED_CANCEL", exit: 161 }), "Closed: time exit");
assert.ok(!/CLOSED \(/.test(ticketState({ ...stopHit, exit_reason: "CANCEL_AGAINST", status: "CLOSED_CANCEL" }).label));

const open = { ...stopHit, status: "OPEN_PAPER", exit: null, closed_ist: null, last_ltp: 169.1 };
assert.equal(ticketState(open).label, "IN PROGRESS");
assert.equal(tradeNow(open).closed, false);
assert.equal(pathInfo(open).markLabel, "now");

console.log("paper_board_unit: ok");

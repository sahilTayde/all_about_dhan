#!/usr/bin/env node
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  CARD_LOSS,
  CARD_WIN,
  SLOT_QTY,
  cardTrades,
  parsePooledCsv,
} from "../src/lib/pooledTrades.js";
import { pathInfo, ticketState } from "../src/lib/paperBoard.js";
import { strategyName } from "../src/lib/tradePipeline.js";

const csv = readFileSync(
  resolve(dirname(fileURLToPath(import.meta.url)), "../public/mock/pooled_trades_1x.csv"),
  "utf8",
);
const rows = parsePooledCsv(csv);
assert.ok(rows.length >= 2);
assert.ok(rows.every((r) => r.date >= "2026-09-29" && r.date <= "2026-10-09"));
assert.ok(!rows.some((r) => r.date === "2026-09-25"));

const { win, loss } = cardTrades(rows);
assert.ok(win && loss);
assert.equal(win.opened_ist.slice(0, 10), CARD_WIN.date);
assert.equal(loss.opened_ist.slice(0, 10), CARD_LOSS.date);
assert.equal(win.entry, 127.25);
assert.equal(win.exit, 134.35);
assert.equal(win.qty, SLOT_QTY);
assert.equal(win.lots, 10);
assert.equal(win.realized_pnl_inr, 4360);
assert.equal(win.source_lots, 10);
assert.equal(strategyName(win), "Premium divergence");
assert.equal(ticketState(win).label, "Closed: time exit");
assert.equal(win.atm_strike, undefined);
assert.equal(win.spot_at_entry, undefined);

assert.equal(loss.entry, 138);
assert.equal(loss.exit, 132.7);
assert.equal(loss.qty, SLOT_QTY);
assert.equal(loss.lots, 10);
assert.equal(loss.source_lots, 28);
assert.equal(loss.source_net, -10311);
assert.ok(loss.realized_pnl_inr < 0);
assert.ok(Math.abs(loss.realized_pnl_inr - ((132.7 - 138) * 650 - loss.charges_inr)) < 0.02);
assert.equal(strategyName(loss), "Premium divergence");
assert.equal(ticketState(loss).label, "Closed: time exit");
assert.equal(loss.atm_strike, undefined);

const winPath = pathInfo(win);
assert.equal(winPath.entryPct, 0);
assert.equal(winPath.pct, 1);
assert.equal(winPath.markLabel, "exit");
const lossPath = pathInfo(loss);
assert.equal(lossPath.entryPct, 1);
assert.equal(lossPath.pct, 0);

assert.equal(strategyName({ strategy_id: "R07_MOM_3_0.0005_TREND_H20" }), "Momentum");
assert.ok(!/MIX-|23300|23128|167\.3|157\.26|1625/.test(JSON.stringify({ win, loss })));

console.log("pooled_trades_unit: ok");

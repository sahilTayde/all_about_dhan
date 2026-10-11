#!/usr/bin/env node
import assert from "node:assert/strict";
import { hasPremiumChart, premiumMarks } from "../src/lib/tradeMarks.js";

const empty = premiumMarks(null);
assert.equal(hasPremiumChart(empty), false);

const open = premiumMarks({
  entry: 140.5,
  last_ltp: 138.2,
  opened_ts: 1_700_000_000,
  last_updated_ts: 1_700_000_400,
  seen_high: 143.1,
  seen_low: 136.4,
  stop: 132,
  target: 149,
  market_kind_open: "CHOPPY",
});
assert.equal(hasPremiumChart(open), true);
assert.equal(open.points[0].label, "entry");
assert.equal(open.points[0].value, 140.5);
assert.ok(open.lines.some((l) => l.id === "entry" && l.value === 140.5));
assert.equal(open.marketKind, "CHOPPY");

const onePoint = premiumMarks({ entry: 100, opened_ts: 10 });
assert.equal(hasPremiumChart(onePoint), false);

const path = premiumMarks({
  premium_path: [
    { t: 1_700_000_000, v: 120, label: "entry" },
    { t: 1_700_000_200, v: 128, label: "exit" },
  ],
  exit_reason: "TARGET",
});
assert.equal(path.points.length, 2);
assert.equal(path.reason, "TARGET");

console.log("PASS trade_marks_unit known marks only");

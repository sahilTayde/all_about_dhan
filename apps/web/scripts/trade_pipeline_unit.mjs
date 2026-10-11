#!/usr/bin/env node
import assert from "node:assert/strict";
import {
  PIPE_STAGES,
  buildLane,
  buildPipelines,
  fromJournal,
  leakMix,
  pipelineText,
  skipWhoWhy,
  strategyName,
} from "../src/lib/tradePipeline.js";

assert.equal(PIPE_STAGES.length, 7);
assert.deepEqual(
  PIPE_STAGES.map((s) => s.id),
  ["analyst", "desk", "overlay", "boss", "imm", "live", "exit"],
);

const coil = skipWhoWhy({ reason: "OVERLAY_COIL", why: "coil market", action: "SKIP" });
assert.equal(coil.who, "Overlay");
assert.equal(coil.why, "Overlay skipped: coil market");

const late = skipWhoWhy({ reason: "NO_NEW_AFTER_1516", why: "No NEW after 15:16 IST" });
assert.equal(late.why, "Overlay skipped: too late in the session");

assert.equal(strategyName({ strategy_id: "R01_PDIV_5_ALL_H20", book_id: "MIX-DEFAULT-BUY" }), "Premium divergence");
assert.equal(strategyName({ book_id: "MIX-DEFAULT-BUY" }), "");

const live = buildLane("NIFTY", {
  open: [
    {
      trade_id: "t-n",
      underlying: "NIFTY",
      side: "PE",
      atm_strike: 20350,
      strategy_id: "R01_PDIV_5_ALL_H20",
      book_id: "MIX-DEFAULT-BUY",
      opened_ist: "2026-01-15T10:00:00+05:30",
      last_updated_ist: "2026-01-15T10:12:00+05:30",
      entry: 140.5,
      lots: 5,
      index_regime: "TREND",
    },
  ],
  traces: {
    "t-n": {
      steps: [
        { id: "analysts", title: "Analysts", status: "OK", decided: "agreed: MIX-SYNTH-A, MIX-SYNTH-B", fields: { book: "MIX-DEFAULT-BUY" } },
        { id: "boss", title: "Boss", status: "OK", decided: "BUY PE via MIX-DEFAULT-BUY", fields: {} },
        { id: "risk", title: "Risk", status: "NO_DATA", fields: {} },
        { id: "broker", title: "Broker", status: "PAPER", decided: "Paper only — no broker order", fields: { execution: "refused" } },
      ],
    },
  },
});
assert.equal(live.kind, "live");
assert.equal(live.name, "Premium divergence");
assert.equal(live.stages.find((s) => s.id === "live").state, "active");
assert.equal(live.stages.find((s) => s.id === "exit").state, "waiting");
assert.equal(live.stages.find((s) => s.id === "overlay").state, "done");
assert.ok(live.stages.find((s) => s.id === "imm").at?.text);
assert.ok(!leakMix(JSON.stringify(live)));

const skipped = buildLane("SENSEX", {
  skips: [{ underlying: "SENSEX", side: "PE", reason: "OVERLAY_COIL", why: "coil market", book_id: "MIX-DEFAULT-BUY" }],
});
assert.equal(skipped.kind, "skipped");
const overlay = skipped.stages.find((s) => s.id === "overlay");
assert.equal(overlay.state, "blocked");
assert.equal(overlay.who, "Overlay");
assert.equal(overlay.why, "Overlay skipped: coil market");
assert.equal(skipped.stages.find((s) => s.id === "imm").state, "waiting");
assert.ok(!leakMix(JSON.stringify(skipped)));

const empty = buildLane("SENSEX", {});
assert.equal(empty.kind, "empty");
assert.ok(empty.stages.every((s) => s.state === "waiting" && s.why === "waiting"));

const model = buildPipelines(
  {
    session_ist_date: "2026-01-15",
    seen_not_taken: {
      skipped_latest: [{ underlying: "SENSEX", side: "PE", reason: "OVERLAY_COIL", why: "coil market", last_updated_ist: "2026-01-15T10:05:00+05:30" }],
    },
  },
  {
    uniqueOpen: [
      {
        trade_id: "t-n",
        underlying: "NIFTY",
        side: "PE",
        atm_strike: 20350,
        strategy_id: "R01_PDIV_5_ALL_H20",
        opened_ist: "2026-01-15T10:00:00+05:30",
      },
    ],
    uniqueClosed: [
      {
        trade_id: "t-c",
        underlying: "NIFTY",
        side: "CE",
        atm_strike: 20200,
        strategy_id: "R07_MOM3_TREND",
        book_id: "MIX-DEFAULT-BUY",
        opened_ist: "2026-01-15T09:40:00+05:30",
        closed_ist: "2026-01-15T09:48:00+05:30",
        exit: 118,
        exit_reason: "TARGET",
      },
    ],
  },
);
assert.equal(model.lanes.length, 2);
assert.equal(model.lanes[0].kind, "live");
assert.equal(model.lanes[1].kind, "skipped");
assert.ok(model.history.some((h) => h.state === "blocked" && /coil market/.test(h.why)));
assert.ok(model.history.some((h) => h.state === "done" && h.name === "Momentum"));
assert.ok(!leakMix(pipelineText(model)));
assert.ok(!/MIX-/.test(pipelineText(model)));

const journal = [
  {
    ts_ist: "2026-01-15T10:00:00+05:30",
    underlying: "NIFTY",
    candidate_id: "t-n",
    stage: "overlay",
    actor: "Overlay",
    decision: "pass",
    reason: "Market TREND",
    inputs: { day_type: "TREND", vix: 12.4, premium: 140.5, sl: 132, target: 149 },
  },
  {
    ts_ist: "2026-01-15T10:00:00+05:30",
    underlying: "NIFTY",
    candidate_id: "t-n",
    stage: "in_trade",
    actor: "Desk",
    decision: "pass",
    reason: "Trade in progress",
  },
];
const fromJ = fromJournal(journal);
assert.equal(fromJ.overlay.state, "done");
assert.equal(fromJ.live.state, "active");
const wired = buildLane("NIFTY", {
  open: [{ trade_id: "t-n", underlying: "NIFTY", side: "PE", opened_ist: "2026-01-15T10:00:00+05:30" }],
  journal,
});
assert.equal(wired.stages.find((s) => s.id === "overlay").why, "Market TREND");
assert.ok(!leakMix(JSON.stringify(wired)));

console.log("trade_pipeline_unit: ok");

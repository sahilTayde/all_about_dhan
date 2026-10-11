#!/usr/bin/env node
import assert from "node:assert/strict";
import {
  PIPE_STAGES,
  buildLane,
  buildPipelines,
  engineCode,
  fromJournal,
  leakMix,
  pipelineText,
  plainMarketType,
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
assert.equal(coil.why, "Skipped: coil market");
assert.equal(coil.rule, "skip coil market");
assert.equal(coil.code, "OVERLAY_COIL");

const late = skipWhoWhy({ reason: "NO_NEW_AFTER_1516", why: "No NEW after 15:16 IST" });
assert.equal(late.why, "Skipped: too late in the session");

assert.equal(strategyName({ strategy_id: "R01_PDIV_5_ALL_H20", book_id: "MIX-DEFAULT-BUY" }), "Premium divergence");
assert.equal(strategyName({ book_id: "MIX-DEFAULT-BUY" }), "");
assert.equal(strategyName({ strategy_id: "R07_MOM_3_0.0005_TREND_H20" }), "Momentum");

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
assert.equal(overlay.why, "Skipped: coil market");
assert.equal(overlay.rule, "skip coil market");
assert.equal(overlay.code, "OVERLAY_COIL");
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
        exit_reason: "CANCEL_NO_PROGRESS",
        realized_pnl_inr: -1840.5,
      },
    ],
  },
);
assert.equal(model.lanes.length, 2);
assert.equal(model.lanes[0].kind, "live");
assert.equal(model.lanes[1].kind, "skipped");
assert.ok(model.history.some((h) => h.state === "blocked" && h.why === "Skipped: coil market"));
assert.ok(model.history.some((h) => h.state === "done" && h.why === "Exited: no progress" && h.pnl === -1840.5 && h.code === "CANCEL_NO_PROGRESS"));
assert.ok(!leakMix(pipelineText(model)));
assert.ok(!/MIX-/.test(pipelineText(model)));
assert.ok(!/CANCEL_NO_PROGRESS|OVERLAY_COIL/.test(pipelineText(model)));
assert.ok(!/Overlay: Overlay skipped/.test(pipelineText(model)));

const inverted = buildLane("SENSEX", {
  open: [
    {
      trade_id: "t-sx",
      underlying: "SENSEX",
      side: "CE",
      atm_strike: 81200,
      opened_ist: "2026-01-15T15:38:00+05:30",
      last_updated_ist: "2026-01-15T15:19:00+05:30",
      entry: 210.4,
    },
  ],
});
const immAt = inverted.stages.find((s) => s.id === "imm").at;
const liveAt = inverted.stages.find((s) => s.id === "live").at;
assert.ok(immAt?.ms != null && liveAt?.ms != null);
assert.ok(liveAt.ms >= immAt.ms, `live ${liveAt.text} must not precede IMM ${immAt.text}`);

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

assert.equal(engineCode("STOP"), "STOP");
assert.equal(engineCode("CANCEL_AGAINST"), "CANCEL_AGAINST");
assert.equal(engineCode("EXIT_STOP"), "STOP");
assert.equal(
  engineCode("The desk bought the NIFTY 23300 put because the index was falling. Premium then dropped to the stop, so the ticket closed."),
  null,
);

assert.equal(plainMarketType("TREND_UP"), "trend up");
assert.equal(plainMarketType("high-VIX"), "high-VIX");
assert.equal(plainMarketType("MOON"), "");

const explained = buildLane("NIFTY", {
  open: [
    {
      trade_id: "t-n",
      underlying: "NIFTY",
      side: "CE",
      opened_ist: "2026-01-15T10:00:00+05:30",
      llm_explanation: "The desk bought the NIFTY call because the index was rising. Premium held the open range.",
      market_type: "trend up",
    },
  ],
  journal: [
    {
      ts_ist: "2026-01-15T10:00:00+05:30",
      underlying: "NIFTY",
      candidate_id: "t-n",
      trade_id: "t-n",
      stage: "llm_explain",
      actor: "LLM judge",
      decision: "pass",
      reason: "The desk bought the NIFTY call because the index was rising. Premium held the open range.",
      inputs: { market_type: "trend up", side: "CE" },
    },
  ],
});
const analyst = explained.stages.find((s) => s.id === "analyst");
assert.equal(analyst.state, "done");
assert.match(analyst.why, /index was rising/);
assert.equal(analyst.inputs.market_type, "trend up");
assert.ok(!/TREND_UP|llm_explain|MIX-/.test(JSON.stringify(explained)));

const stopExplain =
  "The desk bought the NIFTY 23300 put because the index was falling. Premium then dropped to the stop, so the ticket closed.";
const explainedClosed = buildLane("NIFTY", {
  closed: [
    {
      trade_id: "t-stop",
      underlying: "NIFTY",
      side: "PE",
      atm_strike: 23300,
      strategy_id: "R01_PDIV_5_ALL_H20",
      opened_ist: "2026-10-09T10:20:00+05:30",
      closed_ist: "2026-10-09T10:28:00+05:30",
      exit: 157.26,
      exit_reason: "STOP",
      llm_explanation: stopExplain,
      market_type: "trend down",
    },
  ],
  journal: [
    {
      ts_ist: "2026-10-09T10:20:00+05:30",
      underlying: "NIFTY",
      candidate_id: "t-stop",
      trade_id: "t-stop",
      stage: "llm_explain",
      actor: "LLM judge",
      decision: "pass",
      reason: stopExplain,
      inputs: { market_type: "trend down", side: "PE", explanation: stopExplain },
    },
  ],
});
const analystClosed = explainedClosed.stages.find((s) => s.id === "analyst");
assert.match(analystClosed.why, /index was falling/);
assert.ok(!/Stop hit/i.test(analystClosed.why));
assert.ok(!analystClosed.rule);
assert.equal(explainedClosed.stages.find((s) => s.id === "exit").why, "Stop hit");

console.log("trade_pipeline_unit: ok");

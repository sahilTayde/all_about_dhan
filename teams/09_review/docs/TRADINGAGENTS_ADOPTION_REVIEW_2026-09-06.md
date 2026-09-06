# TRADINGAGENTS adoption review — 2026-09-06

**Team:** 09_review
**Layer:** `HYPOTHESIS`
**Gate:** **not RESEARCH_READY_FOR_PROGRAMMING**
**Verdict:** `ADOPT_SKELETON_OK_WITH_GAPS`
**Reviewer:** local_rule_fallback
**OpenAI used:** `False` (key_present=False)

EXTERNAL reference: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).
Plan: [`ADOPT_TRADINGAGENTS.md`](../../00_orchestrator/docs/ADOPT_TRADINGAGENTS.md).

This is **NOTES_ONLY** / design verification — **not** a five-pass product pass.

## Accept

- Additive packages/trading_agents_india does not rewrite monorepo or KEEP_ALL catalog
- News/MACRO_EVENT mapped to ticket HOLD aligned with EVENT_MEMORY / SIGNAL_FUSION
- Separate SQLite KB preserves transcripts.sqlite
- Structured CE/PE/HOLD + risk veto matches paper-only mandate
- TradingAgents roles mapped onto 00/04/05/06 without inventing STRAT-015+

## Reject / watch

- Do not import US equity fundamentals / StockTwits as India SOURCE_FACT
- Do not claim CONFIRMED/IN-PROGRESS from agent loop alone (v0 caps at EARLY)
- Do not treat Docs Auditor PASS or this review as product gate
- LangGraph full port deferred — sequential pipeline is enough for paper dry-run

## DATA_INSUFFICIENT / UNKNOWN

- OPENAI_API_KEY not present in workspace .env at adopt time — live frontier call skipped
- EVENT_MEMORY analogs empty
- Live Dhan chain optional; fixtures used for dry-run
- India sentiment feed not wired

## Must keep

- KEEP_ALL STRAT-001–014
- No live Dhan orders / no /alerts/orders
- Layers SOURCE_FACT / VALIDATION / HYPOTHESIS
- Apache-2.0 citation for TradingAgents

## Fallback note

Frontier OpenAI review unavailable; recorded careful local verification against BOSS_AGENT / EVENT_MEMORY / KEEP_ALL constraints.

## Raw JSON

```json
{
  "verdict": "ADOPT_SKELETON_OK_WITH_GAPS",
  "openai_used": false,
  "layer": "HYPOTHESIS",
  "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
  "accept": [
    "Additive packages/trading_agents_india does not rewrite monorepo or KEEP_ALL catalog",
    "News/MACRO_EVENT mapped to ticket HOLD aligned with EVENT_MEMORY / SIGNAL_FUSION",
    "Separate SQLite KB preserves transcripts.sqlite",
    "Structured CE/PE/HOLD + risk veto matches paper-only mandate",
    "TradingAgents roles mapped onto 00/04/05/06 without inventing STRAT-015+"
  ],
  "reject_or_watch": [
    "Do not import US equity fundamentals / StockTwits as India SOURCE_FACT",
    "Do not claim CONFIRMED/IN-PROGRESS from agent loop alone (v0 caps at EARLY)",
    "Do not treat Docs Auditor PASS or this review as product gate",
    "LangGraph full port deferred — sequential pipeline is enough for paper dry-run"
  ],
  "data_insufficient": [
    "OPENAI_API_KEY not present in workspace .env at adopt time — live frontier call skipped",
    "EVENT_MEMORY analogs empty",
    "Live Dhan chain optional; fixtures used for dry-run",
    "India sentiment feed not wired"
  ],
  "must_keep": [
    "KEEP_ALL STRAT-001–014",
    "No live Dhan orders / no /alerts/orders",
    "Layers SOURCE_FACT / VALIDATION / HYPOTHESIS",
    "Apache-2.0 citation for TradingAgents"
  ],
  "reviewer": "local_rule_fallback",
  "note": "Frontier OpenAI review unavailable; recorded careful local verification against BOSS_AGENT / EVENT_MEMORY / KEEP_ALL constraints."
}
```


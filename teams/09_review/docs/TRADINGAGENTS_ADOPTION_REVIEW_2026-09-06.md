# TRADINGAGENTS adoption review — 2026-09-06

**Team:** 09_review
**Layer:** `HYPOTHESIS`
**Gate:** **not RESEARCH_READY_FOR_PROGRAMMING**
**Verdict:** `strict`
**Reviewer:** openai:gpt-4o
**OpenAI used:** `True` (key_present=True)

EXTERNAL reference: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).
Plan: [`ADOPT_TRADINGAGENTS.md`](../../00_orchestrator/docs/ADOPT_TRADINGAGENTS.md).

This is **NOTES_ONLY** / design verification — **not** a five-pass product pass.

## Accept

- Role graph: analysts → bull/bear → boss → trader → risk triad → final
- Structured outputs (lean + reasons + veto)
- News + sentiment as inputs, not silent
- Risk debate can veto trader
- Separate memory store
- Apache-2.0 citation

## Reject / watch

- Live broker execution / order APIs
- US equity Buy/Sell as customer ticket
- Fundamentals analyst as NIFTY alpha
- StockTwits / Reddit as SOURCE_FACT
- yfinance / Alpha Vantage as Dhan truth
- MACD/RSI as customer entry
- Deleting STRAT-001–014 / inventing STRAT-015+
- Claiming win rates / RESEARCH_READY
- Overwriting transcripts.sqlite
- Mass LangGraph rewrite of monorepo

## DATA_INSUFFICIENT / UNKNOWN

- India sentiment feed
- EVENT_MEMORY analogs empty
- Live chain without tokens
- (Superseded) OpenAI key absence at first adopt pass — key now present and validated; see Frontier pass below

## Frontier pass (validated key)

- `OPENAI_API_KEY`: present (non-empty, length bucket `len>=20`); value never logged
- Model: `gpt-4o` (`openai:gpt-4o` reviewer)
- `python -m trading_agents_india review-plan`: **pass** (`openai_used=true`)
- `python -m trading_agents_india session --dry-run --use-llm`: **pass** (`openai_used=true`, execution refused, gate remains **not RESEARCH_READY_FOR_PROGRAMMING**)
- Frontier verdict from review-plan: `strict` (NOTES_ONLY / HYPOTHESIS — not a five-pass product gate)
- Dry-run tickets: NIFTY/BANKNIFTY/SENSEX paper leans only; NEWS_DAY → HOLD; no live Dhan orders
- Parser note: confidence labels (e.g. Low/Medium/High) now coerced to 0–1 so LLM JSON cannot crash the session loop

## Must keep

- KEEP_ALL STRAT-001–014

## Notes

The adoption plan is well-structured with a clear separation of accepted and rejected elements. The focus on maintaining compliance with Apache-2.0 and ensuring no live orders or execution aligns with the desk's guidelines. The plan is cautious about integrating external data sources and emphasizes the importance of maintaining existing strategies and documentation. The data insufficiencies noted are critical for future integration and should be addressed before any progression towards live environments.

## Raw JSON

```json
{
  "verdict": "strict",
  "openai_used": true,
  "reviewer": "openai:gpt-4o",
  "layer": "HYPOTHESIS",
  "gate": "not RESEARCH_READY_FOR_PROGRAMMING",
  "accept": [
    "Role graph: analysts → bull/bear → boss → trader → risk triad → final",
    "Structured outputs (lean + reasons + veto)",
    "News + sentiment as inputs, not silent",
    "Risk debate can veto trader",
    "Separate memory store",
    "Apache-2.0 citation"
  ],
  "reject_or_watch": [
    "Live broker execution / order APIs",
    "US equity Buy/Sell as customer ticket",
    "Fundamentals analyst as NIFTY alpha",
    "StockTwits / Reddit as SOURCE_FACT",
    "yfinance / Alpha Vantage as Dhan truth",
    "MACD/RSI as customer entry",
    "Deleting STRAT-001–014 / inventing STRAT-015+",
    "Claiming win rates / RESEARCH_READY",
    "Overwriting transcripts.sqlite",
    "Mass LangGraph rewrite of monorepo"
  ],
  "data_insufficient": [
    "OpenAI key not visible in workspace .env at adopt time",
    "India sentiment feed",
    "EVENT_MEMORY analogs empty",
    "Live chain without tokens"
  ],
  "must_keep": [
    "KEEP_ALL STRAT-001–014"
  ],
  "notes": "The adoption plan is well-structured with a clear separation of accepted and rejected elements. The focus on maintaining compliance with Apache-2.0 and ensuring no live orders or execution aligns with the desk's guidelines. The plan is cautious about integrating external data sources and emphasizes the importance of maintaining existing strategies and documentation. The data insufficiencies noted are critical for future integration and should be addressed before any progression towards live environments."
}
```


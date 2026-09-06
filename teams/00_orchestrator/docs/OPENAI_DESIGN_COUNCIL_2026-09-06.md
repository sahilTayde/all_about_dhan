# OpenAI Design Council — TradingAgents India deepen (2026-09-06)

**Layer:** `HYPOTHESIS` (design council)
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`
**Mode default:** `PAPER` (LIVE refuses orders)
**OpenAI model used:** `gpt-5.4`
**Key present:** `True` (value never logged)
**UTC:** `2026-09-06T21:58:53+00:00`

EXTERNAL: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).
Plan: [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md).

## Local co-sign (Cursor founder desk)

- ACCEPT: Additive deepen of packages/trading_agents_india only; KEEP_ALL intact
- ACCEPT: mode=PAPER|LIVE with LIVE always refuse orders for now; default PAPER
- ACCEPT: News: desk_intel Moneycontrol RSS + Dhan if API exists; else stub+DI
- ACCEPT: <=3 MIX-TA-* WAITING/PAPER_WATCH EXTERNAL; not promote
- ACCEPT: Separate agent KB; never touch transcripts.sqlite
- ACCEPT: No win rates; gate not RESEARCH_READY
- REJECT: StockTwits/Reddit/CNBC as SOURCE_FACT for NSE index
- REJECT: Live Dhan order placement
- REJECT: Claiming US TradingAgents performance as India edge

## OpenAI council summary

**Verdict:** `APPROVE_WITH_GUARDRAILS`

### Council bullets

- Deepen TradingAgents personas under packages/trading_agents_india as India-options-focused wrappers, not core rewrites.
- Keep existing STRAT-001 to STRAT-014 unchanged; add only persona packaging, routing, aliases, paper session logging, and DI-honest news wiring.
- PAPER remains default everywhere; LIVE path must exist only as explicit refusal/stub until founder+gate is implemented with DhanHQ-only checks.
- Use layered outputs: SOURCE_FACT for fetched broker/news/session facts, VALIDATION for constraints/gates, HYPOTHESIS for persona opinions.
- News is context/hold filter only, not alpha generation; prefer Dhan then Moneycontrol, else mark DATA_INSUFFICIENT.
- Cite TradingAgents provenance/license in package docs and headers: inspired by TradingAgents, Apache-2.0.

### Implement now

- **Create persona package wrappers in packages/trading_agents_india/personas** — Needed to deepen skeleton into callable India-specific personas without altering existing strategy IDs. (`VALIDATION`)
- **Add persona alias map and registry** — Lets TradingAgents names resolve to India desk roles and our internal team naming consistently. (`SOURCE_FACT`)
- **Implement paper session log module** — Required audit trail for PAPER runs, persona votes, gates, and simulated actions without touching transcripts.sqlite. (`SOURCE_FACT`)
- **Add LIVE refusal stub with founder+gate placeholders** — Prevents accidental order flow while preserving future DhanHQ-only integration seam. (`VALIDATION`)
- **Wire DI-honest news adapter with source priority Dhan then Moneycontrol** — Supports context checks while explicitly returning DATA_INSUFFICIENT when coverage is absent. (`SOURCE_FACT`)
- **Add council response schema enforcing SOURCE_FACT/VALIDATION/HYPOTHESIS blocks** — Makes persona outputs auditable and aligned with mandate. (`VALIDATION`)

### Defer

- Any direct order placement implementation beyond stubbed DhanHQ interface.
- Any STRAT-015+ additions or renumbering.
- Backfilled performance claims, win rates, or synthetic scorecards.
- Using news sentiment as standalone entry signal.
- Any write path that overwrites transcripts.sqlite.

### MIX-TA proposals

- `MIX-TA-001` — Option Flow + Risk Gate persona mix for CE/PE buy-first setups. (status=PROPOSED; Bias to NIFTY/BANKNIFTY/SENSEX expiry structure and premium decay awareness.)
- `MIX-TA-002` — Index Regime + Event Risk mix that can only downgrade conviction or hold. (status=PROPOSED; Uses RBI/FOMC/union-budget style event calendar as hold filter for index options.)
- `MIX-TA-003` — Execution Sanity mix for spread, liquidity, and slippage checks in PAPER. (status=PROPOSED; Tailored to DhanHQ option chain fields and Indian market microstructure.)

### PAPER vs LIVE

```json
{
  "default": "PAPER",
  "live_gate": "REFUSE unless founder approval flag AND explicit gate pass are both true; broker path limited to DhanHQ stub only.",
  "live_behavior_now": "Always refuse live execution, return structured refusal with missing gates and suggest PAPER simulation."
}
```

### News wiring

```json
{
  "dhan": "Primary source when available; parse headlines/market updates only into SOURCE_FACT and never direct trade trigger.",
  "moneycontrol": "Fallback source for corroboration/context; if conflicting with Dhan, reduce confidence or hold.",
  "data_insufficient": "If neither source is available/parsable, mark DATA_INSUFFICIENT and continue without news-derived edge."
}
```

### Persona aliases

- **Market Analyst** → Index Regime Analyst (team RAO_REGIME)
- **News Analyst** → India Event/News Filter (team NIV_NEWS)
- **Fundamentals Analyst** → Macro & Policy Context (team MEERA_MACRO)
- **Technical Analyst** → NIFTY/BANKNIFTY Options Technicals (team TARA_TA)
- **Risk Manager** → Premium Risk & Loss Gate (team RISHI_RISK)
- **Trader** → Paper Execution Coordinator (team DEV_EXEC)

### DATA_INSUFFICIENT

- Exact existing skeleton class names/files under packages/trading_agents_india.
- Current transcript logging mechanism besides transcripts.sqlite avoidance requirement.
- Founder approval flag source and gate contract definition.
- Available DhanHQ stub interface signatures in this codebase.
- Whether Moneycontrol ingestion already exists or needs fresh adapter.

### Must not

- Must not modify or remove STRAT-001 to STRAT-014 behavior.
- Must not add STRAT-015 or higher.
- Must not place live orders now.
- Must not claim fake accuracy, win rates, or backtest outcomes.
- Must not overwrite transcripts.sqlite.
- Must not treat news as alpha generator rather than hold/context filter.

## Agreed application plan (merged)

1. Add explicit `mode=PAPER|LIVE` on session; LIVE path stubbed to DhanHQ-only and **always refuses** orders until founder gate.
2. Deepen personas with TradingAgents display names + India mapping; keep sequential graph.
3. News hook: desk_intel Moneycontrol RSS when available; Dhan news only if client API exists; else DI stub — no invented CNBC/StockTwits.
4. Add ≤3 `MIX-TA-*` catalog rows WAITING/PAPER_WATCH (EXTERNAL_RESEARCH); paper-watch alongside DEFAULT; not promote.
5. Persist paper session log to `trading_agents_india.sqlite` only.
6. Update ADOPT + CONTINUE_NEXT_CHAT + 09 note; run docs_auditor.

## Raw council JSON (no secrets)

```json
{
  "verdict": "APPROVE_WITH_GUARDRAILS",
  "council_bullets": [
    "Deepen TradingAgents personas under packages/trading_agents_india as India-options-focused wrappers, not core rewrites.",
    "Keep existing STRAT-001 to STRAT-014 unchanged; add only persona packaging, routing, aliases, paper session logging, and DI-honest news wiring.",
    "PAPER remains default everywhere; LIVE path must exist only as explicit refusal/stub until founder+gate is implemented with DhanHQ-only checks.",
    "Use layered outputs: SOURCE_FACT for fetched broker/news/session facts, VALIDATION for constraints/gates, HYPOTHESIS for persona opinions.",
    "News is context/hold filter only, not alpha generation; prefer Dhan then Moneycontrol, else mark DATA_INSUFFICIENT.",
    "Cite TradingAgents provenance/license in package docs and headers: inspired by TradingAgents, Apache-2.0."
  ],
  "implement_now": [
    {
      "item": "Create persona package wrappers in packages/trading_agents_india/personas",
      "why": "Needed to deepen skeleton into callable India-specific personas without altering existing strategy IDs.",
      "layer": "VALIDATION"
    },
    {
      "item": "Add persona alias map and registry",
      "why": "Lets TradingAgents names resolve to India desk roles and our internal team naming consistently.",
      "layer": "SOURCE_FACT"
    },
    {
      "item": "Implement paper session log module",
      "why": "Required audit trail for PAPER runs, persona votes, gates, and simulated actions without touching transcripts.sqlite.",
      "layer": "SOURCE_FACT"
    },
    {
      "item": "Add LIVE refusal stub with founder+gate placeholders",
      "why": "Prevents accidental order flow while preserving future DhanHQ-only integration seam.",
      "layer": "VALIDATION"
    },
    {
      "item": "Wire DI-honest news adapter with source priority Dhan then Moneycontrol",
      "why": "Supports context checks while explicitly returning DATA_INSUFFICIENT when coverage is absent.",
      "layer": "SOURCE_FACT"
    },
    {
      "item": "Add council response schema enforcing SOURCE_FACT/VALIDATION/HYPOTHESIS blocks",
      "why": "Makes persona outputs auditable and aligned with mandate.",
      "layer": "VALIDATION"
    }
  ],
  "defer": [
    "Any direct order placement implementation beyond stubbed DhanHQ interface.",
    "Any STRAT-015+ additions or renumbering.",
    "Backfilled performance claims, win rates, or synthetic scorecards.",
    "Using news sentiment as standalone entry signal.",
    "Any write path that overwrites transcripts.sqlite."
  ],
  "mix_ta_proposals": [
    {
      "mix_id": "MIX-TA-001",
      "one_liner": "Option Flow + Risk Gate persona mix for CE/PE buy-first setups.",
      "status": "PROPOSED",
      "origin": "New idea compatible with existing STRAT-001 to STRAT-014 routing.",
      "india_note": "Bias to NIFTY/BANKNIFTY/SENSEX expiry structure and premium decay awareness."
    },
    {
      "mix_id": "MIX-TA-002",
      "one_liner": "Index Regime + Event Risk mix that can only downgrade conviction or hold.",
      "status": "PROPOSED",
      "origin": "New wrapper idea; does not create new alpha strategy.",
      "india_note": "Uses RBI/FOMC/union-budget style event calendar as hold filter for index options."
    },
    {
      "mix_id": "MIX-TA-003",
      "one_liner": "Execution Sanity mix for spread, liquidity, and slippage checks in PAPER.",
      "status": "PROPOSED",
      "origin": "Operational wrapper around existing strategies.",
      "india_note": "Tailored to DhanHQ option chain fields and Indian market microstructure."
    }
  ],
  "paper_vs_live": {
    "default": "PAPER",
    "live_gate": "REFUSE unless founder approval flag AND explicit gate pass are both true; broker path limited to DhanHQ stub only.",
    "live_behavior_now": "Always refuse live execution, return structured refusal with missing gates and suggest PAPER simulation."
  },
  "news_wiring": {
    "dhan": "Primary source when available; parse headlines/market updates only into SOURCE_FACT and never direct trade trigger.",
    "moneycontrol": "Fallback source for corroboration/context; if conflicting with Dhan, reduce confidence or hold.",
    "data_insufficient": "If neither source is available/parsable, mark DATA_INSUFFICIENT and continue without news-derived edge."
  },
  "persona_aliases": [
    {
      "trading_agents_name": "Market Analyst",
      "india_role": "Index Regime Analyst",
      "our_team": "RAO_REGIME"
    },
    {
      "trading_agents_name": "News Analyst",
      "india_role": "India Event/News Filter",
      "our_team": "NIV_NEWS"
    },
    {
      "trading_agents_name": "Fundamentals Analyst",
      "india_role": "Macro & Policy Context",
      "our_team": "MEERA_MACRO"
    },
    {
      "trading_agents_name": "Technical Analyst",
      "india_role": "NIFTY/BANKNIFTY Options Technicals",
      "our_team": "TARA_TA"
    },
    {
      "trading_agents_name": "Risk Manager",
      "india_role": "Premium Risk & Loss Gate",
      "our_team": "RISHI_RISK"
    },
    {
      "trading_agents_name": "Trader",
      "india_role": "Paper Execution Coordinator",
      "our_team": "DEV_EXEC"
    }
  ],
  "data_insufficient": [
    "Exact existing skeleton class names/files under packages/trading_agents_india.",
    "Current transcript logging mechanism besides transcripts.sqlite avoidance requirement.",
    "Founder approval flag source and gate contract definition.",
    "Available DhanHQ stub interface signatures in this codebase.",
    "Whether Moneycontrol ingestion already exists or needs fresh adapter."
  ],
  "must_not": [
    "Must not modify or remove STRAT-001 to STRAT-014 behavior.",
    "Must not add STRAT-015 or higher.",
    "Must not place live orders now.",
    "Must not claim fake accuracy, win rates, or backtest outcomes.",
    "Must not overwrite transcripts.sqlite.",
    "Must not treat news as alpha generator rather than hold/context filter."
  ]
}
```


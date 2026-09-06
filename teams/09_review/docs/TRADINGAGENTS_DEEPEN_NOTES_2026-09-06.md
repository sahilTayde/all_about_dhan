# TRADINGAGENTS deepen notes — 2026-09-06

**Team:** 09_review  
**Layer:** `HYPOTHESIS` / **NOTES_ONLY**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Status:** design deepen verified against KEEP_ALL — **not** a five-pass pass

EXTERNAL: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).  
Council: [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](../../00_orchestrator/docs/OPENAI_DESIGN_COUNCIL_2026-09-06.md) (`gpt-5.4`, verdict `APPROVE_WITH_GUARDRAILS`).  
Plan: [`ADOPT_TRADINGAGENTS.md`](../../00_orchestrator/docs/ADOPT_TRADINGAGENTS.md).

## What landed (additive)

- `mode=PAPER|LIVE` with LIVE **always refusing** orders (`mode.py` + optional `dhan_client.ExecutionClient` refuse).
- Persona registry (`personas.py`) mapping TradingAgents names → India desk → teams 00–09.
- News hook (`hooks/news.py`): Dhan news **DI** if no API; Moneycontrol via desk_intel RSS when importable; no CNBC/StockTwits invent.
- MIX §18: `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY` — PAPER_WATCH / WAITING; not default; not promote.
- Session log remains `data/knowledge/trading_agents_india.sqlite` — **does not** touch `transcripts.sqlite`.

## Red-team checks

| Check | Result |
|-------|--------|
| STRAT-001–014 deleted? | No |
| STRAT-015+ invented? | No |
| Live orders placed? | No — refused |
| Win rates claimed? | No |
| US social as SOURCE_FACT? | Rejected |
| Docs Auditor substitute for five-pass? | No |

## Still DATA_INSUFFICIENT

- DhanHQ news API surface in client
- Moneycontrol RSS stability (VERIFY IF STABLE)
- India social sentiment feed
- EVENT_MEMORY analogs empty
- LIVE founder allow + env gate (default off)
- Option premium fill / slippage model for `MIX-TA-EXEC-SANITY`

## Must keep

- KEEP_ALL; paper-only until confidence; DhanHQ-only future live path; layers; Apache-2.0 cite.

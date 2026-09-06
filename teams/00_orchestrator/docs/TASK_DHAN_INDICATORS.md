# TASK — Official Dhan indicators → strategy docs

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01 (catalog + mapping; YouTube KB rows still STUB)  
**Assigned teams:** **01_research** (official docs `SOURCE_FACT`) + **02_phd_math** (VALIDATION map)  
**Also informed:** 04_quant (topic club), 00_orchestrator (persona seed)  
**Owner paths:** `teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`, `teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`, `research/indicator_knowledge_base.md`  
**Status:** DONE for official-API catalog. Transcript indicator KB **not** complete. **No live-trade.** Not `RESEARCH_READY_FOR_PROGRAMMING`.

---

## Requirement

Review **current official Dhan documents** on indicators they defined / added as part of APIs. Club those defs into strategy documents so PhDs can specify testable strategies. Production indicators remain **Dhan-only**. Never invent API fields.

Sources allowed: `https://dhanhq.co/docs/v2/` and children; dhanhq.co / docs.dhanhq.co searches; official Dhan **support** for ScanX/charts (Tier 2 product). Not blogs. `docs.dhan.co` had **no** results (2026-09-01).

---

## Policy

- Education ≠ proof. [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).  
- Three layers stay separate.  
- `UNKNOWN` / `VERIFY BEFORE IMPLEMENTATION` when the page is silent or inconsistent.  
- Conditional Trigger **places orders** — this workspace **must not** call it live. Document only.  
- `packages/dhan-client` was **not** extended with `/alerts/orders` in this ticket (docs-only).

---

## Done

- [x] Fetch current HQ v2: introduction, annexure, conditional-trigger, historical, market-quote, live-market-feed, option-chain, expired-options  
- [x] Search indicator / chart / scanner / Supertrend / RSI on dhanhq.co and docs.dhan.co  
- [x] ScanX + market-alerts + charts support (product, not REST)  
- [x] Compare to `packages/dhan-client` endpoints (no invented paths)  
- [x] Write `teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`  
- [x] Write `research/indicator_knowledge_base.md` + `teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`  
- [x] Pointers in `MASTER_STRATEGY_PLAN.md` and `teams/04_quant/docs/topics/`  
- [x] Desk persona seed: `teams/00_orchestrator/docs/PERSONA.md` + `AGENT.md` subsection  
- [x] This ticket

---

## Finding (one paragraph)

DhanHQ v2 **does** document technical **indicator names** on the **Conditional Trigger** API (`POST /alerts/orders`, annexure `indicatorName`: SMA/EMA set, `RSI_14`, `ATR_14`, BB upper/lower, stochastic, MACD_12/26/HIST). That API evaluates a **condition** and can place orders; it does **not** return indicator time series. It is documented for **Equities and Indices** only. Historical `/charts/*` returns **OHLC + volume** (optional OI) — Supertrend / session VWAP / RSI **series are chart-only** (plus ScanX product screeners). Quote `average_price` is described as day VWAP. **No ScanX REST** on HQ docs.

---

## Assigned follow-up (not this ticket)

| Team | Next |
|------|------|
| 01_research | Fill KB **transcript** columns from verified `@DhanHQ` captions; do not invent Supertrend API fields |
| 02_phd_math | When chart exports or live docs add ST params, re-VERIFY; keep textbooks as VALIDATION only |
| 04_quant | Keep STRAT-* `UNVALIDATED`; cite official vs chart-only in each topic |
| 07_coding | Do **not** implement `/alerts/orders` live. Do not add fake indicator endpoints |

---

## Not this ticket

- Live orders, paper fills, backtests.  
- Implementing TA in `packages/indicators` (still empty by design).  
- Full desk-persona fusion (seed only).  
- Scraping ScanX HTML for hidden filter IDs.

---

## Artifacts

- [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md)  
- [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md)  
- [`research/indicator_knowledge_base.md`](../../../research/indicator_knowledge_base.md)  
- [`teams/00_orchestrator/docs/PERSONA.md`](PERSONA.md)

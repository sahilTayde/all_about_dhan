# Founder requirements trace — departments

**Date:** 2026-09-09  
**Purpose:** preserve the founder's exact intent so agents do not reduce the company to a folder chart.

---

## Summary

| Founder requirement | Owner | Status |
|---------------------|-------|--------|
| Separate coding department | D1 Engineering / 07 | Defined; code work pending |
| RAG so agents do not burn tokens | D1 C3 + 01 | FTS5 exists; API/book ingest expansion pending |
| DB for candles, options, wins/losses, backtests, research references | D1 C2 + 06 | schema standard written; DDL pending |
| Coding docs in one place for juniors/founder | D1 + D3 | `teams/07_coding/docs/` defined |
| API KB + books KB in RAG/vector app | 01 + D1 C3 | FTS5 now; sqlite-vec later |
| ML models to reduce token burn | D1 C4 + D2 | roadmap written; local model pending |
| Burn tokens mostly for pre/post and model sanity | D1/D5 | policy written; cache pending |
| Nightly updates docs/RAG/SQL, reviews, reports, changes code proposals, backtests | D1 C6 + D3 + 06 | policy written; full factory pending |
| Backtesting section | 06 | exists; skill rewritten |
| Boss for each coding section | 07 | C1–C8 defined |
| Confirm material work with OpenAI/Gemini | 00/07/05/09 | counsel docs written |
| Analyst faculty: PhD Math/Algo/Stats/Market/Quant | D2 | roles defined; skills rewritten |
| Analysts propose improvements, not just fails | 02/04/06 | skill templates now require next test |
| Books / expert knowledge by department | D2 + yaml | assigned in `workspace.yaml` |
| Documentation agent | D3/09 | skill rewritten |
| Monitoring PM, founder talks only to PM | D4/00 | spec written; `/pm` pending |
| PM canvas: active agents, services, errors, next action | D4/00 | spec + SLO cards written; UI pending |
| Front desk customer portal | D5/05 + 07 | spec written; code pending |
| Front desk talks to departments and counsel | D5/05 | skill rewritten |
| Front desk learns from mistakes | D5 + nightly + 06 | mistake loop specified; storage pending |
| Kill unrealistic tickets like 150/96/250 NIFTY CE | D5 + 02 | reason codes written; code pending |
| Treat as real signal company, not toy paper trading | 00 | accepted; live orders still refused |

---

## What “good output” now means

### Engineering

Good output is a tested contract: schema/API/UI behavior, failure mode, health card, and founder note. No hidden token dependency in market hours.

### Faculty

Good output is a root cause plus a next backtestable change. “FAIL” alone is not good enough.

### Docs

Good output lets a founder and junior understand what exists, what is MOCK, what is next, and which service is down.

### PM

Good output is a one-minute founder view: Now / Why / Next, active agents, service health, critical errors, and gate.

### Front Desk

Good output is a feasible, fresh, clear customer ticket or an honest HOLD / `DEALER_KILLED`.

---

## Current Biggest Gaps

1. `/pm` not built.
2. Warehouse DDL not built.
3. Dealer feasibility not coded.
4. RAG does not yet include all API/book chunks.
5. Local ML baseline not trained.
6. Customer UX standard not yet implemented in UI.


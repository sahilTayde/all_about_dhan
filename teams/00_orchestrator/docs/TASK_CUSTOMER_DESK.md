# TASK — Customer desk: 3m chain memory + honest strategy confidence

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned:** 00_orchestrator (this ticket) · 05_analysis (`packages/desk-intel`) · 04_quant (staging + master plan honesty)  
**Informed:** 03_phd_market (chain Δ definitions) · 02_phd_math (nightly retune stays UNVALIDATED) · 06_backtesting (owns mix-and-match later) · 07_coding (dashboard bind later)  
**Owner paths:** [`config/workspace.yaml`](../../../config/workspace.yaml) `desk_intel.poll`, [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md), [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md), [`MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md)  
**Status:** `DONE` (docs + dry-run schema; **no live Dhan scrape**; **no orders**)  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`

---

## Requirement (customer)

1. Poll the **option chain every 3 minutes** and **remember the last snapshot** so trend / OI buildup can feed signals.
2. The customer has **low confidence** in the defined strategies. Do **not** invent extra STRATs, win rates, or a polished strategy catalog. Be honest in customer-facing docs.

## Constraints (kept)

- DhanHQ option-chain REST: **1 unique request / 3 seconds** ([docs](https://dhanhq.co/docs/v2/option-chain/)). **3 minutes between full chain calls is OK.** Do not make 1m full-chain the default.
- Optional **1m ATM±N** quote/cached delta remains optional (`strike_buildup_enabled: false`).
- Education ≠ advice. No orders. No live scrape required on this ticket.
- 14 candidates stay **DRAFT / UNVALIDATED**. Next team (quant freeze → backtest) owns mix-and-match. PhD nightly recon may **suggest** retunes; those stay UNVALIDATED.

## Done

- [x] `desk_intel.poll.chain_interval: 3m` (was 15m). CLI default 3m.
- [x] Snapshot memory: timestamped file + `last.json`; OI / PCR / ATM CE–PE Δ vs last.
- [x] Sentiment windows **10m / 15m / 30m / 1h** on fusion schema (mock bind for dashboard).
- [x] `MASTER_STRATEGY_PLAN.md` **CUSTOMER vs ENGINE** note — UI never shows indicator soup; engine mix is UNVALIDATED.
- [x] `SIGNAL_STAGING.md` **IN-PROGRESS** after CONFIRMED while the trade is live; then ACHIEVED / STOPPED / INVALIDATED.
- [x] This ticket. No live Dhan. No commit required.

## How to run dry

```bash
python -m desk_intel status
python -m desk_intel poll-chain --interval 3m --offline
python -m desk_intel poll-chain --interval 1m --offline   # optional ATM±N path
```

Empty `DHAN_*` → fixtures. Do not scrape live chain for this ticket.

## Not this ticket

- Live Dhan option-chain scrape
- Inventing win rates or additional STRAT-IDs
- Wiring `apps/web` colors for IN-PROGRESS (schema is ready; UI bind later)
- Measuring real 10m/15m/30m/1h sentiment (slots are mock)

## Artifacts

- This file
- [`config/workspace.yaml`](../../../config/workspace.yaml) `desk_intel.poll` + `desk_intel.sentiment`
- [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../../05_analysis/docs/DESK_INTELLIGENCE.md)
- [`TASK_DESK_INTELLIGENCE.md`](TASK_DESK_INTELLIGENCE.md) (poll cadence note)
- [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)
- [`teams/04_quant/docs/MASTER_STRATEGY_PLAN.md`](../../04_quant/docs/MASTER_STRATEGY_PLAN.md)

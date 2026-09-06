# TASK — Retune gate (nightly recon must not overwrite the book)

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned:** 06_backtesting (gate) · 05_analysis (`packages/desk-intel` stub) · 00_orchestrator (this ticket)  
**Informed:** 02_phd_math (REVIEW, not auto-apply) · 04_quant (staging + master plan) · 08_testing  
**Owner paths:** [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md), [`packages/desk-intel`](../../../packages/desk-intel/) `retune_gate.py` + `nightly.py`, [`handoffs/README.md`](../../02_phd_math/docs/handoffs/README.md)  
**Status:** `DONE` (docs + code stubs; **no engine**; **no live Dhan**; **no orders**; **no invented backtest results**)  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`

---

## Requirement (pro trader)

Do **not** blindly update indicator parameters or strategies after nightly recon. Event days make P/L look broken; retuning on that sample overfits.

1. Tag sessions `NEWS_DAY` / `EXPIRY` / `NORMAL` (desk-intel news + calendar + chain expiry).
2. Candidate change → **must backtest** (team 06) on **OOS + non-event (`NORMAL`)** days.
3. Promote only if the new spec is **more profitable on robust metrics** (expectancy, PF, DD — not one-day P/L) than current, **or** a documented **glitch** (lookahead, wrong SL, bug) whose fix is profitable in backtest.
4. Default: **keep current strategy**. PhD handoff is **REVIEW**, not auto-apply.

## Done

- [x] `teams/06_backtesting/docs/RETUNE_GATE.md`
- [x] `teams/02_phd_math/docs/handoffs/README.md`
- [x] Nightly emits `RETUNE_PROPOSAL` `status: BACKTEST_REQUIRED`; `production_params_written: false`
- [x] Session tag stub in `desk_intel.retune_gate`
- [x] Pointers: `AGENT.md`, this ticket, [`TASK_PRE_POST_MARKET_JOBS.md`](TASK_PRE_POST_MARKET_JOBS.md), `SIGNAL_STAGING.md`, `MASTER_STRATEGY_PLAN.md`
- [x] Smoke: `packages/desk-intel/tests/test_retune_gate.py`

## How to run dry

```bash
python -m desk_intel nightly --offline
```

JSON: `data/recon/YYYY-MM-DD.json` (`retune_proposal`, `session_kind`). Markdown: `teams/02_phd_math/docs/handoffs/NIGHTLY_YYYY-MM-DD.md`.

## Not this ticket

- Running or inventing a backtest
- Live orders / live Dhan
- Rewriting `apps/web`
- Auto-applying params to production or STRAT-* files

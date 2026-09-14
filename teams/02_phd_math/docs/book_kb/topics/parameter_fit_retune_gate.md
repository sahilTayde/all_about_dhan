# Exam note — parameter fit vs RETUNE_GATE

**Layer:** `VALIDATION`  
**Chair:** 06 owns the gate; 02 **REVIEW** only · [`RETUNE_GATE.md`](../../../../06_backtesting/docs/RETUNE_GATE.md) · loop: [`QUANT_SELF_REVIEW_LOOP.md`](../../../../06_backtesting/docs/QUANT_SELF_REVIEW_LOOP.md)

## What the oral wants

A **fit** (OLS k, KMeans, paper tuner grid) is a **research object**. A **retune** is a proposed change to production/paper **params**. Nightly and paper review may emit `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`. They must keep `production_params_written: false` and `keep_current_strategy: true` until 06 posts OOS+`NORMAL` metrics that beat the current spec.

Fitting is allowed. **Writing the book from the fit** is not.

## Tokens for FTS

parameter fit, RETUNE_GATE, RETUNE_PROPOSAL, BACKTEST_REQUIRED, production_params_written, keep_current_strategy, Super Order refused

## Desk mapping

| Action | Allowed? |
|--------|----------|
| Estimate k on a named expiry book | Yes — label HYPOTHESIS; sid dies weekly |
| `desk_ml fit` / `tv-ep-paper-tune` | Yes — local `data/recon/*` only |
| Nightly `RETUNE_PROPOSAL` | Yes — `BACKTEST_REQUIRED`, metrics null |
| Write `workspace.yaml` / MIX-DEFAULT-BUY knobs | **No** |
| Live Dhan Super Order from a fit | **No** — execution always refuses |
| Promote on one green replay | **No** |

Paper tuner may write `data/recon/tv_ep_paper_params_*.json` (local paper file). That is **not** production.

## DATA_INSUFFICIENT

No OOS+NORMAL beat of current spec exists for MIX-DEFAULT-BUY. Until then every fit is **REVIEW**, not a freeze.

## Exam trap

“The nightly JSON has BACKTEST_REQUIRED so the backtest ran.” **False.** That status means **a backtest is still required**.

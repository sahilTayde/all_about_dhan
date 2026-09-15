# OPENAI_OVERLAY_REVIEW — paper overlay counsel

**Team:** 06_backtesting · 07 `packages/desk-ml`  
**Date:** 2026-09-15 (IST)  
**Status:** paper overlay / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. No Super Order. No `ExecutionClient`.

Education ≠ advice. Notes ≠ five-pass. Cluster/OU counts are not a win rate.

Counsel was **not** written to a `COUNSEL_*.md` dump (allowlist). Round 1 lived in `counsel-job` stdout on this agent run. `SESSION_PREP_ML.md` is the 09:15 runbook, not the reject log.

---

## Round 1 — why OpenAI said REJECT

**Job:** `REVIEW_NOTES` · **together flag:** `ALIGNED` (both first-line tokens mapped to `OTHER`) · **substance:** SPLIT  
**Models:** Gemini `gemini-3.5-flash-lite` ACCEPT · OpenAI `gpt-5.4-nano` REJECT  
**Truncation:** the OpenAI paragraph was complete (not a mid-(c) cut). The refuse was a **content** refuse, not a nano clip.

Gemini (verbatim, first sentence):

> ACCEPT. The changes implement a desk-level ML warehouse join of OHLC bars, 1-minute bars, and ATM symbols against premium tape, alongside ML-001 embargo logic adhering to an AFML analog without out-of-sample claims, dual-tape follow-gap/hold scoring, and a 09:15 IST session prep routine, while leaving production parameters unwritten, the execution client unused, MRR windows restricted to 40/60/90, existing strategies STRAT-001 through STRAT-014 untouched, and MIX-DEFAULT-BUY unchanged.

OpenAI (verbatim):

> REJECT — Based on JOB REVIEW_NOTES, this is explicitly “09 notes — not a five-pass,” and the required desk_ml details are incomplete for a paper-only acceptance: while the what_changed slot describes joining `warehouse ohlc_bars + bars_1m + ATM symbols join premium_tape`, applying “ML-001 fit embargo last 5 1m rows (AFML analog, cpcv=false, oos_claim=false), score --source dual-tape FOLLOW-GAP HOLD,” “ML-002 score_mrr_last,” and “SESSION_PREP_ML 09:15 IST dual-tape then desk_ml score,” it also states `production_params_written false` and includes a “ExecutionClient unused” plus “MRR windows still 40/60/90 only,” but there is no provided HANDOFF block evidence that the desk_ml output is validated end-to-end for NIFTY/BANKNIFTY/SENSEX (paper-only constraints, no win-rate claims) nor confirmation that the “follow-gap hold” logic actually compiles/runs in the target environment. Keep_all_ok is “yes” and promote_claimed is “no NO_PROMOTE BACKTEST_REQUIRED,” but because the review gate requires founder+five-pass to stay unset and this is not a five-pass, acceptance is not supported. DATA_INSUFFICIENT for final approval.

**Engineering reading (not a prompt rewrite):**

| OpenAI gap | Meaning |
|------------|---------|
| Notes-not-five-pass treated as refuse | Job template said ACCEPT/REJECT with “gate stays unset unless five-pass,” so nano refused *any* accept. Five-pass still must stay unset. Paper overlay may be `ACCEPT_WITH_CAVEATS`. |
| No e2e NIFTY/BANKNIFTY/SENSEX | Overlay must score all three names. |
| Follow-gap not shown compiling/running | Dual-tape persist must write overlay; pytest must run HOLD. |
| DATA_INSUFFICIENT for *final approval* | Correct for RESEARCH_READY. Do not claim that gate. |

---

## What we recoded (paper overlay only)

- Causal residual **z** (`rolling_z(..., causal=True)`): mean/std from **past** bars only. `oos_claim: false`.
- Thin dual-tape (<2 INDEX+CE+PE ticks) → `session_action=HOLD`, `allow_new_paper_ce_pe=false`.
- `python -m desk_ml overlay` scores NIFTY / BANKNIFTY / SENSEX.
- Dual-tape persist writes `overlay_last.json` (fail-soft; no orders).
- Counsel CLI: `--openai-model` / `--max-tokens` so nano is not required; `ACCEPT`/`REJECT`/`ACCEPT_WITH_CAVEATS` tokens.
- `REVIEW_NOTES` output: paper overlay may be `ACCEPT_WITH_CAVEATS`; still not a five-pass; REJECT if look-ahead, missing tests, live orders, or a promote.
- Pytest: embargo, warehouse join, FOLLOW-GAP HOLD, thin HOLD, causal z, overlay three names, dual-tape `overlay_last.json`.

---

## Round 2 verdict

**Job:** `REVIEW_NOTES` · `--openai-model gpt-4.1` · `--max-tokens 1200` · compact JSON in `--route`  
**together:** `ALIGNED` on `ACCEPT_WITH_CAVEATS`  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`. Still **NO_PROMOTE**.

Gemini (`gemini-3.5-flash-lite`), first line + gist: **ACCEPT_WITH_CAVEATS**. Paper overlay only; 28 tests; embargo `oos_claim: false`; KEEP_ALL; `production_params_written` false; gate unset until five-pass + founder.

OpenAI (`gpt-4.1`), first line + gist: **ACCEPT_WITH_CAVEATS**. Notes-only, not a five-pass; pytest 28/28; wiring named; causal z / thin dual-tape HOLD remain as caveats; no Dhan production push.

Honest: this is **not** a five-pass pass. OpenAI no longer REJECTS the *paper overlay*. A REJECT on five-pass / RESEARCH_READY would still be correct if anyone asked for that gate.

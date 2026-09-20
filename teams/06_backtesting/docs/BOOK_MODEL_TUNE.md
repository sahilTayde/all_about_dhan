# BOOK_MODEL_TUNE — cache CREATE/TUNE (ML-001 + ML-002)

**Team:** 06_backtesting (gate) · 04 spec · 07 `packages/desk-ml`  
**Date:** 2026-09-15 (IST)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **NO_PROMOTE** / **BACKTEST_REQUIRED**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Execution:** refused. No Super Order. Cache / warehouse only.

Education ≠ advice. Cluster sizes and OU half-life are **in-sample counts**, not a win rate and not a promote.

JSON: `data/recon/BOOK_MODEL_TUNE_2026-09-15.json` (gitignored).

## Tape inventory (as_of 2026-09-15 IST, last 21 calendar days from 2026-08-25)

| Source | What is on disk | Last 21d |
|--------|-----------------|----------|
| **INDEX 1m JSON** | NIFTY/SENSEX/BANKNIFTY files from 2021-09-06 → **2026-09-03** | 2026-08-25 → 2026-09-03 (~2930 bars each) |
| **INDEX 1m + warehouse** | Join path also reads `warehouse.sqlite` | INDEX last print used in join: **2026-09-10** |
| **premium_tape ATM 1m** | NIFTY / SENSEX / BANKNIFTY day files **2026-09-09, 09-10, 09-11, 09-15** (today still thin mid-session) | Join used for book-tune still **09-09→09-10** (~599 triples). 09-15 dual-tape is live but not yet a full-day join |
| **OPTIDX 1m** | 22 strike-sid files; all touch the window | First bars in-window from 2026-08-25…09-10; **last bar 2026-09-11** |

**Aligned INDEX ∩ ATM CE ∩ ATM PE triples:** **599** for NIFTY and **599** for SENSEX, IST **2026-09-09 → 2026-09-10** only.

### Honest gaps (1–3 week tape)

ATM option tape is **three sessions**, not 15–21 calendar days. Missing from the **join**: 2026-09-11 (ATM tape exists; INDEX warehouse last used bar 09-10), **2026-09-12 … 2026-09-15** (no ATM 1m day files). INDEX JSON cache itself stops **2026-09-03**. Dual-tape on 2026-09-15 was `DhanApiError` / cache fallback to 2026-09-11 — **not** a new 1m history refresh. No live Dhan fetch was run for this job.

## ML-001 (seed **14** fixed)

KMeans k=4 + IsolationForest. `win_rate` null. Last bar overlay **HOLD** (`PREMIUM_DIVERGENCE`) on both underlyings.

| Underlying | triples | feature rows | RANGE | TREND_DN | TREND_UP | DIVERGE |
|------------|---------|--------------|-------|----------|----------|---------|
| NIFTY | 599 | 598 | 304 | 241 | 26 | 27 |
| SENSEX | 599 | 598 | 511 | 6 | 41 | 40 |

## ML-002 (`mrr-fit`) — 3 tweaks only: MRR window 40 / 60 / 90 + FOLLOW-GAP

OLS \(k\) on this two-day book is **not** a greek. NIFTY \(k_{\mathrm{CE}}=-29.77\), \(k_{\mathrm{PE}}=28.37\). SENSEX \(k_{\mathrm{CE}}=-87.22\), \(k_{\mathrm{PE}}=90.32\).

OU is fit on the **full** residual series (same φ for all three windows). Windows only change rolling \(z\), VWMA(PE), and HOLD counts.

### NIFTY

| window | n_scored | FOLLOW-GAP | \|z\|≥2 | HOLD overlay | mean \|z\| | OU φ | half-life (bars) |
|--------|----------|------------|---------|--------------|------------|------|------------------|
| 40 | 559 | 129 | 33 | 136 | 0.705 | 0.162 | 0.38 |
| 60 | 539 | 122 | 27 | 129 | 0.684 | 0.162 | 0.38 |
| 90 | 509 | 115 | 27 | 121 | 0.684 | 0.162 | 0.38 |

In-sample **preferred window 90** (lowest mean \|z\| among mean-reverting OU). **Not** OOS. **Not** MIX write.

### SENSEX

| window | n_scored | FOLLOW-GAP | \|z\|≥2 | HOLD overlay | mean \|z\| | OU |
|--------|----------|------------|---------|--------------|------------|-----|
| 40 | 559 | 182 | 34 | 186 | 0.683 | φ=−0.27 **NOT_MEAN_REVERTING** |
| 60 | 539 | 170 | 35 | 174 | 0.689 | same |
| 90 | 509 | 166 | 32 | 171 | 0.700 | same |

**preferred window:** `DATA_INSUFFICIENT` (no 40/60/90 OU with φ∈(0,1) on this residual).

`production_params_written`: **false**. `gate`: **BACKTEST_REQUIRED**.

## CLI (re-run, cache only)

```bash
pip install -e packages/desk-ml
python -m desk_ml inventory --calendar-days 21
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml score --underlying NIFTY --source cache
python -m desk_ml score --underlying NIFTY --source dual-tape
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml book-tune --calendar-days 21
python -m desk_ml replay-hold --underlying NIFTY --horizon-bars 15
python -m desk_ml paper-scalp --replay
```

09:15 IST paper start (dual-tape + score, no ExecutionClient): [`SESSION_PREP_ML.md`](SESSION_PREP_ML.md).

**replay-hold (2026-09-16, NIFTY cache 599 triples):** 15m ATM straddle fwd. FOLLOW_GAP / ML-001 HOLD n=133: mean **+0.29%** when HOLD vs **−0.18%** when not. ML-002 |z|≥2 n=30: **+0.26%** vs **−0.09%**. UNION n=140 similar. On **this** join, HOLD fired on bars that then recovered and **did not** fire on bars that then bled. Diagnostic only. `win_rate=null`. **NO_PROMOTE.**

## replay-hold ablation 2026-09-16 (second pass, same 599 triples)

Same join: INDEX ∩ ATM CE ∩ ATM PE IST **2026-09-09 → 2026-09-10** only (`n_scored=583`, horizon 15m). ATM day files exist for **09-11 / 09-15 / 09-16** but **do not join** because INDEX 1m JSON last bar is **2026-09-03** and warehouse INDEX 1m last bar is **2026-09-10T07:28Z**. File needed: `ohlc_bars` 1m INDEX (or `INDEX_IDX_I_{13,25,51}_1_*.json`) covering 2026-09-11…16. `win_rate=null`. **NO_PROMOTE.**

| Underlying | Rule | n_hold | mean straddle fwd HOLD | mean NOT HOLD |
|------------|------|-------:|-----------------------:|--------------:|
| NIFTY | FOLLOW_GAP / ML-001_HOLD | 133 | +0.293% | −0.182% |
| NIFTY | ML-002 \|z\|≥2 | 30 | +0.264% | −0.092% |
| NIFTY | DIVERGE_ONLY | 27 | +0.733% | −0.113% |
| NIFTY | UNION_NO_FOLLOW_GAP | 52 | +0.485% | −0.129% |
| BANKNIFTY | FOLLOW_GAP / ML-001_HOLD | 178 | −0.076% | −0.055% |
| BANKNIFTY | ML-002 \|z\|≥2 | 25 | +0.181% | −0.072% |
| BANKNIFTY | DIVERGE_ONLY | 47 | +0.112% | −0.076% |
| SENSEX | FOLLOW_GAP / ML-001_HOLD | 191 | −0.359% | −0.848% |
| SENSEX | ML-002 \|z\|≥2 | 33 | −0.337% | −0.708% |
| SENSEX | DIVERGE_ONLY | 38 | +0.036% | −0.738% |

HOLD is “useful” only if HOLD mean is **more negative** (bleed avoided). NIFTY is inverted. BANKNIFTY FOLLOW_GAP is only a hair more negative. SENSEX HOLD bars bled **less** than trade-through bars. Ablation `DIVERGE_ONLY` / `UNION_NO_FOLLOW_GAP` did **not** flip NIFTY. Keep all rules; do not delete ML-002 (BN/SX OU still `NOT_MEAN_REVERTING` / preferred window `DATA_INSUFFICIENT`).

BANKNIFTY `mrr-fit` this pass: φ=−0.179, preferred window **DATA_INSUFFICIENT**. Row stays.

Pytest: `python -m pytest packages/desk-ml/tests -q`

KEEP_ALL STRAT-001–014. MIX-DEFAULT-BUY unchanged.

## Observer review (2026-09-20, HYPOTHESIS)

One family, not a second buyer. SOD product path: picker one wing, then observer ALLOW / VETO / PASS on closed **1m INDEX vs same-strike ITM**. last-3 mismatch is logged, not a veto. ML-001/002 stay silent (not BUY_CE). ATM / no ITM → PASS. Native tape: 16 mixed ATM+ITM (141 ATM / 39 ITM ticks); 17/18 almost all ITM. Do not mock ATM LTP as ITM quotes.

write=false NIFTY. Unique net = `UNIQUE_PNL_BOOKS` as coded. Skip counts are per 10s tick × book — not per 1m decision. Session cap `nifty_max_filled_per_book=4` still binds NEW (4 dealer fills on 17/18). One-open skip printed **0** on these days because tickets closed before the next picker ticket; cap, not overlap, cut the book. `win_rate` is paper hit rate net, **not** founder wr. **NO_PROMOTE.** Gate **not** `RESEARCH_READY_FOR_PROGRAMMING`.

OLD = parallel fills, `observer_veto_fills=off`, `sod_one_ticket=off`. NEW = `sod_one_ticket` + majority + observer. Double-run MATCH.

| Day | Tape | OLD n_filled unique | OLD unique net | OLD dealer | OLD logit | OLD paper hit net | NEW n_filled unique | NEW unique net | NEW dealer | NEW logit | NEW paper hit net | NEW skips (tick×book) | What moved |
|-----|------|--------------------:|---------------:|-----------:|----------:|------------------:|--------------------:|---------------:|-----------:|----------:|------------------:|------------------------|------------|
| 16 | ATM 141 / ITM 39 | 2 | **+8172.10** | +8172.10 n=2 | 0 | 50% | 3 | **+9774.76** | +9774.76 n=3 | 0 | 66.67% | FOLLOW_GAP 0 · HOLD_MAJORITY 423 · SOD_ONE_OPEN 0 · cap 0 · LAB_OBSERVE 441 | Helped. Extra dealer fill; ATM PASS. |
| 17 | ITM 656 / ATM 1 | 8 | **−24681.74** | −12340.87 n=4 | −12340.87 n=4 | 0% | 4 | **−8804.90** | −8804.90 n=4 | 0 | 0% | FOLLOW_GAP 55 · HOLD_MAJORITY 505 · SOD_ONE_OPEN 0 · cap 35 · LAB_OBSERVE 425 | Helped unique by dropping logit clone + different 4 dealer tickets. Cap 4 still. |
| 18 | ITM 694 / ATM 4 | 8 | **+1776.64** | +888.32 n=4 | +888.32 n=4 | 25% | 4 | **−594.45** | −594.45 n=4 | 0 | 25% | FOLLOW_GAP 73 · HOLD_MAJORITY 558 · SOD_ONE_OPEN 0 · cap 49 · LAB_OBSERVE 619 | Hurt. Picker/observer changed the 4 dealer tickets; clones no longer double the green. |
| 16+17+18 | native | 18 | **−14733.00** | — | — | — | 11 | **+375.41** | — | — | — | — | Net unique better; **18 hurt**. Not a promote. |

Monday: keep SOD flag off for live until founder asks; A/B stays. `production_params_written=false`.

## HANDOFF

```text
From:     teams/06_backtesting + packages/desk-ml
To:       00 / 04 / 07 / 09 / founder
Date:     2026-09-16
Status:   CACHE TUNE / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Inventory + ML-001 seed 14 + ML-002 MRR 40/60/90 + FOLLOW-GAP.
  Fit on 599 triples 2026-09-09..10 for NIFTY/BANKNIFTY/SENSEX. Ablation CLI kept.
  production_params_written false. MIX-ML-LOGIT stays KEEP (scan coded; FAIL/WEAK book).
Rejected: Live Dhan / Super Order; promote from cluster or half-life; STRAT-015+; deleting ML-002.
UNKNOWN: INDEX 1m for 2026-09-11..16 so existing ATM day files can join; OOS+NORMAL.
```

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
| **premium_tape ATM 1m** | NIFTY / SENSEX / BANKNIFTY day files **2026-09-09, 09-10, 09-11** (1146 CE + 1146 PE each) | Same three days only |
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
python -m desk_ml fit --underlying NIFTY --seed 14
python -m desk_ml score --underlying NIFTY
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml book-tune --calendar-days 21
```

Pytest: `python -m pytest packages/desk-ml/tests -q`

KEEP_ALL STRAT-001–014. MIX-DEFAULT-BUY unchanged.

## HANDOFF

```text
From:     teams/06_backtesting + packages/desk-ml
To:       00 / 04 / 07 / 09 / founder
Date:     2026-09-15
Status:   CACHE TUNE / UNVALIDATED / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Inventory + ML-001 seed 14 + ML-002 MRR 40/60/90 + FOLLOW-GAP.
  Fit on 599 NIFTY/SENSEX triples 2026-09-09..10. production_params_written false.
Rejected: Live Dhan / Super Order; promote from cluster or half-life; STRAT-015+.
UNKNOWN: Same-calendar INDEX+ATM for 2026-09-11..15; OOS+NORMAL.
```

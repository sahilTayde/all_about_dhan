# ML-001 + ML-002 — local overlays (INDEX vs CE vs PE)

**KEEP_ALL.** Do not drop these IDs because a session window is empty. They are **overlays** (HOLD/WATCH), not customer BUY tickets. **NO_PROMOTE.**

## ML-001 — unsupervised pattern overlay

**Team:** 04_quant (spec) · 07 code in `packages/desk-ml` · 06 does **not** promote from this fit  
**Date:** 2026-09-14 (Ganesh Chaturthi — **NSE closed**; fit cache only)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Tickets:** [`docs/TOKEN_ML_STRATEGY.md`](../../../docs/TOKEN_ML_STRATEGY.md) · [`docs/COMPETITIVE_PRODUCT_BASELINE.md`](../../../docs/COMPETITIVE_PRODUCT_BASELINE.md) **ML-001**

Education ≠ advice. **No live orders.** Cluster sizes are counts, not edge. No win rates.

## Why KMeans + IsolationForest

| Chosen | Role |
|--------|------|
| **KMeans k=4** | Unsupervised regime: `TREND_UP` / `TREND_DN` / `RANGE` / `DIVERGE` |
| **IsolationForest** | Outlier overlay; residual z is a second tripwire |

Rejected on the 30s path: deep RL, transformers, blocking LLM, sklearn as a hard dep. Supervised logistic skipped unless later labels are thick (`DATA_INSUFFICIENT` / `SKIPPED_THIS_TICKET`). **No MIX param writes** ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).

Features (`ml001-v1`): `idx_ret`, `ce_ret`, `pe_ret`, `spread_chg`, `abs_residual` from aligned 1m INDEX + ATM CE + ATM PE (`data/recon/ohlc` + `premium_tape`). No invented greeks.

**Attach tomorrow:** after 1m bar close **or** two dual-tape ticks, `python -m desk_ml score --underlying NIFTY --source dual-tape`. `overlay=HOLD` / FOLLOW-GAP → dealer HOLDs new paper CE/PE. Fit embargo last 5 bars (AFML analog, not CPCV). Warehouse `ohlc_bars` + `bars_1m` join INDEX; `{UND}_ATM_CE/PE` if present. Regime labels are not BUY_CE/PE. No LLM. ExecutionClient unused.

```bash
pip install -e packages/desk-ml
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml score --underlying NIFTY --source dual-tape
```

Holiday cache fit (NIFTY join of INDEX 1m + ATM tape 2026-09-09..11): **599** triples → **598** rows. Counts: RANGE 304, TREND_DN 241, TREND_UP 26, DIVERGE 27. `win_rate` null. `NO_PROMOTE`.

Book-learning retune of the same overlay (seed **14** fixed) plus ML-002: [`BOOK_MODEL_TUNE.md`](../../06_backtesting/docs/BOOK_MODEL_TUNE.md). `python -m desk_ml book-tune`.

## ML-002 — mean-reversion overlay (KEEP)

OU on `MIX-FORM` residual + VWMA windows **40 / 60 / 90** only. FOLLOW-GAP HOLD. Spec + tune: [`BOOK_MODEL_TUNE.md`](../../06_backtesting/docs/BOOK_MODEL_TUNE.md). Window 90 often `DATA_INSUFFICIENT` — **row stays**. IsolationForest (ML-001) remains an anomaly HOLD, not a BUY.

KEEP_ALL STRAT-001–014. MIX-DEFAULT-BUY unchanged. Catalog §25.

## HANDOFF

```text
From:     teams/04_quant + packages/desk-ml
To:       00 / 05 / 06 / 07 / 09 / founder
Date:     2026-09-14
Status:   HYPOTHESIS overlay coded / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: KMeans k=4 + IsolationForest overlay. Cache fit on holiday.
Rejected: Live orders; blocking LLM; auto-retune; deep RL; STRAT-015+.
UNKNOWN: Walk-forward vs desk_divergence on next NORMAL session.
```

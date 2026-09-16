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

Features (`ml001-v1`): `idx_ret`, `ce_ret`, `pe_ret`, `spread_chg`, `abs_residual` from aligned 1m INDEX + ATM CE + ATM PE (`data/recon/ohlc` + `premium_tape`). No invented greeks. Live Dhan greeks belong in **`MIX-ML-GREEKS`** (`ml-greeks-v1`), not this vector.

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

---

## How we use the ML bucket (not a buy engine)

| Piece | What it does on the desk | What it does **not** do |
|-------|--------------------------|-------------------------|
| **FOLLOW-GAP** | Index moved; ATM CE/PE did not confirm → **HOLD** new paper | Does not pick CE vs PE |
| **ML-001** | KMeans 4 regimes + IsolationForest. HOLD on PREMIUM_DIVERGENCE / DIVERGE / residual+IF | `TREND_UP` is **not** BUY_CE |
| **ML-002** | Residual z ≥ 2 or FOLLOW-GAP → HOLD. Windows 40/60/90 only | Empty window 90 ≠ delete |
| **MIX-FORM-*** | Features (beta residual, diverge-z, straddle, follow-gap) | Not tickets |
| **MIX-ML-LOGIT*** | INDEX 3m walk-forward logit in `ml_leans.py` | **Not** customer default. Scan book. Thin 3m train → `DATA_INSUFFICIENT` |

**Attach:** dual-tape tick → `desk_ml overlay` labels HOLD/WATCH. Parallel PAPER scalpers: `python -m desk_ml paper-scalp --replay`. ML-001 HOLD **skips the ML-001 book only** — it does not veto MIX-DEFAULT-BUY. **Bypass:** `PAPER_TRAIN_NO_DENY=1` books CE/PE **anyway**. Turn the flag **off** when testing HOLD.

**Tune (allowed):** seed **14** fixed; embargo 5; ML-002 windows {40,60,90}; z=2. **Not allowed:** write `MIX-DEFAULT-BUY` params; claim win rate; LLM on the 45s path.

**Check:** `python -m desk_ml replay-hold --underlying NIFTY` — 15m straddle bleed **if HOLD vs if not**. HOLD is useful only if mean_when_hold is **worse** (more bleed avoided). NIFTY cache replay 2026-09-16: HOLD was **the other way around** on that two-day join. Next ablation: do not HOLD on FOLLOW-GAP recovery bars; test HOLD only on DIVERGE + |z| (pass to 06 after a second tape). Details: [`BOOK_MODEL_TUNE.md`](../../06_backtesting/docs/BOOK_MODEL_TUNE.md).

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

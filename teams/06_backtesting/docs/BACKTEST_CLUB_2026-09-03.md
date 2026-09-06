# BACKTEST_CLUB — 2026-09-03 (2y club + annexure nested grid)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / **not a promote**  
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`

Command: `python -m backtest_engine --live --years 5 --interval 1 club`  
Artifact: `data/recon/BACKTEST_CLUB_2026-09-03.json`

**Dhan API:** there is **no** indicator series REST. Annexure names (`RSI_14`, `SMA_20/50`, `EMA_*`, `MACD_HIST`) are **computed from INDEX OHLC**. `/alerts/orders` is not used.

**Clock:** 09:00–09:30 and 15:00–15:30 IST dropped. Flatten session end.

**Discarded this loop:** ORB (empty under clock), MIX-ML-LOGIT (55% wr, exp < 0), PDH/CPR/NR7 (extreme 2y wr).

**Clubbed (WEAK survivors only):** ENGULF, GAP, RANGE-EXP, ML-XR.

**Nested grid:** RSI bands, Donchian n, BB k, EMA pairs. Params locked on **first 60% of 2y by IS expectancy**, scored on **last 40%**. Pick was not win-rate.

## NIFTY 2y (optimistic option premium)

| Book | OOS n | OOS wr | OOS exp | Rating |
|------|------:|-------:|--------:|--------|
| MIX-CLUB-GR (GAP ∧ RANGE-EXP) | 36 | **69.4%** | +4.40 | **WEAK** — n barely 30; SENSEX FAIL 40.5%; winner-soup |
| MIX-RSI-MR (RSI_14 30/70) | 350 | 58.0% | **−0.35** | **FAIL** |
| MIX-RSI-2575 (ScanX-style) | 173 | 54.3% | **−0.69** | **FAIL** |
| MIX-GRID-RSI (locked 20/80) | 168 | 53.0% | **−1.01** | **FAIL** (nested holdout) |
| MIX-MACD-HIST | 811 | 45.3% | **−0.63** | **FAIL** |
| MIX-CLUB-EG / EGR | 0 | — | — | DATA_INSUFFICIENT (AND never fires) |

GRID Donchian locked n=40, BB k=2.5, EMA 10/50 — all **FAIL** holdout wr.

## SENSEX

All FAIL or empty. Best annexure wr EMA-10-50 44.6% (still < 45%). CLUB-GR 40.5% exp −2.61.

**Do not** treat 69% as the next scan’s “improved edge.” It is GAP ∧ RANGE-EXP after those two already survived a prior scan, on **36** OOS trades, one underlying.

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: 2y club + annexure nested grid ran under founder clock.
  CLUB-GR NIFTY WEAK 69% n=36. RSI high wr FAIL exp. KEEP_ALL.
Rejected: promote 69%; CANDIDATE; Dhan series REST; grid after holdout wr;
  live orders; STRAT-015+.
UNKNOWN: costs; NORMAL; family-wise error; Q12.
```

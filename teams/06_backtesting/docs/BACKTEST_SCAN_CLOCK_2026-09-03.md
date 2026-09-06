# BACKTEST_SCAN_CLOCK — 2026-09-03 (founder dead band + ML)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / engine ran / **not a promote**  
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`

Command: `python -m backtest_engine --live --years 5 --interval 1 scan`  
Artifact (gitignored): `data/recon/BACKTEST_SCAN_CLOCK_2026-09-03.json`

**Clock (founder freeze, before wr):** drop INDEX and option bars **09:00–09:30 IST** and **15:00–15:30 IST**. Flatten at session end (no hold into CAS). 009 15:15 flatten is inside the dead band, so it does not fire.

**ML:** `MIX-ML-LOGIT` trains on **INDEX 3m next-close direction** using only bars **before** the 730d cutoff. It never trains on option premium. `MIX-ML-LOGIT-XR` = logit ∧ range-expansion (named before wr). Not sklearn (stdlib logit).

ORB books are **empty** — their 09:15–09:30 box sits inside the dead band. That is the filter working, not a bug.

Costs **UNKNOWN**. Multiple testing (22 IDs × 2 names). Not DHAN-DERIVED. Default mix **unchanged**.

## 2y OOS (NIFTY) — optimistic option premium

| Book | OOS n | OOS wr | OOS exp | Rating |
|------|------:|-------:|--------:|--------|
| MIX-ML-LOGIT | 2199 | **55.7%** | **−0.77** | **FAIL** (exp ≤ 0) |
| MIX-GAP | 100 | 55.0% | +1.00 | **WEAK** |
| MIX-ENGULF | 1226 | 48.0% | +0.31 | **WEAK** |
| MIX-INSIDE-BRK | 533 | 47.5% | −0.19 | **FAIL** |
| MIX-ML-LOGIT-XR | 172 | 47.1% | +0.38 | **WEAK** |
| MIX-RANGE-EXP | 271 | 46.9% | +1.00 | **WEAK** (5y wr 44.9% **FAIL**) |

A **55% win rate that loses money** is the ML book. Win rate is not the mandate.

## 5y confirm (730d survivors only)

| Book | 5y OOS wr | 5y exp | Rating |
|------|----------:|-------:|--------|
| MIX-GAP NIFTY | 54.2% | +0.59 | **WEAK** — n still small; costs UNKNOWN |
| MIX-ENGULF NIFTY | 48.5% | +0.34 | **WEAK** |
| MIX-ML-LOGIT-XR NIFTY | 47.1% | +0.38 | **WEAK** (same sample as 2y — model only predicts after train cutoff) |
| MIX-RANGE-EXP NIFTY | 44.9% | +0.57 | **FAIL** |

## SENSEX

All FAIL wr (best SAR 43.5%). ML logit 30.2%. Engulf 26.8%. No 5y unlock.

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: founder dead band applied; session-end flatten; ML IS-only; ORB empty
  as expected. GAP/ENGULF/ML-XR NIFTY WEAK. ML-LOGIT 55% wr FAIL on exp.
Rejected: promote; CANDIDATE; treat 55% wr as edge; grid logit threshold after wr;
  live orders; STRAT-015+.
UNKNOWN: costs; NORMAL strip; Q12 fills; family-wise error.
```

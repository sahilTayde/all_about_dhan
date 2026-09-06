# BACKTEST_SCAN — 2026-09-03 (20 WEB/PATTERN MIX, expanding windows)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / engine ran / **not a promote**  
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Charter:** [`MIX_SCAN_VALIDATION.md`](../../02_phd_math/docs/MIX_SCAN_VALIDATION.md)  
**IDs:** [`MIX_SCAN_2026-09-03.md`](../../04_quant/docs/MIX_SCAN_2026-09-03.md) · catalog §8

Command: `python -m backtest_engine --live --years 5 --interval 1 scan`  
Artifact (gitignored): `data/recon/BACKTEST_SCAN_2026-09-03.json`

Universe: **NIFTY** and **SENSEX** only. Strike: **005 ITM** (CE ATM-2 / PE ATM+2). Flatten **009**. Costs **UNKNOWN**. News **not** stripped. INDEX 3m leans are **not** FUTIDX VWAP. Origin **WEB-DERIVED** or **PROJECT_MIX** — **not** DHAN-DERIVED. Customer default **unchanged**.

**Multiple testing:** 20 recipes × 2 underlyings × 5 windows. A 730d wr just over 45% is **not** a theorem. Do not grid candle/ORB/Donchian params after seeing wr.

**30d / 90d = SCREEN only.** Example of screen luck: MIX-NR7-BRK NIFTY 30d OOS wr **60%** on **n=5**. That is **not** a promote.

## 730d (2y) OOS — NIFTY (optimistic option premium)

| Book | Origin | OOS n | OOS wr | OOS exp | Rating |
|------|--------|------:|-------:|--------:|--------|
| MIX-GAP | WEB-DERIVED | 100 | 48.0% | +0.63 | **WEAK** (730d gate) |
| MIX-INSIDE-BRK | PROJECT_MIX | 565 | 47.8% | +0.58 | **WEAK** (730d gate) |
| MIX-ENGULF | PROJECT_MIX | 1302 | 46.8% | +0.11 | **WEAK** (730d gate) |
| MIX-SAR | PROJECT_MIX | 1254 | 44.2% | −1.19 | FAIL |
| MIX-EMA-20-50 | PROJECT_MIX | 464 | 43.1% | −3.87 | FAIL |
| MIX-ORB-15 | WEB-DERIVED | 570 | 34.6% | −3.14 | FAIL |
| MIX-ORB-VWAP | WEB-DERIVED | 600 | 34.5% | −2.89 | FAIL |
| MIX-CPR-ORB | WEB-DERIVED | 466 | 35.6% | −2.77 | FAIL |
| MIX-MOM-BODY | PROJECT_MIX | 3940 | 39.3% | −0.17 | FAIL |

Remaining NIFTY books also **FAIL** wr < 45% (Donchian 40.8% exp +0.28 still FAIL on wr). Full table in JSON.

## 730d (2y) OOS — SENSEX

**All 20 FAIL** on wr (best SAR 41.0%; ENGULF 27.6%; INSIDE-BRK 26.9%). Several have **positive** optimistic exp with wr well below 45% — fat tails / SENSEX rolling gaps, **not** a pass. Do not promote on exp while wr fails.

## 5y confirmation (only 730d survivors)

| Book | 5y OOS n | 5y OOS wr | 5y OOS exp | Rating |
|------|--------:|----------:|-----------:|--------|
| MIX-ENGULF NIFTY | 3242 | 48.0% | +0.39 | **WEAK** — costs UNKNOWN, not CANDIDATE |
| MIX-INSIDE-BRK NIFTY | 1490 | 47.5% | +0.19 | **WEAK** — costs UNKNOWN, not CANDIDATE |
| MIX-GAP NIFTY | 214 | 50.0% | **−0.34** | **FAIL** on 5y (optimistic exp ≤ 0) |

GAP cleared the 730d wr gate and **died on 5y**. ENGULF / INSIDE-BRK did **not** replicate on SENSEX. Neither is the customer default.

## Expanding-window honesty (survivors)

| Book | 30d | 90d | 180d | 365d | 730d | 5y |
|------|-----|-----|------|------|------|----|
| MIX-ENGULF NIFTY | SCREEN wr 46% exp −1.72 | SCREEN wr 44% | FAIL exp −0.35 | WEAK | WEAK | WEAK |
| MIX-INSIDE-BRK NIFTY | SCREEN wr 28% n=25 | SCREEN | WEAK | WEAK | WEAK | WEAK |
| MIX-GAP NIFTY | SCREEN wr 20% n=5 | SCREEN | DATA_INSUFFICIENT n=25 | FAIL exp −2.08 | WEAK | **FAIL** |

Do **not** retune lookbacks. Do **not** AND Supertrend/MACD/RSI onto these after wr.

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: 20 WEB/PATTERN MIX books ran on ingested rollingoption; 30d→730d ladder;
  5y only on 3 NIFTY 730d survivors. ORB folklore FAIL. GAP 5y FAIL. ENGULF/INSIDE
  NIFTY WEAK (optimistic). KEEP_ALL. Default unchanged.
Rejected: promote; CANDIDATE; STRAT-015+; DHAN-DERIVED relabel; p-hack after wr;
  live orders; treat 30d NR7 60% as edge.
UNKNOWN: costs; FUTIDX VWAP; SENSEX early rolling EMPTY; Q12 fills; family-wise
  error rate (k=20 × m=5 × 2 names).
```

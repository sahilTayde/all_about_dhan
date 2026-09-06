# BACKTEST_BOOKS — 2026-09-03 (5y HQ 1m)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / engine ran / **not a promote**  
**Gate:** `BACKTEST_REQUIRED` · `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**P/L unit:** underlying **points proxy** (INDEX or current-month FUTIDX). **`option_pnl`: null.** Not customer money.

Command: `python -m backtest_engine --live --years 5 --interval 1`  
Artifact (gitignored): `data/recon/BACKTEST_BOOKS_2026-09-03.json`

## Data actually used

| Tape | Bars (NIFTY / BANKNIFTY / SENSEX) | Window (IST) | Note |
|------|-------------------------------------|--------------|------|
| **INDEX 1m** `IDX_I` 13/25/51 | **524154 / 522920 / 503687** | 2021-09-06 → 2026-09-03 | Official charts: last **5 years**, 90-day chunks, 21/21 ok. Volume present; **UNKNOWN as FUTIDX VWAP**. |
| **FUTIDX 1m** nearest CSV ids **68407 / 68390 / 844615** | **17785 / 17780 / 17203** | **2026-07-01 → 2026-09-03** | Current contract only. Older chunks **empty** (not a continuous back-adjusted series). |

Spoken STRAT-003 is **3m FUTIDX**. This run: **1m → 3m resample**. HQ has no 3m token.

News/expiry **not** stripped (`session_kind: UNKNOWN`). 348 STRAT-008 mixed-index veto days.

## Rating rule (win-rate first, as founder asked)

OOS = last 20% of trades. Need ≥30 IS and ≥30 OOS.

| OOS | Rating |
|-----|--------|
| n < 30 | `DATA_INSUFFICIENT` |
| expectancy_pts ≤ 0 | `FAIL` |
| win_rate ≥ 55% and exp > 0 | `CANDIDATE` (still UNVALIDATED) |
| win_rate ≥ 45% | `WEAK` |
| else | `FAIL` |

**All coded books: `FAIL`.** `validated: false`. `promote: false`.

## Scores (proxy)

| Book | Tape | OOS n | OOS win_rate | OOS exp pts | Rating |
|------|------|------:|-------------:|------------:|--------|
| STRAT-003 / MIX-DEFAULT-BUY | NIFTY INDEX 3m | 1183 | **28.2%** | +0.43 | FAIL |
| STRAT-003 / MIX-DEFAULT-BUY | BANKNIFTY INDEX 3m | 1226 | **26.8%** | +1.66 | FAIL |
| STRAT-003 / MIX-DEFAULT-BUY | SENSEX INDEX 3m | 1204 | **27.2%** | +2.66 | FAIL |
| STRAT-001 | NIFTY INDEX 60m+5m | 112 | **43.8%** | +1.36 | FAIL |
| STRAT-001 | BANKNIFTY | 119 | **42.0%** | +11.2 | FAIL |
| STRAT-001 | SENSEX | 113 | **41.6%** | +14.3 | FAIL |
| STRAT-006 | NIFTY 2m | 2982 | **35.6%** | +0.23 | FAIL |
| STRAT-006 | BANKNIFTY 2m | 3032 | **36.3%** | +1.70 | FAIL |
| STRAT-006 | SENSEX 2m | 2494 | **35.4%** | −0.14 | FAIL |
| STRAT-003 | NIFTY FUTIDX 3m | 64 | **31.3%** | −0.21 | FAIL |
| STRAT-003 | BANKNIFTY FUTIDX 3m | 60 | **30.0%** | +0.59 | FAIL |
| STRAT-003 | SENSEX FUTIDX 3m | 34 | **41.2%** | +2.43 | FAIL |

004/005/010/011/012/013/014 = **NOT_CODED** (parked / overlay / sell WAITING). KEEP_ALL.

## Tune log (not applied)

RETUNE_GATE: default **keep current strategy**. This sample is **not** OOS+`NORMAL` (news filter missing). Costs/slippage **not** in fills.

| Candidate | Why not applied |
|-----------|-----------------|
| Swap default 003 → 001 | 001 win_rate higher (~42% vs ~28%) still **FAIL**; 001 is `PROJECT_MIX` (spoken NIFTY 100 stocks). |
| Drop 008 veto | Would change n; needs a **new** OOS+NORMAL run. |
| Supertrend grid | “103” WEAK. No silent swap. |
| Option-premium engine | Still **DATA_INSUFFICIENT** (Q8). |

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: 5y INDEX 1m is a real chunk; FUTIDX ids from CSV; ratings FAIL; keep_current.
Rejected: promote; option P/L; treating INDEX VWAP as Gokul 3m.
UNKNOWN: NORMAL-only subset; continuous FUTIDX; option fills.
```

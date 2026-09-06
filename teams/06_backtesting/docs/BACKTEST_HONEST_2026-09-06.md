# BACKTEST_HONEST — 2026-09-06 (costs + expiry strip + FUTIDX stitch)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / **not a promote**  
**Gate:** `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`

Command: `python -m backtest_engine --live --years 5 --interval 1 honest`  
Artifact: `data/recon/BACKTEST_HONEST_2026-09-06.json`  
Prior club (optimistic): [`BACKTEST_CLUB_2026-09-03.md`](BACKTEST_CLUB_2026-09-03.md)

**Did not retune.** Frozen club leans only. Nested grids not re-picked.

## Cost model (HYPOTHESIS)

`HYPOTHESIS_OPTION_RT_1PCT` — 1% of premium each way (entry + exit).  
Statutory STT / brokerage / GST = **UNKNOWN** (0 in the formula).  
Not an NSE circular. Not a Dhan REST field. After-cost **CANDIDATE is capped at WEAK**.

## Session tags

| Track | Result |
|-------|--------|
| NEWS_DAY calendar | **DATA_INSUFFICIENT** — [`NEWS_CALENDAR.yaml`](refs/NEWS_CALENDAR.yaml) empty on purpose |
| EXPIRY proxy | last INDEX session of each ISO week (`HYPOTHESIS`, not FROM_CONTRACT weekday) |
| SCORE_SAMPLE (`NORMAL`) | **empty** — cannot tag NORMAL without a news calendar |
| EXPIRY_STRIPPED | scored; **not** OOS+NORMAL validated |

## NIFTY 2y after hypothesis cost (optimistic 69% is gone)

| Book | OOS n | OOS wr | OOS exp | PF | Rating |
|------|------:|-------:|--------:|---:|--------|
| MIX-CLUB-GR AFTER_COST | 36 | **44.4%** | +0.80 | 1.23 | **FAIL** (was 69.4% optimistic) |
| MIX-CLUB-GR EXPIRY_STRIPPED | 27 | 51.9% | +2.69 | 1.96 | **DATA_INSUFFICIENT** (n<30) |
| MIX-CLUB-GR SCORE_SAMPLE | 0 | — | — | — | **DATA_INSUFFICIENT** |
| MIX-CLUB-GXR AFTER_COST | 30 | 50.0% | +1.83 | 1.57 | **WEAK** — SENSEX FAIL; hypothesis cost |
| MIX-RSI-MR AFTER_COST | 348 | 42.2% | **−3.81** | 0.50 | **FAIL** |
| MIX-MACD-HIST AFTER_COST | 806 | 37.8% | **−4.11** | 0.55 | **FAIL** |

SENSEX CLUB-GR AFTER_COST: n=37 wr **32.4%** exp **−24.0** **FAIL**.

## Continuous FUTIDX (spoken STRAT-003)

Live scrip-master listed front + two back months. Only the **current** contract has HQ bars (~64 days, ~17k 1m). OCT/NOV IDs returned empty. Stitch **DATA_INSUFFICIENT**.

| Book | span_days | contracts | Rating |
|------|----------:|----------:|--------|
| STRAT-003/NIFTY/FUTIDX-STITCH-3m | 64 | 3 | **DATA_INSUFFICIENT** |
| STRAT-003/BANKNIFTY/FUTIDX-STITCH-3m | 64 | 3 | **DATA_INSUFFICIENT** |
| STRAT-003/SENSEX/FUTIDX-STITCH-3m | 66 | 3 | **DATA_INSUFFICIENT** |

Spoken 003 stays on INDEX 1m→3m resample until expired-month FUTIDX IDs exist.

```text
HANDOFF
From: 06
To:   00 / 02 / 04 / 09
Accepted: hypothesis 1% RT overlay on frozen club books; expiry ISO-week proxy;
  SCORE_SAMPLE empty without news calendar; FUTIDX stitch attempted.
  CLUB-GR NIFTY after-cost FAIL 44% (was 69% optimistic). KEEP_ALL.
Rejected: promote GXR WEAK; invent STT; call EXPIRY_STRIPPED NORMAL;
  live orders; STRAT-015+; retune grids after seeing after-cost wr.
UNKNOWN: statutory costs; true FROM_CONTRACT expiry; continuous FUTIDX IDs;
  Q12 fills.
```

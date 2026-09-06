# BACKTEST_OPTION — 2026-09-03 (5y rollingoption 1m)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / engine ran / **not a promote**  
**Gate:** `BACKTEST_REQUIRED` · `keep_current_strategy: true` · **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**P/L unit:** **OPTION_PREMIUM_POINTS** (long CE and long PE: `exit − entry`). Costs **UNKNOWN** ⇒ expectancy **OPTIMISTIC**.  
**News / expiry strip:** `DATA_INSUFFICIENT` (`session_kind: UNKNOWN`). 348 STRAT-008 veto days scored on Gokul+008 books only.

Command: `python -m backtest_engine --live --years 5 --interval 1 option`  
Artifact (gitignored): `data/recon/BACKTEST_OPTION_2026-09-03.json`

Lean tape = INDEX 1m resampled (3m Gokul / 5m HAUS / 2m Mukul). Money tape = HQ `POST /charts/rollingoption` 1m, then resampled to the same TF. Fill = next option **open**. `expiryCode` **1** (API rejects `0`). NIFTY **WEEK**; BANKNIFTY / SENSEX **MONTH**.

## Data actually used

| Tape | Bars (NIFTY / BANKNIFTY / SENSEX) | Note |
|------|-------------------------------------|------|
| INDEX 1m `IDX_I` 13/25/51 | 524154 / 522920 / 503687 | Signal only. Volume **UNKNOWN** as FUTIDX VWAP. |
| OPTIDX 1m ATM-2 CE / ATM+2 PE | 463733 / 462879 / **204624** | SENSEX **20 empty** 30-day chunks (2021-09 onward). |
| OPTIDX 1m ATM CE / ATM PE | 463839 / 463075 / **245013** | Same SENSEX gap. |
| OPTIDX 1m ATM+1 CE / ATM-1 PE | 463823 / 463102 / **219426** | HAUS 002 only. |

NIFTY / BANKNIFTY rolling `error_count: 0`. SENSEX early history **empty**, not a silent 5y. Do not read SENSEX **IS** wr ~11–15% as a strategy theorem.

## Rating rule (same split as proxy; 02 premium cap)

OOS = last 20% of trades. Need ≥30 IS and ≥30 OOS. Win = option points > 0.

| OOS | Rating |
|-----|--------|
| n < 30 | `DATA_INSUFFICIENT` |
| expectancy_pts ≤ 0 | `FAIL` |
| win_rate < 45% | `FAIL` |
| wr ≥ 45% and exp > 0 | at most **WEAK** (costs UNKNOWN — **not** CANDIDATE) |

**All 24 books: `FAIL`.** `validated: false`. `promote: false`. `keep_current_strategy: true`.

Teacher clubs from [`TRANSCRIPT_ANALYST.md`](../../01_research/docs/handoffs/TRANSCRIPT_ANALYST.md). **002 never on 003.** Supertrend 10,3 **not** re-gridded.

## Scores (option premium, optimistic)

| Book | Underlying | Strike | OOS n | OOS wr | OOS exp | Rating |
|------|------------|--------|------:|-------:|--------:|--------|
| MIX-GOKUL-003-009 | NIFTY | 005_ITM | 2692 | 38.8% | −0.79 | FAIL |
| MIX-GOKUL-003 | NIFTY | 005_ITM | 1887 | 39.2% | −0.56 | FAIL |
| MIX-DEFAULT-BUY | NIFTY | 005_ITM | 1183 | 35.6% | −0.93 | FAIL |
| MIX-GOKUL-003-009 | NIFTY | ATM | 2692 | 35.6% | −1.34 | FAIL |
| MIX-GOKUL-003 | NIFTY | ATM | 1887 | 36.3% | −1.07 | FAIL |
| MIX-DEFAULT-BUY | NIFTY | ATM | 1183 | 33.9% | −1.50 | FAIL |
| MIX-HAUS-001 | NIFTY | 002_OTM | 149 | 34.9% | −2.84 | FAIL |
| MIX-MUKUL-006 | NIFTY | 005_ITM | 1918 | 38.0% | −0.10 | FAIL |
| MIX-GOKUL-003-009 | BANKNIFTY | 005_ITM | 2797 | 40.4% | −0.92 | FAIL |
| MIX-GOKUL-003 | BANKNIFTY | 005_ITM | 1975 | 40.8% | −0.87 | FAIL |
| MIX-DEFAULT-BUY | BANKNIFTY | 005_ITM | 1226 | 38.9% | −1.94 | FAIL |
| MIX-GOKUL-003-009 | BANKNIFTY | ATM | 2797 | 39.4% | −1.79 | FAIL |
| MIX-GOKUL-003 | BANKNIFTY | ATM | 1975 | 39.5% | −1.66 | FAIL |
| MIX-DEFAULT-BUY | BANKNIFTY | ATM | 1226 | 37.9% | −2.01 | FAIL |
| MIX-HAUS-001 | BANKNIFTY | 002_OTM | 159 | 40.9% | −3.93 | FAIL |
| MIX-MUKUL-006 | BANKNIFTY | 005_ITM | 1998 | **43.5%** | +2.32 | FAIL (wr < 45%; exp optimistic) |
| MIX-GOKUL-003-009 | SENSEX | 005_ITM | 2656 | 37.7% | +5.22 | FAIL |
| MIX-GOKUL-003 | SENSEX | 005_ITM | 1863 | 36.9% | +6.49 | FAIL |
| MIX-DEFAULT-BUY | SENSEX | 005_ITM | 1197 | 39.2% | +7.62 | FAIL |
| MIX-GOKUL-003-009 | SENSEX | ATM | 2656 | 39.3% | +4.56 | FAIL |
| MIX-GOKUL-003 | SENSEX | ATM | 1863 | 38.4% | +4.52 | FAIL |
| MIX-DEFAULT-BUY | SENSEX | ATM | 1197 | 39.4% | +7.71 | FAIL |
| MIX-HAUS-001 | SENSEX | 002_OTM | 151 | 41.1% | −0.34 | FAIL |
| MIX-MUKUL-006 | SENSEX | 005_ITM | 1905 | 40.6% | +11.64 | FAIL |

Closest line: **MIX-MUKUL-006 BANKNIFTY** 43.5%. Still **FAIL**. Not a CANDIDATE. Do not p-hack EMA 10/20.

## What this is not

- Not customer P/L. Not lots × rupees. Not after brokerage/STT/spread.
- Not continuous FUTIDX 003. Not NORMAL-only.
- Not a license to grid Supertrend. Not live orders.
- INDEX proxy FAIL ([`BACKTEST_BOOKS_2026-09-03.md`](BACKTEST_BOOKS_2026-09-03.md)) is a **different** object. Do not average the two wr.

```text
HANDOFF
From: 06_backtesting
To:   00 / 02 / 04 / 09
Date: 2026-09-03
Status: option premium ran / ALL FAIL / keep current
Gate: not RESEARCH_READY_FOR_PROGRAMMING

Accepted: rollingoption 1m OPTIDX as P/L; teacher MIX split; ATM vs 2-ITM;
          002 never on 003; OOS 20% / min 30; FAIL wr<45% or exp≤0.
Rejected: promote; CANDIDATE on optimistic exp; ST grid; Mukul 43.5% as edge;
          SENSEX IS ~12% as a theorem (early EMPTY chunks).
UNKNOWN: costs; news calendar; SENSEX 2021–early-22 history; 3m native bars;
          Q12 true fills.

Artifacts:
- data/recon/BACKTEST_OPTION_2026-09-03.json (gitignored)
- this file
```

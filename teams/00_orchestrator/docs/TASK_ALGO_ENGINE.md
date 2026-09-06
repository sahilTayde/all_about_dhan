# TASK_ALGO_ENGINE — paper algos + large-chunk backtest + live data WS

**Owner:** 00_orchestrator (boss) · 04 YAML · 06 engine · 07 WS · 09 notes  
**Date:** 2026-09-03  
**Status:** `IN_PROGRESS` / **UNVALIDATED**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**

Founder ask: define algos, code the paper system, backtest a **big** HQ chunk, rate by win rate, review after each run, Dhan websockets so the customer sees BUY CALL / BUY PUT / HOLD. Coordinate + document.

## Done this ticket

- FUTIDX nearest IDs from public detailed CSV (not hardcoded): NIFTY **68407**, BANKNIFTY **68390**, SENSEX **844615** as of 2026-09-03.
- Paper books: STRAT-003, 001, 006 + filters 007/008/009. KEEP_ALL. No STRAT-015+.
- 5-year INDEX **1m** (~500k bars/index) + current-month FUTIDX 1m. Ratings: **FAIL**. Nothing promotes.
- 5-year **rollingoption** 1m OPTIDX vs INDEX leans (`--interval 1 option`). **All 24 MIX cells FAIL.** Nothing promotes.
- Dhan live-market-feed → API `/ws/signals?live=1` paper copy. Browser never calls Dhan. `place_order` still `SafeModeError`.

## Commands (no npm)

```bash
python -m dhan_client --live futidx
python -m backtest_engine --live --years 5 --interval 1
python -m backtest_engine --live --years 5 --interval 1 option
# API (when you ask): /ws/signals?live=1  and  /ws/feed?live=1
```

## Not done

True NORMAL (news calendar still empty). Continuous FUTIDX IDs (stitch **DATA_INSUFFICIENT** ~64d). Statutory costs. Q12 true fills. Live orders.

**Done 2026-09-06 (not a promote):** hypothesis 1% RT overlay, ISO-week expiry strip, FUTIDX stitch attempt, 09 five-pass **FAILED REVIEW** ([`BACKTEST_HONEST_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)).

**PAPER_WATCH (founder keep):** [`PAPER_WATCH_CLUB_GR.md`](../../04_quant/docs/PAPER_WATCH_CLUB_GR.md) — MIX-CLUB-GR optimistic 69% recorded; paper beside default on `/ws/signals?live=1`. Not customer default. No live orders.

Option-premium path **ran** 2026-09-03 — all books **FAIL** ([`BACKTEST_OPTION_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_OPTION_2026-09-03.md)). Q8 not waived.

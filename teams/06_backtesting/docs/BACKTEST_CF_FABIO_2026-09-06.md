# BACKTEST — Chart Fanatics Fabio OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-FABIO-TREND-NY`, `MIX-CF-FABIO-MR-RANGE`  
**JSON:** `data/recon/BACKTEST_CF_FABIO_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-fabio`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Teacher recipe needs **order-flow aggression** → **`PARKED` / `DATA_INSUFFICIENT`** on Dhan history.
- What ran is **INDEX 3m NIFTY structure proxies only** (failed auction, break-retest, VA reclaim). **Not** Fabio’s bubble trigger.
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **NY / London session → NSE** map = `DATA_INSUFFICIENT`.
- Spoken guest wr / Robbins Cup % are **not** product metrics. Do not paste OOS wr into customer confidence UI.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | Note |
|----------|--------|----------|-------|------|
| TREND / FAILED_AUCTION | **FAIL** | 300 | 60 | OOS expectancy ≤ 0 |
| TREND / BREAK_RETEST_PD | **WEAK** | 1203 | 241 | Mixed; keep BACKTEST_BOOK |
| MR / MR_TO_POC | **FAIL** | 3822 | 765 | OOS expectancy ≤ 0 |

**No promote.** Teacher OF arms stay PARKED.

## Gaps (unchanged)

See `gap_summary()` in `packages/backtest/src/backtest_engine/fabio_proxy.py`: OF bubbles, CVD, footprint, NQ contract filter, session clocks, GEX not in recipe.

## Paper watch

Stub events appended under `data/recon/paper_watch/MIX-CF-FABIO-*` — ledger only, orders refused.

# BACKTEST — Chart Fanatics TG Capital + Trader Kane OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-TG-TRIDENT`, `MIX-CF-TG-EMA-WAVE`, `MIX-CF-KANE-EQ50`, `MIX-CF-KANE-PO3-SMT`  
**JSON:** `data/recon/BACKTEST_CF_TG_KANE_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-tg-kane`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (killzone≈“Kills on”; FVG≈FBG; PO3≈“peer three”; EMA 13 vs 15).
- What ran is **INDEX 3m NIFTY structure proxies only**. **Not** full guest models (TG London 30m killzone + prop psychology; Kane multi-TF PO3 boxes + NQ/ES SMT).
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **London KZ NY → NSE** and **EST 9:15–11 → NSE** = `DATA_INSUFFICIENT`.
- **SMT NQ vs ES** = `DATA_INSUFFICIENT` on single NIFTY — PO3 arm is sweep-reclaim stand-in only.
- Title / guest “**90%** wr” and host payout marketing are **not** product metrics. Do not paste OOS wr into customer confidence UI.
- **No promote.** Separate from Fabio / Marco / Mayne / Marci / Tori / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| TG / FVG_DOJI_CONFIRM | **FAIL** | 7871 | 1575 | ~50.9% | Trident stand-in; London unmapped |
| TG / EMA_STACK_200 | **FAIL** | 25919 | 5184 | ~35.8% | EMA wave+200; mid=13 default |
| KANE / EQ_MID_TOUCH | **FAIL** | 29498 | 5900 | ~45.8% | 50% mid touch; nested EQ missing |
| KANE / PO3_SWEEP_RECLAIM | **WEAK** | 17595 | 3519 | ~50.7% | Sweep reclaim only — **not** SMT; **no promote** |

**No promote.** Session/SMT-timed arms remain `DATA_INSUFFICIENT` (unmapped). WEAK ≠ customer default.

## Gaps (unchanged)

See `gap_summary_tg_kane()` in `packages/backtest/src/backtest_engine/cf_tg_kane_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-TG-*` and `MIX-CF-KANE-*` — ledger only, orders refused.

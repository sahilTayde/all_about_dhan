# BACKTEST — Chart Fanatics Marco + Mayne OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-MARCO-LIQ-TRAP`, `MIX-CF-MARCO-INT-EXT`, `MIX-CF-MAYNE-ICT-HTF`, `MIX-CF-MAYNE-BREAKER`  
**JSON:** `data/recon/BACKTEST_CF_MARCO_MAYNE_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-marco-mayne`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible.
- What ran is **INDEX 3m NIFTY structure proxies only**. **Not** full guest models (Marco induce narrative; Mayne HTF OB stack / FVG sponsorship).
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **NY / Asia / London / crypto HTF → NSE** map = `DATA_INSUFFICIENT`.
- Host marketing ($500K+ / $10M / prop payouts) and guest RR anecdotes are **not** product metrics. Do not paste OOS wr into customer confidence UI.
- **No promote.** Separate from Fabio / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| MARCO / SWEEP_RECLAIM | **WEAK** | 17595 | 3519 | ~50.7% | Structure trap proxy |
| MARCO / EQ_SWEEP | **FAIL** | 9949 | 1990 | ~38.5% | Equal-extreme epsilon HYPOTHESIS |
| MAYNE / MSB_DISCOUNT | **WEAK** | 2130 | 426 | ~50.0% | Half-range stand-in for OB |
| MAYNE / BREAKER | **WEAK** | 303 | 61 | ~55.7% | No HTF OB gate; still UNVALIDATED |

**No promote.** Session-timed arms remain `DATA_INSUFFICIENT` (unmapped).

## Gaps (unchanged)

See `gap_summary_marco_mayne()` in `packages/backtest/src/backtest_engine/cf_marco_mayne_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-MARCO-*` and `MIX-CF-MAYNE-*` — ledger only, orders refused.

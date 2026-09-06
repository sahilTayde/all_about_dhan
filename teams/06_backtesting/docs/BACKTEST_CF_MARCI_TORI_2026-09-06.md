# BACKTEST — Chart Fanatics Marci + Tori OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-MARCI-RIZZY`, `MIX-CF-MARCI-BB-REALITY`, `MIX-CF-TORI-TL-BOUNCE`, `MIX-CF-TORI-TL-BREAK`  
**JSON:** `data/recon/BACKTEST_CF_MARCI_TORI_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-marci-tori`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (rizzie/rizzy; Tory; week≈“weak sort of data”).
- What ran is **INDEX 3m NIFTY structure proxies only**. **Not** full guest models (Marci hand-drawn little rizzie + fundamentals; Tori thick-line fan + 4H week-data + platinum edge).
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **NY-open avoid / 4H week-of-data → NSE** map = `DATA_INSUFFICIENT`.
- Host marketing (#2 futures / ~$500k) and guest playbook wr tables are **not** product metrics. Do not paste OOS wr into customer confidence UI.
- **No promote.** Separate from Fabio / Marco / Mayne / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| MARCI / RIZZY_EXT | **FAIL** | 24068 | 4814 | ~48.6% | Dual-swing measured-move stand-in |
| MARCI / BB_MID_RECLAIM | **FAIL** | 6643 | 1329 | ~47.7% | BB mid reclaim; no rizzie TL |
| TORI / TL_BOUNCE | **FAIL** | 2947 | 590 | ~41.7% | Swing-line tag; thick-line unmapped |
| TORI / TL_BREAK_SAFETY | **FAIL** | 643 | 129 | ~44.2% | Break+nearby safety; fan pivots missing |

**No promote.** Session/instrument-timed arms remain `DATA_INSUFFICIENT` (unmapped).

## Gaps (unchanged)

See `gap_summary_marci_tori()` in `packages/backtest/src/backtest_engine/cf_marci_tori_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-MARCI-*` and `MIX-CF-TORI-*` — ledger only, orders refused.

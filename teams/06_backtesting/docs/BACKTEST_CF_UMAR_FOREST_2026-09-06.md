# BACKTEST — Chart Fanatics Umar Ashraf + Forest Knight OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-UMAR-MORNING-TOP`, `MIX-CF-UMAR-OPENING-DRIVE`, `MIX-CF-FOREST-VPE-EDGE`, `MIX-CF-FOREST-POC-RETEST`  
**JSON:** `data/recon/BACKTEST_CF_UMAR_FOREST_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-umar-forest`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (“Buma Ashraf”≈Umar; “boat”≈close; “PLC”≈POC).
- What ran is **INDEX 3m NIFTY structure (+ bar-volume) proxies only**. **Not** full guest models (Umar OF tape + process stages; Forest true VAP / overnight H/L / 4H 10&2 ET).
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **ET open / cut → NSE** and **overnight Globex → NSE** = `DATA_INSUFFICIENT`.
- **Opening drive** = **named only** → book `DATA_INSUFFICIENT` (no invented ORB).
- **True volume-at-price** = PROJECT bin stand-in; cash INDEX volume quality UNKNOWN (equal-weight fallback).
- Rhetoric “**100%** react” / host payout ads are **not** product metrics. Do not paste OOS wr into customer confidence UI.
- **No promote.** Separate from Fabio / Marco / Mayne / Marci / Tori / TG / Kane / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| UMAR / OPENING_DRIVE named | **DATA_INSUFFICIENT** | — | — | — | Recipe deferred; no leans |
| UMAR / GAP_FAIL_BOUNCE | **WEAK** | 414 | 83 | ~45.8% | Morning-top stand-in; OF missing; IST window; **no promote** |
| FOREST / PDH_PDL_RELVOL | **FAIL** | 8147 | 1630 | ~48.5% | VPE edge stand-in; overnight/VAP missing |
| FOREST / BIN_POC_VAL | **FAIL** | 11095 | 2219 | ~39.4% | Prior bin POC/VAL; not exchange VAP |

**No promote.** WEAK ≠ customer default. DI opening-drive remains until a later SOURCE_FACT recipe.

## Gaps (unchanged)

See `gap_summary_umar_forest()` in `packages/backtest/src/backtest_engine/cf_umar_forest_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-UMAR-*` and `MIX-CF-FOREST-*` — ledger only, orders refused.

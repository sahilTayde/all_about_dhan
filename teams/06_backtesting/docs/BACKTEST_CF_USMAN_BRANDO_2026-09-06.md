# BACKTEST — Chart Fanatics Usman Ashraf + Brando/Leaf OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-USMAN-OI-STRIKE`, `MIX-CF-USMAN-0DTE-GAMMA`, `MIX-CF-USMAN-WEEKLY-SIZE`, `MIX-CF-USMAN-PRICE-STOP`, `MIX-CF-BRANDO-HTF-RECLAIM`, `MIX-CF-BRANDO-ROUND-BREAK`, `MIX-CF-BRANDO-HTF-BOUNCE`, `MIX-CF-BRANDO-SIZE-ZERO`, `MIX-CF-BRANDO-NEWS-ALIGN`  
**JSON:** `data/recon/BACKTEST_CF_USMAN_BRANDO_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-usman-brando`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (“Osman Astra”; “brand-a-k-a-leaf”).
- What ran is **INDEX 3m NIFTY structure proxies** for three Brando arms only. **Not** Usman OI/greeks/weekly-size/price-stop; **not** Brando news or size-zero.
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **US equity / SPX / 0DTE → NSE OPTIDX** = `DATA_INSUFFICIENT`.
- Title **$6k→$10M** / “80%+” / seven-figure ads are **not** product metrics.
- Usman vs Brando stop philosophy conflict kept as **separate** KEEP_ALL rows.
- **No promote.** Separate from prior CF / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| USMAN / OI_STRIKE | **DATA_INSUFFICIENT** | — | — | — | No OPTIDX OI book |
| USMAN / 0DTE_GAMMA | **DATA_INSUFFICIENT** | — | — | — | No greeks / expiry map |
| USMAN / WEEKLY_SIZE | **DATA_INSUFFICIENT** | — | — | — | Management premium% |
| USMAN / PRICE_STOP | **DATA_INSUFFICIENT** | — | — | — | Entry LOI not frozen |
| BRANDO / SIZE_ZERO | **DATA_INSUFFICIENT** | — | — | — | Premium ledger |
| BRANDO / NEWS_ALIGN | **DATA_INSUFFICIENT** | — | — | — | News join unmapped |
| BRANDO / SWING_RECLAIM | **FAIL** | 156 | 32 | ~50.0% | HTF reclaim stand-in; multi-year majors missing |
| BRANDO / ROUND100 | **WEAK** | 358 | 72 | ~58.3% | Round break; **no news**; transfer unresolved — **no promote** |
| BRANDO / SWING_TOUCH_REJECT | **FAIL** | 547 | 110 | ~46.4% | Bounce/defend stand-in |

**No promote.** WEAK ≠ customer default. DI arms remain until OPTIDX/news paths exist.

## Gaps (unchanged)

See `gap_summary_usman_brando()` in `packages/backtest/src/backtest_engine/cf_usman_brando_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-BRANDO-*` — ledger only, orders refused.

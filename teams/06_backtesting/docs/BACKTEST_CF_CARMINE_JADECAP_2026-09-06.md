# BACKTEST — Chart Fanatics Carmine Rosato + Jadecap OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-CARMINE-ABSORB`, `MIX-CF-CARMINE-FAIL-BREAK`, `MIX-CF-CARMINE-OPEN-HOLD`, `MIX-CF-JADECAP-SWING-FAIL`, `MIX-CF-JADECAP-SESSION-LIQ`, `MIX-CF-JADECAP-FVG-DRAW`  
**JSON:** `data/recon/BACKTEST_CF_CARMINE_JADECAP_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-carmine-jadecap`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (“Car mine”; “rate”≈raid).
- What ran is **INDEX 3m NIFTY structure proxies only**. **Not** full guest models (Carmine DOM/heatmap/footprint/delta; Jade Asia/London/midnight open).
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **ET sessions → NSE** = `DATA_INSUFFICIENT`.
- **Carmine absorb** = OF-required → book `DATA_INSUFFICIENT` / PARKED (no invented delta).
- **Jade session-liq** = Asia/London/NY unmapped → `DATA_INSUFFICIENT`.
- Dollar P/L anecdotes (May $203k) / Apex payout ads are **not** product metrics. Do not paste OOS wr into customer confidence UI.
- Carmine fail-break vs Jade swing-fail share PDH/PDL reclaim geometry but remain **separate KEEP_ALL rows** (different teachers/recipes).
- **No promote.** Separate from Fabio / Marco / Mayne / Marci / Tori / TG / Kane / Umar / Forest / STRAT / IQ.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| CARMINE / ABSORB OF | **DATA_INSUFFICIENT** | — | — | — | No India tape; PARKED |
| JADECAP / SESSION_LIQ | **DATA_INSUFFICIENT** | — | — | — | Asia/London/NY clocks unmapped |
| CARMINE / PDH_PDL_RECLAIM | **FAIL** | 570 | 114 | ~42.1% | Stop-hunt structure stand-in; OF missing |
| CARMINE / SESSION_OPEN_HOLD | **DATA_INSUFFICIENT** | 59 | 12 | ~75%* | Too few OOS (need 30); IST open stand-in; *n tiny |
| JADECAP / PDH_PDL_CLOSE_RECLAIM | **FAIL** | 565 | 113 | ~46.0% | Swing-fail homework stand-in; separate from Carmine/Marco |
| JADECAP / SWEEP_THEN_FVG | **WEAK** | 236 | 48 | ~47.9% | Liq→FVG stand-in; full ICT not frozen; **no promote** |

**No promote.** WEAK ≠ customer default. DI arms remain until tape / session map exists.

## Gaps (unchanged)

See `gap_summary_carmine_jadecap()` in `packages/backtest/src/backtest_engine/cf_carmine_jadecap_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-CARMINE-*` and `MIX-CF-JADECAP-*` — ledger only, orders refused.

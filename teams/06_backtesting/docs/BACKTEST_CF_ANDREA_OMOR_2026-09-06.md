# BACKTEST — Chart Fanatics Andrea Cimi + Omor/NBB OHLC proxies (2026-09-06)

**Team:** 06_backtesting  
**Mix ids:** `MIX-CF-ANDREA-FAIL-AUCTION`, `MIX-CF-ANDREA-ORB-ACCEPT`, `MIX-CF-ANDREA-STOP-FADE`, `MIX-CF-ANDREA-ABSORB`, `MIX-CF-OMOR-MMM-FRAME`, `MIX-CF-OMOR-OTE`, `MIX-CF-OMOR-PDH-REVERSAL`, `MIX-CF-OMOR-KZ-ADR`  
**JSON:** `data/recon/BACKTEST_CF_ANDREA_OMOR_2026-09-06.json`  
**CLI:** `python -m backtest_engine --dry-run --years 2 cf-andrea-omor`  
**Promote:** **false**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Honesty

- Transcripts are **`ASR_WHISPER` / `[ASR]`** — not YouTube captions. Noun errors possible (“Andrea Chimney”; “Omore/MBB”).
- Guest on `TvoQr6ObjnU` is **Andrea Cimi** — **not** Fabio; do **not** merge into `MIX-CF-FABIO-*`.
- What ran is **INDEX 3m NIFTY structure proxies** for six arms. Andrea absorb + Omor KZ/ADR = **DATA_INSUFFICIENT**.
- Unit = **index points proxy**, not option premium. Costs not modeled as OPTIDX.
- **ES OF / FX ICT → NSE OPTIDX** = `DATA_INSUFFICIENT`.
- “70%” VA / “8/10” fade / live $ / 30M+1.1M payouts / OTE RR tables are **not** product metrics.
- **No promote.** Separate from prior CF / STRAT / IQ / Fabio.

## Results (proxy, NIFTY 2y cache)

| Book arm | Rating | Trades n | OOS n | OOS wr (proxy) | Note |
|----------|--------|----------|-------|----------------|------|
| ANDREA / OF_ABSORB | **DATA_INSUFFICIENT** | — | — | — | Footprint/DOM PARKED |
| OMOR / KZ_ADR | **DATA_INSUFFICIENT** | — | — | — | No IST killzone map |
| ANDREA / PD_RANGE_RECLAIM | **DATA_INSUFFICIENT** | 88 | 18 | ~50.0% | Need ≥30 OOS; no true VP VA |
| ANDREA / ORB_HOLD | **FAIL** | 1100 | 220 | ~48.2% | IST OR stand-in; no OF acceptance |
| ANDREA / PDH_PDL_FADE | **FAIL** | 563 | 113 | ~45.1% | Stop-fade stand-in; no cascade tape |
| OMOR / BIAS_SWEEP_DISPLACE | **FAIL** | 206 | 42 | ~45.2% | MMM framework proxy; FX→NIFTY DI |
| OMOR / FIB62_RETRACE | **WEAK** | 811 | 163 | ~55.2% | OTE stand-in; transfer unresolved — **no promote** |
| OMOR / OPEN_NEAR_SWEEP | **DATA_INSUFFICIENT** | 107 | 22 | ~45.5% | Need ≥30 OOS; Asia/London missing |

**No promote.** WEAK ≠ customer default. DI/PARKED arms remain until OF/KZ paths exist.

## Gaps (unchanged)

See `gap_summary_andrea_omor()` in `packages/backtest/src/backtest_engine/cf_andrea_omor_proxy.py`.

## Paper watch

Stub events under `data/recon/paper_watch/MIX-CF-ANDREA-*` and `MIX-CF-OMOR-*` — ledger only, orders refused.

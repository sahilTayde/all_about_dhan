# 03 — Market notes on Marci + Tori CF binds (Phase-5)

**Team:** 03_phd_market  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` microstructure / transfer  
**Binds:** [`AVVM-FyewLg_BIND.md`](../../01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md), [`VTEQ2fhGLqE_BIND.md`](../../01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md)

## Marci — asset & session

| Spoken | NSE transfer |
|--------|----------------|
| SPX / NDX / QQQ crash history; BTC; single-name HHH | **Not 1:1** with NIFTY INDEX or OPTIDX |
| Prefers longer TFs; also 5m/1m fractal | NSE bar availability OK for OHLC proxy; crash-fundamental overlay ≠ Indian macro auto |
| Hates **NY open**; likes London / other opens; day-seasonality anecdote | NSE **09:15 IST** ≠ NY RTH; map = `DATA_INSUFFICIENT` |

## Tori — asset & session

| Spoken | NSE transfer |
|--------|----------------|
| Swing **4H** primary; platinum preferred; copper live; crude bounce harder | Commodity futures microstructure ≠ NIFTY OPTIDX lots/expiry |
| “Week of data” on 4H between touches | 3m NIFTY bar-span stand-in = `DATA_INSUFFICIENT` for exact week |
| Sit out ranges; FOMO on aggressive tariff/tweet moves | Event path — hold ticket / remember event type; not catalog delete |

## Shared gaps

- **GEX / dealer / option chain:** **not in either recipe** — do not invent India GEX filter.  
- **OF / footprint:** not required — Marci mentions OF as alternate lens only.  
- **Lots / fills:** do not invent from prop-firm / platinum margin stories.  
- **ASR quality:** `[ASR]` — treat garbled nouns as UNKNOWN.

## CAS / clocks

No Closing Auction Session content. Do not attach `CAS-*`.

## Verdict

Keep `MIX-CF-MARCI-*` and `MIX-CF-TORI-*` as **EXTERNAL** separate books. India path = OHLC **proxy** or stay honest `DATA_INSUFFICIENT` on session/instrument arms. **Do not veto** guest recipes for transfer risk alone.

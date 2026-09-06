# 03 — Market notes on Fabio CF bind (`tvERE-Beu2U`)

**Team:** 03_phd_market  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` microstructure / transfer  
**Bind:** [`../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md`](../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md)

## Asset & session

| Spoken | NSE transfer |
|--------|----------------|
| NASDAQ / NQ (futures division, Robbins Cup context) | **Not 1:1** with NIFTY INDEX or OPTIDX |
| New York session primary for trend model | NSE regular session **09:15–15:30 IST** ≠ NY RTH; map = `DATA_INSUFFICIENT` |
| London mean-revert window | No London cash clock on NSE F&O |
| Overnight flat (futures margin) | Index options have different overnight / expiry mechanics |

## Microstructure gaps

- **Order-flow bubbles / footprint / CVD:** required for teacher trigger; Dhan client path for historical OF = `DATA_INSUFFICIENT` (aligns with STRAT-010 PARKED class of gap).  
- **GEX / dealer / option chain:** **not in recipe** — do not invent India GEX filter for these MIX ids.  
- **Lots / fills:** do not invent from NQ mini contract $ examples.  
- **Failed auction / liquidity sweep language:** transferable as **price-structure hypothesis** only; OF confirmation missing.

## CAS / clocks

No Closing Auction Session content in this video. Do not attach `CAS-*`.

## Verdict

Keep `MIX-CF-FABIO-TREND-NY` and `MIX-CF-FABIO-MR-RANGE` as **EXTERNAL** books. India paper path = OHLC **proxy** or stay PARKED. **Do not veto** guest recipe for transfer risk alone.

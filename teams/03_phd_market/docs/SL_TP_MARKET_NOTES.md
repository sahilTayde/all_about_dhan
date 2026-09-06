# SL/TP market notes (NIFTY objects + GEX transfer)

**Team:** 03_phd_market  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` / `UNKNOWN`  
**Cites:** [`CHAIN_METRICS.md`](CHAIN_METRICS.md), [`SL_TP_EXTERNAL_HARVEST.md`](../../01_research/docs/SL_TP_EXTERNAL_HARVEST.md)

| Exit object | NIFTY instrument | Liquidity / honesty |
|-------------|------------------|---------------------|
| ATR / ST / swing on **INDEX** | `INDEX` sid 13 (cash) | Proxy only; spoken 003 prefers **FUTIDX** |
| ATR / ST on **FUTIDX** | Front+back months | Continuous stitch still `DATA_INSUFFICIENT` (honest 2026-09-06) |
| Premium % TP | **OPTIDX** CE/PE LTP | Needs rollingoption; costs matter |
| GEX / call wall / gamma flip | US equity options context on IQCapital tape | **Transfer risk:** India index options GEX feed **not in repo** → do not claim edge |

**GEX transfer caveat (hard):** Positive/negative GEX and call/put walls from US 0DTE/dealer models are **not** interchangeable with NSE NIFTY weekly OPTIDX without a documented India GEX construction. Use as **regime vocabulary / hold filter hypothesis** only.

```text
HANDOFF From:03 To:04/06 Accepted: INDEX vs FUTIDX vs OPTIDX split; GEX transfer flagged.
Rejected: inventing NIFTY GEX walls. UNKNOWN: statutory costs; FUTIDX history IDs.
```

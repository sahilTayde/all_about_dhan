# BACKTEST_SCAN_REVIEW — 2026-09-03 (NOTES_ONLY)

**Team:** 09_review  
**Status:** `NOTES_ONLY` — **not** a five-pass  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Source:** [`BACKTEST_SCAN_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_SCAN_2026-09-03.md)

Twenty **WEB-DERIVED / PROJECT_MIX** scan books. Not teacher clubs. Not customer default. Supertrend / MACD / RSI were **not** the entry (founder freeze).

| Item | Call |
|------|------|
| MIX-ORB-15 / ORB-VWAP / CPR-ORB | **FAIL** on 730d. Folklore is not an edge here. |
| MIX-GAP NIFTY 730d 48% | **WEAK** then **5y FAIL** (exp ≤ 0). Do not promote a 2y-only wr. |
| MIX-ENGULF / MIX-INSIDE-BRK NIFTY ~47% | **WEAK**. Costs UNKNOWN. **Did not** replicate on SENSEX (~27%). Multiple testing. **Not** CANDIDATE |
| Swap ENGINE_MIX default to engulf/inside/gap | **REJECT** |
| Grid candle / ORB T / Donchian n after wr | **REJECT** |
| Relabel WEB/PATTERN as DHAN-DERIVED | **REJECT** |
| 30d NR7 60% (n=5) | **SCREEN only** — **REJECT** as evidence |
| Q8 / Q12 | **still FAILED** (next-bar-open; costs UNKNOWN) |
| KEEP_ALL / no STRAT-015+ | **ACCEPT** |
| Five-pass / research-ready | **not passed / not set** |

02 math: three of forty 730d cells clearing wr≥45% **and** exp>0 is the **best-of-k** pattern the scan charter already named. 5y killed GAP. Remaining two are still optimistic premium, still UNVALIDATED.

```text
HANDOFF
From: 09
To:   00
Accepted: scan ran; SCREEN vs 730d vs 5y labeled; origin tags held; default held.
Rejected: RESEARCH_READY; promote 47–48%; treat 30d screens as edge; live orders.
UNKNOWN: after-cost NORMAL; family-wise error; FUTIDX stitch.
```

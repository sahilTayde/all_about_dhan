# BACKTEST_PROJECT_REVIEW — 2026-09-03 (NOTES_ONLY)

**Team:** 09_review  
**Status:** `NOTES_ONLY` — **not** a five-pass  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Source:** [`BACKTEST_PROJECT_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_PROJECT_2026-09-03.md)

Two **PROJECT_MIX** books (Murphy MTF + desk 5m MACD confirm). Not teacher clubs. Not customer default.

| Item | Call |
|------|------|
| MIX-MTF-TREND NIFTY/SENSEX | **FAIL** / keep / **do not promote** |
| MIX-CONFIRM-5M NIFTY 42.5% OOS wr | **FAIL** (exp ≤ 0). Closest of the pair — **not** CANDIDATE |
| Swap ENGINE_MIX default to either | **REJECT** |
| Grid MACD or Supertrend after wr | **REJECT** |
| Relabel PROJECT as DHAN-DERIVED | **REJECT** |
| Q8 / Q12 | **still FAILED** (next-bar-open; costs UNKNOWN) |
| KEEP_ALL / no STRAT-015+ | **ACCEPT** |
| Five-pass / research-ready | **not passed / not set** |

```text
HANDOFF
From: 09
To:   00
Accepted: isolated PROJECT tests ran; FAIL; labels held.
Rejected: RESEARCH_READY; promote 42.5%; live orders.
UNKNOWN: after-cost NORMAL; FUTIDX stitch.
```

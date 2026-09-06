# BACKTEST_SCAN_CLOCK_REVIEW — 2026-09-03 (NOTES_ONLY)

**Team:** 09_review  
**Status:** `NOTES_ONLY` — **not** a five-pass  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Source:** [`BACKTEST_SCAN_CLOCK_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_SCAN_CLOCK_2026-09-03.md)

Founder dead band (09:00–09:30 and 15:00–15:30 IST) plus a walk-forward logit. Not a customer default.

| Item | Call |
|------|------|
| MIX-ML-LOGIT NIFTY 55.7% wr | **FAIL**. Expectancy **negative**. Wr without exp is not an edge. |
| MIX-GAP NIFTY 55% / 5y 54% | **WEAK**. n_OOS=100 on 2y. Costs UNKNOWN. SENSEX FAIL. **Not** CANDIDATE |
| MIX-ENGULF NIFTY ~48% | **WEAK**. SENSEX 26.8%. Multiple testing. |
| MIX-ML-LOGIT-XR | **WEAK**. Same 2y=5y sample (train cutoff). Do not retune 0.55/0.45 after wr. |
| Swap MIX-DEFAULT-BUY | **REJECT** |
| Grid ML / candle after wr | **REJECT** |
| Relabel ML as DHAN-DERIVED | **REJECT** |
| Q8 / Q12 | **still FAILED** |
| KEEP_ALL / no STRAT-015+ | **ACCEPT** |
| Five-pass / research-ready | **not passed / not set** |

02: a classifier can be right more than half the time and still lose the option book (small wins, large losses). That is why the charter scores **wr and optimistic exp**, not wr alone.

```text
HANDOFF
From: 09
To:   00
Accepted: clock applied; ML not trained on premium; 55% wr FAIL named.
Rejected: RESEARCH_READY; promote GAP 55%; live orders.
UNKNOWN: after-cost NORMAL; family-wise error.
```

# STRAT-010 — Order-flow delta / POC overlay

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT` / `DATA_INSUFFICIENT`  
**Origin:** `DHAN-DERIVED` tool (YUXJv_xBStw) + `PROJECT-DERIVED` rules (video has **no** entry recipe)

**HYPOTHESIS (ours, tagged):** only take 003/001 entries if **futures** footprint **volume-delta** agrees with direction on the signal candle (or last closed 1m/5m); optional POC not to be faded. Imbalance ≥3× as spoken default.

**Greek delta ≠ volume delta.**

## Invalidation

No historical footprint in DhanHQ → cannot backtest → stay `DATA_INSUFFICIENT`. Do not proxy with cash-index ticks.

## Risk

DEXT-only data; not in Phase-1 API plan. Overlay must not block engine design.

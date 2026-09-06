# STRAT-008 — Mixed-index avoid

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (2RnBT9 01:08:37–01:11:19)  
**Filter / sizing.**

If STRAT-003 (or 001) is **long** on NIFTY and **short** on BANKNIFTY (or any pair of {NIFTY, BANKNIFTY, SENSEX}): **no new trades** that day, **or** trade only a pre-declared **dominant** index — never both sides.

If all aligned: optional **1 lot each** vs 3 lots in one — size test, not an edge claim.

SENSEX is BSE — alignment uses **each market’s** future, not a fake combined volume.

## Invalidation

Avoid-days still lose on the dominant index at the same rate (filter useless) or kill too many trades for sample size (`DATA_INSUFFICIENT`).

## Risk

Look-ahead if “dominant” is chosen after the close.

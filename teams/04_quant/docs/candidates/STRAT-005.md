# STRAT-005 — High-delta ITM / ATM buy (0.60–0.75)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (2RnBT9 38:06–39:20, 01:02:16–01:03:50)

```yaml
strategy_id: STRAT-005
call_delta_abs: [0.60, 0.75]   # spoken 0.63–0.74; RSI analogy 50–75
put_delta: negative_of_same
avoid_abs_delta_gt: 0.74
fallback_if_no_liquidity: nearest_ATM_or_1_ITM
avoid_50_multiples: TEST_ON_OFF  # host vs guest disagree
```

OTM **not** recommended **in this video** (conflicts STRAT-002). Ablate.

If delta missing in history: map “1–2 strikes ITM” from **spot** at signal time (spoken).

## Invalidation

Higher debit + worse % RR after costs vs 002 on same signals.

## Risk

Capital: 1 ITM lot may exceed RM. Delta ≠ win rate (math team).

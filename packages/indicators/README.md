# packages/indicators

V2-05 feature engine. Incremental EMA, ATR, VWAP/TWAP, realised vol, and lagged OI
change from **closed** bars only (V2-03 `BarBuilder`). Paper only. No broker calls.

VWAP keeps `sum_pv`/`sum_v` separate from TWAP `sum_p`/`n`. After the first volume
bar, zero-volume bars contribute nothing. OI change uses snapshots with
`ts < floor_minute(decision_ts)` in IST. `FeatureEngine.view(now=...)` requires `now`.

`FeatureView(strict=True)` raises `LookAheadError` if a value's `available_ts` is after
`clock.now()`. Strategies treat a missing/warming-up feature as no signal.

REG-01e (prior-day levels) and REG-01f (refuse a future-dated state file) are **not**
in this ticket: REG-01e is V2-05b entry-location; REG-01f waits for feature-state
persistence.

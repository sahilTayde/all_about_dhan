# packages/indicators

V2-05 feature engine. Incremental EMA, ATR, VWAP/TWAP, realised vol, and lagged OI
change from **closed** bars only (V2-03 `BarBuilder`). Paper only. No broker calls.

VWAP keeps `sum_pv`/`sum_v` separate from TWAP `sum_p`/`n`. After the first volume
bar, zero-volume bars contribute nothing. Non-finite price/volume and negative
volume are rejected (not accumulated) and counted on `vwap_rejected_bars`. OI
change uses snapshots with `ts < floor_minute(decision_ts)` in IST. Naive OI
timestamps are rejected at ingest; other zones convert to IST.
`FeatureEngine.view(now=...)` requires a timezone-aware `now` (naive raises
`ValueError`).

`FeatureView(strict=True)` raises `LookAheadError` if a value's `available_ts` is after
`clock.now()`. Strategies treat a missing/warming-up feature as no signal.

Deferred (not in this ticket):

- REG-01e prior-day levels — V2-05b entry-location
- REG-01f refuse a future-dated state file — persistence ticket
- Daily HAR forecast — V2-18
- RegimeLabeller / shadow adapters — V2-07

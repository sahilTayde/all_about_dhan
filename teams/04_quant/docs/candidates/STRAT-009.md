# STRAT-009 — Open skip + 15:15 flatten

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (2RnBT9 23:48–24:03)  
**Filter.** Complements 007 (different speaker clocks — **do not silently merge**).

```yaml
strategy_id: STRAT-009
ignore_bars: 09:15-09:45
flatten_all: before 15:15 Asia/Kolkata
overnight: false
```

F&O close 15:30 vs 15:40: `VERIFY`. Flatten **before** close-VWAP window.

## Invalidation

Open-hour trades (if tested separately) have better risk-adjusted stats after costs — then this filter is a preference, not an edge.

## Risk

15:15 flatten in a 15:40 close world leaves 25 minutes unused — document as-of rule.

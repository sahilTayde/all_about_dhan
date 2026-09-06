# STRAT-014 — Hedged 1-3-2 call ratio (Monday 09:45)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT` / **`WAITING` (not Phase-1 buy UI)** / **`BACKTEST_BOOK`** (`KEEP_ALL` — not deleted; [`MIX_CATALOG.md`](../MIX_CATALOG.md) `MIX-SELL-014`, style `OPTION_SELLER`)  
**Origin:** `DHAN-DERIVED` (`6el9Jqnrdz8` EN 41:29–44:16). Bind **CONFIRMED sell / ratio**. Tuesday NIFTY expiry is **recording-dated** (VERIFY).  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)

```yaml
strategy_id: STRAT-014
underlying: NIFTY
entry: Monday 09:45
exit: Friday EOD
weekend_carry: false
expiry: next_Tuesday_weekly   # VERIFY calendar
structure_if_spot_S:
  buy_1: S+200_call
  sell_3: S+400_call
  buy_2: S+600_call
target_stop: 1_percent_of_capital_each
avoid_50_strikes: true
adjustments: none
```

BANKNIFTY monthly-only caveat in video. POP 80% **unsupported**.

**Not Phase-1 buy UI.**

## Invalidation

1% stop/target after costs and partial fills; gap days (speaker’s own 200/1600-pt stories).

## Risk

Short 3 vs long 3 is defined if filled as a basket; **leg risk** if not. Margin ~spoken 1.3–1.4L `[UNCERTAIN_TRANSCRIPT]`.

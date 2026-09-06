# STRAT-006 — 2-minute EMA 10/20 ITM scalp

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (`pvmvkiS1cx4` EN)  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Not claimed profitable.**

```yaml
strategy_id: STRAT-006
underlyings: [NIFTY, BANKNIFTY, SENSEX]   # CONFIRMED
analysis: spot_OHLC                       # speaker; futures may be more honest — TEST
execution: INDEX_OPTION_BUY
tf: 2m                                    # CONFIRMED; not an HQ interval
ema: [10, 20]                             # CONFIRMED intended pair (chart default 9/26 is UI noise)
strike: ITM_100_to_200_points             # CONFIRMED all three; not ATM, not OTM, not deep ITM
delta: [0.55, 0.60]                       # WEAK [UNCERTAIN_TRANSCRIPT] "555 to 6" / "0.55 to six" — do not freeze
beginner_caution: VIX_above_15_to_16      # spoken condition, not a blanket ban
```

Entry/exit: EMA alignment + PA around “stop clusters” (second-pass detail in transcript ~07:00+).

**Beginner caution (restore spoken condition):** if **India VIX is above 15–16**, beginners should **not** scalp by **buying** options; selling or hedging mentioned as the alternative (`pvmvki` 13:06–13:16). This is **conditional**, not a blanket “beginners must never buy-scalp.” Keep both: the ITM-buy recipe **and** the VIX/beginner warning. Bind on the old blanket line: **WEAK**.

Delta band stays **WEAK**. Do not freeze 0.55–0.60 as if clearly spoken.

## Invalidation

After half-spread + statutory costs, expectancy ≤ 0 (expected for many scalps). Then `REJECTED` honestly.

## Risk

Highest execution sensitivity in this set. Skip if stop > spoken bound. 2m = resample hypothesis vs HQ `{1,5,15,25,60}`.

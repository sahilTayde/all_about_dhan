# STRAT-003 — Futures VWAP + VWMA(20) + Supertrend (“103” → 10,3 WEAK)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (`2RnBT9DDDNI` EN 20:57–40:56). Same-video Gokul stack with 004/005/008/009 — **not** `PROJECT_MIX`.  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Primary index-options candidate. Not claimed profitable.**

```yaml
strategy_id: STRAT-003
name: Fut_VWAP_VWMA_ST_3m
timeframe: {primary: 3m}          # CONFIRMED spoken; not an HQ {1,5,15,25,60} interval
chart: INDEX_FUTURES              # not cash index; not stock options this class
indicators:
  VWAP: session_default           # CONFIRMED
  VWMA: {length: 20}              # CONFIRMED
  Supertrend:
    spoken_raw: "103"             # WEAK [UNCERTAIN_TRANSCRIPT] — not spoken "ten comma three"
    inferred: {atr: 10, multiplier: 3}  # inference from "103" + H_6kee "10 3" (stock/gold)
ignore_open: 09:15-09:45          # same speaker, CONFIRMED (also STRAT-009)
flatten_before: 15:15             # same speaker; VERIFY vs 15:30/15:40 close
call_if: close > VWAP AND close > VWMA AND close > Supertrend
put_if: close < all_three
no_new_entry_if: Supertrend_direction != VWAP_side
exit: 3m close through Supertrend
min_rr: 1.0
prefer_rr: 2.0
strike: STRAT-005 default         # ITM/ATM; OTM not recommended in this video — never STRAT-002
```

Keep the **3m Gokul recipe**. All-three AND is CONFIRMED. Exit: 3m close the other side of Supertrend; **do not** cost-to-cost trail on ST (CONFIRMED).

**Do not AND Himanshu 007 into this yaml as if Gokul taught 10:00 start.** 007∧009 on the Phase-1 ticket is **`PROJECT_MIX`** in [`ENGINE_MIX.md`](../ENGINE_MIX.md).

VWMA = pullback engine (optional re-entry).

## Data

Futures OHLC+volume; strike from **spot** at signal (005); option quotes.

## Invalidation

Cash-index VWAP used; or no edge vs buy-hold-session after costs; or BANKNIFTY monthly-only liquidity too thin on chosen expiry; or 002 attached as strike overlay.

## Risk

3m close stop gaps; mixed NIFTY/BN days (use 008). Supertrend params **WEAK** on this video’s digits.

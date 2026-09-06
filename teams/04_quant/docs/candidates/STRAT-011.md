# STRAT-011 — RSI + Supertrend child (index transfer)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** **`PROJECT_MIX`**. Pieces are `DHAN-DERIVED`; **index-option buy is not**.  
**Not** “Dhan said trade NIFTY options this way.”  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Not claimed profitable.**

```yaml
strategy_id: STRAT-011
origin: PROJECT_MIX
parent_h6kee: RSI_oversold_plus_green_candle   # H_6kee: equity / gold / silver — NO index options in EN
child_h6kee: Supertrend_10_3_close_through     # ST 10,3 CONFIRMED on that video (stock/gold)
gA5_view: RSI_divergence_on_NIFTY_2h           # bullish view CONFIRMED
gA5_executed: BULL_PUT_CREDIT                  # SELL — STRAT-013. Do NOT map this fill to buy CE/PE
horizon_intraday_buy: PROJECT_MIX              # gA5 said if intraday he would buy; this video filled a credit spread (CONFLICT)
horizon_swing: WAITING                         # selling / 013
```

`H_6keeRUCDM`: parent RSI oversold + green candle; child Supertrend close-through; buy above that high. Universe spoken = **equity or gold/silver**. ST default **10, 3** CONFIRMED there. RSI **period not named** (Wilder 14 = VALIDATION default, not Dhan-spoken).

`gA5FtEnSABM`: NIFTY 2h RSI **divergence** → slightly bullish **view**. **Will not become an option buyer** on that swing horizon (theta). “If I were to do this **intraday**, I would be **buying** options. However, for now, I'm teaching you how to **sell**.” **Executes a bull put spread.** Mapping the same view to Phase-1 **buy CE/PE** is **`PROJECT_MIX`** and **`CONFLICT`** with the executed example. **Do not map gA5 bull put to buy CE.**

Phase-1 test (still `UNVALIDATED` transfer): 1h or 2h RSI vs price LL/HH on **index futures**; 5m/15m ST; **buy** index option only as a labeled `PROJECT_MIX` ablation — strike 005 or 002 follows **that** test’s primary, not a silent gA5 conversion.

## Invalidation

Divergence rate of false positives after costs; or only works on stocks (no transfer); or the test “codes gA5’s fill as a CE buy.”

## Risk

RSI period not spoken. Index use is **`PROJECT_MIX`**. Selling fill must stay on 013.

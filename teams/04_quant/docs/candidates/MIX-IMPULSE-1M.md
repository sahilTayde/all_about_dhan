# MIX-IMPULSE-1M — 1m close vs short lookback

**Team:** 04 · **Status:** `WAITING` / `UNVALIDATED` / `customer_default: false` / `NO_PROMOTE`  
**Origin:** `PROJECT-DERIVED` · **Not** STRAT-015+ · **Not** FUTIDX 1m SOURCE_FACT.

Lookback = last 5 INDEX 1m closes. Fraction threshold is HYPOTHESIS. ATM LTP fills Entry/SL/TP only; never paste index points as premium. Empty SL/TP if no LTP. Stage WATCH/EARLY — never CONFIRMED.

```yaml
mix_id: MIX-IMPULSE-1M
origin: PROJECT-DERIVED
styles: [OPTION_BUYER, SCALPER]
inputs: [INDEX_1m, optionchain_atm_ltp]
lookback_bars: 5
customer_default: false
status: WAITING
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-LEAN-SPOT-ATM]
```

**Cite:** 04 `SIGNAL_STAGING.md` L1 impulse. 03 INDEX ≠ FUTIDX. 05 ticket numbers = option premium. 06 no promote on proxy. 09 notes ≠ pass.

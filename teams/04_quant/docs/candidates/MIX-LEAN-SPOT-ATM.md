# MIX-LEAN-SPOT-ATM — gather INDEX last + ATM wall

**Team:** 04 · **Status:** `WAITING` / `UNVALIDATED` / `customer_default: false` / `NO_PROMOTE`  
**Origin:** `PROJECT-DERIVED` (not a `@DhanHQ` recipe; not `STRAT-015+`)  
**Layers:** INDEX last + Dhan `POST /optionchain` ATM/PCR = `SOURCE_FACT` when live gather works; CE/PE lean = `HYPOTHESIS`; 03 PCR-without-price hold = `VALIDATION`.

Does **not** rewrite `MIX-DEFAULT-BUY`. EARLY is a valid ticket. 5m Supertrend/MACD remains **confirm-or-kill** — this MIX never emits `CONFIRMED`.

```yaml
mix_id: MIX-LEAN-SPOT-ATM
origin: PROJECT-DERIVED
styles: [OPTION_BUYER]
inputs: [INDEX_last, optionchain_atm_wall, pcr_oi]
lean: BUY_CE_or_BUY_PE
stage: WATCH_or_EARLY
sl_tp: ATM_LTP_or_empty
customer_default: false
status: WAITING
metrics: {win_rate: null}
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, STRAT-001, STRAT-003]
```

**Cite:** 01 `TRANSCRIPT_STRATEGY_BIND.md` (no spoken “spot+ATM MIX”). 02 `DHAN_INDICATOR_API_MAP.md` (charts = OHLC). 03 `CHAIN_METRICS.md`. 04 `SIGNAL_STAGING.md`. 05 `CUSTOMER_TALK.md` / `CUSTOMER_TICKET.md`. 06 `EVENT_MEMORY.md`. 09 `KEEP_ALL_REVIEW.md`.

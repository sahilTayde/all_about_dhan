# MIX-PCR-EXTREME-HOLD — hold the ticket, keep STRATs

**Team:** 04 overlay · 05 talk · 03 metrics  
**Status:** `WAITING` / `UNVALIDATED` / `customer_default: false` / `NO_PROMOTE`  
**Layer:** `VALIDATION` (03: extreme PCR without price is not a signal). No invented PCR numeric law (05 `CUSTOMER_TALK.md`).

Fires **HOLD** when PCR(OI) is on gather and there is no priced CE/PE wall (no INDEX last / NEUTRAL|NO_TRADE). Does **not** delete `STRAT-001`–`014`. News/PCR remain ticket hold, not alpha.

```yaml
mix_id: MIX-PCR-EXTREME-HOLD
origin: PROJECT-DERIVED
styles: [OPTION_BUYER]
role: HOLD_overlay
customer_default: false
status: WAITING
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY]
keep_all: STRAT-001-014
```

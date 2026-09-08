# MIX-003-INDEX-PROXY — Gokul 003 recipe on INDEX resample

**Team:** 04 · **Status:** `WAITING` / `UNVALIDATED` / labeled **PROXY** / `NO_PROMOTE`  
**Recipe origin:** `DHAN-DERIVED` (`STRAT-003` / `2RnBT9DDDNI` 3m FUTIDX).  
**Path origin:** `PROJECT-DERIVED` (INDEX 1m → 3m resample ≠ FUTIDX/OPTIDX).

Does not replace `STRAT-003` KEEP_ALL book. Customer ticket is **not** driven by this MIX. Stage stays WATCH (5m ST/MACD confirm-or-kill is not entry).

```yaml
mix_id: MIX-003-INDEX-PROXY
recipe_origin: DHAN-DERIVED
path_origin: PROJECT-DERIVED
proxy_label: INDEX_RESAMPLE_NE_FUTIDX
attached: {primary: [STRAT-003]}
customer_default: false
status: WAITING
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-GOKUL-003]
```

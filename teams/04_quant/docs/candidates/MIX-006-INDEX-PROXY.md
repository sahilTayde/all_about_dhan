# MIX-006-INDEX-PROXY — Mukul 006 recipe on INDEX resample

**Team:** 04 · **Status:** `WAITING` / `UNVALIDATED` / labeled **PROXY** / `NO_PROMOTE`  
**Recipe origin:** `DHAN-DERIVED` (`STRAT-006` / `pvmvkiS1cx4` 2m).  
**Path origin:** `PROJECT-DERIVED` (INDEX 1m → 2m EMA 10/20 ≠ OPTIDX premium tape).

VIX>15–16 filter remains `DATA_INSUFFICIENT`. Not customer default. WATCH only.

```yaml
mix_id: MIX-006-INDEX-PROXY
recipe_origin: DHAN-DERIVED
path_origin: PROJECT-DERIVED
proxy_label: INDEX_RESAMPLE_NE_OPTIDX
attached: {primary: [STRAT-006]}
customer_default: false
status: WAITING
NO_PROMOTE: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-SCALP-006]
```

# oms (V2-08 + V2-09)

Paper-only order router and position manager. Risk checks run before any broker
call. Duplicate `order_id` submits are idempotent. Exits are built from the
held position record. Live/Dhan construction is disabled.

```bash
pytest packages/oms tests/regression/test_reg_02_protective_stop.py \
  tests/regression/test_reg_03_held_instrument.py \
  tests/regression/test_reg_05_caps.py tests/regression/test_reg_12_cost_stack.py \
  tests/regression/test_reg_14_fill_rules.py tests/regression/test_reg_15_eod_stale.py \
  tests/regression/test_reg_16_cost_config.py
python -m oms.demo
```

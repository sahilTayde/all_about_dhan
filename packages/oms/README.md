# oms (V2-08)

Paper-only order router. Risk checks run before any broker call. Duplicate
`order_id` submits are idempotent. Live/Dhan construction is disabled.

```bash
pytest packages/oms tests/regression/test_reg_02_protective_stop.py \
  tests/regression/test_reg_05_caps.py tests/regression/test_reg_12_cost_stack.py \
  tests/regression/test_reg_14_fill_rules.py tests/regression/test_reg_16_cost_config.py
```

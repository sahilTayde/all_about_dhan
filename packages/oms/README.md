# oms (V2-08 / V2-08b)

Paper-only order router and chase planner. Risk checks run before any broker
call. Entries are marketable LIMITs (never MARKET). Live/Dhan is disabled.

```bash
pytest packages/oms tests/regression/test_reg_02_protective_stop.py \
  tests/regression/test_reg_04_entry_plans.py \
  tests/regression/test_reg_05_caps.py tests/regression/test_reg_07_entry_config.py \
  tests/regression/test_reg_12_cost_stack.py \
  tests/regression/test_reg_13_entry_location.py \
  tests/regression/test_reg_14_fill_rules.py tests/regression/test_reg_14_entry_limits.py \
  tests/regression/test_reg_16_cost_config.py
```

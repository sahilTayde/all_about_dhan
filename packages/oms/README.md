# oms (V2-08 / V2-08b)

Paper-only order router and chase planner. Risk checks run before any broker
call. Duplicate `order_id` submits are idempotent. Live/Dhan construction is
disabled. Entries are marketable LIMIT orders (ask + `max_chase_ticks`), never
MARKET.

```bash
pytest packages/oms tests/regression/test_reg_02_protective_stop.py \
  tests/regression/test_reg_05_caps.py tests/regression/test_reg_12_cost_stack.py \
  tests/regression/test_reg_14_fill_rules.py tests/regression/test_reg_16_cost_config.py
python packages/oms/tests/demo_planner.py
```

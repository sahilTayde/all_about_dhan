# oms (V2-08 + V2-09 + V2-09b)

Paper-only order router and position manager. Risk checks run before any broker
call. Duplicate `order_id` submits are idempotent. Exits are built from the
held position record plus declared ExitPlan primitives (catastrophic, structural,
ATR fixed at fill, time, grace, signal-flip). Live/Dhan construction is disabled.

## Whole-lot quantities

NSE index options trade only in whole lots. Lot size is
`contracts.instruments.India.lot_size` for the underlying on the instrument id
(never a hard-coded 65). Entry fills, adds, and every exit quantity (partial,
time stop, EOD, founder, kill, failsafe, target, strategy) are `lots * lot_size`.

- A **partial** sells `floor(orig_lots * fraction)` lots, minimum 1 lot when the
  book has 2+ lots. Example: 3 NIFTY lots (195) at 50% sells 1 lot and leaves 2
  (130), not 98 units.
- A **1-lot** book **skips** the partial. A partial is not a flatten; target,
  time stop, EOD, founder, kill, or strategy still close the single lot.
- Protective SL-M qty tracks net: in-place `modify_order(order_id, qty)`,
  cancel-then-replace only if modify is unsupported, then CRITICAL flatten.

```bash
pytest packages/oms tests/regression/test_reg_02_protective_stop.py \
  tests/regression/test_reg_03_held_instrument.py \
  tests/regression/test_reg_05_caps.py tests/regression/test_reg_12_cost_stack.py \
  tests/regression/test_reg_14_fill_rules.py tests/regression/test_reg_15_eod_stale.py \
  tests/regression/test_reg_16_cost_config.py tests/regression/test_reg_18_exit_primitives.py
python -m oms.demo
```

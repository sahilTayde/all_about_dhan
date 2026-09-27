## Summary

<!-- What changed and why, in plain English. Paper only: no live orders, no broker calls, no secrets. -->

## Honest backtest

<!--
Required when strategy, risk, sizing, exit, cost or analyst code/config changes. The backtest-gate CI
checks this section:
- Gated code changed but tools/backtest_gate/expected_results.json did not: each field may be
  "N/A: <reason>" (the gate proved the synthetic replay did not move).
- expected_results.json changed (results moved): every field needs a real value; N/A is refused.
Synthetic fixtures prove "nothing moved by accident"; they say nothing about edge. Edge claims need
walk-forward out-of-sample data, costs and the number of variants you tried.
-->

- **OOS results:** <!-- walk-forward out-of-sample: days, trades, net P&L after costs, max drawdown, vs baseline -->
- **Costs:** <!-- charges model and slippage assumed (config/charges.yaml, ticks); net vs gross -->
- **DSR:** <!-- deflated Sharpe ratio (and the plain Sharpe it deflates) -->
- **Trial count:** <!-- how many variants/parameter sets were tried before this one -->
- **Expected results file:** <!-- unchanged | regenerated with `python tools/backtest_gate/gate.py --update` (say what moved and why) -->

## Handoff Block (Section 106)

### Accepted
-

### Rejected
-

### Unknown / Data Insufficient
-

### Gap Addressed
- <!-- which gap in docs/01_CURRENT_STATE_AND_GAPS.md -->

### Evidence
- <!-- tests run, backtest/tape replay results -->

### Known Risks
-

### Next Steps
-

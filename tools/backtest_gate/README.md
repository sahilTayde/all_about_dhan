# Backtest gate (PR-021)

Replays the synthetic fixture days through the event path (analysts, boss, risk engine, desk,
ledger) under both risk files, and fails if any result moved without an updated
`expected_results.json`. Synthetic data only: a PASS means "nothing moved by accident", not "edge".

```bash
python tools/backtest_gate/gate.py            # PASS / FAIL with a readable diff (about 25 s)
python tools/backtest_gate/gate.py --update   # after an intended change; commit the file
python tools/backtest_gate/pr_check.py --body-file body.md --changed <paths...>
```

| Fixture | Risk profiles |
|---|---|
| `packages/desk-ml/tests/fixtures/synthetic_session_nifty.json` (2026-09-10, seed 23) | `replay_risk` (`config/risk_limits_replay.yaml`), `live_paper_risk` (`live_risk_config` in `config/event_path.yaml`) |
| `fixtures/synthetic_session_sensex.json` (2026-09-11, seed 41, lot 20) | same |

Recorded per run: trades (ids, times, strikes, prices, lots, exit reason, P&L), wins, gross,
charges, net, exit-reason and skip-reason counts, risk vetoes by code, event counts, and the
ledger totals. CI: `.github/workflows/backtest-gate.yml`. When `expected_results.json` changes, the
PR body's honest-backtest section (OOS, costs, DSR, trial count) must be filled in; N/A is refused.

# Backtest gate (PR-021)

Replays synthetic fixture days through the event path (analysts, boss, risk engine, desk, ledger)
under three profiles, and fails if any result moved without an updated `expected_results.json`.
Synthetic data only: a PASS means "nothing moved by accident", not "edge".

```bash
python tools/backtest_gate/gate.py            # PASS / FAIL with a readable diff (about 1 min, 4 processes)
python tools/backtest_gate/gate.py --update   # after an intended change; commit the file
python tools/backtest_gate/mutate.py check    # every exit constant moved one step must fail the gate
python tools/backtest_gate/pr_check.py --body-file body.md --changed <paths...>
```

**Days.** `packages/desk-ml/tests/fixtures/synthetic_session_nifty.json`,
`fixtures/synthetic_session_sensex.json`, plus the 10 recipe days in `fixtures/recipes.json`
(NIFTY, SENSEX, BANKNIFTY; regime walks, scripted trend/pause/chop legs, intrabar lows, OI chain
cells). `synth.py` generates recipe days deterministically into a temp cache; they are not committed.
The recipes were chosen with `mutate.py search` (about 150 candidate days) so that every reachable
exit constant moves at least one day.

**Profiles.** `replay_risk` (`config/risk_limits_replay.yaml`), `live_paper_risk` (the live loop's
`live_risk_config`), `target_shift` (`apply_target_shift=True`, the only path that reads the trail
band, `TARGET_STEP_MAX` and `T1_CONFIRM_SECONDS`).

**Mutation check.** `mutate.py` edits one constant of `desk_ml/paper_scalp.py` in a subprocess (an
import hook applies the source edit, nothing is written) and runs the gate fail-fast. 50 mutants:
38 are caught; 7 cannot move a replay result in the default SOD product (`UNEXERCISABLE`, reason
per constant: `SCALP_HOLD_BARS`, `PREMIUM_PRINT_CAP`, `MIN_STOP_PREMIUM`, NIFTY `min_stop`,
`OVERLAY_CANCEL_COOLDOWN_SEC`, `FILL_AWAY_FRAC`, `UNFILLED_BARS`); 5 are live but no synthetic day
reaches them yet (`NOT_REACHED`: `STALL_HIGH_STALE_SEC`, `STALL_HIGH_STALE_CHOP`, `TRAIL_BAND_MIN`,
NIFTY/SENSEX `rr_continue`). CI job `mutation` runs `tests/test_mutation.py` with `GATE_MUTATION=1`.

Recorded per run: trades (ids, times, strikes, prices, lots, exit reason, P&L), wins, gross,
charges, net, exit-reason and skip-reason counts, risk vetoes by code, event counts, and the
ledger totals. When `expected_results.json` changes, the PR body's honest-backtest section (OOS,
costs, DSR, trial count) must be filled in; N/A is refused.

# Exit Lab report (paper / replay only)

**Status:** HYPOTHESIS / PAPER / NO_PROMOTE. Every number in the tables comes from a command in [Reproduce](#reproduce). If a cell is missing, the run labelled it `DATA_INSUFFICIENT` — it was not filled in.

**Owner:** `packages/exitlab` + this file. V2 defaults are unchanged. Playbook: `config/v2/exits/exitlab_playbook.yaml` (`enabled: false`).

## Now / Why / Next

- **Now:** The lab can replay named exit plans on attached live dual-tapes (2026-09-14..28) and the 1m option/index sample (2025-10..2026-08). New V2 behaviour is opt-in and off.
- **Why:** The legacy desk stopped out on noise, cancelled good tickets, and booked early overlays. This file measures that as a baseline; it does not copy those overlays as the answer.
- **Next:** Founder reads the OOS + stress tables, then decides whether to turn the playbook on in a paper session. Not a promote.

## Data used

| Set | Path (local, gitignored) | What | Sessions / days | Notes |
|-----|--------------------------|------|-----------------|-------|
| Live dual-tape | `.local_data/tape/YYYY-MM-DD.jsonl` | Legacy recorder ticks (index + ATM/ITM + wings) | 2026-09-14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 28 | 19–20 weekend / off-session. Several weekdays start late. |
| V2 recorder | `.local_data/tape/v2/2026-09-28/` | Depth + quote snapshots | 2026-09-28 only | Bid/ask used to state the 1m slip model. |
| Option 1m | `.local_data/NIFTY_*.parquet` | Weekly NIFTY option 1m OHLC | Expiry weeks 2025-10-14, 2026-04-28, 2026-05-26, 2026-06-02, 2026-07-07, 2026-08-04 | 2026-08-04 is thin. |
| Index 1m | `.local_data/index_NIFTY.parquet` | NIFTY 1m | Used for regime labels + history entries | Long history; session filter 09:15–15:30 IST. |

**Split:** choose parameters on earlier data (`<=` the live-day midpoint, and history `<= 2026-05-31`). Report on later untouched live days and history `>= 2026-06-01`.

**Fills:** buy at ask when the book exists; else LTP/close × (1 + 0.40% stated slip). Sell at bid / (1 − 0.40%). Costs: `ledger.charges` + `config/charges.yaml` (NSE). Lot 65, 1 lot unless the V2 selector sizes 2.

**No look-ahead:** 1m bar known only at `available_ts` (close). Tape rows by `as_of_ist` / `available_ts`. Test: `packages/exitlab/tests/test_lookahead.py`.

## Reproduce

From a checkout with the archives extracted to `.local_data/` (do not commit data):

```bash
python -m pip install --no-deps -e packages/exitlab
# history parquet needs: pip install 'pyarrow>=14'
python -m exitlab measure --data .local_data --out /tmp/exitlab-run
python -m exitlab research --data .local_data --out /tmp/exitlab-run --seed 7
python -m exitlab list-plans
python -m exitlab playbook --path config/v2/exits/exitlab_playbook.yaml
```

Tables below are copied from `/tmp/exitlab-run/tables.json` (or the run directory named in the PR). Re-run the commands to regenerate.

## Market measurements

Filled after `python -m exitlab measure` / `research`. See `measure_live.json` and `measure_history.json`.

## Scenario map

Sessions are labelled from **that day's** index path: trend_up / trend_down / chop / mixed, plus expiry / day_before_expiry / gap_open / feed_freeze / high_iv / low_iv. Weekend files are skipped for entries.

## Results

Filled after `python -m exitlab research --seed 7`. Columns: plan × entry set × scenario, net after costs, win rate, avg win/loss, max DD, n trades, bootstrap CI, deflated Sharpe, `n_variants_tested`.

## Stress

Spread ×2, slip ×2, 30s synthetic quote gap, Monte Carlo resample of trade nets. IV crush / 1% open gap are labelled synthetic when not on the tape.

## Legacy comparison

`legacy_overlay` uses the constants in `paper_scalp.py` (STOP_FRAC 0.40, TARGET_FRAC 0.55, NO_PROGRESS 3 bars / 2 pts, BOOK_NEAR 70%, STALL 20m/8m, TIME 45m, ADVERSE 12%, flatten 15:16). `paper_scalp.py` is not edited. Actual filled tickets come from `replay_paper_scalp(..., write=False)` on each dual-tape day.

## Recommended playbook

See `config/v2/exits/exitlab_playbook.yaml`. Off unless `enabled: true` **and** `load_exitlab_playbook(enabled=True)`. Evidence and CIs are in the research tables after the run.

## Handoff

### Accepted
- Paper/replay harness in `packages/exitlab`.
- Opt-in playbook file, default off.
- Honest split + variant count for DSR.

### Rejected
- Shipping any plan as the live default.
- Inventing bid/ask on 1m history (stated slip instead).

### Unknown / data insufficient
- News/event tags; thin 2026-08-04 week; late-start live days.

### Gap addressed
- Exit research gap: no replayable, costed, no-look-ahead exit lab on real tapes.

### Known risks
- V2 entry set is a selector proxy (1m direction + real holds), not the full plugin room.
- Sweep winner can still fail DSR after multiple-testing correction.

### Next steps
- Re-run research on a larger tape once more days exist.
- Founder paper-session only if the OOS table stays non-negative after costs and DSR.

# Reliability (PR-A): CI, offline verification, fault sims

Paper only. Nothing here calls a broker or reads credentials. Critique of the spec and the plan
that was built: [`PR_A_CRITIQUE.md`](PR_A_CRITIQUE.md).

## CI (`.github/workflows/ci.yml`)

Runs on every pull request and on pushes to `main`. `permissions: contents: read`, no secrets,
actions pinned by commit SHA. Required checks to enable in branch protection after the first green run:

| Check name | What it does |
|---|---|
| `hygiene` | `scripts/ci/scan_repo.py` (secrets, files > 2 MB, data payloads outside fixtures, private data in fixtures), hash-pinned install + `scripts/ci/check_local_names.py` (every in-repo package installed from this checkout), fixture regeneration byte-diff |
| `unit (3.11)`, `unit (3.13)` | `scripts/ci/unit.sh`: every package's tests, sockets only to localhost, no `DHAN_*` / live-confirm env, `-m "not network and not sim and not slow"` |
| `golden-replay` | `event_parity` on the committed NIFTY fixture, and `test_golden_replay.py` (legacy dumps byte-identical to the goldens flag off and flag on; replay independent of CWD, `$HOME`, TZ and the wall clock; no `repo_root()` in engine paths; `write=False` writes nothing) |
| `faults (…)` (2 shards) | `pytest -m sim packages/desk-ml/tests/test_sims.py`: full-day live-loop sims with fault injection, invariants I1–I10 |

Local install recipe (Mac, VPS, CI): `bash scripts/ci/install.sh` (third party from
`requirements/ci.txt` with `--require-hashes`, local packages `--no-deps`). Regenerate the lock with
`pip-compile --generate-hashes --allow-unsafe --strip-extras -o requirements/ci.txt requirements/ci.in`.

Commit trailers: prefer the GitHub no-reply address over a personal e-mail in a public repo.

## Goldens and fixtures

- Fixtures (`packages/desk-ml/tests/fixtures/`) are synthetic, produced by
  `python -m desk_ml.testing.canonical --write`; CI regenerates and byte-diffs them.
- Goldens (`packages/desk-ml/tests/golden/*.legacy.json`) are canonical dumps of the legacy
  flag-off replay, verified byte-identical to `main` @ `0375e94`. Regenerate only with a reason in
  the PR: `python -m desk_ml.testing.canonical --write-goldens`.

## Offline replay on the real tapes (owner, box or Mac, `unshare -rn`)

`$R` is a scratch data root with the tapes and the box founder/params/lot files (e.g. `mkroot.sh`).
Run each command on `main` and on the PR head; every per-day `sha256` in `manifest.json` must match.

```bash
D="--since 2026-09-17 --until 2026-09-25"
# NIFTY, box founder file, flag off / flag on (event path with the replay risk file, as event_parity runs it)
python scripts/verify/replay_dump.py --root $R $D --out out/nifty_off
python scripts/verify/replay_dump.py --root $R $D --flag-on --out out/nifty_on
# All three indices, founder all-START in process
python scripts/verify/replay_dump.py --root $R $D --underlyings NIFTY BANKNIFTY SENSEX --all-start --out out/all3_off
python scripts/verify/replay_dump.py --root $R $D --underlyings NIFTY BANKNIFTY SENSEX --all-start --flag-on --out out/all3_on
# Parity, as in the PR #14 round-3 report
python -m desk_ml.event_parity --root $R $D
python -m desk_ml.event_parity --root $R $D --underlyings NIFTY BANKNIFTY SENSEX
```

Expected totals with `SHADOW_LOG=0` (`main` @ `ec91e9e`, #25's closed-bar logit): NIFTY 63 /
−96,190.79; all three 140 / −27,022.54. The lab baseline (36 / +110,000.29) runs through the box's
existing `lab_p2c.py` unchanged; extra kwargs can also be passed to `replay_dump.py` with
`--kw key=<json>`.

Live-loop history check on a recorded day (before: `main`; after: PR head):

```bash
python scripts/verify/live_cycles.py --root $R --day 2026-09-25 --underlyings NIFTY --every 10 \
    --founder-stop 12:30 --out out/live_0925_founder.json
```

On `main` the 12:30 STOP erases the trades booked before it; on the PR head the report shows
0 history-rewrite violations and keeps them.

## Fault sims

```bash
python -m pytest -q -p no:logging -m sim packages/desk-ml/tests/test_sims.py            # full matrix
python -m pytest -q -m sim -k founder packages/desk-ml/tests/test_sims.py                # one scenario
```

Harness: `desk_ml.testing.sim.run_live_day` (writes the tape prefix per cycle into a scratch
root and calls `live_cycle.run_cycle`, flag off or on), faults in `Fault(kind, at, until, args)`,
invariants in `desk_ml.testing.sim.check`.

## Live loop, heartbeat, supervisor

- One live cycle (`desk_ml.live_cycle.run_cycle`) serves both `dual_tape --paper-scalp` and
  `python -m desk_ml paper-scalp --loop`.
- `data/recon/engine_heartbeat.json` is written only by a finished cycle (`last_ok_ist`,
  `consecutive_failures`, `last_error`) and at the top of each loop iteration (`last_loop_epoch`).
  `python -m health` reports `paper_engine` CRITICAL when the last good cycle is older than 120 s in
  market hours or the engine is failing.
- `python -m health.supervise -- <loop command>` restarts a crashed loop (backoff 5 s → 10 min,
  at most 5 restarts per incident) and kills and restarts a hung one. Exit 0 and exit 2 (dual-tape's
  "market closed": weekend, before 09:30 IST, after 15:29 IST) end supervision cleanly. One incident
  = one alert when it starts, one more if it gives up. Default heartbeat/alert paths are absolute
  from the repo root. `scripts/desk.sh morning` starts dual-tape under it at 09:30 (`watch-open`).
  If `health.supervise` is not importable in the legacy `.venv` (Python 3.9 Mac), `desk.sh`
  starts the same dual-tape command without the supervisor and logs a warning.
  `deploy/` has a launchd plist and a systemd service + timer that start it Mon–Fri 09:30 IST and
  never respawn a supervisor that gave up.
- Booked open tickets are carried across cycles and managed at their booked strike; forced exits
  (fail-safe flatten, guard) price the booked strike only (last known quote of that strike, flagged
  `quote_stale`, never another strike).
- Post-market params nudge (next session only): `python -m desk_ml nudge-params --day YYYY-MM-DD`.

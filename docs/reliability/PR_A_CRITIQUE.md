# PR-A critique of RELIABILITY_BUILD_SPEC (and the plan actually built)

Written before any PR-A code, against `main` @ `0375e94` (PR #14 merged). Scope: paper only.
Line references are to `0375e94`. The spec is a good map of the problems; this file argues
where it is wrong, too big, missing something, or would itself introduce a bug.

## 1. Things the spec gets wrong or would make worse

**1.1 The kill switch on the flag-off path (S5) would add a new history-rewrite bug.**
The live loop re-replays the whole day every cycle. A kill-switch file has no timestamp, so
touching it at 13:00 blocks every entry from 09:15 on the next re-run, and the morning's booked
trades disappear. The same is true of every "fail closed for the session" block in the spec
(corrupt founder file, corrupt params, corrupt halt file, `entries_blocked` after N failures).
PR #14's known leftover ("a corrupt file blocks every entry for the rest of that day, and a
re-replay then drops that day's trades from before the corruption") is exactly this class.
**Change:** every block is time-bounded, `block_from_ts` = the first time the live loop saw
the condition, persisted in the incident registry (the alert state file), so re-runs block
from the same moment and reproduce everything before it. If the registry itself cannot be
written, fall back to blocking the whole session (fail closed) and let the booked-trade net
(1.4) keep the board honest.

**1.2 Seeding the founder log "at session_start_ts from the current JSON" is lossy and would
change legacy numbers.** A founder file edited at 12:30 today says nothing about the morning.
Seeding it at session start re-applies it to 09:15 (the bug we are fixing). **Change:** the
first write through the new code seeds the pre-existing JSON state at `ts=0` (the "baseline",
the only state ever known before the log existed), then appends the real command with its own
timestamp. Sessions earlier than the first real command's date use the log's current state,
which is exactly today's behaviour for historical replays (so the owner's replays of Sep 17–25
from a root that only has the JSON file are byte-identical). Sessions on or after it are
evaluated as-of each tick.

**1.3 The spec treats the human override as "consumed then cleared" but misses that
replays clear it too.** `mark_to_market` calls `save_human_override({"action":"CLEAR"})`
unconditionally (`paper_scalp.py:4903/4941/4956/4977`), so a `write=False` lab or parity replay
of any day consumes the founder's live override, and a stale override from another day is
applied to whatever position it first matches in any replay. **Change:** the engine never
writes control files. Overrides are an append-only, session-scoped log applied at the first
tick at or after their timestamp; consumption is tracked in replay memory only.

**1.4 The booked-trade "safety net" is a detector, not the fix.** If the causes (1.1, 1.3,
founder, params, half-written inputs) are not fixed at the source, it fires HISTORY_REWRITE
every cycle and blocks the day. PR-A fixes the sources and keeps the net as the last line: it
publishes the booked truth, alerts once, and blocks entries from that moment.

**1.5 S14 "ignore a final line without `\n`" can change legacy numbers.** If a finished day's
file ends with a complete JSON line and no newline, today's loader uses it. **Change:** only an
*unparseable* last line is treated as in-progress (that is already what the loader does); PR-A
adds counting and one alert per session for mid-file corruption.

**1.6 Wall-clock "30 s fresh" for `check_paper_engine` is too tight.** The live loop re-replays
the whole day (O(n²) `step_context`, spec §7.6). A synthetic 1,126-tick NIFTY day already takes
~4.5 s per path here; real 3-index days late in the session take longer. A 30 s threshold would
page the founder on a healthy engine. **Change:** 120 s default (`ENGINE_STALE_SECONDS`),
separate from the 300 s recorder threshold, plus an immediate CRITICAL on a recorded engine
error regardless of age.

**1.7 `health.monitor` using the desk AlertSink would make `health` depend on `desk_ml`.**
The monitor already dedupes through its persisted `status.json` and deliberately re-alerts every
15 min for an ongoing outage. **Change:** the AlertSink lives in `desk_ml` and is used by the
paper engine, the live cycle and the Desk. The monitor keeps its own dedupe; its writes become
non-raising and atomic. I7 ("exactly one alert per incident") is scoped to engine/desk alerts.

## 2. Things the spec misses

- **`dual_tape --paper-scalp` never passes `live_loop=True`** (`dual_tape.py:1000`). PR #14's
  persisted halt, forced-close re-apply and halt-file fail-closed only run under
  `paper_scalp.run_loop`. On the path that actually trades every day they are dead code.
  PR-A routes both loops through one `live_cycle.run_cycle(...)`.
- **Corrupt params fail open to the code defaults in live** (`load_paper_params`): the next
  re-run silently trades a different `stop_frac`/hold for the whole day. PR-A: live reads the
  frozen snapshot; a corrupt or missing snapshot blocks entries from first sight and exits keep
  running on the defaults. Offline replays keep today's fallback (byte-identical).
- **A full disk kills flag-off exits**: `append_model_log` raises `OSError` inside `_close`, the
  replay aborts, nothing is booked or published. PR-A: model log and alert writes never raise.
- **A restart onto an unwritable disk** loses PR #14's in-memory unsaved halt and resumes
  entries. PR-A: an unsaved halt goes to a fallback file, and the live cycle probes that the data
  root is writable before each cycle; if it is not, entries are blocked for that cycle.
- **In-day look-ahead in `_hold_series`**: KMeans is fitted on the first 60% of the *whole day*
  and the OLS β on every row, so earlier ticks see later data. Today it only feeds observe-only
  books (`resolve_fill_intents`, `--sod-off`) and the overlay packet, not SOD trades, so it
  cannot move a booked trade. Not changed in PR-A (it would move logged observe rows); the I6
  invariant in the sims would catch it the day it reaches a trade.
- **The clean-slate wipe (`wipe_today_paper_book`) is a deliberate rewrite.** With booked-trade
  immutability it would raise HISTORY_REWRITE forever. PR-A makes the wipe archive the day's
  booked file and write the epoch into the frozen params, i.e. an explicit audited reset.
- **Tests write into the checkout**: besides `data/recon/ml` (spec §1a), the agent_rag tests
  rewrite the tracked `data/knowledge/agent_rag.sqlite` and `AGENT_RAG_BUILD.json`.
- **`packages/events` has a CWD-dependent test** (`config/charges.yaml` relative path); it fails
  when pytest runs from the package directory.

## 3. Over-built for PR-A

- **ReplayContext with 11 fields** (lot sizes, index closes, cost model, founder/override
  sequences...) threaded through an 8.4k-line monolith is a large, hard-to-review diff for no
  PR-A benefit. Built instead: a small frozen `ReplayContext(root, session_ist_date, live_loop,
  write, clock, alerts, model_log)` attached to the engine. Engine code reads root/clock from
  it; the founder and override logs are read from the root and evaluated at tick time (no
  wall clock). `cost_model` lands with PR-B.
- **Seven committed fixtures.** SENSEX-fee, resting-limit and tick fixtures only matter for
  §6 (PR-B). PR-A commits the existing NIFTY fixture plus one 3-index fixture from a committed
  generator; gap/stall/corruption variants are derived at test time.
- **The full fault matrix at 10-minute cycles.** Each cycle re-replays the prefix, so cost is
  O(cycles × n²): ~38 cycles × 14 faults × 2 fixtures × 2 paths is hours of CI. PR-A runs
  30-minute cycles, flag-on only where the desk matters (broker reject/timeout, halt, exits),
  and the full cross product in a `slow` job.
- **Partial fills and order timeouts "until reconcile"**: the paper engine is the fill model
  and the desk mirrors it; there is nothing to reconcile in paper. PR-A covers broker reject and
  timeout on entry and exit (flag-on); partial fills go to PR-B with the order state machine.

## 4. Spec rows deferred (with reason)

| Item | Reason |
|---|---|
| §3 property tests | PR-B, as §9 allows. |
| §6 cost realism, S13 stale-quote pricing | PR-B (S13 is a pricing rule; it moves numbers). |
| S11 wall/session clock in `approval_problems` | `ClockedPaperBroker` already cancels the wall clock algebraically; the base-class fix and P-O7 belong with the order properties (PR-B). |
| S12 `critical` bus subscriptions | Desk handlers already catch and fail safe (PR #14); PR-A only bounds `bus.errors`. |
| S17 startup veto self-check | nice-to-have. |
| §7.4 package renames, §7.6 performance, §7.7 ledger gaps | nice / PR-B / later, as the spec says. |
| History purge of the sqlite | Owner's call; PR-A only stops tracking it. |

## 5. Hard constraints and how PR-A keeps them

- **Byte-identical legacy replay.** Offline replays (`live_loop=False`) read the same inputs as
  today: the founder JSON when no log exists, the params file when no frozen snapshot exists,
  and no halt/kill/booked/block state. The paper guard's risk limits run only in the live loop
  (see 7.1). CI pins this with golden canonical dumps of the committed fixtures, verified
  byte-identical to `main`, and the flag-on/flag-off parity.
- **The owner's harness monkeypatch** (`fs.allows_new_fill = lambda underlying, root=None: True`)
  keeps working: without a founder log the engine still calls `new_fill_decision(u, root=...)`
  → `allows_new_fill(u, root=...)` with today's signature.
- **Live-order gate and live tiers untouched.** Reduce-only approvals on a degraded risk config
  do not bypass `DhanBroker`'s own confirm gate, and `MODE_NOT_ENABLED` still applies to exits
  in live modes (not relaxed).

## 6. Plan actually built (PR-A)

1. `desk_ml.reliability`: `atomic_write_json/text`, `AlertSink` (persisted dedupe + incident
   first-seen registry, never raises), `ReplayContext`, model-log sink.
2. Founder commands and human overrides: append-only timestamped JSONL logs, JSON views written
   atomically for the UI, as-of evaluation at tick time, NIFTY fail-open removed
   (`FOUNDER_STATE_UNREADABLE` for every index), engine never writes control files.
3. Paper guard on the flag-off path (and inside `_plan_open` for flag-on): kill switch, halt,
   time-bounded blocks, and the same `RiskEngine` limits with as-of state across indices.
4. Risk engine: kill-switch path resolved against the data root (not CWD), stat errors fail
   closed, reduce-only actions approved (degraded, critical log) on config or audit failure.
5. Frozen per-session params in live; nudge moved to `python -m desk_ml nudge-params`.
6. `live_cycle.run_cycle`: ingest control files → replay → booked-trade guard → atomic board →
   heartbeat. Used by `dual_tape --paper-scalp` and `run_loop`. Honest heartbeat, health
   check on last-ok time and error state, `python -m health.supervise` restarts a dead or hung
   engine; launchd/systemd templates keep the supervisor alive.
7. Desk: halt blocks time-bounded, dedupe through the persisted AlertSink, unsaved halt
   fallback file, refused exits retried each tick with one alert per trade, `Order.transition`
   restores state when the ledger hook raises.
8. Fault-injection live-day sims + invariant checker (I1–I10) with a checker self-test.
9. desk-ml test isolation (conftest root, founder START explicit), two stale tests rewritten
   with precondition guards, no test writes into the checkout.
10. CI (`.github/workflows/ci.yml`): hygiene (secret/size/data scan, local-name guard), unit
    matrix 3.11/3.13 with sockets disabled, parity + golden replay, sims. Stop tracking the 70 MB
    sqlite.

## 7. Changes made while building (after the critique above)

The fault sims found more than the critique predicted. Each change below has a test.

1. **Paper-guard risk limits run in the live loop only**, on the session's frozen copy of
   `risk_limits.yaml` (paper tier: 25 lots, 3 positions, −30,000 per trade, −90,000 per day,
   15-minute loss cooldown, 09:15–15:00). Offline replays skip them: the lab P2C config was never
   parity-checked flag on, so any ticket the replay file vetoed would move a legacy number. The
   live flag-off path therefore now trades under the same limits as the live flag-on path.
2. **Blocks live in their own registry** (`data/recon/live_blocks/<day>.json`, intervals with
   `from` and `until`), not in the alert state. Removing the kill file or repairing a control file
   closes the interval and entries resume; halt, rewrite, engine-failure and frozen-params blocks
   are sticky for the session. A corrupt registry blocks from the moment it is seen.
3. **Last-good inputs.** If the founder or override log turns unreadable mid-day, the live replay
   keeps the last good rows (`live_inputs_last_good.json`) so everything before the damage
   re-derives identically; new entries are blocked from first sight. The frozen params are
   written with a `.bak` twin.
4. **Fail-safe flatten.** After 3 failed cycles in a row with open tickets, the live cycle closes
   them at the last tape quote and books them (`FORCED_ENGINE_FAILURE`), like the desk's MTM
   fail-safe. Nothing stays unmanaged while the engine is down.
5. **Tape validation in the live loop only**: a NaN premium crashed `_hold_series` (KMeans could
   not name 4 clusters) and stopped every exit. The live loader drops non-finite prices and a
   failing ML hold overlay degrades to "no holds" with one alert. Offline replays are unchanged.
6. **Deterministic analysts in the live loop.** The event path used wall-clock analyst timeouts
   when `live_session=True`, so two cycles could vote differently on the same past tick.
7. **`_hold_series` unpacks the fitted model once per replay** instead of once per tick (about 5×
   faster replays, same arithmetic; goldens and the synthetic multi-day dumps are byte-identical to
   `main`). This shortens every live cycle.
8. **Grep gate replaced by a runtime test**: the monolith hosts CLI helpers that legitimately
   default to `repo_root()`, so the test makes `repo_root()` raise and runs the replays flag off and
   flag on. Code config now comes from `persist.code_root()`.
9. **Sim cadence**: 9 cycles a day (every 45 minutes) plus extra cut-offs around each fault,
   split into 2 CI shards. Flag-on runs on the 3-index fixture only where the desk matters.
10. **Deferred**: the agent_rag tests still rebuild the tracked `data/knowledge/agent_rag.sqlite`
    in the checkout (outside the trading engine; the desk-ml suite fails if it writes the checkout).

## 8. Round 2 (owner's real-tape verification: three live-path blockers)

- **F3 root cause: the live logit saw a partial 3-minute bar.** A 3m bar was visible from its last
  tick, so the newest tick of every cycle saw the bucket so far, while the same tick in any later
  cycle does not see that bar. The picker could book a ticket on that signal that no later cycle
  re-derives, and the ticket vanished. Measured with prior-day history: the last tick's logit side
  differed from its full-day value at 20% of ticks. The live loop now uses only closed buckets and
  builds today's bars from the tape alone (history files that grow during the day are not read for
  today). Offline replays keep the legacy rule, byte for byte.
- **Booked open tickets are carried, not re-derived** (`live_cycle.Pins`). From its booked open
  time a ticket holds its slot, and at the first tick after the previous cut-off its saved state
  replaces the re-derivation, so it is managed at its booked strike to its own exit. Drift is
  reconciled with one WARN. Only a ticket that cannot be carried is CRITICAL and blocks entries
  (`HISTORY_UNRECONCILABLE`). This reverses the round-1 choice of a forced close plus a
  rest-of-day block.
- **F2: forced exits price the booked strike** (`live_cycle.booked_quote`, the SOD mark-to-market
  rule): guard closes, the fail-safe flatten (raw-tape fallback when the loader is down) and the
  desk's MTM fail-safe. The round-1 code priced the tape's current ITM/ATM leg.
- **F1: exit code 2 is a clean stop**, restarts are capped with backoff, one alert per incident;
  the deploy templates start the loop each trading morning and never respawn a supervisor that gave up.
- Also: the `risk_limits.yaml` header now says limits apply from the next session (the code
  freezes them; applying them mid-day would change how the morning re-derives). The wipe updates
  the frozen-params backup. A crashed half-written append is repaired and quarantined before the
  next append, and readers recover a record glued onto a fragment; real damage still fails closed.
  With both frozen-params copies damaged, the last good params are kept (one CRITICAL, no drift).
  The agent_rag tests rebuild into a temp root.
- After merging `main` (#17): the live loop keeps the LLM analyst's live provider while analysts
  stay deterministic. Its config is read as code config. With `weight: 1` and an online provider,
  its votes can differ between re-replays; the booked-trade guard and the carried tickets absorb
  that drift, but it would show as WARN reconciliations.

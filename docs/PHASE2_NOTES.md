# Phase 2 notes: event bus, boss, desk, analyst registry (PR-006 to PR-009)

This is a structural refactor with no behaviour change. **Paper only.** The live-order gate in
`packages/brokers` (mode `limited_live`/`live` + `ALL_ABOUT_DHAN_LIVE_CONFIRM` + a fresh risk
approval) is untouched, and nothing here calls Dhan.

## The flag

`USE_EVENT_BUS` is **off by default**. When it is off, `replay_paper_scalp` calls `step_underlying`
exactly as before. Turn it on with the env var `USE_EVENT_BUS=1`, or pass `use_event_bus=True` /
`event_session=EventSession()` to `replay_paper_scalp`. The flag affects every caller of that
function, including the live paper loop, which re-replays the session on each heartbeat.

`step_underlying` and `_try_open` were split into phases (`step_context` → `step_mark` →
`step_vote_inputs` → votes → `step_decide`; `_plan_open` + `_commit_open`). The old path runs the
same code in the same order. The event path runs the same phases as separate services.

## Flow per tick (event path)

```
feed   step_context: 1m bars, regime, ITM bin, FOLLOWS          -> MARKET_TICK
desk   (priority 10) mark-to-market: fills, STOP/TARGET/overlay exits, mirrored to broker + ledger
boss   (priority 20) REQUEST_VOTES
analysts            AnalystRoom: every analyst in parallel, 500 ms timeout -> ANALYST_VOTE x 22
boss                picker majority -> observer -> entry gates (unchanged)
                    -> ENTRY_APPROVED {sized ticket}   or   NO_ENTRY {gate that skipped}
desk   founder pause? -> RiskEngine.check_entry -> PaperBroker.place_order -> book ticket -> ledger
                    (veto, refusal, or error while building the order = no trade, ENTRY_VETOED)
```

- **Founder commands.** `FOUNDER_COMMAND` runs first on the bus (subscriber priority 0; in a
  Redis batch it is dispatched first). The desk handles `PAUSE_ENTRIES`, `RESUME_ENTRIES` and
  `FLATTEN_ALL` (which pauses entries, then closes every ticket with reason `FOUNDER_COMMAND`).
- **Stops never wait on the boss.** Exits happen in the desk's `MARKET_TICK` handler. Targets
  also exit immediately, as they do today; routing target exits through boss `EXIT_APPROVED` is a
  later behaviour change.
- **Audit.** Every event is appended to an append-only SQLite `events` table before any
  subscriber sees it. By default this is an in-memory DB for each replay; pass
  `EventSession(audit=EventAuditLog(path))` to keep it on disk.
- **One ledger per index walk.** Replay walks one index at a time: all of NIFTY, then SENSEX from
  09:15. So each index gets its own ledger, risk engine and PaperBroker. A shared ledger would
  let SENSEX's 10:00 risk check see NIFTY's 14:49 losing exit, a look-ahead that a live desk can
  never hit. Account-wide limits across indices need a time-merged walk.
- **Execution record.** The paper engine's working-limit fill model still decides when a ticket
  fills and at what price. `ClockedPaperBroker.fill_at` books that fill, rounded to the 0.05 tick.
  So ledger prices can differ from engine prices by up to half a tick (≤ ₹0.025).
- **Risk config.** Replay and the parity tool use `config/risk_limits_replay.yaml` (paper mode,
  mirrors the engine's own gates) so the two paths still match. The **live paper loop**
  (`paper-scalp --loop`, or `replay_paper_scalp(live_session=True)` with the flag on) uses
  `live_risk_config` in `config/event_path.yaml`, which defaults to the stricter
  `config/risk_limits.yaml` (₹5k per-trade cap, 15-minute cooldown, 15:00 cutoff). That loop
  never silently falls through to the looser replay file; naming the replay file in
  `live_risk_config` is the only way to select it. The founder kill-switch file still vetoes
  entries. Parity passes its own `EventSession()`, so a parity run stays on the replay file
  even when `live_session=True`.
- **Mark-to-market errors.** An exception in the desk's mark or stop path publishes
  `HEALTH_ALERT`, appends `data/health/alerts.jsonl` (shown by `GET /health/alerts`), and blocks
  new entries for the session. Flatten still closes positions. With the flag off, `step_mark`
  is unchanged.
- **Analyst timeout.** `timeout_ms` in `config/analysts.yaml` (and an optional per-key
  `timeout_ms`) is the live paper loop's wall-clock budget. Replay and parity run analysts
  in order with no wall-clock abstain, so a busy machine cannot change a vote.
- **Shadow analysts.** Rows with `shadow: true` log `value`, `flag`, `confidence` and
  `reasoning` on `ANALYST_VOTE` and are ignored by the boss. Definitions:
  `docs/SHADOW_ANALYSTS.md`. CSV: `python scripts/export_shadow_audit.py --audit <sqlite> --out shadow.csv`.

## Packages

Install the four packages the same way as the other repo packages (`pip install -e`, also in
`.cursor/install.sh`):

```bash
pip install -e packages/events -e packages/analysts -e packages/boss -e packages/desk
```

With `USE_EVENT_BUS` on, the paper loop checks those imports once at startup. A missing package
raises `EventBusStartupError` with the install command. It does not crash again on every replay.

| Package | Role |
|---|---|
| `packages/events` | `EventType` / `Event` (JSON), `MemoryBus` (sync, default), `RedisStreamsBus` (optional), `EventAuditLog` |
| `packages/analysts` | `Analyst.vote(ctx) -> Vote(signal, confidence, reasoning)`, `register("KEY")`, `AnalystRoom`, `config/analysts.yaml` |
| `packages/boss` | `Boss`: REQUEST_VOTES → decision rules → ENTRY_APPROVED / NO_ENTRY |
| `packages/desk` | `Desk` (founder → risk → broker → ledger), `ClockedPaperBroker` |
| `desk_ml.event_path` | `EventSession`: wires bus, audit, ledger, risk, broker, analysts, boss, desk for one replay |
| `desk_ml.event_parity` | parity harness + CLI |

The 22 registered analysts are the paper engine's existing analyst room (`collect_analyst_votes`),
wrapped rather than rewritten, so the picker sees exactly the same votes.

To add a research feature as an analyst:

1. Write an `Analyst` subclass and decorate it with `@register("KEY")`.
2. Import that module before the session starts.
3. Add `KEY` to `config/analysts.yaml`.

Once enabled, it votes in the majority. If it times out or crashes, its vote is `ABSTAIN`.
A row with `shadow: true` is logged and left out of the majority. Replay does not apply the
wall-clock timeout (see above).

## Tests

```bash
source .venv/bin/activate
export PYTHONPATH=packages/events/src:packages/analysts/src:packages/boss/src:packages/desk/src:packages/ledger/src:packages/risk-engine/src:packages/brokers/src:packages/desk-ml/src
python -m pytest packages/events packages/analysts packages/boss packages/desk packages/desk-ml/tests/test_event_parity.py -q
```

The Redis tests skip unless a server is listening on `localhost:6379` and `pip install redis` has
been run; Redis is optional. The latency budgets are asserted in
`packages/events/tests/test_event_bus.py` (publish p99 < 5 ms) and
`packages/desk-ml/tests/test_event_parity.py` (boss decision p99 < 1 s, desk paper execution
p99 < 100 ms).

## Parity (acceptance test)

CI runs parity on a committed synthetic NIFTY session (`packages/desk-ml/tests/fixtures/`; it is
not market data):

```bash
python -m desk_ml.event_parity --fixture packages/desk-ml/tests/fixtures/synthetic_session_nifty.json
```

On real recorded tapes (local only; dual-tape files under `data/recon/paper_watch/DUAL-TAPE/`
are not in git):

```bash
python -m desk_ml.event_parity --since 2026-09-17 --until 2026-09-25 --underlyings NIFTY
# same replay kwargs go to both paths, e.g.  --kw no_new_after_minutes=870 --kw nifty_need_strength=true
```

The check prints `PARITY` or `MISMATCH` per day, and old and new totals (trades and net ₹). Exit
code 0 means every closed-trade field (ids, timestamps, strike, entry/exit, lots, P&L, reasons)
and every skip-reason count matched, and the event path's ledger holds the same filled trades.

Run it with no active `human_trade_override.json`: the first path clears the override, so the
second path would see a different input.

The quoted baseline, **+94,962.39 over 38 trades** ("Phase-2 rules + 10:00–14:30 window"), came
from a lab run of the proven-fix stack (loss cooldown, 10:00–14:30 clock). `replay_paper_scalp`
does not have those rules yet (they are PR-010-class behaviour changes). So this harness proves
the two paths are equivalent for whatever replay configuration you pass; it does not recompute
that lab number. Once those rules land in the replay, rerun the command above to check the figure
on both paths.

## Deliberately not done yet

- Behaviour changes: the proven-fix rules, regime-weighted voting, LLM second opinion, boss-approved
  target exits, and the stricter `config/risk_limits.yaml` on the paper desk.
- Full founder controls (per-position overrides, lot or target changes, time-window blacklist).
  The desk handles pause, resume and flatten only.
- Persistent ledger and audit for the live paper loop. It re-replays the whole session on each
  heartbeat, so it would re-book the same orders. It needs an incremental loop first. The event
  path currently uses an in-memory ledger and audit per replay.
- Cross-process services over Redis. The event path needs the synchronous in-memory bus because
  handlers share engine state. `RedisStreamsBus` is ready as transport and audit only.
- Splitting the 22 legacy analysts into their own modules with their own tests. Today they are
  thin views over `collect_analyst_votes`, so a crash in that function makes all of them ABSTAIN.
- Reconciliation between PaperBroker and the ledger during the event path (Phase 1 `reconcile`
  exists; wiring it into the desk loop comes later).

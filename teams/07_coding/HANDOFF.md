# Handoff log — Team 07 Coding

## As of now (2026-10-04 IST) — C10-01 10 customer paper accounts (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09 / 05
Date:     2026-10-04
Status:   PAPER / C10-01 / NO_PROMOTE
Accepted: accounts.yaml templates customer-01..10
  disabled. Optional customers.example.yaml via
  AAD_CUSTOMERS. CLI enable/disable refuse live.
  Registry cap 10. IsolatedBook still fail-closed
  across all 10 ids. Unknown id closed.
Rejected: Live broker path. Shared book.
  Auto-enable. signals:public (05 / V2-23).
  Encrypted customer creds (V2-24).
UNKNOWN: Wiring IsolatedBook into oms/ledger
  for ten concurrent exec processes.
```

## As of now (2026-10-04 IST) — V2-25 off-market shadow order harness (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-25 / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
Accepted: packages/harness fail-closed gates +
  MockOrderBroker submit+cancel. dhan_live imported
  only after --transport dhan. CI install/lint/mypy
  include harness. No DhanBroker. No oms.router.
  Merged main d26297f (#79 V2-24) without enabling live.
Rejected: Default live client. Mode live/limited_live.
  Dual-tape edits. Exit playbook promote.
UNKNOWN: Real Dhan ACK+CANCEL latency on the
  founder machine (human).
```

## As of now (2026-10-04 IST) — V2-22 accounts layer (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-22 / NO_PROMOTE
Accepted: packages/accounts + config/v2/accounts.yaml.
  IsolatedBook per account_id. Signal/exec
  handler sets disjoint. runtime signal /
  exec CLI paper stubs. No DhanBroker.
  CI install + ruff/mypy on the package.
Rejected: Live orders. Shared paper book.
  Encrypted customer creds (V2-24).
UNKNOWN: Wiring IsolatedBook into oms/ledger
  stores on a later M2 ticket.
```

## As of now (2026-10-04 IST) — V2-21 Postgres LedgerStore (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-21 / NO_PROMOTE
Accepted: Postgres LedgerStore + STATE_DSN config +
  fail-closed migrations + export/cutover checksums +
  dual-engine CI (sqlite always; postgres when DSN set).
  Default remains SQLite-WAL. No live broker.
  Merged origin/main: hygiene #35 deletes kept;
  V2-27 basket + V2-23 auth foundation kept.
Rejected: Day-1 Postgres default. Live orders.
  Rewriting V2-10 SqliteLedgerStore. Warehouse DuckDB retarget.
UNKNOWN: Founder-box Postgres cutover after a real paper session.
```

## As of now (2026-10-04 IST) — V2-23 auth foundation (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-23 stubs / NO_PROMOTE / no live orders
Accepted: packages/auth fail-closed HS256 JWT + founder TOTP.
  Control refuses customer / refresh / missing 2FA when
  `auth` is present. Gateway verifies Bearer JWT, 2FA for
  /v2/control, role channels, REST 10/s + WS 5/s + cmd 1/s.
  Customer = signals:public + CUSTOMER_TALK fields.
  Env names only in .env.example. No secrets in git.
Rejected: pyjwt dependency (stdlib HMAC until V2-24).
  Password login / SSO. Trusting query tokens.
  Live orders. Legacy /paper/* gating.
UNKNOWN: V2-22 account rows. V2-24 secret store.
```

## As of now (2026-10-04 IST) — V2-27 paper/shadow basket (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-27 / NO_PROMOTE
Accepted: Shadow loads registry + exits/defaults.yaml +
  approved_paper_shadow.yaml (dated YAML wins).
  Dry-run TEST-CROSS ENTER. Approved R8 rows
  log PENDING_LAB. SHADOW_FLAT only.
  Mac: ls basket then shadow-start; dual-tape stays.
Rejected: Live / live_eligible basket stages.
  TEST-CROSS in the real basket. Legacy
  CANCEL/COVER. Replacing dual-tape.
  STRAT-015+. Playbook enable.
UNKNOWN: Session-night tape with closed 1m
  bars and non-PENDING_LAB plugins.
```

## As of now (2026-10-04 IST) — V2-24 secret store (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-24 / NO_PROMOTE
Accepted: packages/secretstore + install.sh/CI
  mypy --strict. Fake age keys in tmp only.
  FileSecretStore + DiskBlobBackend.
  AccountStub / MemoryAccounts Protocol.
Rejected: cryptography lock pin. Live Dhan.
  Committing identity files. Env fallback on.
UNKNOWN: age CLI bit-compat with aad-age/v1.
```

## As of now (2026-10-04 IST) — V2-26 Mac start hole (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-26 fix / NO_PROMOTE
Accepted: Lazy runtime.recovery so kernel/shadow.runner
  import without brokers. desk.sh proves
  import shadow.runner and python -m shadow,
  then fail-closed if the follower dies.
  .venv-v2 still has no brokers/ledger/risk-engine.
Rejected: Installing brokers into .venv-v2.
  Widening legacy .venv. Live orders.
  Playbook enable. Replacing dual-tape.
UNKNOWN: Session-night compare still missing.
```

## As of now (2026-10-04 IST) — V2-26 shadow launcher (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-10-04
Status:   PAPER / V2-26 / NO_PROMOTE
Accepted: packages/shadow + desk.sh hooks +
  .venv-v2 install of contracts/events/runtime/shadow.
  Kernel + TapeSource only. No DhanBroker.
  No oms.router. No desk.paper write.
Rejected: Live modes. Morning auto-start.
  Copying legacy CANCEL/COVER exits.
  Installing into .venv.
UNKNOWN: Live recorder tail on a session
  night (human). Feed-down is fail-closed.
```

## As of now (2026-09-28 IST) — P0 CPython 3.9 legacy import (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / Mac CPython 3.9 import / NO_PROMOTE
Accepted: dhan_client.feed OnPacket/OnFrame use typing.Optional/Union so
  PEP 604 | is not evaluated at alias assignment on 3.9. Walked api.main,
  jobs, trading_agents_india dual-tape, health.supervise, python -m jobs
  post-market --help — no other 3.9 language breaks. CI job legacy-py39
  installs the Mac legacy set and checks import + token-free /health and
  /paper/founder-book.
Rejected: Rewriting postponed annotations. Behaviour changes. GATE_ENFORCE=1.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main 91593d6 (#66) into V2-gateway-auth (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-13 auth ∪ V2-11 real controls / NO_PROMOTE
Accepted: Normal-merge origin/main 91593d6. Keep BOTH:
  #67 Bearer/WS auth, query-credential refuse, bind fail-closed,
  mutating 1/s rate limit. Main V2-11 real submit (not stub 501),
  localhost-or-founder authorize_control, V2_GATEWAY_AVAILABLE
  so py3.9 /paper/* stays up. desk.sh still uvicorn 127.0.0.1:8000.
Rejected: Rebase / force-push. Dropping auth or real V2-11 apply.
  GATE_ENFORCE=1.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main 6d4e645 (#64) into V2-recorder (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-recorder ∪ gateway ingest / NO_PROMOTE / no live orders
Accepted: Normal-merge origin/main 6d4e645. Keep BOTH imports:
  uuid (main command_id) + dataclasses.replace (#63 v=1 bus stamp).
  #63 stamps available_ts from hub clock so MemoryBus is not lookahead.
  test_ingest_from_memory_bus stays unpinned GatewayHub(bus).
Rejected: Rebase / force-push. Dropping either import.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main 045ce0e (#65) into V2-OMS-risk (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-OMS-risk ∪ V2-08b ∪ V2-11 / NO_PROMOTE / no live orders
Accepted: Normal-merge origin/main 045ce0e (#61 #55 #59 #60 #65). Keep BOTH:
  founder veto first on submit, then _catastrophic_price(risk, qty).
  exit() uses store-agnostic _live_position; missing row skips resize
  (snapshot flatten never raises). Live row uses #64 Veto (FLAT/SUB_LOT),
  not raise. cancel() + _reject_exit stay. Ledger keeps planner helpers
  + Decimal order_charges. Gateway clock pin stays unpinned.
Rejected: Rebase / force-push. Dropping founder veto, risk-qty stop,
  or raising on a missing store row.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main c723001 (#59) into V2-16 (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-16 / NO_PROMOTE / advisory BLOCK (exit 0)
Accepted: Normal-merge origin/main c723001 (incl #61 #55 #59).
  Gate stays advisory. GATE_ENFORCE is not set.
Rejected: Rebase / force-push. GATE_ENFORCE=1.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — V2-16 advisory mode (do not paint CI red)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-16 / NO_PROMOTE / advisory BLOCK (exit 0)
Accepted: Verdict step always writes the full gate JSON.
  Default advisory: BLOCK exits 0. GATE_ENFORCE=1 BLOCKs with exit 1.
  --merge / --push still exit 2. Missing/stub never PASS.
Rejected: GATE_ENFORCE=1. Making gate a required check today.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main 0d7951c (#61+#62) into V2-08b (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-08b + V2-11 union / NO_PROMOTE / no live orders
Accepted: Normal-merge origin/main 0d7951c. Keep BOTH:
  V2-11 _founder_entry_veto first on submit, then V2-08b
  _catastrophic_price(risk, qty). exit() uses store-agnostic
  _live_position; missing row skips resize (snapshot flatten
  never raises). Live sqlite/memory row still resizes.
Rejected: Rebase / force-push. Dropping founder veto or risk-qty stop.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — merge main 78013e4 (V2-10) into V2-08b (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-08b + V2-10 union / NO_PROMOTE / no live orders
Accepted: Normal-merge origin/main 78013e4 (#58). Keep BOTH:
  V2-10 SqliteLedgerStore / crash recovery / FEED_STALE /
  HALT_UNREADABLE / STRATEGY_DAILY_LOSS / reduce-only
  and V2-08b planner/chase. MemoryLedger is the in-memory
  adapter (not superseded): entry_plans + snapshot veto
  fields. Planner PlanStore API also writes the real
  ledger entry_plans table. Risk before broker. Never MARKET.
Rejected: Two durable ledgers. Rebase / force-push.
UNKNOWN: none
```

## As of now (2026-09-28 IST) — V2-11 + main 78013e4 (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-11 / NO_PROMOTE / no live orders
Accepted: Normal merge of origin/main 78013e4. Kept #54 BAR_CLOSED
  same-underlying + #61 targeted FOUNDER_COMMAND skip. Kept #58
  FEED_STALE / HALT_UNREADABLE / STRATEGY_DAILY_LOSS / reduce-only
  and #61 FOUNDER_LOTS_CAP. Runtime keeps flatten and llm-advisor.
Rejected: Rebase / force-push. Dropping any veto.
UNKNOWN: none for this merge.
```

## As of now (2026-09-28 IST) — V2-11 fix round (PR #61 verifier)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-28
Status:   PAPER / V2-11 / NO_PROMOTE / no live orders
Accepted: Normal merge of PR #49 head 65fea643 (lot-size guards).
  OrderRouter.submit consults CommandBook: PAUSE/STOP/INDEX/
  BASKET_REMOVE veto entries; SET_LOTS caps lots (ceiling from
  config/risk_limits.yaml paper max_lots_per_trade=25).
  KILL cancels working ENTRY orders and flattens via the wired
  paper manager. Command log JSONL under data/ledger (same tree
  as the ledger); resent command_id after restart is a no-op.
  attach_gateway uses AAD_STATE_DIR or cwd (not mkdtemp on the
  real api). Founder token is a label, not auth.
Rejected: Rebase / force-push. DhanBroker. requirements/* edits.
UNKNOWN: retarget to main after #45, #49, #58 merge.
```

## As of now (2026-09-27 IST) — V2-11 founder controls v2 (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-11 / NO_PROMOTE / no live orders
Accepted: Branched from cursor/v2-10-ledger-crash-recovery-dcfd, then
  a normal merge of PR #49 head cursor/v2-09-position-manager-7d86
  @ 2229844f8baad6c3a09209d770ee96434a850c4c. packages/control
  command log + engine handler + gateway /v2/control routes.
  Flatten/kill go through PositionManager + risk.check_flatten.
  KILL_SWITCH file + python -m runtime flatten work with Redis
  down. DhanBroker never constructed. requirements/* unchanged.
  Later: normal merge of updated V2-10 tip (atomic fills / lot veto).
Rejected: Live/Dhan path. Gateway applying entries. Rebase / force-push.
UNKNOWN: retarget to main after #45, #49, #58 merge.
```

## As of now (2026-09-27 IST) — V2-19 llm-advisor service (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-19 / NO_PROMOTE / no live orders
Accepted: Wiring python -m runtime llm-advisor over desk_ml.llm_analyst.
  Consumes DECISION (boss:decisions), publishes ADVICE. Replay uses
  RecordedProvider/mock. Queue-decoupled so a hung provider cannot
  change, delay, or veto an engine decision. EventType DECISION+ADVICE.
Rejected: Putting the advisor on the engine handler list. Live OpenAI
  in CI/replay. DhanBroker. Rebase / force-push / relock.
UNKNOWN: Redis stream name mapping (prefix+DECISION vs boss:decisions)
  until compose wires a topic map.
```

---

## As of now (2026-09-27 IST) — V2-09b founder KILL flatten (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09
Date:     2026-09-27
Status:   V2-09b PAPER fix / NO_PROMOTE
Accepted: Founder FOUNDER_COMMAND kind=KILL now emits
  KILL_SWITCH / plan_field=kill_switch. REG-18a mismatch
  logs CRITICAL and still flattens. house_stop_premium
  snaps UP onto the 0.05 grid.
Rejected: Raising out of on_market on a REG-18a mismatch.
UNKNOWN: none
```

---

## As of now (2026-09-27 IST) — V2-09b exit primitives (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09
Date:     2026-09-27
Status:   V2-09b PAPER exit primitives on V2-09 / NO_PROMOTE
Accepted: StructuralStop, AtrStop (fixed at fill), GracePeriod,
  SignalFlipExit (own_opposite, boss_opposite on bar close).
  defaults.yaml loader freezes values + file hash into
  defaults_from. REG-18a-e. Grep: no CANCEL_AGAINST /
  CANCEL_ADVERSE / CANCEL_STALL / COVER_LONG_UNWIND in
  packages/oms or packages/strategies. Inherit = ₹30k
  house stop + native invalidation; no native level
  refuses. V2-09 stop qty == net invariant kept.
Rejected: Live/Dhan. Intraday exit retune. Loosening REG-02
  resize/flatten. STRAT-015+.
UNKNOWN: V2-10 durable rehydrate of frozen atr_stop_level.
```

---

## As of now (2026-09-27 IST) — V2-10 fix round (atomic / idempotent / P&L / qty / Decimal)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-10 / NO_PROMOTE / no live orders
Accepted: record_fill owns one BEGIN IMMEDIATE; raise
  after INSERT INTO fills rolls back; replay = 1 fill.
  UNIQUE(client_order_id, fill_seq) + fill_id.
  record_fill twice is a no-op. recover() twice does
  not rebook halt. recharge_pending UPDATEs PENDING
  in place. Close writes gross 650 / charges once /
  CLOSED / net_qty 0. insert_order no longer does
  qty*lot_size. rebuild lots=1 lot_size=65. Decimal
  money()/money_sql() on the v2 path. Merged V2-08
  7c09f84 (lot_size mismatch veto) with a normal merge.
Rejected: Rebase / force-push / merge of this PR.
  DhanBroker. Editing Mac-ops merge files. Relock.
UNKNOWN: GitHub CI on the new head.
```

---

## As of now (2026-09-27 IST) — V2-08 lot-size exchange-only (PAPER)

```text
From:     teams/07_coding
To:       00 / 09
Date:     2026-09-27
Status:   V2-08 PAPER router / NO_PROMOTE
Accepted: Exchange lot_size always from lot_size_for(instrument_id).
  decision.lot_size or stored lot_size that differs is LOT_SIZE_MISMATCH
  veto; nothing reaches the broker. Send-time guard: qty>0 and
  qty % exchange lot == 0. Flatten closes only whole lots <= net_qty
  and alerts ODD_LOT_FLATTEN when net is not a multiple.
Rejected: Using decision.lot_size as the send qty. Rounding leftover
  units UP past net_qty.
UNKNOWN: none
```

## As of now (2026-09-27 IST) — V2-10 ledger v2 + crash recovery (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-10 / NO_PROMOTE / no live orders
Accepted: Branched from cursor/v2-08-order-router-fills-1553 (already
  contained origin/main 90455a6). Additive migrations 001_core +
  002_v2_core (session_halts, ingest_errors, positions_v2, checkpoint,
  outbox). SqliteLedgerStore implements LedgerStore. Recovery sequence
  of §3.5. Paper broker rebuild_from_ledger. FEED_STALE +
  STRATEGY_DAILY_LOSS + HALT_UNREADABLE. REG-02b/04a (real SIGKILL),
  04b, 05e, 06b, 16c, 17a-d. Legacy Ledger() never auto-migrates;
  DEFAULT_LEDGER_PATH refused unless allow_legacy. requirements/*
  byte-identical. install.sh unchanged (ledger already on the list).
Rejected: Auto-migrate of the Monday sqlite path. DhanBroker.
  Rebase / force-push / relock.
UNKNOWN: whether a later V2-08 merge commit lands before this PR
  is retargeted to main after #45.
```

---

## As of now (2026-09-27 IST) — V2-04 onto main 971bf81 / V2-15 (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-04 / NO_PROMOTE / no live orders
Accepted: Merged origin/main 971bf81 (PR #51 V2-15) with a
  normal merge. Kept V2-15 __main__ dispatcher, JOBS,
  publish_atomic, services, test_v2_15, pyproject 2.15.0.
  Added kernel/config/store/sources additively. engine
  --once still writes ENGINE_STATUS READY then runs the
  kernel on an empty tape. JobTimeout is the timeout
  class; DeadlineExceeded is an alias. requirements/*
  byte-identical to main. install.sh unchanged.
Rejected: Replacing the V2-15 dispatcher. Second jobs
  module. Rebase / force-push / relock.
UNKNOWN: none
```

---

## As of now (2026-09-27 IST) — V2-04 kernel onto current main (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-04 / NO_PROMOTE / no live orders
Accepted: Merged origin/main (a756e70) into PR #38 with a
  normal merge. One packages/runtime: keep V2-17 bench_legacy
  and python -m runtime bench-legacy; add kernel, jobs,
  wiring, store. Config loader is runtime.config (not
  contracts): contracts owns envelope/schema/clock/ids;
  last-good YAML is runtime config. Deleted duplicate
  ListSource; reuse marketdata.sources.ListSource via
  envelopes_from_list_source. __main__ left as main's
  minimal dispatcher (V2-15 adds commands additively).
  requirements/* byte-identical to main. install.sh is
  main's list (runtime already once). events import
  resolves (in-repo sibling; pyproject deps stay empty
  so check_local_names / PyPI 'events' cannot collide).
Rejected: Second runtime package. contracts.config home.
  sys.exit inside run_with_deadline (library raises
  DeadlineExceeded / JobTimeout; CLI exits 1). Rebase
  or force-push. Relock of requirements/.
UNKNOWN: V2-15 (#51) jobs.py will merge onto this
  run_with_deadline + JobTimeout alias.
```

---

## As of now (2026-09-27 IST) — V2-15 merged main a756e70 (#36/#44/#42/#48) (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09 / founder
Date:     2026-09-27
Status:   PAPER V2-15 / NO_PROMOTE
Accepted: Merged origin/main a756e70 (V2-17 #36, V2-14 #44, #42, #48).
  Keep this branch __main__/__init__/pyproject (one runtime package,
  combined dispatcher). Took main bench_legacy.py, test_bench_legacy.py,
  check_frozen_legacy.py, config/legacy_frozen.sha256, and the real
  frozen-legacy CI job (one job). requirements/* byte-identical to main
  (prometheus-client from #44). install.sh already = main list + runtime.
  python -m runtime health reads the breaker file and writes
  health_status.json; it does not import health.v2_* or start /metrics.
  python -m health is the legacy PR-004 monitor. V2-14 MetricsEndpoint
  is opt-in in the health package. One compose health process. Mac:
  scripts/desk.sh unchanged.
Rejected: Second frozen-legacy job. Starting a second health HTTP
  server from runtime. Live-orders compose. Touching legacy engine
  or data/.
UNKNOWN: Dhan token refresh for unattended VPS (VERIFY).
```

---

## As of now (2026-09-27 IST) — V2-15 + main merge + #36 runtime compat (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09 / founder
Date:     2026-09-27
Status:   PAPER V2-15 / NO_PROMOTE
Accepted: Merged origin/main (6e5e582 V2-02). requirements/* byte-identical
  to main. install.sh = main list + runtime (once). One packages/runtime
  pyproject; python -m runtime dispatches engine/health/reset-breaker/job
  and bench-legacy. Keep/take list executed after #36 landed (see newer
  block).
Rejected: Duplicating a placeholder frozen-legacy job. Live-orders
  compose. Touching legacy engine or data/.
UNKNOWN: (resolved) #36 has merged.
```

---

## As of now (2026-09-27 IST) — V2-15 compose / deploy / breaker (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09 / founder
Date:     2026-09-27
Status:   PAPER V2-15 / NO_PROMOTE
Accepted: Dockerfile (non-root, read-only root), compose replay (no creds),
  compose.vps, Caddyfile, aad.service, deploy/backup/restore, restart
  breaker + reset-breaker, job timeouts, §5.3 CI jobs, founder-guide V2
  note. Stub engine writes ENGINE_STATUS READY (V2-04 kernel not here).
  V2-14 breaker_open is a Protocol (BreakerView); this ticket owns the file.
Rejected: Live-orders compose profile. Copying V2-14 health files.
  Touching legacy engine, desk.sh behaviour, data/, config/v2/exits.
UNKNOWN: Dhan token refresh for unattended VPS (VERIFY). Docker-in-CI
  image build needs the runner's docker socket.
```

---

## As of now (2026-09-27 IST) — V2-09 paper position manager (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 09
Date:     2026-09-27
Status:   V2-09 PAPER positions on V2-08 router / NO_PROMOTE
Accepted: Exit loop from the held position + ExitPlan
  (catastrophic, time stops, EOD, target/partial/trail,
  founder, kill, strategy, failsafe MTM). IST clock.
  REG-02a after envelopes, REG-03a-c, REG-05d, REG-15a-d.
  In-place modify_order(order_id, qty) for protective SL-M
  so stop qty == net. Cancel-then-replace only if modify
  unsupported. Bounded idempotent replace retry; CRITICAL
  STOP_RESIZE_FAILED + paper market flatten if still failing.
  check_exit always allows reduce-only SELL <= net (kill
  included). Never restore a stop larger than live net.
Rejected: Durable ledger/rehydrate (V2-10). Structural /
  ATR / grace / flip / defaults.yaml (V2-09b). Live/Dhan.
  Cancel-then-naked-place without retry/flatten.
UNKNOWN: V2-10 halt row / restart rehydrate.
```

---

## As of now (2026-09-27 IST) — V2-13 token-only ROLE_ACL (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-13 / NO_PROMOTE / no live orders
Accepted: One ROLE_ACL per role, enforced on WS snapshot, WS
  deltas, GET /v2/snapshot, GET /v2/trace. Identity is the
  paper token only (founder iff token=founder). Missing or
  unknown token = customer. Client-supplied role is never
  trusted. Subscribe role/token fields yield IDENTITY_IMMUTABLE
  and do not change the connection. Customers get only
  CUSTOMER_TALK public signal fields; no legacy board /
  founder / founder_book / account overlay. /v2/trace is
  founder-only (403 otherwise). Control POST stays 501.
Rejected: JWT (V2-23). Trusting query/body role. Customer
  overlay of desk JSON. Changing 501 control or loopback.
UNKNOWN: Founder UI behind VITE_V2_FEED=1 now sends the
  paper token=founder label (not a secret; JWT still V2-23).
```

---

## As of now (2026-09-27 IST) — V2-13 gateway websocket + UI rewire (PAPER)

```text
From:     teams/07_coding
To:       founder / 00 / 09
Date:     2026-09-27
Status:   PAPER / V2-13 / NO_PROMOTE / no live orders
Accepted: GET /v2/snapshot + WS /v2/ws (subscribe, snapshot,
  ordered seq deltas, resync). Role-scoped channels: customer
  token cannot take founder channels. REG-04c snapshot lists
  every ledger-open position. Decision trace from correlation
  id includes strike_choice + alternatives. Desk/Founder use
  v2 feed only when VITE_V2_FEED=1. Legacy /ui/* /ws/* stay.
  V2-11 control routes are a marked stub (501, no actions).
Rejected: Implementing founder control actions (V2-11). JWT
  auth (V2-23). Touching legacy engine / marketdata / dhan-
  client / runtime / strategies / data/ / exits defaults.
UNKNOWN: Ledger positions until V2-10 exists are
  in-memory on the hub. Playwright --v2 (PR #15 widths)
  passed on the fixture feed after SSE fallback.
```

---

## As of now (2026-09-22 IST) — freeze spill cols + 2s tick (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00 / 06
Date:     2026-09-22
Status:   PAPER UI + dual-tape / NO_PROMOTE
Accepted: Why days spilled Day/Room/Why columns sticky +
  frozen widths. Founder poll / board cache / dual-tape
  default 2s (clamp ≥2). NIFTY stays START. No live orders.
Rejected: Invent an OPEN fill (board had open_n=0).
UNKNOWN: next SOD fill after 2s ticker refresh.
```

---

## As of now (2026-09-22 IST) — spill on /desk, discarded last on /pm (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00 / 05
Date:     2026-09-22
Status:   PAPER UI / NO_PROMOTE
Accepted: Why days spilled on Desk with Day/Room/Why/Index
  filters + lined grid, columns hug data. Discarded last on
  Founder with Datetime/Who/Outcome/Index filters, IST
  date+time newest first, lined grid. Train / open fills
  / START TRADE untouched.
Rejected: trade_id join to history. Recode overlay.
UNKNOWN: live /paper/sod-exam vs mock until API is up.
```

---

## As of now (2026-09-22 IST) — /pm Now open (missed CE) (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00 / 06
Date:     2026-09-22
Status:   PAPER UI / NO_PROMOTE
Accepted: Last NIFTY CE 10:59–11:00 IST COVER_LONG_UNWIND −₹10,270
  lived ~68s. /pm had no open-ticket strip — only closed Compare
  fills. Added Now open + open rows in history. Overlay unchanged.
Rejected: Recode COVER_LONG_UNWIND / stop / fill path.
UNKNOWN: whether founder was on /desk (has current) or /pm (did not).
```

---

## As of now (2026-09-22 IST) — honesty exam newest-first + contract grid (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00
Date:     2026-09-22
Status:   PAPER UI / NO_PROMOTE
Accepted: Exam day boxes newest first; wheel maps to sideways
  scroll. Day stories date-desc. Fill contract is a per-day grid.
Rejected: Touching live book / START TRADE / fill graph.
UNKNOWN: none
```

---

## As of now (2026-09-22 IST) — /pm roster + honesty exam last (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00
Date:     2026-09-22
Status:   PAPER UI / NO_PROMOTE
Accepted: Honesty exam (06) moved to last block on /pm. Day boxes
  scroll sideways; long stories scroll down. Rooms section retitled
  "Who speaks, who spends" with 4-step line + spend vs vote rails.
Rejected: Touching live book / START TRADE / fill graph / overlay.
UNKNOWN: none
```

---

## As of now (2026-09-22 IST) — hold_trending_open_stall write=false only (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 06
Date:     2026-09-22
Status:   PAPER A/B TOOL / NO_PROMOTE
Accepted: stall_book_reason / replay / CLI flag default False.
  ValueError if write=true with flag. pytest
  test_hold_trending_open_stall_ab_only.
Rejected: Live default on. Dashboard write from A/B.
UNKNOWN: none
```

---

## As of now (2026-09-21 IST) — Close order: nightly then exam (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 06
Date:     2026-09-21
Status:   PAPER OPS / NO_PROMOTE
Accepted: desk.sh close runs jobs post-market first, then sod-exam.
Rejected: Overlay recode. Killing Vite at close.
UNKNOWN: none
```

---

## As of now (2026-09-21 IST) — Keep website, stop capture after close (NO_PROMOTE)

```text
From:     teams/07_coding
To:       founder / 00 / 06
Date:     2026-09-21
Status:   PAPER OPS / NO_PROMOTE
Accepted: scripts/desk.sh is the one founder command. morning starts
  API+Vite+dual-tape. close keeps :5173/:8000 and stops dual-tape.
Rejected: Killing the website at close. Live orders.
UNKNOWN: founder laptop sleep vs screen sessions staying up.
```

---

## As of now (2026-09-21 IST) — Desk tables stay in the viewport (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 05
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Page width is clipped at 100%. Trade history and discarded
  tables scroll inside their section. Why / Models / Notes / Details
  wrap (smaller type). Path meters have a 14rem cap so the fill cannot
  leave the panel.
Rejected: Ellipsis on Why. Widening the whole site for extra columns.
UNKNOWN: very long JSON in Details still wraps; row height grows.
```

---

## As of now (2026-09-21 IST) — Discarded list: Time first, newest first (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 05
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Discarded by boss or dealer is a table. Column 1 is IST
  time. Rows sorted last_updated_ts / closed_ts / ts descending.
Rejected: Grouping that hides which ticket happened when.
UNKNOWN: skip rows without a ts still sort last with "—".
```

---

## As of now (2026-09-21 IST) — Desk founder UX: manage levels, path, clock, discarded, history (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 05 / 06
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Human override on an OPEN paper fill asks for required
  TARGET + STOP, confirm, then SET_LEVELS. Naked EXIT refused.
  Unfilled working limit can still CANCEL. Path uses stop→entry→
  target marker plus remaining-to-target (green pts) vs risk-to-
  stop (red pts). IST digital clock + 5-min bar countdown on /desk.
  Discarded list shows instrument/side/strike/ticket/outcome and
  Dealer ×N / Boss ×N. Trade history is overflow-x table with
  grid lines, long columns last, column hide in localStorage.
Rejected: Immediate flatten as human priority. Two unexplained
  percentages that look like they sum to 100%. Widening the Desk
  page for history. Live broker order.
UNKNOWN: expiry on skip rows until engine stamps it; 5-min clock
  uses system time in Asia/Kolkata, not the dual-tape last bar.
```

## As of now (2026-09-21 IST) — founder desk (i) + selected-index control (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 06
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Dual-tape help lives on the (i) button. Control
  shows START/STOP by color; the current action is disabled.
  No per-index status boxes. Code default STOP TRADE until
  founder START on the chosen index. Tape still records all.
Rejected: Always-on help paragraph. NIFTY: START TRADE text.
  One box per index (does not scale). Default START all.
UNKNOWN: live /paper/founder-book vs mock until API is up.
```

## As of now (2026-09-21 IST) — customer `/` parked (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Customer portal parked during paper. `/` → `/desk`.
  Nav is Desk + Founder only. Customer App (live WS) not mounted.
Rejected: Customer signal feed during this paper session.
UNKNOWN: when founder wants `/` back.
```

## As of now (2026-09-21 IST) — founder index book + history dropdowns (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 06
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: /pm Founder book today (checkboxes). NEW fills only.
  Dual-tape still records all indices. Discarded list hides
  FOCUS_NIFTY_* (not a boss/dealer kill). Trade history
  filters are three dropdowns from the actual rows.
Rejected: Boss/dealer/analyst choose the index book. Flatten
  the open NIFTY CE. 30 index chip buttons.
UNKNOWN: engine silent-skip until dual-tape restarts after
  this open ticket closes.
```

## As of now (2026-09-21 IST) — customer `/` no fixture PE (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 05
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: Customer hero uses MIX-DEFAULT-BUY paper ticket
  (premium + lots) or WAITING. Fixture BUY PE 24850 +
  DATA_INSUFFICIENT no longer paints as IN-PROGRESS.
Rejected: Invent premium from index 24850. Live orders.
UNKNOWN: /paper/signal until this API process is restarted.
```

## As of now (2026-09-21 IST) — live money slate (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 06
Date:     2026-09-21
Status:   PAPER UI / NO_PROMOTE
Accepted: /pm money tiles use live board only. Lab extra_closed
  + day_series emptied. "Today" = session_ist_date, not newest
  trainer day. Graph catalog stays. No live orders.
Rejected: Paint 18 Sep lab P/L as Monday. Promote.
UNKNOWN: one 10-lot NIFTY CE already OPEN from before lot recode.
```

## As of now (2026-09-20 IST) — /pm Honesty exam panel (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder / 06
Date:     2026-09-20
Status:   PAPER UI / NO_PROMOTE
Accepted: Founder /pm section Honesty exam (06). GET /paper/sod-exam
  + mock fallback. No overlay recode. No promote.
Rejected: Customer `/` exam dump. Live orders.
UNKNOWN: live :8000 until that API process is restarted to pick up the route.
```

## As of now (2026-09-20 IST) — founder train graph + tester book (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder
Date:     2026-09-20
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Compact founder_lab overlay (not a second 5k dump).
  Clickable SOD graph + watchers. STRAT-001–014 + models +
  5m confirm/kill indicators on /pm. Desk/founder share
  filterable history (TARGET/T2/STOP/TRAIL/CANCEL/TIME).
  5s fetch cache, AbortController, 12–15s poll. Extra
  trainer days + lab fills for revalidate. Orders refused.
Rejected: Live Super Orders. Promote. Heavy chart libs.
UNKNOWN: live /paper/ml-books vs mock until dual-tape write.
```

## As of now (2026-09-20 IST) — simple founder / desk / customer dashboards (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder
Date:     2026-09-20
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: One site, three views. Founder /pm = trades, win %,
  balance, daily profit/loss, model win % today, charges +
  clone-drag. Desk /desk = current signal life (ACTIVE /
  PROGRESS / STALE / DEAD / DONE), path + trail SL, path
  score (not win rate), history outcomes (TARGET HIT /
  TARGET 2 / STOP / TRAIL / CANCELLED), why, auto-refresh,
  discarded-by-boss/dealer last. Customer / stays one ticket.
Rejected: npm restart. Super Orders. Promote. Fake live fills.
UNKNOWN: live /paper/ml-books vs mock until dual-tape write.
```

## As of now (2026-09-20 IST) — ML paper board SOD copy + analyst tab (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 06 / founder
Date:     2026-09-20
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: SOD-on copy: one MIX-DEFAULT-BUY ticket + analyst
  room. independent_books false. Analysts tab shows MATCH/
  DISSENT/SPOKEN_PICKER_HOLD even when ignored. Mock patched.
Rejected: npm restart. Super Orders. Promote. Parallel fills
  claimed while SOD on.
UNKNOWN: live /paper/ml-books vs mock until dual-tape write.
```

## As of now (2026-09-18 IST) — /pm and /desk live paper UX (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / founder
Date:     2026-09-18
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Founder /pm and research /desk now lead with unique
  net, TARGET vs TIME vs STOP, open path to target/SL, collapsed
  clone fills, grouped skips. Lab toys folded on /desk.
Rejected: npm restart. Super Orders. Promote.
UNKNOWN: Dual-tape still stamps old SUCCESS until reload.
```

## As of now (2026-09-17) — closed board: SL money vs filled-cancel pnl (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 06
Date:     2026-09-17
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: lost₹ uses sl_loss_inr only. Do not copy every LOSS
  into money-lost. Compact /pm too.
Rejected: npm restart required. Super Orders. Promote.
```

## As of now (2026-09-17) — ITM CE/PE bin on ML paper dashboard (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 06
Date:     2026-09-17
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MlPaperDashboard section ITM CE / PE bin (three charts)
  with strike/moneyness/px/vol/OI/delta and PE vs CE votes. Compact /pm too.
Rejected: npm restart required. Super Orders. Promote.
```

## As of now (2026-09-17) — seen-not-taken dashboard section (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 06
Date:     2026-09-17
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MlPaperDashboard section Seen but not taken / cancelled
  with skip+cancel reasons and last-3 observations. Compact /pm too.
Rejected: npm restart required. Super Orders. Promote.
```

## As of now (2026-09-17) — ticket sort OPEN first CLOSED last (NO_PROMOTE)

```text
From:     teams/07_coding
To:       00 / 06
Date:     2026-09-17
Status:   PAPER UI / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: MlPaperDashboard open then closed; last_updated desc.
Rejected: npm restart required. Super Orders. Promote.
```

## As of now (2026-09-15) — desk_ml warehouse join + dual-tape score

```text
From:     teams/07_coding
To:       00 / 04 / 06 / 08
Date:     2026-09-15
Status:   CLI shipped / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: bars_1m + ohlc_bars + ATM warehouse symbols; score --source
  dual-tape; ML-002 score_mrr_last; embargo-bars on fit.
Rejected: Super Order; ExecutionClient; production MIX writes.
CLI: python -m desk_ml score --underlying NIFTY --source dual-tape
```

## As of now (2026-09-15) — desk_ml book-tune / mrr-fit (no Dhan)

```text
From:     teams/07_coding
To:       00 / 04 / 06 / 08
Date:     2026-09-15
Status:   CLI shipped / UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: inventory, mrr-fit, book-tune CLIs. Cache JSON + warehouse only.
Rejected: Super Order; production MIX writes; live history refresh in this job.
CLI: python -m desk_ml book-tune --calendar-days 21
```

## As of now (2026-09-14) — packages/desk-ml ML-001 (no Dhan loop)

```text
From:     teams/07_coding
To:       00 / 04 / 08
Date:     2026-09-14
Status:   OVERLAY CODED / CACHE FIT ONLY / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: packages/desk-ml fit/score CLI. Consumes recon ohlc + premium_tape.
Rejected: sklearn hard dep; live orders; writing MIX params.
```

## As of now (2026-09-10) — Code only USE paths in HQ book

```text
From:     teams/07_coding
To:       00 / 03 / 08
Date:     2026-09-10
Status:   DOCS BIND / NO NEW CLIENT
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: packages/dhan-client remains the only HTTP client. New calls
  must exist on DHAN_API_END_TO_END.md USE/STORE list. Writes stay refused.
Rejected: pip-wrapping a second dhanhq bot; MCP trade; /alerts/orders.
```

## As of now (2026-09-10) — multi-TF ohlc_bars

```text
From:     teams/07_coding
To:       02 / 04 / 06 / 00
Date:     2026-09-10
Status:   OHLC CODED / LIVE PULL DONE / NO LOOP
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: ohlc_bars + load_bars; candles --live wrote INDEX 1m/5m/15m/60m/1d
  and resampled 3m/1w. Reader is the same for history and a later live tick.
Rejected: Fake HQ 3m REST; poll loop; OPTIDX/FUTIDX candles this ticket.
UNKNOWN: INDEX volume still not a VWAP tape (02).

Artifacts: warehouse/ohlc.py, candles.py
```

## As of now (2026-09-10) — one-shot warehouse ingest

```text
From:     teams/07_coding
To:       00 / 05 / 08 / 09
Date:     2026-09-10
Status:   INGEST CODED / LIVE ONCE / NO LOOP
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: python -m warehouse ingest --live wrote compact chain + 1m bars +
  MIX score + dealer HOLD (no typical premium range). Probe JSON ingested.
Rejected: Poll loop; full OC persist; git-add sqlite; live orders; npm.
UNKNOWN: MIX EARLY leans are WAITING / NO_PROMOTE — dealer did not publish.

Artifacts: packages/warehouse/ingest.py, data/knowledge/warehouse.sqlite (local)
```

## As of now (2026-09-09) — DATA-001 warehouse package

```text
From:     teams/07_coding
To:       00 / 05 / 08 / 09
Date:     2026-09-09
Status:   WAREHOUSE CODED / PARTIAL
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: packages/warehouse schema + CLI; WAL; indexes; counsel_events cache
  keys; protected KB paths; gitignore warehouse.sqlite.
Rejected: Live ingest; git-add sqlite; browser Dhan; live orders.
UNKNOWN: no production writers from desk_intel / trading_agents yet.

Artifacts: packages/warehouse, docs/WAREHOUSE.md
```

## As of now (2026-09-09) — Fast app engineering standards

```text
From:     teams/07_coding
To:       00 / 05 / 08 / 09
Date:     2026-09-09
Status:   SPEC / NOT_CODED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: fast path reads precomputed signal payload; no browser Dhan/LLM;
  SQLite append-only events + read model; /pm SLO cards; customer mobile-first
  UX; dealer feasibility state hooks.
Rejected: compute strategy in browser; raw chain in customer payload; live orders;
  day-1 vector DB or DB server migration.
UNKNOWN: schema and components not implemented.

Artifacts: docs/ENGINEERING_SECTIONS.md, docs/PRODUCT_ARCHITECTURE_STANDARDS.md,
  docs/TOKEN_ML_STRATEGY.md, docs/CUSTOMER_PORTAL_UX.md
```

## As of now (2026-09-09) — D1 sections + /pm spec

```text
From:     teams/07_coding
To:       00 / 08 / 09 / founder
Date:     2026-09-09
Status:   SPEC / PARTIAL
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Engineering boss; C1–C8 section bosses; coding docs in teams/07_coding/docs;
  SQLite+FTS5 now; /pm TODO; one site three views.
Rejected: Live orders; npm restart unasked; git-add sqlite; auto-retune.
UNKNOWN: /pm, warehouse DDL, local ML not coded.

Artifacts: docs/ENGINEERING_SECTIONS.md, SKILL.md
```

## As of now (2026-09-08) — live-signals empty snapshot: CLUB-GR PARKED

```text
From:     teams/07_coding
To:       00 / 05
Date:     2026-09-08
Status:   paper snapshot copy
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: GET /paper/live-signals empty default lists Okala-IN + structure
  PAPER_WATCH, not MIX-CLUB-GR. Do not restart npm.
Rejected: Live orders.
```

Newest first.

---

## As of now (2026-09-06) — customer `/` paper dashboard (Astra UX)

Single-ticket hero + index chart (`lightweight-charts`) + confidence rail + paper book. MOCK/PAPER only. Orders refused. `npm install` once for chart dep — do not restart npm until asked.

Newest first.

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-06
Status:   customer paper dashboard MOCK / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm until asked.

Summary:
Astra+desk APPROVE_WITH_GUARDRAILS. Honesty labels on `/`.
Index chart (index units only). Confidence (i) = HYPOTHESIS detail.
Paper book + ledger field list for nightly review.
Sentiment/CAS collapsed below ticket.

Artifacts:
- teams/07_coding/docs/ASTRA_DASHBOARD_REVIEW.md
- apps/web/src/components/IndexChart.jsx
- apps/web/src/components/{SignalCard,ConfidenceBox,TodaysBook}.jsx
- apps/web/public/mock/{signal,paper_agents}.json
- apps/web package: lightweight-charts@4.2.1

Ledger fields (nightly later):
signal_id, trade_id, raw_status, displayed_status, spot, entry/SL/target premium,
lots=1 PAPER, realized_points, outcome, confidence_score, is_mock, execution_mode=PAPER
```

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-06
Status:   paper ticket UI / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm.

Summary:
SignalCard + ConfidenceBox. App merges live ticket/confidence.
ticket_confidence.py builds levels + agreement score.

Artifacts:
- apps/web/src/components/SignalCard.jsx
- apps/web/src/components/ConfidenceBox.jsx
- packages/backtest/src/backtest_engine/ticket_confidence.py
```

---

## As of now (2026-09-03) — paper signal WS

Customer `/` may overlay `/ws/signals` paper BUY CALL/PUT/HOLD. Browser never calls Dhan. **No live orders.** Do not restart npm until asked.

Copy the template from [`docs/HANDOFF.md`](../../docs/HANDOFF.md). Newest first.

---

```text
From:     teams/07_coding
To:       00 / 05 / 09
Date:     2026-09-03
Status:   paper /ws/signals / MOCK desk default / NOT RESEARCH_READY
Gate:     No live orders. Do not restart npm.

Summary:
API /ws/signals?live=1 fans Dhan index ticks through PaperSignalEngine.
apps/web subscribePaperSignals when VITE_API_URL is set. HOLD/CE/PE copy
only — no indicator soup. ExecutionClient still refuses.

Artifacts:
- apps/api/src/api/ws.py
- apps/web/src/lib/liveSignals.js

What the next team must not do:
- Call Dhan from the browser. Place orders. Restart npm unless asked.
```

---

```text
From:     teams/00_orchestrator
To:       teams/07_coding
Date:     2026-09-01
Status:   Customer / vs /desk + CasPanel mock / NOT RESEARCH_READY_FOR_PROGRAMMING
Gate:     No live Dhan. No strategy code. Do not restart npm.

Summary:
Customer desk is `/` (ticket, IN-PROGRESS, CasPanel, MOCK book P/L).
Internal `/desk` keeps indicator soup. Keep CasPanel imported on App.jsx.
Orders refused. STRATs UNVALIDATED.

Artifacts:
- apps/web/src/App.jsx
- apps/web/src/InternalDesk.jsx
- apps/web/src/components/CasPanel.jsx
- apps/web/README.md
- teams/07_coding/README.md

What the next team must do:
- Keep customer vs /desk split. Keep CasPanel on `/`.
- Keep Dhan tokens server-side.

What the next team must not do:
- Call live Dhan from the browser. Place orders. Code strategies.
- Restart npm unless the user asks.

Blockers: RESEARCH_READY_FOR_PROGRAMMING still closed.

Review: n/a
```

---

```text
From:     teams/00_orchestrator
To:       teams/07_coding
Date:     2026-09-01
Status:   Paper dashboard outcomes mock / jobs CLI dry-run
Gate:     No live Dhan. No strategy code.

Summary:
Dashboard now shows lifecycle outcomes (INVALIDATED not leftover CONFIRMED;
ACHIEVED; STOPPED/LOST; EXPIRED). Took Yes = local lots/spot/P-L. Skip =
shadow paper. GET /paper/signal shape includes lifecycle. Jobs/recon:
python -m desk_intel nightly --offline (dry-run only).

Artifacts:
- apps/web/src/components/StagedSignal.jsx
- apps/web/public/mock/signal.json
- apps/api/src/api/models.py

What the next team must do:
- Keep dashboard + jobs dry-run aligned. Keep Dhan tokens server-side.

What the next team must not do:
- Call live Dhan from the browser. Place orders. Code strategies.

Blockers: RESEARCH_READY_FOR_PROGRAMMING still closed.

Review: n/a
```

---

_(no older handoffs)_

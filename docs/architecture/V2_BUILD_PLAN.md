# V2 build plan

**Status:** PLAN (docs only). Paper only. No broker order calls, no credentials, nothing secret in the repo.
**Architecture:** [`V2_PRODUCTION_ARCHITECTURE.md`](V2_PRODUCTION_ARCHITECTURE.md) (section numbers below point there).
**Replaces for new work:** the PR order in [`docs/04_MIGRATION_PLAN.md`](../04_MIGRATION_PLAN.md). That file stays as
history and as the source of the original acceptance tests and budgets.

---

## 0. Now / Why / Next (plain English)

- **Now.** 13 of the 32 old plan steps are merged (PR #21 covers both PR-012 and PR-024). The safety parts (recorder, broker adapter, risk engine, health,
  ledger, event bus, LLM analyst, regime) are good and we keep them. The boss, desk and analyst extraction are wrappers
  around the old engine, so they get rebuilt.
- **Why.** The founder froze the old engine. Many later steps were "fix or tune the old engine". Those are dropped. The
  rest become tickets on the new stack.
- **Next.** 20 tickets of 200-500 lines each, in four parallel tracks after two shared foundation tickets. Milestone 1
  is **paper-live on the new stack** (real Dhan data, paper broker, safe restarts, founder controls, alarms). Milestone 2
  is **customer-ready** (Postgres, accounts, auth, rate limits, backups, compliance sign-off). Neither milestone says a
  strategy makes money; that is decided by the Round 8 forward bar and 09's five-pass.

---

## 1. The 32 steps re-mapped

Legend: **DONE** = merged and kept as-is. **REUSE** = merged, kept, wrapped or extended by a V2 ticket. **REBUILD** =
the requirement stays but the code is new on the V2 stack. **DROP** = not built (old-engine fix or tuning, or not
needed). **LATER** = after customer-ready.

| Step | Old title | Status in repo | V2 verdict | V2 ticket / note |
|---|---|---|---|---|
| PR-001 | Daily data recorder | merged #8 | **DONE** | Keeps running as backup capture; V2-03 reads its files, V2-12 adds the V2 tape |
| PR-002 | Broker adapter + order state machine | merged #10 | **REUSE** | V2-08 adds clock injection, fill models, paper state rehydrate, protective stop |
| PR-003 | Pre-trade risk engine | merged #10 | **REUSE** | V2-08 (clock, account scope), V2-10 (`FEED_STALE`, strategy daily cap) |
| PR-004 | Health alarms | merged #10 | **REUSE** | V2-14 adds engine/feed checks, metrics, alert rules |
| PR-005 | Ledger + charges | merged #10 | **REUSE** | V2-10 migrations, `account_id`, checkpoint, outbox |
| PR-006 | Event bus | merged #12 | **REUSE** | V2-02 envelope v2, stream per topic, consumer groups, outbox publisher |
| PR-007 | Extract boss | merged #12 (wraps `paper_scalp`) | **REBUILD** | V2-07 `boss/selector.py`; old boss frozen |
| PR-008 | Extract desk | merged #12/#14 (wraps `paper_scalp`) | **REBUILD** | V2-08 router + V2-09 position manager; old desk frozen |
| PR-009 | Extract analyst registry | merged #12/#13 | **REUSE** (interface) | `Analyst`/`Vote`/`AnalystRoom` kept for advisory filters; 22 legacy analysts frozen (V2-17) |
| PR-010 | Fix known old-engine bugs | not done | **DROP** | Old engine frozen. The lessons become no-look-ahead tests (V2-03) |
| PR-011 | Proven fixes (cooldown, DTE strikes, clock) | cooldown in risk engine | **REBUILD** | Cooldown: DONE in risk engine. DTE strike rule: V2-06 `select.py`. Time windows: config holds in V2-07 |
| PR-012 | Regime-conditional weighting | merged #21 (shadow) | **REUSE** | Labeller as a feature (V2-05); weights in boss shadow (V2-07) |
| PR-013 | Nightly warehouse ETL | draft #19 | **REUSE** (retarget) | V2-18: keep #19's structure, sink to DuckDB + Parquet |
| PR-014 | Founder emergency controls | draft #18 (old engine hooks) | **REBUILD** | V2-11 ports #18's command log design and semantics |
| PR-015 | Desk UI polish | merged #15 | **REUSE** | V2-13 rewires the UI to `/v2/ws` |
| PR-016 | LLM advisory mode | merged #17 | **REUSE** | V2-19 runs it as the `llm-advisor` service |
| PR-017 | Pre-market analysis | draft #19 | **REUSE** | V2-18 publishes `PRE_MARKET_SUMMARY`, holds and basket inputs |
| PR-018 | Model and stage attribution | not done | **REBUILD** | Falls out of correlation ids; a V2-18 warehouse query |
| PR-019 | Decision visual | partial in #15 (`/paper/trace`) | **REUSE** | V2-13 serves the correlation chain to the existing trace view |
| PR-020 | Post-market improvement loop | not done | **LATER** | After customer-ready; human merge gate stays |
| PR-021 | Backtest integration | draft #19 (expected-results gate) | **REBUILD** | V2-16 new merge gate + V2-20 forward evaluator |
| PR-022 | Lab round 2 filters | not done | **DROP** | Round 8 closed these families. New ideas enter as shadow plugins with a preregistration (V2-20) |
| PR-023 | Exits v2 (trail tuning) | not done | **DROP** (tuning) | Exit mechanics are in V2-09; no tuning (Round 8 §4.3) |
| PR-024 | Intermarket as daily regime | merged #21 (shadow) | **REUSE** | Boss shadow overlay (V2-07) |
| PR-025 | Supply/demand zones | not done | **DROP** | Research only; a shadow plugin if ever preregistered |
| PR-026 | Rebuild proxy book closer to live engine | not done | **DROP** | Old engine |
| PR-027 | Deploy automation | not done | **REBUILD** | V2-15 compose, Dockerfile, systemd, deploy/backup scripts, CI |
| PR-028 | Flow diagrams | partial | **DONE** (docs) | This package; the founder guide gets a short V2 section in V2-15 |
| PR-029 | Performance optimisation | partial in #16 | **REBUILD** | Budgets enforced in V2-16; event-driven by design |
| PR-030 | RAG | not done | **DROP** | Not on the trading path; revisit only if the founder asks |
| PR-031 | Forex adapter | not done | **LATER** | Interfaces ready (`MarketAdapter`, `BrokerAdapter`), section 2.16 |
| PR-032 | Crypto adapter | not done | **DROP** | Until the founder asks |

Count: DONE 2, REUSE 13, REBUILD 8, DROP 7, LATER 2.

---

## 2. Build tickets (in order)

Every ticket: 200-500 changed lines including tests; paper only; no credentials; synthetic fixtures only (recorded
tapes stay local and are never committed); leaves `main` runnable; includes the AGENTS.md handoff block. New packages
get `mypy --strict` and `ruff` from their first ticket. "Depends on" lists hard dependencies; anything not listed can
run in parallel.

### Foundation (sequential, both first)

**V2-01 Contracts: envelope v2, schemas, clock, ids** (`packages/contracts`, ~400 lines)
- `envelope.py` (compatible with `events.schema.Event`), payload dataclasses and JSON Schemas for every type in
  section 4.4, `SimClock`/`LiveClock`, `ids.py` (order, event, signal ids), `instruments.py` (instrument id parse and
  format, `MarketAdapter` protocol, India adapter with session hours).
- Acceptance: round-trip every fixture payload through dataclass → JSON → schema validation; an old `Event` JSON still
  loads; `SimClock.advance_to` raises on going backwards; `order_id` is 27 chars `[a-z0-9]` and stable across
  processes; property test: distinct `(account, signal, leg)` never collide in 1e6 samples.
- Depends on: none.

**V2-02 Event bus v2** (`packages/events`, ~350 lines)
- `EventType` additions; `RedisStreamsBus` with one stream per topic and consumer groups (`XREADGROUP`, `XACK` after
  the handler's commit, `XPENDING`/`XCLAIM` on start); `outbox.py` publisher (drain `outbox` rows, mark published);
  `MemoryBus` unchanged in behaviour.
- Acceptance: existing `packages/events` tests pass unchanged; a consumer killed before `XACK` gets the entry again
  and dedupes by `event_id`; outbox publishes each row exactly once to consumers after two publisher crashes; publish
  p99 < 5 ms (existing budget); Redis tests skip cleanly without a server.
- Depends on: V2-01.

### Track A: market in, decisions out (after V2-01/02)

**V2-03 Event sources, bar builder, no-look-ahead harness** (`packages/marketdata`, ~450 lines)
- `sources.py` (`ListSource`, `TapeSource`, `RecorderTapeSource` over `data/recon/*/YYYYMMDD.jsonl`), `bars.py`
  (`BarBuilder` with finalize delay, gap flag, late-tick counter), `clock.py` (`CLOCK` synthesis in sources), and the
  test harness `tests/lookahead.py` (truncation invariance, future poisoning) reused by later tickets.
- Acceptance: property test: no bar with `available_ts < end`; bars never revised; a recorder fixture day produces the
  expected bar count; sources emit non-decreasing `available_ts`; a synthetic tape with a 30 s hole yields
  `gap: true`; harness self-test catches a planted look-ahead.
- Depends on: V2-01.

**V2-04 Engine kernel** (`packages/runtime/kernel.py`, `wiring.py`, ~350 lines)
- `Engine(source, clock, bus, handlers, store, mode)`, one transaction per input, checkpoint, rehydrate mode (router
  no-op plus intent comparison), `RunSummary` with an output hash.
- Acceptance: the same tape twice gives the same output hash; rehydrate over a finished run reports zero mismatches; a
  planted non-deterministic handler (reads `random()`) is caught by rehydrate; kernel raises on time going backwards;
  `ListSource` 100k envelopes in < 5 s.
- Depends on: V2-01, V2-02. (Uses an in-memory `LedgerStore` stub until V2-10.)

**V2-05 Feature engine** (`packages/indicators`, ~450 lines)
- Incremental EMA, ATR, VWAP/TWAP, realised vol, daily HAR forecast from pre-market inputs, OI change lagged strictly
  before the decision minute; `FeatureView(strict)`; adapters for `RegimeLabeller` and `analysts/shadow.py` helpers.
- Acceptance: each indicator equals a batch reference implementation on fixtures (within 1e-9); strict view raises
  `LookAheadError` on a planted future value; the OI-jump-inside-minute fixture is invisible to the lagged feature;
  truncation invariance on all features; regime labels equal `label_bars()` on the synthetic session.
- Depends on: V2-01, V2-03.

**V2-06 Strategy runtime, registry client, strike selection** (`packages/strategies`, ~450 lines)
- `api.py` (section 2.5), `registry.py` (contract for the separately built module + YAML fallback; no basket = no
  trades), `runtime.py` (load by module path, check declared features and markets, isolation, per-call budget,
  `BASKET_LOADED`), `select.py` (ATM/ITM100/ITM200/DTE rule from an instrument-master fixture), and one test-only
  plugin `TEST-CROSS` (a moving-average cross used only to exercise code paths; stage `shadow`, never in a real basket).
- Acceptance: a raising plugin is disabled for the session and others keep emitting; an over-budget plugin is disabled;
  a plugin for `FX_SPOT` refuses to load into an India basket; missing basket file means zero signals and a health
  alert; the strike selector matches hand-computed strikes on DTE 0/1/2+ fixtures; truncation invariance on signals.
- Depends on: V2-01, V2-05 (the `FeatureView` interface only; can start from a stub).

**V2-07 Boss v2** (`packages/boss/src/boss/selector.py`, ~400 lines)
- Basket gate, holds from `config/v2/engine.yaml` (founder, event day, feed status, recon, Round 8 global skips),
  conflicts, VOLSIZE/CAPLOTS sizing, `DECISION` output, regime/intermarket shadow via `desk_ml.regime` (log only).
- Acceptance: a table test per hold reason; opposite-side signals give `HOLD CONFLICT`; sizing matches the Round 8
  §3.0 formula on fixtures and skips below 2 lots; `BOSS_SHADOW` is published and the decision is unchanged with
  `regime.mode: shadow`; no import of `desk_ml.paper_scalp` (import-linter test).
- Depends on: V2-06.

### Track B: execution and state (after V2-01/02; parallel with Track A)

**V2-08 Order router, fill models, broker wraps** (`packages/oms/router.py`, `packages/brokers/fills.py`, ~450 lines)
- Deterministic ids, `risk.check_entry(now=clock.now())`, order row `NEW` before submit, `needs_lookup` adopt path,
  protective stop placement; `clock=` injection into `BrokerAdapter`/`PaperBroker`; `DepthFill`, `HalfSpreadFill`
  (FC-MEAS table in `config/v2/markets/india.yaml`), `LtpSlippageFill`.
- Acceptance: the same decision routed twice yields one order; a risk veto yields `ENTRY_VETOED` and no broker call;
  decision age is checked with the engine clock in replay (no wall-clock reads: a test freezes wall time far in the
  future); `DepthFill` buys at the ask of the first quote after latency; fallback order and `fill_model` recorded;
  protective stop exists after every entry fill; `DhanBroker` is never constructed in tests (guard test).
- Depends on: V2-01, V2-02.

**V2-09 Position manager and exits** (`packages/oms/positions.py`, `exits.py`, ~450 lines)
- Exit order of section 2.9: founder, stop, EOD flat on `CLOCK`, time stop, target and partials, trailing (modifies the
  protective stop), strategy exit requests; fail-safe close on a mark-to-market exception.
- Acceptance: one table test per exit kind with exact exit time and price; EOD flat fires with zero ticks after 15:00;
  a partial then a trail step moves the protective stop; exits are allowed under the kill switch; a raising mark closes
  at the last good quote and blocks entries; invariant "no position after `flat_by_ist`" holds on all fixtures.
- Depends on: V2-08.

**V2-10 Ledger v2 and crash recovery** (`packages/ledger/migrations`, `packages/runtime/recovery.py`, ~500 lines)
- Migration runner and `002_v2_core.sql` (section 3.3), `LedgerStore` protocol, transaction + checkpoint + outbox,
  `positions_v2`, the restart sequence of section 3.5 (store check, book load, reconcile, rehydrate, resume), paper
  broker rebuilt from the ledger; risk checks `FEED_STALE` and `STRATEGY_DAILY_LOSS`.
- Acceptance: `kill -9` fault tests at each point in section 6.2 (subprocess engine, fixture tape) end with no double
  order and a clean reconciliation; restart after a planted broker-side extra position blocks entries with
  `RECON_MISMATCH` and allows exits; the engine refuses a newer schema; restart to READY on a full fixture day < 60 s;
  existing `packages/ledger` tests pass.
- Depends on: V2-04, V2-08.

**V2-11 Founder controls v2** (`packages/control`, gateway routes, engine handler, ~450 lines)
- Ports PR #18: append-only command log with idempotent `command_id`, confirm tokens, exit-command spool; commands of
  section 2.11 applied from their `available_ts`; `COMMAND_ACK`; out-of-band `python -m runtime flatten`.
- Acceptance: each command has a table test (applied, rejected with reason); replaying the command log gives identical
  trades; a resent `command_id` gets the stored ack; `KILL` flattens and blocks until `REARM`; with Redis stopped, the
  kill-switch file still vetoes entries and the CLI flatten closes paper positions; routes are localhost-only unless
  auth is on (V2-13).
- Depends on: V2-09, V2-10.

### Track C: live data, gateway, operations (after V2-01/02; parallel)

**V2-12 Market data service (live) and tape writer** (`packages/marketdata/dhan_ws.py`, `normalize.py`, `chain.py`,
`tape.py`, ~450 lines)
- Wraps `dhan_client.feed.MarketFeedCollector`; normalises packets; dynamic strike subscription around ATM; chain poller
  at the 3 s rate limit; `FEED_STATUS` DOWN/UP/STALE; `TapeWriter`; `--mode replay` that plays a tape into Redis.
- Acceptance: against a local fake websocket server (fixture frames): normalised ticks and bars match the fixture;
  disconnect gives DOWN then UP with resubscribe; silence beyond `stale_after_s` gives STALE; the tape written equals
  the envelopes published; refuses `live-data` mode without credentials; no credential appears in logs (log capture
  test). Live Dhan runs only on the user's box, never in CI.
- Depends on: V2-01, V2-02, V2-03.

**V2-13 Gateway v2 websocket and UI rewire** (`apps/api`, `apps/web`, ~450 lines)
- `GET /v2/snapshot`, `WS /v2/ws` (subscribe, snapshot then deltas with `seq`, resync), role-scoped channels (founder
  only for now), decision trace from correlation ids; web switches Desk/Founder to the v2 feed behind a flag.
- Acceptance: a websocket client test gets a snapshot then ordered deltas and resyncs after a planted gap; a customer
  role token cannot subscribe to founder channels; existing read-only routes still pass their tests; the Playwright
  layout check from PR #15 passes on the v2 fixture feed.
- Depends on: V2-02 (V2-11 for control routes).

**V2-14 Health, metrics and alerts v2** (`packages/health`, ~350 lines)
- Engine heartbeat, feed status, consumer lag, outbox backlog, checkpoint age, protective-stop check, backup age, token
  expiry; `prometheus-client` endpoint per service; alert rules of section 5.4 with dedupe and recovery.
- Acceptance: each alert fires within its threshold on a simulated failure and clears on recovery; no duplicate
  Telegram messages across a monitor restart; the metrics endpoint exposes every budget metric; existing health tests
  pass.
- Depends on: V2-02.

**V2-15 Docker compose, deploy scripts, CI** (`deploy/`, `.github/workflows/`, ~450 lines)
- Dockerfile (non-root, read-only root fs), `compose.yaml` + `compose.vps.yaml`, Caddyfile, systemd unit,
  `deploy.sh` (market-hours guard, backup, migrate, health wait, auto-rollback), `backup.sh`/`restore.sh` (restic),
  CI jobs of section 5.3 (salvaging PR #16), a short V2 section in `docs/13_FOUNDER_GUIDE.md`.
- Acceptance: `docker compose up` (replay profile) reaches `ENGINE_STATUS READY` with no credentials; `deploy.sh`
  refuses at 10:00 IST (faked clock) and rolls back when READY never arrives; restore from a backup reproduces the
  day's output hash; CI runs green on the branch; secret scan passes.
- Depends on: V2-04 (image needs an entry point); can start in parallel with a stub engine.

### Track D: gate, benchmark, research plumbing (parallel after their dependency)

**V2-16 Merge gate harness and live-like dry run** (`tests/gate/`, `scripts/gate/`, ~450 lines)
- Invariant checker (section 6.2), fault matrix runner, perf budget runner, compose dry run (1x hour, 10x day) that
  compares Redis-path decisions with in-process replay field by field.
- Acceptance: the invariant checker catches each planted violation (self-test per invariant); the dry run on the fixture
  day reports zero diffs; perf report within budgets on the CI runner; wired as required CI checks.
- Depends on: V2-10, V2-12, V2-15.

**V2-17 Frozen legacy benchmark** (`packages/runtime/bench_legacy.py`, `config/legacy_frozen.sha256`, ~250 lines)
- sha256 manifest and the `frozen-legacy` CI check; `python -m runtime bench-legacy --day` runs the frozen
  `replay_paper_scalp` on a recorder tape and writes trades for the warehouse.
- Acceptance: editing any frozen file fails CI; the benchmark on the committed synthetic session reproduces the
  existing parity fixture's trades; it never writes into the checkout's `data/` (test).
- Depends on: none (can start now).

**V2-18 Warehouse ETL to DuckDB and pre-market publish** (`packages/warehouse`, `packages/premarket`, ~450 lines)
- Retarget PR #19's ETL: ledger, events, tapes, recorder, benchmark and forward-evaluator outputs into Parquet
  partitions with DuckDB views (`duckdb` dependency added here); pre-market publishes `PRE_MARKET_SUMMARY`, event-day
  holds and HAR inputs before 09:00.
- Acceptance: ETL is idempotent (a second run changes nothing) and incremental; row counts equal the sources; the
  attribution query (signal → decision → order → trade) returns the full chain for fixture trades; pre-market output
  has `available_ts` before 09:15 and uses no data from the session day.
- Depends on: V2-10 (ledger schema); PR #19 merged or its code carried over.

**V2-19 LLM advisor service** (`packages/runtime/services.py` wiring over `desk_ml/llm_analyst`, ~250 lines)
- Consumes `boss:decisions`, publishes `ADVICE`; budget and provider config reused; `RecordedProvider` in replay.
- Acceptance: the engine's decisions and timings are identical with the advisor on, off, or hung (fault test); no
  provider call in replay or CI (socket guard); secrets are scrubbed from the stored context (existing tests reused).
- Depends on: V2-02, V2-07.

**V2-20 Forward-shadow evaluator and Round 8 shadow plugins** (`packages/strategies/plugins/`, `scripts/forward_eval.py`, ~500 lines, may split in two)
- E1 COIL-SIDE, E2 P5-HV and E3 HV-GATE as `stage: shadow` plugins loading the lab's frozen coefficients by hash;
  nightly evaluator prices hypothetical trades with depth fills and FC-MEAS, and tracks FWD-BAR checkpoints
  (n = 30 / 60 / 120). E4 stays out until the founder decides on writer-side trades.
- Acceptance: a plugin refuses to load if the params hash differs from the preregistered one; truncation invariance on
  every plugin; the evaluator reproduces hand-computed P&L on a synthetic day; FWD-BAR state machine tests (KILL at
  n = 30 gross ≤ 0, and so on). No plugin leaves `shadow` in this ticket.
- Depends on: V2-06, V2-18; the lab's frozen hashes (Round 8 §6 step 1).

### Parallelism at a glance

```
V2-01 ─▶ V2-02 ─┬─▶ A: V2-03 ─▶ V2-05 ─▶ V2-06 ─▶ V2-07 ─────────────▶ V2-19
                │        └──────▶ V2-04 ─┐
                ├─▶ B: V2-08 ─▶ V2-09 ───┴─▶ V2-10 ─▶ V2-11
                ├─▶ C: V2-12 (needs V2-03), V2-13, V2-14, V2-15
                └─▶ D: V2-16 (needs V2-10, V2-12, V2-15), V2-18 (needs V2-10) ─▶ V2-20
V2-17 can start today (no dependency).
```

With four agents: after V2-01 and V2-02, one agent per track. The critical path to Milestone 1 is
V2-01 → V2-02 → V2-08 → V2-09 → V2-10 → V2-11 → V2-16.

---

## 3. Milestones

### M1: paper-live on the new stack

**Scope:** V2-01 to V2-16 (V2-17 recommended alongside). The engine runs during market hours on real Dhan market data
(user box or VPS), with the paper broker, strategies at stage `shadow` or `paper` from a founder-approved basket,
founder controls, alarms, backups, and the frozen benchmark running nightly for comparison.

**Exit criteria (all required):**
1. Every merge gate check green on `main` (section 6.2 of the architecture).
2. **10 consecutive sessions** on the new stack with: zero duplicate orders; zero unresolved reconciliation
   mismatches at EOD; every open position had a protective stop; flat by 15:15; no entry under a hold.
3. **Nightly determinism:** replaying each session's tape through the engine reproduces that session's decisions,
   orders and fills exactly.
4. **Restart drill daily** in at least 5 of those sessions: `kill -9` the engine mid-session; READY in < 60 s; no
   duplicates; clean reconciliation.
5. Alerts proven live: feed drop, engine death and Redis restart each raised and cleared on the founder page and
   Telegram at least once.
6. Backup restore drill passed once.
7. The old paper loop (`paper-scalp --loop`) is switched off for trading and runs only as the nightly benchmark.

M1 does **not** mean a strategy is profitable, and it does not enable live orders.

### M2: customer-ready

**Scope:** M1 plus these tickets (sized the same way, specified after M1):
- **V2-21** Postgres `LedgerStore` + export/cutover tool + dual-engine CI (section 3.2).
- **V2-22** Accounts, per-account isolation, and the signal/exec split (sections 2.15, 5.6), with isolation tests.
- **V2-23** Gateway auth (JWT, founder 2FA), role-scoped channels, rate limits, the customer `signals:public` channel
  with customer-safe copy (`CUSTOMER_TALK.md`).
- **V2-24** Secret store (SOPS + age or Vault) and encrypted per-customer broker credentials.
- **V2-25** Dhan shadow-mode order test harness (submit far off-market and cancel at once; PR-002's original
  acceptance test). Runs only with the founder's explicit approval and credentials on the founder's machine.

**Exit criteria:**
1. M1 criteria hold for 20 more sessions on Postgres.
2. Isolation tests prove account A cannot read, affect or be sized by account B.
3. Auth, rate limits, TLS and backups verified; an external review of the public surface (at least a scripted OWASP
   baseline scan) passes.
4. **Founder and legal sign-off** on SEBI obligations, customer terms and risk disclosures (`docs/COMPLIANCE.md`).
5. At least one strategy has passed Round 8 FWD-BAR **and** 09's five-pass before it is shown to customers as more
   than an educational or shadow signal. Without that, customer-ready means the platform is ready, not the product.
6. Live orders remain off until the founder turns on `limited_live` through the existing three-part gate.

---

## 4. Handoff block

- **Accepted:** the re-map in section 1; 20 tickets within the 200-500 line rule; M1 and M2 criteria that test
  invariants and operations, not P&L.
- **Rejected:** old-engine bug fixes (PR-010), tuning steps (PR-022, PR-023), RAG (PR-030) and crypto (PR-032) as
  build work; byte-identical parity as a gate.
- **UNKNOWN / DATA_INSUFFICIENT:** the registry/basket module's final API (V2-06 codes to the contract and a YAML
  fallback); the lab's frozen hashes for E1-E3 (blocks V2-20 only); depth availability per strike (V2-08 falls back to
  FC-MEAS); Dhan token refresh for unattended runs (V2-12/V2-15 VERIFY).
- **Gap addressed:** `docs/01_CURRENT_STATE_AND_GAPS.md` §5 (backtest/replay: one code path, no look-ahead), §6 (role
  separation without the monolith), §7 (tech stack and deployment), §3 (broker adapter restart safety).

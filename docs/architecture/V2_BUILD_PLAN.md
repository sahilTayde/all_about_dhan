# V2 build plan

**Status:** PLAN (docs only). Paper only. No broker order calls, no credentials, nothing secret in the repo.
**Architecture:** [`V2_PRODUCTION_ARCHITECTURE.md`](V2_PRODUCTION_ARCHITECTURE.md) (section numbers below point there).
**Replaces for new work:** the PR order in [`docs/04_MIGRATION_PLAN.md`](../04_MIGRATION_PLAN.md). That file stays as
history and as the source of the original acceptance tests and budgets.

---

## 0. Now / Why / Next (plain English)

- **Now.** 13 of the 32 old plan steps are merged (PR #21 covers both PR-012 and PR-024). The safety parts (recorder,
  broker adapter, risk engine, health, ledger, event bus, LLM analyst, regime) are good and we keep them. The boss,
  desk and analyst extraction are wrappers around the old engine, so they get rebuilt.
- **Why.** The founder froze the old engine. Many later steps were "fix or tune the old engine". Those are dropped. The
  rest become tickets on the new stack. Three founder addenda (2026-09-27) add: every bug fixed in the old engine
  becomes a must-pass regression test (REG-01 to REG-13, section 3); research round 9 needs bid/ask depth data
  that no dataset we have contains; and entry location (not chasing the top of an impulse candle) is checked by both
  the boss and the desk (V2-05b, V2-08b), log-only until research round 10.
- **Next.** Start **recording depth now** (V2-D1, V2-D2), because it cannot be backfilled and 2-5 minute stops cannot
  be tested without it. In parallel, build 24 more tickets of 200-500 lines each, in four tracks after two shared
  foundation tickets. Milestone 1 is **paper-live on the new stack** (real Dhan data, paper broker, safe restarts,
  founder controls, alarms, all regression tests green). Milestone 2 is **customer-ready** (Postgres, accounts, auth,
  rate limits, backups, compliance sign-off). Neither milestone says a strategy makes money; that is decided by the
  Round 8 forward bar and 09's five-pass.

---

## 1. The 32 steps re-mapped

Legend: **DONE** = merged and kept as-is. **REUSE** = merged, kept, wrapped or extended by a V2 ticket. **REBUILD** =
the requirement stays but the code is new on the V2 stack. **DROP** = not built (old-engine fix or tuning, or not
needed). **LATER** = after customer-ready.

| Step | Old title | Status in repo | V2 verdict | V2 ticket / note |
|---|---|---|---|---|
| PR-001 | Daily data recorder | merged #8 | **DONE** | Keeps running as backup capture; V2-03 reads its files. It has no bid/ask depth and polls the chain every 180 s, so round 9 depth recording is new work (V2-D1, V2-D2), not a patch to it |
| PR-002 | Broker adapter + order state machine | merged #10 | **REUSE** | V2-08 adds clock injection, fill models, paper state rehydrate, protective stop |
| PR-003 | Pre-trade risk engine | merged #10 | **REUSE** | V2-08 (clock, account scope, last-good config), V2-10 (`FEED_STALE`, strategy daily cap) |
| PR-004 | Health alarms | merged #10 | **REUSE** | V2-14 adds engine/feed checks, metrics, alert rules |
| PR-005 | Ledger + charges | merged #10 | **REUSE** | V2-10 migrations, `account_id`, checkpoint, outbox; V2-08 moves the exchange rate to the founder's value |
| PR-006 | Event bus | merged #12 | **REUSE** | V2-02 envelope v2, stream per topic, consumer groups, outbox publisher, bad-entry fix |
| PR-007 | Extract boss | merged #12 (wraps `paper_scalp`) | **REBUILD** | V2-07 `boss/selector.py`; old boss frozen |
| PR-008 | Extract desk | merged #12/#14 (wraps `paper_scalp`) | **REBUILD** | V2-08 router + V2-09 position manager; old desk frozen |
| PR-009 | Extract analyst registry | merged #12/#13 | **REUSE** (interface) | `Analyst`/`Vote`/`AnalystRoom` kept for advisory filters; 22 legacy analysts frozen (V2-17) |
| PR-010 | Fix known old-engine bugs | not done | **DROP** | Old engine frozen. Every legacy bug becomes a regression test on V2 (section 3) |
| PR-011 | Proven fixes (cooldown, DTE strikes, clock) | cooldown in risk engine | **REBUILD** | Cooldown: DONE in risk engine. DTE strike rule: V2-06b strike router. Time windows: config holds in V2-07 |
| PR-012 | Regime-conditional weighting | merged #21 (shadow) | **REUSE** | Labeller as a feature (V2-05); weights in boss shadow (V2-07) |
| PR-013 | Nightly warehouse ETL | draft #19 | **REUSE** (retarget) | V2-18: keep #19's structure, sink to DuckDB + Parquet |
| PR-014 | Founder emergency controls | draft #18 (old engine hooks) | **REBUILD** | V2-11 ports #18's command log design and semantics |
| PR-015 | Desk UI polish | merged #15 | **REUSE** | V2-13 rewires the UI to `/v2/ws` |
| PR-016 | LLM advisory mode | merged #17 | **REUSE** | V2-19 runs it as the `llm-advisor` service |
| PR-017 | Pre-market analysis | draft #19 | **REUSE** | V2-18 publishes `PRE_MARKET_SUMMARY`, holds and basket inputs |
| PR-018 | Model and stage attribution | not done | **REBUILD** | Falls out of correlation ids; a V2-18 warehouse query |
| PR-019 | Decision visual | partial in #15 (`/paper/trace`) | **REUSE** | V2-13 serves the correlation chain to the existing trace view |
| PR-020 | Post-market improvement loop | not done | **LATER** | After customer-ready; human merge gate stays |
| PR-021 | Backtest integration | draft #19 (expected-results gate) | **REBUILD** | V2-16 new merge gate + V2-20a forward-test harness |
| PR-022 | Lab round 2 filters | not done | **DROP** | Round 8 closed these families. New ideas enter as preregistered shadow specs (V2-20a) |
| PR-023 | Exits v2 (trail tuning) | not done | **DROP** (tuning) | Exit mechanics, including first-class time stops, are in V2-09; no tuning (Round 8 §4.3) |
| PR-024 | Intermarket as daily regime | merged #21 (shadow) | **REUSE** | Boss shadow overlay (V2-07) |
| PR-025 | Supply/demand zones | not done | **DROP** | Research only; a shadow spec if ever preregistered |
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
run in parallel. `REG-nn` ids refer to section 3; each ticket ships the regression tests it owns.

### Data first (start now; research round 9; new system only)

**V2-D1 Dhan FULL-packet depth decoder and raw frame capture** (`packages/dhan-client/decode.py`, ~300 lines)
- Real decoder for the FULL packet (LTP, LTQ, LTT, ATP, volume, total buy/sell qty, OI, OHLC and the 5-level
  bid/ask depth) from the Dhan live-market-feed layout, replacing today's placeholder that reads only LTP. Keeps
  `raw_payload`. A `decoder_verified` flag stays `false` until one frame captured on the founder's box is checked.
- Acceptance: golden frames built from the documented layout decode to the expected fields; truncated frames raise
  `DecodeError` and never crash the collector; QUOTE and INDEX decoding unchanged (existing tests pass); no network
  in tests.
- Depends on: none.

**V2-D2 Depth, quote-snapshot and OI-cadence recorder** (`packages/marketdata/{depth,quotes,oi_cadence,tape}.py`,
`python -m runtime marketdata --record-only`, ~450 lines)
- Traded-strike set per basket underlying: ATM, ITM100, ITM200 on CE and PE (nearest weekly), plus index and future;
  re-centred on spot moves, old strikes kept 10 minutes, open positions always kept. FULL-mode subscription;
  `DEPTH_QUOTE` at ≤ 1 s (throttled to 250 ms, 1 s heartbeat repeat); `QUOTE_SNAPSHOT` with bid/ask every 5 s;
  `OI_CADENCE` every minute; `TapeWriter` to `data/tape/v2/YYYY-MM-DD/`, raw frames base64 until V2-D1 is verified.
  Runs standalone, without the engine.
- Acceptance: against a fake websocket server with fixture frames, the tape has a depth row per instrument at least
  once per second and a quote snapshot every 5 s ± 0.5 s; re-centring subscribes the new strikes and keeps the old
  ones for 10 minutes; `stale: true` when depth is older than 5 s; OI cadence stats match hand counts on the fixture;
  a bad frame is logged to `ingest_errors` and recording continues (REG-06); refuses to start without credentials in
  live mode; no credential in logs.
- Depends on: V2-01 (envelope and schemas), V2-D1.
- **Operate from the day it merges** on the founder's box, before M1: depth data cannot be backfilled.

### Foundation (sequential, both first)

**V2-01 Contracts: envelope v2, schemas, clock, ids, test-data guard** (`packages/contracts`, root `conftest.py`, ~450 lines)
- `envelope.py` (compatible with `events.schema.Event`), payload dataclasses and JSON Schemas for every type in
  section 4.4 (including `DEPTH_QUOTE`, `QUOTE_SNAPSHOT`, `OI_CADENCE`, `StrikeChoice`, `TimeStop`),
  `SimClock`/`LiveClock`, `ids.py` (order, event, signal ids), `instruments.py` (instrument id parse and format,
  `MarketAdapter` protocol, India adapter with session hours). A repo-wide pytest guard that makes `data/` and
  `config/` read-only during tests (REG-11).
- Acceptance: round-trip every fixture payload through dataclass → JSON → schema validation; an old `Event` JSON still
  loads; `SimClock.advance_to` raises on going backwards; `order_id` is 27 chars `[a-z0-9]` and stable across
  processes; property test: distinct `(account, signal, leg)` never collide in 1e6 samples; `REG-11a` a test that
  writes into `data/` fails; `REG-11b` `git status` is clean after the full suite.
- Depends on: none.

**V2-02 Event bus v2** (`packages/events`, ~350 lines)
- `EventType` additions; `RedisStreamsBus` with one stream per topic and consumer groups (`XREADGROUP`, `XACK` after
  the handler's commit, `XPENDING`/`XCLAIM` on start); `outbox.py` publisher (drain `outbox` rows, mark published);
  per-entry guarded parsing (today `poll` sets `last_id` before `Event.from_json`, so one bad entry raises and skips
  the good entries before it); `MemoryBus` unchanged in behaviour.
- Acceptance: existing `packages/events` tests pass unchanged; a consumer killed before `XACK` gets the entry again
  and dedupes by `event_id`; outbox publishes each row exactly once to consumers after two publisher crashes; publish
  p99 < 5 ms (existing budget); Redis tests skip cleanly without a server; `REG-06c` a bad entry in the middle of a
  batch is recorded and skipped, and the good entries around it are all dispatched.
- Depends on: V2-01.

### Track A: market in, decisions out (after V2-01/02)

**V2-03 Event sources, bar builder, no-look-ahead harness** (`packages/marketdata`, ~450 lines)
- `sources.py` (`ListSource`, `TapeSource`, `RecorderTapeSource` over `data/recon/*/YYYYMMDD.jsonl`) with per-line
  guarded parsing, `bars.py` (`BarBuilder` with finalize delay, gap flag, late-tick counter; 3m/5m from closed 1m
  bars stamped at bucket close), `clock.py` (`CLOCK` synthesis in sources), and the test harness
  `tests/lookahead.py` (random-cut causality, future poisoning) reused by later tickets.
- Acceptance: property test: no bar with `available_ts < end`; bars never revised; a recorder fixture day produces the
  expected bar count; sources emit non-decreasing `available_ts`; a synthetic tape with a 30 s hole yields
  `gap: true`; harness self-test catches a planted look-ahead; `REG-01a` 3m bars are available at bucket close, never
  at the last print; `REG-06a`/`REG-08a` truncated, non-JSON and wrong-schema lines mid-file are skipped and logged,
  and lines before and after still load.
- Depends on: V2-01.

**V2-04 Engine kernel, config loader, job deadlines** (`packages/runtime/kernel.py`, `wiring.py`, `jobs.py`,
`packages/contracts/config.py`, ~450 lines)
- `Engine(source, clock, bus, handlers, store, mode)`, one transaction per input, checkpoint, rehydrate mode (router
  no-op plus intent comparison), `RunSummary` with an output hash; `load_with_last_good` for every engine YAML;
  `run_with_deadline(fn, timeout_s)` for every one-shot job.
- Acceptance: the same tape twice gives the same output hash; rehydrate over a finished run reports zero mismatches; a
  planted non-deterministic handler (reads `random()`) is caught by rehydrate; kernel raises on time going backwards;
  `ListSource` 100k envelopes in < 5 s; `REG-07a/b/c` bad YAML mid-session keeps the bus running with last-good
  values and one alert, a valid file clears it, and no valid config at start means exits-only; `REG-10a` an
  overrunning job is killed, exits non-zero, alerts, and leaves no partial output.
- Depends on: V2-01, V2-02. (Uses an in-memory `LedgerStore` stub until V2-10.)

**V2-05 Feature engine** (`packages/indicators`, ~450 lines)
- Incremental EMA, ATR, VWAP/TWAP, realised vol, daily HAR forecast from pre-market inputs, OI change lagged strictly
  before the decision minute; `FeatureView(strict)` with a future-lookup counter; adapters for `RegimeLabeller` and
  `analysts/shadow.py` helpers.
- Acceptance: each indicator equals a batch reference implementation on fixtures (within 1e-9); the
  OI-jump-inside-minute fixture is invisible to the lagged feature; regime labels equal `label_bars()` on the
  synthetic session; `REG-01b` random-cut causality on all features; `REG-01c` future poisoning; `REG-01d` strict view
  raises on a planted future value and the lookup counter is 0 on every fixture; `REG-01e` levels (S/R, prior
  high/low) use prior-day data only; `REG-01f` a saved state file dated after the session is refused.
- Depends on: V2-01, V2-03.

**V2-05b Entry-location features** (`packages/indicators/location.py`, ~350 lines)
- `EntryLocation` for every signal (section 2.18): signal candle and body in ATR; unfilled FVGs (3-bar rule, fill rule,
  max age); candle 50%; VWAP from futures volume with a basis shift, else TWAP tagged `twap`; EMA20; volume POC from
  futures volume only (absent otherwise); signed `distance_atr` per zone; `nearest` and `entry_distance_atr`.
- Acceptance: hand-built fixtures for a bullish and a bearish FVG (formed, partly filled, fully filled, expired);
  candle 50% and EMA20 match references; VWAP uses futures volume when present and falls back to TWAP with the tag
  when not; POC is absent without futures volume and matches a hand-computed profile with it; distance signs are
  correct for CE and PE; random-cut causality and strict view on every entry-location field (REG-01); an FVG formed
  by the still-open bar is never reported.
- Depends on: V2-05.

**V2-06 Strategy runtime and registry client** (`packages/strategies`, ~400 lines)
- `api.py` (section 2.5, including `ExitPlan.time_stops` and `Signal.strike_choice`), `registry.py` (contract for the
  separately built module + YAML fallback + a read-only adapter for the basket track's `basket_india.json` /
  `basket_forex.json`, section 4.2 K6; no basket = no trades), `runtime.py` (load by module path, check declared
  features and markets, isolation, per-call budget, `BASKET_LOADED`), `params_hash` over all params **including the
  exit plan, time stops and strike-router rules**, and one test-only plugin `TEST-CROSS` (moving-average cross used
  only to exercise code paths; stage `shadow`, never in a real basket).
- Acceptance: a raising plugin is disabled for the session and others keep emitting; an over-budget plugin is disabled;
  a plugin for `FX_SPOT` refuses to load into an India basket; missing basket file means zero signals and a health
  alert; random-cut causality on signals; `REG-13a` changing any exit field changes `params_hash` and `config_hash`.
- Depends on: V2-01, V2-05 (the `FeatureView` interface only; can start from a stub).

**V2-06b Strike router with shadow-priced alternatives** (`packages/strategies/strikes.py`,
`config/v2/strategies/strike_router.yaml`, ~400 lines)
- `StrikeRouter.route(signal, view, quotes)` → `StrikeChoice(chosen, reason, rule_version, alternatives)`. Rules as
  data: no ATM on expiry day, the 09:15-10:00 decay window, DTE rule, lowest break-even move for the planned hold
  (measured decay and spreads), `STRATEGY_FIXED`. Prices ATM, ITM100 and ITM200 on the signal side at the same
  `decision_ts` from `QUOTE_SNAPSHOT`/depth (`available_ts ≤ decision_ts` only). Lot size and strikes from the
  instrument master.
- Acceptance: the chosen strike and reason match a table of hand-computed cases (DTE 0/1/2+, open window, expiry day,
  pinned); all three alternatives are present with quote age, and marked `no_quote` when missing; the router never
  reads a quote from after `decision_ts` (random-cut test); changing router rules changes `rule_version` (REG-13);
  strikes match hand-computed strikes on instrument-master fixtures.
- Depends on: V2-06 (can start in parallel against the dataclasses from V2-01).

**V2-07 Boss v2** (`packages/boss/src/boss/selector.py`, ~400 lines)
- Basket gate, holds from `config/v2/engine.yaml` (founder, event day, feed status, recon, Round 8 global skips),
  conflicts, VOLSIZE/CAPLOTS sizing, `DECISION` output with the signal's `strike_choice`, regime/intermarket shadow via
  `desk_ml.regime` (log only).
- Acceptance: a table test per hold reason; opposite-side signals give `HOLD CONFLICT`; sizing matches the Round 8
  §3.0 formula on fixtures and skips below 2 lots; `BOSS_SHADOW` is published and the decision is unchanged with
  `regime.mode: shadow`; no import of `desk_ml.paper_scalp` (import-linter test).
- Depends on: V2-06, V2-06b.

### Track B: execution and state (after V2-01/02; parallel with Track A)

**V2-08 Order router, fill models, broker and risk wraps** (`packages/oms/router.py`, `packages/brokers/fills.py`,
`packages/risk-engine`, ~500 lines)
- Deterministic ids, `risk.check_entry(now=clock.now())`, order row `NEW` before submit, `needs_lookup` adopt path,
  protective stop placement; `clock=` injection into `BrokerAdapter`/`PaperBroker`; `DepthFill`, `HalfSpreadFill`
  (FC-MEAS table in `config/v2/markets/india.yaml`), `LtpSlippageFill`; risk engine keeps last-good limits so exits
  and flatten never fail on a bad YAML; `config/charges.yaml` exchange rate to `0.000355299` (VERIFY stays).
- Acceptance: the same decision routed twice yields one order; a risk veto yields `ENTRY_VETOED` and no broker call;
  decision age is checked with the engine clock in replay (a test freezes wall time far in the future); `DepthFill`
  buys at the ask of the first quote after latency; fallback order and `fill_model` recorded; `DhanBroker` is never
  constructed in tests (guard test); `REG-02a` protective stop exists after every entry fill; `REG-02e` bad risk YAML
  still allows the exit; `REG-05a/b/c` cap tables, missing-key validation, kill switch; `REG-12a-d` golden contract
  note per component, a `charges` row for every fill, lot size 65 from the instrument master fixture, slippage and
  fill model recorded.
- Depends on: V2-01, V2-02.

**V2-08b Order planner, boss stretch veto, trade-through limit fills** (`packages/oms/planner.py`,
`packages/boss/src/boss/selector.py`, `packages/brokers/fills.py`, `config/v2/entry_location.yaml`, ~500 lines)
- Planner actions CHASE / LIMIT (zone-priced option limit, `TIMEOUT_UNFILLED` cancel, invalidation cancel) / WAIT (one
  consolidation candle, trigger on its break, `WAIT_EXPIRED`); boss veto `ENTRY_STRETCHED` above `max_stretch_atr`
  or `candle_max_atr`; `log_only` (default) vs `enforce`; risk re-checked at send time; one entry order per signal;
  pending plans in `entry_plans` and rebuilt on restart; exit plan re-anchored at the fill; `ENTRY_PLAN` and
  `ENTRY_PLAN_RESULT` events with the 5-minute give-back; trade-through fill rule for resting limits.
- Acceptance:
  - `log_only`: with stretched fixtures the executed action is CHASE, `shadow_action` is LIMIT or WAIT, the boss logs
    `would_veto: true` and does not veto, and trades are identical to a run with the feature off.
  - `enforce` (test thresholds): not stretched gives CHASE; stretched with a zone gives LIMIT at the zone-derived price;
    no zone or `prefer: WAIT` gives WAIT; above `max_stretch_atr` gives `HOLD ENTRY_STRETCHED` with the numbers logged
    and no order.
  - LIMIT unfilled at `limit_timeout_s` is cancelled `TIMEOUT_UNFILLED`; the underlying stop trading first cancels it;
    WAIT fires on the consolidation bar's break and expires after `wait_max_bars`.
  - Trade-through: a quote whose ask equals the limit does not fill; an ask one tick below, or a trade printed below,
    fills at the limit; a marketable limit fills at the ask.
  - Risk vetoes a LIMIT that fills after the entry cutoff or during a cooldown that started while it rested.
  - `kill -9` with a pending LIMIT: after restart the plan and its order are recovered and never duplicated
    (REG-04); the protective stop is placed on fill (REG-02).
  - `enforce` with a `null` threshold is refused, the last-good log-only config stays, and `CONFIG_INVALID` is raised
    (REG-07); changing any threshold changes `config_hash` (REG-13).
  - Planner + features < 5 ms p99 per decision.
- Depends on: V2-05b, V2-07, V2-08.

**V2-09 Position manager, first-class time stops, exits** (`packages/oms/positions.py`, `exits.py`, ~450 lines)
- Exit order of section 2.9: founder, stop, EOD flat on `CLOCK`, time stops (`TimeStop(after_s, when,
  unless_profit_pts)`, chosen at the fill and stored on the position, checked on the 1 s `CLOCK`), target and
  partials, trailing (modifies the protective stop), strategy exit requests; exits built only from the position record;
  fail-safe close on a mark-to-market exception with the PR #14 halt semantics.
- Acceptance: one table test per exit kind with exact exit time and price; a 180 s time stop for an entry at 09:20 and
  for one on an expiry day fires within 1 s of its deadline with zero ticks, priced at the first depth quote after it;
  a non-matching window applies the default time stop; EOD flat fires with zero ticks after 15:00; a partial then a
  trail step moves the protective stop; exits are allowed under the kill switch; invariant "no position after
  `flat_by_ist`" holds on all fixtures; `REG-02a` the stop invariant holds after every envelope; `REG-03a/b/c` spot
  moves 3 strikes and every forced close still exits the held instrument and qty; `REG-05d` a raising mark closes at
  the last good quote and blocks entries.
- Depends on: V2-08.

**V2-10 Ledger v2 and crash recovery** (`packages/ledger/migrations`, `packages/runtime/recovery.py`, ~500 lines)
- Migration runner and `002_v2_core.sql` (section 3.3, including `session_halts` and `ingest_errors`),
  `LedgerStore` protocol, transaction + checkpoint + outbox, `positions_v2`, the restart sequence of section 3.5 (store
  check, book load, reconcile, rehydrate, resume, stop re-check), paper broker rebuilt from the ledger; risk checks
  `FEED_STALE` and `STRATEGY_DAILY_LOSS`.
- Acceptance: the engine refuses a newer schema; restart to READY on a full fixture day < 60 s; existing
  `packages/ledger` tests pass; `REG-02b` `kill -9` between fill and stop placement, then the stop is placed before
  any entry; `REG-04a` `kill -9` at each fault-matrix point loses no open position; `REG-04b` broker-only and
  ledger-only positions each give `RECON_MISMATCH`, block entries and allow exits; `REG-05e` an unreadable halt
  record blocks all entries, and forced closes re-book at saved time and price; `REG-06b` the first bad line of a
  file is written once to `ingest_errors` and survives restart.
- Depends on: V2-04, V2-08.

**V2-11 Founder controls v2** (`packages/control`, gateway routes, engine handler, ~450 lines)
- Ports PR #18: append-only command log with idempotent `command_id`, confirm tokens, exit-command spool; commands of
  section 2.11 applied from their `available_ts`; `COMMAND_ACK`; out-of-band `python -m runtime flatten`.
- Acceptance: each command has a table test (applied, rejected with reason); replaying the command log gives identical
  trades; a resent `command_id` gets the stored ack; `KILL` flattens and blocks until `REARM`; with Redis stopped, the
  kill-switch file still vetoes entries and the CLI flatten closes paper positions; routes are localhost-only unless
  auth is on (V2-13); `REG-06a` (PR #18 scenario 2e) a corrupt line mid-day in the command log never erases earlier
  trades, later valid exit commands still apply, entries block from the last good command.
- Depends on: V2-09, V2-10.

### Track C: live data, gateway, operations (after V2-01/02; parallel)

**V2-12 Market data service (live): ticks, bars, chain, feed status** (`packages/marketdata/dhan_ws.py`,
`normalize.py`, `chain.py`, ~400 lines)
- Wraps `dhan_client.feed.MarketFeedCollector`; normalises packets; publishes ticks and closed bars; reuses V2-D2's
  traded-strike subscription and tape writer; chain poller at the 3 s rate limit; `FEED_STATUS` DOWN/UP/STALE;
  `--mode replay` that plays a tape into Redis.
- Acceptance: against a local fake websocket server (fixture frames): normalised ticks and bars match the fixture;
  disconnect gives DOWN then UP with resubscribe; silence beyond `stale_after_s` gives STALE; refuses `live-data` mode
  without credentials; no credential appears in logs (log capture test); `REG-02c` a reconnect triggers the engine's
  stop re-check. Live Dhan runs only on the user's box, never in CI.
- Depends on: V2-01, V2-02, V2-03, V2-D2.

**V2-13 Gateway v2 websocket and UI rewire** (`apps/api`, `apps/web`, ~450 lines)
- `GET /v2/snapshot`, `WS /v2/ws` (subscribe, snapshot then deltas with `seq`, resync), role-scoped channels (founder
  only for now), decision trace from correlation ids including the strike choice and its alternatives; web switches
  Desk/Founder to the v2 feed behind a flag.
- Acceptance: a websocket client test gets a snapshot then ordered deltas and resyncs after a planted gap; a customer
  role token cannot subscribe to founder channels; existing read-only routes still pass their tests; the Playwright
  layout check from PR #15 passes on the v2 fixture feed; `REG-04c` the snapshot lists every ledger-open position.
- Depends on: V2-02 (V2-11 for control routes).

**V2-14 Health, metrics and alerts v2** (`packages/health`, ~350 lines)
- Engine heartbeat, feed status, depth coverage per traded strike, consumer lag, outbox backlog, checkpoint age,
  protective-stop check, restart breaker state, backup age, token expiry; `prometheus-client` endpoint per service;
  alert rules of section 5.4 with dedupe and recovery.
- Acceptance: each alert fires within its threshold on a simulated failure and clears on recovery; no duplicate
  Telegram messages across a monitor restart; the metrics endpoint exposes every budget metric; existing health tests
  pass; `REG-02d` a position without a protective stop raises CRITICAL; `REG-09a` (alarm half) an open breaker raises
  `RESTART_LOOP` once.
- Depends on: V2-02.

**V2-15 Docker compose, deploy scripts, CI, supervision** (`deploy/`, `.github/workflows/`, `runtime/services.py`,
~500 lines)
- Dockerfile (non-root, read-only root fs), `compose.yaml` + `compose.vps.yaml`, Caddyfile, systemd unit,
  `deploy.sh` (market-hours guard, backup, migrate, health wait, auto-rollback), `backup.sh`/`restore.sh` (restic),
  restart circuit breaker in every service entry point, `timeout` on every job unit, CI jobs of section 5.3 (salvaging
  PR #16) including `regression`, a short V2 section in `docs/13_FOUNDER_GUIDE.md`.
- Acceptance: `docker compose up` (replay profile) reaches `ENGINE_STATUS READY` with no credentials; `deploy.sh`
  refuses at 10:00 IST (faked clock) and rolls back when READY never arrives; restore from a backup reproduces the
  day's output hash; CI runs green on the branch; secret scan passes; `REG-09a/b` a crash-at-start service backs off,
  the breaker opens after 5 crashes in 10 minutes, and `reset-breaker` restores it; `REG-10` every job unit has a
  timeout.
- Depends on: V2-04 (image needs an entry point); can start in parallel with a stub engine.

### Track D: gate, benchmark, research plumbing (parallel after their dependency)

**V2-16 Merge gate harness and live-like dry run** (`tests/gate/`, `tests/regression/`, `scripts/gate/`, ~450 lines)
- Invariant checker (section 6.2), fault matrix runner, perf budget runner, compose dry run (1x hour, 10x day) that
  compares Redis-path decisions with in-process replay field by field; the `regression` CI job collecting every
  `REG-*` test (no skips, no xfail); a gate check that exit-param changes need a new strategy version.
- Acceptance: the invariant checker catches each planted violation (self-test per invariant); the dry run on the fixture
  day reports zero diffs; perf report within budgets on the CI runner; wired as required CI checks; `REG-10b` every job
  entry point is registered with a deadline; `REG-13c` a PR fixture that edits exit params without a version bump
  fails; a meta-test fails if any REG id in section 3 has no collected test; `TRACE-01` fails if any `C#` in
  `docs/founder/FOUNDER_COMMENTS_LOG.md` or any `REG-nn` lacks a row with a ticket and a test in section 4.1.
- Depends on: V2-10, V2-12, V2-15.

**V2-17 Frozen legacy benchmark** (`packages/runtime/bench_legacy.py`, `config/legacy_frozen.sha256`, ~250 lines)
- sha256 manifest and the `frozen-legacy` CI check; `python -m runtime bench-legacy --day` runs the frozen
  `replay_paper_scalp` on a recorder tape and writes trades for the warehouse.
- Acceptance: editing any frozen file fails CI; the benchmark on the committed synthetic session reproduces the
  existing parity fixture's trades; it never writes into the checkout's `data/` (REG-11 guard); it runs under a
  deadline (REG-10).
- Depends on: none (can start now).

**V2-18 Warehouse ETL to DuckDB and pre-market publish** (`packages/warehouse`, `packages/premarket`, ~450 lines)
- Retarget PR #19's ETL: ledger, events, tapes (including depth, quote snapshots and OI cadence), recorder, benchmark
  and forward-harness outputs into Parquet partitions with DuckDB views (`duckdb` dependency added here); the daily
  `entry_location_daily` review table (per action, zone and strategy: count, fill rate, give-back, stop-outs, net);
  pre-market publishes `PRE_MARKET_SUMMARY`, event-day holds and HAR inputs before 09:00.
- Acceptance: ETL is idempotent (a second run changes nothing) and incremental; row counts equal the sources; the
  attribution query (signal → decision → order → trade) returns the full chain for fixture trades; daily
  `oi_cadence` and spread-by-moneyness tables are built; pre-market output has `available_ts` before 09:15 and uses no
  data from the session day; `REG-08a/b` bad files and lines are skipped, counted and logged, and a rerun is
  idempotent.
- Depends on: V2-10 (ledger schema); PR #19 merged or its code carried over.

**V2-19 LLM advisor service** (`packages/runtime/services.py` wiring over `desk_ml/llm_analyst`, ~250 lines)
- Consumes `boss:decisions`, publishes `ADVICE`; budget and provider config reused; `RecordedProvider` in replay.
- Acceptance: the engine's decisions and timings are identical with the advisor on, off, or hung (fault test); no
  provider call in replay or CI (socket guard); secrets are scrubbed from the stored context (existing tests reused).
- Depends on: V2-02, V2-07.

**V2-20a Forward-test harness (generic; off by default)** (`packages/strategies/forward/`,
`python -m runtime forward-eval`, ~450 lines)
- Spec files `config/v2/forward/specs/<spec_id>.yaml`, `prereg.lock` (sha256 of canonical spec + plugin source +
  coefficients), nightly offline evaluation with the same kernel over `TapeSource`, depth fills with FC-MEAS as the
  second pricing, strike-router alternatives and entry-action alternatives (CHASE / LIMIT per zone / WAIT) as shadow
  legs, placebos, pass/kill bar state machine (default Round 8
  FWD-BAR), `forward_trades`/`forward_checkpoints`; `forward_eval.enabled: false` by default.
- Acceptance: disabled by default (the job exits 0 doing nothing); a spec whose hash differs from the lock is refused;
  the evaluator reproduces hand-computed P&L for the chosen leg and each alternative on a synthetic day; the bar state
  machine goes `RUNNING` → `KILLED` at n = 30 when gross ≤ 0, and to `PROMISING` / `PASS_TO_REVIEW` per the bars;
  sessions with depth coverage < 95% count as `DATA_INSUFFICIENT`; `REG-13b` a changed exit param is refused;
  runs under a deadline (REG-10).
- Depends on: V2-04, V2-06, V2-06b, V2-09 (exit mechanics); V2-D2 data for real sessions.

**V2-20b Round 8 shadow specs** (`packages/strategies/plugins/`, `config/v2/forward/specs/`, ~400 lines)
- E1 COIL-SIDE, E2 P5-HV and E3 HV-GATE as `stage: shadow` plugins loading the lab's frozen coefficients by hash, with
  their preregistered exit plans (including time stops) as spec files. E4 stays out until the founder decides on
  writer-side trades.
- Acceptance: each plugin refuses to load if its params hash differs from the preregistered one; random-cut causality
  on every plugin; each spec runs through V2-20a on the synthetic day; no plugin leaves `shadow`.
- Depends on: V2-20a, V2-18; the lab's frozen hashes (Round 8 §6 step 1).

### Parallelism at a glance

```
V2-D1 ─▶ V2-D2 (needs V2-01)  ── operate from merge; feeds V2-12, V2-20a
V2-01 ─▶ V2-02 ─┬─▶ A: V2-03 ─┬─▶ V2-04
                │             └─▶ V2-05 ─┬─▶ V2-06 ─▶ V2-06b ─▶ V2-07 ─▶ V2-19
                │                        └─▶ V2-05b
                ├─▶ B: V2-08 ─┬─▶ V2-09 ─▶ V2-10 (needs V2-04) ─▶ V2-11
                │             └─▶ V2-08b (needs V2-05b, V2-07)
                ├─▶ C: V2-12 (needs V2-03, V2-D2), V2-13, V2-14, V2-15
                └─▶ D: V2-16 (needs V2-10, V2-12, V2-15), V2-18 (needs V2-10),
                       V2-20a (needs V2-04, V2-06b, V2-09) ─▶ V2-20b (needs V2-18)
V2-17 can start today (no dependency).
```

With four agents: one on V2-D1 → V2-D2 while another does V2-01 → V2-02; then one agent per track. The critical path
to Milestone 1 is V2-01 → V2-02 → V2-08 → V2-09 → V2-10 → V2-11 → V2-16. The data path (V2-D1 → V2-D2) is short and
goes first so recording starts weeks before M1.

---

## 3. Legacy bug carry-over (must-pass tests)

Founder addendum (2026-09-27): every bug found and fixed in the legacy engine carries into V2 as a named regression
requirement with a test id, an owner service and the ticket that implements it. Full requirement text, legacy source
and test descriptions are in architecture section 6.5. The tests live in `tests/regression/test_reg_<nn>_*.py` and
run in the `regression` CI job; none may be skipped or marked xfail. All of them green is an M1 exit criterion.

"Merged coverage today" is checked against the code on `main`. **SATISFIED** = a merged component already enforces it
and V2 adds only the test. **PARTIAL** = a merged mechanism exists, with the named gap. **NEW** = new work.

| ID | Requirement (short) | Test ids | Owner service | Ticket(s) | Merged coverage today |
|---|---|---|---|---|---|
| REG-01 | Decisions see only closed bars; no series stamped at the last print before bucket close (legacy `resample_closes_3m` / `logit_side_series`; PR #11 and PR #21 leaks) | REG-01a-f (bucket-close stamp, random-cut causality, future poisoning, zero future lookups, prior-day levels, future state refused) | marketdata (bars); engine: indicators, strategies | V2-03, V2-05, V2-16 | PARTIAL: `RegimeLabeller` causal and PR #21's future-state refusal reused; rest new |
| REG-02 | Every open position has an enforced stop at all times, including after restart or reconnect (~₹193k stop hole, Phase 2 review) | REG-02a-e | engine: oms | V2-08, V2-09, V2-10, V2-12, V2-14 | PARTIAL: `PaperBroker` super-order stop legs, SL-M, trailing; risk allows exits under kill switch. Gaps: no invariant, paper resting orders lost on restart, bad risk YAML vetoes exits |
| REG-03 | Forced close targets the exact held instrument and strike (F2) | REG-03a-c | engine: oms (positions) | V2-09 | PARTIAL: `brokers.exit_intent(position)` builds exits from the held position; v2 must use only that path |
| REG-04 | No open ticket vanishes (F3); positions rebuilt from the durable ledger on restart; reconciliation | REG-04a-c | engine: ledger, runtime (recovery) | V2-10, V2-13 | PARTIAL: append-only ledger, `brokers.reconcile`, `risk_snapshot` from disk. Gaps: positions keyed by symbol only, no restart sequence, paper broker not rebuilt |
| REG-05 | Caps inside the risk veto: ₹30k/trade, ₹90k/day, 25 lots, 3 positions (paper, configurable); PR #14 halt and kill-switch semantics | REG-05a-e | engine: risk-engine, oms | V2-08, V2-09, V2-10 | **SATISFIED for caps and kill switch** (`RiskEngine._entry_veto`, `load_limits` rejects missing keys, values in `config/risk_limits.yaml`). PARTIAL for the halt: lives in legacy `desk/executor.py` + JSON file; ported to `session_halts` |
| REG-06 | A corrupt or partial line mid-day never erases earlier trades or state; per-line guarded parsing; first bad line recorded durably (PR #18 scenario 2e) | REG-06a-c | events, marketdata, control, ledger | V2-02, V2-03, V2-10, V2-11, V2-D2 | PARTIAL: ledger and event audit are SQLite with append-only triggers (satisfied there). Gaps: `RedisStreamsBus.poll` skips good entries before a bad one; no durable bad-line record; PR #18 unmerged |
| REG-07 | Bad YAML/config never stops the bus; last-good config kept; alarm | REG-07a-c | contracts (config loader), engine: risk-engine | V2-04, V2-08 | PARTIAL: `MemoryBus` catches subscriber errors; risk fails closed. Gaps: no last-good copy, no alarm, bad YAML vetoes exits |
| REG-08 | ETL and loaders skip and log bad lines, never crash | REG-08a-b | warehouse, marketdata (sources) | V2-03, V2-18 | PARTIAL: `warehouse/ingest.py` catches some errors but reads whole files; PR #19 ETL unmerged |
| REG-09 | Supervisor never restart-loops (F1): backoff, circuit breaker, alarm | REG-09a-b | runtime (services), health | V2-15, V2-14 | NEW (recorder and feed have backoff only) |
| REG-10 | Every replay and job has a wall-clock timeout | REG-10a-b | runtime (jobs) | V2-04, V2-15, V2-16 | NEW |
| REG-11 | Tests never write into real data folders (`agent_rag` rewrote `data/knowledge`) | REG-11a-b | CI (all packages) | V2-01 | NEW (PR #16's guard covers `desk-ml` only, unmerged) |
| REG-12 | Real cost stack on every simulated fill: ₹20/order, STT 0.15% sell, NSE exchange 0.0355299%, stamp 0.003% buy, SEBI, GST 18% on brokerage+exchange+SEBI, NIFTY lot 65, configurable slippage | REG-12a-d | engine: brokers (fills), ledger (charges) | V2-08 | PARTIAL: `ledger.charges.order_charges` has every component and `Ledger.record_fill` charges every fill; `PaperBroker` slippage configurable. Gap: `config/charges.yaml` exchange is `0.0003503`, not `0.000355299` |
| REG-13 | Exit params are part of every strategy and config gate (infra PR #19 miss) | REG-13a-c | engine: strategies, forward harness, CI gate | V2-06, V2-06b, V2-16, V2-20a | NEW |

Tally: SATISFIED 1 (REG-05 caps, with the halt part still to port), PARTIAL 8, NEW 4.

---

## 4. Founder comments traceability

Source of truth: [`docs/founder/FOUNDER_COMMENTS_LOG.md`](../founder/FOUNDER_COMMENTS_LOG.md) (C1-C11, committed
verbatim from the founder's upload; times there are CT on 2026-09-26). This table maps every comment, and every legacy
carry-over item, to the V2 service, ticket and test that satisfies it. Following the log's rule, nothing here counts as
done until its test passes. A comment that conflicts with another comment or with the 32-step plan is marked
**⚑ Kn** and listed in section 4.2. Those conflicts are **not** resolved here. The design's current default is stated
so the build can continue, and the founder decides.

### 4.1 Traceability table

| Item | What it asks (short) | V2 service(s) | Ticket(s) | Test / proof that satisfies it | Conflict |
|---|---|---|---|---|---|
| **C1** | Option buyer; no long ATM holds; no 1-2 trades/day cap; active management; market-driven trade count | strategy runtime, strike router, position manager, risk engine | V2-06, V2-06b, V2-09 | V2-06b: ATM is never chosen for a planned hold beyond the router's ATM limit; V2-09: exit table tests (time stops, partials, trail); no trade-count limit exists in `risk_limits.yaml` or engine config (config schema test) | ⚑ K1, ⚑ K2 |
| **C2** | Judge strategies on final total net P&L after costs; small losers and low win rate are fine | forward harness, warehouse, founder page | V2-20a, V2-18, V2-08 (costs) | V2-20a: every spec report's headline is total net after the REG-12 cost stack (depth and FC-MEAS), and win rate is never a pass criterion (bar state-machine tests); V2-18: daily report headline = total net | ⚑ K3 |
| **C3** | Strike per trade with a reason (ATM ≤ 5 min holds, ITM100/200 for 15-30+ min; care on expiry day and 09:20-10:00) | strike router (strategy runtime) | V2-06b, V2-20a | V2-06b: router table tests for hold length, expiry day and the open window; every signal carries `strike_choice.reason` and all three alternatives priced at the same timestamp; V2-20a prices the alternatives as shadow legs. Log status: shadow, router lost less than fixed strikes but still lost, so no promotion | — |
| **C4** | Use SSRN papers and good traders' setups; test them, don't trust posted win rates | research track (harvest lab, PR #24) feeding the forward harness | V2-20a (plus the external harvest lab) | Each harvested idea enters V2 only as a preregistered, hash-locked spec (`prereg.lock` refusal test, REG-13b); posted win rates are never an input field in the spec schema (schema test) | ⚑ K4 |
| **C5** | Strategy library; India basket (NIFTY + SENSEX) and forex basket (parked); per-regime weight/rank so the boss picks a daily basket | registry/basket client (strategy runtime), boss | V2-06, V2-07 | V2-06: loads the basket module's output; no basket means no trades; an `FX_SPOT` plugin refuses an India basket; V2-07: regime weights and ranks are logged as `BOSS_SHADOW` and do not change the decision in `shadow` mode | ⚑ K5, ⚑ K6 |
| **C6** | The basket module is a separate parallel track; never blocks the 32-step build; draft PR, merges later | strategy runtime (`registry.py` contract + YAML fallback) | V2-06 | V2-06: the runtime works with the YAML fallback and no basket module installed; the contract test runs against a fixture of the module's output | ⚑ K6, ⚑ K7 |
| **C7** | Don't follow the old engine; build our own production system (Redis, DuckDB, websockets, VPS, customer-ready); old tape engine is reference only | whole V2 stack | all tickets; V2-15 (deploy), V2-16 (gate), V2-17 (freeze) | New merge gate (architecture §6.2: unit, integration, fault, no-look-ahead, determinism, perf, live-like dry run); V2-17 `frozen-legacy` CI check; M1 exit criteria | ⚑ K7, ⚑ K8 |
| **C8** | Bring every fix done on the old engine into the new one | per REG item below | per REG item | The 13 REG rows below, each one must-pass test set in the `regression` CI job (V2-16 meta-test fails if any REG id has no collected test) | ⚑ K8, ⚑ K9 |
| **C9** | The system enters at the top of big candles, gives back 4-5 pts to the imbalance/POC, then stops out | entry-location features, desk order planner, boss veto; research round 10 (external lab) | V2-05b, V2-08b, V2-20a | V2-05b feature fixtures (FVG, candle 50%, VWAP, EMA20, POC; causal); V2-08b: 5-minute give-back logged on every fill; V2-20a prices CHASE vs LIMIT vs WAIT legs; thresholds come from the round 10 report | ⚑ K2, ⚑ K10 |
| **C10** | Boss and desk must be aligned on the entry-location rule | boss selector, desk order planner; basket strategy cards | V2-08b | V2-08b: one config file and one `config_hash` feed both the boss veto and the planner (nesting test: chase ≤ limit/wait ≤ veto); log-only until round 10 thresholds; `enforce` with a null threshold is refused | ⚑ K11 |
| **C11** | Don't mess up with mid-build comments; lots of money and time spent | this log + this table; morning status checklist | V2-16 | V2-16 docs meta-test (**TRACE-01**): every `C#` row in `FOUNDER_COMMENTS_LOG.md` and every `REG-nn` has a row in this table with a ticket and a test; the build fails otherwise | — |
| REG-01 | Closed bars only; no bucket stamped at last print (legacy 3m resample; PR #11, PR #21 leaks) | marketdata, indicators, strategies | V2-03, V2-05, V2-16 | REG-01a-f | — |
| REG-02 | Enforced stop on every open position at all times, incl. restart/reconnect (~₹193k hole) | oms | V2-08, V2-09, V2-10, V2-12, V2-14 | REG-02a-e | — |
| REG-03 | Forced close hits the exact held instrument (F2) | oms (positions) | V2-09 | REG-03a-c | — |
| REG-04 | No open ticket vanishes (F3); rebuild from ledger; reconcile | ledger, runtime (recovery) | V2-10, V2-13 | REG-04a-c | — |
| REG-05 | Caps in the risk veto (₹30k/trade, ₹90k/day, 25 lots, 3 positions); PR #14 halt and kill switch | risk engine, oms | V2-08, V2-09, V2-10 | REG-05a-e | ⚑ K1 |
| REG-06 | A corrupt line never erases earlier state; first bad line recorded durably (PR #18 2e) | events, marketdata, control, ledger | V2-02, V2-03, V2-10, V2-11, V2-D2 | REG-06a-c | — |
| REG-07 | Bad config never stops the bus; last-good kept; alarm | contracts, risk engine | V2-04, V2-08 | REG-07a-c | — |
| REG-08 | ETL and loaders skip and log bad lines | warehouse, marketdata | V2-03, V2-18 | REG-08a-b | — |
| REG-09 | No restart loop (F1): backoff, breaker, alarm | runtime, health | V2-15, V2-14 | REG-09a-b | — |
| REG-10 | Wall-clock timeout on every replay and job | runtime | V2-04, V2-15, V2-16 | REG-10a-b | — |
| REG-11 | Tests never write into real data folders | CI | V2-01 | REG-11a-b | — |
| REG-12 | Real cost stack on every simulated fill | brokers (fills), ledger | V2-08 | REG-12a-d | ⚑ K12 |
| REG-13 | Exit params in every strategy/config gate | strategies, forward harness, CI | V2-06, V2-06b, V2-16, V2-20a | REG-13a-c | — |
| *not in log* | Founder addendum 2 (research round 9): ≤ 1 s depth, ≤ 5 s bid/ask snapshots, OI cadence, time stops first-class, forward harness | marketdata, oms, forward harness | V2-D1, V2-D2, V2-09, V2-20a | V2-D2 cadence tests; V2-09 time-stop tests; V2-20a harness tests | ⚑ K13 |
| *not in log* | Standing rules at the foot of the log (paper only; every number from a source file or real run; verified cost stack; live for customers only on Sahil's call) | all | all; V2-08 (costs); M2 criterion 6 | Live-order gate unchanged (three-part gate, no live-orders compose profile); REG-12 cost tests; PR evidence sections cite source files or runs | ⚑ K12 |

### 4.2 Conflicts flagged (not silently resolved)

Each entry: what conflicts, what the V2 design does **by default** until the founder decides, and the decision needed.

| # | Conflict | Items | Current V2 default (not a resolution) | Founder decision needed |
|---|---|---|---|---|
| **K1** | C1 says "no 1-2 trades/day cap, market-driven trade count". The risk engine and the old plan still limit activity: 15-minute cooldown after a loss (PR-011 proven fix, `cooldown_after_loss_minutes: 15`), max 3 open positions, ₹90k daily loss cap (REG-05), and Round 8 E2 allows "no second trade per day" | C1 vs REG-05, PR-011, Round 8 E2 | No per-day trade-count cap anywhere. The cooldown, position cap and daily loss cap stay, because they are risk limits, not count caps. E2 keeps its preregistered one-per-day rule (changing it would break its preregistration) | Keep the 15-minute loss cooldown and the 3-position cap as they are, or loosen them for an active buyer? |
| **K2** | C9/C10 pullback limits and "wait for a consolidation candle" skip or delay entries. That reduces trade count and misses some moves, against C1's active, market-driven trading | C9/C10 vs C1 | Log-only: trades stay as today (chase); the missed-move cost is measured by the CHASE vs LIMIT vs WAIT shadow legs | After round 10: accept fewer trades for better entry location? |
| **K3** | C2 says judge on total net P&L. The Round 8 forward bar (FWD-BAR) also requires a gross > 0 kill check at n = 30, both halves net > 0, a placebo percentile, and one-sided t ≥ 2.13 at n ≥ 120 before 09's five-pass. A strategy can be net-positive and still fail significance | C2 vs Round 8 FWD-BAR, 09 five-pass (SDLC gate) | Total net is the report headline; promotion still needs FWD-BAR and the five-pass | Is total net alone enough to promote, or does significance still gate promotion? |
| **K4** | C4 wants SSRN papers and traders' setups tested actively. Round 8 §5 warns that selection at the current trial count (3,841) is not informative and every new test raises it | C4 vs Round 8 multiple-testing rules | Every harvested idea is one preregistered spec, trials are counted, and reports carry the deflated Sharpe | Accept the trial budget, or cap the number of harvested specs per round? |
| **K5** | C5 says "the boss picks a daily basket". The V2 design has the basket module (pre-market) produce the basket and the boss only *apply* it, freezing it for the session (founder can remove, not add) | C5 vs architecture §2.5/§2.6 | Basket module picks; the boss applies and logs regime ranks in shadow | Should the boss choose among basket entries by regime intraday, or keep the basket fixed per session? |
| **K6** | The basket track (bc-80505954) writes `basket_india.json` / `basket_forex.json`. The V2 contract assumed `config/v2/baskets/YYYY-MM-DD.yaml` | C5/C6 vs architecture §2.5 | V2-06 adds a read-only adapter for the basket module's JSON; no change is asked of the basket track (C6) | Confirm the basket JSON is the canonical format |
| **K7** | C6 says the basket track "never blocks the 32-step build". After C7 the 32-step plan is superseded for new work by this V2 plan | C6 vs C7, `04_MIGRATION_PLAN.md` | Read as "never blocks the V2 build plan"; V2-06 runs on the YAML/JSON fallback | Confirm the reading |
| **K8** | C7 (don't follow the old engine) conflicts with the 32-step plan's own principles: "Incremental, not rewrite", "No breaking changes to working paper system", and the PR-007 to PR-009 acceptance tests that require identical trades to `paper_scalp.py` | C7 vs `04_MIGRATION_PLAN.md` principles 1 and 6, PR-007..009 | V2 follows C7 (the later, explicit founder direction). `04_MIGRATION_PLAN.md` carries a "superseded for new work" note; parity is no longer a gate | Confirm that C7 overrides those plan principles |
| **K9** | C8 (bring every old-engine fix across) against C7 (don't follow the old engine). Also, PR-010's known-but-unfixed legacy bugs (look-ahead in `_hold_series`, reversed OI signal, double-counted `greeks_vote_intent`, degenerate ML models) are not in the 13 REG items | C8 vs C7, PR-010 | Fixes carry over as **behaviour tests** (REG), not code. PR-010's analyst-specific bugs are not REG items because those analysts are not ported; the `_hold_series` look-ahead is covered generically by REG-01 | Should PR-010's analyst bugs become REG tests anyway (for example, if a legacy analyst is re-implemented as a v2 strategy)? |
| **K10** | C9's pullback limits are passive entries. Round 8 **closed** passive entries on breakout-style signals: 94-96% fill rate, saved ~₹355/trade in spread, and lost more to adverse selection (fills cluster on failed breaks) | C9 vs Round 8 §1.1 | Log-only; round 10 decides the thresholds; the forward harness measures fill-conditional outcomes for LIMIT vs CHASE | After round 10: does the pullback limit avoid the adverse selection Round 8 found? |
| **K11** | C10 requires the basket's strategy cards to follow the entry-location rule. That is a dependency on the basket track, which C6 says must stay independent | C10 vs C6 | A strategy card without an entry policy gets the default `EntryPolicy`; V2 does not wait on the basket track | Should entry-policy fields be required on basket strategy cards? |
| **K12** | The log's standing cost stack lists "GST 18%" and no SEBI fee. Founder addendum 1 (REG-12) specifies a SEBI fee and GST on brokerage + exchange + SEBI. `config/charges.yaml` also has the NSE rate at `0.0003503`, not the `0.0355299%` both sources state | Log standing rules vs REG-12 vs `config/charges.yaml` | REG-12 as written (includes SEBI; GST on brokerage + exchange + SEBI); V2-08 moves the NSE rate to `0.000355299` (VERIFY against the circular) | Confirm SEBI fee and GST base |
| **K13** | Founder addendum 2 (depth and quote recording, OI cadence, first-class time stops, forward harness) has **no C# entry** in the log. The log's rule says every comment gets an entry the same turn. This addendum (commit the log plus traceability) is not in the log either | Log completeness | Tracked here as *not in log*; the log file is committed verbatim and not edited by the agent | Add C12+ entries for these (the founder owns the log's numbering and times) |

---

## 5. Milestones

### M1: paper-live on the new stack

**Scope:** V2-D1, V2-D2, and V2-01 to V2-16 including V2-05b, V2-06b and V2-08b (V2-17 recommended alongside). The engine runs during
market hours on real Dhan market data (user box or VPS), with the paper broker, strategies at stage `shadow` or
`paper` from a founder-approved basket, founder controls, alarms, backups, and the frozen benchmark running nightly for
comparison.

**Exit criteria (all required):**
1. Every merge gate check green on `main` (section 6.2 of the architecture), including **every REG-01 to REG-13
   test** (section 3) and `TRACE-01` (section 4); every C1-C11 row whose ticket is in M1 has its test passing.
2. **10 consecutive sessions** on the new stack with: zero duplicate orders; zero unresolved reconciliation
   mismatches at EOD; every open position had a protective stop; flat by 15:15; no entry under a hold.
3. **Nightly determinism:** replaying each session's tape through the engine reproduces that session's decisions,
   orders and fills exactly.
4. **Restart drill daily** in at least 5 of those sessions: `kill -9` the engine mid-session; READY in < 60 s; no
   duplicates; clean reconciliation; every open position still has its stop.
5. Alerts proven live: feed drop, engine death, Redis restart and a restart-loop breaker each raised and cleared on
   the founder page and Telegram at least once.
6. Backup restore drill passed once.
7. **Depth recording:** V2-D2 has captured those 10 sessions with depth for ≥ 95% of market minutes on every traded
   strike, and the FULL decoder is verified against a captured frame.
8. The old paper loop (`paper-scalp --loop`) is switched off for trading and runs only as the nightly benchmark.

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
1. M1 criteria hold for 20 more sessions on Postgres, with the REG suite green on both store engines.
2. Isolation tests prove account A cannot read, affect or be sized by account B.
3. Auth, rate limits, TLS and backups verified; an external review of the public surface (at least a scripted OWASP
   baseline scan) passes.
4. **Founder and legal sign-off** on SEBI obligations, customer terms and risk disclosures (`docs/COMPLIANCE.md`).
5. At least one strategy has passed the forward harness bar (Round 8 FWD-BAR) **and** 09's five-pass before it is
   shown to customers as more than an educational or shadow signal. Without that, customer-ready means the platform
   is ready, not the product.
6. Live orders remain off until the founder turns on `limited_live` through the existing three-part gate.

---

## 6. Handoff block

- **Accepted:** the re-map in section 1; 26 tickets within the 200-500 line rule (V2-D1, V2-D2, V2-01 to V2-19,
  V2-05b, V2-06b, V2-08b, V2-20a, V2-20b); founder addendum 3 (entry location: V2-05b features, V2-08b desk planner,
  boss stretch veto and trade-through fills, log-only until research round 10); M1 and M2 criteria that test invariants and operations, not P&L; founder addendum 1
  (REG-01 to REG-13 in section 3, each with test ids, owner and ticket); founder addendum 2 (depth and quote recording,
  OI cadence, strike router, first-class time stops, forward harness off by default) as early tickets in the new
  system only.
- **Also accepted:** `docs/founder/FOUNDER_COMMENTS_LOG.md` (C1-C11) committed verbatim as the single source of truth
  for mid-build comments, with the traceability table and 13 flagged conflicts (K1-K13) in section 4. The conflicts
  are left for the founder; the table states only the design's current default.
- **Rejected:** old-engine bug fixes (PR-010), tuning steps (PR-022, PR-023), RAG (PR-030) and crypto (PR-032) as
  build work; byte-identical parity as a gate; patching `paper_scalp.py` for any addendum item.
- **UNKNOWN / DATA_INSUFFICIENT:** the registry/basket module's final API (V2-06 codes to the contract and a YAML
  fallback); the lab's frozen hashes for E1-E3 (blocks V2-20b only); Dhan FULL-packet byte layout (V2-D1 verifies
  against a captured frame); whether chain REST carries bid/ask; OI update cadence (V2-D2 measures it); Dhan token
  refresh for unattended runs (V2-12/V2-15 VERIFY); exact code lines behind F1/F2/F3 and the ₹193k stop hole (from the
  founder's Phase 2 review, not in the repo; the REG tests specify behaviour); entry-location thresholds (research
  round 10, due Sunday; log-only until then).
- **Gap addressed:** `docs/01_CURRENT_STATE_AND_GAPS.md` §5 (backtest/replay: one code path, no look-ahead), §6 (role
  separation without the monolith), §7 (tech stack and deployment), §3 (broker adapter restart safety), §4 (data
  capture: bid/ask depth).

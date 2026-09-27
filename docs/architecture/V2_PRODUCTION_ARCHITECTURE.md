# V2 production architecture

**Status:** DESIGN (docs only). Paper only. No broker order calls, no credentials, nothing secret in the repo.
**Founder direction (Sahil, 2026-09-26):** stop building on the old engine. Build our own production trading
system from the new requirements. The old tape-replay paper engine (`packages/desk-ml/src/desk_ml/paper_scalp.py`
and `picker.py`) is **reference only**: it lost a lot of money. The system must be able to move to a VPS and go
live for customers when the founder asks.
**Companion:** [`V2_BUILD_PLAN.md`](V2_BUILD_PLAN.md) (the 32-step plan re-mapped, and the next build tickets).
**Inputs read:** [`docs/04_MIGRATION_PLAN.md`](../04_MIGRATION_PLAN.md), [`docs/PHASE2_NOTES.md`](../PHASE2_NOTES.md),
[`docs/02_TARGET_ARCHITECTURE.md`](../02_TARGET_ARCHITECTURE.md), [`docs/03_DATA_CONTRACTS.md`](../03_DATA_CONTRACTS.md),
[`docs/MASTER_REQUIREMENTS.md`](../MASTER_REQUIREMENTS.md), `docs/research/ROUND8_STRATEGY_REDESIGN.md` (PR #22, draft),
and the merged code in `packages/{data-recorder,brokers,risk-engine,health,ledger,events,analysts,boss,desk}` and
`packages/desk-ml/src/desk_ml/{regime,llm_analyst}`.

---

## 0. Now / Why / Next (plain English)

- **Now.** We have good safety parts already merged: a data recorder, a broker interface with a paper broker and an
  order state machine, a risk engine that can veto, health alarms, an append-only ledger with charges, an event bus
  (in-memory, plus Redis Streams), an LLM analyst that only advises, and a regime labeller. But the boss, the desk and
  the 22 analysts from Phase 2 are thin wrappers around the old engine. They cannot run without `paper_scalp.py`.
- **Why.** The old engine re-replays the whole day on every heartbeat, mixes decision and execution code in one 8,440-line
  file, and its only merge gate was "same bytes as the old engine". That gate protects the losing behaviour. Round 8
  (PR #22) also showed the money was lost **before costs**: the problem is the entry edge, not tuning. So the new system
  has to make it cheap and safe to try, measure and kill strategies. It must not be one more copy of the old picker.
- **Next.** Build a small event-driven engine where backtest, replay and live run the **same code**. A bar only becomes
  visible after it closes. Every order has an idempotent id. Every state change is written to a durable ledger before
  anyone acts on it. Strategies are plugins that emit signals, not orders. The boss picks, the risk engine can veto, and
  the router and position manager execute. The first milestone is **paper-live on the new stack**: real Dhan market
  data, paper broker, safe restarts, founder controls, health alarms. The old engine runs next to it only as a frozen
  benchmark.

What this design does **not** claim: that any strategy is profitable. Architecture readiness is not strategy readiness.
A strategy reaches customers only after the Round 8 forward bar (FWD-BAR) and 09's five-pass review.

---

## 1. Design principles (the few rules everything else follows)

1. **One code path.** Backtest, tape replay, live-like dry run and live paper all run the same `Engine` over a stream of
   envelopes. Only the event source (tape file, warehouse history, Redis) and the broker adapter (paper, later Dhan)
   change. There is no "replay mode" branch inside strategy, boss, risk or position code.
2. **Event time, not wall time.** Decisions read `clock.now()`, and that clock is driven by the inputs
   (`available_ts`). Wall time is used only for I/O timeouts and liveness, never to decide a trade.
3. **Nothing is visible before it is knowable.** Every input carries `event_ts` (when it happened) and `available_ts`
   (when we could have known it). The engine processes inputs in `available_ts` order. A 1-minute bar
   `[10:00, 10:01)` is available at `10:01:00 + finalize delay`, never earlier.
4. **Durable before visible.** A state change (order, fill, position, founder command, checkpoint) is committed to the
   durable store **before** it is published to Redis or shown in the UI (transactional outbox).
5. **Idempotent everywhere.** Order ids, event ids and command ids are deterministic or client-supplied, and every
   consumer deduplicates. Retries and restarts never create a second order.
6. **Fail closed on entries, fail open on exits.** Any doubt (stale data, reconciliation mismatch, bad config, ledger
   write failure) blocks new entries. Exits, cancels and flatten are always allowed (the merged risk engine already
   works this way: `risk_engine.engine._adjust_veto`).
7. **LLM is advice only and never on the hot path.** Zero blocking LLM calls between a bar closing and an order.
8. **Reuse the merged components; do not grow the monolith.** No new code imports `desk_ml.paper_scalp` or
   `desk_ml.picker`, except the frozen benchmark harness.
9. **Ponytail.** One engine process for the hot path, stdlib `sqlite3`, the Redis we already use, and FastAPI we already
   use. New dependencies must be justified in the ticket (only `duckdb`, `prometheus-client` and `pyjwt` are proposed,
   each at a named milestone).

---

## 2. Services and boundaries

### 2.1 Topology

```
                    Dhan WS / REST (user box or VPS only; creds from env)
                                   │
                         ┌─────────▼──────────┐        ┌───────────────────┐
                         │ marketdata         │───────▶│ tape-writer       │──▶ data/tape/v2/YYYY-MM-DD/*.jsonl
                         │ ticks→bars, chain, │        │ (same process)    │
                         │ depth, clock, feed │        └───────────────────┘
                         └─────────┬──────────┘
                                   │ Redis Streams md:*
   ┌───────────────────────────────▼────────────────────────────────────────────┐
   │ engine  (ONE process, single-threaded kernel, in-process MemoryBus)         │
   │                                                                              │
   │  features ─▶ strategy runtime ─▶ boss ─▶ risk engine ─▶ order router ─▶ broker│
   │     ▲        (plugins, registry,   (basket,  (veto)       (idempotent)  (paper│
   │     │         daily basket)        select,                               now) │
   │     │                              size)        position manager ◀── fills   │
   │     │                                          (exits, time stops, trail)    │
   │  founder controls (commands)                    ledger + charges + outbox    │
   └───────┬──────────────────────────────────────────────┬──────────────────────┘
           │ Redis Streams ctl:*, sig:*, boss:*, oms:*, pos:* (from outbox)
   ┌───────▼─────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐
   │ gateway (API +  │  │ health      │  │ llm-advisor  │  │ nightly jobs (ETL,   │
   │ websocket)      │  │ + metrics   │  │ (advice only)│  │ legacy benchmark,    │
   │ UI, customers   │  │ + alerts    │  │              │  │ forward evaluator)   │
   └─────────────────┘  └─────────────┘  └──────────────┘  └──────────────────────┘
```

**Why the hot path is one process.** Features, strategies, boss, risk, router, position manager and the ledger writer
share one ordered input stream, so one process gives us determinism (same inputs, same outputs), a single SQLite writer,
and no network hop on the path from bar to order. Each part is still a separate package that only talks through
envelopes on the bus, so it can move to its own process later (section 2.13) without changing its code.

**Processes (compose services):** `redis`, `marketdata`, `engine`, `gateway`, `health`, `llm-advisor` (optional
profile), `recorder` (the existing PR-001 recorder, kept as an independent backup), `nightly` (one-shot jobs from a
timer). One Python image runs all of them with different commands (`python -m runtime <service>`).

### 2.2 Package layout

Existing packages keep their names. New code goes into new packages; `packages/contracts` and `packages/indicators`
are notes-only today and become real.

```
packages/
  contracts/src/contracts/     NEW   envelope v2, payload schemas, Clock, deterministic ids, instrument ids
      envelope.py  schemas.py  clock.py  ids.py  instruments.py
  events/src/events/           REUSE+EXTEND  bus.py (+ stream-per-topic, consumer groups), audit.py, outbox.py (new)
  marketdata/src/marketdata/   NEW   market data service + event sources
      dhan_ws.py      (wraps dhan_client.feed.MarketFeedCollector)
      normalize.py    (Dhan packet -> Tick / DepthQuote; security id -> InstrumentId)
      bars.py         (BarBuilder: ticks -> closed 1m bars, finalize delay)
      chain.py        (option chain poller; dhan_client.option_chain; 1 unique request / 3 s)
      clock.py        (CLOCK heartbeat every second; synthesised by sources in replay)
      sources.py      (TapeSource, RecorderTapeSource, WarehouseSource, RedisSource)
      tape.py         (TapeWriter: md:* -> data/tape/v2/YYYY-MM-DD/<stream>.jsonl)
  indicators/src/indicators/   NEW   pure incremental indicators + feature engine
      core.py (EMA, ATR, VWAP/TWAP, realised vol, HAR forecast, OI change with lag)
      engine.py (FeatureEngine) view.py (FeatureView with as-of guard)
      adapters.py (wraps desk_ml.regime.labels.RegimeLabeller, analysts.shadow helpers)
  strategies/src/strategies/   NEW   strategy runtime
      api.py (Strategy protocol, StrategyMeta, Signal, ExitPlan)
      registry.py (client for the registry/basket module; YAML fallback)
      runtime.py (StrategyRuntime: load, isolate, route events, budgets)
      select.py (strike selection: ATM/ITM100/ITM200 by DTE, from the instrument master)
      plugins/ (one file per strategy; shadow research plugins such as Round 8 E1-E3)
  boss/src/boss/               REBUILD  selector.py (v2 boss). orchestrator.py stays, frozen legacy.
  risk-engine/                 REUSE+WRAP  (account scope, injected clock; section 7.2)
  brokers/                     REUSE+WRAP  (clock injection, fill models, paper state rehydrate)
      fills.py (NEW: DepthFill, HalfSpreadFill, LtpSlippageFill)
  oms/src/oms/                 NEW   router.py (order router), positions.py (position/desk manager), exits.py
  ledger/                      REUSE+EXTEND  migrations/NNN_*.sql, account_id, checkpoint, outbox, commands
  control/src/control/         NEW   founder command log and semantics (ports PR #18's design)
  health/                      REUSE+EXTEND  (engine heartbeat, feed status, metrics, alert rules)
  runtime/src/runtime/         NEW   engine kernel + service entry points + wiring from config
      kernel.py (Engine) wiring.py services.py __main__.py recovery.py
  warehouse/                   REUSE+EXTEND  DuckDB ETL (adapts PR #19's etl.py)
  desk-ml/                     FROZEN legacy engine; regime/ and llm_analyst/ reused by import
  desk/  analysts/legacy.py    FROZEN legacy wrappers (desk/paper.py helpers reused)
  data-recorder/  dhan-client/ REUSE as-is
apps/
  api/                         EXTEND into the gateway (v2 websocket, auth, rate limits); legacy routes read-only
  web/                         REUSE (Desk/Founder UI from PR #15), switched to the v2 feed
deploy/
  docker/Dockerfile  compose.yaml  compose.vps.yaml  Caddyfile  systemd/aad.service  scripts/{deploy,backup,restore}.sh
config/
  v2/engine.yaml  v2/markets/india.yaml  v2/strategies/registry.yaml  v2/baskets/  (plus existing risk/charges yaml)
```

### 2.3 Market data service (`packages/marketdata`, process `marketdata`)

- **Input:** Dhan live market feed over websocket via `dhan_client.feed.MarketFeedCollector`. It already does connect,
  subscribe, decode, and reconnect with exponential backoff up to 30 s. Option chain over REST
  (`dhan_client.option_chain`), rate-limited to one unique request per 3 s. Instrument master from
  `dhan_client.instruments` / `data_recorder.instruments`.
- **Subscriptions:** index spot (NIFTY 13, BANKNIFTY 25, SENSEX 51; ids verified from the instrument master at start),
  current futures, and the strikes the runtime asks for (ATM ± N for the day's baskets, re-centred when spot moves more
  than one strike step). Quote mode for depth (best bid/ask) on traded strikes.
- **Output streams:** `md:ticks`, `md:depth`, `md:bars:1m`, `md:chain`, `md:clock`, `md:status`.
- **Bar rule:** `BarBuilder` keeps one open bar per instrument. It closes bar `[t, t+60s)` at the first tick with
  `event_ts ≥ t+60s`, or at the `CLOCK` heartbeat `t+60s+finalize_delay` (default 1.5 s), whichever comes first. The bar
  gets `available_ts` = the time it was closed. Late ticks for a closed bar are counted (`late_ticks` metric) and
  dropped; bars are never revised.
- **Reconnect and staleness:** On disconnect it publishes `FEED_STATUS {status: DOWN}` at once, reconnects with backoff,
  resubscribes, and publishes `FEED_STATUS {status: UP, gap_s}`. If no tick arrives on a subscribed index for more than
  `stale_after_s` (default 5 s during market hours), it publishes `FEED_STATUS {status: STALE, instrument}`. The engine
  blocks entries on any underlying that is DOWN or STALE. A bar that spans a gap is flagged `gap: true`, and features
  treat it as missing.
- **Tape writer:** a second task in the same process consumes `md:*` and appends to
  `data/tape/v2/YYYY-MM-DD/<stream>.jsonl` (gzip at end of day). That file is exactly what the engine saw, so it
  becomes the replay input for the same engine code.
- **Credentials:** only in this process and only from env (`DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`) or a Docker secret
  file. Without credentials it refuses to start in `live-data` mode. In `replay` mode it plays a tape into Redis
  (`TapeSource → Redis`) for the live-like dry run.

### 2.4 Feature / indicator service (`packages/indicators`, in the engine)

- `FeatureEngine.on_event(envelope)` updates incremental state per instrument and timeframe: EMA, ATR, VWAP (TWAP when
  the index has no volume), realised volatility, the daily HAR forecast, OI change per strike lagged to the last
  snapshot **strictly before** the decision minute (Round 8 E1 rule), efficiency ratio, range/ATR, and the regime label.
- Reused as-is by adapter: `desk_ml.regime.labels.RegimeLabeller` (causal; built for streaming bars) and the pure
  helpers in `analysts/shadow.py` (`efficiency_ratio()`, `range_over_atr()`, `dealer_gex()`).
- `FeatureView` is what strategies read. `view.get(name, instrument, tf)` returns a `FeatureValue(value, as_of,
  available_ts)`. With `strict=True` (always in tests and gates) it raises `LookAheadError` if
  `available_ts > clock.now()`. A missing or warming-up feature returns `None`, and the strategy must treat it as
  "no signal".
- 5-minute Supertrend/MACD/RSI exist only as confirm-or-kill filters (`teams/04_quant/docs/SIGNAL_STAGING.md`), never
  as entries.

### 2.5 Strategy runtime (`packages/strategies`, in the engine)

Strategies are plugins. They emit **signals**, never orders.

```python
# packages/strategies/src/strategies/api.py
@dataclass(frozen=True)
class StrategyMeta:
    strategy_id: str              # "R8-E1-COIL-SIDE", "LEGACY-BENCH", "MIX-..." (never STRAT-015+)
    version: str                  # semver; bump on any logic change
    params_hash: str              # sha256 of frozen params (preregistration hash)
    markets: tuple[str, ...]      # ("IN_INDEX_OPT",) now; ("FX_SPOT",) later
    underlyings: tuple[str, ...]  # ("NIFTY", "SENSEX")
    inputs: tuple[str, ...]       # ("bars:1m", "chain", "depth")
    features: tuple[str, ...]     # feature names it reads (checked at load)
    stage: str                    # "shadow" | "paper" | "live_eligible"
    max_positions: int = 1

@dataclass(frozen=True)
class ExitPlan:
    stop: Level | None            # Level(kind="premium"|"underlying", price=..)
    target: Level | None
    time_stop_s: int | None
    flat_by_ist: str = "15:15"
    partials: tuple[Partial, ...] = ()   # Partial(at=Level, fraction=0.5)
    trail: Trail | None = None           # Trail(kind="step", activate_at=Level, step=..)
    protective_stop: Level | None = None # resting broker-side stop (disaster stop)

@dataclass(frozen=True)
class Signal:
    signal_id: str                # ids.signal_id(strategy_id, version, underlying, decision_ts, n)
    strategy_id: str
    underlying: str
    side: str                     # "CE" | "PE"  (buyer-only desk; writer-side needs a founder decision)
    strike_rule: str              # "ATM" | "ITM100" | "ITM200" | "DTE_RULE"
    decision_ts: str              # == clock.now() when emitted
    confidence: float             # 0..1, calibrated or null; never shown as a win rate
    exit_plan: ExitPlan
    reasons: tuple[str, ...]      # short machine codes + one human line
    features: dict[str, float]    # the exact inputs used (for audit and the forward evaluator)

class Strategy(Protocol):
    meta: StrategyMeta
    def on_session_start(self, ctx: SessionContext) -> None: ...
    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]: ...
    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]: ...
    def on_position(self, update: PositionUpdate) -> list[ExitRequest]: ...   # optional early exit
    def on_session_end(self) -> dict[str, Any]: ...                           # per-strategy day stats
```

- **Registry and daily basket.** The registry/basket module is being built separately (shadow only). The runtime
  depends only on this contract:

  ```python
  # packages/strategies/src/strategies/registry.py
  def load_registry() -> dict[str, RegistryEntry]        # strategy_id -> module path, version, params_hash, stage
  def basket_for(session: date, market: str) -> Basket    # Basket(session, market, entries=[BasketEntry(
                                                          #   strategy_id, underlyings, weight, max_lots, stage)],
                                                          #   source, basket_hash)
  ```

  Until that module lands, `registry.py` reads `config/v2/strategies/registry.yaml` and
  `config/v2/baskets/YYYY-MM-DD.yaml`. **No basket means no trades** (fail closed). The runtime publishes
  `BASKET_LOADED {basket_hash, entries}` at session start. The basket is frozen for the session; a founder command
  can only remove entries mid-session, not add them.
- **Markets.** `India NIFTY/SENSEX` now (BANKNIFTY data is recorded; trading it is a basket decision). Forex later
  through a `MarketAdapter` (section 2.12). A strategy declares its markets, and the runtime refuses to load it into a
  basket for another market.
- **Isolation.** Each strategy call is wrapped: an exception, or a call over `budget_ms` (default 20 ms, measured on
  the engine thread), disables that strategy for the rest of the session, publishes `HEALTH_ALERT`, and never affects
  the other strategies. Strategies get a read-only `FeatureView` and no access to the broker, ledger or bus.
- **Stages.** `shadow` signals are logged (`sig:signals` with `stage: shadow`) and evaluated by the forward evaluator.
  They never reach the router. `paper` signals go to the boss. `live_eligible` is a label that only a founder-approved
  registry change can set, after FWD-BAR and 09's five-pass.

### 2.6 Boss (`packages/boss/src/boss/selector.py`, in the engine)

The boss turns signals into at most one **decision** per underlying per bar. It never calls the broker.

1. **Basket gate.** Drop signals from strategies not in today's basket, or not in stage `paper` or above.
2. **Holds.** Drop everything on an underlying under a hold: founder pause, stop or blocked window; the pre-market event
   day or news hold (`EVENT_MEMORY.md`); feed DOWN or STALE; reconciliation mismatch; global skips from Round 8 (no
   option buying 09:15–10:00 except a spec that prices it; no ATM on expiry day; no entries after 14:45). Holds are
   data in `config/v2/engine.yaml`, not code.
3. **Conflicts.** Opposite sides on one underlying in the same bar mean HOLD (logged as `CONFLICT`), unless the basket
   gives one strategy priority. Same side from several strategies means one decision tagged with every contributor.
4. **Sizing.** `lots = min(basket max_lots, VOLSIZE(EM30), CAPLOTS(risk budget, δ, stop))`, skip if < 2 (Round 8 §3.0).
   The strike comes from `strategies.select` using the instrument master (lot size is never hard-coded).
5. **Regime and weights (shadow).** The merged adaptive weights (`desk_ml.regime.weights`) and the intermarket overlay
   run next to the static decision and publish `BOSS_SHADOW`, exactly as today. They do not change the decision
   until a founder-approved config flips `regime.mode: apply`.
6. **Output.** `DECISION {decision: ENTER|HOLD, ...}` with the signal ids, sizing inputs and the hold or conflict
   reason. An ENTER becomes a `TradeIntent` (reused from `risk_engine.TradeIntent`) for each account that follows the
   basket.

The LLM analyst never sits in this path. It reads published decisions and returns advice later (section 2.11).

### 2.7 Risk engine with veto (`packages/risk-engine`, in the engine)

Reused: `RiskEngine.check_entry / check_exit / check_flatten`, the limits in `config/risk_limits.yaml`, re-read on
every check, fail closed, every decision recorded to the ledger, and state rebuilt from the ledger (`risk_snapshot`)
so a restart loses nothing. Wrapped for v2:

- `now` always comes from the engine clock. `RiskEngine` already accepts `now`; the router always passes it.
- **Account scope:** one `RiskEngine` per account, bound to that account's ledger partition and limits
  (`config/risk_limits.yaml` for the founder account now; an `account_limits` table at the customer milestone).
- New entry checks: feed status (DOWN or STALE means veto `FEED_STALE`) and a strategy-level daily loss cap
  (`STRATEGY_DAILY_LOSS`), both read from the same snapshot.
- Latency budget stays at < 10 ms p99 (SQLite reads, WAL).

### 2.8 Order router over a broker interface (`packages/oms/router.py`, in the engine)

- **Interface:** the merged `brokers.BrokerAdapter` (place, super order, modify, cancel, flatten, status, positions,
  orders, balance). Implementations: `PaperBroker` now, `DhanBroker` later (already written, and it refuses unless
  mode is `limited_live`/`live` **and** `ALL_ABOUT_DHAN_LIVE_CONFIRM` is set **and** a fresh approval exists), and a
  forex broker later.
- **Sequence per intent (idempotent):**
  1. `client_order_id = ids.order_id(account_id, signal_id, leg)`, a deterministic 27-character `[a-z0-9]` string that
     fits Dhan's `correlationId`. The same signal on replay or restart gives the same id.
  2. `risk.check_entry(intent, now=clock.now())`. A veto means `ENTRY_VETOED` and nothing is sent.
  3. Ledger write: order row in state `NEW`, in the same transaction as the input checkpoint.
  4. `broker.place_order(intent, decision)`. On timeout the order is marked `needs_lookup`, and the next attempt asks
     the broker by correlation id (`DhanBroker._adopt`; `/orders/external/{correlation_id}`) before resending.
  5. Broker transitions and fills go to the ledger through `attach_ledger`, then out through the outbox.
- **Clock injection:** `BrokerAdapter.approval_problems` reads `datetime.now(IST)` for the 30 s decision age today
  (`ClockedPaperBroker` overrides it for replay). v2 passes the engine clock to every adapter (`clock=` constructor
  argument), so replay and live check age the same way.
- **Paper fills (`brokers/fills.py`):** `PaperBroker` gets a pluggable fill model. Priority: `DepthFill` (buy at the
  recorded ask, sell at the bid, of the first depth quote with `available_ts ≥ order.available_ts + latency_ms`, plus
  0.05 impact at 25 lots), then `HalfSpreadFill` (LTP ± the measured half-spread by moneyness and time of day, the
  Round 8 FC-MEAS table in `config/v2/markets/india.yaml`), then the current `LtpSlippageFill` as the last fallback.
  The fill model used is stored on every fill. Charges come from `ledger.charges` (`config/charges.yaml`).
- **Protective stop.** After an entry fills, the router places a resting stop order (`SL-M`, from
  `ExitPlan.protective_stop`, else the strategy stop widened by a configured buffer). If the engine dies, the position
  is still protected at the broker. In paper, `PaperBroker` simulates it. The position manager cancels or modifies it
  on every exit or trail step.

### 2.9 Position / desk manager (`packages/oms/positions.py`, `exits.py`, in the engine)

Owns every open position after the entry fill. On each `TICK`/`DEPTH`/`BAR_CLOSED`/`CLOCK` it checks, in this order:

1. founder `CUT_LOSS`, `FLATTEN_ALL` or kill switch, then exit at market (never refused);
2. **stop** (premium or underlying level; bar-close or tick trigger as the plan says);
3. **EOD flat** at `flat_by_ist` (15:15 default) using the `CLOCK` heartbeat, so it fires with no ticks at all;
4. **time stop** (`time_stop_s` after the fill);
5. **target** or **partials** (scale out a fraction, then move the stop as the plan says);
6. **trailing** (step trail once activated; every step modifies the protective stop);
7. strategy `on_position` exit requests.

Each exit is an `EXIT` intent through `risk.check_exit` (allowed under the kill switch) and the router. A mark-to-market
exception keeps the merged fail-safe behaviour (`desk.executor` `failsafe_mtm_error`): close at the last good quote and
block new entries for the session. Exits are mechanics, not edge (Round 8 §4.3), so there is no exit tuning in the
build plan.

### 2.10 Ledger and charges (`packages/ledger`, in the engine; read by gateway, health, nightly)

Reused: the append-only SQLite ledger (`orders`, `order_events`, `fills`, `positions`, `trades`, `charges`,
`risk_decisions`, `recon_runs`, with no-delete and no-update triggers) and `order_charges()` from
`config/charges.yaml`. Extended (section 3.3): `account_id` on every row, `positions` keyed by
`(account_id, instrument_id)` (today it is keyed by `symbol` only), `engine_checkpoint`, `outbox`, `founder_commands`,
`strategy_day_stats`, and numbered SQL migrations.

### 2.11 Founder controls (`packages/control`; API in the gateway; applied in the engine)

- Commands: `START`, `STOP`, `PAUSE {minutes}`, `BLOCKED_WINDOWS {windows}`, `CUT_LOSS {position_id}`,
  `FLATTEN_ALL {underlying?}`, `KILL`, `REARM`, `SET_LOTS {lots|null}`, `INDEX {underlying, enabled}`,
  `BASKET_REMOVE {strategy_id}`, `MIN_CAPITAL`, `ADD_FUNDS`. This is the PR #18 control set plus basket removal.
- **Path:** gateway validates (Pydantic, `extra="forbid"`), and destructive commands need a single-use confirm token
  (120 s). It publishes `FOUNDER_COMMAND` on `ctl:commands` with a client `command_id`. The engine persists the command
  (`founder_commands`, unique `command_id`), applies it from its own `available_ts`, and publishes `COMMAND_ACK
  {applied|rejected, reason}`. The same log replayed gives the same result.
- **Out-of-band kill (works when Redis or the engine is down):** the risk engine already vetoes every entry while
  `data/ledger/KILL_SWITCH` exists. `python -m runtime flatten --account founder` talks straight to the broker adapter
  with `risk.check_flatten()`. Both are documented in the runbook and tested.
- Founder commands always win over the boss and strategies. The risk engine still enforces founder-set limits.

### 2.12 Websocket API gateway (`apps/api`, process `gateway`)

- Keeps the existing FastAPI app and read-only routes (`/health/status`, `/ui/snapshot`, `/ui/stream`, ...) during the
  switch. Adds `GET /v2/snapshot` and `WS /v2/ws`.
- `WS /v2/ws`: the client sends `{"op":"subscribe","channels":["positions","decisions","health","market:NIFTY"]}`.
  The server sends a snapshot per channel, then deltas `{channel, seq, envelope}`. The source is the Redis streams
  (consumer group `gateway`) plus hot-state hashes. A client that misses sequence numbers asks for a new snapshot.
  The browser never talks to Dhan or Redis.
- Channels are scoped by role: `founder` sees everything; `customer` sees `signals:public` (the customer-safe ticket:
  trend, 3-minute chain, cited news; no indicator soup, `CUSTOMER_TALK.md`) and its own account channels only.
- Auth, rate limits and tenancy are in section 5.6.

### 2.13 LLM analyst (advice only; process `llm-advisor`)

- Reuses `desk_ml.llm_analyst` (Advisor, providers, `build_context` with secret scrubbing and prompt-injection
  filtering, budgets, `RecordedProvider` for replay) and `analysts.llm.LLMAnalyst` semantics.
- Consumes `boss:decisions` and `pos:updates`. Builds the compact context. Returns `ADVICE {decision_id, verdict:
  agree|disagree|abstain, reasons, cost_usd}` on `llm:advice`. Async, budgeted, off the hot path. Weight 0: the boss
  logs advice next to decisions and never waits for it. A future "LLM can veto" rule needs a founder decision, and even
  then it could only block entries, never place orders.
- In replay the advisor uses `RecordedProvider` keyed by `context_hash`, so replays never call a provider.

### 2.14 Health, metrics and alerts (process `health`)

Reuses `health.monitor.HealthMonitor` (recorder freshness, reconciliation, critical vetoes, disk, Telegram). Adds
`ENGINE_STATUS` heartbeat freshness (every 5 s), `FEED_STATUS`, consumer-group lag per stream, outbox backlog,
checkpoint age, and the metrics endpoint (section 5.4).

### 2.15 Splitting later (not needed for paper-live)

At the customer milestone the engine splits along an existing boundary. `runtime signal` runs features, strategies
and the boss, and publishes `boss:decisions`. `runtime exec --account <id>` runs risk, router, position manager and
ledger for one account group, consuming `md:*`, `boss:decisions` and `ctl:commands`. Both are the same kernel with a
different handler set. In paper-live both run in one process joined by the in-memory bus.

### 2.16 Forex later (`MarketAdapter`)

`config/v2/markets/<market>.yaml` plus a small `MarketAdapter` in `contracts/instruments.py`: calendar and sessions
(IST cash/F&O hours vs 24x5 FX), instrument model (option chain vs spot pair), tick size, lot model, expiry rules, and
the EOD flat rule. Strategies declare `markets`. The broker side is a new `BrokerAdapter` implementation. Nothing in
the kernel, risk engine or ledger changes. Crypto is dropped until the founder asks.

---

## 3. Data

### 3.1 Stores and what lives where

| Store | Holds | Writer | Readers | Survives restart? | Source of truth? |
|---|---|---|---|---|---|
| **SQLite, WAL** `data/state/aad.sqlite` | ledger (orders, order_events, fills, positions, trades, charges, risk_decisions, recon_runs), `founder_commands`, `engine_checkpoint`, `outbox`, `events` audit, `strategy_day_stats` | **engine only** (single writer) | gateway, health, nightly (read-only connections) | Yes (fsync on commit; `synchronous=FULL` for this file) | **Yes** for orders, fills, positions, money, commands |
| **Redis 7** (AOF `everysec`) | streams `md:*`, `sig:*`, `boss:*`, `oms:*`, `pos:*`, `ctl:*`, `health:*`, `llm:*`; hot hashes `hot:quote:<instrument>`, `hot:positions:<account>`, `hot:health`; rate-limit buckets | marketdata, engine outbox publisher, gateway (`ctl:commands` only), health | everyone | Mostly; **rebuildable** from tapes + SQLite | **No** |
| **Tapes** `data/tape/v2/YYYY-MM-DD/<stream>.jsonl(.gz)` | every `md:*` envelope exactly as the engine saw it | tape-writer | engine (replay/rehydrate), gates, forward evaluator, ETL | Yes | Yes for "what the market showed us" |
| **Recorder** `data/recon/<source>/YYYYMMDD.jsonl` | PR-001 independent capture (index, futures, chain, heavyweights, news, global) | data-recorder | ETL, research, `RecorderTapeSource` | Yes | Backup capture |
| **DuckDB warehouse** `data/warehouse/aad.duckdb` + `data/warehouse/parquet/<table>/date=YYYY-MM-DD/` | research and analytics copies of ledger, events, tapes, recorder, legacy benchmark, forward-evaluator results | nightly ETL only | research, founder reports, `WarehouseSource` for long backtests | Yes | **No** (always rebuildable) |

The warehouse is never read on the market-hours hot path. `.md` files are never read at runtime: pre-market compiles
configs into `config/v2/*.yaml` / JSON before 09:00.

### 3.2 Durable store recommendation

**SQLite-WAL now, Postgres at the customer milestone.**

- **Why SQLite now:** one engine process is the only writer; the ledger is already SQLite with append-only triggers;
  it is zero-ops on Mac and VPS; readers do not block the writer in WAL mode; and backup is `sqlite3 .backup` plus
  offsite copies.
- **When Postgres:** when a second process must write (several `exec` engines, the gateway taking customer
  "took-trade" records, billing), when we need point-in-time recovery, or with the first real customer account,
  whichever comes first.
- **Migration path (planned now, so the switch is boring):**
  1. All DDL lives in `packages/ledger/migrations/NNN_<name>.sql`, written in the SQL subset both engines accept
     (`TEXT`, `INTEGER`, `NUMERIC(18,4)` for money, ISO-8601 text timestamps, no SQLite-only functions in queries).
     Append-only triggers are the one per-engine file (`NNN_<name>.sqlite.sql` / `.pg.sql`).
  2. The `Ledger` class keeps its public methods (`record_order`, `record_fill`, `risk_snapshot`, ...) behind a
     `LedgerStore` protocol. The Postgres implementation is a second class, and the same test suite runs against both
     in CI.
  3. Cutover after close: stop the engine, `python -m ledger export --to postgres` (row-by-row copy with counts and a
     per-table checksum), flip `STATE_DSN`, start, reconcile against the broker. Rollback = flip `STATE_DSN` back; the
     SQLite file is untouched.
  4. Expand/contract only: a migration never drops or renames a column that the previous release reads.

### 3.3 Schema additions (migration `002_v2_core.sql`)

```sql
ALTER TABLE orders       ADD COLUMN account_id TEXT NOT NULL DEFAULT 'founder';
ALTER TABLE orders       ADD COLUMN signal_id TEXT;             -- correlation to sig:signals
ALTER TABLE orders       ADD COLUMN decision_id TEXT;
ALTER TABLE fills        ADD COLUMN fill_model TEXT;            -- depth | half_spread | ltp_slippage | broker
ALTER TABLE trades       ADD COLUMN account_id TEXT NOT NULL DEFAULT 'founder';
ALTER TABLE trades       ADD COLUMN strategy_id TEXT;
-- positions: new table keyed by account + instrument (old table stays for the legacy path)
CREATE TABLE positions_v2 (
  account_id TEXT NOT NULL, instrument_id TEXT NOT NULL, net_qty INTEGER NOT NULL,
  avg_price NUMERIC(18,4) NOT NULL, opened_at TEXT, strategy_id TEXT, exit_plan_json TEXT,
  updated_at TEXT NOT NULL, PRIMARY KEY (account_id, instrument_id));
CREATE TABLE engine_checkpoint (          -- one row per input stream per engine role
  role TEXT NOT NULL, stream TEXT NOT NULL, last_entry_id TEXT NOT NULL, input_seq INTEGER NOT NULL,
  session TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (role, stream));
CREATE TABLE outbox (                     -- transactional outbox; drained to Redis after commit
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, stream TEXT NOT NULL,
  envelope_json TEXT NOT NULL, created_at TEXT NOT NULL, published_at TEXT);
CREATE TABLE founder_commands (
  command_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, kind TEXT NOT NULL, args_json TEXT NOT NULL,
  actor TEXT NOT NULL, reason TEXT, received_ts TEXT NOT NULL, applied_ts TEXT, status TEXT NOT NULL,
  status_reason TEXT);
CREATE TABLE strategy_day_stats (
  session TEXT NOT NULL, strategy_id TEXT NOT NULL, version TEXT NOT NULL, stage TEXT NOT NULL,
  signals INTEGER, decisions INTEGER, trades INTEGER, gross_pnl NUMERIC(18,4), net_pnl NUMERIC(18,4),
  disabled_reason TEXT, PRIMARY KEY (session, strategy_id, version));
CREATE TABLE schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);
```

`outbox.published_at` is the only column ever updated in an append-only table; the no-update trigger on `outbox`
allows that column alone.

### 3.4 Event-sourced audit log

- **Inputs are journaled:** market data in tapes; founder commands in `founder_commands`; broker order updates and
  fills in `order_events`/`fills`; the basket hash in `BASKET_LOADED`. Together with the code version and config hash
  (in `ENGINE_STATUS`), they are enough to re-run a session and get the same decisions.
- **Outputs are audited:** every envelope the engine publishes also goes to the append-only `events` table (the merged
  `EventAuditLog`, now inside the same SQLite file and transaction).
- **Correlation:** every envelope carries `correlation_id` (the signal id for a trade's whole life) and `causation_id`
  (the envelope that caused it). One query rebuilds the chain for the decision trace in the UI: bar, then feature
  values, then signal, decision, risk decision, order, fills, exits, trade.

### 3.5 Exactly how state survives restarts

**Normal operation (per input envelope, engine thread):**

1. Read the next input (Redis `XREADGROUP` for group `engine`, or the tape iterator).
2. Skip it if `event_id` was already processed (watermark `engine_checkpoint.input_seq` plus the event id kept in the
   same transaction).
3. Run handlers. All ledger writes, `engine_checkpoint` updates and `outbox` rows happen in **one SQLite
   transaction**. Broker calls happen **after** the order row is committed in state `NEW`.
4. Commit, then `XACK` the input, then the outbox publisher drains new rows to Redis (at least once; consumers dedupe on
   `event_id`).

**Crash anywhere, then restart (`runtime/recovery.py`), in this order:**

1. **Open and check the store.** Refuse to start if `schema_version` is newer than the code knows (a rollback without
   a compatible migration). Run pending migrations only when started with `--migrate` (the deploy script does this).
2. **Load book state** from the ledger: open orders (`NEW`, `SUBMITTED`, `PARTIAL`), `positions_v2`, today's trades.
   Risk state needs no step because `RiskEngine` rebuilds it from the ledger on every check.
3. **Broker reconciliation** (`brokers.reconcile.reconcile`):
   - An order in `NEW` with no broker id: if its decision is older than 30 s, mark it `CANCELLED
     (STALE_ON_RESTART)`; else look it up by correlation id and adopt it, or submit it once.
   - `needs_lookup` orders: look up by correlation id and adopt.
   - Positions vs broker positions. Any mismatch writes `recon_runs.ok = 0`, which already blocks entries
     (`RECON_MISMATCH`) until resolved, and raises a CRITICAL alert. Exits stay allowed.
   - Paper: `PaperBroker` is rebuilt from the ledger (open orders, including resting protective stops and positions),
     so paper and live recover the same way.
4. **Rehydrate derived state deterministically.** Feed today's journaled inputs (tape v2 for today, founder commands,
   broker updates) through the same kernel up to the checkpoint in **rehydrate mode**: the router is a no-op, and
   every intent it would have sent is compared with the ledger by `client_order_id`. A mismatch means a
   non-determinism bug: entries are blocked for the session, and a CRITICAL `REHYDRATE_MISMATCH` alert is raised.
   Features, strategy state and bar builders come back exactly as they were. No strategy state snapshots to maintain.
5. **Resume live:** process the Redis consumer-group pending list (`XPENDING`/`XCLAIM`), then new entries. Publish
   `ENGINE_STATUS {status: READY, restart: true, recovered_orders, recon_ok}`.
6. **Budget:** restart to READY in under 60 s for a full session (one day of 1-minute bars and chain snapshots
   replays in seconds; the gate measures it).

**Redis lost (flush or crash):** the engine blocks entries (feed status unknown). The marketdata service republishes;
the gateway rebuilds hot hashes from `GET /v2/snapshot`, which the engine serves from SQLite. Positions stay protected
by broker-side stops. Nothing durable was in Redis only.
**SQLite lost or corrupt:** restore from the latest backup (section 5.5), then reconcile against the broker. For
paper, the broker is the paper broker, so paper history after the last backup is lost; for live, the broker is the
truth for open positions. This is why backups and the restore drill are a paper-live requirement.

---

## 4. Correctness by design

### 4.1 One code path

```python
# packages/runtime/src/runtime/kernel.py (shape, not final code)
class Engine:
    def __init__(self, source: EventSource, clock: SimClock, bus: MemoryBus, handlers: list[Handler],
                 store: LedgerStore, mode: Literal["run", "rehydrate"]) -> None: ...
    def run(self) -> RunSummary:
        for env in source:                      # ordered by (available_ts, stream_priority, seq)
            clock.advance_to(env.available_ts)  # monotonic; raises on time going backwards
            with store.transaction():
                bus.publish_envelope(env)       # handlers run synchronously, depth-first (MemoryBus today)
                store.checkpoint(env)
            source.ack(env)
```

| Use | `EventSource` | Broker | Clock |
|---|---|---|---|
| Unit / integration tests | `ListSource` (fixtures) | `PaperBroker` | `SimClock` |
| Historical backtest (years) | `WarehouseSource` (1-minute bars and chain from the warehouse, converted to envelopes with conservative `available_ts`) | `PaperBroker(HalfSpreadFill)` | `SimClock` |
| Tape replay | `TapeSource(data/tape/v2/<day>)` or `RecorderTapeSource(data/recon)` | `PaperBroker(DepthFill)` | `SimClock` |
| Live-like dry run | `RedisSource` fed by `marketdata --replay <day>` at 1x or 10x | `PaperBroker(DepthFill)` | `SimClock` driven by `available_ts` |
| Paper-live | `RedisSource` fed by Dhan | `PaperBroker(DepthFill)` | same |
| Live (founder only, later) | `RedisSource` | `DhanBroker` | same |

The clock is a `SimClock` in every row: live simply gets `available_ts` from real receipt times. `LiveClock` exists
only for I/O timeouts and liveness checks outside the decision path.

### 4.2 No-look-ahead contracts

1. **Envelope contract:** `available_ts ≥ event_ts` for every input, and sources emit in non-decreasing
   `available_ts`. Enforced by the kernel (it raises).
2. **Bar contract:** a bar is published only when closed; `available_ts ≥ bar.end`. For recorder or warehouse bars,
   `available_ts = bar.end + finalize_delay` (1.5 s) unless a real receipt time exists.
3. **Chain/OI contract:** `available_ts` = receipt time of the snapshot. Features that use OI read the last snapshot
   with `available_ts < decision minute start` (strictly before).
4. **Daily inputs:** previous close, ATR14, HAR forecast and intermarket closes are computed in pre-market from data
   up to yesterday, and published as `PRE_MARKET_SUMMARY` with `available_ts` = the run time (before 09:15).
5. **Feature access:** `FeatureView(strict=True)` raises `LookAheadError` on any value with
   `available_ts > clock.now()`.
6. **Decisions:** `Signal.decision_ts == clock.now()` and the fill model only uses quotes with
   `available_ts ≥ order available_ts + latency`.

**Tests that enforce it (in the merge gate):**

- **Truncation invariance:** run the engine on a tape cut at time T and on the full tape; every signal, decision and
  order with `decision_ts ≤ T` must be identical. Run at 20 random T per fixture day.
- **Future poisoning:** replace every input after T with random garbage (prices, OI, NaNs); decisions up to T must
  not change.
- **Bar visibility:** property test: for random tick streams, no `BAR_CLOSED` has `available_ts < end`, and no
  strategy callback ever sees a bar whose `end > clock.now()`.
- **Strict view:** the whole gate runs with `strict=True`; one `LookAheadError` fails the build.
- **OI lag:** a fixture where OI jumps inside the decision minute; the E1-style feature must not see it.

### 4.3 Idempotent order handling

- `client_order_id = "aad" + sha256(account_id | signal_id | leg)[:24]` (27 chars, `[a-z0-9]`, fits Dhan
  `correlationId`). The same input gives the same id, so replay, rehydrate and retries are safe.
- The ledger's `orders.client_order_id` primary key refuses a second row. `PaperBroker._accept` already returns the
  existing order for a repeated id, and `DhanBroker._submit` never sends the same id twice (lookup first).
- The risk engine rejects a repeated `client_order_id` (`used_client_order_ids`) and a repeated fingerprint within
  `idempotency_seconds`.
- Every consumer dedupes on `event_id`. Engine-produced `event_id = sha256(role | input_event_id | n)[:32]`, so a
  re-run produces the same ids and the outbox `UNIQUE(event_id)` refuses duplicates.
- Founder commands dedupe on the client `command_id` (as in PR #18).

### 4.4 Message schemas

**Envelope v2** extends the merged `events.schema.Event` without breaking it (old fields kept; new fields optional in
the reader, required in the writer):

```json
{
  "v": 2,
  "event_type": "BAR_CLOSED",
  "event_id": "5f0c2d6e8a1b4c3d9e7f6a5b4c3d2e1f",
  "stream": "md:bars:1m",
  "source": "marketdata",
  "event_ts": "2026-09-28T10:01:00.000+05:30",
  "available_ts": "2026-09-28T10:01:01.512+05:30",
  "timestamp": "2026-09-28T10:01:01.512+05:30",
  "account_id": null,
  "correlation_id": null,
  "causation_id": null,
  "payload": { }
}
```

New `EventType` values: `TICK`, `DEPTH_QUOTE`, `BAR_CLOSED`, `CHAIN_SNAPSHOT`, `CLOCK`, `FEED_STATUS`, `SIGNAL`,
`DECISION`, `RISK_DECISION`, `ORDER_UPDATE`, `FILL`, `COMMAND_ACK`, `ADVICE`, `ENGINE_STATUS`, `BASKET_LOADED`.
Existing values stay (`PRE_MARKET_SUMMARY`, `POSITION_UPDATE`, `POSITION_CLOSED`, `ENTRY_VETOED`, `HEALTH_ALERT`,
`FOUNDER_COMMAND`, `REGIME_LABEL`, `BOSS_SHADOW`, ...), so the legacy path keeps working.

**Instrument id:** `NSE_FNO:NIFTY:2026-09-29:24500:CE`, `NSE_IDX:NIFTY`, `BSE_FNO:SENSEX:2026-10-01:81000:PE`,
`FX:EURUSD` (later). A broker security-id map comes from the instrument master and is loaded at session start.

**Payloads (JSON; numbers are floats; times are ISO-8601 IST):**

```json
// TICK  (md:ticks)
{"instrument_id":"NSE_IDX:NIFTY","ltp":24512.35,"ltq":0,"volume":null,"oi":null,"exchange_ts":"2026-09-28T10:00:59.870+05:30"}

// DEPTH_QUOTE  (md:depth)
{"instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","bid":151.10,"bid_qty":1950,"ask":151.35,"ask_qty":1300,"ltp":151.20,"oi":4412350}

// BAR_CLOSED  (md:bars:1m)
{"instrument_id":"NSE_IDX:NIFTY","tf":"1m","start":"2026-09-28T10:00:00+05:30","end":"2026-09-28T10:01:00+05:30",
 "o":24498.1,"h":24515.0,"l":24496.4,"c":24512.35,"v":null,"n_ticks":57,"gap":false,"late_ticks":0}

// CHAIN_SNAPSHOT  (md:chain)
{"underlying":"NIFTY","expiry":"2026-09-29","spot":24512.35,"strikes":[
  {"strike":24500,"ce":{"ltp":88.2,"bid":88.1,"ask":88.4,"oi":5123400,"oi_chg":84500,"iv":11.8,"volume":1234567},
                  "pe":{"ltp":76.9,"bid":76.8,"ask":77.1,"oi":4987200,"oi_chg":-22100,"iv":12.1,"volume":1102345}}]}

// CLOCK  (md:clock)
{"session":"2026-09-28","phase":"MARKET","minute":"10:01"}

// FEED_STATUS  (md:status)
{"status":"STALE","instrument_id":"BSE_IDX:SENSEX","since":"2026-09-28T11:14:03+05:30","gap_s":7.2}

// SIGNAL  (sig:signals)
{"signal_id":"sg_r8e1_nifty_20260928_1001_0","strategy_id":"R8-E1-COIL-SIDE","version":"1.0.0","params_hash":"30416a4a…",
 "stage":"shadow","underlying":"NIFTY","side":"CE","strike_rule":"ITM100","decision_ts":"2026-09-28T10:01:01.512+05:30",
 "confidence":0.63,"exit_plan":{"stop":{"kind":"underlying","price":24488.0},"target":{"kind":"underlying","price":24531.0},
 "time_stop_s":900,"flat_by_ist":"15:15","partials":[],"trail":null,"protective_stop":{"kind":"premium","price":118.0}},
 "reasons":["COIL_AGE_7M","P_UP_GE_Q90","D_16PTS"],"features":{"p_up":0.63,"box_d":16.0,"em30":27.1}}

// DECISION  (boss:decisions)
{"decision_id":"dc_nifty_20260928_1001","underlying":"NIFTY","decision":"ENTER","signal_ids":["sg_..."],
 "instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","lots":14,"lot_size":65,"limit_price":151.35,
 "sizing":{"volsize":17,"caplots":14,"basket_max":25},"holds":[],"basket_hash":"b7e1…","shadow":{"regime":"trend_up"}}

// RISK_DECISION  (oms:risk)
{"client_order_id":"aad3f9…","action":"ENTRY","approved":false,"reason_code":"MAX_LOSS_PER_TRADE","reason":"risk ₹31,200 exceeds max_loss_per_trade ₹30,000","critical":false,"ticket_risk_inr":31200.0}

// ORDER_UPDATE  (oms:orders)
{"client_order_id":"aad3f9…","broker_order_id":"PAPER-aad3f9…","account_id":"founder","from":"SUBMITTED","to":"FILLED","reason":"fill 910 @ 151.35","purpose":"ENTRY"}

// FILL  (oms:fills)
{"client_order_id":"aad3f9…","qty":910,"price":151.35,"fill_model":"depth","quote_available_ts":"2026-09-28T10:01:01.800+05:30","charges_inr":null}

// POSITION_UPDATE  (pos:updates)
{"position_id":"ps_…","account_id":"founder","instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","net_qty":910,"avg_price":151.35,
 "mark":153.10,"unrealized_inr":1592.5,"stop":{"kind":"underlying","price":24488.0},"protective_order":"aad…-S","strategy_id":"R8-E1-COIL-SIDE"}

// POSITION_CLOSED  (pos:updates)
{"position_id":"ps_…","exit_reason":"TIME_EXIT","gross_inr":1820.0,"charges_inr":212.4,"net_inr":1607.6,"held_s":900,"trade_id":"tr_…"}

// FOUNDER_COMMAND  (ctl:commands)
{"command_id":"cmd_01J…","account_id":"founder","kind":"CUT_LOSS","args":{"position_id":"ps_…"},"actor":"founder","reason":"news","confirm_token":"…"}

// COMMAND_ACK  (ctl:acks)
{"command_id":"cmd_01J…","status":"applied","applied_ts":"2026-09-28T11:02:14.100+05:30","reason":null}

// ADVICE  (llm:advice)
{"decision_id":"dc_…","verdict":"disagree","reasons":["event day: RBI 11:30"],"provider":"openai","prompt_version":"llm-analyst-v1","cost_usd":0.0009,"context_hash":"…"}

// ENGINE_STATUS  (health:engine)
{"role":"engine","status":"READY","session":"2026-09-28","code_version":"<git sha>","config_hash":"…","basket_hash":"…","restart":false,"input_lag_ms":12}
```

JSON Schemas for every payload live in `packages/contracts/src/contracts/schemas/*.json`. Writers validate in tests
and at trust boundaries (gateway input, broker responses); the hot path trusts in-process dataclasses.

---

## 5. Production

### 5.1 Docker Compose (local and VPS)

`deploy/docker/compose.yaml` (shared) plus `compose.vps.yaml` (TLS proxy, restart policies, resource limits,
log rotation). One image: `aad-python:<git sha>` (Python 3.11 slim, `uv` lockfile install, non-root user, read-only
root filesystem, `data/` as a volume). The web UI is built into a small static image served by Caddy.

```yaml
services:
  redis:       { image: redis:7-alpine, command: ["redis-server","--appendonly","yes","--appendfsync","everysec"],
                 volumes: ["redis:/data"], healthcheck: {test: ["CMD","redis-cli","ping"]} }
  marketdata:  { image: aad-python:${SHA}, command: ["python","-m","runtime","marketdata","--mode","${MD_MODE:-replay}"],
                 env_file: [/etc/aad/aad.env], secrets: [dhan_access_token], depends_on: [redis] }
  engine:      { image: aad-python:${SHA}, command: ["python","-m","runtime","engine","--role","all"],
                 volumes: ["state:/app/data/state","tape:/app/data/tape:ro"], depends_on: [redis], stop_grace_period: 30s }
  gateway:     { image: aad-python:${SHA}, command: ["python","-m","runtime","gateway"], ports: ["127.0.0.1:8000:8000"],
                 volumes: ["state:/app/data/state:ro"] }
  health:      { image: aad-python:${SHA}, command: ["python","-m","runtime","health"],
                 volumes: ["state:/app/data/state:ro"] }
  llm-advisor: { image: aad-python:${SHA}, command: ["python","-m","runtime","llm-advisor"], profiles: ["llm"] }
  recorder:    { image: aad-python:${SHA}, command: ["python","-m","data_recorder"], profiles: ["live-data"] }
  web:         { image: aad-web:${SHA} }
  # nightly: `docker compose run --rm nightly <job>` from a systemd timer (not a long-running service)
secrets:
  dhan_access_token: { file: /etc/aad/secrets/dhan_access_token }
```

Profiles: default = replay (no credentials needed anywhere; runs on a laptop and in CI). `live-data` = Dhan market
data (user box or VPS only). There is **no** live-orders profile. Live orders stay behind the existing three-part gate
(risk mode, `ALL_ABOUT_DHAN_LIVE_CONFIRM`, fresh risk approval), plus a founder confirm in the UI.

The founder's Mac can run the same compose file (Docker Desktop or OrbStack). A no-Docker path (`uv run python -m
runtime <service>` per process, plus a local Redis) is kept working for development, because
`02_TARGET_ARCHITECTURE.md` promised Docker would be optional.

### 5.2 Config and secrets

- **Config** (in git, no secrets): `config/v2/engine.yaml` (holds, windows, budgets, fill model, stream names),
  `config/v2/markets/india.yaml` (sessions, half-spread table, lot source = instrument master), registry and baskets,
  plus the existing `risk_limits.yaml`, `charges.yaml`, `regime.yaml`, `llm_analyst.yaml`. `ENGINE_STATUS` publishes a
  `config_hash`, so every trade is tied to the config that made it.
- **Secrets** (never in the repo; the repo is public): now, `/etc/aad/aad.env` (mode 600, owner `aad`) and
  `/etc/aad/secrets/*` files mounted as Docker secrets. Names only in `.env.example`. Dhan token refresh runs as a
  scheduled job that writes the secret file and signals `marketdata` to reload. Later (customer milestone), move to a
  real secret store (SOPS + age in a private ops repo, or HashiCorp Vault / 1Password Connect), and keep per-customer
  broker tokens encrypted at rest with a key held outside the database.
- **Guards:** the secret scan from PR #16 (`scripts/ci/scan_repo.py`) runs in CI; logs pass through the existing
  redaction (`dhan_client.logging_util.redact_url`, `llm_analyst.context.scrub`); envelopes never contain credentials.

### 5.3 CI (GitHub Actions)

Salvage PR #16's workflow (hash-pinned `requirements/ci.txt`, local packages `--no-deps`, pytest-socket
localhost-only, secret scan). Jobs on every PR:

| Job | What | Blocks merge |
|---|---|---|
| `lint` | `ruff check` + `ruff format --check` on new packages; legacy excluded | yes |
| `types` | `mypy --strict` on `contracts`, `runtime`, `oms`, `strategies`, `indicators`, `marketdata`, `control`; non-strict elsewhere | yes (new packages) |
| `unit` | pytest, Python 3.11 and 3.13, no network | yes |
| `integration` | engine + in-memory bus; engine + real Redis (service container) | yes |
| `no-lookahead` | truncation invariance, future poisoning, bar visibility, strict view (section 4.2) | yes |
| `determinism` | same tape twice gives identical output hash; rehydrate equals run | yes |
| `faults` | fault matrix (section 6.2) | yes |
| `perf` | budgets (section 6.3) on the CI runner, with a 2x headroom factor | yes |
| `dry-run` | compose up (replay profile), play 1 fixture day through Redis, compare to in-process replay | yes (nightly on main; on PRs touching runtime/oms/marketdata/events) |
| `frozen-legacy` | sha256 manifest of the frozen legacy files must match | yes |
| `docs` | `python -m docs_auditor` when docs/requirements change | yes |
| `image` | build `aad-python` and `aad-web`, SBOM, `pip-audit` | yes |

### 5.4 Observability

- **Logs:** stdlib `logging` with a JSON formatter (no new dependency). Fields: `ts`, `level`, `service`, `role`,
  `session`, `account_id`, `event_id`, `correlation_id`, `client_order_id`, `msg`. Stdout, collected by Docker with
  rotation (`max-size=50m`, `max-file=10`); journald on the VPS.
- **Metrics:** `prometheus-client` (one small dependency, added in the health ticket), exposed on each service's
  `127.0.0.1:91xx/metrics`: tick→bar latency, bar→decision latency, risk check latency, decision→paper-ack latency,
  consumer lag per stream, outbox backlog, checkpoint age, vetoes by code, orders by state, open positions, realised
  and unrealised P&L, strategy exceptions, feed reconnects, late ticks, LLM spend. No Prometheus server is required for
  paper-live: `health` scrapes them itself and alerts. Grafana is optional later.
- **Alerts** (health → founder page + Telegram, deduped, with a recovered message): feed DOWN > 10 s or STALE in
  market hours; engine heartbeat missing > 15 s; consumer lag > 5 s; outbox backlog > 100; reconciliation mismatch;
  REHYDRATE_MISMATCH; any CRITICAL risk veto; strategy disabled; order stuck in SUBMITTED > 30 s; protective stop
  missing on an open position; disk < 5 GB; backup older than 26 h; Dhan token expires within 2 h.

### 5.5 Deployment, backup and rollback

- **VPS:** Ubuntu 24.04 LTS in an Indian region (low latency to Dhan), 2 vCPU / 4 GB minimum, Docker Engine,
  `deploy/systemd/aad.service` runs `docker compose up`, Caddy for TLS, firewall allows 443 only, SSH by key. Founder
  console reachable over Tailscale/WireGuard only until customer auth exists (section 5.6).
- **Deploy** (`deploy/scripts/deploy.sh <sha>`): pull images tagged by git sha, refuse during 09:00–15:35 IST unless
  `--emergency`, back up SQLite, run migrations (expand-only), restart services, wait for `ENGINE_STATUS READY` and
  `recon_ok`, else roll back automatically.
- **Rollback:** `deploy.sh <previous sha>`. Expand-only migrations mean the previous release runs on the new schema.
  The engine refuses to start if the schema is newer than any version it knows. That is the one case that needs a
  restore, and the deploy script blocks it by never shipping a contract migration in the same release as its expand.
- **Backups** (paper-live requirement): `sqlite3 .backup` every 15 minutes during market hours and at EOD, copied
  offsite with `restic` to object storage; Redis AOF daily; tapes synced nightly. A monthly **restore drill** (restore
  to a scratch VM, replay the day, compare output hashes) is on the runbook.
- **Runbook** (`deploy/README.md`): start, stop, deploy, rollback, restore, token refresh, out-of-band kill and
  flatten, and "what to do when" for each alert.

### 5.6 Multi-tenant readiness

| Capability | Design | Needed for paper-live (founder only) | Needed before the first real customer | Later |
|---|---|---|---|---|
| Account model | `accounts(account_id, kind founder\|customer, broker, status)`; `account_id` on every ledger row and envelope | single `founder` account | yes | — |
| Isolation | per-account `RiskEngine`, ledger partition, positions, streams `pos:<account>`; tests that account A can never read or affect B | — | yes (tests in the gate) | Postgres row-level security |
| Signal vs execution | shared `runtime signal`; per-account-group `runtime exec` (section 2.15) | one process | yes | horizontal scale |
| Auth | gateway: founder and customer logins, short-lived JWT (`pyjwt`), refresh tokens, argon2 passwords (stdlib `hashlib.scrypt` acceptable), 2FA for founder | founder console over Tailscale + localhost-only controls (PR #18) | yes | SSO |
| Authorisation | role-scoped channels and routes; founder controls only for the `founder` role; customers only their own account | — | yes | fine-grained roles |
| Rate limits | Redis token bucket per token and per IP: REST 10/s, WS subscribe 5/s, commands 1/s | — | yes | per-plan quotas |
| Broker credentials per customer | encrypted at rest, key outside DB, never logged; per-account `DhanBroker` | — | yes (only if we execute for them) | KMS |
| Durable store | Postgres (section 3.2) | SQLite-WAL | yes | replicas / PITR |
| Audit | event log + command log per account, exportable | yes (exists) | yes | customer-visible export |
| Compliance | SEBI rules for research analysts / algo providers, customer T&Cs, risk disclosures (`docs/COMPLIANCE.md`) | — | **founder/legal sign-off required** | — |
| TLS, backups, restore drill | section 5.5 | yes | yes | multi-region |
| Customer surface | `signals:public` channel with customer-safe copy | — | yes | mobile push |

---

## 6. Legacy and the new merge gate

### 6.1 What is reused, wrapped, rebuilt or frozen

| Component | Merged in | V2 verdict | How |
|---|---|---|---|
| Data recorder (`packages/data-recorder`) | PR #8 | **Reuse as-is** | Keeps running as an independent backup capture. `RecorderTapeSource` reads its files for replay |
| Dhan client (`packages/dhan-client`) | earlier | **Reuse as-is** | The only Dhan HTTP/WS client (no second client). `feed.MarketFeedCollector` inside `marketdata` |
| Broker adapter + order state machine + `PaperBroker` + `DhanBroker` + `reconcile` | PR #10 | **Reuse + wrap** | Add `clock=` injection, pluggable fill models, paper state rebuilt from the ledger, protective stop helper. The live gate is unchanged |
| Risk engine | PR #10 | **Reuse + wrap** | Engine clock always passed; one instance per account; add `FEED_STALE`, `STRATEGY_DAILY_LOSS` |
| Health monitor | PR #10 | **Reuse + extend** | New checks, metrics endpoint, alert rules |
| Ledger + charges | PR #10 | **Reuse + extend** | Migrations, `account_id`, `positions_v2`, checkpoint, outbox, commands |
| Event bus (`MemoryBus`, `RedisStreamsBus`, `EventAuditLog`) | PR #12 | **Reuse + extend** | Envelope v2 (compatible), stream per topic, consumer groups with `XACK` after commit, outbox publisher |
| Analyst interface (`Analyst`, `Vote`, `AnalystRoom` timeouts) | PR #12 | **Reuse interface** | For advisory and filter analysts outside the decision path |
| `analysts/shadow.py` helpers | PR #13 | **Reuse** | As pure feature functions in `indicators/adapters.py` |
| 22 legacy analysts (`analysts/legacy.py` → `picker.collect_analyst_votes`) | PR #12 | **Frozen reference** | Only inside the legacy benchmark |
| Boss (`boss/orchestrator.py`) | PR #12 | **Frozen; rebuilt** as `boss/selector.py` | The old one calls `paper_scalp.step_decide` |
| Desk (`desk/executor.py`) | PR #12/#14 | **Frozen; rebuilt** as `oms/` | Reuse `desk/paper.py` helpers (`option_symbol`, `ledger_exit_reason`) and the fail-safe MTM rule |
| `desk_ml.event_path`, `event_parity` | PR #12 | **Frozen** | Parity with the old engine is no longer a gate |
| LLM analyst (`desk_ml/llm_analyst`, `analysts/llm.py`) | PR #17 | **Reuse** | Runs in `llm-advisor`, advice only, `RecordedProvider` in replay |
| Regime labeller, adaptive weights, intermarket (`desk_ml/regime`) | PR #21 | **Reuse** | Labeller as a feature; weights and overlay in boss shadow (`BOSS_SHADOW`) |
| Desk/Founder UI (`apps/web`), read-only feed (`apps/api`) | PR #15 | **Reuse + rewire** | UI reads `/v2/ws`; old routes stay read-only until switched |
| `paper_scalp.py`, `picker.py` | — | **Frozen benchmark** | No fixes, no features. Run nightly as `LEGACY-BENCH` on the same tapes |

**Open draft PRs (recommendation; the founder decides):**

- #16 (reliability core): salvage the CI workflow, secret scan and fault-sim harness ideas. Its goldens become the
  frozen benchmark's regression check. Do not keep adding behaviour to the live loop.
- #18 (founder controls): port the command log design (append-only, idempotent `command_id`, confirm tokens,
  exit-command spool) and `book.py` semantics into `packages/control`. Do not extend the old engine hooks.
- #19 (warehouse ETL, pre-market, backtest gate): keep `premarket` and the ETL structure, and retarget the ETL sink to
  DuckDB. Replace its expected-results gate with the v2 gate.
- #20 (cost realism): port the BSE fee, stale-quote guard and tick rounding into `brokers/fills.py` and
  `ledger.charges`. The `paper_scalp.py` hooks are not needed once the legacy engine is frozen.
- #23 (ML shadow logging): it edits `paper_scalp.py`. Under the freeze it should merge only if it is
  benchmark-neutral; its shadow schema can feed the forward evaluator.
- #22, #24 (research docs): inputs to strategy plugins; no engine change.

### 6.2 The new merge gate (replaces "byte-identical to the old engine")

A PR that touches `runtime`, `oms`, `strategies`, `indicators`, `marketdata`, `events`, `brokers`, `risk-engine`,
`ledger` or `control` must pass all of these in CI:

1. **Unit tests** for the changed package (pure functions, state machines, schemas).
2. **Integration tests:** engine with the in-memory bus and with real Redis, over fixture days: signal → decision →
   risk → order → fill → exits → trade → ledger, including founder commands.
3. **Fault tests** (each asserts invariants, not P&L):

   | Fault | Expected |
   |---|---|
   | `kill -9` engine between order row commit and broker submit | restart adopts or cancels, never double-sends |
   | `kill -9` after broker fill, before ledger fill write | restart reconciles the fill from the broker |
   | Redis down 30 s mid-session | entries blocked; exits via protective stops; resume without duplicates |
   | Websocket disconnect / reconnect storm | `FEED_STATUS` DOWN/UP; no bars built across the gap; entries blocked while down |
   | Duplicate and out-of-order stream delivery | deduped; kernel rejects time going backwards from one source |
   | Stale depth (no quote for 60 s) | fill model falls back and records it; entries on that strike blocked |
   | Broker timeout on submit | `needs_lookup` → adopt by correlation id |
   | Broker rejects exit | retry with backoff, CRITICAL alert, protective stop still resting |
   | Ledger write failure | risk vetoes (existing), engine halts entries |
   | Corrupt founder command | rejected with reason; exit commands still apply |
   | Strategy raises / exceeds budget | that strategy disabled for the session; others unaffected |
   | Clock skew between processes | decisions unchanged (event time) |

4. **No-look-ahead tests** (section 4.2).
5. **Determinism:** same tape twice gives the same output hash; rehydrate equals run; the live-like dry run over
   Redis equals the in-process replay (decisions, orders, fills compared field by field).
6. **Performance budgets** (section 6.3).
7. **Live-like dry run on recorded data:** compose with `marketdata --replay <day>` at 1x for one fixture hour and at
   10x for a full day, real processes and Redis. Pass = zero invariant violations, zero duplicate orders, every open
   position has a protective stop, EOD flat by 15:15, reconciliation clean.

**Invariants checked after every test run:** ledger positions equal broker positions; every fill has an order in
FILLED/PARTIAL; no order id sent twice; realised P&L equals the sum of trades; no entry after cutoff or under a hold;
no position open after `flat_by_ist`; every `DECISION ENTER` has exactly one `RISK_DECISION`; every envelope has
`available_ts ≥ event_ts`.

**Recorded tapes are test data, not a P&L target.** The gate never asserts a rupee total. P&L is measured and
reported (warehouse, forward evaluator), and strategies are judged by the Round 8 FWD-BAR and 09's five-pass, not by
CI.

### 6.3 Performance budgets

| Path | Budget | Measured in |
|---|---|---|
| Dhan tick → `md:ticks` publish | < 20 ms p99 | marketdata |
| Last tick → `BAR_CLOSED` publish | < finalize_delay + 50 ms p99 | marketdata |
| `BAR_CLOSED` → `DECISION` (all strategies + boss) | < 100 ms p99 | engine |
| Risk check | < 10 ms p99 (existing budget) | engine |
| `DECISION` → paper ack | < 50 ms p99 | engine |
| `DECISION` → Dhan ack (later) | < 500 ms p95 (existing budget) | engine |
| Engine throughput, tape replay | one full session (bars + chain + depth for the basket) in < 60 s | CI perf |
| Restart → READY | < 60 s | CI faults |
| Envelope → UI websocket | < 1 s p99 | gateway |
| Engine RSS | < 1.5 GB | health |

### 6.4 The frozen benchmark

- Files: `paper_scalp.py`, `picker.py`, `desk_ml/event_path.py`, `desk_ml/event_parity.py`, `boss/orchestrator.py`,
  `desk/executor.py`, `analysts/legacy.py`. Their sha256 values go into `config/legacy_frozen.sha256`, and the CI job
  `frozen-legacy` fails on any change. Allowed changes: security fixes and deletion, with the manifest updated in the
  same PR and a founder-visible note.
- `python -m runtime bench-legacy --day <d>` runs `replay_paper_scalp` on the same day's recorder tape and writes
  its trades to `warehouse.bench_legacy_trades`. The founder page shows "new stack vs legacy benchmark" as
  information, never as a target to match.

---

## 7. Interfaces the build tickets code against (summary)

```python
# contracts
class Clock(Protocol):      def now(self) -> datetime: ...
class SimClock(Clock):      def advance_to(self, ts: datetime) -> None: ...   # monotonic
class EventSource(Protocol):
    def __iter__(self) -> Iterator[Envelope]: ...
    def ack(self, env: Envelope) -> None: ...

# indicators
class FeatureView(Protocol):
    def get(self, name: str, instrument_id: str, tf: str = "1m") -> FeatureValue | None: ...

# strategies (section 2.5): Strategy, StrategyMeta, Signal, ExitPlan, load_registry(), basket_for()

# boss
class Boss(Protocol):
    def on_signals(self, signals: list[Signal], ctx: DecisionContext) -> list[Decision]: ...

# risk (existing): RiskEngine.check_entry(intent, now) / check_exit(intent, action, now) / check_flatten(now)

# oms
class OrderRouter(Protocol):
    def submit(self, decision: Decision, account: Account) -> Order | Veto: ...
    def exit(self, position: PositionV2, reason: str) -> Order: ...
class PositionManager(Protocol):
    def on_market(self, env: Envelope) -> list[ExitRequest]: ...
    def on_fill(self, fill: Fill) -> None: ...

# brokers (existing BrokerAdapter) + FillModel
class FillModel(Protocol):
    def price(self, order: Order, quote: DepthQuote | None, ltp: float, now: datetime) -> tuple[float, str] | None: ...

# ledger
class LedgerStore(Protocol):  # existing Ledger methods + these
    def transaction(self) -> ContextManager[None]: ...
    def checkpoint(self, env: Envelope) -> None: ...
    def outbox_put(self, env: Envelope) -> None: ...
```

---

## 8. Handoff block

- **Accepted:**
  - The founder direction: new stack, old engine frozen as reference only, paper only, VPS-ready.
  - Round 8 (PR #22) consequences for the platform: entry edge is the binding constraint; strategies must be
    forward-testable from recorded data; depth fills are the primary paper cost model with FC-MEAS as fallback; global
    skips live in config.
  - Every merged safety component, reused or wrapped (section 6.1).
  - The existing performance budgets from `04_MIGRATION_PLAN.md`.
- **Rejected:**
  - Byte-identical parity with the old engine as a merge gate (it protects losing behaviour).
  - A microservice per role on the hot path (network hops and lost determinism for no gain at this scale).
  - Postgres on day 1 (single writer; SQLite-WAL is enough until customers), and MySQL or embeddings (counsel
    rejected them).
  - Exit tuning as a work item (Round 8 §4.3).
  - LLM on the decision path.
- **UNKNOWN / DATA_INSUFFICIENT:**
  - Dhan depth availability and update rate for every traded strike (the depth recorder starts 28 Sep).
  - OI update cadence (it decides whether E1's lag rule is stale).
  - Whether Dhan's feed exposes exchange timestamps for every packet type; if not, `event_ts` = receipt time.
  - Dhan access-token lifetime and refresh flow for unattended VPS runs (`.env.example` note: VERIFY).
  - SEBI registration path for a signal/algo product (founder/legal).
  - The final shape of the separately built registry/basket module (only the contract in section 2.5 is assumed).
- **Cross-team citations:** 04 `SIGNAL_STAGING.md` (5m indicators confirm or kill only); 05 `CUSTOMER_TALK.md`
  (customer copy); 06 `EVENT_MEMORY.md` (event days held); 09 five-pass before any paper or customer book. KEEP_ALL
  untouched: no `STRAT-*` is deleted or relabelled; new strategy ids are research ids or `MIX-*`, never `STRAT-015+`.

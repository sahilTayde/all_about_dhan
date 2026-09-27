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
  the router and position manager execute. Entries are marketable next-bar orders (round 10 found no
  entry-location rule), and exits are per-strategy primitives with no hard-coded tight cancels. Recording ≤ 1 s bid/ask depth starts first, because it cannot be
  backfilled and short stops cannot be tested without it. The first milestone is **paper-live on the new stack**: real Dhan market
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
   ┌───────────────────────────────▼────────────────────────────────────────────────────────┐
   │ engine  (ONE process, single-threaded kernel, in-process MemoryBus)                    │
   │                                                                                        │
   │  features ─▶ strategy ─▶ boss ─▶ order planner ─▶ risk ─▶ order router ─▶ broker       │
   │  (+entry     runtime     (basket, (marketable     (veto)  (idempotent)    (paper now)  │
   │   location)  (plugins,   select,   next-bar entry;                                     │
   │     ▲         registry,  size,                      position manager ◀── fills         │
   │     │         basket)    stretch                    (exit primitives per strategy)     │
   │     │                    record)                                                       │
   │  founder controls (commands)                        ledger + charges + outbox          │
   └───────┬────────────────────────────────────────────────────┬───────────────────────────┘
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
      bars.py         (BarBuilder: ticks -> closed 1m bars, finalize delay; 3m/5m resampled from CLOSED 1m bars)
      chain.py        (option chain poller; dhan_client.option_chain; 1 unique request / 3 s)
      depth.py        (FULL-mode depth for the traded strikes, <= 1 s; raw frame kept until the decoder is verified)
      quotes.py       (QUOTE_SNAPSHOT with bid/ask every <= 5 s for the traded strikes, sampled from depth)
      oi_cadence.py   (OI update frequency per instrument)
      clock.py        (CLOCK heartbeat every second; synthesised by sources in replay)
      sources.py      (TapeSource, RecorderTapeSource, WarehouseSource, RedisSource)
      tape.py         (TapeWriter: md:* -> data/tape/v2/YYYY-MM-DD/<stream>.jsonl)
  indicators/src/indicators/   NEW   pure incremental indicators + feature engine
      core.py (EMA, ATR, VWAP/TWAP, realised vol, HAR forecast, OI change with lag)
      engine.py (FeatureEngine) view.py (FeatureView with as-of guard)
      location.py (entry-location features: signal candle size, FVG / candle 50% / VWAP / EMA20 / POC distances in ATR)
      adapters.py (wraps desk_ml.regime.labels.RegimeLabeller, analysts.shadow helpers)
  strategies/src/strategies/   NEW   strategy runtime
      api.py (Strategy protocol, StrategyMeta, Signal, ExitPlan)
      registry.py (client for the registry/basket module; YAML fallback)
      runtime.py (StrategyRuntime: load, isolate, route events, budgets)
      strikes.py (StrikeRouter: ATM/ITM100/ITM200 choice + reason + shadow-priced alternatives)
      plugins/ (one file per strategy; shadow research plugins such as Round 8 E1-E3)
      forward/ (forward-test harness: preregistered hashed specs, nightly offline evaluation; off by default)
  boss/src/boss/               REBUILD  selector.py (v2 boss). orchestrator.py stays, frozen legacy.
  risk-engine/                 REUSE+WRAP  (account scope, injected clock; section 7.2)
  brokers/                     REUSE+WRAP  (clock injection, fill models, paper state rehydrate)
      fills.py (NEW: DepthFill, FcMeasFill moneyness table fallback; realistic rules only, from PR #20)
  oms/src/oms/                 NEW   planner.py (order planner: entry location -> CHASE / LIMIT / WAIT), router.py (order router),
                                     positions.py (position/desk manager), exits.py
  ledger/                      REUSE+EXTEND  migrations/NNN_*.sql, account_id, checkpoint, outbox, commands
  control/src/control/         NEW   founder command log and semantics (ports PR #18's design)
  health/                      REUSE+EXTEND  (engine heartbeat, feed status, metrics, alert rules)
  runtime/src/runtime/         NEW   engine kernel + service entry points + wiring from config
      kernel.py (Engine) wiring.py services.py __main__.py recovery.py
  warehouse/                   REUSE+EXTEND  DuckDB ETL (adapts PR #19's etl.py)
  desk-ml/                     FROZEN legacy engine; regime/ and llm_analyst/ reused by import
  desk/  analysts/legacy.py    FROZEN legacy wrappers (desk/paper.py helpers reused)
  data-recorder/               REUSE as-is (independent backup capture)
  dhan-client/                 REUSE; decode.py gets a real FULL-packet (5-level depth) decoder (today a placeholder)
apps/
  api/                         EXTEND into the gateway (v2 websocket, auth, rate limits); legacy routes read-only
  web/                         REUSE (Desk/Founder UI from PR #15), switched to the v2 feed
deploy/
  docker/Dockerfile  compose.yaml  compose.vps.yaml  Caddyfile  systemd/aad.service  scripts/{deploy,backup,restore}.sh
config/
  v2/engine.yaml  v2/markets/india.yaml  v2/strategies/registry.yaml  v2/baskets/  v2/entry_location.yaml
  (plus existing risk/charges yaml)
```

### 2.3 Market data service (`packages/marketdata`, process `marketdata`)

- **Input:** Dhan live market feed over websocket via `dhan_client.feed.MarketFeedCollector`. It already does connect,
  subscribe, decode, and reconnect with exponential backoff up to 30 s. Option chain over REST
  (`dhan_client.option_chain`), rate-limited to one unique request per 3 s. Instrument master from
  `dhan_client.instruments` / `data_recorder.instruments`.
- **Subscriptions:** index spot (NIFTY 13, BANKNIFTY 25, SENSEX 51; ids verified from the instrument master at start),
  current futures, and the strikes the runtime asks for (ATM ± N for the day's baskets, re-centred when spot moves more
  than one strike step). Quote mode for depth (best bid/ask) on traded strikes.
- **Output streams:** `md:ticks`, `md:depth`, `md:quotes`, `md:bars:1m`, `md:chain`, `md:clock`, `md:status`,
  `md:oi_cadence`.
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
- **Recording requirements (research round 9; new system only, the legacy engine is not patched):**
  - **Why.** No dataset we have contains bid/ask. The PR-001 recorder polls the chain every 180 s
    (`option_chain_recorder._poll_interval = 180`), the Dhan QUOTE packet has no bid/ask
    (`dhan_client.decode`, QUOTE fields), and the FULL packet with 5-level depth is a placeholder decoder that
    reads only LTP. A 2-5 minute stop cannot be tested without real bid/ask at second resolution.
  - **Traded strikes set.** For each basket underlying and the nearest weekly expiry: ATM, ITM100 and ITM200 on both
    CE and PE (6 option instruments per underlying), plus the index and current future. Re-centred when spot crosses
    a strike step; the old strikes keep streaming for 10 minutes so open positions and shadow alternatives stay priced.
    Instruments with an open position are always subscribed. That is about 24 instruments for NIFTY + SENSEX, far
    inside Dhan's 5,000 per connection.
  - **Depth at ≤ 1 s.** Subscribe FULL mode for the traded strikes. Publish `DEPTH_QUOTE` (5 levels, bid/ask price and
    quantity) on every change, throttled to at most one per instrument per 250 ms, and at least once per second
    (a heartbeat repeat when nothing changed, flagged `repeat: true`) so "no change" and "no data" can be told apart.
    Until the FULL decoder is verified against a captured frame, the tape also stores the raw payload (base64), so
    every day recorded before the fix can be decoded later.
  - **Quote snapshots at ≤ 5 s.** Every 5 s on the `CLOCK` heartbeat, publish one `QUOTE_SNAPSHOT` per traded
    strike: best bid, best ask, mid, spread, LTP, last trade time, OI and `depth_age_ms`. This is the compact series
    for research and the strike router's shadow prices. A snapshot with `depth_age_ms > 5000` is flagged `stale`.
  - **OI update frequency.** `oi_cadence.py` counts OI changes per instrument (from the feed's OI and FULL packets and
    from chain snapshots) and publishes `OI_CADENCE` every minute: updates in the last minute, median and p90 seconds
    between changes, and the last change time. The warehouse keeps a daily `oi_cadence` table. This answers the
    Round 8 VERIFY on whether an OI signal lagged to the last snapshot is stale.
  - **Budget.** About 24 instruments × 1 row/s × 22,500 s ≈ 540k depth rows a day (~150 MB raw JSONL, ~20-30 MB
    gzipped), plus ~110k quote snapshots.
  - **Runs early and on its own.** `python -m runtime marketdata --record-only` runs the depth, quote and OI-cadence
    recorders and the tape writer without the engine, so capture can start before the rest of M1 exists. Recorded
    data cannot be backfilled.
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
- Entry-location features (`indicators/location.py`) are computed for every signal from closed bars only; see
  section 2.18.
- Higher timeframes (3m, 5m) are built only from **closed** 1m bars, and a 3m bar is stamped and made available at
  its **bucket close** (`start + 180 s`), never at its last print. The legacy `paper_scalp.resample_closes_3m`
  stamped each bucket at the timestamp of its last 1m close (`ts=grp[-1][0]`), so `logit_side_series` could see a
  bar before the bucket ended. That bug is regression requirement REG-01 (section 6.5).
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
    entry_policy: EntryPolicy = EntryPolicy()   # how the desk may enter (section 2.18)

# Exit primitives (section 2.9). Each strategy declares the ones it uses; there are no hidden engine exits.
@dataclass(frozen=True)
class CatastrophicStop:           # required on every strategy; the resting broker-side stop (REG-02)
    level: Level                  # Level(kind="premium"|"underlying", price=..) or an ATR/percent rule resolved at fill

@dataclass(frozen=True)
class StructuralStop:             # beyond the structure that defines the idea (swing, box edge, FVG edge)
    level: Level
    trigger: str = "bar_close"    # "bar_close" (1m close beyond) | "tick"

@dataclass(frozen=True)
class AtrStop:
    k: float                      # stop = entry_underlying -/+ k * ATR14(1m) at fill
    trigger: str = "bar_close"

@dataclass(frozen=True)
class TimeStop:
    after_s: int                  # seconds after the entry fill, e.g. 180
    when: str = "always"          # "always" | "entry_in:09:15-10:00" | "expiry_day" | "entry_in:..&expiry_day"
    unless_profit_pts: float | None = None   # optional: skip if the premium is up at least this much

@dataclass(frozen=True)
class GracePeriod:
    seconds: int                  # after the fill, only the catastrophic stop, EOD flat and founder commands can exit

@dataclass(frozen=True)
class SignalFlipExit:
    on: tuple[str, ...] = ("own_opposite",)  # "own_opposite" (same strategy signals the other side) |
                                             # "boss_opposite" (boss DECISION ENTER on the other side, same underlying)
    trigger: str = "bar_close"

@dataclass(frozen=True)
class ExitPlan:
    catastrophic: CatastrophicStop                   # required; a plan without it refuses to load
    structural: StructuralStop | None = None
    atr: AtrStop | None = None
    time_stops: tuple[TimeStop, ...] = ()            # first matching `when` at the fill wins; checked on the 1 s CLOCK
    grace: GracePeriod | None = None
    signal_flip: SignalFlipExit | None = None
    target: Level | None = None
    partials: tuple[Partial, ...] = ()               # Partial(at=Level, fraction=0.5)
    trail: Trail | None = None                       # Trail(kind="step", activate_at=Level, step=..)
    flat_by_ist: str = "15:15"
    defaults_from: str | None = None                 # "exit_defaults@<hash>" when fields came from config/v2/exits/defaults.yaml

@dataclass(frozen=True)
class Signal:
    signal_id: str                # ids.signal_id(strategy_id, version, underlying, decision_ts, n)
    strategy_id: str
    underlying: str
    side: str                     # "CE" | "PE"  (buyer-only desk; writer-side needs a founder decision)
    strike_rule: str              # "ATM" | "ITM100" | "ITM200" | "ROUTER"
    strike_choice: StrikeChoice   # filled by the StrikeRouter: chosen strike, reason, shadow-priced alternatives
    decision_ts: str              # == clock.now() when emitted
    confidence: float             # 0..1, calibrated or null; never shown as a win rate
    exit_plan: ExitPlan
    reasons: tuple[str, ...]      # short machine codes + one human line
    features: dict[str, float]    # the exact inputs used (for audit and the forward evaluator)
    entry_location: EntryLocation | None = None  # filled by the runtime, never by the strategy (section 2.18)

@dataclass(frozen=True)
class ZoneDistance:
    zone: str                     # "fvg" | "candle_50" | "vwap" | "ema20" | "poc"
    price: float                  # underlying (index) price of the zone edge nearest to current price
    distance_atr: float           # (spot - zone) / ATR14(1m), signed so + means price is stretched away
    source: str                   # e.g. "fut_vwap" | "twap" | "fut_volume_profile"

@dataclass(frozen=True)
class EntryLocation:             # shared: every strategy gets it the same way
    signal_candle_atr: float      # (high - low) / ATR14 of the signal bar (last closed 1m bar)
    signal_body_atr: float
    zones: tuple[ZoneDistance, ...]   # every zone found on the pullback side of the signal
    nearest: ZoneDistance | None      # smallest positive distance; None = no zone found
    entry_distance_atr: float | None  # = nearest.distance_atr (the "stretch")
    atr: float; spot: float; as_of: str   # as_of = available_ts of the last closed bar used

@dataclass(frozen=True)
class EntryPolicy:                # kept on every strategy card (founder addendum 6)
    mode: str = "chase"            # "chase" (marketable next-bar entry; default) | "pullback_limit" | "wait_consolidation"
                                   # the last two are supported but globally disabled in config/v2/entry_location.yaml
    zones: tuple[str, ...] = ("fvg", "candle_50")   # zones used for the stretch record (EMA20 and TWAP always recorded)
    max_chase_ticks: int = 2       # marketable limit = best ask + this many ticks (2 = ₹0.10); never a plain market order
    chase_timeout_s: float = 2.0   # unfilled after this -> cancel and record MISSED_CHASE
    chase_calibration: str = "chase_defaults@<hash>"  # versioned source of the two values above (decision K20)

class Strategy(Protocol):
    meta: StrategyMeta
    def on_session_start(self, ctx: SessionContext) -> None: ...
    def on_bar(self, bar: Bar, view: FeatureView) -> list[Signal]: ...
    def on_chain(self, snap: ChainSnapshot, view: FeatureView) -> list[Signal]: ...
    def on_position(self, update: PositionUpdate) -> list[ExitRequest]: ...   # optional early exit
    def on_session_end(self) -> dict[str, Any]: ...                           # per-strategy day stats
```

- **Strike router (first-class, `strategies/strikes.py`).** Every signal goes through `StrikeRouter.route(signal,
  view, quotes)`, which picks ATM, ITM100 or ITM200 and records why:

  ```python
  @dataclass(frozen=True)
  class StrikeQuote:
      rule: str                     # "ATM" | "ITM100" | "ITM200"
      instrument_id: str
      bid: float | None; ask: float | None; mid: float | None; spread: float | None
      quote_age_ms: int | None      # age of the QUOTE_SNAPSHOT / depth used; None = no quote
      est_delta: float | None       # from the chain or a Black-76 estimate; tagged with its source
      est_round_trip_pts: float | None  # charges + spread, from the cost model

  @dataclass(frozen=True)
  class StrikeChoice:
      chosen: str                   # "ITM100"
      reason: str                   # machine code, e.g. "EXPIRY_DAY_NO_ATM", "OPEN_DECAY_WINDOW",
                                    # "DTE_GE_2", "LOWEST_BREAKEVEN_AT_HOLD", "STRATEGY_FIXED"
      rule_version: str             # router version + params hash (part of the gate, REG-13)
      alternatives: tuple[StrikeQuote, ...]   # all three, priced at the SAME decision_ts
  ```

  Rules are data (`config/v2/strategies/strike_router.yaml`): the Round 8 skips (no ATM on expiry day, no buying
  09:15-10:00 unless the spec prices it), a DTE rule, and "lowest break-even move for the planned hold" using the
  measured decay and spreads. A strategy can pin a strike (`STRATEGY_FIXED`), and the router still prices the others.
  Shadow pricing uses only quotes with `available_ts ≤ decision_ts`, so it is causal. The forward harness
  (section 2.17) replays each alternative with the same exit plan and fill model, so every trade leaves a
  "what if ATM / ITM100 / ITM200" row. That is how the router is measured.
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
  `config/v2/baskets/YYYY-MM-DD.yaml`. The basket module's JSON (`basket_india.json`, `basket_forex.json`) is
  **canonical** (decision K6) and is read through a read-only adapter. **No basket means no trades** (fail closed). The runtime publishes
  `BASKET_LOADED {basket_hash, entries}` at session start. The basket is fixed for the session; a founder command
  can only remove entries mid-session, not add them (decision K5, desk default pending founder review). The boss
  applies the basket and logs regime-based ranks in shadow. Intraday regime selection by the boss is a preregistered
  forward shadow spec with no live effect until it passes the forward bar.
- **Markets.** `India NIFTY/SENSEX` now (BANKNIFTY data is recorded; trading it is a basket decision). Forex later
  through a `MarketAdapter` (section 2.12). A strategy declares its markets, and the runtime refuses to load it into a
  basket for another market.
- **Isolation.** Each strategy call is wrapped: an exception, or a call over `budget_ms` (default 20 ms, measured on
  the engine thread), disables that strategy for the rest of the session, publishes `HEALTH_ALERT`, and never affects
  the other strategies. Strategies get a read-only `FeatureView` and no access to the broker, ledger or bus.
- **Onboarding checklist (decision K9).** A registry entry declares `legacy_logic_from` (legacy analyst ids whose
  logic it re-implements, or empty). If it is not empty, every PR-010 bug for that analyst (for example the reversed
  OI signal or the double-counted `greeks_vote_intent`) must have a REG test before the strategy loads. CI enforces
  this in V2-06.
- **Stages.** `shadow` signals are logged (`sig:signals` with `stage: shadow`) and evaluated by the forward-test
  harness (section 2.17).
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
   The strike comes from the signal's `strike_choice` (section 2.5); lot size comes from the instrument master
   (never hard-coded; NIFTY 65 today).
5. **Entry-location record (no veto power).** On every signal the boss records the stretch in ATR from the nearest
   zone (FVG or candle 50%), from EMA20 and from TWAP (section 2.18) in the decision's `stretch` block. Round 10 found
   no entry-location rule (founder addendum 6), so stretch never holds or vetoes an entry.
6. **Regime and weights (shadow).** The merged adaptive weights (`desk_ml.regime.weights`) and the intermarket overlay
   run next to the static decision and publish `BOSS_SHADOW`, exactly as today. They do not change the decision
   until a founder-approved config flips `regime.mode: apply`.
7. **Output.** `DECISION {decision: ENTER|HOLD, ...}` with the signal ids, sizing inputs, the `entry_location` block,
   the boss's stretch verdict, and the hold or conflict reason. An ENTER goes to the desk's order planner
   (section 2.18), which turns it into a `TradeIntent` (reused from `risk_engine.TradeIntent`) for each account that
   follows the basket.

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
- **Caps live in the veto, not only in config (REG-05).** `MAX_LOSS_PER_TRADE` (₹30k), `MAX_DAILY_LOSS` (₹90k),
  `MAX_LOTS` (25) and `MAX_OPEN_POSITIONS` (3) are already checks inside `_entry_veto` (paper values in
  `config/risk_limits.yaml`, configurable per mode). v2 keeps them there and adds tests that a missing or edited
  config key can never silently disable a cap.
- **Last-good config (REG-07).** Today `_decide` loads `risk_limits.yaml` before deciding **any** action, so a bad
  YAML edit vetoes exits and flatten too (`ENGINE_ERROR`). v2 keeps the last config that validated. A bad file
  raises a `CONFIG_INVALID` alert. Entries stay blocked until a valid file is back (fail closed), and exits, cancels
  and flatten always run on the last-good limits. The same loader (`contracts.config.load_with_last_good`) is used
  for every YAML the engine reads, and a config error never stops the bus.
- **No per-day trade-count cap anywhere** (decision K1, desk default pending founder review). The 15-minute loss
  cooldown, the 3-position cap and the ₹90k daily loss cap stay as risk limits. Round 8's E2 keeps its
  preregistered one-trade-per-day rule, because that rule belongs to the spec, not to the engine.
- Latency budget stays at < 10 ms p99 (SQLite reads, WAL).

### 2.8 Order router over a broker interface (`packages/oms/router.py`, in the engine)

- **Interface:** the merged `brokers.BrokerAdapter` (place, super order, modify, cancel, flatten, status, positions,
  orders, balance). Implementations: `PaperBroker` now, `DhanBroker` later (already written, and it refuses unless
  mode is `limited_live`/`live` **and** `ALL_ABOUT_DHAN_LIVE_CONFIRM` is set **and** a fresh approval exists), and a
  forex broker later.
- **Input:** the order planner's `EntryPlan` (section 2.18), never a raw decision.
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
- **Paper fills (`brokers/fills.py`): realistic is the only mode.** v2 has no optimistic or `legacy` cost mode. The
  merged `PaperBroker(cost_model="realistic")` logic from PR #20 (`c004ace`: side-aware tick rounding, trade-through
  limits at the limit) is the base, and the `cost_model` switch is not exposed in any v2 config (REG-12e). The
  slippage source, in order:
  1. `DepthFill`: the recorded ask (buy) or bid (sell) of the first depth quote with
     `available_ts ≥ order.available_ts + latency_ms`, which is the real half-spread, plus 0.05 impact at 25 lots.
  2. `FcMeasFill` (decision K15): when no recorded bid/ask exists for that strike at that time, LTP ± the Round 8
     FC-MEAS half-spread for the strike's moneyness bucket and time of day, which is the more conservative choice.
     The table lives in `config/v2/markets/india.yaml` (points per side):

     | Bucket | before 12:00 | 12:00-15:00 | after 15:00 |
     |---|---|---|---|
     | ATM | 0.20 | 0.25 | 0.30 |
     | ITM100 | 0.30 | 0.35 | 0.40 |
     | ITM200 | 0.35 | 0.40 | 0.45 |

     Round 8 measured the time-of-day add-on (+0.05 after 12:00, +0.10 after 15:00) on ATM only. Applying the same
     increments to ITM100 and ITM200 is a conservative assumption, marked VERIFY until V2-D2 depth measures it.
  The flat 0.20 pt/side (`config/paper_costs.yaml` `slippage_pts_per_side` default) is shown **only as a
  sensitivity** in reports. Once V2-D2 has recorded the real half-spread for a strike bucket, `DepthFill` replaces
  both. The fill model and slippage source (`depth` | `fcmeas` ) are stored on every fill.
  **Order-type fill rules (REG-14):**
  - A resting **limit** (take-profit or entry) fills only when the market trades *through* it by at least one tick (a
    depth quote with the ask one tick below a buy limit, or a print below it; mirrored for sells), and **always at the
    limit price**. It never fills at an overshoot print. In the PR #20 verification, fixing this one rule moved
    paper P&L by −₹164,934 over 7 days of ALL3. Touching the limit is not a fill. A limit that is already marketable when placed
    also fills at its limit price, with no price improvement (decision K17). That is conservative, and it is revisited
    after 5 sessions of V2-D2 depth, alongside the `max_chase_ticks` recalibration.
  - A **stop** (SL-M) fills at or worse than its trigger: at the triggering print (or the depth bid/ask) minus or plus
    slippage, tick-rounded against the order's side, never better than the trigger.
  - Before PR #20, `PaperBroker` filled limits on a touch (`ltp <= order.price`). That rule only exists behind
    `cost_model="legacy"` on `main` now, and v2 never selects it.
- **Protective stop.** After an entry fills, the router places a resting stop order (`SL-M`, from
  `ExitPlan.catastrophic`, which every plan must have). If the engine dies, the position
  is still protected at the broker. In paper, `PaperBroker` simulates it. The position manager cancels or modifies it
  on every exit or trail step.
- **Stop invariant (REG-02).** Every open position has an enforced stop at all times: a resting protective order at
  the broker **and** the engine's tactical stop. The Phase 2 review found a stop-loss hole worth about ₹193k in the
  legacy engine. After a fill, a restart or a feed reconnect, the router checks each open position and places a
  missing protective stop before any new entry is allowed. A position without one raises a CRITICAL alert and
  blocks entries. `PaperBroker` resting orders are rebuilt from the ledger on restart (today they live only in
  memory).
- **Every simulated fill pays the verified cost stack (REG-12).** Paper fills always go through the ledger, which
  charges them with `ledger.charges.order_charges(..., exchange=...)` using `load_rates(by_exchange=True)`:
  - Dhan brokerage ₹20 per order;
  - STT 0.15% of sell premium;
  - exchange transaction charge **per exchange**: NSE 0.0355299% (`config/charges.yaml` has `0.0003553`, i.e.
    ₹3,552.99 + ₹0.01 IPFT per crore; decision K14: the IPFT is included and this circular-cited value is kept) and
    BSE ₹3,250 per crore (`0.000325`), picked from
    `underlying_exchange` (SENSEX and BANKEX → BSE);
  - SEBI fee;
  - stamp duty 0.003% on buy;
  - GST 18% on (brokerage + exchange transaction charges + SEBI fee), as `order_charges` already computes. STT and
    stamp duty carry no GST (decision K12).

  The flat `exchange_txn_frac: 0.0003503` in the same file serves only legacy callers and is never read by v2. Lot
  sizes come from the instrument master (NIFTY 65).
- **Every closed trade carries its exchange tag (REG-17).** `trades.exchange` (`NSE` | `BSE`, not null) is written
  when the trade opens, from the same `underlying_exchange` map the charges use. NSE and BSE rates differ, so
  reports and reconciliation group by it.
- **A malformed cost config fails closed (REG-16).** `load_rates` raises `ValueError` on a bad or incomplete
  `charges.yaml`/`paper_costs.yaml`, and today nothing catches it. v2 loads both through `load_with_last_good`
  (REG-07):
  - a bad file mid-session keeps the last-good rates, raises `CONFIG_INVALID` (component `costs`) and blocks new
    entries, while exits and flatten continue on the last-good rates;
  - with no valid cost config at start, the engine runs exits-only, and any fill booked meanwhile gets
    `charges_status = PENDING`, then is recharged once a valid file appears.

  Never a crash, never a fill booked at zero cost.

### 2.9 Position / desk manager (`packages/oms/positions.py`, `exits.py`, in the engine)

Owns every open position after the entry fill.

**Exit layer = per-strategy primitives, nothing hidden (founder addendum 6, REG-18).** The -4/-5 point loss
cluster the founder saw came from the legacy engine's hard-coded tight cancel exits: `CANCEL_AGAINST`,
`CANCEL_ADVERSE`, the stall cancel, and `COVER_LONG_UNWIND` (`paper_scalp.py` around lines 3846 and 4865). In v2 the
position manager has **no exit logic of its own**. It runs only the primitives in the position's `ExitPlan`
(section 2.5), plus three non-strategy exits that always apply: founder commands, the kill switch, and the EOD
flatten. The primitives are:

| Primitive | What it does | Notes |
|---|---|---|
| `CatastrophicStop` | Resting broker-side stop at a far level | **Required** on every plan; it is the protective stop of REG-02 |
| `StructuralStop` | Exit when the structure behind the idea breaks (swing, box edge, FVG edge); bar-close or tick trigger | Underlying level; survives a restart |
| `AtrStop` | Exit at entry ∓ k × ATR14 of the underlying, fixed at the fill | Bar-close or tick trigger |
| `TimeStop` | Exit `after_s` seconds after the fill; windows such as the open or expiry day | See below |
| `GracePeriod` | For N seconds after the fill, only the catastrophic stop, EOD flatten and founder commands can exit | Stops noise exits in the first bars; it never delays the catastrophic stop |
| `SignalFlipExit` | Exit when the same strategy signals the opposite side (or the boss enters the opposite side on that underlying), on a bar close | Replaces the legacy "ticket against market" cancel with an explicit, per-strategy choice |

Targets, partials and trailing stay available as before.

**Order checked on each `TICK`/`DEPTH`/`BAR_CLOSED`/`CLOCK`:**
1. founder `CUT_LOSS`, `FLATTEN_ALL` or kill switch → exit at market (never refused);
2. **catastrophic stop** (resting at the broker; the engine also checks it in case the resting order failed);
3. **EOD flat** at `flat_by_ist` (15:15 default) on the `CLOCK` heartbeat, so it fires with no ticks at all. The EOD
   flatten is **never held back by the stale-quote guard** (REG-15). On `main`, PR #20's guard defers the
   `FLATTEN_1516` exit while the quote is older than `exit_quote_max_age_s` until `stale_exit_hard_flatten_ist:
   "15:20"`. In v2 the flatten is sent at `flat_by_ist` regardless (decision K16: EOD, founder and kill-switch
   flattens are exempt from the guard; the legacy `paper_costs.yaml` 15:20 value stays unchanged as a benchmark only). In paper it is priced at the freshest quote, or the
   last good print flagged `STALE_QUOTE`, with an alert. In live it is a market exit at the broker;
4. if inside the **grace period**, stop here;
5. **structural stop**, then **ATR stop**;
6. **time stop**;
7. **signal-flip exit**;
8. **target** or **partials**, then **trailing** (every step modifies the resting catastrophic stop only toward
   safety);
9. strategy `on_position` exit requests.

**Rules that keep it honest:**
- Every exit's reason is one of the primitive names (`CATASTROPHIC_STOP`, `STRUCTURAL_STOP`, `ATR_STOP`, `TIME_EXIT`,
  `SIGNAL_FLIP`, `TARGET_HIT`, `PARTIAL`, `TRAIL_STOP`, `FLATTEN_EOD`, `FOUNDER_COMMAND`, `KILL_SWITCH`,
  `STRATEGY_EXIT`, `FAILSAFE_MTM`), and it cites the `ExitPlan` field that fired. An exit with any other reason, or
  one fired by a primitive the plan does not contain, is a test failure (REG-18). `CANCEL_AGAINST`,
  `CANCEL_ADVERSE`, `CANCEL_STALL` and `COVER_LONG_UNWIND` do not exist in v2.
- **Defaults come from research round 11** (due 08:00 CT Sunday) in `config/v2/exits/defaults.yaml` (decision K18).
  Round 11 is preregistered and hashed before outcomes, and its trials count toward the cumulative trial budget
  (about 4,621 after round 10, plus deep dive 1's 6,693 on its own book). The defaults are a versioned, hashed input,
  never tuned intraday. Until that file
  has values, every strategy must declare its own full `ExitPlan`, and a plan missing a field it does not declare
  refuses to load (fail closed). When defaults exist, a strategy may inherit them. The inherited values and the
  defaults file hash are frozen into the plan (`defaults_from`) and the params hash (REG-13), so changing the
  defaults is a new strategy version, never a silent change to running strategies.
- The resolved plan is stored on the position (`positions_v2.exit_plan_json`) at the fill, so restarts use exactly
  the same exits.
- Exit-rule changes follow the Round 8 caution that exits choose holding time rather than create edge. A new
  default must come from a preregistered, hashed round with its trials counted, and is shadow-priced in the forward
  harness. Never intraday tuning (K18, decided).

**Time stops are a first-class exit primitive.** Research round 9 found that a 3-minute time stop at the open and on
expiry day drove most of the strike router's improvement. So:
- `ExitPlan.time_stops` is a list of `TimeStop(after_s, when, unless_profit_pts)`. The matching entry is chosen at the
  fill (for example `after_s=180, when="entry_in:09:15-10:00"` and `after_s=180, when="expiry_day"`) and stored on
  the position (`positions_v2.exit_plan_json`), so it survives a restart.
- It is checked on the 1 s `CLOCK` heartbeat, so it fires on time with no ticks. Its deadline is
  `fill_ts + after_s` in event time, identical in replay and live.
- The exit is priced with the depth fill model at the first quote after the deadline. That is why ≤ 1 s depth
  recording (section 2.3) is required before any 2-5 minute stop result counts.
- Time stops and their windows are part of the strategy params hash and the gate (REG-13).

**Exits always target the held instrument.** An exit intent is built from the position record (`instrument_id`,
`net_qty`) with `brokers.exit_intent(position)`, never by recomputing ATM or re-running the strike router (REG-03).

Each exit is an `EXIT` intent through `risk.check_exit` (allowed under the kill switch) and the router. A mark-to-market
exception keeps the merged fail-safe behaviour (`desk.executor` `failsafe_mtm_error`): close at the last good quote and
block new entries for the session. The PR #14 halt semantics are ported too: the halt is saved durably (a
`session_halts` row instead of `mtm_halt.json`); a halt record that cannot be read blocks every entry (fail closed);
forced closes are re-booked at their saved time and price on rehydrate; and flatten always runs (REG-05).

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

### 2.17 Forward-test harness (`packages/strategies/forward/`, nightly job; **off by default**)

Research round 9 asks for preregistered, hashed strategy specs evaluated nightly offline on recorded data, with
pass and kill bars. It is the Round 8 FWD-BAR process built into the platform.

- **Spec files:** `config/v2/forward/specs/<spec_id>.yaml`. Each holds `strategy_id`, plugin module, frozen params
  (including exit plan, time stops and strike-router rules), the data it needs, the cost model, the bars (default:
  Round 8 FWD-BAR, i.e. n = 30 gross-kill, n = 60 PROMISING, n ≥ 120 PASS to 09's five-pass with one-sided
  t ≥ 2.13), placebos (side-flip, random-minute), and `start_session`.
- **Preregistration lock:** `config/v2/forward/prereg.lock` stores `spec_id → sha256(canonical spec + plugin source
  + model coefficients)` and the registration time. The harness refuses to evaluate a spec whose hash differs from
  the lock. Changing anything means a new `spec_id` and a new count; a bug fix restarts the count (Round 8 rule).
- **Run:** `python -m runtime forward-eval --session <day>` runs after close, when `forward_eval.enabled: true` in
  `config/v2/engine.yaml` (default `false`). It uses the **same engine kernel** over `TapeSource` for that day
  (one code path), with the plugin at stage `shadow`, `PaperBroker(DepthFill)`, the FC-MEAS moneyness table as the
  fallback fill (and as the conservative second pricing), the flat 0.20 as a sensitivity, and the strike router's alternatives priced as extra shadow legs.
- **Headline, ranking and promotion (decisions K3 and K4).**
  - **Total net after costs** is the headline and the ranking metric (C2).
  - Promotion to a non-zero engine weight still needs FWD-BAR and 09's five-pass, including significance. The
    founder's rules are "no luck" and "proven on unseen data": a net-positive spec that fails significance is not
    proven, so it stays in shadow (`NET_POSITIVE_NOT_SIGNIFICANT`) and keeps collecting forward data. K3 is a desk
    default pending founder review.
  - There is no cap on the number of harvested specs. Each one is preregistered and counted, and every report
    carries the deflated Sharpe ratio and the cumulative trial count.
- **Output:** append-only `forward_trades` and `forward_checkpoints` tables (warehouse copy nightly), and one line
  per spec on the founder page: n, gross, net at depth and at FC-MEAS, current bar state (`RUNNING`, `KILLED`,
  `PROMISING`, `PASS_TO_REVIEW`). A `KILLED` spec stops being evaluated. Nothing here changes a basket or places an
  order. Promotion is a founder decision after 09's five-pass.
- **Data gate:** a session where depth coverage for the spec's strikes is below 95% of minutes is marked
  `DATA_INSUFFICIENT` for depth pricing and does not count toward n.
- **Entry alternatives:** for every signal the harness also prices the entry actions it did not take (CHASE, LIMIT
  at each zone, WAIT) as shadow legs (`leg = "entry:LIMIT:fvg"` and so on). Round 10 found no entry-location rule, so these legs
  only keep the question open on forward data; they never change a live entry. Exit primitives likewise get shadow
  legs for the round 11 default versus each strategy's own plan.

### 2.18 Entry location (desk order planner; boss records stretch, no veto)

**History.** The founder observed (C9) that the legacy engine entered at the top of big impulse candles, gave back
4-5 points, and got stopped. Research round 10 (founder addendum 6, 2026-09-27) tested that and **found no
entry-location rule**:
- stretched entries do not carry a disproportionate share of the losses;
- pullback limits fill the losers and miss the winners (the same adverse selection Round 8 found for passive entries).

The -4/-5 point loss cluster comes from the old engine's **tight cancel exits**, not from where it entered. In
`paper_scalp.py`, `CANCEL_AGAINST` (from `ticket_against_market`), `CANCEL_ADVERSE` and the stall cancel, and
`COVER_LONG_UNWIND` (a long-unwind label, even when only 3 points underwater in chop) are hard-coded. So v2 fixes
this in the exit layer (section 2.9, REG-18), and entry location becomes a **recorded diagnostic** with no rule
attached.

**Desk: marketable next-bar entries (decision K20).** For trend signals the desk enters with a **marketable limit,
never a plain market order**: best ask + `max_chase_ticks` at the first quote after the signal bar closes. This is
`EntryPolicy.mode = "chase"`, the default on every strategy card.
- `max_chase_ticks` (default **2**, ₹0.10) and `chase_timeout_s` (default **2 s**) are per strategy card.
- If the chase limit is not filled within `chase_timeout_s`, it is cancelled (`TIMEOUT_UNFILLED`) and the result is
  `MISSED_CHASE`. That result records the price chasing would have paid (the best ask at the cancel, and the first
  ask that would have filled it within the next 5 s of depth), plus the shadow P&L of that fill.
- The two defaults are versioned like the exit defaults: `config/v2/entry/chase_defaults.yaml` is hashed, its hash is
  frozen into each strategy's params (REG-13), and a change is a new strategy version.
- They are **recalibrated once** from the first 5 sessions of V2-D2 recorded depth: the spread distribution per
  strike bucket (ATM / ITM100 / ITM200 × time-of-day band × expiry vs non-expiry), chosen so that the cap covers the
  measured p90 half-spread plus one tick. The recalibration is a documented, versioned change, never an intraday
  adjustment.
- `pullback_limit` and `wait_consolidation` stay **supported but off** (`enabled: false` in
  `config/v2/entry_location.yaml`). Turning either on needs a founder-approved config change, a new strategy version
  (REG-13), and a preregistered forward spec that shows it helps.
- If a resting limit is ever used, it fills only at the limit when price trades through it (REG-14). Every signal
  whose limit expires or is cancelled unfilled is counted as **MISSED**: an `ENTRY_PLAN_RESULT` with status `MISSED`,
  plus the shadow P&L the chase entry would have made. Fill rate and missed-winner cost are on the daily review.
- A WAIT plan works the same way: it expires as `MISSED` when no consolidation break comes.

**Boss: records stretch, no veto power.** On every signal the boss records the stretch in ATR from:
- the nearest trusted **zone** (unfilled FVG or candle 50%);
- **EMA20**;
- **TWAP** (futures VWAP when futures volume exists, kept as an extra column).

The boss never holds or vetoes an entry because of stretch (decision K19: C10 is met by the boss and desk being
aligned on the round 10 outcome). A veto can come back **only** through a future preregistered research result plus
a new strategy version. There is no config switch for it. The `ENTRY_STRETCHED` hold code is reserved in the schema
for that case and is unused today.

**Features (`indicators/location.py`, shared).** Unchanged from V2-05b and built only from closed 1m bars (REG-01):
- signal candle and body in ATR;
- zone distances: FVG (3-bar rule, fill rule, max age) and candle 50%;
- EMA20 and TWAP distances, plus futures VWAP and POC where futures volume exists (absent otherwise).

All distances are signed so that a positive number means price is stretched away from the pullback side.

**Config (`config/v2/entry_location.yaml`).**

```yaml
source: "research round 10: no entry-location rule found (founder addendum 6)"
boss_stretch: record_only        # no veto power; the only allowed value
default_entry_policy: chase      # marketable next-bar entry
chase_defaults: config/v2/entry/chase_defaults.yaml   # max_chase_ticks: 2, chase_timeout_s: 2.0 (versioned, hashed;
                                                       # per-card overrides allowed; recalibrated from 5 depth sessions)
pullback_limit: {enabled: false, limit_timeout_s: null}
wait_consolidation: {enabled: false, consol_max_atr: null, wait_max_bars: null}
zones: [fvg, candle_50]          # "zone" for the stretch record; EMA20 and TWAP always recorded
fvg: {fill_rule: full, max_age_bars: 60}
```

A config that sets `boss_stretch` to anything else, or enables an optional mode with a `null` parameter, is invalid.
The last-good config stays in force and `CONFIG_INVALID` is raised (REG-07). All values are in `config_hash`
(REG-13).

**Logging for daily review.** Every entry is an `ENTRY_PLAN` event, and its result follows as `ENTRY_PLAN_RESULT`
(`FILLED`, `MISSED_CHASE` with the price chasing would have paid, `MISSED` for an optional resting mode,
`CANCELLED_INVALIDATED`). Both carry the three stretch readings, the zone type,
`signal_candle_atr`, the action taken, and for fills the 5-minute give-back. The nightly ETL builds
`entry_location_daily` (by stretch bucket, zone type, strategy and action: count, fill rate, missed signals,
give-back, stop-outs, net P&L). The forward harness keeps pricing the non-default entry actions as shadow legs, so
the data can reopen the question later without a code change.
---

## 3. Data

### 3.1 Stores and what lives where

| Store | Holds | Writer | Readers | Survives restart? | Source of truth? |
|---|---|---|---|---|---|
| **SQLite, WAL** `data/state/aad.sqlite` | ledger (orders, order_events, fills, positions, trades, charges, risk_decisions, recon_runs), `founder_commands`, `engine_checkpoint`, `outbox`, `events` audit, `strategy_day_stats` | **engine only** (single writer) | gateway, health, nightly (read-only connections) | Yes (fsync on commit; `synchronous=FULL` for this file) | **Yes** for orders, fills, positions, money, commands |
| **Redis 7** (AOF `everysec`) | streams `md:*`, `sig:*`, `boss:*`, `oms:*`, `pos:*`, `ctl:*`, `health:*`, `llm:*`; hot hashes `hot:quote:<instrument>`, `hot:positions:<account>`, `hot:health`; rate-limit buckets | marketdata, engine outbox publisher, gateway (`ctl:commands` only), health | everyone | Mostly; **rebuildable** from tapes + SQLite | **No** |
| **Tapes** `data/tape/v2/YYYY-MM-DD/<stream>.jsonl(.gz)` | every `md:*` envelope exactly as the engine saw it, including ≤ 1 s depth, 5 s quote snapshots with bid/ask and OI cadence (~20-30 MB/day gzipped) | tape-writer | engine (replay/rehydrate), gates, forward evaluator, ETL | Yes | Yes for "what the market showed us" |
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
ALTER TABLE trades       ADD COLUMN exchange TEXT NOT NULL DEFAULT 'UNKNOWN'; -- NSE | BSE (REG-17); backfilled from
                                                             -- underlying_exchange; v2 never writes UNKNOWN
ALTER TABLE fills        ADD COLUMN slippage_source TEXT;       -- depth | fcmeas (REG-12)
ALTER TABLE charges      ADD COLUMN charges_status TEXT NOT NULL DEFAULT 'FINAL'; -- FINAL | PENDING (REG-16)
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
CREATE TABLE session_halts (             -- PR #14 halt semantics, durable (replaces data/desk/live_loop/mtm_halt.json)
  session TEXT NOT NULL, account_id TEXT NOT NULL, halt_ts TEXT NOT NULL, kind TEXT NOT NULL,
  forced_closes_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE ingest_errors (             -- first-seen bad line per file, recorded durably (REG-06, REG-08)
  source TEXT NOT NULL, path TEXT NOT NULL, line_no INTEGER NOT NULL, byte_offset INTEGER NOT NULL,
  error TEXT NOT NULL, line_sha256 TEXT NOT NULL, first_seen TEXT NOT NULL, PRIMARY KEY (source, path, line_no));
CREATE TABLE forward_trades (            -- forward-test harness (section 2.17); append-only
  spec_id TEXT NOT NULL, spec_hash TEXT NOT NULL, session TEXT NOT NULL, signal_id TEXT NOT NULL,
  leg TEXT NOT NULL,                     -- "chosen" | "alt:ATM" | "alt:ITM100" | "alt:ITM200" | "placebo:*"
  entry_ts TEXT, exit_ts TEXT, exit_reason TEXT, gross_inr NUMERIC(18,4), net_depth_inr NUMERIC(18,4),
  net_fcmeas_inr NUMERIC(18,4), PRIMARY KEY (spec_id, signal_id, leg));
CREATE TABLE forward_checkpoints (
  spec_id TEXT NOT NULL, spec_hash TEXT NOT NULL, session TEXT NOT NULL, n INTEGER NOT NULL,
  state TEXT NOT NULL, stats_json TEXT NOT NULL, PRIMARY KEY (spec_id, session));
CREATE TABLE entry_plans (               -- pending and finished entry plans (section 2.18); rebuilt on restart
  plan_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, decision_id TEXT NOT NULL, signal_id TEXT NOT NULL,
  mode TEXT NOT NULL, action TEXT NOT NULL, shadow_action TEXT, zone TEXT, zone_price NUMERIC(18,4),
  entry_distance_atr NUMERIC(18,4), signal_candle_atr NUMERIC(18,4), limit_price NUMERIC(18,4),
  expires_at TEXT, status TEXT NOT NULL, client_order_id TEXT, created_at TEXT NOT NULL);
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
| Historical backtest (years) | `WarehouseSource` (1-minute bars and chain from the warehouse, converted to envelopes with conservative `available_ts`) | `PaperBroker(DepthFill, else FcMeasFill)` | `SimClock` |
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

New `EventType` values: `TICK`, `DEPTH_QUOTE`, `QUOTE_SNAPSHOT`, `OI_CADENCE`, `BAR_CLOSED`, `CHAIN_SNAPSHOT`, `CLOCK`, `FEED_STATUS`, `SIGNAL`,
`DECISION`, `ENTRY_PLAN`, `ENTRY_PLAN_RESULT`, `RISK_DECISION`, `ORDER_UPDATE`, `FILL`, `COMMAND_ACK`, `ADVICE`, `ENGINE_STATUS`, `BASKET_LOADED`.
Existing values stay (`PRE_MARKET_SUMMARY`, `POSITION_UPDATE`, `POSITION_CLOSED`, `ENTRY_VETOED`, `HEALTH_ALERT`,
`FOUNDER_COMMAND`, `REGIME_LABEL`, `BOSS_SHADOW`, ...), so the legacy path keeps working.

**Instrument id:** `NSE_FNO:NIFTY:2026-09-29:24500:CE`, `NSE_IDX:NIFTY`, `BSE_FNO:SENSEX:2026-10-01:81000:PE`,
`FX:EURUSD` (later). A broker security-id map comes from the instrument master and is loaded at session start.

**Payloads (JSON; numbers are floats; times are ISO-8601 IST):**

```json
// TICK  (md:ticks)
{"instrument_id":"NSE_IDX:NIFTY","ltp":24512.35,"ltq":0,"volume":null,"oi":null,"exchange_ts":"2026-09-28T10:00:59.870+05:30"}

// DEPTH_QUOTE  (md:depth; <= 1 s per traded strike; raw_b64 kept until the FULL decoder is verified)
{"instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","bid":151.10,"bid_qty":1950,"ask":151.35,"ask_qty":1300,"ltp":151.20,"oi":4412350,
 "levels":{"bid":[[151.10,1950],[151.05,2600],[151.00,4550],[150.95,1300],[150.90,3250]],
           "ask":[[151.35,1300],[151.40,2275],[151.45,3900],[151.50,1950],[151.55,2600]]},
 "exchange_ts":"2026-09-28T10:01:01.230+05:30","repeat":false,"raw_b64":"…"}

// QUOTE_SNAPSHOT  (md:quotes; every 5 s on CLOCK for each traded strike)
{"instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","rule":"ITM100","side":"CE","bid":151.10,"ask":151.35,"mid":151.225,
 "spread":0.25,"ltp":151.20,"ltt":"2026-09-28T10:01:04.910+05:30","oi":4412350,"depth_age_ms":310,"stale":false}

// OI_CADENCE  (md:oi_cadence; every minute per instrument)
{"instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","window_s":60,"oi_updates":2,"median_gap_s":31.0,"p90_gap_s":58.0,
 "last_oi_change":"2026-09-28T10:00:47.100+05:30","sources":["feed_oi","full","chain"]}

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
 "stage":"shadow","underlying":"NIFTY","side":"CE","strike_rule":"ROUTER","decision_ts":"2026-09-28T10:01:01.512+05:30",
 "confidence":0.63,"exit_plan":{"catastrophic":{"level":{"kind":"premium","price":118.0}},
 "structural":{"level":{"kind":"underlying","price":24488.0},"trigger":"bar_close"},"atr":null,
 "grace":{"seconds":60},"signal_flip":{"on":["own_opposite"],"trigger":"bar_close"},
 "target":{"kind":"underlying","price":24531.0},
 "time_stops":[{"after_s":180,"when":"entry_in:09:15-10:00"},{"after_s":180,"when":"expiry_day"},{"after_s":900,"when":"always"}],
 "flat_by_ist":"15:15","partials":[],"trail":null,"defaults_from":null},
 "strike_choice":{"chosen":"ITM100","reason":"LOWEST_BREAKEVEN_AT_HOLD","rule_version":"router-1.0.0+9c2e…","alternatives":[
   {"rule":"ATM","instrument_id":"NSE_FNO:NIFTY:2026-09-29:24500:CE","bid":88.05,"ask":88.25,"mid":88.15,"spread":0.20,"quote_age_ms":640,"est_delta":0.51,"est_round_trip_pts":0.64},
   {"rule":"ITM100","instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","bid":151.10,"ask":151.35,"mid":151.23,"spread":0.25,"quote_age_ms":410,"est_delta":0.66,"est_round_trip_pts":0.88},
   {"rule":"ITM200","instrument_id":"NSE_FNO:NIFTY:2026-09-29:24300:CE","bid":226.00,"ask":226.35,"mid":226.18,"spread":0.35,"quote_age_ms":820,"est_delta":0.79,"est_round_trip_pts":1.26}]},
 "reasons":["COIL_AGE_7M","P_UP_GE_Q90","D_16PTS"],"features":{"p_up":0.63,"box_d":16.0,"em30":27.1}}

// DECISION  (boss:decisions)
{"decision_id":"dc_nifty_20260928_1001","underlying":"NIFTY","decision":"ENTER","signal_ids":["sg_..."],
 "instrument_id":"NSE_FNO:NIFTY:2026-09-29:24400:CE","lots":14,"lot_size":65,"limit_price":151.35,
 "sizing":{"volsize":17,"caplots":14,"basket_max":25},"holds":[],"basket_hash":"b7e1…","shadow":{"regime":"trend_up"},
 "entry_location":{"signal_candle_atr":2.4,"signal_body_atr":1.9,"entry_distance_atr":1.6,"atr":6.8,"spot":24512.35,
   "nearest":{"zone":"fvg","price":24501.5,"distance_atr":1.6,"source":"1m"},
   "zones":[{"zone":"fvg","price":24501.5,"distance_atr":1.6,"source":"1m"},{"zone":"candle_50","price":24504.2,"distance_atr":1.2,"source":"1m"},
            {"zone":"vwap","price":24488.9,"distance_atr":3.4,"source":"fut_vwap"},{"zone":"ema20","price":24496.0,"distance_atr":2.4,"source":"1m"}]},
 "stretch":{"record_only":true,"zone_atr":1.6,"zone":"fvg","ema20_atr":2.4,"twap_atr":3.1,"config_hash":"e4a0…"}}

// ENTRY_PLAN  (oms:plans)
{"plan_id":"ep_…","decision_id":"dc_nifty_20260928_1001","signal_id":"sg_…","account_id":"founder",
 "action":"CHASE","shadow_actions":["LIMIT:fvg","WAIT"],"stretch":{"zone_atr":1.6,"ema20_atr":2.4,"twap_atr":3.1},"zone":"fvg","zone_price":24501.5,"entry_distance_atr":1.6,"signal_candle_atr":2.4,
 "limit_price":144.10,"est_delta":0.66,"expires_at":"2026-09-28T10:04:01.512+05:30","client_order_id":"aad3f9…"}

// ENTRY_PLAN_RESULT  (oms:plans)
{"plan_id":"ep_…","status":"FILLED","fill_price":151.35,"filled_at":"2026-09-28T10:01:01.800+05:30","waited_s":0.3,
 "giveback_5m_pts":4.6,"giveback_5m_atr":0.68,"shadow":{"LIMIT":{"status":"FILLED","fill_price":144.10,"waited_s":95}}}

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

**Supervision without restart loops (REG-09).** The legacy supervisor restart-looped (F1). In v2, compose uses
`restart: on-failure` with Docker's growing restart delay, and each service's entry point (`runtime/services.py`)
adds a circuit breaker. It records starts in `data/state/restarts.jsonl`; after 5 crashes in 10 minutes it stops
restarting, exits with a distinct code, and `health` raises a CRITICAL `RESTART_LOOP` alert. A human clears it with
`python -m runtime reset-breaker <service>`. The engine's crash path is safe to stop in, because positions keep their
broker-side stops.

**Wall-clock timeouts on every replay and job (REG-10).** Every one-shot job (replay, forward-eval, ETL,
bench-legacy, pre-market, backup) runs under `runtime.jobs.run_with_deadline(fn, timeout_s)` and under
`timeout` in its systemd unit or `docker compose run`. The defaults are in `config/v2/engine.yaml` `jobs:`. A job
that times out exits non-zero, raises a `JOB_TIMEOUT` alert, and leaves no partial output (it writes to a temp path
and renames on success).

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
| `regression` | legacy bug carry-over REG-01 to REG-18 (section 6.5); no skips, no xfail | yes |
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
| Data recorder (`packages/data-recorder`) | PR #8 | **Reuse as-is** | Keeps running as an independent backup capture. `RecorderTapeSource` reads its files for replay. It has no bid/ask depth and polls the chain every 180 s, so the round 9 depth and quote recording is new work in `marketdata` (section 2.3), not a patch to it |
| Dhan client (`packages/dhan-client`) | earlier | **Reuse as-is** | The only Dhan HTTP/WS client (no second client). `feed.MarketFeedCollector` inside `marketdata` |
| Broker adapter + order state machine + `PaperBroker` + `DhanBroker` + `reconcile` | PR #10 | **Reuse + wrap** | Add `clock=` injection, pluggable fill models, paper state rebuilt from the ledger, protective stop helper. The live gate is unchanged |
| Risk engine | PR #10 | **Reuse + wrap** | Engine clock always passed; one instance per account; add `FEED_STALE`, `STRATEGY_DAILY_LOSS` |
| Health monitor | PR #10 | **Reuse + extend** | New checks, metrics endpoint, alert rules |
| Ledger + charges | PR #10 | **Reuse + extend** | Migrations, `account_id`, `positions_v2`, checkpoint, outbox, commands |
| Event bus (`MemoryBus`, `RedisStreamsBus`, `EventAuditLog`) | PR #12 | **Reuse + extend** | Envelope v2 (compatible), stream per topic, consumer groups with `XACK` after commit, outbox publisher. Fix: `RedisStreamsBus.poll` sets `last_id` before parsing, so one bad entry raises and silently skips the good entries earlier in that batch (REG-06) |
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
- #20 (cost realism): **merged** (`c004ace`). v2 reuses its realistic fill rules (`PaperBroker` realistic branch),
  per-exchange charges (`load_rates(by_exchange=True)`, `exchange_for`) and the property tests, as the only mode.
  Its stale-quote guard is reused for ordinary exits, but not for the EOD flatten (REG-15). Its `legacy` mode and
  `paper_scalp.py` hooks are not used by v2.
- #23 (ML shadow logging): **merged** (`5c3b913`). Its shadow schema can feed the forward harness.
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
5. **Legacy regression suite** `tests/regression/test_reg_*.py` (REG-01 to REG-18, section 6.5). Every test must pass;
   none may be skipped or marked xfail.
6. **Determinism:** same tape twice gives the same output hash; rehydrate equals run; the live-like dry run over
   Redis equals the in-process replay (decisions, orders, fills compared field by field).
7. **Performance budgets** (section 6.3).
8. **Live-like dry run on recorded data:** compose with `marketdata --replay <day>` at 1x for one fixture hour and at
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
| Depth cadence per traded strike | ≤ 1 s between `DEPTH_QUOTE`s (p99 during market hours) | marketdata |
| Quote snapshot cadence | every 5 s ± 0.5 s per traded strike | marketdata |
| Time stop firing | ≤ 1 s after `fill_ts + after_s` (event time) | engine |
| Entry-location features + order planner per decision | < 5 ms p99 | engine |

### 6.4 The frozen benchmark

- Files: `paper_scalp.py`, `picker.py`, `desk_ml/event_path.py`, `desk_ml/event_parity.py`, `boss/orchestrator.py`,
  `desk/executor.py`, `analysts/legacy.py`. Their sha256 values go into `config/legacy_frozen.sha256`, and the CI job
  `frozen-legacy` fails on any change. Allowed changes: security fixes and deletion, with the manifest updated in the
  same PR and a founder-visible note.
- `python -m runtime bench-legacy --day <d>` runs `replay_paper_scalp` on the same day's recorder tape and writes
  its trades to `warehouse.bench_legacy_trades`. The founder page shows "new stack vs legacy benchmark" as
  information, never as a target to match.

### 6.5 Legacy bug carry-over (must-pass tests)

Founder addenda 1 and 5 (2026-09-27): every bug found and fixed in the legacy engine carries into v2 as a named
regression requirement (REG-14 to REG-17 and the REG-12 update come from addendum 5, the PR #20 cost-realism
verification). Each has a test id, an owner service and the ticket that implements it. The tests live in
`tests/regression/test_reg_<nn>_*.py`, run in CI as the `regression` job, and are part of the merge gate
(section 6.2) and of the M1 exit criteria. They are written against the v2 stack; the legacy engine is not patched.

"Merged coverage today" says what the already-merged reusable components (risk engine, ledger/charges, broker
adapter/order state machine, health alarms, recorder) give us, checked against the code on `main`:
**SATISFIED** = the merged component already enforces it and v2 adds only the test; **PARTIAL** = a merged mechanism
exists, with a named gap; **NEW** = needs new work.

| ID | Requirement | Legacy source | Must-pass tests | Owner service | Ticket | Merged coverage today |
|---|---|---|---|---|---|---|
| **REG-01** | Decisions only see **closed** bars. No series is stamped at the last print before its bucket closes. | `paper_scalp.resample_closes_3m` stamps each 3m bar at its last 1m print (`ts=grp[-1][0]`), which `logit_side_series` then reads early; PR #11 (S/R preload used the replayed day's own high/low; follow-gap compared against the last tick of the current minute); PR #21 (saved weight state from the future) | `REG-01a` resampled bars have `available_ts = bucket close`; `REG-01b` random-cut causality (truncate the future at 20 random cuts per fixture day, decisions ≤ cut unchanged); `REG-01c` future poisoning; `REG-01d` zero future lookups (`FeatureView(strict=True)` raises; lookup counter = 0); `REG-01e` levels and session state use prior-day data only; `REG-01f` state files dated after the session are refused | marketdata (bars), engine: indicators, strategies | V2-03, V2-05, V2-16 | **PARTIAL.** `RegimeLabeller` is causal and PR #21 refuses future weight state (both reused). Everything else is new. |
| **REG-02** | Every open position has an enforced stop **at all times**, including after a restart or feed reconnect. | Stop-loss hole of about ₹193k found in the Phase 2 review | `REG-02a` invariant after every envelope in every fixture: each open position has a resting protective stop and a tactical stop; `REG-02b` `kill -9` after the entry fill, before the stop is placed, then restart places the stop before any entry; `REG-02c` feed DOWN/UP re-checks stops; `REG-02d` a position without a stop raises a CRITICAL alert and blocks entries; `REG-02e` bad risk YAML does not block the stop or the exit | engine: oms (router, positions) | V2-08, V2-09, V2-10, V2-12, V2-14 | **PARTIAL.** `PaperBroker` supports super orders (target + SL-M, OCO, trailing) and the risk engine allows exits under the kill switch. Gaps: nothing enforces "every position has a stop"; `PaperBroker` resting orders live in memory and are lost on restart; a bad `risk_limits.yaml` makes `_decide` veto exits too. |
| **REG-03** | A forced close targets the **exact held instrument and strike**. | F2: the legacy forced close hit the wrong strike | `REG-03a` spot moves 3 strikes after entry, then founder `CUT_LOSS`, EOD flat, fail-safe MTM and kill switch each exit the held `instrument_id` with the held qty; `REG-03b` exit intents are built only from the position record (`brokers.exit_intent`), never from the strike router; `REG-03c` ledger position is flat for that instrument afterwards | engine: oms (positions) | V2-09 | **PARTIAL.** `brokers.exit_intent(position)` already builds the exit from the held `Position` (symbol, instrument_id, net_qty), and `PaperBroker` keys positions by symbol. v2 must use only that path; test is new. |
| **REG-04** | No open ticket may vanish from tracking. Positions are rebuilt from the durable ledger on restart, and reconciled. | F3: open tickets disappeared from tracking | `REG-04a` `kill -9` at each point of the fault matrix, then every open position before the crash is open after it with the same qty and exit plan; `REG-04b` reconciliation: a planted broker-only position and a planted ledger-only position each give `RECON_MISMATCH`, block entries and allow exits; `REG-04c` the UI snapshot lists every ledger-open position | engine: ledger, runtime (recovery) | V2-10, V2-13 | **PARTIAL.** Append-only ledger `positions`/`trades`, `brokers.reconcile` (positions and open orders) and `risk_snapshot` rebuilt from disk exist. Gaps: `positions` is keyed by `symbol` only (no account), there is no restart sequence, and the paper broker is not rebuilt. |
| **REG-05** | Risk caps are enforced **inside the risk engine veto**, not only in config: ₹30k/trade, ₹90k/day loss, 25 lots max, 3 positions max (paper values, configurable). Halt and kill-switch semantics from PR #14. | PR #14 (paper risk limits sized; MTM halt persisted; corrupt halt file fails closed; flatten still runs) | `REG-05a` one table test per cap, including a trade that would *cross* the daily cap; `REG-05b` a missing or renamed cap key fails validation, never disables the cap; `REG-05c` kill switch (flag or file) vetoes entries and allows exits/flatten; `REG-05d` MTM error closes at last good quote and blocks entries for the session; `REG-05e` an unreadable halt record blocks every entry; forced closes re-book at the same time and price on rehydrate | engine: risk-engine, oms | V2-08 (caps tests), V2-09 + V2-10 (halt port) | **SATISFIED for the caps:** `MAX_LOSS_PER_TRADE`, `MAX_DAILY_LOSS` (incl. would-exceed), `MAX_LOTS`, `MAX_OPEN_POSITIONS`, kill switch flag and file are all in `RiskEngine._entry_veto`, and `load_limits` rejects missing keys; paper values are in `config/risk_limits.yaml`. **PARTIAL for the halt:** PR #14's halt lives in legacy `desk/executor.py` and a JSON file, so it is ported to a durable `session_halts` table. |
| **REG-06** | A corrupt or partial log or event line mid-day never erases earlier trades or state. Per-line guarded parsing; the first bad line is recorded durably. | PR #18 scenario 2e (corrupt founder log mid-day); PR #14 corrupt halt file | `REG-06a` for each line-parsed input (tapes, recorder files, command log, Redis stream entries): insert a truncated line, a non-JSON line and a wrong-schema line mid-day, then trades and state before it are unchanged and the lines after it still load; `REG-06b` the first bad line is written once to `ingest_errors` (path, line number, byte offset, sha256) and survives restart; `REG-06c` a bad Redis entry does not skip the good entries around it | events, marketdata (sources), control, ledger | V2-02, V2-03, V2-10, V2-11, V2-D2 | **PARTIAL.** The ledger and event audit are SQLite with no-delete/no-update triggers, so they have no line parsing to corrupt (SATISFIED there). Gaps: `RedisStreamsBus.poll` sets `last_id` before `Event.from_json`, so a bad entry raises and the good entries earlier in that batch are never dispatched; the JSONL readers have no durable bad-line record; PR #18 is unmerged. |
| **REG-07** | Bad YAML or config never stops the bus. The last-good config is kept and an alarm is raised. | Founder addendum (legacy finding) | `REG-07a` corrupt each engine YAML mid-session: the bus keeps dispatching, a `CONFIG_INVALID` alert is raised once, entries block, and exits/flatten run on the last-good values; `REG-07b` a valid file clears the block; `REG-07c` start-up with no valid config (no last-good yet) runs exits-only: no entries, exits and flatten allowed, CRITICAL alert | contracts (config loader), engine: risk-engine | V2-04, V2-08 | **PARTIAL.** `MemoryBus._dispatch` catches subscriber exceptions, so the bus keeps running, and the risk engine fails closed. Gaps: no last-good copy, no alarm, and exits are vetoed with `ENGINE_ERROR` when the YAML is bad. |
| **REG-08** | The ETL and data loaders skip and log bad lines and never crash. | Founder addendum (legacy finding) | `REG-08a` a fixture folder with truncated gzip, bad JSON lines, an empty file and a wrong-schema row: ETL finishes, counts skipped rows per file, writes `ingest_errors`, and loads the rest; `REG-08b` a second run is idempotent | warehouse (ETL), marketdata (sources) | V2-03, V2-18 | **PARTIAL.** `warehouse/ingest.py` catches some parse errors but reads whole files with `json.loads(path.read_text())`; PR #19's ETL is unmerged. |
| **REG-09** | The supervisor never restart-loops: backoff, circuit breaker and an alarm. | F1: legacy supervisor restart loop | `REG-09a` a service that crashes at start: restarts back off, the breaker opens after 5 crashes in 10 minutes, and `RESTART_LOOP` is raised once; `REG-09b` `reset-breaker` restores normal restarts | runtime (services), health | V2-15, V2-14 | **NEW.** The recorder backs off per recorder (up to 300 s) and the feed reconnects with backoff (up to 30 s), but there is no circuit breaker and no restart-loop alarm. |
| **REG-10** | Every replay and job has a wall-clock timeout. | Founder addendum (legacy finding) | `REG-10a` a job that sleeps past its deadline is killed, exits non-zero, raises `JOB_TIMEOUT`, and leaves no partial output; `REG-10b` every job entry point is registered with a deadline (test enumerates them) | runtime (jobs) | V2-04, V2-15, V2-16 | **NEW.** |
| **REG-11** | Tests never write into real data folders. | `agent_rag` tests rewrote `data/knowledge` | `REG-11a` a repo-wide pytest guard makes `data/` and `config/` read-only during tests (write attempts fail the test) and every fixture uses `tmp_path`; `REG-11b` the checkout's `git status` is clean after the full suite | CI (all packages) | V2-01 | **NEW.** PR #16 (unmerged) adds a similar guard for `desk-ml` only. |
| **REG-12** | The **verified** cost stack is applied to every simulated fill: Dhan ₹20/order brokerage, STT 0.15% of sell premium, NSE exchange 0.0355299%, **BSE ₹3,250/crore**, SEBI fee, stamp 0.003% on buy, GST 18%, NIFTY lot 65. Slippage comes from the recorded bid/ask half-spread once recorded; until then the fallback is the Round 8 FC-MEAS moneyness table (decision K15; flat 0.20 only as a sensitivity). GST 18% applies to brokerage + exchange + SEBI only (K12); the NSE rate includes IPFT (K14). **Realistic fills are the only mode in v2**; there is no optimistic legacy mode. | Legacy paper P&L used an older cost model; Round 8 friction; founder addenda 1 and 5 (PR #20 verification) | `REG-12a` golden contract-note test per component for a buy and a sell at 65 × 25 lots, on NIFTY (NSE rate) and SENSEX (BSE rate); `REG-12b` every paper fill in every fixture has a `charges` row (no fill escapes the ledger); `REG-12c` lot size comes from the instrument master fixture (65), never a literal; `REG-12d` a strike with recorded bid/ask fills at the ask/bid (slippage source `depth`); without it, LTP ± the FC-MEAS half-spread for its moneyness bucket and time of day (`fcmeas`: ATM 0.20/0.25/0.30, ITM100 0.30/0.35/0.40, ITM200 0.35/0.40/0.45); the source is recorded on each fill; reports also show the flat-0.20 sensitivity; `REG-12e` no v2 code path or config can select `cost_model: legacy` (config schema rejects it; `PaperBroker` is always built realistic) | engine: brokers (fills), ledger (charges) | V2-08 | **PARTIAL (mostly satisfied on `main` after PR #20).** `order_charges` has every component, including per-exchange rates via `load_rates(by_exchange=True)` (NSE `0.0003553`, BSE `0.000325`); `Ledger.record_fill` charges every fill with its exchange; `paper_costs.yaml` has the 0.20 pt/side default and `use_recorded_spread` (v2 uses the FC-MEAS table instead, K15). Gaps: `cost_model: legacy` is still the default on `main`; the flat legacy rate `0.0003503` still exists for legacy callers; the NSE value includes ₹0.01/crore IPFT, which is kept (K14, decided). |
| **REG-13** | Exit params are part of every strategy and config gate. | Infra PR #19's gate compared results but did not hash exit params | `REG-13a` changing any exit field (stop, target, time stops, trail, partials, flat time, strike-router rules) changes the strategy `params_hash` and the engine `config_hash`; `REG-13b` the forward harness refuses a spec whose exit params differ from the prereg lock; `REG-13c` the gate fails a PR that changes exit params without a new strategy version | engine: strategies, forward harness, CI gate | V2-06, V2-06b, V2-16, V2-20a | **NEW.** |
| **REG-14** | Take-profit and other limit orders fill **only at the limit price** when price trades through it, never at an overshoot print. Stops fill at or worse than the trigger. | PR #20 verification (`desk/specs/reliability_evidence/pr20_verify.md`, on the box, not in the repo): fixing the overshoot-print rule alone moved paper P&L by −₹164,934 over 7 days of ALL3 | `REG-14a` a buy/sell limit is not filled by a print or quote exactly at the limit; `REG-14b` a print one tick through fills at the limit; `REG-14c` a gap print far through the limit (overshoot) still fills at the limit, never at the print; `REG-14d` an SL-M sell stop triggered by a gap print fills at that print minus slippage (≤ trigger), and a buy stop at print plus slippage (≥ trigger); `REG-14e` property test over random price paths: no limit fill is ever better than its limit, and no stop fill is ever better than its trigger | engine: brokers (fills) | V2-08 | **SATISFIED in the merged realistic branch** (`PaperBroker._fill_price_realistic`: trade-through by one tick, at the limit; SL-M at print ± slippage, side-rounded; `test_paper_fill_properties.py`). PARTIAL overall: only when `cost_model="realistic"`, which is not the default on `main`; v2 makes it the only mode. |
| **REG-15** | The end-of-day flatten is **never held back by the stale-quote guard**. | PR #20: `desk_ml.costs` defers any exit on a quote older than `exit_quote_max_age_s` (90 s) until `stale_exit_hard_flatten_ist` (15:20), and that includes the 15:16 `FLATTEN_1516` | `REG-15a` all quotes stale from 15:10: the EOD flatten is sent at `flat_by_ist` (15:15), not later; `REG-15b` it is priced at the last good print flagged `STALE_QUOTE`, with an alert; `REG-15c` ordinary (non-EOD) exits still wait for a fresh quote up to the guard limit; `REG-15d` no position is open after `flat_by_ist` on any fixture (shared with the REG-02 invariant) | engine: oms (positions/exits) | V2-09 | **NEW.** The merged guard holds the EOD flatten until 15:20; v2 exempts EOD, founder and kill-switch flattens from it. |
| **REG-16** | A malformed cost config fails closed with an alert, never a crash. | `ledger.charges.load_rates` raises `ValueError` on missing or bad keys, and nothing catches it | `REG-16a` corrupt, truncated or key-missing `charges.yaml` / `paper_costs.yaml` at start: the engine runs exits-only, raises `CONFIG_INVALID(costs)`, and does not crash; `REG-16b` corrupted mid-session: last-good rates are kept, entries block, exits are charged at the last-good rates; `REG-16c` a fill booked with no valid rates is `charges_status = PENDING`, never zero, and is recharged when a valid file returns | contracts (config loader), ledger (charges) | V2-08, V2-10 | **NEW.** Validation exists (`load_rates` rejects missing keys), but the error is uncaught, with no last-good copy and no alert. |
| **REG-17** | Every closed trade row carries its **exchange tag** (NSE vs BSE rates differ). | PR #20 added per-exchange charges but no exchange column on `trades` | `REG-17a` every closed trade in NIFTY and SENSEX fixtures has `exchange` = NSE / BSE matching `underlying_exchange`; `REG-17b` an underlying missing from the map is refused at entry (no trade with `UNKNOWN`); `REG-17c` the charges on a trade match the rate of its tagged exchange; `REG-17d` the migration backfills existing rows from the map | ledger | V2-10 | **PARTIAL.** `exchange_for()` and per-exchange charges exist, and a missing underlying raises; `trades` has no exchange column. |
| **REG-18** | No hard-coded tight cancel exits. Every exit comes from a declared per-strategy primitive (catastrophic, structural, ATR or time stop, grace period, signal-flip, target/partial/trail) or from founder, kill-switch or EOD. | Founder addendum 6 / round 10: the -4/-5 pt loss cluster came from `CANCEL_AGAINST` (`ticket_against_market`), `CANCEL_ADVERSE`, the stall cancel and `COVER_LONG_UNWIND` hard-coded in `paper_scalp.py` | `REG-18a` on every fixture, every exit reason is in the allowed list and names the `ExitPlan` field that fired; `REG-18b` a position whose plan has only a catastrophic stop and a time stop is never closed by anything else while the premium wanders ±5 pts; `REG-18c` a grace period blocks structural, ATR, time and flip exits but never the catastrophic stop, EOD flatten or founder commands; `REG-18d` a plan without a catastrophic stop refuses to load; `REG-18e` changing `config/v2/exits/defaults.yaml` does not change a running strategy's resolved plan (it needs a new version) | engine: oms (positions/exits), strategies | V2-06, V2-09 | **NEW.** No merged component has exit logic outside the legacy engine; the legacy cancels are frozen and not ported. |

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
  - Founder addendum 1 (2026-09-27): every legacy bug fixed becomes a named regression requirement, REG-01 to REG-18 (REG-14 to REG-17 from addendum 5, REG-18 from addendum 6)
    (section 6.5), in the merge gate and the M1 exit criteria.
  - Founder addendum 5 (PR #20 cost realism, merged `c004ace`): limits fill only at the limit on a trade-through
    and stops at or worse than the trigger (REG-14); the EOD flatten is never held back by the stale-quote guard
    (REG-15); a malformed cost config fails closed with an alert (REG-16); every trade carries its exchange tag
    (REG-17); the verified cost stack with the BSE rate, recorded half-spread slippage and a fallback (0.20 pt/side
    in the addendum, changed to the FC-MEAS moneyness table by decision K15)
    (REG-12). Realistic fills are the only mode in v2.
  - Desk-lead decisions (2026-09-27) on K1, K3-K9, K12 and K14-K17 (build plan §4.2). K1, K3 and K5 are desk defaults
    pending founder review in the 08:00 CT report; the rest are decided. The one that changes the design is K15: the
    no-bid/ask fallback fill is the FC-MEAS moneyness table, with flat 0.20 as a sensitivity.
  - Decisions K18, K19 and K20 (2026-09-27):
    - K18: round 11 is preregistered and hashed before outcomes, and its trials count toward the budget (about 4,621
      after round 10, plus deep dive 1's 6,693 on its own book). Exit defaults are versioned and hashed.
    - K19: C10 is met; the boss records stretch with no veto, and a veto can only return through preregistered
      research plus a new strategy version.
    - K20: marketable limits only; `max_chase_ticks: 2` and a 2 s fill timeout per strategy card; `MISSED_CHASE` with
      the price chasing would have paid; one recalibration from 5 sessions of V2-D2 depth, versioned.
  - Founder addendum 6 (round 10 result): no entry-location rule. The desk uses marketable next-bar entries (chase
    default); `pullback_limit` and `wait_consolidation` are supported but off, and missed signals are counted if a
    resting limit is ever used. The boss records stretch (zone, EMA20, TWAP) with no veto power. The exit layer is
    per-strategy primitives (catastrophic, structural, ATR and time stops, grace period, signal-flip), with no
    hard-coded tight cancels (REG-18); round 11 sets the defaults.
  - Founder addendum 3 (superseded in part by addendum 6): entry location is first-class for the boss (hard stretch veto, `ENTRY_STRETCHED`) and the
    desk (order planner: CHASE / LIMIT with timeout / WAIT for one consolidation candle), with trade-through limit
    fills in simulation and `ENTRY_PLAN` logging for daily review. Log-only until research round 10 sets the
    thresholds (section 2.18).
  - Founder addendum 2 (research round 9): ≤ 1 s depth and ≤ 5 s quote snapshots with bid/ask for ATM/ITM100/ITM200
    on both sides; OI update frequency; the strike router with shadow-priced alternatives; time stops as a
    first-class exit; the forward-test harness, off by default. All in the new system only; `paper_scalp.py` is
    not patched.
- **Rejected:**
  - Byte-identical parity with the old engine as a merge gate (it protects losing behaviour).
  - A microservice per role on the hot path (network hops and lost determinism for no gain at this scale).
  - Postgres on day 1 (single writer; SQLite-WAL is enough until customers), and MySQL or embeddings (counsel
    rejected them).
  - Exit tuning as a work item (Round 8 §4.3).
  - LLM on the decision path.
- **UNKNOWN / DATA_INSUFFICIENT:**
  - Dhan depth availability and update rate for every traded strike. The lab-box depth recorder starts 28 Sep; the
    in-repo recorder is V2-D2.
  - The byte layout of Dhan's FULL packet (5-level depth). `dhan_client.decode` is a placeholder today. The decoder
    must be verified against one captured frame on the founder's box; raw frames are kept until then.
  - Whether the option chain REST response really carries bid/ask. The PR-001 recorder reads `bid_price`/`ask_price`
    without a verified field name.
  - OI update cadence (it decides whether E1's lag rule is stale); V2-D2 measures it from day 1.
  - Round 11 exit defaults (due 08:00 CT Sunday). Until then every strategy must declare its own exit primitives.
  - The recalibrated `max_chase_ticks` / `chase_timeout_s` (after 5 sessions of V2-D2 depth).
  - How well `ask − est_delta × (spot − zone)` predicts the option price when the underlying reaches the zone (IV and
    decay move meanwhile). The forward harness measures it; if it is poor, LIMIT becomes an engine-side zone trigger.
  - Futures volume quality per minute (it decides whether VWAP and POC come from futures or fall back / go absent).
  - Which legacy findings F1/F2/F3 and the ₹193k stop hole map to exact code lines. They come from the founder's
    Phase 2 review, which is not in the repo. The REG tests specify the behaviour, not the old code path.
  - Whether Dhan's feed exposes exchange timestamps for every packet type; if not, `event_ts` = receipt time.
  - Dhan access-token lifetime and refresh flow for unattended VPS runs (`.env.example` note: VERIFY).
  - SEBI registration path for a signal/algo product (founder/legal).
  - The final shape of the separately built registry/basket module (only the contract in section 2.5 is assumed).
- **Cross-team citations:** 04 `SIGNAL_STAGING.md` (5m indicators confirm or kill only); 05 `CUSTOMER_TALK.md`
  (customer copy); 06 `EVENT_MEMORY.md` (event days held); 09 five-pass before any paper or customer book. KEEP_ALL
  untouched: no `STRAT-*` is deleted or relabelled; new strategy ids are research ids or `MIX-*`, never `STRAT-015+`.

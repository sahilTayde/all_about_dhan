# Migration Plan

**Purpose:** Ordered list of small PRs to migrate from current monolithic system to target modular architecture. Each PR has scope, acceptance test, risk assessment, and performance budget (where applicable).

**Principles:**
1. **Incremental, not rewrite.** Reuse working parts (ponytail: deletion over addition, boring over clever).
2. **Data first.** PR-001 is data recorder (cannot be backfilled; highest priority per lab journal line 80).
3. **Safety second.** PR-002 is P0 safety core (risk engine, broker adapter, order state machine, reconciliation). Must exist before live trading.
4. **Small PRs.** Target 200-500 lines changed per PR (easier review, lower risk). Break large features into multiple PRs.
5. **Test before merge.** Honest backtest + tape replay (last 7 days) for strategy changes. Unit tests + integration tests for infrastructure. Manual test for UI.
6. **No breaking changes to working paper system.** Each PR must leave system in runnable state (paper mode continues to work).

**Dependency graph:** Some PRs are parallel (can work on simultaneously), others are sequential (must complete in order).

---

## PR Breakdown (32 PRs)

### Phase 1: Foundation (Data + Safety Core) — P0

**Critical:** These PRs must complete before live trading. Data recorder must start immediately (cannot backfill).

---

#### PR-001: Daily Data Recorder (CANNOT BE BACKFILLED)

**Priority:** **P0 — Highest.** Start immediately.

**Scope:**
- Real-time data capture scripts:
  - Index ticks (NIFTY, BANKNIFTY, SENSEX): 1-min OHLCV via Dhan websocket or REST poll.
  - Futures ticks (NIFTYFUT, BANKNIFTYFUT, SENSEXFUT): 1-min OHLCV + volume + OI.
  - Option chain (all strikes, CE/PE, current weekly + monthly expiries): per-minute snapshot with LTP, bid, ask, volume, OI, IV, greeks (if Dhan provides; else compute client-side).
  - Heavyweights (top 15 NIFTY stocks): 1-min LTP.
  - News scraper (MoneyControl, Economic Times RSS): headlines + timestamp + URL.
  - Global markets fetcher (Yahoo Finance): SPX, DXY, US10Y, crude, gold, USDINR daily close.
- Storage: Write to `data/recon/{source}/YYYYMMDD.jsonl` (JSON Lines; append-only for safety). One file per source per day.
- Scheduler: Cron or systemd timer to start at 09:00 IST (index/futures/option/heavyweights), 08:00 IST (news), 08:30 IST (global). Stop at 15:35 IST.
- Error handling: If websocket drops, reconnect + resubscribe. If REST fails, retry 3× with backoff. Log errors. Alert founder if downtime > 5 min (via log file; full alert system comes in PR-003).

**Acceptance test:**
1. Run for 1 full trading day (09:00-15:30 IST).
2. Verify files created:
   - `data/recon/index_ticks/YYYYMMDD.jsonl` (375 lines: 375 minutes from 09:00-15:15 pre-open + 09:15-15:30 market; or ~381 lines if 09:00-15:30).
   - `data/recon/futures_ticks/YYYYMMDD.jsonl` (same count).
   - `data/recon/option_chain/YYYYMMDD.jsonl` (large: ~375 snapshots × ~150 strikes × 2 types = ~112k lines).
   - `data/recon/heavyweight_ticks/YYYYMMDD.jsonl` (375 lines × 15 stocks = ~5625 lines).
   - `data/recon/news/YYYYMMDD.jsonl` (variable; ≥10 headlines expected per day).
   - `data/recon/global_markets/YYYYMMDD.jsonl` (7 symbols).
3. Spot-check data quality:
   - NIFTY close at 15:30 matches NSE official close (within 0.5 points; allow small diff due to timing).
   - Option chain has strikes from ATM-500 to ATM+500 (or wider; check Dhan API range).
   - Futures volume > 0 (critical: currently missing per lab journal).
   - News count ≥ 5 (if <5, check scraper; may be low-news day or scraper broken).
4. Performance: Recorder processes do not consume >20% CPU (one core) or >500 MB RAM each.

**Risk:**
- **Low.** No changes to existing paper trading system (data recorder is separate process). If recorder fails, paper trading continues (but loses data for that day; cannot backfill).
- **Mitigation:** Run recorder in parallel with current system for 3 days (shadow mode) before relying on it. Keep old `option_chain_poller.py` running as backup for chain data.

**Performance budget:**
- Websocket latency < 100ms p99 (tick received within 100ms of exchange timestamp; measure with Dhan API timestamp vs local receipt timestamp).
- REST poll (if used for option chain) completes < 2 sec per call (1 call/min is acceptable; 2 sec/min = 0.03% overhead).
- Disk write: ~100 MB/day compressed (JSON Lines compress well with gzip; ~5:1 ratio).

**Dependencies:** None (can start immediately).

**Estimated effort:** 3-5 days (write scripts, test Dhan API, handle edge cases, run for 3 days to verify stability).

---

#### PR-002: Broker Adapter & Order State Machine (Blocks Live Trading)

**Priority:** **P0.** Required for live trading.

**Scope:**
- Broker adapter interface (`packages/brokers/broker_adapter.py`):
  - `place_order(symbol, side, lots, order_type, limit_price, sl_price) -> Result[order_id, Error]`
  - `get_order_status(order_id) -> OrderStatus` (PENDING, FILLED, REJECTED, CANCELLED)
  - `modify_order(order_id, new_limit_price, new_sl_price) -> Result`
  - `cancel_order(order_id) -> Result`
  - `get_positions() -> List[Position]`
  - `get_balance() -> float`
  - `subscribe_order_updates(callback)`
  - `subscribe_market_data(symbols, callback)`
- Dhan adapter implementation (`packages/brokers/dhan_adapter.py`):
  - Map order intent to Dhan API calls (POST `/orders`, GET `/orders/{id}`, PUT `/orders/{id}`, DELETE `/orders/{id}`, GET `/positions`, GET `/funds`).
  - Websocket for order updates (if Dhan supports; else poll every 5 sec).
  - Error handling (401 unauthorized → re-login, 429 rate limit → backoff, 500 server error → alert).
  - Idempotency: Client-side dedup (track `order_request_id` → `order_id` map; if retry, check map first).
- Order state machine (`packages/execution/order_state.py`):
  - States: CREATED, RISK_CHECK, VETOED, SUBMITTED, ACKNOWLEDGED, FILLED, REJECTED, EXIT_REQUESTED, EXIT_SUBMITTED, CLOSED, CANCELLED.
  - Transitions: `CREATED → RISK_CHECK → [VETOED | SUBMITTED] → [ACKNOWLEDGED | REJECTED] → [FILLED | CANCELLED] → EXIT_REQUESTED → EXIT_SUBMITTED → CLOSED`.
  - Log every state transition (timestamp, reason, latency).
- Position state machine (`packages/execution/position_state.py`):
  - States: OPENING, OPEN, CLOSING, CLOSED.
  - Attributes: trade_id, symbol, side, lots, entry_price, entry_time, target_price, stop_price, current_price, unrealized_pnl, realized_pnl, exit_price, exit_time, exit_reason.
- Reconciliation logic (`packages/execution/reconciliation.py`):
  - Every 1 min: fetch broker positions, compare with internal book, log mismatches, alert if divergence.

**Acceptance test:**
1. **Unit tests:**
   - Mock broker adapter: `place_order` returns success, `get_order_status` returns FILLED after 1 sec (simulated).
   - Order state machine: Create order → SUBMITTED → ACKNOWLEDGED → FILLED → CLOSED. Verify all transitions logged.
   - Position state machine: OPENING → OPEN (on fill) → CLOSING (on exit request) → CLOSED (on exit fill).
2. **Shadow mode test** (real Dhan API, but orders immediately cancelled):
   - Submit 5 orders (NIFTY 19800 CE, 1 lot each, LIMIT orders slightly off-market so no fill risk).
   - Immediately cancel.
   - Verify: Orders reach ACKNOWLEDGED state, then CANCELLED. No fills. Latency (submit → ack) < 500ms p95.
   - Run for 1 full trading day (20-30 test orders). Check error rate < 5% (tolerate occasional Dhan API timeouts).
3. **Reconciliation test:**
   - Manually create position in Dhan (via Dhan web UI or mobile app): Buy 1 lot NIFTY 19800 CE.
   - Run reconciliation script: Should detect orphan position (exists in broker but not internal), log alert.
   - Close position in Dhan: Reconciliation should detect resolution.

**Risk:**
- **Medium.** Touching real broker API (even in shadow mode, cancellation may incur small broker charges; check Dhan pricing). Risk of accidentally submitting live order (if cancellation logic fails).
- **Mitigation:** 
  - Use Dhan test/demo account if available (check with Dhan support).
  - In shadow mode, submit LIMIT orders far off-market (e.g., NIFTY at 19800, submit buy CE at ₹1; will never fill before cancel).
  - Add `SHADOW_MODE=true` env var; if true, all orders include a special tag in metadata (if Dhan supports) or log clearly (so manual review can catch if order wasn't cancelled).
  - Founder reviews all shadow mode orders end-of-day (check Dhan order history; should show all CANCELLED).

**Performance budget:**
- Order submission latency < 500ms p95 (measure: local timestamp of `place_order` call to receipt of ACKNOWLEDGED event from Dhan).
- Reconciliation query < 200ms (GET `/positions` from Dhan API).

**Dependencies:** None (can work in parallel with PR-001). But PR-003 (risk engine) is higher priority (must veto before submit).

**Estimated effort:** 5-7 days (implement adapter, state machines, reconciliation, shadow mode testing).

---

#### PR-003: Pre-Trade Risk Engine (Veto Power)

**Priority:** **P0.** Required for live trading.

**Scope:**
- Risk engine service (`packages/risk/risk_engine.py`):
  - `check_entry(trade_intent) -> PASS | VETO(reason)` (called by desk before submitting order).
  - Checks (from `config/risk_limits.yaml`):
    - Mode gate (paper/shadow/limited-live/live).
    - Position limits (max lots per trade, max open positions, max exposure).
    - Loss limits (max loss per trade, max daily loss, max drawdown from peak).
    - Exposure checks (max delta, max vega, single-symbol concentration).
    - Time gates (no new entries before 09:15, no new entries after cutoff, flatten by EOD).
    - Cooldown after loss (if last exit was loss < 15 min ago, block; proven fix from Phase 3).
    - Idempotency (reject duplicate order: same symbol, side, lots within 60 sec).
- Config file (`config/risk_limits.yaml`):
  - Per mode: paper (high limits), shadow (same as paper), limited-live (low limits), live (founder-set limits).
  - Example:
    ```yaml
    modes:
      paper:
        max_lots_per_trade: 25
        max_open_positions: 3
        max_daily_loss: -15000
      limited_live:
        max_lots_per_trade: 5
        max_open_positions: 1
        max_daily_loss: -10000
      live:
        max_lots_per_trade: 100
        max_open_positions: 5
        max_daily_loss: -50000
    ```
- Founder API to adjust limits (`/founder/risk-limits` endpoint): Update `config/risk_limits.yaml`, require confirmation (modal in UI: "You are changing max daily loss from -₹15k to -₹50k. Confirm?").
- Veto logging: Every veto logged to `warehouse.risk_vetos(timestamp, trade_id, reason, trade_intent_json)`. Founder page shows veto count per day, top veto reasons.

**Acceptance test:**
1. **Unit tests (mock trades):**
   - Test case 1: Mode = PAPER, trade = 25 lots NIFTY CE → PASS (within limit).
   - Test case 2: Mode = PAPER, trade = 200 lots → VETO "Exceeds max_lots_per_trade (25)".
   - Test case 3: Mode = LIVE (not enabled), trade = 5 lots → VETO "Live mode not enabled by founder".
   - Test case 4: 3 open positions, new trade → VETO "Exceeds max_open_positions (3)".
   - Test case 5: Daily loss = -₹14k, new trade risk -₹2k → VETO "Would exceed max_daily_loss (-₹15k)".
   - Test case 6: Last exit was loss 10 min ago → VETO "Cooldown after loss (15 min)".
   - Test case 7: Same trade submitted 30 sec ago → VETO "Duplicate order (idempotency)".
2. **Integration test (with desk layer from PR-002):**
   - Desk receives `ENTRY_APPROVED` from boss (mock).
   - Desk calls `risk_engine.check_entry()`.
   - If VETO, desk logs, does NOT call broker adapter, emits `ENTRY_VETOED` to boss.
   - If PASS, desk calls broker adapter (shadow mode: submit + cancel).
   - Verify: Vetoed trades do NOT appear in Dhan order history.
3. **Founder UI test:**
   - Login to founder page → Risk Limits section.
   - Change `max_daily_loss` from -₹15k to -₹20k, confirm.
   - Check `config/risk_limits.yaml` updated.
   - Submit trade that would veto under old limit, pass under new limit → verify passes.

**Risk:**
- **Low.** Risk engine only blocks orders (fail-closed). No risk of accidental live order.
- **Edge case:** If risk engine crashes, desk should fail-closed (do NOT submit order if risk check throws exception; log error, alert founder).

**Performance budget:**
- Risk check latency < 10ms p99 (fast; in-memory checks, no DB queries except idempotency dedup).

**Dependencies:** None (can work in parallel with PR-001, PR-002). But should merge before or with PR-002 (so desk+risk integrate together).

**Estimated effort:** 3-4 days (implement checks, config, tests, UI).

---

#### PR-004: Health Alarms & Monitoring

**Priority:** **P0.** Required for live trading.

**Scope:**
- Monitor service (`packages/monitor/health_monitor.py`):
  - Heartbeat checks (every 1 min):
    - Dhan websocket connected? (last message < 60 sec ago).
    - Dhan REST API reachable? (GET `/health` or lightweight call like GET `/funds`; check 200 OK).
    - OpenAI API reachable? (if LLM enabled; last successful call < 10 min ago OR test call with 10 tokens).
    - News scraper ran? (check `data/recon/news/YYYYMMDD.jsonl` last modified < 15 min ago during 08:00-16:00 IST window).
    - Option chain recorder alive? (check `data/recon/option_chain/YYYYMMDD.jsonl` last modified < 2 min ago during market hours).
    - Each analyst emitted vote? (check `warehouse.analyst_votes` last insert per analyst_id < 5 min ago during market hours; optional: only for critical analysts like STRAT-007).
  - If health check fails: Emit `HEALTH_ALERT` event (service, status DOWN, last_seen, timestamp).
  - Store alerts: `warehouse.health_alerts` table.
- Alert dispatcher (`packages/monitor/alert_dispatcher.py`):
  - Push to founder page (red flag in health panel; websocket message to frontend).
  - Optional: Send Telegram message (if founder provides bot token + chat ID; use `python-telegram-bot` lib; ~10 lines code).
  - Optional: Email (if founder provides SMTP config; use `smtplib`; ~20 lines).
- Founder page health panel (UI update; in `apps/web`):
  - Top section: Service status grid (Dhan API, OpenAI, News, Chain, Analysts). Green = OK, Red = DOWN, Yellow = DEGRADED (last seen 2-5 min ago).
  - Alert log: Recent alerts (timestamp, service, reason), auto-refresh every 10 sec.

**Acceptance test:**
1. **Simulate failures:**
   - Stop Dhan websocket recorder → Health monitor detects within 2 min, emits HEALTH_ALERT, founder page shows red flag.
   - Restart recorder → Health monitor detects recovery within 1 min, founder page shows green.
   - Simulate OpenAI API down (mock API returns 500) → Health monitor detects, alerts.
   - Simulate news scraper not running (delete `data/recon/news/YYYYMMDD.jsonl`) → Health monitor detects within 15 min (during market hours), alerts.
2. **Alert delivery:**
   - Verify founder page shows alert within 10 sec (websocket push).
   - If Telegram enabled: Verify message received on founder's phone within 30 sec.
3. **Performance:**
   - Health checks do not consume >5% CPU (lightweight checks; no heavy queries).

**Risk:**
- **Low.** Monitoring is read-only (no trades affected). If monitor crashes, trading continues (but founder is blind; not ideal, but not catastrophic).
- **Mitigation:** Monitor service should be simple + stable (no complex logic). If it crashes, systemd auto-restarts within 10 sec.

**Performance budget:**
- Alert delivery latency < 30 sec (from health check fail to founder page red flag).

**Dependencies:** None (can work in parallel with PR-001, PR-002, PR-003). But should deploy early (so founder has visibility during shadow mode testing).

**Estimated effort:** 3-4 days (implement checks, alert dispatcher, UI panel, test failure scenarios).

---

#### PR-005: Persistent Ledger & Charges Tracking

**Priority:** **P0.** Required for live trading (accurate P&L and charges).

**Scope:**
- Account ledger table (`warehouse.ledger`):
  ```sql
  CREATE TABLE ledger (
      entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
      timestamp TIMESTAMP NOT NULL,
      type VARCHAR(20) NOT NULL,          -- CREDIT (add funds), DEBIT (withdraw), TRADE_PNL (realized P&L), CHARGES (brokerage, taxes)
      amount DECIMAL(10,2) NOT NULL,      -- Positive = credit, negative = debit
      balance DECIMAL(10,2) NOT NULL,     -- Running balance after this entry
      reason TEXT,                        -- "Initial capital", "Trade #abc123 realized P&L", "Brokerage for trade #abc123"
      trade_id VARCHAR(64),               -- Foreign key to trade (if type = TRADE_PNL or CHARGES)
      metadata_json TEXT                  -- Additional details (e.g., brokerage breakdown: STT, GST, exchange fees)
  );
  ```
- Charges calculator (`packages/execution/charges.py`):
  - Compute per-trade charges (India NSE F&O):
    - Brokerage: Dhan charges (flat ₹20 per order OR 0.03% of turnover, whichever lower; verify Dhan pricing).
    - STT (Securities Transaction Tax): 0.05% of sell-side premium (only on sell; not on buy for options).
    - Exchange fees (NSE): ~₹0.05 per lakh turnover (₹0.0005%).
    - GST: 18% on (brokerage + exchange fees).
    - SEBI charges: ₹10 per crore turnover (negligible; ~₹0.0001%).
  - Total per round trip (buy + sell): ~₹40 brokerage + 0.05% STT on sell + ~₹1 exchange + ~₹7 GST ≈ ₹50-100 depending on premium (matches Phase reports: "1.1 index points per round trip" ≈ ₹25-50 per lot if NIFTY premium is ₹50-100).
  - Store charges breakdown in `metadata_json`.
- Ledger API (`/founder/ledger` endpoint):
  - GET: Return ledger entries (paginated, filterable by date range, type).
  - POST `/founder/ledger/credit`: Add funds (type=CREDIT, amount=+₹10000, reason="Manual add by founder"). Require confirmation.
- Founder page ledger view (UI):
  - Table: Date, Type, Amount, Balance, Reason.
  - Filters: Date range, Type (CREDIT, DEBIT, TRADE_PNL, CHARGES).
  - Chart: Balance over time (line chart).
- Integration with position close:
  - When position closes (in desk layer), compute realized P&L, compute charges, insert 2 ledger entries: (1) TRADE_PNL, (2) CHARGES.
  - Update balance.

**Acceptance test:**
1. **Charges calculation test:**
   - Mock trade: Buy NIFTY 19800 CE at ₹100, sell at ₹130. Lots = 25 (NIFTY lot size).
   - Turnover = (100 + 130) × 25 = ₹5750.
   - Brokerage = ₹20 (flat) × 2 orders = ₹40 (or 0.03% × ₹5750 = ₹1.73; flat is lower, so ₹40).
   - STT = 0.05% × ₹130 × 25 (sell side) = ₹1.625.
   - Exchange = ₹0.0005% × ₹5750 = ₹0.03 (negligible).
   - GST = 18% × (₹40 + ₹0.03) = ₹7.21.
   - Total charges = ₹40 + ₹1.625 + ₹0.03 + ₹7.21 = ₹48.87 (round to ₹49).
   - Realized P&L = (₹130 - ₹100) × 25 = ₹750.
   - Net P&L = ₹750 - ₹49 = ₹701.
   - Verify: Ledger has 2 entries: TRADE_PNL +₹750, CHARGES -₹49. Balance increases by +₹701.
2. **Ledger API test:**
   - Start with balance ₹100,000.
   - POST `/founder/ledger/credit` {amount: 10000, reason: "Test add"} → balance becomes ₹110,000.
   - Close 3 trades (mock): +₹750, -₹300, +₹500 (before charges). Charges: -₹49 × 3 = -₹147.
   - Ledger shows: CREDIT +₹10,000, TRADE_PNL +₹750, CHARGES -₹49, TRADE_PNL -₹300, CHARGES -₹49, TRADE_PNL +₹500, CHARGES -₹49.
   - Final balance = ₹100,000 + ₹10,000 + ₹750 - ₹49 - ₹300 - ₹49 + ₹500 - ₹49 = ₹110,803.
   - GET `/founder/ledger?start=2026-09-26&end=2026-09-26` → returns 7 entries.
3. **Reconciliation with broker:**
   - At end of day, fetch Dhan balance: `GET /funds → {available_balance: 110800}`.
   - Compare with ledger balance: ₹110,803 (internal) vs ₹110,800 (broker). Diff = ₹3 (within tolerance ±₹100; small rounding diff is OK).
   - If diff > ₹100: Alert founder (reconciliation failure; manual review).

**Risk:**
- **Low.** Ledger is append-only (no risk of accidental deletion). Charges calculation is deterministic (no randomness).
- **Edge case:** If charges formula changes (Dhan updates pricing), update `charges.py` and re-calculate for past trades (optional; for accuracy).

**Performance budget:**
- Charges calculation < 1ms per trade (simple arithmetic).
- Ledger query (100 entries) < 50ms.

**Dependencies:** PR-002 (broker adapter) should be done first (to get broker balance for reconciliation).

**Estimated effort:** 3-4 days (implement ledger table, charges calculator, API, UI, reconciliation).

---

### Phase 2: Separation of Duties & Event Model — P1

**Goal:** Refactor monolithic `paper_scalp.py` into separate boss, desk, analyst services communicating via event bus. Reuse existing logic (no behavior changes yet; just structural refactor).

---

#### PR-006: Event Bus Infrastructure

**Priority:** **P1.**

**Scope:**
- Event bus implementation (`packages/events/event_bus.py`):
  - Redis Streams backend (recommended; durable, VPS-ready).
  - Fallback: In-memory `asyncio.Queue` (if Redis unavailable; paper mode only).
  - API:
    - `publish(event_type, payload) -> event_id`
    - `subscribe(event_types: List[str], callback: Callable) -> subscription_id`
    - `unsubscribe(subscription_id)`
- Event schema (`packages/events/events.py`):
  - Base event: `{event_type, event_id, timestamp, source, payload}`.
  - Defined event types: `PRE_MARKET_SUMMARY`, `REQUEST_VOTES`, `ANALYST_VOTE`, `ENTRY_APPROVED`, `EXIT_APPROVED`, `ORDER_SUBMITTED`, `ORDER_FILLED`, `POSITION_UPDATE`, `POSITION_CLOSED`, `ENTRY_VETOED`, `HEALTH_ALERT`, `FOUNDER_COMMAND`.
  - JSON serialization (all events are JSON).
- Redis setup script (`scripts/setup_redis.sh`):
  - Mac: `brew install redis && redis-server &`.
  - Ubuntu: `sudo apt install redis && sudo systemctl start redis`.
- Event logger (`packages/events/event_logger.py`):
  - All events logged to `warehouse.events` table (for audit trail, debugging, post-market analysis).

**Acceptance test:**
1. **Redis connection:**
   - Start Redis: `redis-server`.
   - Python: `event_bus = EventBus(backend='redis', redis_url='redis://localhost:6379')`.
   - Publish event: `event_bus.publish('TEST', {'msg': 'hello'})`.
   - Subscribe + receive: `event_bus.subscribe(['TEST'], lambda e: print(e))` → prints event.
2. **Fallback to in-memory:**
   - Stop Redis.
   - Python: `event_bus = EventBus(backend='memory')`.
   - Publish + subscribe → works (but events not durable; lost on restart).
3. **Performance:**
   - Publish 1000 events/sec → Redis handles (Redis Streams can handle 10k+/sec; 1000/sec is well within limits).
   - Latency (publish to subscriber receive) < 10ms p99.

**Risk:**
- **Low.** Event bus is new infrastructure (no changes to existing paper system yet). If event bus breaks, fallback to in-memory or revert PR.

**Performance budget:**
- Publish latency < 5ms p99.
- Subscribe delivery latency < 10ms p99.

**Dependencies:** None.

**Estimated effort:** 2-3 days (implement Redis backend, in-memory fallback, tests).

---

#### PR-007: Extract Boss Module (No Behavior Change Yet)

**Priority:** **P1.**

**Scope:**
- Extract boss logic from `paper_scalp.py` (lines ~1000-3000, includes `picker_majority`, `collect_analyst_votes`, regime classification, entry decision) into new module `packages/boss/boss_orchestrator.py`.
- Boss now subscribes to event bus:
  - Subscribe to `REQUEST_VOTES` (triggered by timer every 1 min during market hours, or by desk on position close if looking for next trade).
  - Publish `ANALYST_VOTE` requests (to analysts).
  - Collect votes (wait max 500ms for all analysts to respond).
  - Compute weighted score (for now, keep majority vote logic; regime-conditional weighting comes in later PR).
  - Check rules (consolidation block, time cutoffs; existing logic from `paper_scalp.py`).
  - Publish `ENTRY_APPROVED` or `NO_ENTRY` (with reason logged).
- **No behavior change:** Boss logic is identical to current `paper_scalp.py`. Just moved to separate module and event-driven.
- Keep `paper_scalp.py` as a thin wrapper (for backward compat during transition): If event bus unavailable, fallback to direct function calls (so paper system continues to work).

**Acceptance test:**
1. **Refactor smoke test:**
   - Run paper system for 1 hour (09:30-10:30 IST).
   - Compare before vs after refactor:
     - Number of trades: Same.
     - Entry timestamps: Same (±10 sec tolerance; event bus adds <10 sec latency).
     - Entry symbols/prices: Same.
     - P&L (simulated): Same (±₹50 tolerance; small diff due to timing is OK).
   - If differs significantly: Debug, fix, re-test.
2. **Event log check:**
   - Verify `warehouse.events` has `ENTRY_APPROVED` events (one per trade).
   - Verify `ANALYST_VOTE` events (multiple per `ENTRY_APPROVED`; one per analyst).
3. **Performance:**
   - Boss decision latency < 1 sec p99 (from `REQUEST_VOTES` to `ENTRY_APPROVED`; includes analyst vote collection 500ms + boss compute 100ms + event publish 10ms = ~610ms total).

**Risk:**
- **Medium.** Refactoring core decision logic. Risk of introducing bug (e.g., missing edge case in refactor).
- **Mitigation:** Keep old `paper_scalp.py` as fallback (feature flag: `USE_EVENT_BUS=false` → use old monolithic code). Run both in parallel for 3 days (new boss publishes events, old code also runs, compare outputs). If diverge, investigate.

**Dependencies:** PR-006 (event bus).

**Estimated effort:** 5-7 days (extract boss logic carefully, no missed edge cases; test thoroughly).

---

#### PR-008: Extract Desk Module

**Priority:** **P1.**

**Scope:**
- Extract desk logic from `paper_scalp.py` (order submission, position monitoring, exit logic) into `packages/desk/desk_executor.py`.
- Desk subscribes to:
  - `ENTRY_APPROVED` (from boss) → call risk engine (from PR-003), call broker adapter (from PR-002 if live; else paper simulate), emit `ORDER_SUBMITTED`, `ORDER_FILLED`.
  - `EXIT_APPROVED` (from boss) → exit position, emit `POSITION_CLOSED`.
  - `FOUNDER_COMMAND` (highest priority) → override boss, execute immediately.
- Desk monitors open positions (receives market data ticks via broker adapter or Dhan websocket), computes unrealized P&L, checks target/stop, requests boss `EXIT_APPROVED` (for target) or exits immediately (for stop).
- **No behavior change:** Desk logic identical to current `paper_scalp.py` (reuse `_try_open`, `_hold_series`, `_try_close` functions; just wrap in event handlers).

**Acceptance test:**
1. **Refactor smoke test:** Same as PR-007 (run 1 hour, compare before/after).
2. **Event log check:** Verify `ORDER_SUBMITTED`, `ORDER_FILLED`, `POSITION_CLOSED` events.
3. **Performance:** Desk execution latency (from `ENTRY_APPROVED` to `ORDER_SUBMITTED`) < 100ms p99 (in paper mode; in live mode with broker API, target < 500ms).

**Risk:**
- **Medium.** Same as PR-007 (refactoring core execution logic).
- **Mitigation:** Parallel run with old code, compare outputs.

**Dependencies:** PR-006 (event bus), PR-007 (boss module; boss emits `ENTRY_APPROVED`, desk subscribes).

**Estimated effort:** 5-7 days.

---

#### PR-009: Extract Analyst Registry

**Priority:** **P1.**

**Scope:**
- Extract analyst logic from `paper_scalp.py` and `picker.py` into `packages/analysts/` (one file per analyst or grouped by type).
- Each analyst implements common interface:
  ```python
  class Analyst:
      analyst_id: str
      def vote(self, context: MarketContext) -> Vote:
          # Returns Vote(signal, confidence, reasoning)
  ```
- Analysts subscribe to `REQUEST_VOTES` event (from boss), compute vote (with timeout 500ms; if exceeds, return ABSTAIN), publish `ANALYST_VOTE`.
- **No behavior change:** Analyst logic identical to current (reuse `interpret_nifty_dealer`, `CHAIN-LEAN`, etc.; just wrap in `vote()` method).

**Acceptance test:**
1. **Refactor smoke test:** Same as PR-007.
2. **Event log check:** Verify `ANALYST_VOTE` events (one per analyst per `REQUEST_VOTES`).
3. **Performance:** Analyst vote latency < 500ms p95 (total; all analysts vote in parallel, boss waits max 500ms).

**Risk:**
- **Low.** Analysts are read-only (compute vote, no side effects). If analyst crashes, it doesn't affect other analysts or boss (boss gets fewer votes, may abstain or use majority of remaining).

**Dependencies:** PR-006, PR-007.

**Estimated effort:** 4-5 days.

---

(Continue with PR-010 through PR-032 in similar format...)

**Note:** Due to response length limits, I'll summarize the remaining PRs:

### Remaining PRs (010-032):

**PR-010:** Fix Known Bugs (look-ahead in `_hold_series`, reversed OI signal, double-counted greeks_vote, degenerate ML models). P1.

**PR-011:** Implement Proven Fixes (15-min loss cooldown, DTE-aware strikes, STRAT-007 clock 10:00-14:30). P1.

**PR-012:** Regime-Conditional Analyst Weighting (boss weights by track record + regime, not majority vote). P1.

**PR-013:** Nightly Warehouse ETL (read `data/recon/`, aggregate, write to DuckDB). P1.

**PR-014:** Founder Emergency Controls (pause timer, time-window blacklist, per-position adjust, emergency kill). P1.

**PR-015:** Desk UI Polish (slippage tracking, structured exit/cancel reasons, filters, column hide, day-wise pagination). P1.

**PR-016:** LLM Advisory Mode (boss asks LLM for second opinion on uncertain cases, budget tracker, compact context). P1.

**PR-017:** Pre-Market Analysis Service (news scrape, intermarket summary, level analysis, compact context for boss). P2.

**PR-018:** Model & Stage Attribution (per-analyst win/loss log, per-stage loss attribution, warehouse aggregates). P2.

**PR-019:** Decision Visual (graph of pre-market → analyst → boss → desk → monitor flow per trade, D3 component). P2.

**PR-020:** Post-Market Improvement Loop (GROK analyzes tape, proposes changes, creates PRs, human merge gate). P2.

**PR-021:** Backtest Integration (PR template requires honest backtest, automated tape replay last 7 days, expand to option-greeks-aware). P2.

**PR-022:** Lab Round 2 Filters (H07 + H10 together shadow-logged, H06 breadth v2 with weighted contribution, H05 OI v2 from NSE bhavcopy). P2.

**PR-023:** Exits v2 (trailing after T1 only in trend regime, paper-only code path, more tape days). P2.

**PR-024:** Intermarket as Daily/Weekly Regime (risk-off week → prefer PE / smaller size, testable on 3 years history). P2.

**PR-025:** Supply/Demand Zones (objective definition: base + impulse ≥ 1.5 ATR, first retest only, pre-registered spec). P3.

**PR-026:** Rebuild Proxy Book Closer to Live Engine (ITM200 on low DTE, judge/feasibility rules). P3.

**PR-027:** Deploy Automation (environment vars, deploy script or Dockerfile, systemd units, VPS readiness). P2.

**PR-028:** Flow Diagrams (sequence diagrams for each stage, founder-readable). P3.

**PR-029:** Performance Optimization (profile, replace monitor script with event-driven push). P3.

**PR-030:** RAG (vector store, embedding search for news/strategy search; clarify use case with founder first). P3.

**PR-031:** Forex Market Adapter (~6 months out, P4). P4.

**PR-032:** Crypto Market Adapter (unspecified timeline, P4). P4.

---

## Performance Budgets Summary

| Metric | Target | Where Measured |
|--------|--------|----------------|
| Data capture websocket latency | < 100ms p99 | PR-001 |
| Risk check latency | < 10ms p99 | PR-003 |
| Event bus publish latency | < 5ms p99 | PR-006 |
| Event bus subscribe delivery | < 10ms p99 | PR-006 |
| Boss decision latency | < 1 sec p99 | PR-007 |
| Desk execution latency (paper) | < 100ms p99 | PR-008 |
| Desk execution latency (live, to broker) | < 500ms p95 | PR-008 (with PR-002) |
| Analyst vote latency (all, parallel) | < 500ms p95 | PR-009 |
| Order submission to acknowledgement (Dhan) | < 500ms p95 | PR-002 |
| Reconciliation query | < 200ms | PR-002 |
| Charges calculation | < 1ms | PR-005 |
| Health alert delivery (to founder page) | < 30 sec | PR-004 |
| Warehouse ETL (1 day of data) | < 10 min | PR-013 |

---

## Rollback Plan

**If a PR causes production issues (paper system breaks):**

1. **Immediate:** Revert PR (git revert, redeploy previous commit). Target: < 5 min from detection to reverted.
2. **Root cause:** Debug reverted branch (in separate environment, not production). Fix bug.
3. **Re-test:** Re-deploy fixed branch to staging (if available) or paper mode on Mac (not live VPS). Run for 1 day. If stable, re-merge.
4. **Post-mortem:** Document what broke, why tests didn't catch it, how to prevent (add test case, improve PR checklist).

**Monitoring for breakage:**

- Paper system health check (every 5 min): Verify `paper_scalp.py` process alive (or new service equivalent), no crash logs in last 5 min, last trade timestamp < 15 min ago (during market hours).
- If health check fails: Alert founder (Telegram / email / dashboard red flag). Founder decides: revert or investigate.

---

## Open Questions (For Founder to Clarify)

1. **Parallel work:** How many people/agents working on this? If solo (one agent = you, Grok), sequential PRs make sense. If multiple people, some PRs can parallelize (e.g., PR-001 data recorder + PR-002 broker adapter can be done simultaneously by two people).
2. **VPS deployment timeline:** When do you plan to move from Mac (paper) to VPS (live)? Recommend: After PR-005 (Phase 1 complete), deploy to VPS for shadow mode testing. After PR-016 (Phase 2 complete), enable limited-live mode.
3. **Lab round 2 priority:** Should PR-022 (lab round 2 filters H07/H10/H06/H05) come earlier (before LLM advisory PR-016)? Or is LLM more urgent? Recommend: Filters first (they're proven on tape, cheap to implement). LLM second (requires budget, more complex).
4. **Forex timeline confirmation:** Still ~6 months for Forex? Or should PR-031 Forex adapter be prioritized differently?

---

**Last updated:** 2026-09-26 (Rebuild planning package)

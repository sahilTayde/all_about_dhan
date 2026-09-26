# Target Architecture

**Purpose:** This document describes the target modular architecture that supports the founder's requirements: common core + market adapters + broker adapters, clear separation of duties, event model, order/position state machines, multiple modes (paper/shadow/limited-live/live), and deterministic risk veto over everything including LLM output.

**Design principles:**
1. **Reuse what already works.** Don't rebuild working parts just for tidiness (ponytail principle: deletion over addition, boring over clever).
2. **Justify every new dependency** (complexity budget, FOUNDER_REQUIREMENTS § 57).
3. **Market-agnostic core:** NSE options today, Forex in ~6 months, crypto later. Adapter interface isolates market-specific logic.
4. **Broker-agnostic execution:** Dhan today, other brokers later. Adapter interface isolates broker API calls.
5. **Deterministic risk always wins:** Pre-trade risk engine can veto any decision from boss, LLM, analyst, or human (except founder emergency kill switch).
6. **Event-driven, not monolithic:** Stages communicate via event bus (pre-market → analyst → boss → desk → monitor → post-market). Each stage is testable in isolation.
7. **Fail closed:** Default to paper mode, no live orders unless founder explicitly enables and risk engine approves.

---

## High-Level Layered Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Founder Controls (Top Priority)             │
│  • Start/pause/stop   • Kill switch   • Override any decision    │
│  • Lot adjust   • Time windows   • Emergency flatten             │
└─────────────────────────────────────────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Pre-Trade Risk Engine (Veto Power)             │
│  • Position limits   • Loss limits   • Exposure checks           │
│  • Mode gate (paper/shadow/limited-live/live)                    │
│  • Vetoes boss, LLM, analyst, desk (except founder)              │
└─────────────────────────────────────────────────────────────────┘
                                 ▼
┌───────────────┬───────────────┬──────────────┬──────────────────┐
│  Pre-Market   │   Analysts    │     Boss     │      Desk        │
│  (Research)   │  (Signals)    │ (Orchestrate)│   (Execute)      │
├───────────────┼───────────────┼──────────────┼──────────────────┤
│ • News scrape │ • STRAT-001.. │ • Collect    │ • Submit orders  │
│ • Global mkts │   014         │   analyst    │ • Monitor fills  │
│ • Intermarket │ • ML models   │   votes      │ • Reconcile      │
│ • Event tag   │ • Chain bias  │ • Regime-    │ • Alert on       │
│ • Summary for │ • Dealer      │   conditional│   anomalies      │
│   boss        │ • Volume      │   weighting  │ • Consult boss   │
│               │ • Greeks      │ • Check      │ • Obey founder   │
│               │ • Custom      │   rules      │   first          │
│               │ • Log votes   │ • Ask LLM    │                  │
│               │               │   (if unsure)│                  │
│               │               │ • Log        │                  │
│               │               │   decision   │                  │
└───────────────┴───────────────┴──────────────┴──────────────────┘
                                 ▼                       ▼
                    ┌─────────────────────────────────────┐
                    │         Monitor (Feedback)          │
                    │  • Track position P&L               │
                    │  • Send updates to boss/desk        │
                    │  • Health checks (API, feeds, data) │
                    │  • Alert founder on failure         │
                    └─────────────────────────────────────┘
                                 ▼
                    ┌─────────────────────────────────────┐
                    │    Post-Market (Improve & Learn)    │
                    │  • Capture data to warehouse        │
                    │  • Analyze wins/losses              │
                    │  • Backtest + replay proposals      │
                    │  • GROK creates PRs (human merge)   │
                    └─────────────────────────────────────┘
```

---

## Layer Descriptions

### 1. Founder Controls Layer (Highest Priority)

**Duty:** Human override for everything. Founder commands skip all queues and override boss, desk, risk engine.

**Components:**
- **Founder UI:** Web dashboard (`apps/web`), mobile-friendly.
- **Founder API:** REST endpoints (`/founder/start`, `/founder/pause`, `/founder/kill`, `/founder/override/{trade_id}`).
- **Founder command queue:** Separate from boss → desk event flow. Desk checks this queue *first* every cycle.

**Commands:**
| Command | Effect | Bypasses |
|---------|--------|----------|
| `START` | Enable boss signal generation + desk execution | Risk mode gate (but risk engine still applies limits) |
| `PAUSE` | Halt new entries for N minutes (default infinite) | Boss |
| `STOP` | Halt new entries, keep monitoring open positions | Boss |
| `KILL_SWITCH` | Cancel all pending orders, exit all open positions, halt new entries | Boss, desk, risk engine (except position limits after exit) |
| `OVERRIDE_EXIT {trade_id}` | Force exit now (market order) | Desk hold logic |
| `OVERRIDE_LOT {trade_id, new_lots}` | Adjust position size (add/reduce) | Boss, risk engine lot limit (but founder-set limits still apply) |
| `OVERRIDE_TARGET {trade_id, new_target}` | Change target (e.g., go for T2) | Desk target logic |
| `SET_TIME_WINDOW {start_hhmm, end_hhmm, action: AVOID}` | Block new entries in time window | Boss clock rules |

**Logging:** Every founder command is logged with timestamp, user, command, reason (if provided), and outcome. Immutable audit log (append-only).

---

### 2. Pre-Trade Risk Engine (Veto Power)

**Duty:** Enforce safety limits deterministically. Can veto any decision from boss, LLM, analyst, or desk. Cannot veto founder emergency kill switch, but can enforce founder-set limits.

**Checks (evaluated before order submission):**
1. **Mode gate:**
   - **Paper mode** (default): No real broker orders. Simulate fills with paper engine. Safe for testing.
   - **Shadow mode:** Real broker orders submitted but immediately cancelled (measure latency, API errors). No fills.
   - **Limited-live mode:** Real orders, but max lots per trade ≤ founder-set limit (e.g., 5 lots), max daily loss ≤ limit (e.g., -10k).
   - **Live mode:** Full capital allocation. Requires founder approval + successful limited-live phase (≥20 trades, positive, max DD < threshold).
2. **Position limits:**
   - Max lots per trade (e.g., 25 lots paper, 5 lots limited-live, 100 lots live).
   - Max open positions (e.g., 3).
   - Max total exposure (notional; e.g., ₹5L paper, ₹50k limited-live, ₹25L live).
3. **Loss limits:**
   - Max loss per trade (e.g., -₹5k).
   - Max daily loss (e.g., -₹15k paper, -₹10k limited-live, -₹50k live).
   - Max drawdown from peak (e.g., -20%).
4. **Exposure checks:**
   - Max delta (e.g., ±1000 delta).
   - Max vega (e.g., ±5000 vega).
   - Single-symbol concentration (e.g., ≤50% of capital in one symbol).
5. **Time gates:**
   - No new entries before market open (09:15 IST).
   - No new entries after founder-set cutoff (default 15:00 IST, proven fix from Phase 3).
   - Flatten all by 15:20 IST (current rule; maybe adjust to 15:25 for ITM deep options with better liquidity).
6. **Cooldown after loss:**
   - If last exit was loss < 15 min ago, block new entry (proven fix from Phase 3).
7. **Idempotency:**
   - Reject duplicate order (same symbol, side, lots, within 60 sec).

**Veto behavior:**
- If check fails, return `VETO {reason}` to desk.
- Desk logs veto, does *not* submit order, notifies boss, alerts founder if veto reason is critical (e.g., daily loss limit hit).
- Boss can ask LLM "why did risk veto this trade?" but cannot override (only founder can).

**Configuration:**
- Limits stored in `config/risk_limits.yaml` (per mode: paper, shadow, limited-live, live).
- Founder can adjust via UI (`/founder/risk-limits`).
- Changes logged + require confirmation (prevent accidental live-mode enable).

---

### 3. Pre-Market Layer

**Duty:** Research, context-gathering, summarization. Runs before 09:15 IST. Output: compact context for boss (200-500 chars), event tags, intermarket summary.

**Components:**
- **News scraper:** Scrape MoneyControl, Economic Times, NSE announcements (via Beautiful Soup or API if available). Extract: headline, timestamp, sentiment (bullish/bearish/neutral via simple keyword heuristic or LLM), relevance (NIFTY, BANKNIFTY, SENSEX, sector, stock).
- **Event tagger:** Tag news as: earnings, policy (RBI, budget, election), global (Fed, war, oil shock), sector (banking, IT, pharma), stock-specific (results, scandal).
- **Global market analyzer:** Fetch overnight moves: SPX, Nasdaq, DXY, US10Y, crude oil, gold, USDINR. Compute intermarket score: risk-on (+SPX, -DXY, -US10Y) vs risk-off.
- **Multi-timeframe level analyzer:** Fetch NIFTY daily/4H/weekly chart. Identify: 52w high/low, daily support/resistance (yesterday's high/low/close, weekly pivot), current position relative to levels.
- **Summary compiler:** Generate compact summary for boss:
  - "NIFTY gap +0.5% (SPX +1.2%, DXY -0.3%, risk-on). News: RBI holds rates (neutral). Near daily R1 19850."
  - Store full details in warehouse; boss reads summary only (save LLM tokens).

**Output:**
- Event: `PRE_MARKET_SUMMARY {date, gap_pct, intermarket_score, news_summary, levels_summary, tagged_events: […]}`
- Store in `warehouse.pre_market_summaries` table.
- Push summary to boss context (in-memory, not .md file read during market hours per requirement line 34).

**Scheduling:** Run at 08:45 IST (30 min before market open). If fails, retry at 09:00. If still fails, send minimal summary: "Pre-market analysis unavailable, proceed with caution."

---

### 4. Analyst Layer (Signal Generators)

**Duty:** Consume data, generate signals, log reasoning. Analysts do *not* decide trade; they vote. Boss decides.

**Analyst registry (current):**
- **STRAT-001 .. STRAT-014:** Existing strategies (keep per KEEP_ALL rule, even if negative; mark as `WAITING` or `PARKED` per `expert-coalition.mdc`).
- **Dealer analyst** (`desk_ml/picker.py` `interpret_nifty_dealer`): PE writers vs CE writers.
- **Volume analyst:** Unusual volume in index futures or heavyweights.
- **Greeks analyst:** IV skew, max-pain, put-call OI ratio.
- **Chain-bias analyst** (`CHAIN-LEAN`): OI build-up (currently buggy, reversed; fix per gap matrix).
- **ML-001, ML-002:** Machine learning models (currently broken; fix or disable per gap matrix).
- **Custom analysts:** Founder can add new ones (e.g., supply/demand zones, breadth, sentiment).

**Analyst interface:**
```python
class Analyst:
    def vote(self, context: MarketContext) -> Vote:
        """
        Returns: Vote(
            analyst_id: str,
            signal: "BUY_CE" | "BUY_PE" | "HOLD" | "ABSTAIN",
            confidence: float [0.0, 1.0],
            reasoning: str (50-100 chars),
            metadata: dict (any supporting data)
        )
        """
```

**Vote logging:**
- Every vote stored: `warehouse.analyst_votes(timestamp, analyst_id, signal, confidence, reasoning, metadata_json)`.
- Enables post-market attribution: which analyst was right, which was wrong, which regime did they work in.

**Analyst must-not rules:**
- No live orders (analysts don't execute).
- No file I/O during market hours (pre-load models at startup).
- No blocking LLM calls (if analyst uses LLM, it must be async + cached + budgeted).
- No assumptions about market (e.g., don't assume BSE data available if only NSE is connected).

---

### 5. Boss Layer (Orchestrator)

**Duty:** Collect analyst votes, apply regime-conditional weighting (not majority vote per requirement line 75), check rules, ask LLM for second opinion if uncertain, emit entry decision, manage trade lifecycle, consult with desk, spawn juniors (delegated tasks).

**Boss decision flow:**

```
09:15 IST: Market opens
  ↓
Boss receives PRE_MARKET_SUMMARY (from pre-market layer)
  ↓
Every 1 min (or on event: new chain data, new signal):
  ↓
Boss emits REQUEST_VOTES {context: current chain, index level, time, regime}
  ↓
Analysts return votes (in parallel, with timeout 500ms)
  ↓
Boss computes weighted score:
  - Weight by regime-conditional track record (e.g., STRAT-007 weight = 1.5 in TREND, 0.5 in CONSOLIDATION)
  - Weight by recency (last 30 days > last 90 days)
  - Weight by confidence (analyst-reported)
  - Example: weighted_score = Σ(analyst_vote * weight * confidence)
  ↓
Boss checks rules:
  - Is regime CONSOLIDATION? (range ≤ 0.6 × 5-day median 30m range) → BLOCK
  - Is time < 10:00 or > 14:30? (STRAT-007 clock, proven fix) → BLOCK
  - Is last exit loss < 15 min ago? (cooldown, proven fix) → BLOCK
  - Is weighted_score > entry_threshold? (e.g., +0.3) → CANDIDATE
  ↓
If CANDIDATE and uncertain (score close to threshold, or conflicting high-confidence votes):
  ↓
  Boss asks LLM (OpenAI GPT-4 or Claude):
    Prompt (compact, <300 tokens):
      "Market: NIFTY 19820, gap +0.5%, regime TREND. Analysts: STRAT-007 BUY_CE 0.8 (trend breakout), CHAIN-LEAN BUY_PE 0.6 (OI buildup). Weighted score +0.28 (threshold 0.3). Pre-market: SPX +1.2%, risk-on. Second opinion?"
    LLM response (JSON):
      {"signal": "BUY_CE" | "BUY_PE" | "HOLD", "reasoning": "...", "confidence": 0.0-1.0}
  ↓
  Boss adjusts score with LLM vote (weight = LLM confidence)
  Boss logs LLM call (cost, latency, reasoning)
  ↓
If final score > entry_threshold:
  ↓
  Boss computes strike:
    - Read expiry from chain (current weekly or monthly)
    - Compute DTE (days to expiry)
    - If DTE ≥ 2: ITM100 (~100 pts ITM) (proven fix)
    - If DTE ≤ 1: ITM200 (~200 pts ITM, deep ITM for expiry day) (proven fix)
    - Find closest strike to target ITM depth
  ↓
  Boss emits ENTRY_APPROVED {
    trade_id: UUID,
    symbol: "NIFTY2492619800CE",
    side: "BUY_CE",
    lots: 25 (from config),
    target_pct: 30% (or points),
    stop_pct: 10% (or points),
    reason: "STRAT-007 trend breakout + risk-on",
    analysts: [{analyst_id, vote, weight}, ...],
    llm_vote: {...} (if used),
    timestamp
  }
  ↓
  Event sent to desk
  ↓
Boss monitors open positions (receives updates from monitor layer):
  - If position hits target or stop → Boss emits EXIT_APPROVED
  - If intermarket changes (e.g., crude oil spikes +5% in 10 min) → Boss re-evaluates, may emit EXIT_NOW
  - If analyst changes vote (e.g., chain-bias flips) → Boss logs, may adjust
  - If desk reports anomaly (order rejected, fill price far from LTP) → Boss investigates, alerts founder
  ↓
Boss logs all decisions:
  - Entry: why yes/no, which analysts voted, final score, rules applied, LLM call (if any)
  - Exit: why, trigger (target/stop/manual/boss-override), actual P&L vs expected
  ↓
Boss spawns juniors (optional, future):
  - Junior-01: Intermarket monitor (watches crude/gold/FX every 5 min, alerts boss if big move)
  - Junior-02: News monitor (polls news API every 10 min during market, alerts boss if high-impact event)
  - Junior-03: Risk monitor (checks exposure, alerts if approaching limit)
  - Communication: Juniors emit events, boss subscribes
```

**Boss must-not rules:**
- No direct broker calls (boss → desk → broker).
- No file reads during market hours (pre-load config at startup).
- LLM calls: only when uncertain, max 10 calls/day (budget), log every call.
- No assumptions (e.g., don't assume analyst X always available; handle abstain/timeout).

**Boss config:**
- `config/boss.yaml`:
  - `entry_threshold: 0.3`
  - `analyst_weights: {STRAT-007: {TREND: 1.5, CONSOLIDATION: 0.5, RANGE: 0.2}, ...}`
  - `llm_enabled: true`
  - `llm_budget_daily_calls: 10`
  - `llm_uncertainty_threshold: 0.05` (if score within 0.05 of threshold, ask LLM)

---

### 6. Desk Layer (Execution)

**Duty:** Execute orders, monitor fills, reconcile positions, consult boss, obey founder first.

**Desk loop:**

```
Every 1 sec (or on event):
  ↓
Desk checks founder command queue (highest priority):
  - If KILL_SWITCH → cancel all pending, exit all open, halt
  - If OVERRIDE_EXIT {trade_id} → exit now, skip boss
  - If OVERRIDE_LOT / OVERRIDE_TARGET → adjust, notify boss
  ↓
Desk checks boss event queue:
  - If ENTRY_APPROVED → proceed to pre-trade risk check
  - If EXIT_APPROVED → proceed to exit
  ↓
For ENTRY_APPROVED:
  ↓
  Desk calls pre-trade risk engine:
    risk_check(trade_intent) → PASS | VETO {reason}
  ↓
  If VETO:
    - Log veto
    - Emit ENTRY_VETOED {trade_id, reason} to boss
    - If critical reason (daily loss limit hit) → alert founder
    - STOP (do not submit order)
  ↓
  If PASS:
    - Desk calls broker adapter:
        broker.place_order(symbol, side, lots, order_type, limit_price, sl_price)
    - Broker adapter returns order_id (broker's ID) or error
    - If error (API down, insufficient funds, symbol not found) → log, alert founder, emit ENTRY_FAILED to boss
    - If success → log, store order_id, emit ORDER_SUBMITTED to monitor
  ↓
Desk monitors order status (via broker websocket or polling):
  - ORDER_ACKNOWLEDGED (broker accepted) → log
  - ORDER_FILLED (full or partial fill) → update position, log, emit POSITION_OPENED to monitor
  - ORDER_REJECTED (broker rejected) → log, alert founder (anomaly), emit ENTRY_FAILED to boss
  ↓
Desk monitors open positions (receives market data from broker websocket):
  - Compute unrealized P&L (current LTP vs entry price)
  - Check target hit (P&L ≥ target_pct) → request boss EXIT_APPROVED (boss may delay if thinks trend continues)
  - Check stop hit (P&L ≤ -stop_pct) → immediate exit (no boss approval needed for stop loss per safety rule)
  - Emit POSITION_UPDATE {trade_id, current_pnl, current_price} to monitor (every 10 sec or on significant move)
  ↓
For EXIT_APPROVED or stop hit:
  ↓
  Desk calls broker adapter:
    broker.place_order(symbol, "EXIT", lots, "MARKET")
  - Broker adapter returns order_id or error
  - If error → retry 3 times, if still fail → alert founder (critical: cannot exit position)
  - If success → log, emit ORDER_SUBMITTED (exit)
  ↓
Desk monitors exit fill:
  - ORDER_FILLED → update position (closed), log realized P&L, emit POSITION_CLOSED to monitor
  ↓
Desk reconciles positions (every 1 min):
  - Fetch broker positions via API: broker.get_positions()
  - Compare with internal book
  - If mismatch (position exists in broker but not internal, or vice versa) → alert founder (critical: reconciliation failure)
  - Log discrepancy, halt new entries until resolved
```

**Desk must-not rules:**
- No decision-making (desk executes, boss decides).
- No risk limit changes (only risk engine adjusts limits, per founder config).
- No ignoring founder commands (founder queue is checked first, always).

**Desk logging:**
- Every order (submitted, acknowledged, filled, rejected) logged with: timestamp, trade_id, order_id (broker), symbol, side, lots, order_type, limit_price, sl_price, fill_price (if filled), latency (submit → ack), status.
- Immutable audit log (append-only).

---

### 7. Monitor Layer (Feedback & Health)

**Duty:** Track position P&L, send updates to boss/desk, health checks (API, feeds, data), alert founder on failure.

**Monitor loop:**

```
Every 10 sec:
  ↓
Monitor receives POSITION_UPDATE from desk
  ↓
Monitor computes metrics:
  - Current P&L per position
  - Total open P&L
  - Total closed P&L (today, week, month)
  - Max drawdown from peak (today)
  - Win rate (closed trades, today/week/month)
  ↓
Monitor emits POSITION_METRICS {total_open_pnl, total_closed_pnl, drawdown, win_rate, timestamp}
  ↓
Monitor stores in warehouse: `warehouse.position_metrics_1min` (time-series)
  ↓
Monitor checks health (every 1 min):
  - Dhan websocket connected? (last message < 60 sec ago)
  - Dhan API reachable? (GET /api/v1/health → 200 OK) (if Dhan has health endpoint; else test with lightweight call)
  - OpenAI API reachable? (if LLM enabled; last successful call < 10 min ago OR test call)
  - News scraper ran? (last run < 10 min ago; check `warehouse.news` last insert)
  - Option chain poller alive? (last chain insert < 2 min ago)
  - Each analyst emitted vote? (last vote per analyst < timeout, e.g., 5 min)
  ↓
  If any health check fails:
    - Emit HEALTH_ALERT {service, status: DOWN, last_seen, timestamp}
    - Store in `warehouse.health_alerts`
    - Push to founder page (red flag in health panel)
    - Optional: Send Telegram/email (if founder configured)
```

**Monitor must-not rules:**
- No execution (monitor observes, does not act).
- No decision-making (monitor reports, boss decides).

**Monitor output:**
- Founder page health panel (green/yellow/red status per service).
- Founder page P&L dashboard (live total P&L, today's closed trades, open positions).

---

### 8. Post-Market Layer (Improve & Learn)

**Duty:** Capture data to warehouse, analyze wins/losses, backtest + replay proposals, GROK (post-market agent) creates PRs, human merge gate.

**Post-market job (runs at 16:00 IST, after market close at 15:30):**

```
Step 1: Data capture to warehouse
  ↓
  - Read all `data/recon/*` JSON (index ticks, option chain, futures, news)
  - ETL: clean, join (index ↔ chain ↔ news ↔ futures), write to warehouse tables
  - Aggregate: daily summary (open, high, low, close, volume per symbol), daily P&L (per strategy, per analyst, per stage)
  - Tag events: expiry day, election day, RBI policy, earnings, global shock (from news tags)
  ↓
Step 2: Win/loss analysis
  ↓
  - Fetch today's closed trades from warehouse
  - Group by: analyst (which analyst voted for this trade), strategy (which strategy generated signal), regime (what was the market regime at entry)
  - Compute: win rate, avg profit per win, avg loss per loss, profit factor, max DD
  - Compare with yesterday, last week, last month
  - Identify: which analyst improved, which degraded, which regime had most wins/losses
  ↓
Step 3: GROK analysis (LLM-assisted)
  ↓
  - GROK reads: today's trades, today's chain/tick data, today's news, today's decisions (why boss said yes/no)
  - GROK identifies: (1) missed opportunities (should have taken trade but didn't; why?), (2) mistakes (took trade but lost; why?), (3) anomalies (order rejected, fill price bad, reconciliation failure)
  - GROK generates hypotheses: "STRAT-007 lost 3/4 trades today; all in CONSOLIDATION regime; should we lower STRAT-007 weight in CONSOLIDATION?"
  ↓
Step 4: Backtest + replay proposals
  ↓
  - For each hypothesis:
    - GROK runs honest backtest (last 30 days, walk-forward, costs, random placebos)
    - If backtest shows improvement (p < 0.05 vs random skip, better than baseline on 4/5 metrics: profit, win rate, profit factor, max DD, Sharpe) → GROK proposes change
    - GROK runs tape replay (last 7 days of exact quotes)
    - If tape replay confirms improvement → GROK generates PR
  ↓
Step 5: GROK creates PR (but does NOT merge)
  ↓
  - PR title: "Post-market 2026-09-26: Lower STRAT-007 weight in CONSOLIDATION (backtest +12.5 L, tape +18.3k)"
  - PR description (handoff block per § 106):
    - What was accepted: "STRAT-007 weight in TREND stays 1.5"
    - What was rejected: "STRAT-007 weight in CONSOLIDATION 0.5 is too high"
    - Proposal: "Lower to 0.2"
    - Evidence: "Backtest last 30 days: +12.5 L vs baseline. Tape last 7 days: +18.3k (4 fewer losing trades in CONSOLIDATION). Random skip p-value: 0.03."
    - Risk: "May hurt if CONSOLIDATION breaks into TREND quickly; watch first 3 days."
    - Next steps: "Merge if founder approves; shadow-log for 3 days; full deploy if no regression."
  - PR commits: config change only (`config/boss.yaml`), no code change (unless hypothesis requires code fix)
  - PR assigned to: founder (human review + merge gate)
  ↓
Founder reviews PR next morning (pre-market):
  - Founder reads PR, checks backtest report, checks tape replay report
  - Founder decides: merge, reject, request more evidence, shadow-log first
  - If merge → change goes live today
  - If shadow-log → change runs in parallel (both old and new), compare results end of day
```

**GROK must-not rules (from requirement lines 90-104):**
- **Do NOT assume anything.** Backtest + replay everything before proposing (requirement line 91).
- **Do NOT merge PRs** (requirement line 90). Human gate.
- **Do NOT just type "add sentences"** (requirement line 93). Data-driven reports: improvement, pros/cons, win rate, metrics.
- **Do NOT push to production harness** (requirement line 90). PR only.
- **Do NOT invent strategies with untested edge** (FOUNDER_REQUIREMENTS § 4). Propose changes to existing strategies or rules, with evidence.

**GROK live monitoring (optional, during market hours per requirement lines 96-101):**
- **Every 5-10 min:** GROK fetches current trades, open P&L, drawdown.
- **If losing trades ≥ threshold (e.g., 3 losses in a row, or -₹10k today):** GROK analyzes, may suggest boss to pause/stop (but cannot command boss; only suggest; boss decides).
- **If boss unreachable:** GROK sends alert to founder page + Telegram (per requirement line 98).
- **GROK monitors:** Alerts, disconnects, health failures (monitors the monitor; meta-monitoring).

---

## Cross-Cutting Concerns

### Event Model

**Event bus:** Publish-subscribe. Each stage (pre-market, analyst, boss, desk, monitor, post-market) subscribes to relevant events and emits new events.

**Event types:**
- `PRE_MARKET_SUMMARY` (pre-market → boss)
- `REQUEST_VOTES` (boss → analysts)
- `ANALYST_VOTE` (analyst → boss)
- `ENTRY_APPROVED` (boss → desk)
- `EXIT_APPROVED` (boss → desk)
- `ORDER_SUBMITTED` (desk → monitor, boss)
- `ORDER_FILLED` (desk → monitor, boss)
- `POSITION_UPDATE` (desk → monitor, boss)
- `POSITION_CLOSED` (desk → monitor, boss, post-market)
- `ENTRY_VETOED` (risk engine → boss, founder)
- `HEALTH_ALERT` (monitor → founder, boss)
- `FOUNDER_COMMAND` (founder → desk, boss; highest priority)

**Event schema (JSON):**
```json
{
  "event_type": "ENTRY_APPROVED",
  "event_id": "uuid",
  "timestamp": "2026-09-26T10:32:15.123Z",
  "source": "boss",
  "payload": {
    "trade_id": "uuid",
    "symbol": "NIFTY2492619800CE",
    "side": "BUY_CE",
    "lots": 25,
    "target_pct": 30,
    "stop_pct": 10,
    "reason": "STRAT-007 trend breakout + risk-on",
    "analysts": [...],
    "llm_vote": {...}
  }
}
```

**Event bus implementation options:**
- **In-memory queue** (Python `queue.Queue` or `asyncio.Queue`): Simplest, works for single-machine deployment (Mac, small VPS). Lose events on restart (OK for paper/shadow; not OK for live).
- **Redis pub/sub or Redis Streams**: Lightweight, fast, durable (with persistence). Good for VPS deployment. Easy to inspect events (Redis CLI).
- **Kafka / RabbitMQ**: Overkill for this system (complexity budget violation per § 57). Only if scaling to multiple machines or need strict event ordering guarantees.

**Recommendation:** Start with **Redis Streams** (lightweight, durable, debuggable, VPS-ready). Falls back to in-memory queue if Redis unavailable (paper mode on Mac without Redis).

---

### Order State Machine

**States:**
1. **CREATED:** Boss approved entry, desk received `ENTRY_APPROVED` event.
2. **RISK_CHECK:** Desk called pre-trade risk engine, waiting for result.
3. **VETOED:** Risk engine vetoed, order not submitted. Terminal state (log and alert).
4. **SUBMITTED:** Desk called broker adapter, order sent to broker, waiting for acknowledgement.
5. **ACKNOWLEDGED:** Broker accepted order, order is active (pending fill).
6. **FILLED:** Broker filled order (full or partial), position is open.
7. **REJECTED:** Broker rejected order. Terminal state (log and alert).
8. **EXIT_REQUESTED:** Boss or desk requested exit (target hit, stop hit, manual).
9. **EXIT_SUBMITTED:** Exit order sent to broker.
10. **CLOSED:** Exit filled, position closed, realized P&L recorded. Terminal state.
11. **CANCELLED:** Order cancelled before fill (founder kill switch, or boss changed mind). Terminal state.

**Transitions:**
```
CREATED → RISK_CHECK → [VETOED | SUBMITTED]
SUBMITTED → [ACKNOWLEDGED | REJECTED]
ACKNOWLEDGED → [FILLED | CANCELLED]
FILLED → EXIT_REQUESTED → EXIT_SUBMITTED → [CLOSED | (retry)]
```

**Logging:** Every state transition logged with timestamp, reason, latency (time in previous state).

---

### Position State Machine

**States:**
1. **OPENING:** Order submitted, waiting for fill.
2. **OPEN:** Position is open, being monitored.
3. **CLOSING:** Exit order submitted, waiting for fill.
4. **CLOSED:** Position closed, realized P&L recorded.

**Attributes:**
- `trade_id` (UUID, immutable)
- `symbol`, `side` (BUY_CE / BUY_PE), `lots`, `entry_price`, `entry_time`
- `target_price`, `stop_price`
- `current_price` (updated every tick or every 10 sec)
- `unrealized_pnl` (for OPEN), `realized_pnl` (for CLOSED)
- `exit_price`, `exit_time`, `exit_reason` (TARGET_HIT / STOP_HIT / BOSS_OVERRIDE / FOUNDER_COMMAND / FLATTEN_EOD)

---

### Reconciliation

**Broker vs internal book:**
- Every 1 min during market hours, desk fetches broker positions: `broker.get_positions()`.
- Compare with internal book (positions in state OPEN).
- **Match:** position exists in both, quantities match → OK.
- **Mismatch (quantity):** position exists in both, but lots differ → log, alert founder (critical), halt new entries until resolved (manual intervention: did broker partially fill? did we miss fill event?).
- **Orphan (broker side):** position exists in broker but not internal → log, alert founder (critical; unknown position), option to import or flatten.
- **Orphan (internal side):** position exists in internal but not broker → log, alert founder (critical; order may have failed silently), option to resubmit or close internal position.

**Ledger vs broker cash:**
- End of day, fetch broker cash balance: `broker.get_balance()`.
- Compare with internal ledger balance (starting capital ± realized P&L ± charges).
- **Match (within tolerance ±₹100):** OK.
- **Mismatch:** Log discrepancy, alert founder. Possible causes: charges not tracked accurately, broker adjusted (penalty, interest), failed order charged but not recorded.

**Resolution:** Manual review. Founder decides: adjust internal ledger (if broker is truth), or query broker support (if internal ledger is truth and broker charged incorrectly).

---

### Single Source of Truth

**Position book (internal):** `warehouse.positions` table. This is the system's source of truth for *what we think* positions are.

**Broker book (external):** Broker API `get_positions()`. This is the *actual* source of truth for *what broker thinks* positions are.

**Reconciliation ensures these align.** If they diverge, **broker wins** (we adjust internal book), but we **alert founder** (divergence means something went wrong: missed fill event, broker API bug, our bug).

**Order book (internal):** `warehouse.orders` table. Maps our `trade_id` to broker `order_id`. This is the join key for reconciliation.

---

### Idempotency

**Problem:** Network failures, retries can cause duplicate orders (e.g., desk submits order, network times out, desk retries, broker receives twice, two positions opened).

**Solution:**
1. **Client-side idempotency key:** Desk generates `order_request_id` (UUID) before calling broker. Passes to broker adapter. Broker adapter includes in request (if Dhan API supports; if not, track client-side).
2. **Retry with same ID:** If broker call times out, retry with same `order_request_id`. Broker recognizes duplicate, returns original `order_id` instead of creating new order.
3. **Client-side dedup:** Desk tracks `order_request_id → order_id` map. Before submitting, check map: if `order_request_id` already submitted in last 60 sec, skip (dedup).

**Dhan API support:** Check Dhan API docs for idempotency support. If not supported, implement client-side dedup only (good enough for paper/shadow; for live, test thoroughly in shadow mode first).

---

### Modes (Paper / Shadow / Limited-Live / Live)

| Mode | Real Orders? | Real Fills? | Risk Limits | Use Case |
|------|--------------|-------------|-------------|----------|
| **Paper** | No | No (simulated) | High (100 lots, ₹5L exposure) | Testing strategies, UI, flows. Safe, no real money. Default. |
| **Shadow** | Yes (submitted then immediately cancelled) | No | Same as paper | Test broker integration, measure latency, API errors. No fills (orders cancelled before fill). Costs: cancellation may incur minimal broker charge (₹0 or small fixed fee per cancellation, check Dhan pricing). |
| **Limited-Live** | Yes | Yes | Low (5 lots, ₹50k exposure, -₹10k daily loss limit) | First real money. Validate execution, slippage, costs. Prove strategy works with real fills. After ≥20 trades, positive P&L, max DD < threshold → graduate to live. |
| **Live** | Yes | Yes | High (100 lots, ₹25L exposure, -₹50k daily loss limit; founder-set) | Full deployment. Only after successful limited-live phase + founder approval. |

**Mode transitions:**
- **Paper → Shadow:** Founder enables in UI (`/founder/mode → SHADOW`). Requires: (1) broker adapter tested (unit tests pass), (2) API credentials valid, (3) founder confirms "I understand orders will be submitted and cancelled, may incur small charges."
- **Shadow → Limited-Live:** Founder enables. Requires: (1) shadow mode ran for ≥3 days, no API errors, latency < threshold (e.g., 500ms p95), (2) founder confirms "I understand real fills will occur, max ₹10k daily loss."
- **Limited-Live → Live:** Founder enables. Requires: (1) limited-live ran for ≥20 trades, (2) positive P&L (total), (3) max DD < -20%, (4) founder reviews and approves.

**Mode gate enforcement:** Pre-trade risk engine checks current mode. If mode = PAPER, skip broker call, simulate fill. If mode = SHADOW, submit order then immediately cancel. If mode = LIMITED_LIVE or LIVE, submit order normally, but enforce mode-specific limits.

---

## Market Adapter Layer (Multi-Market Support)

**Purpose:** Isolate market-specific logic (calendar, lot/tick size, expiry rules, hours, margin, symbology) from core engine. Enables Forex (~6 months), crypto (later) without rewriting core.

**Market adapter interface:**

```python
class MarketAdapter:
    def calendar(self) -> Calendar:
        """Returns market calendar (holidays, trading days, hours)."""
        
    def lot_size(self, symbol: str) -> int:
        """Returns lot size for symbol (e.g., NIFTY = 25, BANKNIFTY = 15)."""
        
    def tick_size(self, symbol: str) -> float:
        """Returns tick size (min price increment; e.g., 0.05 for options)."""
        
    def expiry_schedule(self, symbol: str) -> List[date]:
        """Returns expiry dates (weekly, monthly) for symbol."""
        
    def trading_hours(self, date: date) -> (time, time):
        """Returns (market_open, market_close) for date (e.g., 09:15, 15:30 IST)."""
        
    def margin_required(self, symbol: str, lots: int) -> float:
        """Returns margin required for position (for risk checks)."""
        
    def symbology(self, base: str, expiry: date, strike: float, option_type: str) -> str:
        """Generates broker symbol (e.g., NSE: "NIFTY2492619800CE", Forex: "EURUSD-2026-09-26-1.1000C")."""
```

**Market adapter implementations:**

1. **NSEOptionsAdapter** (current, for NIFTY/BANKNIFTY/SENSEX):
   - Calendar: NSE holidays (from NSE website or hardcoded).
   - Lot size: NIFTY=25 (as of Sep 2026; check NSE for current), BANKNIFTY=15, SENSEX=10.
   - Tick size: 0.05 for options.
   - Expiry: Weekly (Thursday), monthly (last Thursday).
   - Hours: 09:15-15:30 IST (pre-open 09:00-09:15).
   - Margin: SPAN + exposure (fetch from broker API or use approximate 15-20% of notional).
   - Symbology: NSE format `{underlying}{expiry:YYMDD}{strike}{CE/PE}`.

2. **ForexAdapter** (future, ~6 months):
   - Calendar: 24/5 market (Sun 5pm ET – Fri 5pm ET), no Indian holidays.
   - Lot size: Standard lot (e.g., 100,000 units for EURUSD) or mini lot (10,000).
   - Tick size: 0.0001 (pip).
   - Expiry: Weekly options (Fri), monthly (3rd Fri or end-of-month, depends on exchange).
   - Hours: 24/5 (split into sessions: Asia, London, NY).
   - Margin: Leverage 50:1 or 100:1 (broker-dependent).
   - Symbology: Broker-specific (e.g., Oanda: "EUR_USD", FXCM: "EURUSD").

3. **CryptoAdapter** (future, unspecified timeline):
   - Calendar: 24/7, no holidays.
   - Lot size: Variable (BTC = 1, altcoins = varies; broker-specific).
   - Tick size: 0.01 for BTC/USD (or smaller for altcoins).
   - Expiry: Perpetual futures (no expiry) or quarterly expiries (varies by exchange).
   - Hours: 24/7.
   - Margin: Leverage 10:1 to 125:1 (exchange-dependent).
   - Symbology: Exchange-specific (e.g., Binance: "BTCUSDT", Deribit: "BTC-PERPETUAL").

**Core engine changes for market adapters:**
- Boss strike selection: Instead of hardcoding ITM100/ITM200, call `market_adapter.compute_strike(underlying, signal, dte)`.
- Desk time checks: Instead of hardcoding 09:15/15:30, call `market_adapter.trading_hours(today)`.
- Risk engine margin checks: Call `market_adapter.margin_required(symbol, lots)`.
- Position P&L: Compute points using `market_adapter.tick_size(symbol)`.

**Configuration:** `config/market.yaml`:
```yaml
market: NSE  # or FOREX, CRYPTO
adapter: NSEOptionsAdapter  # or ForexAdapter, CryptoAdapter
```

---

## Broker Adapter Layer (Broker-Agnostic Execution)

**Purpose:** Isolate broker API calls (Dhan today, other brokers later: Zerodha, Upstox, Interactive Brokers for Forex) from desk logic.

**Broker adapter interface:**

```python
class BrokerAdapter:
    def place_order(self, symbol: str, side: str, lots: int, order_type: str, limit_price: float = None, sl_price: float = None) -> Result[str, Error]:
        """
        Places order. Returns broker order_id or error.
        order_type: "MARKET", "LIMIT", "SL", "SL-M"
        side: "BUY", "SELL"
        """
        
    def get_order_status(self, order_id: str) -> OrderStatus:
        """Returns order status (PENDING, FILLED, REJECTED, CANCELLED)."""
        
    def modify_order(self, order_id: str, new_limit_price: float = None, new_sl_price: float = None) -> Result[None, Error]:
        """Modifies order (trailing SL, target shift)."""
        
    def cancel_order(self, order_id: str) -> Result[None, Error]:
        """Cancels order."""
        
    def get_positions(self) -> List[Position]:
        """Returns current positions (for reconciliation)."""
        
    def get_balance(self) -> float:
        """Returns available cash balance."""
        
    def subscribe_order_updates(self, callback: Callable) -> None:
        """Subscribes to order update websocket. Callback called on each update."""
        
    def subscribe_market_data(self, symbols: List[str], callback: Callable) -> None:
        """Subscribes to market data (LTP, bid/ask) websocket."""
```

**Broker adapter implementations:**

1. **DhanAdapter** (current, for NSE options via Dhan):
   - API docs: https://api.dhan.co (verify current docs).
   - Authentication: Bearer token (from login API or OAuth; store in `secrets/dhan_token.txt`, NEVER commit).
   - REST endpoints:
     - Place order: `POST /orders` (body: `{symbol, side, quantity, order_type, limit_price, ...}`). Docs say "super order" = bracket order (entry + target + SL in one call); regular order = entry only.
     - Order status: `GET /orders/{order_id}`.
     - Modify order: `PUT /orders/{order_id}` (trailing SL = modify SL as market moves; check if Dhan supports trailing natively or must be done client-side).
     - Cancel order: `DELETE /orders/{order_id}`.
     - Positions: `GET /positions`.
     - Balance: `GET /funds`.
   - Websocket:
     - Order updates: Dhan websocket (check docs for exact channel; may be `wss://api.dhan.co/ws/orders`).
     - Market data: Dhan websocket (subscribe to symbols for LTP, OI, bid/ask).
   - Idempotency: Check if Dhan supports client-side request ID. If yes, use it. If no, implement client-side dedup.
   - Error handling: Dhan API may return errors (insufficient funds, RMS rejection, symbol not found, market closed). Map to standardized error codes (INSUFFICIENT_FUNDS, RMS_REJECT, SYMBOL_NOT_FOUND, MARKET_CLOSED).

2. **ZerodhaAdapter** (future, if switching to Zerodha Kite):
   - Similar interface, different API (Kite Connect REST + websocket).
   - Authentication: API key + access token (OAuth flow).
   - Order placement: `POST /orders/regular` or `POST /orders/variety` (bracket, cover).
   - Good docs, widely used.

3. **ForexBrokerAdapter** (future, for Forex; broker TBD; candidates: Oanda, Interactive Brokers, FXCM):
   - REST API + FIX protocol or websocket for order updates.
   - Different symbology, different margin calculations.

**Broker adapter selection:** Configured in `config/broker.yaml`:
```yaml
broker: Dhan  # or Zerodha, Oanda, IB
adapter: DhanAdapter
credentials:
  token_file: secrets/dhan_token.txt  # Never commit this file
  client_id: REDACTED  # Read from env var DHAN_CLIENT_ID
```

**Desk uses broker adapter:**
```python
broker = get_broker_adapter(config)  # Factory returns DhanAdapter or ZerodhaAdapter
result = broker.place_order(symbol, "BUY", lots, "LIMIT", limit_price)
if result.is_ok():
    order_id = result.value
    # log, emit event
else:
    error = result.error
    # log, alert, emit ENTRY_FAILED
```

**Testing:** Mock broker adapter for unit tests (returns success for place_order, simulates fills). Real broker adapter used in shadow/limited-live/live modes only.

---

## Technology Stack (Lightweight, Mac Now, VPS Later)

**Design constraints:**
1. **Lightweight:** Minimize dependencies (ponytail principle: stdlib first, avoid heavyweight frameworks per § 57).
2. **Mac-testable:** Runs on founder's Mac for paper trading.
3. **VPS-ready:** Deploys to Ubuntu VPS (or cloud VM) for live trading.
4. **No Docker required** (adds complexity; founder may not have Docker on Mac). Optional: Dockerfile provided for VPS deployment, but not mandatory.

**Recommended stack:**

### Core Services (Python)
- **Language:** Python 3.11+ (good async support, type hints, fast enough for this scale).
- **Services:**
  - `boss_service.py`: Boss orchestrator.
  - `desk_service.py`: Execution + monitoring (combined; can split later if needed).
  - `risk_service.py`: Pre-trade risk engine.
  - `analyst_service.py`: Analyst registry + vote collector (or analysts run as separate processes; TBD based on load).
  - `pre_market_service.py`: Pre-market analysis (runs once at 08:45 IST).
  - `post_market_service.py`: Post-market analysis + GROK (runs once at 16:00 IST).
  - `api_service.py`: FastAPI for founder UI + external integrations.
  - `monitor_service.py`: Health checks + metrics.

### Event Bus
- **Redis Streams** (recommended): Lightweight, durable, VPS-ready. Install: `brew install redis` (Mac) or `apt install redis` (Ubuntu). Start: `redis-server`. Python client: `redis-py`.
- **Fallback:** In-memory `asyncio.Queue` if Redis unavailable (paper mode only; lose events on restart).

### Data Storage

#### Warehouse (Historical Data, Reports, Aggregates)
- **Option 1: DuckDB** (recommended for simplicity):
  - Embedded (no separate server), fast analytical queries, Parquet-backed.
  - Good for: Time-series data (index ticks, option chain), warehouse aggregates (daily P&L, win rates), backtest results.
  - Python: `duckdb` package.
  - Storage: Single file (`data/warehouse.duckdb`) or Parquet files (`data/warehouse/*.parquet` + DuckDB queries them).
  - Pros: Zero setup, fast, lightweight.
  - Cons: Single-writer (one process writes at a time; OK for this system: post-market ETL is single process).
- **Option 2: PostgreSQL + Timescale**:
  - Separate server, more powerful (multi-writer, replication, advanced indexing).
  - Good for: Same as DuckDB, but also supports concurrent writes (e.g., multiple analyst processes writing votes simultaneously).
  - Python: `psycopg2` or `asyncpg`.
  - Setup: `brew install postgresql` (Mac) or `apt install postgresql` (Ubuntu). Start: `pg_ctl start` or systemd service.
  - Timescale extension: Optimized for time-series (automatic partitioning, fast queries on `timestamp` ranges).
  - Pros: Production-grade, scales to VPS + future cloud.
  - Cons: More complex setup, more memory usage.

**Recommendation:** Start with **DuckDB** (Mac paper trading). If concurrent-write or replication needed (live trading, multiple services), migrate to **PostgreSQL + Timescale** (straightforward migration: export DuckDB → CSV → import to Postgres).

#### Operational Data (Live State: Positions, Orders, Config)
- **Option 1: SQLite**:
  - Embedded, same as DuckDB, but more mature, better concurrent-read support.
  - Good for: Position book, order book, ledger, config, health status.
  - Python: `sqlite3` (stdlib).
  - Storage: `data/trading.db`.
  - Pros: No setup, fast, reliable.
  - Cons: Single-writer (OK for this system: desk is only writer for positions/orders).
- **Option 2: Redis** (if already using for event bus):
  - In-memory (fast), persistent (with AOF or RDB snapshot).
  - Good for: Same as SQLite, but also supports pub/sub (event bus).
  - Python: `redis-py`.
  - Pros: One less dependency (reuse Redis).
  - Cons: Higher memory usage (in-memory), less query flexibility (no SQL; use Redis commands or RedisJSON).

**Recommendation:** **SQLite** for operational data (positions, orders, ledger), **Redis** for event bus + cache (if needed). Simple, lightweight, works on Mac and VPS.

#### File Storage (Raw Data: Tick Files, Tape, Logs)
- **Local filesystem:** `data/recon/` for raw JSON (index ticks, option chain, news), `data/tape/` for replay tapes, `logs/` for service logs.
- **Parquet files** for tick data (compressed, columnar, fast for backtest queries). Python: `pyarrow` or `pandas.to_parquet()`.

### Web UI
- **Frontend:** React + Vite (already exists in `apps/web`). Lightweight, fast, modern.
- **State management:** React Context or Zustand (lightweight alternative to Redux).
- **Charts:** Chart.js or Recharts (lightweight) or D3.js (more powerful, bigger bundle).
- **Websocket client:** Native WebSocket API or `socket.io-client` (if using Socket.IO on backend; check current setup).

### API
- **FastAPI** (already exists in `apps/api`): Modern, fast, async, auto-generated OpenAPI docs. Good choice.
- **Websocket:** FastAPI supports websockets natively (`/ws/signals` already exists). Use for real-time updates (position P&L, order status, health alerts).

### LLM
- **OpenAI GPT-4 or GPT-4-turbo** (founder has API key): Expensive ($0.01/1k input tokens, $0.03/1k output tokens as of 2023; check current pricing). Budget: 10 calls/day × 300 tokens/call × $0.01 = $0.30/day = ~$9/month (cheap; OK).
- **Anthropic Claude** (if founder has key): Similar pricing, good for structured reasoning.
- **Gemini** (Google; if founder has key): Cheaper, but API less mature. Test if budget is concern.

**LLM client:** Python `openai` package or `anthropic` package. Async calls (`openai.ChatCompletion.acreate()`).

### News Scraping
- **Beautiful Soup 4** + **requests** (for HTML scraping): Lightweight, simple.
- **RSS feeds:** MoneyControl, Economic Times have RSS; faster than scraping.
- **Optional API:** Alpha Vantage (news API, free tier 5 calls/min), NewsAPI (free tier 100 calls/day). Check if sufficient.

### Global Market Data
- **Yahoo Finance API** (`yfinance` Python package): Free, covers SPX, DXY, US10Y, crude, gold. Rate limits unknown; test.
- **Alpha Vantage** (free tier 5 calls/min): Covers same + more. Good fallback.

### Backtest / Replay
- **Existing lab framework** (`scripts/lab/lab_hist.py`): Reuse. Good structure (walk-forward, placebos, costs). Integrate into PR template (requirement: honest backtest before merge).

### Deployment / Process Management
- **Mac (paper trading):**
  - Start services: Shell script `scripts/start_all.sh` (launches all Python services in background).
  - Stop: `scripts/stop_all.sh` (pkill by script name or use PID file).
  - Logs: Each service writes to `logs/{service}.log` (rotate with `logrotate` or manual).
- **VPS (live trading):**
  - **systemd** (recommended for Ubuntu VPS): One `.service` file per service (e.g., `boss.service`, `desk.service`). Auto-restart on failure, logs to journalctl.
  - **supervisor** (alternative): Python-based process manager. Simpler config than systemd, but less integration with OS.
  - **Docker** (optional): Dockerfile provided, but not required (adds complexity). Use if founder wants containerization.

### Dependencies
- **Minimize:** Ponytail principle. Use stdlib where possible (e.g., `sqlite3`, `json`, `csv`, `asyncio`, `queue`, `logging`).
- **Required non-stdlib:**
  - `redis` (event bus)
  - `duckdb` or `psycopg2` (warehouse)
  - `fastapi`, `uvicorn` (API)
  - `requests`, `beautifulsoup4` (news scraping)
  - `yfinance` or `alpha_vantage` (global market data)
  - `openai` or `anthropic` (LLM)
  - `pandas`, `numpy` (data analysis; already used in lab scripts)
  - `pyarrow` (Parquet files; optional but recommended for tick data)

**Total new dependencies:** ~10 (all lightweight, well-maintained).

---

## Deployment (Mac Now, VPS Later)

### Mac Paper Trading (Current)
1. **Install dependencies:** `pip install -r requirements.txt` (or `poetry install` if using Poetry).
2. **Start Redis:** `brew install redis && redis-server` (or use Docker: `docker run -d -p 6379:6379 redis`).
3. **Initialize DB:** `python scripts/init_db.py` (creates SQLite `data/trading.db` + DuckDB `data/warehouse.duckdb`, initializes tables).
4. **Start services:** `scripts/start_all.sh` (launches boss, desk, risk, analyst, api, monitor in background).
5. **Start UI:** `cd apps/web && npm run dev` (Vite dev server, http://localhost:5173).
6. **Access founder page:** Open browser, go to `http://localhost:5173/founder`.
7. **Stop:** `scripts/stop_all.sh`.

### VPS Live Trading (Future)
1. **Provision VPS:** Ubuntu 22.04 or 24.04, ≥2 vCPU, ≥4 GB RAM (or ≥2 GB RAM if only running this system).
2. **Install dependencies:** `sudo apt update && sudo apt install python3.11 python3-pip redis-server postgresql` (if using Postgres; skip if using DuckDB).
3. **Clone repo:** `git clone <repo> && cd all_about_dhan`.
4. **Install Python deps:** `pip3 install -r requirements.txt`.
5. **Set secrets:** Create `secrets/dhan_token.txt` (Dhan API token), set env vars `DHAN_CLIENT_ID`, `OPENAI_API_KEY` (use VPS env vars or `.env` file; never commit).
6. **Initialize DB:** `python3 scripts/init_db.py`.
7. **Setup systemd:** Copy `deploy/systemd/*.service` to `/etc/systemd/system/`, `sudo systemctl daemon-reload`, `sudo systemctl enable boss desk risk api monitor`, `sudo systemctl start boss desk risk api monitor`.
8. **Setup nginx:** Reverse proxy to FastAPI (port 8000), serve React build (`apps/web/dist`) as static files. Config: `deploy/nginx/all_about_dhan.conf`.
9. **Setup cron:** Pre-market at 08:45 IST, post-market at 16:00 IST. Add to crontab: `45 8 * * 1-5 /path/to/venv/bin/python /path/to/scripts/pre_market.py`, `0 16 * * 1-5 /path/to/venv/bin/python /path/to/scripts/post_market.py` (adjust for IST; cron uses server TZ; set server TZ to Asia/Kolkata or convert times).
10. **Monitor logs:** `journalctl -u boss -f`, `journalctl -u desk -f`.
11. **Access founder page:** `https://yourdomain.com/founder` (HTTPS via Let's Encrypt + certbot).

### Future Cloud Deployment (AWS / GCP / Azure)
- **VM:** Similar to VPS (Ubuntu VM).
- **Managed services:** RDS for Postgres (if using Postgres), ElastiCache for Redis (if high availability needed). Overkill for initial deployment; only if scaling to multiple regions or high-availability requirements.

---

## Open Questions (For Founder to Answer)

1. **Warehouse choice:** DuckDB (simpler, embedded) or PostgreSQL + Timescale (more powerful, scalable)? Recommendation: Start with DuckDB, migrate to Postgres if needed.
2. **LLM provider:** OpenAI (GPT-4) or Anthropic (Claude) or Gemini? Recommendation: OpenAI GPT-4-turbo (founder has key, good docs).
3. **Forex broker:** Which broker for Forex (~6 months)? Candidates: Oanda, Interactive Brokers, FXCM. Recommendation: Research after NSE live phase proves profitability.
4. **Alert delivery:** Where should health alerts reach founder? Options: Dashboard only, Email, Telegram, SMS, Phone call (via Twilio). Recommendation: Dashboard (P0) + Telegram (P1; easy setup, real-time).
5. **VPS provider:** AWS, GCP, Azure, DigitalOcean, Linode? Recommendation: DigitalOcean or Linode (cheaper, simpler for single VPS; ~$20/month for 4GB RAM).
6. **Repository visibility:** Keep public (current) or make private (safer for trade data, but secrets are gitignored)? Recommendation: Make private before adding any production config (even if secrets are gitignored, public repo invites scrutiny).

---

## Summary: What's Different from Current System?

### Current System (Monolithic)
- Boss logic mixed with desk logic inside `paper_scalp.py` (5400+ lines).
- No event bus (direct function calls).
- No broker adapter (paper-only).
- No pre-trade risk engine (risk checks scattered in `paper_scalp.py`).
- No structured decision log (decisions in .md files or print statements).
- No health monitoring (failures appear in logs only).
- No regime-conditional weighting (boss uses majority vote).
- LLM cost not tracked.
- No clear separation: pre-market / analyst / boss / desk / monitor / post-market are conceptually separate but code-tangled.

### Target System (Modular)
- Boss is separate service (orchestrates via event bus).
- Desk is separate service (executes, monitors).
- Risk is separate service (veto power).
- Event-driven (boss → desk via `ENTRY_APPROVED` event, not direct function call).
- Broker adapter (Dhan for NSE, swappable for Forex/crypto).
- Structured logs (every decision, every order, every state transition → warehouse).
- Health monitoring (monitor service checks all services, alerts on failure).
- Regime-conditional weighting (boss weights analysts by regime + track record, not majority).
- LLM budget + event-driven (only when uncertain, not per tick).
- Clear separation (each stage is independently testable).

### Migration Path
See `docs/04_MIGRATION_PLAN.md`. Do NOT rebuild from scratch (violates ponytail principle: reuse what works). Refactor incrementally: extract boss → separate module, add event bus, wrap in services, one PR at a time.

---

**Last updated:** 2026-09-26 (Rebuild planning package)

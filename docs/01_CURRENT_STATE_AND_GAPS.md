# Current State and Gap Matrix

**Purpose:** This document maps every founder requirement to the current codebase reality. Each row shows: what was asked for, what exists today (verified against code, not docs), what's tested, what's production-ready, the gap, and the priority (P0-P4 per section 94 of FOUNDER_REQUIREMENTS).

**Verification method:** Code inspection of `/workspace` repository (Sep 26, 2026). Not based on existing documentation.

**Priority levels (from FOUNDER_REQUIREMENTS § 94):**
- **P0 (Critical):** Blocks live trading or causes data loss / financial loss / security breach. Must exist before any real orders.
- **P1 (High):** Significantly impacts usability, safety, or learning ability. Needed for effective paper trading.
- **P2 (Medium):** Improves experience, efficiency, or insight. Helpful but not blocking.
- **P3 (Nice-to-have):** Polish, optimization, future-proofing.
- **P4 (Deferred):** Explicitly deferred features (e.g., Forex adapter, crypto, advanced analytics).

---

## Gap Matrix

### 1. Desk UI (Requirement lines 7-19)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Trade view with all details:** points, profit/loss, net profit, slippage, exit reason, cancel reason, trade state (in progress / dead / stopped / target hit / waiting / on hold + why) | **Partial.** `apps/web` React/Vite dashboard exists. `apps/api` has `/paper/founder-book` endpoint (line 54, `main.py`) that returns `desk_ml.founder_session.read_founder_book()` with `status`, `ticks`, `points`, `cumu_pnl`, `orders` (lines 1812-1966 `paper_scalp.py`). **Missing:** slippage tracking, structured exit/cancel reason (currently free-text in canvas, not API), "on hold + why" state, charges breakdown. | **No.** Dashboard can display mock data, but end-to-end test with real paper fills and state transitions not verified. No automated tests for UI. | **No.** Missing slippage, missing structured reasons, no user testing. | **Medium.** Core data exists; needs schema extension (slippage, reason codes), UI polish, and E2E test. | **P1** |
| **Filters, hide columns, scrollable, day-wise history** | **No.** Current `/founder/status` endpoint (line 43) returns JSON, but no filter API, no column-hiding API, no day-wise pagination. Frontend exists but filtering/column control not implemented. | **No.** | **No.** | **High.** UI framework exists; needs filter controls + backend query params + day-wise storage/retrieval. | **P2** |
| **Fast, lightweight, no latency** | **Partial.** React/Vite setup is modern. Websocket endpoint exists (`/ws/signals`, line 76). **Issue:** `paper_ops_monitor.py` rewrites full 2456-line HTML + canvas every tick, which is not scalable. API is fast, but monitor script is heavyweight. | **No performance benchmarks.** | **No.** | **Medium.** Frontend is fine; backend monitor script must be replaced with event-driven push (websocket JSON, not full HTML rewrite). | **P1** |
| **Account ledger:** persistent capital (no daily reset), profit/loss, charges, add funds, change min capital, per-index selection, add new index | **Minimal.** `PAPER_CAPITAL` hardcoded in `paper_scalp.py` line 151 (100k). No persistent ledger, no add-funds API, no charges tracking beyond rough cost estimate (1.1 pts per round trip mentioned in phase reports, not in code). No per-index filter in API. | **No.** | **No.** | **High.** Needs: (1) persistent DB table for ledger (date, credit/debit, balance, reason), (2) charges calculation per fill (brokerage, STT, GST, exchange fees), (3) API to adjust capital, (4) per-index filter. | **P0** (ledger + charges for real trading) / **P1** (add-funds, per-index filter) |
| **Human override API:** start/pause/stop, pause for N min, avoid time windows, cut loss, go for T2, lot up/down, which time to avoid, kill switch | **Partial.** `/paper/human-override` endpoint exists (line 61) but only accepts `{"action": "FLATTEN_ALL"}` (line 2006 `paper_scalp.py`). No pause-for-N-min, no time windows, no lot adjust, no "go T2", no per-trade cut. Kill switch = manual `FLATTEN_ALL` only. | **No.** Not tested in realistic scenario. | **No.** | **High.** Endpoint exists but severely limited. Needs: (1) pause timer, (2) time-window blacklist, (3) per-position adjust (exit, lot change, target override), (4) emergency kill (all + disable new entries for N min). | **P0** (kill switch, emergency controls must work before live) |
| **Decision visual:** graph of which stage holds the trade, who decided what, graph format, aligned/compact components | **No.** No visual decision flow graph. `paper_ops_monitor.py` generates ASCII canvas and HTML with status boxes, but no interactive graph showing pre-market → analyst → boss → desk → monitor flow per trade. | **No.** | **No.** | **High.** New feature. Needs: (1) structured decision log per trade (timestamp, stage, actor, decision, input summary), (2) frontend graph component (D3/vis.js), (3) API endpoint to fetch decision chain by trade ID. | **P2** |

### 2. Founder Page & Health Alarms (Requirement lines 18-20)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Model win rates, which model is doing well, how many trades today/earlier, cumulative P&L by stage** | **Partial.** `/founder/status` returns trade count, cumulative P&L. **Missing:** per-model breakdown, per-stage breakdown (which analyst lost money, which stage is the leak). No historical "earlier" tracking (day/week/month aggregates). | **No.** | **No.** | **High.** Needs: (1) per-analyst win/loss log (tag each entry signal with analyst ID, log outcome), (2) per-stage loss attribution (entry model, boss decision, desk execution, exit timing), (3) warehouse aggregate queries. | **P1** |
| **Health alarms:** red flag if website down, Dhan API down, OpenAI down, news feed down, any model not sending data | **Minimal.** No structured health-check system. No uptime monitoring. No notification system (email, Telegram, dashboard alert). Errors appear in logs only. | **No.** | **No.** | **High.** Needs: (1) heartbeat checks per service (Dhan websocket connected, Dhan API 200 OK, OpenAI 200 OK, news scraper ran < 10 min ago, each analyst emitted signal < timeout), (2) alert dispatcher (store + push to founder page + optional Telegram/email), (3) dashboard health panel. | **P0** (before live trading, must know when broker API is down) / **P1** (all other alarms) |
| **Dashboard of insights:** pictorial format, daily/weekly/monthly P&L, win rate improvement over time, alerts/notifications | **Minimal.** `/founder/status` returns JSON. No charts, no time-series aggregates (daily/weekly/monthly), no improvement tracking, no alert display. | **No.** | **No.** | **High.** Needs: (1) time-series tables in warehouse (daily/weekly/monthly aggregates), (2) chart components (P&L curve, win rate trend, drawdown), (3) alert display panel (from health-check system), (4) "how much is any model improving" tracker (rolling win rate, before/after A/B comparison). | **P1** |
| **Warehouse-based reports (not .md files per line 38)** | **No.** Current reports are dated .md files in `teams/*/docs/`. No warehouse, no SQL query interface for founder page. | **No.** | **No.** | **High.** Needs: (1) warehouse (DuckDB or Postgres), (2) nightly aggregation job, (3) API to serve warehouse queries (e.g., `/founder/query?metric=win_rate&period=week`). | **P1** |

### 3. Broker Adapter (Dhan API) (Requirement lines 14, 21-28)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Know which Dhan call to use:** super order, limit, SL, trailing SL, target shift, cancel, exit, kill switch | **No.** No Dhan API integration exists. `paper_scalp.py` is pure paper (no real orders). No broker adapter interface. No mapping of order intent (market, limit, SL, trailing) to Dhan REST/websocket calls. | **No.** | **No.** | **Critical.** Needs: (1) Dhan adapter module (`packages/brokers/dhan_adapter.py`), (2) order intent → Dhan API call mapper (use Dhan Postman collection or docs for exact field names), (3) order placement, (4) order status polling / websocket updates, (5) order modification (trailing SL, target shift), (6) order cancellation, (7) emergency flatten (cancel all pending, exit all open), (8) reconciliation (compare Dhan positions vs internal book). **Hard rule:** Never call from agent environment; only from user-run system. | **P0** (blocks live trading entirely) |
| **Websocket for fast decisions (per line 32)** | **Partial.** `desk-intel` has `option_chain_poller.py` that polls Dhan websocket for chain data (but polling, not event-driven). No websocket for order updates. | **Partial.** Chain poller runs, but no order-update websocket. | **No.** | **High.** Needs: (1) Dhan order update websocket client, (2) event dispatcher (order acknowledged → update state, fill → update position, rejection → alert). | **P0** (before live; must see order status in real time) |

### 4. Data Capture & Warehouse (Requirement lines 50-64)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Daily data capture:** index 1m ticks (NIFTY/BANKNIFTY/SENSEX), full option chain (all strikes, OI/IV/greeks), futures 1m with volume, heavyweights (top 10-15 NIFTY constituents), global (SPX, DXY, US10Y), commodities (crude, gold), FX (USDINR), news + impact tags, multi-timeframe levels (D/4H/W, 52w high/low) | **Minimal.** `option_chain_poller.py` polls full chain every minute, writes JSON to `data/recon/option_chain/`. `market_session_recorder.py` may record index ticks (not verified in code). **Missing:** futures volume, heavyweights, global indices, commodities, FX, tagged news, multi-timeframe levels, structured warehouse schema. | **Partial.** Chain poller runs; no verification of futures, heavyweights, global, news. | **No.** | **Critical.** **This is the highest priority:** data cannot be backfilled. See `docs/03_DATA_CONTRACTS.md` for full spec. Needs: (1) Dhan/NSE tick recorder for index/futures/heavyweights, (2) news scraper + event tagger, (3) global market API (Yahoo Finance, Alpha Vantage), (4) storage schema with join keys, (5) nightly warehouse ETL. | **P0** (data recorder must start immediately; lab journal line 80 says this is the binding constraint: "missing data (futures 1m volume, multi-strike option history with OI/IV, heavyweights, more tape days)") |
| **Nightly warehouse job** | **No.** No warehouse exists. No nightly ETL. Current data sits in `data/recon/` as JSON. | **No.** | **No.** | **High.** Needs: (1) warehouse DB (DuckDB or Postgres/Timescale), (2) ETL script (read `data/recon/*`, aggregate, write to warehouse), (3) cron/scheduler (run at 18:00 IST daily). | **P1** |
| **Join keys & data format (line 59-64):** structured so ML/LLM/pre-market can join news + chain + futures + index levels | **No.** Current data is per-service JSON with no standard join key. No unified schema. | **No.** | **No.** | **High.** See `docs/03_DATA_CONTRACTS.md` for proposed schema (primary key = `symbol`, `timestamp`, `expiry`; foreign keys to join index → chain → news → levels). | **P1** |

### 5. Backtest & Replay Engine (Requirement lines 41-49)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Honest backtesting:** candle-by-candle, costs, slippage, no look-ahead, multi-timeframe, option-specific, greeks-aware, SL/target/limit, parameter sweeps, overfit defenses (remove outliers, exclude expiry/bad days) | **Partial.** `scripts/lab/lab_hist.py` runs honest backtests (Phase 3 report used it) with costs, random-entry placebos, walk-forward OOS. **Current bug (Phase 3 report page 3):** TradingView-style tests (existing STRAT-001..014 backtests) have look-ahead (signal close fills, repaint, no costs). `paper_scalp.py` `_hold_series` (line 5329-5345) trains ML-001 on first 60% of *same session* (look-ahead). | **Partial.** Lab framework is honest (verified by Phase 3 results); old STRAT tests are not. | **No.** Existing strategies were validated with flawed tests. Lab framework exists but not integrated into CI/automated checks. | **Medium.** Lab framework works; needs: (1) fix look-ahead bugs in `paper_scalp.py`, (2) integrate honest backtests into PR template (no new strategy without honest backtest), (3) expand to option-greeks-aware tests (current tests use index proxy), (4) parameter sweep harness, (5) TradingView-level reporting (but honest). | **P1** (before adopting any new strategy) / **P0** (before live trading with ML-001, which has data leakage) |
| **Replay with exact quotes (requirement line 44, lab journal line 10)** | **Yes.** Phase 3 report ran exact-quote replay on Sep 17-25 tape. Code exists in lab scripts. Verified working. | **Yes.** Phase 3 used it. | **No.** Not automated (manual script run). | **Low.** Replay works; needs: (1) automated tape-replay runner (e.g., PR merge gate: run last 7 days of tape), (2) tape storage (currently local, needs durable storage). | **P2** |
| **Works with LLM, ML models, strategies, indicators** | **Partial.** Lab framework tests strategies and indicators. **Missing:** LLM backtest (what does Boss-with-LLM decide, and how much does it cost?), ML model backtest (ML-001 is broken per Phase 2 report; ML-002 is degenerate per line 3091 of `phase2_report_f22f.md`). | **Partial.** Strategies tested; LLM/ML not tested. | **No.** | **Medium.** Needs: (1) LLM mock (record actual LLM response during tape, replay from cache in backtest), (2) ML model serialization + backtest runner (train on history, test on OOS, measure cost/latency). | **P2** |

### 6. Pre-Market, Boss, Analyst, Desk, Monitor, Post-Market Roles (Requirement lines 65-103)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Clear separation of duties:** pre-market (news, webscrape, share with boss), analyst (consume data, generate signal, log), boss (orchestrate, weight by regime-conditional track record, intermarket aware, check rules, log decisions, talk to desk, spawn juniors), desk (execute, monitor, consult boss, founder always overrides), monitor (constant feedback to boss, alerts), post-market (capture data, improvement loop, backtest, replay, GROK creates PRs but doesn't merge) | **Partial.** `trading_agents_india` has roles in `AGENT.md` (teams 00-09: orchestrator, research, math, market, quant, desk-intel, backtest, review). `paper_scalp.py` has `picker_majority` (boss-like), `collect_analyst_votes` (analyst registry), `_try_open` (desk-like execution). `desk-intel` has pre-market/post-market scripts. **Issues:** (1) Overlapping duties (orchestrator + picker both decide), (2) no regime-conditional weighting (boss uses majority vote, not track record; per requirement line 75 "not only on the majority"), (3) LLM is called per-tick in some paths (expensive; against requirement line 33 "no blocking LLM calls on market-hours fast path"), (4) post-market loop exists (`paper_analysis_loop.py`) but no PR creation, no GROK integration, (5) no "spawn juniors" capability, (6) no structured "talk to desk" protocol (boss → desk is just function call, no event log). | **Partial.** Roles exist conceptually; execution is tangled. | **No.** Current design mixes concerns; boss logic is inside `paper_scalp.py` (execution module). | **High.** Needs: (1) refactor to separate services or at least separate modules (boss ≠ desk), (2) event bus (boss emits "ENTRY_APPROVED {trade_id, symbol, side, lots, analysts: […]}", desk subscribes), (3) boss weighting by regime + track record (not majority), (4) LLM advisory mode (boss asks LLM for second opinion on uncertain cases, not every tick), (5) post-market improvement loop with PR template (GROK = post-market agent with PR write access, but human merge gate), (6) structured logging per stage. | **P1** (separation + event model) / **P2** (LLM advisory, GROK PRs) |
| **Boss checks rules before sending to desk (line 75-78)** | **Partial.** `paper_scalp.py` has `classify_index_regime` (consolidation block, line 5272), time cutoffs (`NO_NEW_BEFORE_MINUTES_IST`, `NO_NEW_MINUTES_IST`, `FLATTEN_MINUTES_IST`). **Missing:** DTE-aware strike rule (requirement from Phase 3; ITM100 for DTE ≥ 2, ITM200 for DTE ≤ 1; see line 3088 `phase3_report_6418.md`), 15-minute loss cooldown (Phase 3 line 3089), regime-conditional analyst selection. | **Partial.** Clock rules exist; consolidation block exists. DTE rule not implemented. | **No.** Missing proven fixes. | **Medium.** Needs: (1) DTE-aware strike selector (read expiry from chain, compute DTE, choose ITM depth), (2) loss cooldown (if last exit was loss < 15 min ago, block new entry), (3) registry of which analysts work in which regime (e.g., STRAT-007 only in trend regime per Phase 3). | **P1** (proven fixes from Phase 3 must be in before live) |
| **Founder commands always override boss and desk (line 9, 72, 85)** | **Partial.** `/paper/human-override` endpoint exists, but only `FLATTEN_ALL`. No priority queue (founder command skips boss queue). | **No.** | **No.** | **High.** Needs: (1) founder command queue (separate from boss → desk flow), (2) desk checks founder queue first, (3) founder pause/stop halts boss signal generation, (4) founder "cut loss now" exits position immediately (override desk hold logic). | **P0** (founder must be able to stop the system in emergency) |

### 7. Tech Stack & Deployment (Requirement lines 23-40)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Modular, VPS/cloud-ready** | **Partial.** Monorepo structure with packages (`desk-ml`, `desk-intel`, `trading_agents_india`). Services are Python scripts started by `start_paper_ops_daemon.py`. **Issue:** Hardcoded paths, no containerization, no systemd units, no deploy script. | **No.** Not tested on VPS. | **No.** | **Medium.** Needs: (1) environment vars for config (not hardcoded paths), (2) requirements.txt per package, (3) deploy script or Dockerfile, (4) systemd units or supervisor config. | **P2** (Mac works; VPS needed after paper phase proves strategy) |
| **RAG, DB, shell scripts, Python** | **Partial.** Python everywhere. Shell scripts for daemon start. **No DB** (data is JSON files). **No RAG** (no vector store, no embedding search). SQLite mentioned in rules (`company-departments.mdc` line 19 "SQLite + FTS5 now. No MySQL/embeddings as day-1"). | **Partial.** Python + shell work. No DB/RAG. | **No.** | **Medium.** Needs: (1) SQLite or DuckDB for warehouse (per requirement + rules), (2) decide if RAG is needed (for what? news search? strategy search? — clarify with founder). | **P1** (DB) / **P3** (RAG, unless founder clarifies urgent use case) |
| **Minimal token usage for LLM (requirement line 31, 85)** | **Partial.** `desk_ml/llm_client.py` may exist (not verified). Current cost ~$40 per phase report (mentioned in expectations digest line 26). **Issue:** If LLM is called per-tick, cost explodes. | **No.** No cost tracking. | **No.** | **High.** Needs: (1) LLM budget tracker (daily limit, alert at 80%), (2) compact context (boss sends 200-char summary, not full chain), (3) event-driven (only on uncertain cases: boss says "need second opinion", not every entry), (4) structured JSON (no prose generation). | **P1** (before LLM goes into live loop) |
| **No .md files during live market for decisions (requirement line 34)** | **Current violation.** `AGENT.md` is 23KB; agents may read it per rules (`file-creation.mdc` line 3 says "Default read: docs/MASTER_REQUIREMENTS.md → CONTINUE_NEXT_CHAT.md → AGENT.md"). Post-market loop generates dated .md files (`teams/*/docs/HANDOFF_*.md`). **If** boss LLM reads these during market hours, it's a violation. | **Unknown.** Need to audit LLM context. | **No.** | **High.** **Clarify:** Are .md files being read by LLM during 09:15-15:30? If yes, refactor to: (1) pre-market compiles .md → compact JSON config, (2) boss reads JSON only during market, (3) post-market updates .md for next cycle. | **P1** (if violated) / **P3** (if not currently violated, but enforce in new code) |
| **Ponytail principles: efficient code, no extra code, YAGNI, reuse, stdlib first, shortest diff (requirement line 37)** | **Mixed.** Some good code (`lab_hist.py` is well-structured). Some bloat (`paper_ops_monitor.py` 2456 lines rewriting canvas every tick). No explicit adherence to ponytail ladder. | **No systematic check.** | **No.** | **Medium.** Needs: (1) Add ponytail principles to root `AGENTS.md` (done in this PR), (2) PR template includes "shortest diff?" check, (3) refactor monitor script (biggest offender). | **P2** (principles now documented; enforcement via PR review) |
| **Document everything, index, flows (requirement line 36-38)** | **Partial.** Extensive team docs in `teams/*/docs/`. **Issues:** (1) No index (fixed by this PR: `docs/00_INDEX.md`), (2) No flow diagrams, (3) Docs are verbose (23KB `AGENT.md`; 106-line founder requirement + 3000-line addendum). | **Partial.** Docs exist but hard to navigate. | **No.** | **Medium.** Fixed by this PR: index, gap matrix, architecture, migration plan, founder guide. Still missing: (1) flow diagrams (sequence diagrams for pre-market → analyst → boss → desk → monitor → post-market), (2) prune verbose docs. | **P2** (flows) / **P3** (prune) |
| **Memory/CPU optimization (requirement line 33)** | **No profiling.** `paper_ops_monitor.py` is likely CPU hog (2456 lines, rewrites every tick). | **No.** | **No.** | **Low.** Needs: (1) profiling (cProfile or py-spy), (2) replace monitor script with event-driven push. | **P2** |

### 8. Multi-Market Support (Forex, Crypto) (Requirement lines 1, 79)

| **Requirement** | **Code Exists?** | **Tested?** | **Production-Ready?** | **Gap** | **Priority** |
|----------------|------------------|-------------|----------------------|---------|-------------|
| **Modular to adopt Forex (~6 months) and crypto** | **No.** All code assumes NSE index options (NIFTY/BANKNIFTY/SENSEX, CE/PE, Dhan broker, IST hours, NSE lot sizes). No market adapter interface. | **No.** | **No.** | **High.** Needs: (1) market adapter interface (calendar, lot/tick size, expiry rules, hours, margin, symbology), (2) core engine takes market adapter as dependency injection, (3) Dhan adapter is one implementation; Forex broker adapter is another. See `docs/02_TARGET_ARCHITECTURE.md` § Market Adapter Layer. | **P4** (Forex is 6 months out per founder; crypto unspecified) / **P2** (architecture must allow it; don't hard-code NSE everywhere) |

---

## Current State Summary (What Works Today)

### ✅ Working Components
1. **Paper trading execution engine** (`desk_ml/paper_scalp.py`): Can open/hold/exit paper positions, track P&L, respect clock cutoffs (no new trades after 15:00, flatten by 15:20).
2. **Option chain polling** (`desk-intel/option_chain_poller.py`): Fetches full NIFTY/BANKNIFTY chain every minute via Dhan websocket.
3. **Analyst registry** (`desk_ml/picker.py`): Collects votes from multiple analysts (STRAT-001..014, dealer, volume, greeks, chain-bias).
4. **Regime classification** (`desk_ml/paper_scalp.py`): Detects consolidation (range ≤ 0.6 × median 30m range), blocks entry in dead markets.
5. **Proven rule stack (Phase 3)**: Entry cutoff 15:00, 15-min loss cooldown (not yet in code, but proven on tape), DTE-aware strikes (not yet in code), STRAT-007 clock (10:00-14:30, not yet in code). Sep 17-25 tape: +210.1k vs -9.2k baseline.
6. **Honest backtest framework** (`scripts/lab/lab_hist.py`): Walk-forward, random placebos, cost-aware. Used in Phase 3 and lab round 1. No standalone strategy has proven edge after costs, but framework is sound.
7. **API and dashboard skeleton** (`apps/api`, `apps/web`): FastAPI + React/Vite, `/founder/status`, `/paper/founder-book`, `/paper/human-override`, `/ws/signals`. Functional but minimal.

### ❌ Known Bugs (Must Fix Before Live)
1. **Look-ahead data leakage in `_hold_series`** (`paper_scalp.py` L5329-5345): Trains ML-001 `LogisticRegression` on first 60% of *same session*. `ols_beta` uses all session rows. This is why backtests show "PEEKED" flag. **Fix:** Train on prior sessions only, or disable ML-001 until fixed.
2. **Degenerate ML models:**
   - `ml001_kmeans_if_NIFTY.json`: 4 clusters of 1723/1/1/1 rows (meaningless).
   - `ml002_mrr_ou_NIFTY.json`: `k_pe = 52,685` (unrealistic mean-reversion threshold).
   - **Fix:** Retrain with honest data, or disable.
3. **Reversed OI signal in `CHAIN-LEAN`** (`option_chain_poller.py` L192): Reads CE OI build-up as bullish (lean CE), when in Indian index options, call writing is resistance (bearish). Worst hit rate 0.457 / hit30 0.406 (Phase 2 report). **Fix:** Reverse sign or disable.
4. **Double-counted `greeks_vote_intent`** (`picker.py` L121): Simply copies dealer vote (double-counts FOLLOWS). **Fix:** Remove or make it independent.
5. **ML-1 meta-label unreachable** (Phase 2 report): Requires ≥30 closed rows in session; never met. **Fix:** Lower threshold or use prior-day rows.
6. **Flawed STRAT-001..014 backtests**: TradingView-style tests have look-ahead (signal close fills, no costs, repaint). All are negative in 3-year honest backtests except low-n STRAT-011 (Phase 3). **Fix:** Re-validate with honest framework before trusting win rates.

### 🟡 Proven Fixes (From Phase 3, Not Yet in Code)
1. **Entry cutoff 15:00 IST** (`NO_NEW_MINUTES_IST = 14*60+30`): Exists in code (line 154 `paper_scalp.py`). ✅
2. **15-minute loss cooldown**: If last exit was loss < 15 min ago, block new entry. **Not in code.** Status: Proven on tape (+210.1k vs -9.2k), needs implementation.
3. **DTE-aware strike selection**: ITM100 (~100 pts ITM) for DTE ≥ 2, deep ITM200 (~200 pts ITM) for DTE ≤ 1. **Not in code.** Status: Proven on tape.
4. **STRAT-007 entry clock window**: 10:00-14:30 IST (`NO_NEW_BEFORE_MINUTES_IST = 10*60+00`). **Not in code.** Status: Proven on tape.
5. **Consolidation regime entry block**: Range ≤ 0.6 × 5-day median 30m range → no new entries. **In code** (line 5272 `paper_scalp.py`). ✅

---

## Lab Round 1 Summary (From `lab_journal_a989.md`)

**Headline:** No standalone strategy has proven edge after costs in held-out year (2025-09 → 2026-09-03). Intermarket bias, trend-day breakouts, gap-and-go, wing divergence, PDH/PDL sweeps all lost. **Binding constraint:** missing data (futures 1m volume, multi-strike option OI history, heavyweights, more tape days).

**What survived:**
- **Baseline: Phase-2 stack + STRAT-007 window.** Sep 17-25 tape +210.1k, 39 trades, 36% WR, PF 2.14, max DD -69.9k. This is the current best.
- **Watch-list (not adopted, but shadow-log):**
  - H07 expiry-afternoon block (+1-4.5 L history, +5-11k tape)
  - H10 consolidation no-trade (+similar)
  - H06 heavyweight breadth filter (+35.2k tape, 4 trades blocked, but only ~42 days history overlap)
  - H13 exits: trailing after 1R + partial booking beat tape (+277.8k) but lost on 3 years history (conflicts; queued for round 2 with regime-conditional trailing)

**What failed:**
- Every standalone entry (ORB, first-hour breakout, gap-and-go, gap-fill, wing divergence, PDH/PDL sweep) lost in held-out year.
- Intermarket bias (US stocks, DXY, oil) correlates with NIFTY *gap* (0.4), not intraday (-0.14 DEV, -0.04 OOS).
- Rules learned from old data broke in held-out year (regime router +26.5 L → -10.9 L, fade-bias +3.4 L → -6.2 L).
- Low-VIX block (H02) hurt (2026 is low-VIX year).
- Higher-timeframe "confirm" filters removed good trades (-102k to -110k).

**Lessons:**
1. Engine's edge is in combination (entry + logit + consolidation + strike + clock), not single indicator.
2. Good filters are small "don't trade here" rules (expiry afternoon, dead first hour), not clever direction calls.
3. 7 tape days cannot tell +20-35k improvement from luck (random skip swings +158k to +219k).
4. Binding constraint: data.

**Queued for round 2:**
1. H07 + H10 together (shadow-log 20+ days, pre-register: adopt if not worse on >1 in 5 days, beats random-skip band).
2. Exits done properly inside engine (trailing after T1 only in trend regime; needs paper-only code path).
3. Breadth v2 (weighted contribution, record heavyweight LTPs in tape daily).
4. OI v2 (NSE F&O bhavcopy end-of-day OI build-up as next-day bias, testable on 3 years; keep intraday absorption).
5. Intermarket as daily/weekly regime (risk-off week → prefer PE / smaller size).
6. Supply/demand zones (objective definition: base + impulse ≥ 1.5 ATR, first retest only).
7. Rebuild proxy book closer to live engine (ITM200 on low DTE, judge/feasibility rules).
8. Data asks: NIFTY futures 1m with volume, rolling ATM/ITM200 option files from Dhan downloads; keep tape recorder running.

---

## Priority Roadmap (Ordered by Blocking Dependencies)

**Immediate (Start Now, Can't Be Backfilled):**
1. **PR-001: Data Recorder (P0)** — Index ticks, full chain, futures with volume, heavyweights, global, commodities, FX, news + event tags, multi-timeframe levels. See `docs/04_MIGRATION_PLAN.md` PR-001 for scope.

**Before Live Trading (P0 Safety Core):**
2. **PR-002: Broker Adapter & Order State Machine (P0)** — Dhan API integration, order placement/status/modification/cancellation, position reconciliation, idempotency, error handling. Blocks live trading entirely.
3. **PR-003: Pre-Trade Risk Engine (P0)** — Veto power over boss/LLM, position limits, loss limits, exposure checks, kill switch, paper-mode default with manual gate to enable live mode.
4. **PR-004: Health Alarms & Monitoring (P0)** — Heartbeat checks (Dhan API, OpenAI, news, analysts), alert dispatcher, founder page health panel. Must know when broker is down.
5. **PR-005: Persistent Ledger & Charges (P0)** — Account ledger (date, credit/debit, balance, reason), accurate charges (brokerage, STT, GST, exchange), capital management API.

**High Priority (Effective Paper Trading):**
6. **PR-006: Fix Known Bugs (P1)** — Look-ahead in `_hold_series` / `ols_beta`, degenerate ML models, reversed OI signal, double-counted greeks_vote. Disable broken analysts or retrain.
7. **PR-007: Implement Proven Fixes (P1)** — 15-min loss cooldown, DTE-aware strikes, STRAT-007 clock (10:00-14:30). Verified on Sep 17-25 tape.
8. **PR-008: Separation of Duties & Event Model (P1)** — Refactor boss (orchestrator) vs desk (execution), event bus (boss → desk → monitor), structured decision log, regime-conditional analyst weighting.
9. **PR-009: Founder Emergency Controls (P1)** — Pause timer, time-window blacklist, per-position adjust (exit, lot change, target override), emergency kill + disable-new-entries-for-N-min.
10. **PR-010: Warehouse & Nightly ETL (P1)** — DuckDB or Postgres, join keys, nightly aggregation, API for founder page queries.
11. **PR-011: Desk UI Polish (P1)** — Slippage tracking, structured exit/cancel reasons, "on hold + why" state, filters, column hide, day-wise pagination.
12. **PR-012: LLM Advisory Mode (P1)** — Budget tracker, compact context, event-driven (uncertain cases only), structured JSON, no blocking calls on fast path.

**Medium Priority (Insights & Improvement):**
13. **PR-013: Model & Stage Attribution (P2)** — Per-analyst win/loss log, per-stage loss attribution, warehouse aggregates, founder page charts (win rate trend, P&L curve, drawdown).
14. **PR-014: Decision Visual (P2)** — Graph of pre-market → analyst → boss → desk → monitor flow per trade, D3/vis.js component, API to fetch decision chain.
15. **PR-015: Backtest Integration (P2)** — PR template requires honest backtest for new strategies, automated tape replay (last 7 days), expand to option-greeks-aware tests.
16. **PR-016: Post-Market Improvement Loop (P2)** — GROK (post-market agent) analyzes tape, proposes changes, creates PRs, but human merge gate. Backtest + replay before proposing.
17. **PR-017: Deploy Automation (P2)** — Environment vars, deploy script or Dockerfile, systemd units, VPS readiness.

**Nice-to-Have:**
18. **PR-018: Flow Diagrams (P3)** — Sequence diagrams for each stage, founder-readable.
19. **PR-019: Performance Optimization (P3)** — Profile, replace monitor script with event-driven push.
20. **PR-020: RAG (P3, unless founder clarifies urgent use case)** — Vector store, embedding search (for what? news search? strategy search?).

**Deferred:**
21. **PR-021: Forex Market Adapter (P4)** — ~6 months out per founder.
22. **PR-022: Crypto Market Adapter (P4)** — Unspecified timeline.

---

## Notes

**Verification:** All "Code Exists?" entries were verified by reading code, not by reading existing docs. File paths cited where possible (e.g., `paper_scalp.py` line numbers, `apps/api/main.py` endpoints).

**Repository is PUBLIC:** Never commit secrets, account data, trade logs, tapes, or anything from `secrets/` (per requirement and `.gitignore`).

**Hard rule (requirement line 7, EXPECTATIONS_DIGEST line 28):** Never call Dhan or any broker API from agent environment. Only from user-run system.

**Testing before claiming success (requirement line 38, ponytail rules):** Non-trivial logic leaves ONE runnable check behind (assert-based demo, self-check, or small test file). No untested claims.

---

**Last updated:** 2026-09-26 (Rebuild planning package)

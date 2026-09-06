# OpenAI Design Council — Market-hours paper agents (2026-09-06)

**Layer:** `HYPOTHESIS` (design council)  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Mode default:** `PAPER` (`LIVE` refuses orders)  
**OpenAI model used:** `gpt-5.4`  
**Key present:** `True` (value never logged)  
**UTC:** `2026-09-06T22:40:20+00:00`  
**Finish:** `stop` (completion tokens ~3325)

**Founder ask:** From 09:00 IST, persona agents analyze + paper-trade CE/PE using OPTIDX premium charts + chain (fake-breakout guards); share handoffs; **trader alone** decides paper fills; RAG/SQLite for speed; PhD math + market; news + risk + existing strategies; TradingAgents-style coordination; EOD recon; backtest; share results with OpenAI; dashboards/wires; **no live orders** until founder + gate.

**Related:** [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md) · prior council [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](OPENAI_DESIGN_COUNCIL_2026-09-06.md) · build plan [`PLAN_MARKET_HOURS_PAPER_AGENTS.md`](PLAN_MARKET_HOURS_PAPER_AGENTS.md) · RAG [`../../01_research/docs/AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)

EXTERNAL: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0).

---

## Local co-sign (00 boss desk)

### ACCEPT

- PAPER-first market-hours loop extending `packages/trading_agents_india` (not a second product).
- Trader-only paper fill authority; execution path stays refuse for LIVE.
- OPTIDX premium + 3m chain as primary objects; INDEX proxy only if labeled `HYPOTHESIS` / `DATA_INSUFFICIENT`.
- Fake-breakout guards as `HYPOTHESIS` filters (not catalog deletes).
- News / extreme PCR → **hold ticket**, not alpha, not STRAT/MIX delete.
- 5m ST/MACD/RSI = **confirm-or-kill** only ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)).
- Separate KBs: `trading_agents_india.sqlite` + `agent_rag.sqlite` — **never** overwrite `transcripts.sqlite`.
- EOD recon → `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; no blind auto-retune ([`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md)).
- Anonymized paper/backtest rollups may be shared with OpenAI for review notes — **no fake wr**.
- Honest DI on depth/ticks: Dhan Live Market Feed documents ticker/quote/full; repo decode partial/placeholder — **no depth alpha**.

### REJECT

- Live Dhan orders / `/alerts/orders` before founder allow + live gate + `RESEARCH_READY`.
- STRAT-015+ or deleting STRAT-001–014 (KEEP_ALL).
- Claiming sub-second tape/depth edge from incomplete WS decode.
- Auto-fill “truth” without trader confirmation in paper phase.
- News-sentiment alpha engine; StockTwits/Reddit as SOURCE_FACT.
- Overwriting `transcripts.sqlite`; inventing Dhan REST fields/lots/fills.
- Promoting any MIX/STRAT from this council alone.

### Map OpenAI persona names → desk

| OpenAI id | Display | Desk mapping |
|-----------|---------|--------------|
| P01 OpenDrive | Conductor | 00 boss + session orchestrator |
| P02 QuantLens | Premium/math | 02 + 04 (`technical` / premium hook) |
| P03 ChainWatch | Chain/OI | 05 desk-intel + `chain_watcher` |
| P04 PriceAction | Structure/traps | 04 staging + CF MIX inputs (PAPER_WATCH) |
| P05 RiskMarshal | Risk veto | 06 risk triad + `MIX-TA-EXEC-SANITY` |
| P06 NewsHold | Event hold | 05 news hook + `MIX-TA-EVENT-HOLD` |
| P07 ExecutionScribe | Paper fills | 07/08 trader + ledger |
| P08 ResearchJudge | EOD/backtest | 06 + 09 + `agent_rag` paper-backtest |

---

## OpenAI council summary

**OpenAI verdict string:** `APPROVE_PAPER_BUILD_FIRST`  
**00 desk normalized verdict:** `APPROVE_WITH_GUARDRAILS` (same meaning: build paper path now; live blocked)

### Council bullets

- PAPER only; trader manually confirms fills.
- Use STRAT-001..014 only; no new STRAT ids (new clubs = MIX-* if needed).
- Start 09:00 IST persona cycle; market-hours handoffs.
- Alpha candidates from premium + chain + price structure; news = hold/filter.
- 5m ST/MACD/RSI used only as confirm-or-kill.
- RAG + SQLite for speed; never overwrite `transcripts.sqlite`.
- DI-honest: Dhan WS supports ticker/quote/full; repo depth decode partial.
- Live blocked until founder signoff + gates + `RESEARCH_READY`.

### Implement now (OpenAI → priority)

| P | Item | Owner (OpenAI) | Layer | Boss note |
|---|------|----------------|-------|-----------|
| P0 | market_hours_orchestrator | desk-intel | SOURCE_FACT | Ship under `trading_agents_india` + 00; skeleton already started |
| P0 | dhan_ingest_index_options | trading_agents_india | SOURCE_FACT | Charts + chain via `dhan-client`; DI if empty |
| P0 | paper_execution_ledger | desk-intel | VALIDATION | `ledger.py` + recon jsonl; trader-confirmed only |
| P0 | fake_breakout_guard_pack | trading_agents_india | HYPOTHESIS | Chain watcher flags; not catalog delete |
| P0 | strategy_router_001_014 | trading_agents_india | VALIDATION | KEEP_ALL; cite MIX-DEFAULT-BUY + MIX-TA-* |
| P1 | confirm_or_kill_5m_pack | desk-intel | VALIDATION | `/desk` only; not customer entry |
| P1 | rag_sqlite_research_cache | desk-intel | SOURCE_FACT | Use **`agent_rag.sqlite`** (exists); not a second invent path |
| P1 | eod_recon_retune | desk-intel | VALIDATION | Align POST_MARKET + RETUNE_GATE |
| P1 | backtest_harness_premium_chain | trading_agents_india | VALIDATION | Via 06 + agent_rag paper-backtest; NO_PROMOTE default |
| P1 | dashboard_surfaces | desk-intel | SOURCE_FACT | `/desk` paper; `/` stays customer-safe |
| P2 | docs_wires_runbooks | desk-intel | SOURCE_FACT | This council + PLAN + ADOPT |

### Defer

- LIVE order routing.
- Any STRAT-015+ invention.
- Depth/orderbook alpha claims.
- Tick-accurate microstructure models.
- Auto-fill simulation as truth.
- Cross-broker adapters.
- News sentiment alpha engine.

### PAPER vs LIVE

```json
{
  "paper_default": "yes",
  "paper_fill_authority": "trader_alone",
  "live_status": "blocked",
  "live_unlock_requires": [
    "founder_yes",
    "backtest_gates_pass",
    "RESEARCH_READY",
    "ops_runbook_complete",
    "risk_gate_signoff"
  ]
}
```

### Depth / ticks (honest DI)

| Field | Value |
|-------|--------|
| Claim | Use documented Dhan WS ticker/quote/full confidently; **do not** claim reliable depth/orderbook alpha now |
| Dhan support | Live Market Feed documents ticker, quote, full packet classes ([live-market-feed](https://dhanhq.co/docs/v2/live-market-feed/)); up to 5 sockets / 5000 instruments |
| Repo status | `dhan_client.decode`: ticker implemented; quote/full/depth **placeholder** |
| Build rule | If depth-like fields arrive, store raw separately, mark experimental, **exclude from alpha and promote gates** until 02/03 validate |

### DATA_INSUFFICIENT (council)

- Exact chain refresh vs desk **3m** default under option-chain **1/3s** unique budget.
- Guaranteed OPTIDX premium candle history per contract.
- Reliable intraday OI at chosen cadence.
- Precise WS full/depth payload offsets (VERIFY FROM DOCS).
- Founder-approved first underlyings/expiries for paper (default: NIFTY/BANKNIFTY/SENSEX from yaml).
- Canonical spoken applicability of every STRAT-001–014 on OPTIDX premium (bind exists; engine map still HYPOTHESIS).

### Must not

- Place live orders now.
- Invent STRAT-015+.
- Use news as standalone alpha.
- Use ST/MACD/RSI beyond 5m confirm-or-kill.
- Claim depth support beyond validated docs + decode.
- Overwrite `transcripts.sqlite`.
- Report fake win rates or cherry-picked backtests.

---

## HANDOFF — what implementation agents build first

Ordered (00 ticket call). Do **not** implement the full engine in the council agent.

1. **Lock contracts** — session clock IST, tick cadence 30–60s (default 45s), dead-bands HOLD-only, `mode=PAPER|LIVE` refuse.
2. **Data objects** — OPTIDX premium lean hook, chain snapshot hook, news hold hook; fixtures when `DHAN_*` empty.
3. **Handoff schema** — structured persona messages → boss brief → **trader-only** paper fill ledger.
4. **Fake-breakout guards** — HYPOTHESIS flags from chain/premium divergence; never delete STRAT/MIX.
5. **KB** — write paper sessions to `trading_agents_india.sqlite`; retrieve via `agent_rag` FTS (rebuild after docs); never touch `transcripts.sqlite`.
6. **EOD** — freeze ledger → recon JSON → `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` → optional anonymized OpenAI review note.
7. **Backtest gate** — premium+chain replay / paper rollup; costs honest; **NO_PROMOTE** until 06 OOS+`NORMAL` + 09 five-pass.
8. **Dashboard** — `/desk` persona board + blotter; customer `/` stays ticket talk without indicator soup.
9. **WS depth** — only after decode VALIDATION; until then DI and poll REST/charts/chain.

**Accepted this council:** PAPER market-hours design + DI depth honesty + build-first order.  
**Rejected:** Live path; depth alpha; auto-fills; STRAT deletes; fake wr.  
**UNKNOWN / DI:** OPTIDX dual CE/PE history completeness; full/depth packet offsets; India sentiment SOURCE_FACT; EVENT_MEMORY still empty.

---

## Raw council JSON (no secrets)

```json
{
  "verdict": "APPROVE_PAPER_BUILD_FIRST",
  "council_bullets": [
    "PAPER only; trader manually confirms fills",
    "Use STRAT-001..014 only; no new STRAT ids",
    "Start 09:00 IST persona cycle; market-hours handoffs",
    "Alpha from premium+chain+price structure; news=hold/filter",
    "5m ST/MACD/RSI used only as confirm-or-kill",
    "RAG+SQLite for speed; never overwrite transcripts.sqlite",
    "DI-honest: Dhan WS supports ticker/quote/full; repo depth decode partial",
    "Live blocked until founder signoff + gates + RESEARCH_READY"
  ],
  "implement_now": [
    {"item": "market_hours_orchestrator", "why": "Run persona loop, club votes, handoffs from 09:00 IST", "layer": "SOURCE_FACT", "owner_team": "desk-intel", "priority": "P0"},
    {"item": "dhan_ingest_index_options", "why": "Capture OPTIDX premium candles, option chain, index spot/futures refs", "layer": "SOURCE_FACT", "owner_team": "trading_agents_india", "priority": "P0"},
    {"item": "paper_execution_ledger", "why": "Manual trader fills, state, PnL, slippage, audit trail", "layer": "VALIDATION", "owner_team": "desk-intel", "priority": "P0"},
    {"item": "fake_breakout_guard_pack", "why": "Wick/volume/OI/spot-premium divergence filters before paper entry", "layer": "HYPOTHESIS", "owner_team": "trading_agents_india", "priority": "P0"},
    {"item": "strategy_router_001_014", "why": "Map existing strategy clubs to CE/PE buy-first contexts only", "layer": "VALIDATION", "owner_team": "trading_agents_india", "priority": "P0"},
    {"item": "confirm_or_kill_5m_pack", "why": "Apply ST/MACD/RSI only as final confirm-or-kill on 5m", "layer": "VALIDATION", "owner_team": "desk-intel", "priority": "P1"},
    {"item": "rag_sqlite_research_cache", "why": "Fast retrieval of docs, prior sessions, chain patterns, postmortems", "layer": "SOURCE_FACT", "owner_team": "desk-intel", "priority": "P1"},
    {"item": "eod_recon_retune", "why": "Reconcile fills/data, score clubs, update RETUNE_GATE nightly", "layer": "VALIDATION", "owner_team": "desk-intel", "priority": "P1"},
    {"item": "backtest_harness_premium_chain", "why": "Replay premium+chain setups with honest constraints", "layer": "VALIDATION", "owner_team": "trading_agents_india", "priority": "P1"},
    {"item": "dashboard_surfaces", "why": "Show persona views, club verdicts, chain, ledger, recon", "layer": "SOURCE_FACT", "owner_team": "desk-intel", "priority": "P1"},
    {"item": "docs_wires_runbooks", "why": "Speed implementation and safe founder review", "layer": "SOURCE_FACT", "owner_team": "desk-intel", "priority": "P2"}
  ],
  "defer": [
    "LIVE order routing",
    "Any STRAT-015+ invention",
    "Depth/orderbook alpha claims",
    "Tick-accurate microstructure models",
    "Auto-fill simulation as truth",
    "Cross-broker adapters",
    "News sentiment alpha engine"
  ],
  "agent_roster": [
    {"persona_id": "P01", "display_name": "OpenDrive", "team_id": "desk-intel", "job": "Conductor; starts loops, gathers handoffs, forms final paper brief"},
    {"persona_id": "P02", "display_name": "QuantLens", "team_id": "trading_agents_india", "job": "Premium-chart structure, regime, expectancy math"},
    {"persona_id": "P03", "display_name": "ChainWatch", "team_id": "trading_agents_india", "job": "Option-chain/OI/PCR/strike migration analysis"},
    {"persona_id": "P04", "display_name": "PriceAction", "team_id": "trading_agents_india", "job": "Breakout/retest/trap read on premium and underlying context"},
    {"persona_id": "P05", "display_name": "RiskMarshal", "team_id": "desk-intel", "job": "Guardrails, max loss, cooldowns, no-trade calls"},
    {"persona_id": "P06", "display_name": "NewsHold", "team_id": "desk-intel", "job": "Event calendar/news as hold filter only"},
    {"persona_id": "P07", "display_name": "ExecutionScribe", "team_id": "desk-intel", "job": "Trader handoff, manual fill capture, audit log"},
    {"persona_id": "P08", "display_name": "ResearchJudge", "team_id": "trading_agents_india", "job": "Backtest/replay, gate metrics, RETUNE proposals"}
  ],
  "rag_sqlite_note": "OpenAI proposed data/rag/market_kb.sqlite — desk OVERRIDES to existing data/knowledge/agent_rag.sqlite + trading_agents_india.sqlite",
  "depth_interest_honest": {
    "claim": "Use only documented Dhan WS ticker/quote/full confidently; do not claim reliable depth/orderbook alpha now",
    "dhan_support": "WebSocket market feeds documented for ticker, quote, full packet classes",
    "repo_status": "community/repo depth decode appears partial/not fully trusted",
    "build_rule": "If depth fields arrive, store raw packets separately, mark experimental, exclude from alpha and backtest gates until validated"
  },
  "handoff_build_first": [
    "Create packages/trading_agents_india extension: market_hours/",
    "Add Dhan connectors for indexes, OPTIDX premiums, chain snapshots",
    "Define SQLite schemas for market, ledger, recon, RAG cache",
    "Build orchestrator schedule: 09:00 warmup, 09:15 open, intraday cadence, EOD",
    "Implement persona interfaces and club vote contract",
    "Port STRAT-001..014 router with CE/PE buy-first applicability map",
    "Add fake-breakout guard service using wick/volume/OI divergence rules",
    "Add 5m confirm-or-kill service for ST/MACD/RSI",
    "Build trader handoff UI/API and manual fill capture",
    "Build nightly recon + RETUNE_GATE job and founder packet export"
  ],
  "must_not": [
    "Place live orders now",
    "Invent STRAT-015+",
    "Use news as standalone alpha",
    "Use ST/MACD/RSI beyond 5m confirm-or-kill",
    "Claim depth support beyond validated docs",
    "Overwrite transcripts.sqlite",
    "Report fake win rates or cherry-picked backtests"
  ]
}
```

# ADOPT TradingAgents — India desk mapping (EXTERNAL reference)

**Date:** 2026-09-06  
**Layer:** `HYPOTHESIS` (orchestration design) + `SOURCE_FACT` (what the clone contains)  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Status:** `ADOPTED_SKELETON` / **UNVALIDATED** — paper signals only  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)  
**Local clone:** `research/TradingAgents/` (shallow; **do not** treat as our product; gitignored nested tree)

Education ≠ advice. No live Dhan orders. No `/alerts/orders`. No win rates. KEEP_ALL STRAT-001–014.

---

## 1. License (cite every time we borrow ideas)

| Field | Value |
|-------|-------|
| Upstream | https://github.com/TauricResearch/TradingAgents |
| Paper | https://arxiv.org/abs/2412.20138 |
| License | **Apache License 2.0** (`research/TradingAgents/LICENSE`) |
| Our use | Study + **adapt** role graph into `packages/trading_agents_india` |
| Not claimed | Their US-equity performance, ratings, or data vendors as our edge |

We do **not** vendor-copy LangGraph / yfinance / Alpha Vantage stacks into production. We **map roles** and keep DhanHQ + our coalition truth.

---

## 2. What TradingAgents is (SOURCE_FACT from clone v0.4.0)

Sequential LangGraph firm:

```text
Analysts (market / social-sentiment / news / fundamentals)
    → Bull ↔ Bear debate → Research Manager
    → Trader proposal
    → Aggressive ↔ Conservative ↔ Neutral risk debate
    → Portfolio Manager (final rating)
```

| Piece | Upstream behavior | India desk note |
|-------|-------------------|-----------------|
| Analyst team | LLM + tool nodes (yfinance, FRED, Reddit, StockTwits, AV) | Replace tools with desk-intel RSS + Dhan chain fixtures |
| Bull / Bear | Structured debate rounds | Keep as **peer challenge**; not catalog delete |
| Research Manager | 5-tier Buy…Sell plan | Map to **boss ticket lean** CE/PE/HOLD |
| Trader | Buy/Hold/Sell + optional prices | Map to **paper** BUY_CE / BUY_PE / HOLD only |
| Risk triad | Agg / Cons / Neutral | Map to **veto / hold** (NEWS_DAY, expiry, circuit) |
| Portfolio Manager | Final rating | Map to **00 default call** (`MIX-DEFAULT-BUY` book remains catalog) |
| Memory log | Markdown decision memory | New SQLite `trading_agents_india.sqlite` — **not** `transcripts.sqlite` |
| Checkpoint | LangGraph SQLite resume | Optional later; v0 uses simple session rows |

---

## 3. Compare to our coalition

| Our team | Job today | Closest TradingAgents role |
|----------|-----------|----------------------------|
| 00 Boss | Customer ticket call; KEEP_ALL | Research Manager + Portfolio Manager |
| 01 Research | Transcripts / binds | *No direct role* — our SOURCE_FACT spine (keep) |
| 02 Math | VALIDATION | Bear/Bull evidence quality (not delete) |
| 03 Market / CAS | Clocks, lots, CAS-* | News/macro + session clocks |
| 04 Quant | STRAT/MIX + staging | Market/technical **confirm-or-kill** (not entry soup) |
| 05 Desk-intel | News + 3m chain → MARKET_SIGNAL | News + Sentiment hooks |
| 06 Backtest / EVENT_MEMORY | Score vs analog | Memory of NEWS_DAY paths (empty today) |
| 09 Review | Five-pass; auditor | External red-team of *this* adoption |

**We already have** numbered teams + HANDOFF + layers. TradingAgents adds: **runtime debate loop**, structured agent outputs, and LLM-mediated synthesis. We keep human/doc coalition; agents **call into** desk packages.

---

## 4. TAKE (adopt / adapt)

| Take | Why | Where |
|------|-----|-------|
| Role graph: analysts → bull/bear → boss → trader → risk triad → final | Clear coordination | `packages/trading_agents_india` |
| Structured outputs (lean + reasons + veto) | Auditability | `schemas.py` |
| News + sentiment as **inputs**, not silent | Aligns EVENT_MEMORY | `agents/news.py`, `agents/sentiment.py` |
| Risk debate can **veto** trader | NEWS_DAY holds ticket | `agents/risk.py` + hooks |
| Separate memory store | Do not touch transcripts KB | `data/knowledge/trading_agents_india.sqlite` |
| OpenAI for deep/quick think when key present | User mandate | `llm.py` + honest fallback |
| Apache-2.0 citation | Compliance | This file + package README |

---

## 5. REJECT (do not import)

| Reject | Why |
|--------|-----|
| Live broker execution / order APIs | Hard stop; ExecutionClient refuses |
| US equity Buy/Sell as customer ticket | We sell **index options CE/PE buy-first** |
| Fundamentals analyst as NIFTY alpha | Index options ≠ company filings |
| StockTwits / Reddit as SOURCE_FACT | Noise; India index DI; never fake sentiment |
| yfinance / Alpha Vantage as Dhan truth | DhanHQ-only for tape |
| MACD/RSI as customer entry | Confirm-or-kill on `/desk` only ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)) |
| Deleting STRAT-001–014 / inventing STRAT-015+ | KEEP_ALL; new ideas = MIX-* |
| Claiming win rates / RESEARCH_READY | Gate not earned |
| Overwriting `transcripts.sqlite` | New KB only |
| Mass LangGraph rewrite of monorepo | Additive package only |

---

## 6. Role → team / package map (wiring)

```text
TradingAgents          →  our wire
─────────────────────     ──────────────────────────────────────────
News Analyst           →  05 news_ingest + tai.agents.news
Sentiment Analyst      →  tai.agents.sentiment (stub / DI until real feed)
Market / Technical     →  04 staging + desk chain lean (fixture OK)
Fundamentals           →  SKIP / CAS note only (03) — not equity filings
Bull Researcher        →  tai.agents.bull (CE case)
Bear Researcher        →  tai.agents.bear (PE / hold case)
Research Manager       →  00 boss synthesize (tai.agents.boss)
Trader                 →  paper lean BUY_CE|BUY_PE|HOLD (no orders)
Risk Agg/Cons/Neutral  →  tai.agents.risk → vetoes[] / NEWS_DAY HOLD
Portfolio Manager      →  00 final paper ticket (still MIX catalog intact)
Memory                 →  data/knowledge/trading_agents_india.sqlite
```

Default book cited in reasons: **`MIX-DEFAULT-BUY`**. Other MIX/STRAT stay `BACKTEST_BOOK`. News never deletes catalog rows ([`CUSTOMER_TALK.md`](../../05_analysis/docs/CUSTOMER_TALK.md), [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md)).

---

## 7. India paper signal contract (v0)

Each underlying session emits:

| Field | Allowed |
|-------|---------|
| `underlying` | NIFTY \| BANKNIFTY \| SENSEX |
| `lean` | BUY_CE \| BUY_PE \| HOLD |
| `stage` | WATCH \| EARLY \| VETOED (CONFIRMED+ only if later wired; v0 max EARLY) |
| `reasons[]` | short strings, cited layers |
| `risk_veto` | bool + `vetoes[]` |
| `session_kind` | NORMAL \| NEWS_DAY \| EXPIRY |
| `layer` | HYPOTHESIS |
| `execution` | always `refused` |
| `data_gaps[]` | honest `DATA_INSUFFICIENT` / `UNKNOWN` |

On `NEWS_DAY` / `MACRO_EVENT` / risk veto → **HOLD** (ticket hold). Catalog unchanged.

---

## 8. End-state vision (honest path)

1. **Now:** local dry/paper loop in `packages/trading_agents_india` (fixtures + optional OpenAI).  
2. **Next:** hook live desk-intel morning JSON when `DHAN_*` present (data only).  
3. **Later:** optional LangGraph port *inside* the package; never replace 01–09 docs.  
4. **Not yet:** live orders, promote gate, filled win rates, RESEARCH_READY.

---

## 9. HANDOFF

**Accepted:** Role graph + structured paper leans + separate KB + news-as-hold.  
**Rejected:** Broker exec, US fundamentals alpha, social as fact, STRAT deletes, LangGraph monorepo rewrite.  
**UNKNOWN / DATA_INSUFFICIENT:** OpenAI key not visible in workspace `.env` at adopt time (fallback path required); India sentiment feed; EVENT_MEMORY analogs empty; live chain without tokens.

**Artifacts:**
- This file
- `packages/trading_agents_india/`
- `teams/09_review/docs/TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md`
- `data/knowledge/trading_agents_india.sqlite` (created on first run)

**Run:** `python -m trading_agents_india session --dry-run` (from repo root with package installed / `PYTHONPATH`).

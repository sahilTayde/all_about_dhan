# ADOPT TradingAgents — India desk mapping (EXTERNAL reference)

**Date:** 2026-09-06  
**Layer:** `HYPOTHESIS` (orchestration design) + `SOURCE_FACT` (what the clone contains)  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Status:** `ADOPTED_SKELETON` / **DEEPENED_PAPER** / **MARKET_HOURS_LOOP** / **UNVALIDATED** — paper signals only  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)  
**Local clone:** `research/TradingAgents/` (shallow; **do not** treat as our product; gitignored nested tree)  
**Design council (2026-09-06):** [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](OPENAI_DESIGN_COUNCIL_2026-09-06.md) — OpenAI `gpt-5.4` + founder desk; verdict `APPROVE_WITH_GUARDRAILS`  
**Market-hours council (2026-09-06):** [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md) — `APPROVE_WITH_GUARDRAILS` (PAPER build-first; LIVE refuse)  
**Market-hours plan:** [`PLAN_MARKET_HOURS_PAPER_AGENTS.md`](PLAN_MARKET_HOURS_PAPER_AGENTS.md)  
**MIX paper-watch:** `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`, `MIX-TA-MARKET-HOURS` ([`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) §18) — not default, not promote

Education ≠ advice. No live Dhan orders. No `/alerts/orders`. No win rates. KEEP_ALL STRAT-001–014.

**Mode:** `PAPER` (default) | `LIVE` (stub: DhanHQ-only path; **always refuses** orders until founder allow + live gate + `RESEARCH_READY` — currently all refuse). See `packages/trading_agents_india/mode.py`.

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
| Mode | US live/paper brokers | **`PAPER` default**; **`LIVE` → refuse** (DhanHQ stub only) |

---

## 2b. Persona display names (deepen 2026-09-06)

Registry: `packages/trading_agents_india/personas.py` — TradingAgents name → India role → our team.

| TradingAgents | Pipeline role | India role | Team |
|---------------|---------------|------------|------|
| News Analyst | `news_analyst` | India Event / News Filter | 05 |
| Sentiment Analyst | `sentiment_analyst` | India Sentiment (DI) | 05 |
| Market Analyst | `technical_analyst` | Index Regime / Chain Lean | 04 |
| Option Chain Watcher | `chain_watcher` | 3m Chain / Wall Hypothesis | 05/04 |
| Fundamentals Analyst | skipped | Macro/CAS note only | 03 |
| Bull / Bear Researcher | `bull_researcher` / `bear_researcher` | CE / PE-Hold challengers | 02/04 |
| Research Manager + Portfolio Manager | `boss_research_manager` | Boss desk + final paper call | 00 |
| Trader | `trader` | Paper Execution Coordinator | 07/08 |
| Risk triad / Risk Manager | `risk_committee` | Premium risk & loss gate | 06 |

CLI: `python -m trading_agents_india personas`

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

1. **Now:** local dry/paper loop in `packages/trading_agents_india` (fixtures + optional OpenAI + `mode=PAPER|LIVE` refuse).  
2. **Next:** hook live desk-intel morning JSON when `DHAN_*` present (data only); Moneycontrol RSS via desk_intel (`--gather-news`).  
3. **Later:** optional LangGraph port *inside* the package; never replace 01–09 docs. Founder allow + live gate still required for any LIVE attempt.  
4. **Not yet:** live orders, promote gate, filled win rates, RESEARCH_READY.

### NEWS wiring (honest)

| Source | Status |
|--------|--------|
| DhanHQ news API | **DATA_INSUFFICIENT** — not exposed in `dhan_client` skeleton (quotes/chain/charts only) |
| Moneycontrol | Prefer **RSS** via `desk_intel` + `workspace.yaml` (`VERIFY IF STABLE`); not HTML scrape |
| CNBC / StockTwits / Reddit | **REJECT** as India SOURCE_FACT |

### PAPER vs LIVE

```text
PAPER (default) → paper ledger in trading_agents_india.sqlite; execution refused
LIVE            → evaluate founder allow + TRADING_AGENTS_LIVE_GATE + RESEARCH_READY
                  → always refuse in this package; may call dhan_client.ExecutionClient
                    which also refuses; broker path name = dhanhq only
```

---

## 9. HANDOFF

**Accepted:** Role graph + structured paper leans + separate KB + news-as-hold + `mode=PAPER|LIVE` refuse + persona aliases + `MIX-TA-*` PAPER_WATCH rows + OpenAI design council 2026-09-06 + **market-hours paper council** (`APPROVE_WITH_GUARDRAILS`).  
**Rejected:** Broker exec, US fundamentals alpha, social as fact, STRAT deletes, LangGraph monorepo rewrite, inventing Dhan news headlines, depth alpha before decode VALIDATION.  
**UNKNOWN / DATA_INSUFFICIENT:** Dhan news API; Moneycontrol RSS stability; India sentiment feed; EVENT_MEMORY analogs empty; live chain without tokens; LIVE founder flags (default off); WS full/depth offsets.

**Artifacts:**
- This file
- [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](OPENAI_DESIGN_COUNCIL_2026-09-06.md)
- [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md)
- [`PLAN_MARKET_HOURS_PAPER_AGENTS.md`](PLAN_MARKET_HOURS_PAPER_AGENTS.md)
- `packages/trading_agents_india/` (`mode.py`, `personas.py`, `hooks/news.py`, market-hours skeleton)
- `teams/09_review/docs/TRADINGAGENTS_ADOPTION_REVIEW_2026-09-06.md`
- `teams/09_review/docs/TRADINGAGENTS_DEEPEN_NOTES_2026-09-06.md`
- `data/knowledge/trading_agents_india.sqlite` (created on first run)
- MIX §18: `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`

**Run:**
```bash
python -m trading_agents_india session --dry-run
python -m trading_agents_india session --mode PAPER --gather-news
python -m trading_agents_india session --mode LIVE   # documents refuse
python -m trading_agents_india market-hours --simulate --max-ticks 2
python -m trading_agents_india market-hours --tick-seconds 45 --max-ticks 4
python -m trading_agents_india clock
python -m trading_agents_india session --dry-run --use-llm
python -m trading_agents_india personas
```

### Market-hours loop (2026-09-06 deepen)

- Session runner: IST shell 09:00–15:30; active paper 09:30–15:00; dead-bands → HOLD (`MIX-CLOCK-CAS`).
- Default tick **45s** (30–60 band); path toward **15s** documented in plan — not default.
- Dual ledger: `trading_agents_india.sqlite` + `data/recon/paper_watch/`.
- Handoffs: structured messages; trader paper CE/PE only; execution refused.
- Chain watcher persona + OPTIDX premium lean (else INDEX proxy `HYPOTHESIS`).
- Reasons cite `MIX-DEFAULT-BUY` + `MIX-TA-*` + optional PhD snippets (inputs, not deletes).

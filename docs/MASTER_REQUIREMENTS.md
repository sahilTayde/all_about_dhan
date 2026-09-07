# MASTER_REQUIREMENTS — morning check sheet

**Date frozen:** 2026-09-01 (session end). Catalog `retrieved_at`: 2026-08-31T03:15:28Z (not re-fetched).  
**Audience:** user + frontier-model reviewer. **Do not restart `npm` until asked.**  
**How to use:** this file is the score. Evidence lives in the linked paths. If a ticket says `DONE` but the artifact is a stub, the **row status here wins**.

**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Do not place live orders. Do not invent win rates. Proxy backtest ratings are **UNVALIDATED**.

Review brief: [`teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](../teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md).  
SDLC: [`docs/SDLC.md`](SDLC.md). Orchestrator snapshot: [`teams/00_orchestrator/docs/STATUS.md`](../teams/00_orchestrator/docs/STATUS.md).

---

## Status legend

| Label | Meaning |
|-------|---------|
| **DONE** | Requirement met for the *stated* scope (often docs + dry-run). Remaining work is explicitly out of that ticket. |
| **PARTIAL** | Real artifacts exist, but they are mock, stub, dry-run, incomplete extraction, or `UNVALIDATED`. |
| **TODO** | Required; not started, or a checkbox left empty on purpose. |
| **BLOCKED** | Cannot proceed without a user action (token, circular PDF, live tape). |

**Honesty rules for this sheet**

- A mock dashboard is **PARTIAL**, not a paper-trading gate.
- A nightly JSON with `BACKTEST_REQUIRED` is **not** a backtest.
- `STRAT-001`–`014` are **DRAFT / UNVALIDATED**. Proxy OOS wr: [`BACKTEST_BOOKS_2026-09-03.md`](../teams/06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md). Option-premium OOS wr: [`BACKTEST_OPTION_2026-09-03.md`](../teams/06_backtesting/docs/BACKTEST_OPTION_2026-09-03.md) — **all FAIL**, **not a promote**.
- `packages/indicators` is **empty by design**. Do not treat that as a missing Supertrend REST.
- Empty `DHAN_*` → fixtures. Live Dhan **data** was probed 2026-09-03; **orders still refused**.

---

## Scorecard

| # | Requirement | Status | Honest one-liner |
|---|-------------|--------|------------------|
| 1 | Company repo, `@DhanHQ` research, transcripts + English, `workspace.yaml` | **PARTIAL** | Tree + collector + 45/45 English **done**; OPTIONS_INDEX English SOURCE_FACT **done** 2026-09-03; EQUITY English **second pass** 2026-09-03 (scanners/BTST/swing on disk); catalog `STOCK_ONLY` **9** still no EN; `.git` still absent. |
| 2 | Dhan-only broker, no live orders | **DONE** | Policy + `ExecutionClient` always refuses. Live *data* still unvalidated. |
| 3 | Official Dhan indicators (no Supertrend series API) | **PARTIAL** | Docs catalog **done**. Transcript KB stub. TA package empty (correct). |
| 4 | Desk intel: news, chain **3m** + last snapshot, PRE vs POST nightly | **PARTIAL** | Live morning 2026-09-03: chain+news ran; all three underlyings **HOLD** (`NO_TRADE`/`VETOED`). Dry-run fixtures still exist. GIFT/SGX **VERIFY**. |
| 5 | Recon + **backtest-before-retune** (no blind news-day retune) | **PARTIAL** | Honest leftover 2026-09-06: hypothesis costs + expiry strip. CLUB-GR after-cost **FAIL**. SCORE_SAMPLE empty. Nothing promotes. Statutory UNKNOWN. |
| 6 | Staged signals WATCH→EARLY→CONFIRMED→IN-PROGRESS→outcomes; customer vs engine; no indicator soup on client UI | **PARTIAL** | Paper `/ws/signals` from Dhan feed (BUY CALL/PUT/HOLD). Mock UI still default without API. **UNVALIDATED**. 09 `NOTES_ONLY`. Multi-agent paper: `packages/trading_agents_india` — dry CE/PE/HOLD + risk veto + **market-hours poll** (`market-hours --simulate`) + chain watcher; ledger `paper_watch/` + sqlite; not a promote. |
| 7 | Dashboard: ticket SL/target, (i) legend, book, sentiment windows, `/desk` internal | **PARTIAL** | Customer `/` MOCK: suggested ticket + index chart + honesty labels + confidence (i) + paper book ([`ASTRA_DASHBOARD_REVIEW.md`](../teams/07_coding/docs/ASTRA_DASHBOARD_REVIEW.md)). Sentiment/CAS below ticket. Not live fills. Confidence ≠ win rate. |
| 8 | CAS analyst (NIFTY / BANKNIFTY / SENSEX) | **PARTIAL** | Folder + research + `cas_calls[]` + CasPanel **exist**. **CAS-001–005** defined (`CAS_STRATEGIES.md`) `UNVALIDATED`. No Dhan-video CAS recipe (`DATA_INSUFFICIENT`). No win rates. |
| 9 | Paper/shadow vs user lots; 30% capital quality bar | **PARTIAL** | Spec + ledger stubs. No real P/L. Quality bar is a **product penalty**, not a measured metric. |
| 10 | Token for live Dhan validation | **PARTIAL** | Data plan **Active** (profile 2026-09-03). Live GET `/profile` + POST quote/chain/charts **worked**. **Orders still refused.** Do not paste tokens in chat. |
| 11 | Standing **Docs Auditor** (after requirement change + nightly) | **DONE** (checker) | `python -m docs_auditor`. Real fail paths (stub sheet, `1m` chain, missing nightly hook). Latest: [`AUDIT_LATEST.md`](../teams/00_orchestrator/docs/AUDIT_LATEST.md). |

---

## 1. Company repo, YouTube research, transcripts + English, workspace.yaml — **PARTIAL**

### Company repo

| Item | Status | Evidence |
|------|--------|----------|
| Modular monorepo (`docs/`, `teams/00–09`, `apps/`, `packages/`, `data/`, `secrets/`) | **DONE** | Root [`AGENT.md`](../AGENT.md), [`PLAN.md`](../PLAN.md) |
| `.gitignore` + `.env.example` (names only) | **DONE** | [`.env.example`](../.env.example) |
| Cursor routing | **DONE** | `.cursor/rules/` |
| Git repo / remote | **TODO** | Prior STATUS: `.git` still absent. Do not invent a remote. |
| Product brand | **TODO** | Working name **all_about_dhan** only. |

### YouTube research (`@DhanHQ`)

| Item | Status | Evidence |
|------|--------|----------|
| Enabled source = official `@DhanHQ` `TIER_1` | **DONE** | [`config/workspace.yaml`](../config/workspace.yaml) `sources.youtube[]` |
| Catalog | **DONE** | 2,034 videos. `data/youtube/video_catalog.{csv,json}`. Run report [`teams/01_research/youtube/docs/RUN_REPORT.md`](../teams/01_research/youtube/docs/RUN_REPORT.md) |
| Collector | **DONE** | `teams/01_research/youtube/src/` |
| External channels (Zerodha / Market Analyst Academy / Master Bull) | **DONE** (disabled) | yaml `enabled: false`, `EXTERNAL_RESEARCH`. Do not scrape. |
| Codex Stage 1 plan (verbatim) | **DONE** | [`teams/01_research/youtube/PLAN.md`](../teams/01_research/youtube/PLAN.md) |
| Re-fetch catalog | **TODO** | Not required overnight. `retrieved_at` is 2026-08-31. |

Ticket: [`TASK_YOUTUBE_TRANSCRIPT_RETRY.md`](../teams/00_orchestrator/docs/TASK_YOUTUBE_TRANSCRIPT_RETRY.md) **DONE**.

### Transcripts + English

| Metric (disk) | Count | Status |
|---------------|------:|--------|
| `TRANSCRIPT_VERIFIED` | 45 | **DONE** (retry 2026-09-01; 12 newly verified) |
| `ENGLISH_VERIFIED` (`tlang=en` + native) | 45 | **DONE**. **No LLM translation.** Hindi sources intact. |
| `ENGLISH_PENDING` | 0 | **DONE** |
| Related 429 / IP-block remaining | 0 | **DONE** |
| Parked (unrelated / captions disabled) | 4 | **DONE** (stay parked) |
| Full `SOURCE_FACT` packets (index-options / selling / OF) | 10 | **PARTIAL** (EN packet 2026-09-03; Hindi 6 kept) |
| Thin / transferable / promo touched | 8 | **PARTIAL** |
| OPTIONS_INDEX English packet | 1 | **DONE** — [`OPTIONS_INDEX_PACKET.md`](../teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) |
| STRAT-001–014 English bind (spoken vs spec) | 1 | **DONE** 2026-09-03 — [`TRANSCRIPT_STRATEGY_BIND.md`](../teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). Prior mix copied STRAT timestamps; this file re-read `normalized_en/`. 04 applied to `ENGINE_MIX` + STRAT files. |
| EQUITY English per-video (scanners / BTST / swing) | 6 | **DONE** 2026-09-03 — `_byuht` / `4TT8` / `pBQ` / `G31` / `dEv` / `EVk` (product). Catalog `STOCK_ONLY` **9** still no EN. |
| Newly verified IDs still without SOURCE_FACT | 0 | **DONE** (the 12 from retry all have OPTIONS, TA, or EQUITY notes) |

Handoffs: [`teams/01_research/docs/handoffs/`](../teams/01_research/docs/handoffs/) (`HAUSZx-hYdY` + `.en`, `2RnBT9DDDNI`, `6el9Jqnrdz8`, `gA5FtEnSABM`, `YUXJv_xBStw`, `pvmvkiS1cx4`, `_exmJYgFwFA`, `DzT_681GThA`, `8h9SYvQWKMA` + [`OPTIONS_INDEX_PACKET.md`](../teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md) + [`TRANSCRIPT_STRATEGY_BIND.md`](../teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) + [`EQUITY_ETF_PACKET.md`](../teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md) + `_byuht38r5s` / `4TT8IV5S1_A` / `pBQ1oVDVe3M` / `G31RFueZLvk` / `dEvF8biE02M` / `EVk_Wa_1cm0` + [`TRANSFERABLE_AND_SKIPPED.md`](../teams/01_research/docs/handoffs/TRANSFERABLE_AND_SKIPPED.md)).  
English files: `data/transcripts/normalized_en/`. Parked: `data/transcripts/parked_tomorrow/`. Coalition: [`TASK_TRANSCRIPT_COALITION.md`](../teams/00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md).

**TODO (01_research):** catalog `STOCK_ONLY` **9** + stock-options series + ETF titles still have **no** English file (`TRANSCRIPT_PENDING`). `2YBmiyVmNNw` still `DATA_INSUFFICIENT`. OPTIONS_INDEX + remaining verified-EN equity IDs **done**. Prefer `normalized_en/`. Do not overwrite Hindi `SOURCE_FACT`.

### `workspace.yaml` sources

Ticket: [`TASK_WORKSPACE_CONFIG.md`](../teams/00_orchestrator/docs/TASK_WORKSPACE_CONFIG.md) **DONE** (topic strategy write-up still STUB).

| Block | Status | Notes |
|-------|--------|-------|
| `implementation.broker: dhan` / `indicators: dhan_only` | **DONE** | Production stays Dhan-only unless yaml is changed. |
| `markets[]` NIFTY / BANKNIFTY / SENSEX | **DONE** | Scrips 13 / 25 / 51 = **VERIFY FROM instrument master**, not eternal. |
| `secrets_from_env` names only | **DONE** | Values in `.env`, never this file. |
| `sources.youtube[]` | **DONE** | Switch channel by URL + `enabled`. |
| `sources.books[]` (Murphy, Natenberg) | **DONE** | `use: VALIDATION`, not proof of edge. |
| `sources.news[]` RSS/official | **DONE** (schema) | Moneycontrol historical RSS: **VERIFY IF STABLE**. |
| `sources.pre_open` / `gift_nifty` / `global_tape` / `cas` | **PARTIAL** | URLs documented; GIFT/SGX/pre-open = **VERIFY**, not Dhan REST. |
| Topic cluster pipeline | **PARTIAL** | [`TOPIC_STRATEGY_PIPELINE.md`](../teams/01_research/docs/TOPIC_STRATEGY_PIPELINE.md); [`teams/04_quant/docs/topics/`](../teams/04_quant/docs/topics/) stubs. |

Loader: `config/load.py`. Overlay `config/workspace.local.yaml` is gitignored.

---

## 2. Dhan-only broker, no live orders — **DONE** (policy + SafeMode)

| Rule | Status | Evidence |
|------|--------|----------|
| Broker is Dhan / DhanHQ only | **DONE** | yaml `implementation.broker: dhan`. [`docs/COMPLIANCE.md`](COMPLIANCE.md), [`docs/SECURITY.md`](SECURITY.md) |
| No other broker credentials in git | **DONE** | `.env.example` names only |
| No live orders in Phase 0–6 | **DONE** | [`packages/dhan-client/src/dhan_client/execution.py`](../packages/dhan-client/src/dhan_client/execution.py) — `place_order` / modify / cancel / super / forever all raise `SafeModeError` |
| Conditional Trigger `/alerts/orders` not wired | **DONE** | No matches in `packages/dhan-client`. Docs-only. **Do not live-trade it.** |
| Browser never calls Dhan | **DONE** | [`apps/web/README.md`](../apps/web/README.md) |
| Live quote / chain / feed | **TODO** | See §10. Skeleton client exists; token check not run this session. |

Generic client + FastAPI dry-run: `packages/dhan-client`, `apps/api` (`GET /health`, mock `GET /paper/signal`). Orders refused.

---

## 3. Official Dhan indicators (no Supertrend series API) — **PARTIAL**

Ticket: [`TASK_DHAN_INDICATORS.md`](../teams/00_orchestrator/docs/TASK_DHAN_INDICATORS.md) — **DONE** for official-API catalog; transcript KB **not** complete.

| Fact | Layer | Status |
|------|-------|--------|
| **No** Supertrend / RSI / MACD / EMA9 **series** REST | `SOURCE_FACT` (docs 2026-09-01) | **DONE** (documented) |
| Conditional Trigger names conditions; **does not return series**; Equities + Indices only | same | **DONE** |
| Annexure EMA set is **5, 10, 20, 50, 100, 200**. **`EMA_9` is not in the annexure** | same | **DONE** |
| Charts REST = OHLC + volume (+ optional OI). Intervals **1, 5, 15, 25, 60** min | same | **DONE** |
| Quote `average_price` described as day VWAP | same | **DONE** |
| ScanX / chart Supertrend = product UI, not HQ series | same | **DONE** |
| `packages/indicators` implementation | — | **TODO** (empty by design until review) |
| Transcript columns on KB | — | **PARTIAL** / STUB |

Clubbed defs: [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md).  
VALIDATION map: [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).  
KB: [`research/indicator_knowledge_base.md`](../research/indicator_knowledge_base.md).  
Persona seed (do not invent HQ Supertrend): [`teams/00_orchestrator/docs/PERSONA.md`](../teams/00_orchestrator/docs/PERSONA.md).

Later engine may **compute** Supertrend/RSI/MACD/EMA9 from OHLC. That is **not** an API. Do not send `EMA_9` to `/alerts/orders`.

---

## 4. Desk intel: news, chain **3m** + last snapshot, PRE vs POST nightly — **PARTIAL**

Tickets:

- [`TASK_DESK_INTELLIGENCE.md`](../teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md) **DONE** (skeleton; dry-run; no orders)
- [`TASK_CUSTOMER_DESK.md`](../teams/00_orchestrator/docs/TASK_CUSTOMER_DESK.md) **DONE** (docs + dry-run schema; no live scrape)
- [`TASK_PRE_POST_MARKET_JOBS.md`](../teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md) **DONE** (skeleton; dry-run)

Spec: [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](../teams/05_analysis/docs/DESK_INTELLIGENCE.md).  
Code: [`packages/desk-intel/`](../packages/desk-intel/).  
Chain metrics: [`teams/03_phd_market/docs/CHAIN_METRICS.md`](../teams/03_phd_market/docs/CHAIN_METRICS.md).  
Operator checklist: [`PERSONA_DESK.md`](../teams/00_orchestrator/docs/PERSONA_DESK.md).

| Piece | Status | Notes |
|-------|--------|-------|
| News RSS / official (RBI, Fed, BLS, EIA, BBC; Moneycontrol historical) | **PARTIAL** | Ingest exists. Moneycontrol **VERIFY IF STABLE**. Surprise prints `UNKNOWN` until a calendar adapter exists. |
| Full option chain poll default **3m** | **DONE** (schema) | yaml `desk_intel.poll.chain_interval: 3m`. HQ limit 1 unique / 3 s. 3m is inside budget. |
| Remember last snapshot (OI / PCR / ATM CE–PE Δ) | **DONE** (schema + dry-run) | `remember_last_snapshot: true`. Timestamped file + `last.json`. |
| Optional 1m ATM±N strike-buildup | **TODO** (off) | `strike_buildup_enabled: false`. Not a full-chain 1m poll. |
| PRE_MARKET before 09:15 IST | **PARTIAL** | CLI `python -m desk_intel morning\|pre-market --offline`. GIFT Nifty / SGX / NSE pre-open = **VERIFY**, not Dhan endpoints. Fixtures only. |
| POST_MARKET after close | **PARTIAL** | yaml `after_ist: "15:40"`. F&O close **15:30 vs 15:40** is **UNKNOWN** / **VERIFY FROM circular**. |
| `MARKET_SIGNAL` fusion | **PARTIAL** | Bias / regime. Adapter JSON shape exists. `apps/api` still mock — **not wired**. |
| Sentiment windows 10m / 15m / 30m / 1h | **PARTIAL** | Schema slots. **Mock bind.** Not measured rolling windows. |
| Live `POST /optionchain` | **TODO** | Empty `DHAN_*` → fixtures. See §10. |

Dry-run (do **not** start npm for this):

```bash
python -m desk_intel status
python -m desk_intel morning --offline
python -m desk_intel poll-chain --interval 3m --offline
python -m desk_intel nightly --offline
```

---

## 5. Recon + backtest-before-retune — **PARTIAL**

**Engine exists** (`packages/backtest`). Ticket [`TASK_ALGO_ENGINE.md`](../teams/00_orchestrator/docs/TASK_ALGO_ENGINE.md). INDEX proxy: [`BACKTEST_BOOKS_2026-09-03.md`](../teams/06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md). Option premium: [`BACKTEST_OPTION_2026-09-03.md`](../teams/06_backtesting/docs/BACKTEST_OPTION_2026-09-03.md) — 5y rollingoption, **all 24 MIX cells FAIL**, **keep current**. 09 [`BACKTEST_OPTION_REVIEW_2026-09-03.md`](../teams/09_review/docs/BACKTEST_OPTION_REVIEW_2026-09-03.md) **NOTES_ONLY**.

Spec: [`teams/06_backtesting/docs/RETUNE_GATE.md`](../teams/06_backtesting/docs/RETUNE_GATE.md).  
Nightly stub still emits `BACKTEST_REQUIRED` (does **not** auto-apply this run).

| Rule | Status | What is true on disk |
|------|--------|----------------------|
| Tag session `NEWS_DAY` / `EXPIRY` / `NORMAL` | **PARTIAL** | Nightly stamps flags. Historical news calendar **empty**. EXPIRY ISO-week proxy is HYPOTHESIS. SCORE_SAMPLE empty ([`BACKTEST_HONEST_2026-09-06.md`](../teams/06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)). |
| Candidate change **must** backtest OOS + **NORMAL** | **PARTIAL** | Engine ran; SCORE_SAMPLE empty (news `DATA_INSUFFICIENT`). Nothing promotes. |
| Promote only if more profitable on robust metrics | **DONE** (gate) | 2026-09-03 books all **FAIL** on OOS win_rate. No promote. |
| Default: **keep current strategy** | **DONE** | `keep_current_strategy: true` |
| Nightly **never** writes production params | **DONE** (stub) | `production_params_written: false` |
| Nightly emits `RETUNE_PROPOSAL` `status: BACKTEST_REQUIRED` | **DONE** (stub) | Does **not** emit `PROMOTED` |
| Backtest engine (Phase 3) | **PARTIAL** | 5y INDEX 1m + current FUTIDX **plus** 5y rollingoption OPTIDX. Hypothesis 1% RT overlay 2026-09-06. Statutory still UNKNOWN. All promote paths FAIL / DATA_INSUFFICIENT. Q8/Q12 not waived. |
| Invented win rates / PF / DD | **forbidden** | Proxy rates in 06 markdown are **measured**, labeled FAIL/UNVALIDATED, not customer P/L. |

Older [`NIGHTLY_2026-09-02.md`](../teams/02_phd_math/docs/handoffs/NIGHTLY_2026-09-02.md) **predates** the retune stub (format note in file). Re-run `python -m desk_intel nightly --offline` for current JSON keys. Do not treat that file’s zero P/L as a track record.

---

## 6. Staged signals — **PARTIAL**

Ticket: [`TASK_STAGED_SIGNALS.md`](../teams/00_orchestrator/docs/TASK_STAGED_SIGNALS.md) **`IN_PROGRESS`**. Paper engine: [`TASK_ALGO_ENGINE.md`](../teams/00_orchestrator/docs/TASK_ALGO_ENGINE.md). Live `DHAN_*` **data** may feed `/ws/signals?live=1`. **Orders refused.**

Spec: [`teams/04_quant/docs/SIGNAL_STAGING.md`](../teams/04_quant/docs/SIGNAL_STAGING.md) `HYPOTHESIS` / `UNVALIDATED`.  
Postmortem: [`teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md`](../teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md).  
Honesty: [`MASTER_STRATEGY_PLAN.md`](../teams/04_quant/docs/MASTER_STRATEGY_PLAN.md) **CUSTOMER vs ENGINE**.

| State / outcome | Role | Status |
|-----------------|------|--------|
| WATCH → EARLY → CONFIRMED → **IN-PROGRESS** → terminal | Spec + paper WS | **PARTIAL**. `/ws/signals` paper copy. Not a fill. |
| EARLY ~1 min lead | Product **target**, not a measured SLA | **PARTIAL** (specified). Do not implement omniscience. |
| 5m Supertrend / MACD = **confirm or kill**, not entry | Spec + 003 paper | **PARTIAL** (003 all-three is the paper lean; lagging stack still confirm-or-kill in staging spec) |
| Outcomes ACHIEVED / STOPPED / INVALIDATED / EXPIRED / LOST / COMPLETED / SHADOW_CLOSED | Spec + stub | **PARTIAL** (`outcomes.py`, mock UI). |
| Customer UI: staged lean + honesty copy; **no indicator soup** | Mock + optional live paper | **PARTIAL** — BUY CALL/PUT/HOLD copy; internals on `/desk` |
| Engine mix of 14 STRATs | Paper subset | **PARTIAL**. 003/001/006 coded. Rest KEEP_ALL NOT_CODED. **FAIL** proxy. |
| Wire stages to `MARKET_SIGNAL` adapter | — | **TODO** (news hold still 05) |
| OHLC 1m/5m TA in `packages/indicators` | — | **TODO** (empty by design). Compute lives in `packages/backtest`. |

**CUSTOMER vs ENGINE (must hold in review)**

| Surface | Sees | Must not see |
|---------|------|----------------|
| Customer UI | WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED + readable reasons | RSI+MACD+Supertrend+EMA stack as the product; fake win rates |
| Engine (later) | May mix regime-specific DRAFT IDs | A claim that the mix is validated or live-ready |

---

## 7. Dashboard — **PARTIAL** (mock)

README: [`apps/web/README.md`](../apps/web/README.md). Stack: Vite + React. Default mock: [`apps/web/public/mock/signal.json`](../apps/web/public/mock/signal.json).

| Surface | Status | Notes |
|---------|--------|-------|
| Customer desk `http://localhost:5173` | **PARTIAL** | **Do not restart npm until asked.** Assume a prior `npm run dev` if the port is up. |
| Ticket strike / entry / **SL** / **target** | **DONE** (mock fields) | Always shown in mock. Not live levels. |
| Status WATCH / EARLY / CONFIRMED / IN-PROGRESS + outcomes | **DONE** (mock mapping) | IN-PROGRESS = issued ticket, **not a fill**. |
| **(i)** legend | **DONE** | `LegendDialog.jsx`. Legend not dumped on canvas. |
| Today’s book | **PARTIAL** | Labeled **MOCK**. Customer-taken vs platform shadow counts are placeholders. |
| Sentiment windows 1h / 30m / 15m / 10m | **PARTIAL** | Mock fusion. Not indicator names. |
| Close auction / cash bias | **PARTIAL** | `CasPanel.jsx` on customer `App.jsx`. See §8. |
| Internal `/desk` | **DONE** (route) | Research view: honesty stages, indicator lights, factor checklist. **Not** the customer product. |
| Live API bind `VITE_API_URL` | **TODO** | Empty → mock JSON. FastAPI still mock. |
| Charts / auth / multi-signal | **TODO** | Listed as extension points in the README. |

Mock tabs (do not treat as production marks): NIFTY **IN-PROGRESS**; BANKNIFTY **ACHIEVED**; SENSEX **INVALIDATED**.

---

## 8. CAS analyst (NIFTY / BANKNIFTY / SENSEX) — **PARTIAL**

**Just finished this session (research + skeleton).** Ticket [`TASK_CAS_ANALYST.md`](../teams/00_orchestrator/docs/TASK_CAS_ANALYST.md) **`IN_PROGRESS`**. Files **exist** — this row is **not** TODO.

Home: [`teams/03_phd_market/cas/`](../teams/03_phd_market/cas/).

| Fact | Status |
|------|--------|
| Official CAS = NSE/BSE **Closing Auction Session** | **DONE** (research) — [`cas/RESEARCH.md`](../teams/03_phd_market/cas/RESEARCH.md) |
| Phase 1 = F&O **cash names**; session **15:15–15:35 IST**; live **3 Aug 2026** | **DONE** (cited). Equilibrium close; indicative index during order entry. |
| **Not** pre-open, **not** PCA (periodic call auction), **not** “cash vs F&O” slang | **DONE** (tagged separately in yaml `sources.cas` / `sources.pre_open`) |
| Daily `BOUNCE \| SIDEWAYS \| FALL` + confidence + **`UNVALIDATED`** | **PARTIAL** — first note [`cas/notes/2026-09-01.md`](../teams/03_phd_market/cas/notes/2026-09-01.md) is SIDEWAYS / confidence 0.20 / **`DATA_INSUFFICIENT`** (clocks only, no live IEP) |
| Nightly `cas_calls[]` | **DONE** (loader) — `desk_intel.nightly.load_cas_calls`; sample [`cas/calls/2026-09-01.json`](../teams/03_phd_market/cas/calls/2026-09-01.json) `retune: BACKTEST_REQUIRED` |
| Dashboard CasPanel | **DONE** (mock bind) — `apps/web/src/components/CasPanel.jsx` on customer desk. No RSI/MACD. |
| Win rates | **none** — do not invent |
| Live indicative-index / IEP / imbalance feed | **TODO** / **BLOCKED** — no Dhan/NSE live CAS book in this workspace |
| Coded CAS strategy | **TODO** — not this ticket; still not `RESEARCH_READY_FOR_PROGRAMMING` |
| CAS-* hypotheses (close-bias / F&O tail / no-new-opt / expiry mark / pre-open) | **PARTIAL** — [`CAS_STRATEGIES.md`](../teams/03_phd_market/cas/CAS_STRATEGIES.md) CAS-001–005 `UNVALIDATED`. Dhan EN tape: **no** spoken Closing Auction Session ([`CAS_FROM_DHAN_VIDEOS.md`](../teams/01_research/docs/handoffs/CAS_FROM_DHAN_VIDEOS.md)). |

yaml URLs: `sources.cas[]` (NSE CAS product page, PCA, market timings, BSE notice 20260610-41).

---

## 9. Paper/shadow vs user lots; 30% capital quality bar — **PARTIAL**

| Requirement | Status | Evidence |
|-------------|--------|----------|
| If user **took** the trade: record lots / spot / reported P/L | **PARTIAL** | Spec in [`PERSONA_DESK.md`](../teams/00_orchestrator/docs/PERSONA_DESK.md). Mock `TookTrade.jsx` + API stub `POST .../took-trade`. Not live fills. |
| If user **skipped**: still **shadow-paper** to target / SL / invalidation | **PARTIAL** | `SHADOW_CLOSED` outcome. Nightly ledger stub. Dashboard book labeled MOCK. |
| Lots never hardcoded | **DONE** (policy) | Master plan `lot_size: FROM_INSTRUMENT_MASTER`. Official lots **not in repo** — **VERIFY**. |
| Quality bar: wrong call can cost **up to 30% of capital** (customer penalty) | **DONE** (requirement text) | Staging spec + persona. **Not** a backtested drawdown. EARLY ≠ reckless. |
| Learn on paper **before** 30% pain | **PARTIAL** | Jobs + outcomes exist as stubs. No real session P/L. |

Do not quote mock book points as performance.

---

## 10. Token TODO for live Dhan validation — **TODO**

**Do not call live Dhan in overnight / review.** Conceptual follow-up on [`TASK_STAGED_SIGNALS.md`](../teams/00_orchestrator/docs/TASK_STAGED_SIGNALS.md) and [`TASK_DESK_INTELLIGENCE.md`](../teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md).

| Check | Status |
|-------|--------|
| `YOUTUBE_API_KEY` validated (catalog era) | **DONE** (prior). Not needed for this review. Never paste into chat. |
| `DHAN_CLIENT_ID` + `DHAN_ACCESS_TOKEN` in gitignored `.env` | **TODO** / **BLOCKED** until the user puts them there |
| `python -m dhan_client status` | **TODO** |
| `python -m desk_intel --live morning` | **TODO** |
| `python -m desk_intel --live poll-chain --interval 3m` | **TODO** |
| Confirm chain rate-limit gate (1 unique / 3 s) | **TODO** |
| Confirm `execution.place_order` still **refuses** with tokens present | **TODO** (must stay refused) |
| Token refresh field names | **VERIFY FROM DOCS** | `.env.example` notes RenewToken vs `DHAN_REFRESH_TOKEN` |

If tokens empty: keep fixtures. Do not invent a live chain.

---

## 11. Standing Docs Auditor — **DONE** (checker; board may still FAIL)

Ticket: [`TASK_DOCS_AUDITOR.md`](../teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md) **DONE** (standing job). Charter: [`DOCS_AUDITOR.md`](../teams/09_review/docs/DOCS_AUDITOR.md).

Must run **after any requirement change** and as the last step of **POST_MARKET nightly**. yaml `jobs.docs_auditor.cadence: daily`. **No requirement merge without auditor.**

| Piece | Status | Notes |
|-------|--------|-------|
| CLI `python -m docs_auditor` / `python -m desk_intel audit-docs` | **DONE** | [`packages/docs-auditor`](../packages/docs-auditor/). Exit 0 pass / 1 stale. Never prints secrets. No web scrape. |
| Nightly hook | **DONE** | End of `python -m desk_intel nightly` and `python -m jobs post-market` |
| Report | **DONE** (overwrite daily) | [`AUDIT_LATEST.md`](../teams/00_orchestrator/docs/AUDIT_LATEST.md) |
| Manager sheet missing | **fail** | Auditor writes a HANDOFF stub and still exits 1 |
| Company board vs this sheet | **checked** | `company_board_drift` flags `PLAN.md` if transcript counts or Paper UI phase lag this sheet. |

```bash
python -m docs_auditor
python -m desk_intel audit-docs
python -m jobs post-market --offline
```

---

## SDLC gate (never skip)

```text
Research → Independent validation → Strategy spec → Backtest → Review → Paper UI → Live
```

| Gate artifact | Status |
|---------------|--------|
| Five-pass + red-team ([`docs/REVIEW.md`](REVIEW.md)) | **FAILED REVIEW** — performed 2026-09-06 ([`FIVE_PASS_HONEST_2026-09-06.md`](../teams/09_review/docs/FIVE_PASS_HONEST_2026-09-06.md)) |
| `RESEARCH_READY_FOR_PROGRAMMING` | **not set** |
| 14 strategy candidates + mixes | **DRAFT / UNVALIDATED** — KEEP_ALL. Default `MIX-DEFAULT-BUY`. After-cost 2026-09-06: MIX-CLUB-GR NIFTY **44% wr FAIL** (69% was optimistic); SCORE_SAMPLE empty; FUTIDX continuous **DATA_INSUFFICIENT** ([`BACKTEST_HONEST_2026-09-06.md`](../teams/06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)). 09 five-pass **FAILED REVIEW**. **No STRAT-015+.** Algo YAML [`ALGO_HANDOFF.md`](../teams/04_quant/docs/ALGO_HANDOFF.md). |
| Coded strategies | **paper/backtest only** — not live orders |
| Live orders | **none** (refused) |

---

## Open first (reviewer)

1. This file.  
2. [`REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](../teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md) — what **not** to trust.  
3. [`AGENT.md`](../AGENT.md) — roster + golden rules.  
4. [`teams/00_orchestrator/docs/HANDOFF_TOMORROW.md`](../teams/00_orchestrator/docs/HANDOFF_TOMORROW.md).  
5. Then jump via [`docs/INDEX.md`](INDEX.md). **Do not scan the whole tree.**  
6. **Do not** `npm install` / `npm run dev` until the user asks.

---

## Known blockers (not status theater)

1. Live **orders** still refused (correct). Data API **Active** as of 2026-09-03 paper-probe.  
2. Official lot-size + F&O close (15:30 vs 15:40) circulars **not in repo** — VERIFY.  
3. Super Scalper EMA lengths **UNKNOWN**; MACD ×3/×4 and 9 vs 10 MA **SOURCE_UNCERTAIN**.  
4. Order-flow history likely `DATA_INSUFFICIENT` (DEXT). Transcript `DzT_681GThA` SOURCE_FACT **extracted** 2026-09-03 (English); HQ series still missing.  
5. No git remote.  
6. CAS: no live IEP / indicative index. First daily book is research-only SIDEWAYS.  
7. Backtest **engine** ran 5y INDEX 1m **and** 5y rollingoption — both **FAIL**. Honest leftover 2026-09-06 — **no promote** (CLUB-GR after-cost 44% FAIL; SCORE_SAMPLE empty; FUTIDX stitch ~64d DATA_INSUFFICIENT). FUTIDX current-month ids **68407 / 68390 / 844615** (CSV, 2026-09-03). Retune still `BACKTEST_REQUIRED`. Q8/Q12 not waived.  
8. INDEX volume UNKNOWN as VWAP tape (02). Spoken 003 is 3m FUTIDX; paper path is 1m→3m resample. Continuous FUTIDX history **DATA_INSUFFICIENT** (live CSV + stitch attempted 2026-09-06).

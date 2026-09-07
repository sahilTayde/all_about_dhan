# AGENT.md — orchestrator for all_about_dhan

**Read this file first.** Morning / frontier review: open [`docs/MASTER_REQUIREMENTS.md`](docs/MASTER_REQUIREMENTS.md) (the score) and [`teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md) (what not to trust). Then [`docs/INDEX.md`](docs/INDEX.md) and jump to one team folder. Do not scan the whole tree. **Do not restart npm until asked.**

---

## Company one-liner

**all_about_dhan** is a DhanHQ-only research → validate → backtest → paper → live workspace for NIFTY, BANKNIFTY, and SENSEX index options (CE/PE buy signals first). Working name only — no product brand yet.

Never skip: **Research → Independent validation → Strategy spec → Backtest → Review → Paper UI → Live**.

---

## Roster

| ID | Team | Job | Home |
|----|------|-----|------|
| 00 | Orchestrator | Task board, SDLC gates, routing | `teams/00_orchestrator/` |
| 01 | Research | YouTube catalog + transcripts (channels from `config/workspace.yaml`; default `@DhanHQ`) | `teams/01_research/` |
| 02 | PhD math | Independent math / indicator / Greeks validation | `teams/02_phd_math/` |
| 03 | PhD market | Exchange, microstructure, contract rules; **CAS analyst** (Closing Auction Session) | `teams/03_phd_market/` · CAS home `teams/03_phd_market/cas/` |
| 04 | Quant | Testable hypotheses; **staged signals** (WATCH → EARLY → CONFIRMED → IN-PROGRESS) | `teams/04_quant/` |
| 05 | Analysis | Scorecards, ablation; **desk-intel** (news + **3m** chain → MARKET_SIGNAL) | `teams/05_analysis/` · `packages/desk-intel/` |
| 06 | Backtesting | Historical tests, OOS, costs; **retune gate** (`RETUNE_PROPOSAL` `BACKTEST_REQUIRED`) | `teams/06_backtesting/` |
| 07 | Coding | Product: **customer desk** (`/`) vs internal **`/desk`**; code in `apps/` + `packages/` | `teams/07_coding/` · `apps/web/` · `apps/api/` |
| 08 | Testing | QA, fixtures, paper-trade checks | `teams/08_testing/` |
| 09 | Review | Five-pass + red-team; `RESEARCH_READY_FOR_PROGRAMMING`; **Docs Auditor** (after requirement change + nightly) | `teams/09_review/` · charter `teams/09_review/docs/DOCS_AUDITOR.md` |

Shared code: `packages/dhan-client`, `packages/desk-intel`, `packages/docs-auditor`, `packages/contracts`, `packages/indicators`.  
Product: `apps/api` (FastAPI dry-run; orders refused), `apps/web` (**customer** `/` vs research **`/desk`**; MOCK JSON, no Dhan in the browser).

---

## Current phase

**Phase 0–2 overlap** plus Phase 1 Dhan **data**, Phase 3 **paper engine** (INDEX proxy **FAIL** + option-premium **FAIL** + after-cost club **FAIL**, not a promote), Phase 6 paper-UI **mock** + optional live-signal WS. Not a paper gate. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.

Catalog + 45 transcripts + 45 English companions exist. SOURCE_FACT **partial**. **English STRAT bind** [`TRANSCRIPT_STRATEGY_BIND.md`](teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md). **Engine mix** (`ENGINE_MIX.md` / `MIX_CATALOG.md` KEEP_ALL) still `UNVALIDATED`; 09 five-pass **FAILED REVIEW**. **Boss** [`BOSS_AGENT.md`](teams/00_orchestrator/docs/BOSS_AGENT.md). Generic DhanHQ client (**orders refused**). Dashboard `apps/web` = **MOCK** unless `/ws/signals` paper overlay. **No live orders.** Honest leftover 2026-09-06: after-cost CLUB-GR NIFTY **44% wr FAIL** (69% was optimistic); SCORE_SAMPLE empty; continuous FUTIDX **DATA_INSUFFICIENT** ([`BACKTEST_HONEST_2026-09-06.md`](teams/06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)). FUTIDX CSV ids resolved 2026-09-03. Chain **3m**. Docs Auditor standing. **2026-09-07:** Okala-IN `FOUNDER_PAPER_ACCEPT` PAPER CE/PE notify (robust WR>50% cells) — **NO_PROMOTE** ([`OKALA_IN_PAPER_ACCEPT.md`](teams/04_quant/docs/OKALA_IN_PAPER_ACCEPT.md)).

Full SDLC: [`docs/SDLC.md`](docs/SDLC.md). **Score sheet:** [`docs/MASTER_REQUIREMENTS.md`](docs/MASTER_REQUIREMENTS.md). Company board: [`PLAN.md`](PLAN.md). Snapshot: [`teams/00_orchestrator/docs/STATUS.md`](teams/00_orchestrator/docs/STATUS.md). Wake-up: [`HANDOFF_TOMORROW.md`](teams/00_orchestrator/docs/HANDOFF_TOMORROW.md).

---

## Task board (Phase 0)

- [x] Create modular monorepo tree, `.gitignore`, `.env.example`
- [x] Move Codex YouTube plan to `teams/01_research/youtube/PLAN.md` (verbatim)
- [x] Write master docs, team stubs, Cursor routing rules
- [x] YouTube API key validated; catalog `@DhanHQ` playlists (2,034 videos)
- [x] Transcript collector under `teams/01_research/youtube/src/`
- [x] Park unrelated blocked videos in `data/transcripts/parked_tomorrow/`
- [x] After timedtext cooldown: `python -m src transcripts --retry-pending --english` — **DONE 2026-09-01** (12 newly verified; 44 new YouTube English; remaining 429s: 0). Ticket: `teams/00_orchestrator/docs/TASK_YOUTUBE_TRANSCRIPT_RETRY.md`
- [x] Claim / indicator extraction **started** on verified HIGH index-options (HAUSZx-hYdY first) — **partial**; not all 45 verified files
- [x] OPTIONS_INDEX English SOURCE_FACT packet (2026-09-03) — HAUSZx / `_exm` / DzT / 8h9 + EN deltas
- [x] Finish SOURCE_FACT on remaining verified HIGH/MEDIUM **STOCK_ONLY** / scanners with English on disk (2026-09-03); catalog `STOCK_ONLY` **9** still no EN; keep PENDING / UNAVAILABLE out
- [x] Generic `packages/dhan-client` + `apps/api` dry-run (no live orders; token refresh VERIFY FROM DOCS)
- [x] Thin paper dashboard `apps/web` (Vite + React; mock CE/PE; `VITE_API_URL` optional)
- [x] Customer master config `config/workspace.yaml` (URLs/books; keys stay in `.env`)
- [x] Desk intelligence (news RSS + Dhan option chain → MARKET_SIGNAL bias) — `packages/desk-intel`; ticket `teams/00_orchestrator/docs/TASK_DESK_INTELLIGENCE.md`
- [x] PRE_MARKET / POST_MARKET jobs + signal **outcomes** + nightly PhD recon (paper/shadow only; no orders) — ticket `teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md`
- [x] Nightly **retune gate** (session tags `NEWS_DAY`/`EXPIRY`/`NORMAL`; `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; no production param write) — ticket `teams/00_orchestrator/docs/TASK_RETUNE_GATE.md`
- [x] Official Dhan **indicator API vs chart-only** catalog (2026-09-01 docs) — ticket `teams/00_orchestrator/docs/TASK_DHAN_INDICATORS.md`
- [x] Staged signals — **docs `IN_PROGRESS`**; paper `/ws/signals`; orders **refused**. Ticket: `TASK_STAGED_SIGNALS.md` + [`TASK_ALGO_ENGINE.md`](teams/00_orchestrator/docs/TASK_ALGO_ENGINE.md)
- [x] CAS special analyst (Closing Auction Session research + daily BOUNCE/SIDEWAYS/FALL `UNVALIDATED` + `cas_calls[]` recon + CasPanel) — ticket `teams/00_orchestrator/docs/TASK_CAS_ANALYST.md` (`IN_PROGRESS`; no live tape; **no win rates**; no orders)
- [x] Standing **Docs Auditor** (09) — after any requirement change **and** post-market nightly. `python -m docs_auditor`. Ticket `teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md`
- [ ] Transcript coalition (English packets + STRAT bind + KEEP_ALL MIX/CAS) — ticket `TASK_TRANSCRIPT_COALITION.md` (`IN_PROGRESS`; 14 STRATs `BACKTEST_BOOK` / `UNVALIDATED`; **not** `RESEARCH_READY_FOR_PROGRAMMING`; no auto-retune)
- [ ] Boss agent + customer talk (trend + 3m chain + news hold + analog) — docs `IN_PROGRESS` ([`BOSS_AGENT.md`](teams/00_orchestrator/docs/BOSS_AGENT.md), [`CUSTOMER_TALK.md`](teams/05_analysis/docs/CUSTOMER_TALK.md)). Mandate ≠ claimed profit.

---

## Open these files

| If the task is… | Open |
|-----------------|------|
| **Morning / frontier review** | [`docs/MASTER_REQUIREMENTS.md`](docs/MASTER_REQUIREMENTS.md), [`REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md), this file. Do not restart npm. |
| Any agent session | This file, then [`docs/INDEX.md`](docs/INDEX.md) |
| **Customer URLs / books / source switch** | [`config/workspace.yaml`](config/workspace.yaml) — **this is the file customers change** |
| **Desk intel (news + chain bias)** | [`teams/05_analysis/docs/DESK_INTELLIGENCE.md`](teams/05_analysis/docs/DESK_INTELLIGENCE.md), [`packages/desk-intel/`](packages/desk-intel/), persona [`teams/00_orchestrator/docs/PERSONA_DESK.md`](teams/00_orchestrator/docs/PERSONA_DESK.md). News URLs + poll intervals: `sources.news[]` / `desk_intel` in workspace.yaml (**3m** full chain default). Ticket [`TASK_CUSTOMER_DESK.md`](teams/00_orchestrator/docs/TASK_CUSTOMER_DESK.md). Jobs: [`TASK_PRE_POST_MARKET_JOBS.md`](teams/00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md). **Retune gate:** [`TASK_RETUNE_GATE.md`](teams/00_orchestrator/docs/TASK_RETUNE_GATE.md), spec [`RETUNE_GATE.md`](teams/06_backtesting/docs/RETUNE_GATE.md). Nightly ends with **Docs Auditor**. |
| **Staged signals / missed lagging PE** | Ticket [`TASK_STAGED_SIGNALS.md`](teams/00_orchestrator/docs/TASK_STAGED_SIGNALS.md) (`IN_PROGRESS`; live token **TODO**), spec [`SIGNAL_STAGING.md`](teams/04_quant/docs/SIGNAL_STAGING.md) (WATCH → EARLY → CONFIRMED → **IN-PROGRESS** → ACHIEVED/STOPPED/INVALIDATED). Postmortem [`MISSED_TRADE_POSTMORTEM.md`](teams/09_review/docs/MISSED_TRADE_POSTMORTEM.md). EARLY ≠ guaranteed fill. No live orders. **Customer UI** vs internal `/desk` (indicator soup stays on `/desk` only). |
| **Docs vs code drift** | Charter [`DOCS_AUDITOR.md`](teams/09_review/docs/DOCS_AUDITOR.md), ticket [`TASK_DOCS_AUDITOR.md`](teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md), report [`AUDIT_LATEST.md`](teams/00_orchestrator/docs/AUDIT_LATEST.md). `python -m docs_auditor` or `python -m desk_intel audit-docs`. **No requirement merge without auditor.** |
| YouTube catalog / transcripts | `teams/01_research/youtube/ANALYSIS.md`, `teams/01_research/` |
| Topic → per-topic strategy docs | [`teams/01_research/docs/TOPIC_STRATEGY_PIPELINE.md`](teams/01_research/docs/TOPIC_STRATEGY_PIPELINE.md), [`teams/04_quant/docs/topics/`](teams/04_quant/docs/topics/) |
| Dhan ecosystem URLs / what is not evidence | [`teams/01_research/docs/DHAN_ECOSYSTEM.md`](teams/01_research/docs/DHAN_ECOSYSTEM.md), [`docs/RESEARCH.md`](docs/RESEARCH.md) |
| **Official Dhan indicators (API vs chart)** | [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md), [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md), [`research/indicator_knowledge_base.md`](research/indicator_knowledge_base.md) |
| Desk persona seed (OI / stop hunts / news) | [`teams/00_orchestrator/docs/PERSONA.md`](teams/00_orchestrator/docs/PERSONA.md); operator confirm/veto checklist [`PERSONA_DESK.md`](teams/00_orchestrator/docs/PERSONA_DESK.md) |
| Education ≠ advice / provenance | [`docs/COMPLIANCE.md`](docs/COMPLIANCE.md) |
| Independent math validation | `teams/02_phd_math/`, [`docs/RESEARCH.md`](docs/RESEARCH.md) |
| Market / contract / SENSEX rules | `teams/03_phd_market/` |
| **CAS (close auction / cash bias)** | [`teams/03_phd_market/cas/RESEARCH.md`](teams/03_phd_market/cas/RESEARCH.md), ticket [`TASK_CAS_ANALYST.md`](teams/00_orchestrator/docs/TASK_CAS_ANALYST.md). Nightly `cas_calls[]`. Customer panel `CasPanel.jsx`. |
| **Transcript coalition / algo handoff (docs only)** | Ticket [`TASK_TRANSCRIPT_COALITION.md`](teams/00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md). **Spoken-rule bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](teams/01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) (English wins). Packets: [`OPTIONS_INDEX_PACKET.md`](teams/01_research/docs/handoffs/OPTIONS_INDEX_PACKET.md), [`TA_STRUCTURE_PACKET.md`](teams/01_research/docs/handoffs/TA_STRUCTURE_PACKET.md), [`EQUITY_ETF_PACKET.md`](teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md). Merge shape: [`ALGO_HANDOFF.md`](teams/04_quant/docs/ALGO_HANDOFF.md) (YAML only; **do not code**). Review notes: [`COALITION_REVIEW.md`](teams/09_review/docs/COALITION_REVIEW.md). Market clocks: [`TRANSCRIPT_MARKET_NOTES.md`](teams/03_phd_market/docs/TRANSCRIPT_MARKET_NOTES.md). Still **not** `RESEARCH_READY_FOR_PROGRAMMING`. |
| Expert coalition / engine mix (docs only) | Board [`EXPERT_COALITION.md`](teams/00_orchestrator/docs/EXPERT_COALITION.md). **Boss** [`BOSS_AGENT.md`](teams/00_orchestrator/docs/BOSS_AGENT.md). KEEP_ALL [`MIX_CATALOG.md`](teams/04_quant/docs/MIX_CATALOG.md). Mix [`ENGINE_MIX.md`](teams/04_quant/docs/ENGINE_MIX.md) (`UNVALIDATED`). **Paper watch** [`PAPER_WATCH_CLUB_GR.md`](teams/04_quant/docs/PAPER_WATCH_CLUB_GR.md) (MIX-CLUB-GR 69% optimistic kept; not default). CAS [`CAS_STRATEGIES.md`](teams/03_phd_market/cas/CAS_STRATEGIES.md). Talk [`CUSTOMER_TALK.md`](teams/05_analysis/docs/CUSTOMER_TALK.md). Analog [`EVENT_MEMORY.md`](teams/06_backtesting/docs/EVENT_MEMORY.md). 09 [`KEEP_ALL_REVIEW.md`](teams/09_review/docs/KEEP_ALL_REVIEW.md) — **not** a pass. |
| Strategy spec / hypotheses | [`teams/04_quant/docs/MASTER_STRATEGY_PLAN.md`](teams/04_quant/docs/MASTER_STRATEGY_PLAN.md) (v0.1 DRAFT, **14 candidates, no win rates**; coalition banner). Staging: [`SIGNAL_STAGING.md`](teams/04_quant/docs/SIGNAL_STAGING.md). Algo YAML: [`ALGO_HANDOFF.md`](teams/04_quant/docs/ALGO_HANDOFF.md) |
| Resume tomorrow | [`teams/00_orchestrator/docs/HANDOFF_TOMORROW.md`](teams/00_orchestrator/docs/HANDOFF_TOMORROW.md) — read MASTER_REQUIREMENTS first; do not restart npm until asked |
| Backtest | `teams/06_backtesting/`, [`docs/REVIEW.md`](docs/REVIEW.md), retune gate [`RETUNE_GATE.md`](teams/06_backtesting/docs/RETUNE_GATE.md) |
| Dhan token / DhanHQ API | `packages/dhan-client/`, [`docs/SECURITY.md`](docs/SECURITY.md) |
| Signal UI | `apps/web/` — **customer desk** `/` (ticket + **IN-PROGRESS** + **CasPanel** + **confidence box**; book P/L **MOCK**) vs internal **`/desk`**. Mock: http://localhost:5173 · `/desk`. Ticket shape: [`CUSTOMER_TICKET.md`](teams/05_analysis/docs/CUSTOMER_TICKET.md). |
| API | `apps/api/` |
| Handoff between teams | [`docs/HANDOFF.md`](docs/HANDOFF.md) + the team's `HANDOFF.md` |
| **TradingAgents India paper agents** | [`ADOPT_TRADINGAGENTS.md`](teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md), package `packages/trading_agents_india` (`python -m trading_agents_india session --dry-run`). EXTERNAL Apache-2.0. No live orders. |
| **Agent RAG (speed KB)** | [`AGENT_RAG.md`](teams/01_research/docs/AGENT_RAG.md), package `packages/agent_rag` — `data/knowledge/agent_rag.sqlite` (FTS5; **not** `transcripts.sqlite`). `python -m agent_rag query "…"`, `paper-backtest`, `eod-recon`. |
| Review gate | [`docs/REVIEW.md`](docs/REVIEW.md), `teams/09_review/`, Docs Auditor [`DOCS_AUDITOR.md`](teams/09_review/docs/DOCS_AUDITOR.md) |

Full map: [`docs/INDEX.md`](docs/INDEX.md).

---

## Credentials needed

**YouTube:** `YOUTUBE_API_KEY` is in repo-root `.env` (never in chat). Key validated HTTP 200. How-to: [`teams/01_research/youtube/README.md`](teams/01_research/youtube/README.md). **Channel list:** [`config/workspace.yaml`](config/workspace.yaml) — default enabled source is [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ). To switch channel, change the URL/`enabled` flags there; do not hard-code a new channel in Python.

**Later (Phase 1):** `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN`, and Dhan's documented refresh fields — `.env` / `secrets/` only. Names: [`.env.example`](.env.example) and `secrets_from_env` in workspace.yaml. Rules: [`docs/SECURITY.md`](docs/SECURITY.md).

**Optional (paper agents):** `OPENAI_API_KEY` / `OPENAI_MODEL` for `packages/trading_agents_india` LLM path — empty → rule fallback. Never paste keys into chat.

---

## Golden rules

1. Default YouTube source is official Dhan (`@DhanHQ`) while `config/workspace.yaml` has that row enabled as `TIER_1`. Other channels in that file are `EXTERNAL_RESEARCH` and stay disabled until the customer enables them. Do not scrape disabled rows.
2. Education ≠ proof. Never hallucinate transcripts or invent parameters.
3. Three layers: `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS` — never collapse them.
4. Broker is **Dhan / DhanHQ** by default (`implementation.broker: dhan`). Production indicators stay Dhan-only unless `implementation.indicators` is changed. No other broker credentials in git.
5. Phase 0 markets: NIFTY, BANKNIFTY, SENSEX **index options**. No stock strategies, no live orders, no swing/positional yet.
6. Never hardcode lot sizes. Always model costs and slippage in backtests.
7. Never skip the SDLC gate. Review must pass before coding a strategy.
8. Tokens never in git, never in LLM prompts. Use `.env` / `secrets/`.
9. Stay in your team's owned paths (see that team's `README.md`).
10. When evidence is missing: `UNKNOWN` or `DATA_INSUFFICIENT`. Do not guess.
11. Do **not** retune live indicator params or STRAT-* from nightly recon. Tag `NEWS_DAY`/`EXPIRY`/`NORMAL`; emit `RETUNE_PROPOSAL` `BACKTEST_REQUIRED`; default **keep current strategy**. Gate: [`teams/06_backtesting/docs/RETUNE_GATE.md`](teams/06_backtesting/docs/RETUNE_GATE.md).
12. **No requirement merge without the Docs Auditor.** After editing `MASTER_REQUIREMENTS.md`, `AGENT.md`, team `HANDOFF.md`, or `workspace.yaml` poll/jobs, run `python -m docs_auditor` (or `python -m desk_intel audit-docs`). Nightly POST_MARKET runs it daily. Charter: [`teams/09_review/docs/DOCS_AUDITOR.md`](teams/09_review/docs/DOCS_AUDITOR.md).

Full golden list: `teams/01_research/youtube/PLAN.md` Appendix D.

---

## Desk persona (seed — indicator expert)

Full fusion of institutional + educator personas is **another agent**. This seed is for later writers so strategies do not pretend HQ returns Supertrend series.

- **Desk:** inventory and risk in **premium / delta / vega**; lots discrete; VWAP on **futures or option tape**; Conditional Trigger indicator names are **EQ/IDX**, not a documented OPTIDX scanner.  
- **Operator psychology:** **open interest** is positioning (chain `oi` / `previous_oi`), not a crystal ball; **stop hunts** run obvious **chart** VWAP/Supertrend/round strikes — model gap, not touch fills; **news shock** makes lagging `RSI_14`/MACD late — default **no-trade**, not “wait for the cross.”  
- **Staged desk (post missed PE):** mix indicators + news + chain; **EARLY** (~1 min lead **target**) with honesty/color; 5m Supertrend/MACD **confirm or kill**. Quality bar: wrong call can cost **up to 30% of capital**. States WATCH/EARLY/CONFIRMED/**IN-PROGRESS**/EXPIRED/VETOED. **Outcomes** ACHIEVED/STOPPED/INVALIDATED/EXPIRED/LOST/COMPLETED/SHADOW_CLOSED — never leave CONFIRMED still valid after lunch if the idea is dead. Customer `/` has no indicator soup; internals stay on **`/desk`**. [`PERSONA_DESK.md`](teams/00_orchestrator/docs/PERSONA_DESK.md).  
- **Indicator expert:** name the surface (trigger enum vs OHLC compute vs ScanX vs spoken param). No invented tokens. **No Supertrend/RSI/MACD/EMA9 series API**; **no `EMA_9` in annexure**. Details: [`teams/00_orchestrator/docs/PERSONA.md`](teams/00_orchestrator/docs/PERSONA.md).

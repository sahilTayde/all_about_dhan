# PLAN.md — company SDLC board

Working name: **all_about_dhan**. Broker: **Dhan / DhanHQ only**. First markets: **NIFTY, BANKNIFTY, SENSEX index options** (CE/PE buy). Swing/positional later.

This file is the **company** plan. The long Codex YouTube research plan lives at [`teams/01_research/youtube/PLAN.md`](teams/01_research/youtube/PLAN.md) — do not duplicate it here.

Agents: read [`AGENT.md`](AGENT.md) first. **Score:** [`docs/MASTER_REQUIREMENTS.md`](docs/MASTER_REQUIREMENTS.md). Phases: [`docs/SDLC.md`](docs/SDLC.md). Morning brief: [`teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md`](teams/00_orchestrator/docs/REVIEW_BRIEF_FOR_FRONTIER_MODEL.md).

---

## SDLC (never skip)

**Research → Independent validation → Strategy spec → Backtest → Review → Paper UI → Live**

Honest phase: **0–2 overlap** plus Phase 1 **data**, Phase 3 **paper engine** (FAIL proxy), Phase 6 **mock** + optional live paper WS. **Not** `RESEARCH_READY_FOR_PROGRAMMING`. No live orders. Proxy ratings are UNVALIDATED.

| Phase | Name | Status |
|-------|------|--------|
| 0 | Research infra (repo + YouTube collector) | **Mostly done** — catalog 2,034; **45** `TRANSCRIPT_VERIFIED` + **45** English; SOURCE_FACT still partial |
| 1 | Dhan data infra | **Skeleton** — `dhan-client` + FastAPI (orders refused). Data API **probed** 2026-09-03. FUTIDX CSV ids resolved |
| 2 | Knowledge corpus | **PARTIAL DRAFT** — 14 STRATs **UNVALIDATED**; official indicator catalog done |
| 3 | Backtest engine | **PARTIAL** — 5y INDEX + rollingoption + honest leftover 2026-09-06; after-cost FAIL; `BACKTEST_REQUIRED` |
| 4 | Strategy specs | **v0.1 DRAFT** — `STRAT-001`–`014` **UNVALIDATED**; paper 003/001/006 coded |
| 5 | Validation + review | **FAILED REVIEW** — five-pass performed 2026-09-06 ([`FIVE_PASS_HONEST_2026-09-06.md`](teams/09_review/docs/FIVE_PASS_HONEST_2026-09-06.md)); not research-ready |
| 6 | Paper UI | **Mock exists** — customer `/` vs `/desk`. Optional `/ws/signals` paper overlay. **MOCK** P/L |
| 7 | Production | **Not started** |

---

## This week's work — Phase 0–2 overlap

Collector has run. Generic DhanHQ client + FastAPI exist (orders refused). Paper dashboard `apps/web` is **MOCK** plus optional `/ws/signals` paper overlay. Customer switch file: [`config/workspace.yaml`](config/workspace.yaml). Paper algos in `packages/backtest` — **not** live orders.

### Task board

- [x] Create modular monorepo tree (`docs/`, `teams/00–09`, `apps/`, `packages/`, `data/`, `secrets/`)
- [x] `.gitignore` + `.env.example` (names only)
- [x] Move Codex plan verbatim → `teams/01_research/youtube/PLAN.md`
- [x] Master docs + per-team stubs + `.cursor/rules`
- [x] Validate `YOUTUBE_API_KEY`; catalog `@DhanHQ` playlists → `data/youtube/video_catalog.{csv,json}`
- [x] Transcript collector `teams/01_research/youtube/src/` — **45** verified + **45** English (`tlang=en`; no LLM)
- [x] Timedtext retry — **DONE 2026-09-01** (12 newly verified; remaining related 429s: 0). Parked 4 stay parked
- [x] Claim extraction **started** (partial) — see `teams/04_quant/docs/MASTER_STRATEGY_PLAN.md`
- [x] OPTIONS_INDEX English SOURCE_FACT (2026-09-03) — packet + `_exm` / DzT / 8h9 / HAUSZx.en
- [x] Finish SOURCE_FACT on remaining verified HIGH/MEDIUM **STOCK_ONLY** / scanners **with English on disk** (2026-09-03). Catalog `STOCK_ONLY` **9** still no EN.
- [x] Generic `packages/dhan-client` + FastAPI dry-run (**no live orders**). Data API paper-probe 2026-09-03.
- [x] Customer master config [`config/workspace.yaml`](config/workspace.yaml) (URLs/books; keys in `.env`)
- [x] Desk intelligence [`packages/desk-intel`](packages/desk-intel) (news RSS + **3m** chain + last snapshot; no orders)
- [x] PRE/POST jobs + nightly recon — dry-run; `RETUNE_PROPOSAL` **BACKTEST_REQUIRED** (no engine; no production param write)
- [ ] Staged signals — **docs `IN_PROGRESS`**; live `DHAN_*` **TODO** (do not call)
- [x] CAS analyst (Closing Auction Session) — research + `cas_calls[]` + CasPanel mock; ticket **`IN_PROGRESS`**; daily book **UNVALIDATED** / `DATA_INSUFFICIENT`; no win rates
- [ ] Transcript coalition — KEEP_ALL + MIX/CAS docs + bind applied; ticket [`TASK_TRANSCRIPT_COALITION.md`](teams/00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md) **`IN_PROGRESS`**; 14 STRATs stay **UNVALIDATED**; not `RESEARCH_READY_FOR_PROGRAMMING`

---

## Product shape (document now; mock UI exists)

- **Customer desk `/`:** one ticket — underlying (NIFTY / SENSEX / BANKNIFTY), **BUY CE** or **BUY PE**, strike/entry/stop/target, status including **IN-PROGRESS**, (i) legend, mock sentiment windows, **CasPanel** (Closing Auction Session bias), “Did you take this trade?”, shadow paper. Book P/L is **MOCK**.
- **Internal `/desk`:** research view (honesty stages, indicator lights, factor checklist). **Not** the customer product.
- **API:** FastAPI, DhanHQ only, token service in `packages/dhan-client`. Orders refused.
- **Not live:** orders, other brokers, stock strategies, swing/positional, coded STRATs.

---

## Next ask (blocked on user)

1. Confirm we execute [`teams/01_research/youtube/PLAN.md`](teams/01_research/youtube/PLAN.md) as Stage 1 research.
2. Confirm enabled YouTube sources in [`config/workspace.yaml`](config/workspace.yaml) (default `@DhanHQ`). Switch channel by URL there; do not enable external rows unless you want them scraped.
3. YouTube key is already in `.env` (do not paste into chat). Live Dhan: put `DHAN_*` in `.env` only when ready; **do not call live APIs in review**.

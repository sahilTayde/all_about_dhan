# OpenAI Astra review — paper agents today

**Canonical path:** `teams/00_orchestrator/docs/open_ai_astra_review.md`  
**Root pointer:** [`open_ai_astra_review.md`](../../../open_ai_astra_review.md)  
**Date (UTC):** 2026-09-06  
**Primary model:** `gpt-6-astra` (`OPENAI_MODEL` from `.env`; key present, value never logged)  
**Second opinion:** `gpt-4o`  
**Founder brief:** [`Open_ai_astra.md`](../../../Open_ai_astra.md)  
**Related:** [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md) · [`PLAN_MARKET_HOURS_PAPER_AGENTS.md`](PLAN_MARKET_HOURS_PAPER_AGENTS.md) · [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md) · MIX_CATALOG §18 · [`AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)

**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE**. **KEEP_ALL** STRAT-001–014. **No live orders.**

**Raw council JSON (no secrets):** `data/recon/ASTRA_COUNCIL_RAW_2026-09-06.json`

---

## 1. What Astra understands as requirements

From founder brief + desk mandate (Astra turn, compact):

1. Agentic **PAPER** operation for NIFTY / BANKNIFTY / SENSEX CE/PE **buy-first** during IST market hours.
2. Keep existing capabilities (**KEEP_ALL**); do not invent STRAT-015+; do not promote on thin samples (**NO_PROMOTE**).
3. Multi-agent graph may propose/explain; **hard risk + LIVE refuse** stay deterministic.
4. Review-first then implement only approved paper-today items; never enable live broker orders by default.
5. Honesty: **no demonstrated edge**; mocks / LLM prose ≠ validation; SCORE_SAMPLE stays empty until real NORMAL days exist.
6. Calendar honesty: if IST date is a weekend/holiday, use **simulate / replay**, not “live market” claims.

Astra role note (brief §2): “Astra” is a **reviewer persona**; runtime model id is whatever is configured (`gpt-6-astra` here). Do not invent a separate Grok path.

---

## 2. Requirements matrix (brief REQ-01…18)

Assessments are desk-evidence (code + docs), not a claim that Astra inspected every line. Layers stay separate.

| ID | Requirement (brief) | Assessment | Evidence / note |
|----|---------------------|------------|-----------------|
| REQ-01 | NIFTY/BN/SENSEX signal generation | **Partial** | `trading_agents_india` + fixtures / optional live chain; leans are HYPOTHESIS / paper |
| REQ-02 | Clear entry/stop/target/invalidation | **Partial** | Ticket + ATR MIX docs; option premium LTP often DI; SL/TP backtest FAIL |
| REQ-03 | Automatic paper trades for approved signals | **Partial** | Paper ledger + trader role; fills are simulated paper, not broker |
| REQ-04 | User taken/skipped/unknown | **Partial** | Customer UI Yes/No exists; agent loop confirmation incomplete vs brief |
| REQ-05 | Persistent trades + EOD recon | **Partial** | sqlite + paper_watch jsonl; `agent_rag eod-recon` stub `BACKTEST_REQUIRED` |
| REQ-06 | Dhan market-data integration | **Partial** | Client + hooks; fixtures when dry/empty; orders refused |
| REQ-07 | Verified historical coverage | **Partial** / **DI** | Recon OHLC on disk; expired options / full chain history not claimed |
| REQ-08 | Paper vs live separation | **Implemented** (policy) | `ExecutionClient` + `mode.LIVE` refuse; dashboard toggle alone not the gate |
| REQ-09 | Explicit testable strategies | **Partial** | STRAT/MIX docs KEEP_ALL; metrics null; UNVALIDATED |
| REQ-10 | Traceable YouTube extraction | **Partial** | Transcripts + binds; CF fail=30 remain |
| REQ-11 | Controlled research variations | **Partial** | MIX-* namespace; no silent catalog deletes |
| REQ-12 | Defensible backtesting | **Partial** | Multiple books **FAIL** promote; proxy ≠ premium P/L |
| REQ-13 | Useful multi-agent roles | **Partial** | Personas + handoffs shipped; LLM optional |
| REQ-14 | Pre-market global/macro context | **Partial** | desk-intel RSS; GIFT/SGX VERIFY |
| REQ-15 | Safe nightly learning / promotion | **Partial** | RETUNE_GATE + EVENT_MEMORY; **no auto-retune** |
| REQ-16 | Clear dashboard | **Partial** | Customer `/` ticket; `/desk` paper agents mock seed only this phase |
| REQ-17 | Risk, security, tests | **Partial** | Smoke tests + refuse paths; more isolation tests still useful |
| REQ-18 | Owner approval before impl changes | **Implemented** (this ticket) | Founder Phase B authorized paper-today items only |

---

## 3. Have vs gaps

### Have

- `packages/trading_agents_india` paper graph (news → … → trader → risk → ledger).
- IST `session_clock`: shell **09:00–15:30**; dead-band HOLD **09:00–09:30** + **15:00–15:30**; active **09:30–15:00**; default tick **45s**.
- `market-hours` CLI (`--simulate`, `--live-chain`, `--prefer-desk`, `--gather-news`).
- `llm.py` Astra/gpt-6 aware (`max_completion_tokens`, no temperature).
- MIX-TA-* PAPER_WATCH (catalog §18); MIX-DEFAULT-BUY unchanged.
- `agent_rag` FTS5 + EOD stub + paper-backtest **NO_PROMOTE**.
- Mock seed `apps/web/public/mock/paper_agents.json`.
- Dhan **orders refused**; KEEP_ALL; prior OpenAI councils `APPROVE_WITH_GUARDRAILS`.

### Gaps (honesty)

- `--use-llm` was opt-in only (fixed for market-hours when key present — see §4).
- `agent_rag` not previously injected into agent prompts (bounded inject now).
- `/desk` live wire **CLOSED** this phase (CLI is source of truth).
- SCORE_SAMPLE empty; EVENT_MEMORY analogs empty.
- Depth / full WS decode **PARKED / DATA_INSUFFICIENT**.
- User confirmation loop incomplete vs brief REQ-04.
- **No validated edge**; all promote-relevant books FAIL or WAITING.

---

## 4. Council debate → resolved decisions

| Point | Astra | gpt-4o | **00 desk resolve** |
|-------|-------|--------|---------------------|
| Default `--use-llm` when key | Approve (paper) + `--no-llm` | Prefer explicit only | **Accept Astra + founder Phase B** — market-hours soft-default when key present; `--no-llm` wins |
| `--live-chain` default | Document; keep off | Keep off | **Keep opt-in** |
| `agent_rag` in prompts today | Bound + ship | Allow with caution | **Ship bounded** (cap hits; untrusted delimiter; never override risk) |
| Readiness claim | `ReadyIsolatedResearch` | Avoid overclaim | **Isolated research + supervised paper via CLI**; Sunday 2026-09-06 → prefer `--simulate` |
| EOD clears NO_PROMOTE? | Never | Soft disagreement | **Reject gpt-4o** — EOD never promotes; `BACKTEST_REQUIRED` stands |

Astra paper verdict string: **`ReadyIsolatedResearch`**. Desk gloss: ready for **supervised paper CLI** (fixtures / optional live *data*), not broader evaluation, not live trading.

---

## 5. Agreed changes (prioritized for paper trading today)

Implementation order (Astra): `P0 → D → B → A → E → C → H → F → G`

| ID | Change | Acceptance (today) |
|----|--------|--------------------|
| P0 | Paper safety labels on runner/CLI | Mode PAPER default; LIVE refuse unchanged; output gate flags |
| D | Harden/verify 09:00 IST clock | Tests: weekend, shell open 09:00, dead-band, active window |
| B | Astra LLM params | Higher default `max_completion_tokens` for gpt-6/astra; no temperature |
| A | Default LLM on market-hours if key | `--no-llm` opt-out; session cmd stays explicit `--use-llm` unless flagged |
| E | Bounded `agent_rag` snippets in prompts | Fail-soft if DB missing; cap ≤4 hits |
| C | Soft-default desk + news on market-hours | `--no-prefer-desk` / `--no-gather-news` to disable |
| H | Refresh `paper_agents.json` | Labeled MOCK/PAPER; point at new CLI defaults |
| F | EOD recon runbook | Document cron + `python -m agent_rag eod-recon` |
| G | Live-chain docs | Opt-in `--live-chain`; never default; orders still refuse |

---

## 6. Rejected / deferred (with why)

| Item | Status | Why |
|------|--------|-----|
| Live Dhan orders / `/alerts/orders` | **Rejected** | Hard stop until founder + gates + `RESEARCH_READY` |
| Promote / RESEARCH_READY | **Rejected** | NO_PROMOTE; books FAIL / UNVALIDATED |
| Fake win rates / edge claims | **Rejected** | Honesty mandate |
| Delete STRAT-001–014 | **Rejected** | KEEP_ALL |
| `--live-chain` as default | **Rejected** | Cost + isolation; opt-in only |
| `/desk` full UI wire | **Deferred** | Backlog UI-DESK-PAPER-AGENTS; CLI SoT |
| Depth / sub-second alpha | **Deferred / PARKED** | Decode DI |
| Broader paper eval / SCORE_SAMPLE fill | **Deferred** | Need NORMAL sessions + calendar |
| Auto-retune from EOD | **Rejected** | RETUNE_GATE |

---

## 7. Risks to profitability claims

- Paper ledger + LLM agreement ≠ edge. Confidence on `/` is **agreement**, not calibrated P(win).
- INDEX proxy premium leans are **HYPOTHESIS**; OPTIDX path only when live charts work.
- Weekend/holiday `--simulate` must not be narrated as “today’s market P/L.”
- RAG snippets are **untrusted context**; injection must not raise size or bypass risk veto.
- Default LLM raises **token cost** and failure modes — use `--no-llm` for pure rule path.
- Prior backtests (proxy, option premium, SL/TP, CF books, CLUB-GR after-cost) **do not promote**.

**Profitability honesty (Astra):** no demonstrated edge. Populate SCORE_SAMPLE only from reproducible labeled NORMAL runs; promotion remains prohibited.

---

## 8. How to run paper market-hours today (post-implement)

See runbook: [`PAPER_MARKET_HOURS_RUNBOOK.md`](PAPER_MARKET_HOURS_RUNBOOK.md).

```bash
# from repo root, venv with packages installed
python -m trading_agents_india clock
# Sunday / closed: simulate
python -m trading_agents_india market-hours --simulate --max-ticks 2 --stop-outside-shell
# Next NSE session (optional live *data*, still no orders):
python -m trading_agents_india market-hours --max-ticks 4 --live-chain --stop-outside-shell
# Force rules-only:
python -m trading_agents_india market-hours --simulate --no-llm --max-ticks 1
# EOD stub:
python -m agent_rag eod-recon --offline
```

---

## HANDOFF

```text
HANDOFF
From: 00 / Astra council (gpt-6-astra + gpt-4o)
To:   07 / 05 / 06 / 09
Accepted: Review doc; paper-today A/B/C/D/E/F/G/H + P0; LIVE refuse; KEEP_ALL; NO_PROMOTE.
Rejected: Live orders; promote; live-chain default; EOD clears BACKTEST_REQUIRED.
UNKNOWN: Live OPTIDX/chain quality today depends on tokens + exchange open.
```

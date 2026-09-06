# PLAN — Market-hours paper agents (build board)

**Date:** 2026-09-06  
**Status:** `PAPER_LOOP_SHIPPED` / **UNVALIDATED** / paper only  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Council:** [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md) — OpenAI `gpt-5.4` + 00 desk → **`APPROVE_WITH_GUARDRAILS`**  
**Adopt map:** [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md)  
**Package:** `packages/trading_agents_india` (+ `packages/agent_rag`, `packages/dhan-client`, `packages/desk-intel`)  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)

No live orders. No win rates. KEEP_ALL STRAT-001–014. Does **not** touch `transcripts.sqlite`.

### Phase close-out (2026-09-06) — three prior “still open” items

| # | Item | This-phase close | Status |
|---|------|------------------|--------|
| A | Continuous sub-second Dhan depth alpha | Honest park — no fake edge | **CLOSED:** `PARKED` / `DATA_INSUFFICIENT` (stub `hooks/depth.py`) |
| B | `/desk` UI wire for paper market-hours agents | Prefer CLI over half-broken UI | **CLOSED this phase** → use `market-hours` CLI; mock seed `apps/web/public/mock/paper_agents.json`; backlog **UI-DESK-PAPER-AGENTS** |
| C | Promote / research-ready | Explicit refuse | **CLOSED:** **`NO_PROMOTE`** until 06 OOS+`NORMAL` + 09 five-pass **passes** |

---

## Goal

From **09:00 IST** session shell, run a TradingAgents-style multi-persona graph that:

1. Reads **OPTIDX premium** charts + **option chain** (+ news hold).
2. Applies **fake-breakout guards** (`HYPOTHESIS`).
3. Shares structured **handoffs**; **trader alone** decides **paper** fills.
4. Persists to SQLite + recon; EOD reconcile under **RETUNE_GATE**; backtest rollups may be shared with OpenAI (**anonymized**, no fake wr).
5. Wires `/desk` (internal) — customer `/` stays ticket talk without indicator soup.

**LIVE** path exists only as **refuse** until founder allow + gate + `RESEARCH_READY`.

---

## Prioritized todos

### P0 — build first (implementation agents)

| # | Todo | Owner | Done when | Evidence / path |
|---|------|-------|-----------|-----------------|
| 1 | Session clock IST + dead-bands (HOLD-only) + tick 30–60s (default **45s**) | 00 / 07 | CLI `clock` + unit tests | `session_clock.py`, this PLAN |
| 2 | Market-hours poll loop (simulate + live-data dry) | 00 / 07 | `market-hours --simulate` works | `session_runner.py` |
| 3 | Data ingest hooks: OPTIDX premium, chain snapshot, index proxy DI | 05 / 07 | Fixtures when empty `DHAN_*`; live when tokens | `hooks/premium.py`, `hooks/chain.py`, `dhan-client` |
| 4 | Structured handoffs + boss brief | 00 | `AgentHandoff` between roles | `handoffs.py`, `schemas.py` |
| 5 | Paper ledger: trader-confirmed fills only; LIVE refuse | 07 / 08 | Ledger rows + refuse tests | `ledger.py`, `mode.py` |
| 6 | Fake-breakout guard flags (chain/premium) — no catalog deletes | 04 / 05 | Flags on handoff; DI if no OI | `hooks/chain.py` + docs |
| 7 | Strategy router cites STRAT-001–014 + MIX-DEFAULT-BUY + MIX-TA-* (KEEP_ALL) | 04 | Reasons cite IDs; no STRAT-015+ | `mix_inputs.py`, `MIX_CATALOG` §18 |

### P1 — next

| # | Todo | Owner | Done when | Phase note |
|---|------|-------|-----------|------------|
| 8 | Confirm-or-kill 5m ST/MACD/RSI on `/desk` only | 04 / 07 | Never on customer entry soup | Future backlog |
| 9 | RAG retrieval via `agent_rag` (FTS5) for personas | 01 / 05 | `python -m agent_rag query` used in session context | Skeleton done; deepen later |
| 10 | EOD recon job → `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` | 05 / 06 | `eod-recon` JSON + no auto-retune | **Done** (stub path) |
| 11 | Paper/backtest rollup + optional OpenAI review notes | 06 / 09 | `paper-backtest` + `NO_PROMOTE` default | **Done** — stamped **`NO_PROMOTE`** |
| 12 | Dashboard hooks: persona board, chain, blotter on `/desk` | 07 | Labeled PAPER/MOCK; no live fills | **CLOSED this phase** — backlog **UI-DESK-PAPER-AGENTS**; CLI is source of truth |

### P2 — docs / ops

| # | Todo | Owner | Done when | Phase note |
|---|------|-------|-----------|------------|
| 13 | Runbooks + CONTINUE_NEXT_CHAT pointer | 00 | Linked from ADOPT + CONTINUE | **Done** |
| 14 | Rate-limit runbook (chain 1/3s; charts 1/5s; quote 1/s) | 07 | Cite [`RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md) | Cite exists |
| 15 | WS full/depth decode VALIDATION (02/03) before any DI claim drop | 02 / 03 | Decode tests; else stay DI | **CLOSED this phase as PARKED / DI** — stub `hooks/depth.py`; reopen only after decode+history |

### Explicitly deferred / parked

- Live order routing / ExecutionClient enable.
- **Depth/orderbook alpha; tick microstructure** — **PARKED / DATA_INSUFFICIENT** (not “TODO open”).
- Auto-fill as truth; cross-broker adapters; news sentiment alpha.
- STRAT-015+; **promote** any MIX — **CLOSED: NO_PROMOTE** this phase (gate unchanged).

---

## Agent roster

Map OpenAI council names → runtime roles → coalition teams.

| Persona | Runtime role | Team | Job | Inputs | Outputs |
|---------|--------------|------|-----|--------|---------|
| OpenDrive | orchestrator / boss | 00 | Clock, gather handoffs, final paper brief | all notes, clock | club lean, handoff queue |
| QuantLens | technical + premium | 02 / 04 | Premium structure / regime | OPTIDX, index | setup lean, gaps |
| ChainWatch | chain_watcher | 05 | Chain / OI / PCR / fake-breakout flags | option_chain | bias, guards, DI |
| PriceAction | bull/bear debate | 04 | Trap / retest read | premium + index | zones, invalidation |
| RiskMarshal | risk_committee | 06 | Size/veto/cooldown | ledger, leans | HOLD / size cap |
| NewsHold | news_analyst | 05 | Event hold only | RSS / calendar | hold windows |
| ExecutionScribe | trader | 07 / 08 | **Only** paper fill decision + log | brief | `paper_ledger` |
| ResearchJudge | EOD / backtest | 06 / 09 | Recon + gates | ledger, history | recon, NO_PROMOTE |

Graph (sequential, TradingAgents-shaped):

```text
news → sentiment(DI) → technical/premium → chain_watcher
  → bull ↔ bear → boss → trader(paper) → risk → ledger
```

PhD math (02) and PhD market (03) are **validators** on packets and clocks — they do not place fills.

---

## Data objects

### OPTIDX premium

| Field | Notes |
|-------|--------|
| `ts_ist`, `symbol`, `expiry`, `strike`, `side` (CE/PE) | Contract id from instrument master — VERIFY |
| `ohlcv` | Prefer Dhan `/charts/intraday` on OPTIDX security id |
| `oi_if_avail` | DI if missing |
| Grain | 1m / 5m (intervals allowed: 1,5,15,25,60) |
| Fallback | INDEX proxy lean labeled **`HYPOTHESIS`** + `data_gaps` |

### Option chain

| Field | Notes |
|-------|--------|
| `ts_ist`, `underlying`, `expiry`, `strike` | Desk default full-chain poll **3m** |
| `ce_ltp` / `pe_ltp`, OI, OI chg, IV if present | Do not invent PCR law |
| Guards | Thin wall / fake breakout = **HYPOTHESIS** flags |
| Rate | Option-chain **1 unique request / 3s** — do not poll every tick |

### News

| Field | Notes |
|-------|--------|
| `ts_ist`, `source`, `headline`, `url`, `event_type` | Moneycontrol RSS via desk-intel; Dhan news API = DI if absent |
| Use | **Hold** customer/paper ticket — not entry alpha |

### Indexes

NIFTY / BANKNIFTY / SENSEX from `workspace.yaml` scrips (VERIFY FROM instrument master). Spot/fut refs for context only.

### Paper ledger

| Field | Notes |
|-------|--------|
| `trade_id`, `ts_signal`, `ts_fill`, `strategy_or_mix_id` | Cite MIX/STRAT; KEEP_ALL |
| `side` BUY_CE\|BUY_PE\|HOLD, `qty`, `entry`, `exit` | Paper only |
| `manual_by_trader` | Must be true for fills |
| `pnl`, `slippage_note`, `data_gaps` | Honest; no fake wr |
| Dual write | `trading_agents_india.sqlite` + `data/recon/paper_watch/{MIX-*}/YYYY-MM-DD.jsonl` |

---

## RAG / SQLite

| Store | Path | Role |
|-------|------|------|
| Paper sessions | `data/knowledge/trading_agents_india.sqlite` | Session rows, handoffs, ledger |
| Agent RAG (FTS5) | `data/knowledge/agent_rag.sqlite` | Fast MIX/STRAT/CF/ADOPT/paper lookup |
| Transcripts | `data/knowledge/transcripts.sqlite` | **NEVER WRITE / OVERWRITE** from this plan |

OpenAI suggested `data/rag/market_kb.sqlite` — **rejected**; reuse `agent_rag`.  
Embeddings/vector models: **optional later**; FTS5 is the speed path shipped ([`AGENT_RAG.md`](../../01_research/docs/AGENT_RAG.md)).

```bash
python -m agent_rag rebuild
python -m agent_rag query "fake breakout"
python -m trading_agents_india market-hours --simulate --max-ticks 2
```

---

## EOD recon

| When (IST) | Action |
|------------|--------|
| ~15:40 | Prelim freeze paper ledger (VERIFY close clock) |
| ~16:15 | Final match bars used at signal time; MAE/MFE if available |
| Nightly POST_MARKET | Tag `NEWS_DAY` / `EXPIRY` / `NORMAL`; emit `RETUNE_PROPOSAL` **`BACKTEST_REQUIRED`** |
| Optional | Anonymized summary → OpenAI review notes (09); **no auto-retune**; **no promote** |

Align [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) + [`EVENT_MEMORY.md`](../../06_backtesting/docs/EVENT_MEMORY.md).  
CLI: `python -m agent_rag eod-recon --day YYYY-MM-DD --offline` / `python -m desk_intel eod-recon`.

---

## Backtest gates

Promote / live discussion **only if all** hold:

1. Paper path only until founder + gate.
2. Honest costs/slippage; no hidden missing-data days.
3. Score on `NORMAL` OOS; news/expiry out of SCORE_SAMPLE (remember as analogs).
4. Regime breakdown, not aggregate wr cherry-pick.
5. 06 book pass + 09 five-pass — notes ≠ pass.
6. **No** invented win rates in UI or docs.

Share with OpenAI: anonymized rollups + DI list — for review, not as edge proof.  
Default stamp: **`NO_PROMOTE`**.

---

## Dashboard hooks

| Surface | Where | Content | Label |
|---------|-------|---------|-------|
| Persona board | `/desk` | Handoffs, disagreements, holds | PAPER — **not wired this phase** |
| Premium / chain | `/desk` | Selected CE/PE + chain guards | PAPER / DI — backlog |
| Trade blotter | `/desk` | Trader-confirmed paper fills | PAPER — backlog |
| Recon lab | `/desk` or recon MD/JSON | EOD scorecards | UNVALIDATED |
| Customer ticket | `/` | Trend + chain + news talk | No indicator soup; confidence ≠ wr |
| Mock seed (read-only) | `apps/web/public/mock/paper_agents.json` | Last-lean placeholder | MOCK / PAPER |

**Desk wire this phase:** **CLOSED**. Operator path = CLI `python -m trading_agents_india market-hours`. Backlog ticket **UI-DESK-PAPER-AGENTS** (CONTINUE). Do not show MOCK P/L as proven edge.

## Promote gate — **NO_PROMOTE** (closed this phase)

Default stamp remains **`NO_PROMOTE`**. Do **not** set `RESEARCH_READY_FOR_PROGRAMMING`. Re-open promote discussion only after **06 OOS + `NORMAL` score pass** and **09 five-pass passes** (notes ≠ pass).

---

## Depth interest (honest DI) — **PARKED this phase**

| Claim | Status |
|-------|--------|
| Sub-second tape for paper guards | **PARKED** — not claimed |
| Documented packets | ticker / quote / full (see Dhan Live Market Feed docs) — **exist as docs** |
| Repo | `dhan_client.decode`: ticker OK; quote/full/depth **placeholder** |
| Package stub | `packages/trading_agents_india` `hooks/depth.py` → always `DATA_INSUFFICIENT`, `claims_alpha=False` |
| Build rule | Persist raw experimental packets separately; **exclude from alpha + promote** until 02/03 VALIDATION + history replay |
| Not default | Do not block paper loop on depth — use charts + 3m chain + quote REST |
| Unblock when | Decode offsets proven in tests **and** replayable history exists — until then stay DI |

---

## Session clock (IST) — locked for implementers

| Window | Behavior |
|--------|----------|
| 09:00–09:30 | Session shell; **HOLD only** (dead-band) |
| 09:30–15:00 | Active paper window — CE/PE paper leans allowed |
| 15:00–15:30 | Dead-band (CAS) → **HOLD only** |
| else / weekend | Outside shell → no directional paper |

Tick default **45s** (allowed 30–60s). Path to **15s** documented only after chain budget + graph cost allow — **not default**.

---

## CLI (current skeleton)

```bash
python -m trading_agents_india session --dry-run
python -m trading_agents_india market-hours --simulate --max-ticks 2
python -m trading_agents_india market-hours --tick-seconds 45 --max-ticks 8
python -m trading_agents_india clock
python -m trading_agents_india session --mode LIVE   # refuses
python -m agent_rag rebuild && python -m agent_rag query "MIX-TA"
```

---

## MIX (paper-watch only)

- `MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY` ([`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) §18)
- Optional ledger tag: **`MIX-TA-MARKET-HOURS`** (`PAPER_WATCH`, not default, not promote)
- Customer default playbook remains **`MIX-DEFAULT-BUY`** until a real promote

---

## HANDOFF (for next implementation agents)

**This phase closed (2026-09-06):**

1. Depth alpha → **PARKED / DI** (`hooks/depth.py`).
2. `/desk` paper agents wire → **CLOSED**; CLI + mock JSON seed; backlog **UI-DESK-PAPER-AGENTS**.
3. Promote → **NO_PROMOTE** until OOS+`NORMAL` + five-pass.

**Still useful next (true backlog only):**

1. IST session with `DHAN_*` data-only: `market-hours` (not simulate) when founder asks.
2. **UI-DESK-PAPER-AGENTS** — wire `/desk` to paper ledger / `paper_agents.json` when asked (no npm restart until asked).
3. Decode VALIDATION (02/03) before ever un-parking depth.
4. CF fail=30 ASR + Phase-11 bind (separate track).

**Do not:** full live engine, invent depth edge, half-wire `/desk`, overwrite transcripts KB, invent wr, restart npm unless founder asks, set RESEARCH_READY.

**Accepted:** Council `APPROVE_WITH_GUARDRAILS`; PAPER market-hours loop; DI depth park; reuse agent_rag; explicit NO_PROMOTE.  
**Rejected:** Live unlock; auto-fills; depth-as-edge; promote from thin paper.  
**UNKNOWN / DI:** OPTIDX history completeness; WS full/depth offsets; EVENT_MEMORY empty; India sentiment SOURCE_FACT.

After edits to this PLAN / council / ADOPT / CONTINUE: run `python -m docs_auditor`.

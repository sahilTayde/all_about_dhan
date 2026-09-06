# PLAN — Market-hours paper agents (build board)

**Date:** 2026-09-06  
**Status:** `SKELETON_IN_PROGRESS` / **UNVALIDATED** / paper only  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Council:** [`OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md`](OPENAI_MARKET_HOURS_PAPER_COUNCIL_2026-09-06.md) — OpenAI `gpt-5.4` + 00 desk → **`APPROVE_WITH_GUARDRAILS`**  
**Adopt map:** [`ADOPT_TRADINGAGENTS.md`](ADOPT_TRADINGAGENTS.md)  
**Package:** `packages/trading_agents_india` (+ `packages/agent_rag`, `packages/dhan-client`, `packages/desk-intel`)  
**EXTERNAL:** [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (Apache-2.0)

No live orders. No win rates. KEEP_ALL STRAT-001–014. Does **not** touch `transcripts.sqlite`.

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

| # | Todo | Owner | Done when |
|---|------|-------|-----------|
| 8 | Confirm-or-kill 5m ST/MACD/RSI on `/desk` only | 04 / 07 | Never on customer entry soup |
| 9 | RAG retrieval via `agent_rag` (FTS5) for personas | 01 / 05 | `python -m agent_rag query` used in session context |
| 10 | EOD recon job → `RETUNE_PROPOSAL` `BACKTEST_REQUIRED` | 05 / 06 | `eod-recon` JSON + no auto-retune |
| 11 | Paper/backtest rollup + optional OpenAI review notes | 06 / 09 | `paper-backtest` + `NO_PROMOTE` default |
| 12 | Dashboard hooks: persona board, chain, blotter on `/desk` | 07 | Labeled PAPER/MOCK; no live fills |

### P2 — docs / ops

| # | Todo | Owner | Done when |
|---|------|-------|-----------|
| 13 | Runbooks + CONTINUE_NEXT_CHAT pointer | 00 | Linked from ADOPT + CONTINUE |
| 14 | Rate-limit runbook (chain 1/3s; charts 1/5s; quote 1/s) | 07 | Cite [`RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md) |
| 15 | WS full/depth decode VALIDATION (02/03) before any DI claim drop | 02 / 03 | Decode tests; else stay DI |

### Explicitly deferred

- Live order routing / ExecutionClient enable.
- Depth/orderbook alpha; tick microstructure models.
- Auto-fill as truth; cross-broker adapters; news sentiment alpha.
- STRAT-015+; promote any MIX from thin paper samples.

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
| Persona board | `/desk` | Handoffs, disagreements, holds | PAPER |
| Premium / chain | `/desk` | Selected CE/PE + chain guards | PAPER / DI |
| Trade blotter | `/desk` | Trader-confirmed paper fills | PAPER |
| Recon lab | `/desk` or recon MD/JSON | EOD scorecards | UNVALIDATED |
| Customer ticket | `/` | Trend + chain + news talk | No indicator soup; confidence ≠ wr |

Do not show MOCK P/L as proven edge.

---

## Depth interest (honest DI)

| Claim | Status |
|-------|--------|
| Sub-second tape for paper guards | **Only** if using Dhan Live Market Feed WS |
| Documented packets | ticker / quote / full (see Dhan docs) |
| Repo | `dhan_client.decode`: ticker OK; quote/full/depth **placeholder** |
| Build rule | Persist raw experimental packets separately; **exclude from alpha + promote** until 02/03 VALIDATION |
| Not default | Do not block P0 on depth — use charts + 3m chain + quote REST |

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

**Build first (in order):**

1. Harden clock + market-hours loop tests (simulate).
2. Finish premium + chain hooks with explicit `SOURCE_FACT` / `HYPOTHESIS` / `DATA_INSUFFICIENT` layers.
3. Trader-only paper ledger API + refuse LIVE.
4. Wire persona handoffs → boss brief → blotter.
5. Hook `agent_rag` retrieval into session context (read-only).
6. EOD recon + paper-backtest rollup stamped `NO_PROMOTE`.
7. `/desk` surfaces last (after ledger exists).

**Do not in this pass:** full live engine, depth alpha, STRAT deletes, overwrite transcripts KB, invent wr, restart npm unless founder asks.

**Accepted:** Council `APPROVE_WITH_GUARDRAILS`; PAPER market-hours plan; DI depth; reuse agent_rag.  
**Rejected:** Live unlock; auto-fills; second RAG path invent; depth-as-edge.  
**UNKNOWN / DI:** OPTIDX history completeness; WS full/depth offsets; EVENT_MEMORY empty; India sentiment SOURCE_FACT.

After edits to this PLAN / council / ADOPT: run `python -m docs_auditor`.

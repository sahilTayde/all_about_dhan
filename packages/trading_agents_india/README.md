# trading_agents_india

Local multi-agent **paper** signal orchestration for NIFTY / BANKNIFTY / SENSEX CE/PE **buy-first**.

Inspired by [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (**Apache-2.0** EXTERNAL reference).  
Adapted for this monorepo’s coalition (`teams/00–09`), KEEP_ALL STRAT-001–014, and DhanHQ-only desk rules.

**Not** financial advice. **No live orders.** Gate is **not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Mode:** `PAPER` (default) | `LIVE` (always refuses; DhanHQ stub only).

## Install

```bash
# from repo root
pip install -e packages/trading_agents_india
# optional LLM path
pip install -e "packages/trading_agents_india[openai]"
```

## Run (dry / paper)

```bash
python -m trading_agents_india session --dry-run
python -m trading_agents_india session --dry-run --underlying NIFTY
python -m trading_agents_india session --mode PAPER --gather-news
python -m trading_agents_india session --mode LIVE              # refuses orders
python -m trading_agents_india market-hours --simulate --max-ticks 2
python -m trading_agents_india market-hours --tick-seconds 45 --max-ticks 4
python -m trading_agents_india clock
python -m trading_agents_india session --dry-run --use-llm      # needs OPENAI_API_KEY
python -m trading_agents_india personas
python -m trading_agents_india review-plan
```

## KB + ledger

Creates **`data/knowledge/trading_agents_india.sqlite`** on first run.  
Market-hours ticks also append **`data/recon/paper_watch/MIX-*/YYYY-MM-DD.jsonl`**.  
Does **not** modify `data/knowledge/transcripts.sqlite`.

## Paper-watch MIX (not default)

`MIX-TA-FLOW-RISK`, `MIX-TA-EVENT-HOLD`, `MIX-TA-EXEC-SANITY`, `MIX-TA-MARKET-HOURS` — see MIX_CATALOG §18.

## Depth / sub-second tape — **PARKED / DATA_INSUFFICIENT**

Dhan Live Market Feed **docs** cover ticker / quote / full packets. In-repo `dhan_client.decode`: ticker OK; quote/full/depth still **placeholder**.

This package exposes `hooks/depth.py` → always returns `DATA_INSUFFICIENT` with `claims_alpha=False`.  
**We will not claim** continuous depth alpha until decode offsets are validated (02/03) **and** history replay exists. Market-hours paper does **not** depend on depth.

## `/desk` wire — **CLOSED this phase**

Operator path: CLI above (`market-hours`). Read-only mock seed (not a live wire): `apps/web/public/mock/paper_agents.json`.  
UI backlog: **UI-DESK-PAPER-AGENTS** in [`CONTINUE_NEXT_CHAT.md`](../../teams/00_orchestrator/docs/CONTINUE_NEXT_CHAT.md). Do not restart npm for this.

## Promote — **NO_PROMOTE**

Paper rollups stay **`NO_PROMOTE`**. Not `RESEARCH_READY_FOR_PROGRAMMING` until 06 OOS+`NORMAL` + 09 five-pass **passes**.

## Mapping

See [`teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md`](../../teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md)  
and [`OPENAI_DESIGN_COUNCIL_2026-09-06.md`](../../teams/00_orchestrator/docs/OPENAI_DESIGN_COUNCIL_2026-09-06.md).

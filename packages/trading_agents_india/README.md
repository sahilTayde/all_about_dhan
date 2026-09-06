# trading_agents_india

Local multi-agent **paper** signal orchestration for NIFTY / BANKNIFTY / SENSEX CE/PE **buy-first**.

Inspired by [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (**Apache-2.0** EXTERNAL reference).  
Adapted for this monorepo’s coalition (`teams/00–09`), KEEP_ALL STRAT-001–014, and DhanHQ-only desk rules.

**Not** financial advice. **No live orders.** Gate is **not** `RESEARCH_READY_FOR_PROGRAMMING`.

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
python -m trading_agents_india session --dry-run --use-llm   # needs OPENAI_API_KEY; else honest fallback
python -m trading_agents_india review-plan                  # frontier design review notes helper
```

## KB

Creates **`data/knowledge/trading_agents_india.sqlite`** on first run.  
Does **not** modify `data/knowledge/transcripts.sqlite`.

## Mapping

See [`teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md`](../../teams/00_orchestrator/docs/ADOPT_TRADINGAGENTS.md).

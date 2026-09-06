# Team 04 — Quant

## Mission

Turn validated concepts into **explicit, testable hypotheses** and strategy specs for NIFTY, BANKNIFTY, and SENSEX index options (CE/PE buy first). Mark every hypothesis `UNVALIDATED` until backtest + review. Do not claim profitability. Do not implement execution.

## In artifacts

- `SOURCE_FACT` + `VALIDATION` from teams 01–03
- Charter: [`docs/RESEARCH.md`](../../docs/RESEARCH.md)

## Out artifacts

- Strategy / hypothesis specs under `teams/04_quant/docs/` and later `src/`
- Handoff to 06_backtesting (`BACKTEST_PENDING`)
- Never skip to 07_coding

## Owned paths

- `teams/04_quant/**`

## Do not own

- `teams/06_backtesting/**` (engine and runs)
- `apps/**` (product)
- `packages/dhan-client/**`
- Live or paper order placement

## Current status

v0.1 DRAFT specs: [`docs/MASTER_STRATEGY_PLAN.md`](docs/MASTER_STRATEGY_PLAN.md) + `docs/candidates/STRAT-001`–`014` (**DRAFT; no win rates**). Algo YAML (later engine, **do not code**): [`docs/ALGO_HANDOFF.md`](docs/ALGO_HANDOFF.md). Coalition ticket: [`TASK_TRANSCRIPT_COALITION.md`](../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md). Per-topic stubs: [`docs/topics/`](docs/topics/) (each cites official Dhan indicator defs). Staging: [`docs/SIGNAL_STAGING.md`](docs/SIGNAL_STAGING.md) (`WAITING_FOR_EDIT`, includes **IN-PROGRESS** + outcomes). Paper daily + pre-prod recon is **06/desk-intel**, not a live rewrite here. All `UNVALIDATED`. Do not implement.

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English; SOURCE_FACT still partial. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/`: ticket + **IN-PROGRESS** + CasPanel; book P/L **MOCK**. Internal `/desk`. Chain **3m**. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED** — do not retune STRAT-* from mock JSON. CAS = Closing Auction Session. **STRAT-001–014 UNVALIDATED** / DRAFT; no win rates. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

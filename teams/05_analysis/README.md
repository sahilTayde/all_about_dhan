# Team 05 — Analysis

## Mission

Scorecards, ablation, comparison, missed-signal tracking. Rank by **risk-adjusted robustness**, not headline return. Consume backtest and paper outputs; do not own the backtest engine.

Also owns **desk intelligence** (PRE_MARKET news + VERIFY tape + Dhan option-chain fusion → `MARKET_SIGNAL` bias; POST_MARKET nightly paper/shadow recon). That is a risk-regime overlay, not a coded strategy and not advice. Ticket: [`TASK_PRE_POST_MARKET_JOBS.md`](../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md).

## In artifacts

- Backtest reports from `teams/06_backtesting/`
- Paper/live audit logs (later, from apps)
- RSS / official news via `config/workspace.yaml` `sources.news[]`
- Option-chain snapshots via `packages/dhan-client`

## Out artifacts

- Comparison notes and scorecards under `teams/05_analysis/docs/`
- Desk intel how-to: [`docs/DESK_INTELLIGENCE.md`](docs/DESK_INTELLIGENCE.md)
- Handoff to 09_review

## Owned paths

- `teams/05_analysis/**`
- `packages/desk-intel/**` (news ingest, chain poller, fusion, CLI)

## Do not own

- `teams/06_backtesting/**` (engine)
- `teams/04_quant/**` (specs)
- `apps/**` (UI)
- `packages/dhan-client/**` (REST/WS)

## Current status

Desk intel skeleton **dry-run ready** (morning + pre/post jobs). Tickets: `TASK_DESK_INTELLIGENCE.md`, `TASK_CUSTOMER_DESK.md` (**3m** chain + last snapshot), `TASK_PRE_POST_MARKET_JOBS.md`. No orders. `apps/api` `/paper/signal` still mock.

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. News/chain URLs in [`config/workspace.yaml`](../../config/workspace.yaml). Dhan **dry-run, no orders**. Full chain default **3m** + last snapshot. Customer `/`: ticket + **IN-PROGRESS** + CasPanel; book P/L **MOCK**. Internal `/desk`. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. CAS = Closing Auction Session (`cas_calls[]`). STRATs **UNVALIDATED**. `MARKET_SIGNAL` is overlay only — not a coded strategy. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

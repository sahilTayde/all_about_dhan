# Team 00 — Orchestrator

## Mission

Keep the company SDLC honest: allocate work, copy task-board notes here, and route agents to one team folder. Does not implement scrapers, strategies, or apps.

## In artifacts

- User decisions, blockers, credential status (names only)
- Handoffs that need a gate decision

## Out artifacts

- Task allocation notes under `teams/00_orchestrator/docs/`
- Updates to root [`AGENT.md`](../../AGENT.md) and [`PLAN.md`](../../PLAN.md) (company board only)

## Owned paths

- `teams/00_orchestrator/**`
- Root orchestrator docs (edit with care): `AGENT.md`, `PLAN.md`, `docs/INDEX.md`, `docs/SDLC.md`, `docs/HANDOFF.md`, `docs/MASTER_REQUIREMENTS.md`
- Customer master config (edit with care): `config/workspace.yaml`

## Do not own

- `teams/01_research/youtube/**` (research)
- `apps/**`, `packages/**` (coding / shared libs)
- `secrets/`, `.env` (never commit; see `docs/SECURITY.md`)

## Current status

Collector has run; first research DRAFT written. Desk intel + PRE/POST jobs skeleton (`packages/desk-intel`). Paper desk mock shows lifecycle outcomes — not live Dhan. **New chat:** [`docs/CONTINUE_NEXT_CHAT.md`](docs/CONTINUE_NEXT_CHAT.md). See [`docs/STATUS.md`](docs/STATUS.md) and [`docs/HANDOFF_TOMORROW.md`](docs/HANDOFF_TOMORROW.md) (2026-09-01 history). Keep `TASK_STAGED_SIGNALS` docs-only for live Dhan. Tickets: [`docs/TASK_DESK_INTELLIGENCE.md`](docs/TASK_DESK_INTELLIGENCE.md), [`docs/TASK_CUSTOMER_DESK.md`](docs/TASK_CUSTOMER_DESK.md), [`docs/TASK_PRE_POST_MARKET_JOBS.md`](docs/TASK_PRE_POST_MARKET_JOBS.md), [`docs/TASK_RETUNE_GATE.md`](docs/TASK_RETUNE_GATE.md), [`docs/TASK_STAGED_SIGNALS.md`](docs/TASK_STAGED_SIGNALS.md) (`IN_PROGRESS`; live token **TODO`), [`docs/TASK_CAS_ANALYST.md`](docs/TASK_CAS_ANALYST.md) (`IN_PROGRESS`; Closing Auction Session), [`docs/TASK_DOCS_AUDITOR.md`](docs/TASK_DOCS_AUDITOR.md) (standing; `python -m docs_auditor`), [`docs/TASK_TRANSCRIPT_COALITION.md`](docs/TASK_TRANSCRIPT_COALITION.md) (`IN_PROGRESS`; 14 STRATs stay UNVALIDATED). Score: [`docs/MASTER_REQUIREMENTS.md`](../../docs/MASTER_REQUIREMENTS.md).

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. Customer switch: [`config/workspace.yaml`](../../config/workspace.yaml). Dhan **dry-run, no orders**. Customer `/`: ticket + **IN-PROGRESS** + **CasPanel**; book P/L **MOCK**. Internal **`/desk`**. Chain **3m**. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. CAS = **Closing Auction Session**. STRATs **UNVALIDATED**. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

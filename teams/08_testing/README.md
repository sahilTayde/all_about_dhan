# Team 08 — Testing

## Mission

QA the product: fixtures, regression, paper-trade checks, “did we record MTM when the user skipped the trade?” Does not invent strategies. Tests live behavior of `apps/` and `packages/`.

## In artifacts

- Builds from 07_coding
- Signal/audit schemas from `packages/contracts`

## Out artifacts

- Test notes and later test trees under `teams/08_testing/`
- Failures handed back to 07_coding

## Owned paths

- `teams/08_testing/**`

## Do not own

- Feature implementation (`apps/**`, `packages/**`) — tests may *import* them
- Research extraction (`teams/01_research/**`)

## Current status

Phase 0 stub. Desk-intel smoke: `packages/desk-intel/tests/test_lifecycle_smoke.py` (outcome enum + recon keys). **Not** a full pytest suite.

### Prerequisites / TODOs (automation later)

| Need | Where |
|------|--------|
| Fixtures | `python -m desk_intel morning --offline` and `python -m desk_intel nightly --offline`. Chain/news/GIFT fixtures; empty `DHAN_*` OK. |
| Nightly JSON schema | `desk_intel.nightly.RECON_JSON_KEYS`. File `data/recon/YYYY-MM-DD.json`. Includes `session_kind` + `retune_proposal` (`BACKTEST_REQUIRED`) + `cas_calls`. |
| Took-trade body | `POST /signals/{id}/took-trade` may include `lots`, `spot`, `reported_pnl` (optional). |
| Stale CONFIRMED | Assert `still_valid` is false when `outcome` is INVALIDATED/ACHIEVED/STOPPED/EXPIRED/LOST/COMPLETED/SHADOW_CLOSED. |
| Full suite | **TODO** — paper-trade checks, “did we record MTM when the user skipped?”, UI stillValid. Do not block on writing it in this ticket. |

Ticket: [`TASK_PRE_POST_MARKET_JOBS.md`](../00_orchestrator/docs/TASK_PRE_POST_MARKET_JOBS.md).

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/` fixtures: NIFTY **IN-PROGRESS**, BANKNIFTY ACHIEVED, SENSEX INVALIDATED; book P/L **MOCK**. Internal `/desk`. Chain **3m**. Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED** + `cas_calls[]`. CAS = Closing Auction Session. STRATs **UNVALIDATED**. Automate WATCH → EARLY → CONFIRMED → IN-PROGRESS → terminal outcomes; skip = shadow paper. Do not implement `apps/` features here. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

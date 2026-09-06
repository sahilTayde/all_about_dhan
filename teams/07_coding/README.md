# Team 07 — Coding

## Mission

Implement **product** code only after `RESEARCH_READY_FOR_PROGRAMMING`. Real apps live in `/apps`; shared libs in `/packages`. This folder holds pointers, implementation notes, and coding-task copies — not research notebooks.

## In artifacts

- Review-passed packets from `teams/09_review/`
- Specs from `teams/04_quant/` (read-only)

## Out artifacts

- `apps/api`, `apps/web`
- Shared packages (except treat `packages/dhan-client` as its own API/token surface)

## Owned paths

- `teams/07_coding/**` (pointers and notes)
- `apps/api/**`
- `apps/web/**`
- `packages/contracts/**`
- `packages/indicators/**`

## Do not own

- `teams/01_research/**` (do not scrape from here)
- `packages/dhan-client/**` (token/API agent; coding may *use* it)
- Research corpora under `data/`

## Current status

- **Customer desk `/`** in [`apps/web`](../../apps/web): ticket + **IN-PROGRESS** + **CasPanel**; book P/L labeled **MOCK**. No Dhan in the browser. No strategy logic.
- **Internal `/desk`**: research view (honesty stages, indicator lights). **Not** the customer product. How to run: [`apps/web/README.md`](../../apps/web/README.md) — **do not restart npm until asked**.
- FastAPI skeleton in [`apps/api`](../../apps/api): `/health`, `/paper/signal`, optional `/ws/feed`. Dry-run; orders refused.

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/` vs **`/desk`**. Mock tabs: NIFTY **IN-PROGRESS**, BANKNIFTY ACHIEVED, SENSEX INVALIDATED. Keep **CasPanel** on the customer page. Chain **3m** (desk-intel). Nightly `RETUNE_PROPOSAL` **BACKTEST_REQUIRED**. CAS = Closing Auction Session. STRATs **UNVALIDATED**. Book P/L is **MOCK**. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

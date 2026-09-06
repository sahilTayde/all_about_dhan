# Team 03 — PhD market

## Mission

Independently validate **market microstructure and contract facts**: NSE vs BSE, NIFTY/BANKNIFTY/SENSEX rules, lots, expiries, trading hours, liquidity, index vs options vs futures. SENSEX needs BSE-specific handling. Never hardcode current lot sizes as historical truth.

## In artifacts

- `SOURCE_FACT` packets from `teams/01_research/`
- Exchange / DhanHQ documentation links (not secrets)

## Out artifacts

- `VALIDATION` notes (market layer) under `teams/03_phd_market/docs/` — coalition clocks: [`docs/TRANSCRIPT_MARKET_NOTES.md`](docs/TRANSCRIPT_MARKET_NOTES.md); rolling OPTIDX history: [`docs/ROLLING_OPTION.md`](docs/ROLLING_OPTION.md)
- Handoff to 04_quant (with 02_phd_math)

## Owned paths

- `teams/03_phd_market/**` including **CAS analyst** `teams/03_phd_market/cas/` (Closing Auction Session — not PCA)

## Do not own

- Indicator math proofs (`teams/02_phd_math/**`)
- YouTube scraper (`teams/01_research/youtube/**`)
- `packages/dhan-client/**` (token/API implementation)
- Strategy code or UI

## Current status

Partial DRAFT: [`docs/VALIDATION_MARKET.md`](docs/VALIDATION_MARKET.md), [`docs/DESK_EXECUTION_NOTES.md`](docs/DESK_EXECUTION_NOTES.md), [`docs/CHAIN_METRICS.md`](docs/CHAIN_METRICS.md) (PCR / OI / max-pain stubs for desk intel). Lots/session VERIFY — never hardcode.

**CAS special analyst:** [`cas/README.md`](cas/README.md) — official **Closing Auction Session** (NSE/BSE, live 3 Aug 2026). Daily `BOUNCE/SIDEWAYS/FALL` + `UNVALIDATED`. Nightly `cas_calls[]`. Ticket [`TASK_CAS_ANALYST.md`](../00_orchestrator/docs/TASK_CAS_ANALYST.md).

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. `config/workspace.yaml` holds CAS / pre-open URLs. Dhan **dry-run, no orders**. Customer `/`: ticket + **IN-PROGRESS** + **CasPanel**; book P/L **MOCK**. Internal `/desk`. Chain **3m**. Nightly `cas_calls[]` retune **BACKTEST_REQUIRED**. CAS = **Closing Auction Session** (not PCA). Daily book **UNVALIDATED** / `DATA_INSUFFICIENT`. STRATs **UNVALIDATED**. Lots/session still VERIFY. No live tape from this folder. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

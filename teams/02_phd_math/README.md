# Team 02 — PhD math

## Mission

Independently validate **mathematics** of extracted concepts: indicator definitions, Greeks, IV, statistical claims. Record supported / partially supported / context-dependent / unsupported. Do not rewrite Dhan’s claim to make it look correct. Do not backtest.

## In artifacts

- `SOURCE_FACT` packets from `teams/01_research/` (video id, timestamp, quote)

## Out artifacts

- `VALIDATION` notes (math layer) under `teams/02_phd_math/docs/`
- Handoff to 04_quant (with 03_phd_market) when math status is set

## Owned paths

- `teams/02_phd_math/**`

## Do not own

- Transcript collection (`teams/01_research/**`)
- Exchange/contract rules (`teams/03_phd_market/**`)
- Strategy specs (`teams/04_quant/**`)
- `apps/**`, `packages/**`

## Current status

Partial DRAFT: [`docs/VALIDATION_MATH.md`](docs/VALIDATION_MATH.md). Official token map: [`docs/DHAN_INDICATOR_API_MAP.md`](docs/DHAN_INDICATOR_API_MAP.md). Option-premium charter (rollingoption vs INDEX 3m leans, **not a run**): [`docs/OPTION_PREMIUM_VALIDATION.md`](docs/OPTION_PREMIUM_VALIDATION.md). PROJECT_MIX books charter (`MIX-MTF-TREND`, `MIX-CONFIRM-5M`, **not a run**): [`docs/MIX_PROJECT_VALIDATION.md`](docs/MIX_PROJECT_VALIDATION.md). WEB/PATTERN scan charter (expanding windows, **not a run**): [`docs/MIX_SCAN_VALIDATION.md`](docs/MIX_SCAN_VALIDATION.md). Nightly recon handoffs (paper/shadow, **REVIEW not auto-apply**): `docs/handoffs/NIGHTLY_YYYY-MM-DD.md` after `python -m desk_intel nightly --offline`. See [`docs/handoffs/README.md`](docs/handoffs/README.md). Concepts only; no strategy P&L. Retune gate: [`teams/06_backtesting/docs/RETUNE_GATE.md`](../06_backtesting/docs/RETUNE_GATE.md).

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English; SOURCE_FACT still partial. `config/workspace.yaml` is the customer switch. Dhan **dry-run, no orders**. Customer `/` book P/L is **MOCK**; NIFTY **IN-PROGRESS** is UI only. Nightly packet is **REVIEW**; `RETUNE_PROPOSAL` is **BACKTEST_REQUIRED** — do not auto-apply. CAS = Closing Auction Session (`cas_calls[]` UNVALIDATED). STRATs **UNVALIDATED**. Supertrend/RSI/MACD/EMA9 remain OHLC-computed, not REST. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

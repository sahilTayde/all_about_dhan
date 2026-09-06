# Team 01 — Research

## Mission

Discover and extract YouTube per [`config/workspace.yaml`](../../config/workspace.yaml): catalog, popularity/relevance filters, public transcripts, `SOURCE_FACT` records. Default enabled source is official `@DhanHQ`. No independent “proof,” no strategy code. Non-Dhan channels are `EXTERNAL_RESEARCH` and stay disabled until the customer enables them.

Day-to-day extraction: [`youtube/ANALYSIS.md`](youtube/ANALYSIS.md). Topic clustering: [`docs/TOPIC_STRATEGY_PIPELINE.md`](docs/TOPIC_STRATEGY_PIPELINE.md). Official HQ indicators: [`docs/DHAN_OFFICIAL_INDICATORS.md`](docs/DHAN_OFFICIAL_INDICATORS.md). Full spec (Codex, verbatim): [`youtube/PLAN.md`](youtube/PLAN.md). Collector: [`youtube/src/README.md`](youtube/src/README.md).

## In artifacts

- `YOUTUBE_API_KEY` in repo-root `.env` (not in git). How-to: [`youtube/README.md`](youtube/README.md)
- Channel URLs / enabled flags: [`config/workspace.yaml`](../../config/workspace.yaml) (default [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ))

## Out artifacts

- Catalog / playlist dumps → `data/youtube/` (gitignored payloads)
- Transcripts → `data/transcripts/` (gitignored payloads)
- Extraction notes → `teams/01_research/docs/`
- Handoff to 02_phd_math and 03_phd_market with `SOURCE_FACT` only

## Owned paths

- `teams/01_research/**`
- `teams/01_research/youtube/**` (plan + future scraper)
- `data/youtube/**` (payloads)
- `data/transcripts/**` (payloads)

## Do not own

- `packages/dhan-client/**`, `apps/**`
- `teams/04_quant/**`, `teams/06_backtesting/**`
- Validation (`VALIDATION`) and hypotheses (`HYPOTHESIS`) — those are other teams

## Current status

Collector + SOURCE_FACT DRAFT: `docs/handoffs/` ([`OPTIONS_INDEX_PACKET.md`](docs/handoffs/OPTIONS_INDEX_PACKET.md) + [`EQUITY_ETF_PACKET.md`](docs/handoffs/EQUITY_ETF_PACKET.md) 2026-09-03). See [`HANDOFF.md`](HANDOFF.md). **45** `TRANSCRIPT_VERIFIED` + **45** English on disk. OPTIONS_INDEX + remaining verified-EN equity extract **done**. Catalog `STOCK_ONLY` **9** still no EN.

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English (`tlang=en`; no LLM). Channels from [`config/workspace.yaml`](../../config/workspace.yaml). Dhan **dry-run, no orders** from this folder. Customer `/` ticket + **IN-PROGRESS** + CasPanel and book P/L are **MOCK** — not transcript evidence. Chain **3m** and nightly `BACKTEST_REQUIRED` are other teams. CAS = Closing Auction Session. STRATs **UNVALIDATED**. Catalog `STOCK_ONLY` titles still lack English. Still **not** `RESEARCH_READY_FOR_PROGRAMMING`.

# Team 09 — Review

## Mission

Five-pass review + red-team **before any coding of a strategy**. Issue `RESEARCH_READY_FOR_PROGRAMMING` or `FAILED REVIEW`. Checklist: [`docs/REVIEW.md`](../../docs/REVIEW.md).

## In artifacts

- Research + validation + specs + backtest/analysis packets from teams 01–06

## Out artifacts

- Verdicts under `teams/09_review/docs/`
- Coalition notes (not a pass): [`docs/COALITION_REVIEW.md`](docs/COALITION_REVIEW.md)
- Option-premium five-pass **template** (NOTES_ONLY, gate **not** set): [`docs/BACKTEST_OPTION_REVIEW_TEMPLATE.md`](docs/BACKTEST_OPTION_REVIEW_TEMPLATE.md)
- Handoff to 07_coding only on pass

## Owned paths

- `teams/09_review/**`
- Charter ownership (with orchestrator): `docs/REVIEW.md`

## Do not own

- Implementing the strategy or UI
- Changing transcripts to “fix” a fail — send back to 01_research

## Current status

Open issues only: [`docs/RESEARCH_REVIEW_NOTES.md`](docs/RESEARCH_REVIEW_NOTES.md). Missed-trade notes: [`docs/MISSED_TRADE_POSTMORTEM.md`](docs/MISSED_TRADE_POSTMORTEM.md). Standing Docs Auditor: [`docs/DOCS_AUDITOR.md`](docs/DOCS_AUDITOR.md) — `python -m docs_auditor` after requirement changes and nightly. **No pass.**

## As of now (2026-09-01) / your prerequisite

YouTube **45** verified + **45** English. `config/workspace.yaml`. Dhan **dry-run, no orders**. Customer `/` ticket + **IN-PROGRESS** + CasPanel; book P/L **MOCK** — **not** a five-pass. Internal `/desk`. Chain **3m**. Nightly `BACKTEST_REQUIRED` is a queue, not a promote. CAS = Closing Auction Session. STRATs **UNVALIDATED**. Keep postmortem notes-only. Do not issue `RESEARCH_READY_FOR_PROGRAMMING` from mock JSON.

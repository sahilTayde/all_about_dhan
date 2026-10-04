# TASK — V2 shadow launcher + fail-closed safety

**Date opened:** 2026-10-04  
**Assigned:** 07_coding (`packages/shadow`, `scripts/desk.sh`) · 00_orchestrator (this ticket) · 09_review (docs auditor after HANDOFF)  
**Status:** `IN_PROGRESS` / **PAPER** / **NO_PROMOTE**  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. Do not enable `ExecutionClient`. Do not construct `DhanBroker`.

## Requirement

Run the V2 paper engine **beside** the legacy dual-tape desk. Legacy keeps the live paper book every session night. V2 shadow logs parallel decisions / P&L under `data/shadow/v2/` for a daily compare.

- Paper only. Never live orders. Never Dhan execution.
- Optional, non-blocking `desk.sh` hooks: `shadow-start` / `shadow-status` / `shadow-stop`.
- Fail closed if the tape is missing or V2 dies. Do not share a broker with the live paper path.
- Do not copy legacy `CANCEL` / `COVER_LONG_UNWIND` exits. Those stay the comparison baseline.
- Mac: `.venv-v2` (3.11+) for V2; `.venv` stays the legacy desk.

## Done when

- [x] `packages/shadow` launcher + safety + isolated journal
- [x] `desk.sh` hooks; morning does not auto-start shadow
- [x] Unit tests + dry-run demo
- [ ] Founder runs one session-night compare (human)

## Must not

- Replace or pause dual-tape
- Write `data/recon`, `data/ledger`, or legacy `data/shadow/<day>.jsonl`
- Claim a win rate or promote a strategy

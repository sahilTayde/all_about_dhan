# TASK — V2-25 Dhan off-market shadow order harness

**Date opened:** 2026-10-04  
**Assigned:** 07_coding (`packages/harness`) · 00_orchestrator (this ticket) · 09_review (docs auditor after HANDOFF)  
**Status:** `IN_PROGRESS` / **PAPER** / **NO_PROMOTE**  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** off-market LIMIT submit+cancel only, founder machine only. CI never hits Dhan.

## Requirement

PR-002's original shadow acceptance: submit a far-off LIMIT (₹1 buy) and cancel at once. Not live trading. Not the V2-26 paper log launcher.

- Default = OFF. Missing approval flag, missing credentials, or mode not `shadow`/`harness` → exit 2.
- `ALL_ABOUT_DHAN_LIVE_CONFIRM` does not enable this path. Mode `live` / `limited_live` is refused.
- CI: mocks / recorded fixtures only. Default path never constructs a live Dhan client.
- Do not enable `DhanBroker`, do not edit the legacy dual-tape loop, do not promote an exit playbook.

## Done when

- [x] Isolated `packages/harness` with fail-closed gates
- [x] Mocked tests: refuse without flag; refuse without credentials; submit+cancel on mock; no live client on default path
- [ ] Founder runs `--transport dhan` once on their machine (human)

## Must not

- Place MARKET or marketable limits
- Call Dhan from CI or the default CLI
- Set `V2_LIVE_BROKERS_ENABLED`
- Claim a win rate or promote a strategy

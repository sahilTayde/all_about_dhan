# TASK — Standing Docs Auditor (after requirement change + nightly)

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned:** 09_review (charter + verdicts) · 07_coding (`packages/docs-auditor`) · 05_analysis (nightly hook in `packages/desk-intel`) · 00_orchestrator (this ticket + `AUDIT_LATEST.md`)  
**Informed:** all teams (HANDOFF drift is in scope)  
**Owner paths:** [`DOCS_AUDITOR.md`](../../09_review/docs/DOCS_AUDITOR.md), [`packages/docs-auditor`](../../../packages/docs-auditor/), [`AUDIT_LATEST.md`](AUDIT_LATEST.md)  
**Status:** `DONE` (standing checker; **no live Dhan**; **no orders**; **does not claim docs are already perfect**)  
**Gate:** still **not** `RESEARCH_READY_FOR_PROGRAMMING`

---

## Requirement

An auditor **must run every time** (and **daily**) so documents stay honest when requirements are added or changed.

1. After any requirement change: compare `MASTER_REQUIREMENTS.md`, `AGENT.md`, team HANDOFFs vs code/config (poll interval, signal states, CAS, retune gate, no live orders). Flag `STALE` / `MISSING` / `CONTRADICTS`.
2. Same checker as part of **post-market nightly**.
3. If the manager sheet is missing: write a stub that points at HANDOFF and **fail** until the real sheet exists.
4. Never print secrets. Never scrape the web. Never restart npm. Never live Dhan.

## Done

- [x] Charter [`teams/09_review/docs/DOCS_AUDITOR.md`](../../09_review/docs/DOCS_AUDITOR.md)
- [x] Package [`packages/docs-auditor`](../../../packages/docs-auditor/) — `python -m docs_auditor`
- [x] CLI alias `python -m desk_intel audit-docs`
- [x] Nightly / `python -m jobs post-market` calls auditor **at the end**
- [x] `config/workspace.yaml` `jobs.docs_auditor` cadence `daily`
- [x] `AGENT.md` roster **Docs Auditor** (09) + golden rule: no requirement merge without auditor
- [x] Cursor rule `.cursor/rules/docs-auditor.mdc` (`alwaysApply: true`)
- [x] After-edit hook `.cursor/hooks.json` (`postToolUse` reminder)
- [x] Report `teams/00_orchestrator/docs/AUDIT_LATEST.md`

## How to run

```bash
pip install -e packages/docs-auditor
python -m docs_auditor
python -m desk_intel audit-docs
python -m desk_intel nightly --offline    # recon, then auditor
python -m jobs post-market --offline      # same as nightly
```

Exit **0** if pass, **1** if stale. First runs may FAIL (e.g. `PLAN.md` vs score sheet). That is the checker working.

## Checks (minimum)

| Check | Pass when |
|-------|-----------|
| Required files | `AGENT.md`, manager sheet, `RETUNE_GATE.md`, `cas/RESEARCH.md`, team HANDOFFs, … |
| AGENT.md phrases | CAS, IN-PROGRESS, RETUNE, 3m chain, customer vs `/desk`, Docs Auditor |
| Manager sheet | Real scorecard — not the HANDOFF stub |
| `chain_interval` | `3m` in `config/workspace.yaml` |
| Retune | `RETUNE_GATE.md` + nightly `BACKTEST_REQUIRED` |
| CAS | `cas/RESEARCH.md` names Closing Auction Session |
| Signal states | schema vs `SIGNAL_STAGING.md` |
| No live orders | `ExecutionClient` refuses |
| yaml job | `jobs.docs_auditor` daily |

## Not this ticket

- Making `PLAN.md` / every HANDOFF current (auditor **flags**; owners fix)
- Five-pass review
- Live Dhan / live orders
- Weakening checks so the first run is green

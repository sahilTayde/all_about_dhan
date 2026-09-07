# Docs Auditor — latest

**Date (IST):** `2026-09-08T00:52:38+05:30`
**Result:** **PASS** (0 findings)
**Cadence:** after any requirement change **and** post-market nightly (`jobs.docs_auditor: daily`)
**CLI:** `python -m docs_auditor` · `python -m desk_intel audit-docs`
**Nightly hook:** end of `python -m desk_intel nightly` / `python -m jobs post-market`
**Agent force:** Cursor rule `.cursor/rules/docs-auditor.mdc` (`alwaysApply: true`) + `.cursor/hooks.json`
**Charter:** [`teams/09_review/docs/DOCS_AUDITOR.md`](../../09_review/docs/DOCS_AUDITOR.md)

Compare `MASTER_REQUIREMENTS.md`, `AGENT.md`, team `HANDOFF.md` vs code/config (poll interval, signal states, CAS, retune gate, no live orders). Does **not** scrape the web. Does **not** print secrets.

## Findings

_None. Checker ran; do not treat this as `RESEARCH_READY_FOR_PROGRAMMING`._

## Checks run

- `required_files`
- `master_requirements_sheet`
- `team_handoffs`
- `agent_phrases`
- `chain_interval`
- `retune_gate`
- `cas_research`
- `signal_states`
- `no_live_orders`
- `jobs_docs_auditor`
- `nightly_hook`
- `cursor_rule`
- `company_board_drift`

## How to re-run

```bash
python -m docs_auditor
python -m desk_intel audit-docs
python -m jobs post-market --offline   # recon first, auditor last
```

Exit 0 = pass. Exit 1 = stale/missing/contradicts.

## Compliance

Education ≠ advice. Tokens never printed. No live Dhan. No live orders.

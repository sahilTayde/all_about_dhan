# packages/docs-auditor

Standing **Docs Auditor** (team **09_review** + orchestrator). Compares `MASTER_REQUIREMENTS.md`, `AGENT.md`, team `HANDOFF.md` files, and `config/workspace.yaml` against code on disk. **No web scrape. Never prints secrets.**

Charter: [`teams/09_review/docs/DOCS_AUDITOR.md`](../../teams/09_review/docs/DOCS_AUDITOR.md).  
Ticket: [`TASK_DOCS_AUDITOR.md`](../../teams/00_orchestrator/docs/TASK_DOCS_AUDITOR.md).  
Latest report: [`AUDIT_LATEST.md`](../../teams/00_orchestrator/docs/AUDIT_LATEST.md).

## How to run

```bash
cd /path/to/all_about_dhan
pip install -e packages/docs-auditor
python -m docs_auditor
# same checker via desk-intel (no extra install if path-insert works):
python -m desk_intel audit-docs
```

Exit **0** if pass, **1** if any `MISSING` / `STALE` / `CONTRADICTS`. Writes `teams/00_orchestrator/docs/AUDIT_LATEST.md`.

## Nightly hook

`python -m desk_intel nightly` and `python -m jobs post-market` call the auditor **at the end**. yaml: `jobs.docs_auditor.cadence: daily`.

## What it checks

Required files, AGENT.md key phrases (CAS, IN-PROGRESS, RETUNE, 3m chain, customer vs `/desk`), manager sheet vs stub, `chain_interval: 3m`, `RETUNE_GATE.md`, `cas/RESEARCH.md`, signal states vs `schema.py`, `ExecutionClient` refuses orders, team HANDOFFs, company board drift vs the score sheet.

Does **not** claim the tree is already perfect. First runs often fail on purpose.

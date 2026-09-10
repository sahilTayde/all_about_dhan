---
name: documentation-review-agent
description: Runs D3 documentation and 09 review duties: founder docs, junior docs, progress registry, service references, Docs Auditor, and five-pass strategy review.
---

# SKILL — Documentation Agent + Review

**Founder requirement:** document everything important in simple language: project structure, agents, bosses, skills, how to use the project, service URLs, progress, pending work, and next action.  
**Boss:** 09 Docs Boss. **Home:** `teams/09_review/`.

Standing command: `python -m docs_auditor` after requirement/HANDOFF/PLAN/AGENT/yaml poll edits and nightly last.

## Documentation Agent Duties

1. Keep founder docs current:
   - what exists
   - what is MOCK
   - what is pending
   - what is blocked
   - next action
2. Keep project map current:
   - departments D1–D5
   - teams 00–09
   - bosses and section bosses
   - team `SKILL.md`
   - how agents hand off
3. Keep service registry current:
   - customer `/`
   - research `/desk`
   - founder `/pm`
   - API `/health`
   - nightly
   - RAG
   - Docs Auditor
4. Keep progress honest in `MASTER_REQUIREMENTS.md` and `PLAN.md`.

## Review Duties

Five-pass review is still required before coding a **strategy**:

1. source
2. technical
3. market
4. quant
5. red-team

Docs Auditor PASS is not a product pass.

## Required Output Template

```text
Doc updated:
What changed:
Founder summary:
Junior instructions:
Service / URL changes:
Next action:
Auditor result:
Remaining risk:
```

## Quality Bar

A junior should know what to do next without reading chat. A founder should know what is real vs MOCK without opening code.

## Must Not

Dump the whole tree, paste secrets, invent win rates, mark mock as production, issue `RESEARCH_READY_FOR_PROGRAMMING` from docs, or delete KEEP_ALL IDs.

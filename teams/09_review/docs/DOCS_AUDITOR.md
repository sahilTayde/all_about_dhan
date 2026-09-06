# DOCS_AUDITOR — standing mandate (team 09_review + orchestrator)

**Owner:** 09_review (checker + verdicts) · 00_orchestrator (score sheet + `AUDIT_LATEST.md`)  
**Code:** [`packages/docs-auditor`](../../../packages/docs-auditor/)  
**Ticket:** [`TASK_DOCS_AUDITOR.md`](../../00_orchestrator/docs/TASK_DOCS_AUDITOR.md)  
**Latest report:** [`AUDIT_LATEST.md`](../../00_orchestrator/docs/AUDIT_LATEST.md)  
**Status:** standing. **Not** a five-pass. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.

---

## Why this exists

Requirements change. Agents add tickets. `PLAN.md` and team `HANDOFF.md` files lag. A human “we’ll update docs later” is how the morning score sheet dies.

The Docs Auditor **must run every time a requirement changes** and **again as part of post-market nightly**. It is not optional, not a one-shot, not a web scrape.

## When it runs

1. **After any requirement change** — `docs/MASTER_REQUIREMENTS.md`, `AGENT.md`, team `HANDOFF.md`, `PLAN.md`, `config/workspace.yaml` poll/jobs, retune/CAS/staging specs. Cursor rule `.cursor/rules/docs-auditor.mdc` is `alwaysApply: true`. After-edit hook: `.cursor/hooks.json`.
2. **Daily / post-market** — end of `python -m desk_intel nightly` and `python -m jobs post-market`. yaml `jobs.docs_auditor.cadence: daily`.

**Golden rule:** no requirement merge without a passing auditor (or an explicit FAIL report that names the drift).

## What it compares

| Source of truth (docs) | vs code/config |
|------------------------|----------------|
| [`docs/MASTER_REQUIREMENTS.md`](../../../docs/MASTER_REQUIREMENTS.md) | files actually on disk; stub ≠ sheet |
| [`AGENT.md`](../../../AGENT.md) | CAS, IN-PROGRESS, RETUNE, 3m chain, customer vs `/desk` |
| Team `HANDOFF.md` (00–09) | file exists |
| [`config/workspace.yaml`](../../../config/workspace.yaml) | `desk_intel.poll.chain_interval: 3m`; `jobs.docs_auditor` daily |
| [`RETUNE_GATE.md`](../../06_backtesting/docs/RETUNE_GATE.md) | nightly emits `BACKTEST_REQUIRED`; no production param write |
| [`cas/RESEARCH.md`](../../03_phd_market/cas/RESEARCH.md) | CAS = Closing Auction Session; `sources.cas[]` |
| [`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md) | `schema.py` states WATCH → … → IN-PROGRESS |
| No live orders | `ExecutionClient` `SafeModeError` / refuse |

Flags: **`MISSING`** · **`STALE`** · **`CONTRADICTS`**.

The checker is **honest**. It will fail if `PLAN.md` still cites old transcript counts while the score sheet says 45. Do not “fix” that by weakening the checker.

## How to run

```bash
python -m docs_auditor
python -m desk_intel audit-docs
```

Exit **0** pass · **1** stale. Writes `teams/00_orchestrator/docs/AUDIT_LATEST.md` (date + findings). Never prints secrets. Does not read `.env`. Does not call Dhan. Does not scrape the web.

If `MASTER_REQUIREMENTS.md` is absent, the auditor writes a **stub** that points at `docs/HANDOFF.md` and **still fails** until the manager sheet exists.

## Out of scope

- Five-pass / red-team (`docs/REVIEW.md`)
- Inventing win rates or live fills
- Restarting npm
- Live Dhan

---
name: engineering-department
description: Runs the D1 Engineering department for the all_about_dhan signal product. Use when building or reviewing API, web, RAG, SQLite warehouse, local ML, nightly jobs, backtest infrastructure, or coding section ownership.
---

# SKILL — D1 Engineering Department

**Founder requirement:** build a quick, scalable, beautiful signal app with RAG, SQL storage, local ML, nightly jobs, backtesting, and coding docs that juniors and founders can review.  
**Boss:** 07 Engineering Boss. **QA:** 08. **Docs:** 09.  
**Home:** `teams/07_coding/`, `apps/`, approved `packages/`.

Standards:

- [`ENGINEERING_SECTIONS.md`](docs/ENGINEERING_SECTIONS.md)
- [`PRODUCT_ARCHITECTURE_STANDARDS.md`](../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md)
- [`TOKEN_ML_STRATEGY.md`](../../docs/TOKEN_ML_STRATEGY.md)
- [`CUSTOMER_PORTAL_UX.md`](../../docs/CUSTOMER_PORTAL_UX.md)

## Operating Workflow

1. Start from `AGENT.md`, this skill, and the relevant standard doc.
2. Decide which section owns the work: C1 API, C2 warehouse, C3 RAG, C4 local ML, C5 backtest, C6 nightly, C7 portals, C8 QA.
3. Define the data contract first: inputs, outputs, idempotency key, error codes, timestamps, source/version fields.
4. Keep market-hours fast path local: Dhan/cache → features → feasibility/risk → read model → UI. **No LLM calls.**
5. Keep heavy work in batch: RAG rebuild, model training, backtests, docs, counsel review.
6. Add tests or a dry-run check for every changed contract.
7. Write founder/junior notes in `teams/07_coding/docs/`.

## Section Bosses

| Section | Boss must review | Quality bar |
|---------|------------------|-------------|
| C1 API / Dhan | no browser secrets; SafeMode refuses orders; rate-limit handling | 401/429 visible on `/pm`; no invented Dhan fields |
| C2 Warehouse | schema, indexes, retention, provenance | append-only raw events; idempotent ticket writes |
| C3 RAG | chunking, layer tags, golden queries | answers cite source path + layer; no raw book spam to LLM |
| C4 Local ML | features, labels, model version, OOS plan | local rules/model first; no LLM fine-tune before labels |
| C5 Backtest | costs, slippage, OOS, `NORMAL` gate | FAIL / `DATA_INSUFFICIENT` accepted; no promote |
| C6 Nightly | ordering and stop-the-line checks | docs/RAG/SQL/backtest then auditor last; no auto-retune |
| C7 Portals | `/`, `/desk`, `/pm` separation | customer mobile-first, fast, no indicator soup |
| C8 QA | fixtures, health checks, regression | mock clearly labeled; sqlite not committed unless explicitly staged |

## Required Outputs

- Code or migration with tests.
- Contract note: request/response or table schema.
- Failure behavior: what turns amber/red on `/pm`.
- Founder note: what changed, what is MOCK, next action.

## Books / Training

Engineering does not learn trading edge from books. It learns systems: event sourcing, idempotency, observability, API versioning, local-first RAG. Trading books stay with D2.

## Must Not

`place_order`, live order UI, Dhan keys in browser, npm/paper restart without founder ask, git-add sqlite unless asked, auto-retune from nightly, or invent HQ indicator series.

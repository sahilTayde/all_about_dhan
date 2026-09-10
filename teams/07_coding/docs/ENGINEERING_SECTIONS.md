# D1 Engineering — section bosses

**Department boss:** 07. **QA:** 08. **Docs:** 09.  
**Junior review:** read this file + the PR note. **Founder review:** `/pm` + this page.

Coding docs for the product live **here** (`teams/07_coding/docs/`), not scattered in chat.

Product standards:

- Architecture / speed: [`PRODUCT_ARCHITECTURE_STANDARDS.md`](../../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md)
- Token + ML: [`TOKEN_ML_STRATEGY.md`](../../../docs/TOKEN_ML_STRATEGY.md)
- Customer UX: [`CUSTOMER_PORTAL_UX.md`](../../../docs/CUSTOMER_PORTAL_UX.md)

| ID | Section | Boss reviews | Code home |
|----|---------|--------------|-----------|
| C1 | Dhan / API | SafeMode still refuses orders | `packages/dhan-client`, `apps/api` |
| C2 | Warehouse | Append-only events, features, signals, ticket events, outcomes, provenance | `data/knowledge/*.sqlite` (do not git-add) |
| C3 | RAG | FTS rebuild; later local embeddings/sqlite-vec only if needed | `packages/agent_rag` |
| C4 | Local ML | Zero-token fast path: rules → logistic/tree → LightGBM/XGBoost-style tabular models | TBD under `packages/` — not started |
| C5 | Backtest | Costs, OOS, no invented fills | `packages/backtest` |
| C6 | Nightly | Auditor last; no auto-retune | `packages/desk-intel` |
| C7 | Portals | `/` `/desk` `/pm` | `apps/web` |
| C8 | QA | Fixtures, health probes | `teams/08_testing`, package tests |

Material merge: section boss + 07. If the change touches signal language or gates, run counsel `REVIEW_NOTES` (Gemini **and** OpenAI).

**Nightly may** update RAG/SQL, docs, and **propose** code. **Nightly may not** write production MIX params or enable live orders.

## Non-negotiable engineering standards

- Customer `/` reads a compact precomputed signal payload.
- Browser never calls Dhan and never calls LLMs.
- Fast path uses local features, local feasibility, and cached read models only.
- Every signal/ticket write is idempotent and carries source snapshot, feature version, model version, and reason code.
- Exit / kill / expire wins over new entry.
- `/pm` must show vendor key health, 401/429, chain freshness, API status, RAG age, nightly age, and auditor status.

**Still TODO:** `/pm`, warehouse DDL, local ML, dealer feasibility in API, optional sqlite-vec/embeddings.

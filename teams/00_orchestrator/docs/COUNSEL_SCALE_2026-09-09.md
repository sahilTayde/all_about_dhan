# Dual-model counsel — scalability, token cost, ML, UX

**Date:** 2026-09-09  
**Policy:** review only. Keys never printed. **No live orders. NO_PROMOTE.**

## Result

Both Gemini and OpenAI answered successfully. Verdict was **split wording** but aligned on the important engineering direction:

- Gemini: `AGREE_WITH_CAVEATS`
- OpenAI: typo `AGREE_WITH_CAVETS`, interpreted as `AGREE_WITH_CAVEATS`
- Together: `SPLIT` only because the verdict token was misspelled, not because the substance disagreed.

## Accepted

1. **Fast path / batch path split:** market-hours signal serving must not call LLMs or scan books. Nightly handles heavy work.
2. **Local first:** SQLite + FTS5 now; Postgres/Timescale or MySQL only when concurrency/volume proves SQLite is the bottleneck.
3. **Precomputed UI read model:** customer `/` reads compact JSON, not raw chain or strategy internals.
4. **Token control:** Gemini/OpenAI only for pre/post market synthesis, dealer sanity, and faculty review on compact facts.
5. **Local ML first:** rules, logistic/tree models, LightGBM/XGBoost-style tabular models before any LLM fine-tune.
6. **Monitoring:** API latency, WebSocket heartbeat/staleness, vendor keys, 401/429, Dhan freshness, RAG/nightly freshness.
7. **Dealer state machine:** exit/kill/expire has priority over new entries. No stale `IN-PROGRESS`.

## Rejected / modified by 00

- **Rust/Go rewrite now:** rejected. Python/FastAPI is acceptable until measurement proves otherwise.
- **3-second TTL for every signal:** rejected as too blunt. TTL must depend on stage, data freshness, and option context.
- **Bracket/order language:** rejected. ExecutionClient refuses live orders; this is a signal portal.
- **Cloud vector DB day-1:** rejected. FTS5 first, local embeddings/sqlite-vec later if needed.

## Standards written from this review

- [`PRODUCT_ARCHITECTURE_STANDARDS.md`](../../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md)
- [`TOKEN_ML_STRATEGY.md`](../../../docs/TOKEN_ML_STRATEGY.md)
- [`CUSTOMER_PORTAL_UX.md`](../../../docs/CUSTOMER_PORTAL_UX.md)


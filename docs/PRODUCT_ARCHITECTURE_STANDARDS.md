# Product architecture standards — fast signal app

**Date:** 2026-09-09  
**Product class:** DhanHQ-only index-options signal company.  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**

This is the engineering standard for building a quick, scalable, low-token trading signal app. It upgrades the department chart into a product architecture.

---

## 00 ruling after second counsel

Gemini and OpenAI both supported the main direction:

- Keep **LLMs off the fast path**.
- Use **local deterministic checks + local ML** for day-to-day signal gating.
- Keep **SQLite + FTS5 now**, add clearer schemas, retention, indexes, and read models.
- Use one site with three views: customer `/`, research `/desk`, founder `/pm`.
- Add monitoring SLOs: API latency, WebSocket lag, rate limits, key status, nightly freshness.

Rejected:

- Rust/Go as a day-1 rewrite. Python/FastAPI is fine for this stage if the hot path is cached, async, and local.
- 3-second signal TTL as a universal rule. Index-options signals can have TTL by stage, not one hard number.
- Any live/bracket order language. The app is a **signal portal** until the gate changes.

---

## Fast Path vs Batch Path

| Path | Time | Allowed | Not allowed |
|------|------|---------|-------------|
| **Fast path** | Market hours | Dhan feed/REST snapshots, local feature compute, local feasibility rules, cached read model, WebSocket/UI push | LLM calls, book/RAG scan, parameter sweeps, doc writes |
| **Near-real-time path** | 3m / stage clock | Chain snapshot, sentiment windows, dealer feasibility, stale-ticket kill, PM health | Full backtest, vector rebuild |
| **Batch path** | Pre/post/nightly | Backtest, parameter sweeps, RAG rebuild, docs update, model evaluation, mistake book, counsel review | Live execution, production auto-retune |

**Rule:** customer `/` reads a **precomputed ticket read model**. It should not compute strategy logic in the browser and should never call Dhan.

---

## Latency and Freshness Targets

These are engineering targets, not trading performance claims.

| Surface | Target |
|---------|--------|
| Customer page first load | p95 under 2 seconds on a normal mobile connection |
| Cached signal API | p95 under 250 ms locally / intranet |
| WebSocket heartbeat | visible stale warning if no update within 10 seconds during market mode |
| Local signal evaluation | under 500 ms after required data is present |
| Full chain poll | 3m default; never switch to 1m full-chain without rate-limit proof |
| Dhan / LLM vendor errors | visible on `/pm` within one poll cycle |
| Nightly report freshness | visible before next pre-market checklist |

If a target cannot be measured yet, mark it `UNKNOWN`, not green.

---

## Data Standard

SQLite remains the correct default while we are single-workspace, paper/shadow, and local-first.

### Required tiers

| Tier | Purpose | Minimum columns |
|------|---------|-----------------|
| `raw_market_events` | Immutable source packets | source, symbol, segment, received_at, payload_hash, payload_json |
| `bars_1m` / `bars_5m` | Canonical OHLCV / OI bars | symbol, ts, open, high, low, close, volume, oi, source |
| `chain_snapshots` | Option-chain state | underlying, ts, expiry, atm, pcr, payload_hash |
| `features` | Reproducible model inputs | symbol, ts, feature_set_version, feature_json |
| `signals` | Exact ticket decision | signal_id, ts, underlying, stage, side, levels_json, model_version, feature_set_version |
| `ticket_events` | State changes | signal_id, ts, old_state, new_state, reason_code |
| `outcomes` | Paper/shadow result | signal_id, outcome, exit_reason, points, is_mock |
| `research_sources` | Provenance | source_id, url, title, retrieved_at, layer, hash |
| `rag_chunks` | Retrieval surface | source_id, chunk_id, kind, layer, text, fts_terms |
| `model_runs` | ML/backtest audit | run_id, model_version, train_window, test_window, metrics_json, verdict |

### SQLite operating rules

- Use WAL mode for concurrent reads.
- Append raw data; update only derived/read-model rows.
- Index by `(underlying, ts)`, `(signal_id, ts)`, and `(source_id, layer)`.
- Keep raw high-frequency data local/off-git. Commit schemas and migrations, not DB files.
- Promote to Postgres/Timescale only when concurrency, retention, or multi-user writes prove SQLite is the bottleneck.

---

## Token and ML Standard

Detailed token plan: [`TOKEN_ML_STRATEGY.md`](TOKEN_ML_STRATEGY.md).

Standing rule: **zero LLM calls on the fast path**.

| Work | Default engine |
|------|----------------|
| KB/API/book lookup | SQLite FTS5 / later sqlite-vec |
| Indicator math | local Python |
| Dealer feasibility | deterministic rules |
| Regime / hold-vs-trade classifier | local tabular model first |
| Customer copy | templated + cached, LLM only for pre/post-market summary |
| Deep review | Gemini + OpenAI counsel on short JSON facts |

Fine-tuning an LLM is **not** the next step. First train small local models on clean feature/outcome tables. Only after enough labeled sessions exist should we consider distillation or fine-tuning.

---

## Customer Portal UX Standard

Spec: [`CUSTOMER_PORTAL_UX.md`](CUSTOMER_PORTAL_UX.md).

Customer `/` must be:

- Mobile-first.
- One primary call, one clear action.
- Beautiful but not noisy: strong typography, calm colors, no indicator soup.
- Honest: signal state, reason, expiry/stale status, and risk shown plainly.
- Fast: reads a precomputed ticket payload.
- Trustworthy: no fake P/L, no fake win rate, no stale `IN-PROGRESS`.

Research internals stay on `/desk`. Founder operations stay on `/pm`.

---

## Monitoring Standard

Founder PM spec: [`FOUNDER_PM.md`](../teams/00_orchestrator/docs/FOUNDER_PM.md).

Minimum health checks:

| Check | Red when |
|-------|----------|
| Dhan auth | missing key, 401/403, repeated data failure |
| Dhan rate | 429 or local token bucket exhausted |
| Chain freshness | last full-chain snapshot older than expected |
| WebSocket | heartbeat stale during market mode |
| OpenAI / Gemini | missing key, 401, 429, model error |
| RAG | index older than latest source update |
| Nightly | no post-market report before next pre-market |
| Docs Auditor | non-zero exit |
| API | health endpoint down |
| Portal | build failure or stale payload |

Customer sees graceful “market data delayed / signal paused.” Founder sees the error and next action.

---

## Industry Guardrails

1. **Idempotency:** every signal and ticket event has a stable id; repeated writes do not duplicate trades.
2. **State machine:** exit/kill/expire has priority over new entry.
3. **Auditability:** every ticket stores feature version, model version, source snapshot, and reason code.
4. **No token dependency during market hours:** if LLMs are down, local rules still HOLD/kill safely.
5. **No silent retune:** nightly proposes; 06 + 09 + founder gate decides.
6. **No customer confusion:** customer page never shows mock results as performance.
7. **Disaster recovery:** after restart, rebuild read models from append-only events, mark stale if reconciliation fails.

---

## Implementation order

1. Warehouse schema + idempotent ticket events.
2. Dealer feasibility rules and stale-ticket state machine.
3. `/pm` health canvas.
4. Customer UX refresh on top of the new read model.
5. Local model feature table + baseline classifier.
6. Optional sqlite-vec only after FTS misses real questions.


# Token and ML strategy

**Date:** 2026-09-09  
**Goal:** spend tokens where human-level reasoning helps, not where a database or small model can answer faster.

---

## Prime Directive

**No LLM on the blocking market-hours fast path.**

During trading hours the app must be able to:

1. Pull cached data / Dhan snapshots.
2. Compute local features.
3. Run local feasibility and stale-ticket rules.
4. Serve customer `/` from a read model.
5. Mark HOLD / killed if vendors are down.

OpenAI or Gemini may review the desk's reasoning, including during live market, but the product must not freeze waiting for them. If LLM counsel times out, local rules still HOLD / kill safely.

---

## Token Budget

| Use | Token policy |
|-----|--------------|
| Pre-market brief | Allowed, summarized facts only |
| Post-market review | Allowed, mistake book + concise data |
| Dealer sanity check | Allowed only on **our proposed ticket** and compact JSON facts |
| Live risk counsel | Allowed on material state changes only: OI shock, premium reversal, near stop/target, news shock, stale tape |
| Faculty deep review | Allowed for material regime/parameter changes |
| Documentation rewrite | Allowed after local facts are collected |
| KB/API/book lookup | **Local only** (SQLite FTS5 / later sqlite-vec) |
| Indicator calculation | **Local only** |
| Backtest / score | **Local only** |
| Customer page render | **Local only** |

Every LLM call should carry:

- `job_id`
- `facts_hash`
- `provider`
- `model`
- `prompt_version`
- `token_estimate`
- `output_hash`
- `verdict`

Cache by `(job_id, facts_hash, prompt_version, model)`. If the facts have not changed, reuse the previous answer.

## Live LLM Risk Counsel

Purpose: give the dealer judgment when local features show a material change, like sudden OI reversal or premium momentum fading.

Allowed output:

- `RISK_REVIEW`
- `PARTIAL_BOOK_REVIEW`
- `EXIT_REVIEW`
- `HOLD`
- `DATA_INSUFFICIENT`

Not allowed:

- Place order.
- Generate a new CE/PE from raw vibes.
- Claim a fill.
- Override stop/target feasibility.
- Continue a stale `IN-PROGRESS`.

Prompt payload must be compact JSON:

```json
{
  "ticket_id": "paper-nifty-001",
  "underlying": "NIFTY",
  "stage": "IN_PROGRESS",
  "levels": {"entry": 150, "stop": 126, "target": 192},
  "state": {
    "premium_ltp": 176,
    "premium_velocity": "fading",
    "oi_delta_3m": "CE_unwind",
    "pcr_delta_3m": "falling",
    "news_tags": [],
    "time_to_expiry": "same_day"
  },
  "ask": "risk_review_only"
}
```

Output is stored as a counsel event and shown as customer-friendly risk text only after deterministic safety checks.

---

## RAG Plan

Current: `packages/agent_rag` with SQLite FTS5. Keep it.

Add ingestion targets:

| Corpus | Layer |
|--------|-------|
| Dhan API docs and field notes | `SOURCE_FACT` |
| @DhanHQ English transcript packets | `SOURCE_FACT` |
| Books / academic references | `VALIDATION` |
| STRAT/MIX/CAS docs | `HYPOTHESIS` |
| Backtest reports | `VALIDATION` / score |
| Mistake book | `VALIDATION` for future analogs |

Retrieval output must be short: top hits + source path + snippet + layer. The LLM never receives raw books unless a human explicitly asks for a deep review.

**Embeddings later:** add sqlite-vec or local embeddings only when FTS misses semantic questions that matter to the desk. Do not add a hosted vector DB as the first move.

---

## Local ML Roadmap

Fine-tuning an LLM is not first. The first useful models are small, local, fast, and auditable.

| Phase | Model | Input | Output | Gate |
|-------|-------|-------|--------|------|
| ML-0 | Rules | stage, chain freshness, levels | HOLD / feasible / stale | unit tests |
| ML-1 | Logistic regression / tree | features table | hold-vs-trade probability bucket | shadow only |
| ML-2 | LightGBM / XGBoost | richer chain + bar features | regime / confidence bucket | OOS + 09 review |
| ML-3 | Exit / partial-book assist | favorable/adverse excursion, OI delta, premium velocity | exit-review / partial-book-review bucket | shadow only |
| ML-3b | Calibrated ensemble | multiple models | dealer assist only | no auto-promote |
| ML-4 | Distilled/fine-tuned LLM | only after large labeled corpus | text explanation | must not drive entry |

Required training rows:

- market session tag (`NORMAL`, `NEWS_DAY`, `EXPIRY`, `UNKNOWN`)
- underlying, expiry, moneyness
- 1m/3m/5m features
- chain snapshot features
- ticket levels and state transitions
- outcome and mistake reason
- costs and slippage assumptions
- model/feature version

If labels are thin, output `DATA_INSUFFICIENT`.

---

## Guardrails

- Local ML can **assist HOLD / risk / regime**, not independently publish a customer ticket.
- A model cannot override deterministic hard stops.
- No model version is promoted without OOS, costs, and 09 review.
- Nightly may train/evaluate and propose. It may not write production params.
- Customer never sees “AI says 87% win.” Confidence is desk agreement / data quality only.


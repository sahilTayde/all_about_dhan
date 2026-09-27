# packages/desk-ml — ML-001 + ML-002 overlays

Unsupervised **ML-001** (KMeans k=4 + IsolationForest) and **ML-002** (OU on MIX-FORM residual + VWMA MRR windows 40/60/90) on 1m INDEX + ATM CE + ATM PE triples.

**Not** MIX param writes. **Not** orders. Dual-tape poll stays deterministic (`desk_divergence`). Score after bar close **or** ` --source dual-tape`. FOLLOW-GAP overlay HOLDs new paper CE/PE. Session prep: [`SESSION_PREP_ML.md`](../../teams/06_backtesting/docs/SESSION_PREP_ML.md).

Specs: [`ML_001_LOCAL_PATTERN.md`](../../teams/04_quant/docs/ML_001_LOCAL_PATTERN.md) · [`BOOK_MODEL_TUNE.md`](../../teams/06_backtesting/docs/BOOK_MODEL_TUNE.md)

```bash
pip install -e packages/desk-ml
python -m desk_ml inventory --calendar-days 21
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml score --underlying NIFTY --source dual-tape
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml book-tune --calendar-days 21
python -m desk_ml replay-hold --underlying NIFTY --horizon-bars 15
python -m desk_ml paper-scalp --replay
```

Empty / non-overlapping cache → `DATA_INSUFFICIENT`. Models land in `data/recon/ml/` (gitignored). `production_params_written: false`. **NO_PROMOTE**. Cluster/MRR numbers are counts, not a win rate.

## LLM analyst (PR-016), advisory only

`desk_ml.llm_analyst` gives a strict-JSON second opinion (`agree | disagree | abstain`, confidence, reasons, risk flags) on the analyst room's provisional CE/PE side. It is registered as `LLM-ANALYST` (`analysts.llm`) and has **no order authority**: it cannot import the broker, desk, risk engine, ledger or paper order path (enforced by `tests/test_llm_analyst.py`). Any parse failure, timeout (`timeout_ms`, default 2000) or error is `abstain` and the tick carries on.

- **Default = shadow.** `weight: 0` in `config/llm_analyst.yaml` and `shadow: true` on its `config/analysts.yaml` row: logged, never counted, replay trades byte-identical. To let it vote, set `weight: 1` **and** drop `shadow: true`; then `agree` is one CONFIRM vote and `disagree` is silent (no veto).
- **Providers.** `mock` (deterministic rules, offline), `recorded` (replays logged responses by context hash), `openai` (stdlib HTTP, strict `json_schema`). Add Gemini/Claude by subclassing `Provider` and adding it to `PROVIDERS`. The online `provider` runs only in the live paper loop (`live_loop`). Every other replay, including `live_session`, uses the offline `replay_provider`. Online and offline calls share one call and token budget; a replay still always gets an answer.
- **OpenAI on the live paper loop.** `export OPENAI_API_KEY=...` (env only; never in a file in the repo), then set `provider: openai` in `config/llm_analyst.yaml`. With weight 0 the call runs in the background, so the tick never waits.
- **Guardrails.** Identical-context cache, same-signal reuse window, per-day call and USD budgets (restored from the log on restart), rate limit, one call in flight, stale-tick skip. News/notes are sanitised and quoted as `*_untrusted` data. Credential/account-shaped keys and values are scrubbed from the prompt and the log.
- **Log + scoring.** Online calls are appended to `data/llm_analyst/calls.jsonl` (gitignored): context hash, prompt version, context, response, latency, tokens, cost. Score offline:

```bash
python -m desk_ml.llm_analyst.scorer --log data/llm_analyst/calls.jsonl --trades closed_trades.json
```

# Topic → strategy-doc pipeline

**Status:** stub. Catalog/transcripts are wired. Topic clustering writes **pointers**, not a finished research packet.  
**Honesty:** education ≠ proof. Every topic file is `UNVALIDATED` / `HYPOTHESIS` until backtest + review. Never claim guaranteed profits. [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).

Master file (URLs, books, secret *names*): [`config/workspace.yaml`](../../../config/workspace.yaml).  
Keys: repo-root `.env` only.  
Official indicator defs (API vs chart): [`DHAN_OFFICIAL_INDICATORS.md`](DHAN_OFFICIAL_INDICATORS.md). Each topic file in `teams/04_quant/docs/topics/` must cite that catalog.

---

## What the customer changes

| Want | Edit |
|------|------|
| YouTube channel (e.g. `@DhanHQ` today, Zerodha / Market Analyst Academy / Master Bull later) | `sources.youtube[]` `url` or `handle`, then `enabled: true` on that row |
| Books used as independent checks | `sources.books[]` (`use: VALIDATION`) |
| API keys | `.env` (`YOUTUBE_API_KEY`, `DHAN_*`). Names are listed in `secrets_from_env` |

Non-Dhan rows stay `tier: EXTERNAL_RESEARCH`. Production indicators stay Dhan-only while `implementation.indicators: dhan_only`. Disabled examples are **not** scraped.

---

## Pipeline (cluster by topic, not one blob)

```text
config/workspace.yaml
        │
        ▼
  catalog (01_research)     → data/youtube/video_catalog.{csv,json}
        │                     each row tagged source_id / source_tier / origin_tag
        ▼
  transcripts + english     → data/transcripts/{raw,normalized,normalized_en}
        │
        ▼
  topic_extract (cluster)   → teams/04_quant/docs/topics/<topic>.md
        │                     one file per topic (options buying, VWAP, RSI+Supertrend, …)
        ▼
  read context              → 01 writes SOURCE_FACT into the topic file (timestamps)
        │                     02/03 write VALIDATION (books + exchange)
        ▼
  strategy_docs (04_quant)  → HYPOTHESIS section in the same per-topic file
                              plus STRAT-IDs under teams/04_quant/docs/candidates/
```

Agents **must not** concatenate every transcript into a single markdown dump. A video that hits several tags appears in several topic files as a pointer (`video_id` + title + source).

---

## Agent routing (`agent_routing` in workspace.yaml)

| Step | Team |
|------|------|
| catalog, transcripts, english, topic_extract, SOURCE_FACT | 01_research |
| VALIDATION math | 02_phd_math |
| VALIDATION market | 03_phd_market |
| strategy_docs (HYPOTHESIS) | 04_quant |
| backtest | 06_backtesting |
| review | 09_review |

---

## Commands (no huge scrape)

From `teams/01_research/youtube` with the local venv:

```bash
python -m src show-config          # dry: yaml + enabled channels, no secrets
python -m src topics               # cluster existing catalog → per-topic stubs
# python -m src catalog            # only when you intend to hit YouTube Data API
```

`topics` reads the current catalog. It does not call YouTube. It refreshes the auto cluster block inside each topic file and leaves human SOURCE_FACT / VALIDATION / HYPOTHESIS sections intact.

---

## Output

Per-topic markdown: [`teams/04_quant/docs/topics/`](../../04_quant/docs/topics/).  
Coded (still UNVALIDATED) candidates stay in `teams/04_quant/docs/candidates/` — this pipeline does not replace them.

---

## Still stub vs wired

| Piece | State |
|-------|--------|
| `config/workspace.yaml` load + `${ENV}` interpolation | **Wired** |
| Catalog/transcripts from **enabled** youtube sources + `source_id` tags | **Wired** |
| Disabled Zerodha / MAA / Master Bull examples | **Not scraped** (leave `enabled: false`) |
| `python -m src topics` cluster → stub files | **Wired (stub content)** |
| Reading transcripts into SOURCE_FACT per topic | **Still human/agent work** |
| Independent VALIDATION fill | **Still 02/03** |
| Per-topic HYPOTHESIS freeze | **Still 04; UNVALIDATED** |

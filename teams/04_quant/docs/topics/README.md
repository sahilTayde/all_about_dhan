# Topic strategy documents

**Status:** stubs / `UNVALIDATED` / `HYPOTHESIS`. Not `RESEARCH_READY_FOR_PROGRAMMING`.
One markdown file per topic. Agents cluster videos here; they do **not** dump all
transcripts into a single blob.

Source channels and books: [`config/workspace.yaml`](../../../../config/workspace.yaml).
Customer switches YouTube by changing a URL (or `enabled`) in that file.

Refresh cluster tables from the current catalog (no YouTube scrape):

```bash
cd teams/01_research/youtube
python -m src topics
```

Coded candidates (still UNVALIDATED): [`../candidates/`](../candidates/).
Pipeline: [`../../../01_research/docs/TOPIC_STRATEGY_PIPELINE.md`](../../../01_research/docs/TOPIC_STRATEGY_PIPELINE.md).

| Topic | File | Catalog hits | Verified transcripts |
|---|---|---:|---:|
| Options buying | [`options_buying.md`](options_buying.md) | 325 | 10 |
| VWAP | [`vwap.md`](vwap.md) | 20 | 1 |
| RSI + Supertrend | [`rsi_supertrend.md`](rsi_supertrend.md) | 5 | 1 |
| MACD | [`macd.md`](macd.md) | 17 | 0 |
| Option chain | [`option_chain.md`](option_chain.md) | 47 | 1 |
| Scalping | [`scalping.md`](scalping.md) | 81 | 6 |

Template: [`_TEMPLATE.md`](_TEMPLATE.md).

**Official Dhan indicator defs (every topic file cites these):** [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · VALIDATION map [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md) · KB [`../../../../research/indicator_knowledge_base.md`](../../../../research/indicator_knowledge_base.md). Clubbed from HQ v2 (2026-09-01): trigger **names** exist; Supertrend/session VWAP are **chart/product**, not series endpoints.

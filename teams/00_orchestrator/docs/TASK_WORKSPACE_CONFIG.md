# TASK — Customer master workspace config

**Date opened:** 2026-09-01  
**Date closed:** 2026-09-01  
**Assigned team:** 00_orchestrator (routing) + 01_research (collector wiring) + 04_quant (topic stubs)  
**Owner path:** `config/workspace.yaml`  
**Status:** DONE (topic strategy write-up still STUB)

---

## Requirement

One customer-facing master file for URLs, books, and secret *references* so a customer can switch YouTube source (e.g. `@DhanHQ` today, tomorrow Zerodha / Market Analyst Academy / Master Bull) by changing a URL. Agents then: catalog → transcripts → read context → write **per-topic** strategy documents. Multiple videos, multiple topics; cluster by topic, not one blob.

## Policy (kept honest)

- Default source remains official Dhan while `config/workspace.yaml` has `dhanhq` enabled as `TIER_1`.
- Non-Dhan channels are `EXTERNAL_RESEARCH`. Production Dhan indicators stay Dhan-only unless `implementation.broker` / `implementation.indicators` say otherwise.
- Education ≠ proof. Strategy docs are `UNVALIDATED` / `HYPOTHESIS`. Never claim guaranteed profits. [`docs/COMPLIANCE.md`](../../../docs/COMPLIANCE.md).
- Secrets: master file lists **variable names** (and `${YOUTUBE_API_KEY}` interpolation). Values stay in gitignored `.env`. Optional overlay `config/workspace.local.yaml` is gitignored.

## Done

- [x] Master file: `config/workspace.yaml` (Dhan default + disabled external examples)
- [x] Loader: `config/load.py` (overlay + env interpolation; secret **names** only)
- [x] YouTube collector reads enabled `sources.youtube[]`; catalog tags `source_id` / `source_tier` / `origin_tag`
- [x] `python -m src show-config` dry load (no scrape)
- [x] `python -m src topics` stub cluster → `teams/04_quant/docs/topics/`
- [x] Pipeline note: `teams/01_research/docs/TOPIC_STRATEGY_PIPELINE.md`
- [x] AGENT.md INDEX points customers at `config/workspace.yaml`
- [x] `.gitignore` overlay + `data/topics/`

## Not this ticket

- Do **not** scrape Zerodha / Market Analyst Academy / Master Bull unless the customer sets `enabled: true`.
- Do **not** run a full catalog refresh just to prove the yaml.
- Filling SOURCE_FACT / VALIDATION / HYPOTHESIS inside topic files remains later research work.

## How a customer switches channel

1. Edit `config/workspace.yaml`.
2. Put the channel URL (or handle) on the row they want; set `enabled: true`.
3. Set other youtube rows `enabled: false` if they want a single source.
4. Keep non-Dhan `tier: EXTERNAL_RESEARCH`.
5. Put keys in `.env` once (`YOUTUBE_API_KEY`, later `DHAN_*`).
6. From `teams/01_research/youtube`: `python -m src show-config` then `python -m src catalog` when they intend to hit the API.

## Commands (dry)

```bash
cd teams/01_research/youtube
source .venv/bin/activate
python -m src show-config
python -m src topics
```

# ANALYSIS.md — YouTube extraction contract

Day-to-day spec for research and coding agents. Full plan: [`PLAN.md`](PLAN.md). Do not re-read PLAN.md to extract; use this file. Do not implement the scraper from this document.

---

## 1. Purpose and source rule

Pipeline: **Videos → Metadata → Transcripts → Topics → Claims → Rules → Indicators → Parameters → Hypotheses**. Output is a structured research corpus, not a transcript dump. Per-topic strategy stubs: [`../docs/TOPIC_STRATEGY_PIPELINE.md`](../docs/TOPIC_STRATEGY_PIPELINE.md).

**Live channel list:** [`config/workspace.yaml`](../../../config/workspace.yaml). Customers switch YouTube by changing a URL/`enabled` flag. Default enabled source is official `@DhanHQ` (`TIER_1`).

- **Tier 1 (transcripts):** official Dhan channel — [https://www.youtube.com/@DhanHQ](https://www.youtube.com/@DhanHQ) ([playlists](https://www.youtube.com/@DhanHQ/playlists)) while that yaml row is enabled. Other yaml channels, when enabled, are `EXTERNAL_RESEARCH` (ideas only). Do not scrape disabled rows. No blogs, social summaries, or third-party transcripts as a silent substitute.
- **Education ≠ proof.** A Dhan video is a hypothesis source. It does not prove profitability, predictive power, or suitability for NIFTY / BANKNIFTY / SENSEX options.
- **Never hallucinate transcripts.** Never invent text from title/description. Never write “Dhan recommends X” or “the expert said X” unless the transcript supports it.
- Phase-1 instruments: NIFTY, BANKNIFTY, SENSEX **index options**. `STOCK_ONLY` videos stay in the catalog; exclude from Phase-1 strategy construction unless the concept clearly transfers. Exclusive stock/fundamentals/long-term/unrelated: tag `EXCLUDED_STOCK_ONLY` — do not delete metadata.
- Popularity ranks **which video to read**, not strategy quality.

**SOURCE HIERARCHY (addendum)** — URL classes: [`../docs/DHAN_ECOSYSTEM.md`](../docs/DHAN_ECOSYSTEM.md). Charter: [`docs/RESEARCH.md`](../../../docs/RESEARCH.md).

- **Tier 1:** `@DhanHQ` playlists/videos. Only source for Dhan-video transcripts.
- **Tier 2:** official Dhan product/docs (ScanX, charts, Options Trader, API at dhanhq.co/docs). Secondary; cannot replace transcripts.
- **Tier 3:** user-approved `EXTERNAL_RESEARCH` videos listed in `config/workspace.yaml` (later / when `enabled: true`). Ideas only; must be tagged; must not silently replace Dhan transcripts. Production indicators remain Dhan-only unless `implementation.indicators` says otherwise.
- **Never claims:** social, downloads, forms, community, contact.

---

## 2. Pipeline stages and required outputs

| Stage | Job | Emit |
|-------|-----|------|
| **1 Discover** | Channel, videos, playlists, membership, metadata | `data/youtube/video_catalog.csv`, `data/youtube/video_catalog.json` |
| **2 Popularity** | Rank with measurable public metrics | Same catalog + rank / `PopularityScore` |
| **Relevance** | HIGH / MEDIUM / LOW; `EXCLUDED_STOCK_ONLY` | Same catalog (do not drop rows) |
| **3 Transcripts** | Public captions only; timestamps; raw + normalized | `data/transcripts/raw/<video_id>.json`, `data/transcripts/normalized/<video_id>.md` |
| **QA** | Numbers, names, timestamps | Flags on those files; no silent “fixes” |
| **4 Intelligence** | Knowledge extraction record — **not** a trading strategy | Claims + topics + indicators + rules (schemas below) |
| **Indicator KB** | One record per indicator | `research/indicator_knowledge_base.md` (official API layer started 2026-09-01; transcript columns still partial), `research/indicator_knowledge_base.json` (not emitted yet) (corpus twin: `research/03_indicator_knowledge_base.md`) |
| **Claims** | One YAML record per substantive claim | Data-model store `research_claims`; corpus `research/02_transcript_index.md` |
| **Strategy specs** | Machine-readable spec (later; after validation) | YAML §53; corpus `research/07_strategy_candidates.md` |
| **Corpus** | Narrative pack for programming (after extraction) | `research/` tree in PLAN.md §51; then `DHAN_RESEARCH_CORPUS.md` |

Do not assume search found every video. Prefer YouTube Data API, channel feeds, playlist enumeration, official channel pages. Search is supplemental.

**PopularityScore** (weights configurable):

```text
PopularityScore =
    normalized_views * 0.55
  + normalized_likes * 0.20
  + normalized_comments * 0.10
  + recency_score * 0.15
```

**HIGH PRIORITY relevance:** options, NIFTY, BANKNIFTY, SENSEX, index derivatives, option buying/selling, option chain, strike, expiry, Greeks, IV, OI, price action, candlesticks, intraday, scalping, breakout/breakdown, momentum, opening, trend, reversal, S/R, VWAP, RSI, Supertrend, MAs, MACD, ADX, volume, volatility, risk, stop/target, sizing, custom/Dhan indicators, leading/lagging, strategy builder, market structure.

**MEDIUM:** transferable TA. **LOW:** investing, valuation, stock recs, MFs/SIPs, unrelated product tutorials.

Extraction-stage workflow (stop before backtest/live): Discover → Popularity → Relevance → Transcript → QA → Topic → Claim → Indicator → Strategy-rule extraction → Independent validation (other teams).

---

## 3. Schemas (field names 1:1 with PLAN.md)

### 3.1 Video catalog (`video_catalog.csv` / `.json`)

```text
video_id
title
url
published_at
duration_seconds
view_count
like_count
comment_count
channel_id
channel_name
playlist_ids
description
caption_available
language
retrieved_at
```

Also capture (discovery objective, not extra schema names): thumbnail, caption/transcript availability, topic classification, popularity rank / `PopularityScore`, relevance band, `STOCK_ONLY` / `EXCLUDED_STOCK_ONLY` when applicable.

### 3.2 Raw transcript JSON (`data/transcripts/raw/<video_id>.json`)

```json
{
  "video_id": "...",
  "source_url": "...",
  "retrieved_at": "...",
  "language": "en",
  "segments": [
    {
      "start": 123.45,
      "duration": 4.2,
      "text": "..."
    }
  ]
}
```

Normalized copy: `data/transcripts/normalized/<video_id>.md` (same provenance; readable for models). If retrieval fails: `TRANSCRIPT_UNAVAILABLE`. Do not invent segments.

### 3.3 Three-layer knowledge (never merge)

Every extracted item is **exactly one** of:

| Layer | Label | Meaning |
|-------|--------|---------|
| A | `SOURCE_FACT` | What Dhan actually said |
| B | `VALIDATION` | What authoritative sources say (do not overwrite Dhan) |
| C | `HYPOTHESIS` | What this project proposes to test |

Team 01 emits `SOURCE_FACT` only. `VALIDATION` → 02/03. `HYPOTHESIS` → 04_quant. Never collapse layers.

### 3.4 Claim record (PLAN.md §52)

```yaml
claim_id:
video_id:
timestamp:
topic:
claim:
claim_type:
source_confidence:
requires_validation:
validation_source:
validation_result:
project_relevance:
```

Every substantive claim also needs: exact transcript timestamp, paraphrased claim, claim type, confidence, **rule vs general education**.

### 3.5 Stage 4 extraction record (per video)

**Metadata:** video ID, title, publication date, views, popularity rank, transcript confidence.

**Topics** (examples): `OPTIONS`, `PRICE_ACTION`, `CANDLESTICKS`, `RSI`, `SUPERTREND`, `RISK_MANAGEMENT`, `OPTION_CHAIN`. Classifier buckets: `PRICE ACTION`, `CANDLESTICKS`, `INDICATORS`, `OPTIONS`, `OPTION CHAIN`, `VOLATILITY`, `MARKET STRUCTURE`, `OPENING`, `SCALPING`, `RISK MANAGEMENT`, `STRATEGY DESIGN`.

**Indicators** (each): name, purpose, category, parameters, timeframe, input price, interpretation, entry use, exit use, limitations.

**Strategy rules** (extract separately, still not a final strategy): market condition, setup, entry, confirmation, stop, target, trailing stop, exit, position sizing, timeframe, instrument.

### 3.6 Indicator KB (`research/indicator_knowledge_base.md` + `.json`)

```text
Indicator
Category
Mathematical definition
Inputs
Default parameters
Dhan parameters
Dhan transcript source
Typical interpretation
Known failure modes
Suitable market regimes
Unsuitable market regimes
Applicable instruments
Applicable timeframes
Potential options application
Data requirements
Backtest candidates
```

Categories (PLAN.md §14): lagging/trend, momentum, volatility, volume/market activity, market structure/price action, options-specific.

### 3.7 Strategy spec YAML (PLAN.md §53) — later emit; do not fill as “validated”

```yaml
strategy_id: STRAT-001
name: Opening Range Momentum
market:
  - NIFTY
  - BANKNIFTY
  - SENSEX
instrument:
  type: INDEX_OPTION
timeframe:
  primary: 5m
  confirmation: 1m
regime:
entry:
confirmation:
stop:
target:
trailing_stop:
position_sizing:
option_selection:
risk_limits:
avoid_conditions:
data_requirements:
backtest_requirements:
```

Label origin: `DHAN-DERIVED` or `PROJECT-DERIVED`. Never invent a strategy and pretend Dhan recommended it.

When a spec is handed to coding (after review), it must also carry: Strategy ID, Source evidence, Source timestamps, Rule definition, Data requirements, Parameters, Assumptions, Known limitations, Backtest design, Validation status. Example status until tests exist: `NOT YET VALIDATED` / `UNVALIDATED`.

### 3.8 Source citation (every Dhan-derived component)

```text
Source: Dhan YouTube
Video: <exact title>
Video ID: <id>
URL: <official URL>
Timestamp: <start-end>
Transcript evidence: <paraphrased statement>
Interpretation: <our interpretation>
Independent validation: <source>
Implementation status: <status>
```

---

## 4. What to document during analysis

For each selected video:

1. **Topics** — from transcript, not title guesswork.
2. **Claims** — §52 YAML; timestamp; paraphrase; type; confidence; rule vs education; layer = `SOURCE_FACT` until validation.
3. **Indicators + params** — name, purpose, category, parameters **exactly as spoken**, timeframe, input price, interpretation, entry/exit use, limitations. Spoken RSI/Supertrend/EMA values are evidence, not hardcoded production defaults.
4. **Rules** — market condition, setup, entry, confirmation, stop, target, trailing stop, exit, position sizing, timeframe, instrument — as separate fields.
5. **Options mapping** (if the video speaks to options; do not invent chain fields): Underlying, Spot, Futures, Expiry, ATM / ITM / OTM strikes, CE/PE LTP, volume, OI, Change in OI, IV, Delta, Gamma, Theta, Vega, Bid, Ask, Bid quantity, Ask quantity. Strike choice is ATM vs 1–2 ITM/OTM vs delta bands — **test, do not assume ATM**.
6. **Data requirements** — every feature:

   ```text
   DATA_SOURCE
   INSTRUMENT
   EXCHANGE_SEGMENT
   CALCULATION
   TIMEFRAME
   ```

   VWAP/volume: do not treat cash-index NIFTY as a traded volume instrument. Name futures vs options vs index explicitly. NIFTY/BANKNIFTY → NSE; SENSEX → BSE.
7. **Status labels** — use **only** Appendix C:

   ```text
   DISCOVERED
   TRANSCRIPT_PENDING
   TRANSCRIPT_VERIFIED
   EXTRACTED
   INDEPENDENTLY_VALIDATED
   HYPOTHESIS
   BACKTEST_PENDING
   BACKTESTED
   OOS_VALIDATED
   WALK_FORWARD_VALIDATED
   ROBUSTNESS_VALIDATED
   PAPER_TRADING
   PRODUCTION_CANDIDATE
   PRODUCTION
   DEGRADED
   REJECTED
   RETIRED
   DATA_INSUFFICIENT
   SOURCE_UNCERTAIN
   ```

   Plus sentinels (not substitutes for Appendix C): `TRANSCRIPT_UNAVAILABLE`, `EXCLUDED_STOCK_ONLY`, `STOCK_ONLY`. Missing evidence: `UNKNOWN`. Unavailable: `NOT AVAILABLE`. Needs a live docs check: `VERIFY BEFORE IMPLEMENTATION`. Red-team fail: `FAILED REVIEW` / `RESEARCH STATUS = FAILED REVIEW`. Do not guess.

---

## 5. Quality rules

- **Numbers are high-risk.** Watch `20` vs `200`, `0.5` vs `5`, `14` vs `40`, `20000` vs `2000`, `9 EMA` vs `20 EMA`, `14 RSI` vs `40 RSI`. Also strike prices and percentages.
- QA every transcript for: missing sections, duplicated text, timestamp anomalies, language mismatch, STT errors, wrong indicator names.
- Uncertain token: `[UNCERTAIN_TRANSCRIPT]`. Never silently correct a number by guesswork.
- Retrieval fail: `TRANSCRIPT_UNAVAILABLE`. Do not hallucinate.
- **No invented parameters.** Identify parameters exactly as spoken. Do not optimize. Do not invent indicator settings, stops, targets, win rates, profitability, API fields, historical availability, or lot sizes.
- Preserve: timestamps, source URLs, original `video_id`, provenance.
- Do not assume an indicator or API field exists in DhanHQ without current docs.
- If required history is missing: `DATA_INSUFFICIENT`. Do not synthesize unavailable history.
- Source uncertain: `SOURCE_UNCERTAIN`. Prefer failure over a fabricated answer.

---

## 6. What NOT to do yet

- **No final strategy.** Stage 4 is a knowledge extraction record. Do not design the production strategy. Do not rank by return. Do not populate backtest scorecards with invented numbers.
- **No Dhan live code in this folder.** No WebSocket collector, no order APIs, no tokens, no `packages/dhan-client` usage here. Scraper/extractor code comes later under `teams/01_research/youtube/src/` only after the company `PLAN.md` board says so.
- Do not implement the collector from this file.
- Do not use other YouTube channels unless they are listed and `enabled: true` in `config/workspace.yaml` as `EXTERNAL_RESEARCH` (Tier 3: ideas only, tagged; never a silent substitute for `@DhanHQ` Dhan-video SOURCE_FACT).
- Do not merge `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`.
- Do not hardcode lot sizes or treat education as proof.

---

## 7. Full spec

Canonical long plan (schemas, stages, Appendix C/D, research tree): [`teams/01_research/youtube/PLAN.md`](PLAN.md).

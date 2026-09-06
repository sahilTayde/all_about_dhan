# RSI + Supertrend

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`  
**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`  
**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.  
See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

Production Dhan indicators stay Dhan-only unless `config/workspace.yaml` `implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH` are ideas only.

Cluster match is **all** of tags `RSI` and `SUPERTREND` on the same catalog row (metadata). Agents still split claims by timestamp when they read transcripts.

## Official Dhan indicator defs (Tier 2)

Catalog: [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · map: [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).

| Name | HQ v2 | Params in official docs |
|------|-------|-------------------------|
| RSI | Conditional Trigger `indicatorName` = **`RSI_14` only** | Period **14** is in the token. No RSI series on `/charts/*`. ScanX support copy uses **75 / 25** bands — **not** annexure |
| Supertrend | **Not** in annexure Indicator Name table | ScanX names an “Intraday Supertrend” screener **without** ATR period/multiplier. Spoken **(10, 3)** is transcript/VALIDATION, not an API field |

Conditional Trigger: **Equities and Indices** only — do not assume `RSI_14` conditions on `OPTIDX`. Compute RSI/ST from documented OHLC if a series is required. `UNKNOWN` if Dhan chart ST matches Wilder ATR(10)×3.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `rsi_supertrend` · tags `RSI, SUPERTREND` · match `all`
**Catalog hits:** 5 · **TRANSCRIPT_VERIFIED:** 1

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `H_6keeRUCDM` | RSI + Supertrend Strategy for Positional and Swing Setups / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `6EDBgspfyQM` | The Only Indicators Masterclass You'll Ever Need / Indicator Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `R4KmCIubaYE` | How To Use Supertrend Indicator / Super Trend & Stochastic RSI Trading Strategy / Intraday Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `CDu_c0yQ5A8` | How to Create a Stock Screener Using Supertrend + RSI / FREE Screener Included / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `UhwDeSK_OGE` | How to Create a Stock Screener Using EMA + RSI / FREE Screener Included / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../candidates/STRAT-011.md`](../candidates/STRAT-011.md) (RSI divergence → Supertrend child, UNVALIDATED).

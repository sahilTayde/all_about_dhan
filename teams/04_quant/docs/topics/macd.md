# MACD

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`
**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`
**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.
See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

Production Dhan indicators stay Dhan-only unless `config/workspace.yaml`
`implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH`
are ideas only.

## Official Dhan indicator defs (Tier 2)

Catalog: [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · map: [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).

| Name | HQ v2 | Params in official docs |
|------|-------|-------------------------|
| MACD fast / slow / hist | Conditional Trigger: **`MACD_12`**, **`MACD_26`**, **`MACD_HIST`** | 12 and 26 baked into names. **No** `MACD_9` / `MACD_SIGNAL` in annexure → signal length `UNKNOWN` |
| Series | **None** on `/charts/*` (OHLC only) | Compute from close if testing STRAT-001; do not invent a `macd` JSON key |

Appel 12/26/9 and spoken “×4” are VALIDATION / SOURCE_FACT — not extra API enums.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `macd` · tags `MACD` · match `any`
**Catalog hits:** 17 · **TRANSCRIPT_VERIFIED:** 0

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `6EDBgspfyQM` | The Only Indicators Masterclass You'll Ever Need / Indicator Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `AiaRSRkj9Fs` | This Momentum Scanner Finds Winning Stocks Before They Rally! 🔥 (Free Screener) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `WbocoVuZSa4` | Best Trading Indicator for Intraday / Intraday Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qJkDsSd487w` | 90% of the Traders use MACD Indicator Wrong! / BankNifty Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `oVGDm2u-4nM` | MACD Trading Secrets REVEALED You Wont Believe How EASY It Is | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `UnhA9rCP64s` | MACD Trading Strategy for Beginners / FREE Screener to Find Setups / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `CFaRXjcvZJs` | MACD + Supertrend Strategy for Swing Traders / Catch Big Moves Early / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `4ZjxjEPBfMI` | Catch the Perfect Swing Entry: RSI + MACD Strategy + FREE Screener / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `TGKsHFOf7SE` | Build Advanced Breakout Screener That Finds Winners | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `GbJd_mWBtmk` | Top 3 Indicators on Dhan Most Traders Use | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `4X5Zvqt_HEE` | Use Indicators for Exit Not Entry! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qh5rL0LYebw` | MACD Trick to Spot Market Reversals Before Anyone Else / Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ROWRA_q4I7A` | Technical Indicator / Episode 5 / Swing Trading Series / Trading / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `fFmcONKy3bA` | Top 5 Technical Analysis Indicators / Moving Average, RSI, Bollinger Bands, MACD, Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `zH968ldAqfM` | MACD Trick to Catch Reversals Early! - #dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ltxTh6Um3xI` | MACD Indicator | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ZWuSLE3piJw` | How To Use MACD Trading Indicator in Stock Market? Learn MACD Trading Strategy in Hindi / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) if a STRAT-ID already covers this topic.

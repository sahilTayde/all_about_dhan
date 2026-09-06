# Options buying

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`  
**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`  
**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.  
See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

Production Dhan indicators stay Dhan-only unless `config/workspace.yaml` `implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH` are ideas only.

## Official Dhan indicator defs (Tier 2)

Catalog: [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · map: [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).

Options **buying** hypotheses should pull **chain + candles**, not a hidden RSI endpoint:

- Chain: `POST /optionchain` — documented `oi`, `implied_volatility`, `greeks.delta|gamma|theta|vega`, bid/ask, volume (methodology `UNKNOWN`).  
- Bars: `POST /charts/historical` / `/charts/intraday` — OHLC + volume only.  
- Named TA (`RSI_14`, `EMA_*`, …): Conditional Trigger **names**, Equities/Indices only — **not** a series on OPTIDX.  
- Supertrend / Power Scalper / “43 Dhan indicators”: **chart/product / transcript**, not HQ fields.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `options_buying` · tags `OPTIONS` · match `any`
**Catalog hits:** 325 · **TRANSCRIPT_VERIFIED:** 10

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `6WZxLShiUT8` | Options Trading Like a Pro! Pick Best Options / Dhan Hai Toh Done Hai! | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `2RnBT9DDDNI` | FREE Option Buying Masterclass: This Changes How You Trade Forever | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `6el9Jqnrdz8` | Hedge Like a Pro: 100% FREE Option Selling Masterclass (Hedging Strategy) / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `YUXJv_xBStw` | Introducing: Order Flow on DEXT T3 Trading Terminal | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `G31RFueZLvk` | How to Find Stocks Today That Can Move Tomorrow / The Complete BTST Masterclass | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `eApl0SfVBBY` | We Built 43 Advanced Trading Indicators for You on Dhan! (How to Use Them) | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `8h9SYvQWKMA` | The New Dhan Charts Every Trader Should Try / Complete Walkthrough | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `HAUSZx-hYdY` | The Ultimate 1-Hour Masterclass on Option Buying Strategies / Option Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `_exmJYgFwFA` | FREE 1-Hour Masterclass on OPTION SELLING / Option Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `gA5FtEnSABM` | Create An Option Trading Strategy in 15 Mins / Option Trading During Bear Market Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `BTe6ekvvDHk` | Buy Gold & Silver Directly From Exchange on Gold Vault by Dhan / The New Way To Buy The Oldest Asset | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_PENDING |
| `5x6bYmCB0Gw` | Now Live: Super Order on Dhan / Set Entry, Target, & Stop Loss in One Order! / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_PENDING |
| `H_-8Nzlb5dY` | The Ultimate Stock Options FREE Masterclass / Unlock Pro-Level Strategies | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `6EDBgspfyQM` | The Only Indicators Masterclass You'll Ever Need / Indicator Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `bNtM7vkGmDo` | Why Most Option Buyers Lose Money (And How to Be the 1%) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `vALrsM3TwcU` | Trade Like the 1%: Option Selling Strategies Revealed / FREE Option Selling Course | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `x5MEUzSBEiA` | Now Live: Power Scalper for Option Trader / Dedicated Terminal for Option Scalping / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `fyvGP_vuw2E` | Trading Without Charts: Only Option Chain Strategy You Should Know / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `d3X5TNpZ0NM` | The Reality of Passive Income from Option Selling (Truth Revealed) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `h9XVkigX4Mg` | 5 Powerful Dhan App Settings Every Trader Should Use Right Now! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `m3NBm5jpmvc` | Best Gold & Silver Trading Strategies / Commodity Trading For Beginners 2024 / Options Trading /Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `mj8jzpSdLfE` | Trading Indicators You MUST Know in 2026 (Special Edition) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Y4MyJIdYPfM` | Option Selling in Volatility: Hedging Strategy That Saves You (FREE Masterclass) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qcg7HfjoCjI` | The Ultimate Matrix Calendar Strategy Masterclass for Options Traders | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `VWa73w1TUTI` | From Auto Rides to Options Trading: - Ft. Trader Rikshawala | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `eaWcOGJqga0` | The 2:16 PM ATM Shift Secret Most Option Traders Miss ⏰👀 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qaQR5hphedQ` | Intraday Scalping Strategy: Scalp Like a Pro with This Easy Setup! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qVlkK4slFjY` | Introducing: Order Flow on DEXT T3 Trading Terminal | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `nnNfJRBBVtA` | Trading Without Charts - Only Option Chain Strategy You Should Know / Support & Resistance / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `DVXOQGK0wio` | How to use Scalper on Charts on Options Trader App Explained in Hindi / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `gQXaA2dPBa8` | Options Trading Strategy with ScanX Screener! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `9LBO9c18mD0` | The Ultimate Trend Acceleration Strategy for Scalpers (Step-by-Step) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `r4jFwxqAKrA` | The Ultimate Bollinger Bands Scalping Trading Strategy for Sensex | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `mh5B111svOc` | The 1:30 PM Expiry Day Strategy / How to Spot Trapped Option Writers | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `jhdkKmutGvA` | Footprint Charts Explained for Indian Traders! (With Real Examples) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `dc91MNBuDnQ` | How to Start Order Flow Trading in India (Step-by-Step Guide in English) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `CRzuVqisVo4` | The ULTIMATE Intraday Strategies For Stock Options Part 1 / Intraday Trading Strategies / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `bfXfZp95x6k` | Nifty Option Buying After 3 PM Strategy! (High Momentum Setup) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Ka0n2ETQi1s` | DOS (Directional Option Selling) Trading Strategy / Advance Algo Trading 2026 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `KwOcnzmtXIQ` | How to use Dhan Webhook on Dhan Charts / Options Trading / Pine Script / Alert Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| … | 285 more in catalog | | | |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) (CE/PE buy-first candidates).

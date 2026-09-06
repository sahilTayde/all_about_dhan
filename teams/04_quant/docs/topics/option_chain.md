# Option chain

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`
**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`
**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.
See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

Production Dhan indicators stay Dhan-only unless `config/workspace.yaml`
`implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH`
are ideas only.

## Official Dhan indicator defs (Tier 2)

Catalog: [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · map: [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).

This cluster is **chain microstructure**, not SMA/RSI. Documented REST (do not invent):

| Endpoint | Documented fields (subset) |
|----------|----------------------------|
| `POST /optionchain` | `data.last_price`; per strike `ce`/`pe`: `average_price`, `greeks.*`, `implied_volatility`, `last_price`, `oi`, `previous_oi`, `previous_volume`, `previous_close_price`, `security_id`, `top_bid_*`, `top_ask_*`, `volume` |
| `POST /optionchain/expirylist` | `data[]` expiry dates `YYYY-MM-DD` |
| Quote / full feed | `oi`, `oi_day_high`, `oi_day_low` (NSE_FNO note on quote page) |
| `POST /charts/rollingoption` | request `requiredData`: `open,high,low,close,iv,volume,strike,oi,spot` |

**Not** documented as HQ series: OI Profile widget, “trapped writers” overlays, DEXT order-flow. Rate limit: **1 unique chain request / 3 s**.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `option_chain` · tags `OPTION_CHAIN` · match `any`
**Catalog hits:** 47 · **TRANSCRIPT_VERIFIED:** 1

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `HAUSZx-hYdY` | The Ultimate 1-Hour Masterclass on Option Buying Strategies / Option Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `juQGb7DIWck` | This Open Interest Strategy Will Blow Your Mind! / Predict Market Movements Like a Pro / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `0TdCtYcEHpQ` | Identify Trades Easily With Dhan Open Interest Profile / Open Interest Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `vALrsM3TwcU` | Trade Like the 1%: Option Selling Strategies Revealed / FREE Option Selling Course | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `x5MEUzSBEiA` | Now Live: Power Scalper for Option Trader / Dedicated Terminal for Option Scalping / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `fyvGP_vuw2E` | Trading Without Charts: Only Option Chain Strategy You Should Know / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `lYHayytb6rA` | Best Intraday Trading Strategy For Beginners (2024) / Open Interest Indicator Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `nnNfJRBBVtA` | Trading Without Charts - Only Option Chain Strategy You Should Know / Support & Resistance / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `mh5B111svOc` | The 1:30 PM Expiry Day Strategy / How to Spot Trapped Option Writers | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Ka0n2ETQi1s` | DOS (Directional Option Selling) Trading Strategy / Advance Algo Trading 2026 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `FjFlFXTVc4o` | Catch Intraday Trades Easily with OI Profile / Intraday Trading Strategies / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `W7qEuKM46LQ` | 5 Hidden Dhan App Features Every Trader & Investor Must Use | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `mx_zBHTfwrM` | The Only Advanced Trading Terminal You Need in 2026 / DEXT T3 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Qm_XgltdwqM` | Master Open Interest Trading With This ONE Simple Trick / Open Interest Trading Strategy / Part 1 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `0zWOX6JZtfc` | Identify Swing Trades Easily with OI Profile / Swing Trading Strategies / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `aA3Uxi6Mec0` | Master Open Interest Trading Strategy In 10 Mins / Open Interest Trading Strategy / Part 2 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Ij5s-kfjkQ8` | Open Interest – The Hidden Clue to Killer Trades! / Open Interest Analysis / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `pXFutKPXaOI` | Introducing Advanced OI Analytics on Options Trader Web | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `nH828FsV_ms` | Learn Open Interest Strategies / OT Web | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `_YomrvTKpXM` | Find Important Levels using Options Chain / Analyse Option Chain like a PRO / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ZXVwpwRY4gs` | Build an Option Chain Algo Using Dhan API / Advanced Algo Trading Series 2026 / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `T9VIlaiGeIk` | Spot Market Reversals Early / Open Interest Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `UyclpeGSyWs` | All About Open Interest / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `myc2R8vdqB8` | LIVE: Complete Option Chain Analysis Ft. Himanshu Arora, SuperTrader | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `CYYJt3KXnZQ` | Swing Trading Strategy Using F&O Data / Swing Trading Guide for Traders | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `hBHiNbQyIyM` | Trading Without Charts / Option Chain Strategy Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `a0sRF9viSto` | Advanced Options Strategies: Mastering Open Interest with Super Order / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `BmeNBt3TK2U` | Open Interest Indicator Strategy Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qC2EhoVRDI8` | How to Use Advanced Option Chain / Catch Big Moves with Advanced Option Chain / Options Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `YFS1PLp0V6g` | Expired Option Data / Dhan API / Advanced Algo Trading 2026 / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `JbI5egSGiF8` | Introducing Options Data on DhanHQ APIs / Build Option Strategies Faster | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `cg7j8z8bbUQ` | Option Chain Alone Won’t Make You Money | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `IHZQln-ZbYY` | Options Trading Strategy (Part 2) / How to Catch Directional Moves / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `mgOthYgN4Vo` | Advanced Algo Trading Series / Episode 2: How To Create A Scanner & Scanning Option Chain / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `C_vjGCfl3nY` | Open Interest Indicator Secret Trading Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `33YfPdy7ZFM` | Option Chain Interpretation / Episode 4 / Stock Options Trading Series / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `YiNfee9pPE4` | Advanced Options Masterclass Part 2: Strategies That Actually Work | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `3TSZG7ZFwQk` | Commodity Option Chain - EXPLAINED  #stockmarket #commodities | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `S4L4hDUOphQ` | How to use Option Chain on Dhan Web? Option Chain Explained in Hindi / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `8o1BgWs9mtw` | Insightful Options Chain on Dhan Explained in Hindi / Top OI & IV , Open High/Low / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| … | 7 more in catalog | | | |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) if a STRAT-ID already covers this topic.

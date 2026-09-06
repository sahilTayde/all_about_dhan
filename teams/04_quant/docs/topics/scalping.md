# Scalping

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
| Fast MAs | Trigger names `EMA_5`/`EMA_10`/`EMA_20` (and SMA counterparts) | Period in the token. **No** series endpoint |
| Intraday bars | `/charts/intraday` intervals **1, 5, 15, 25, 60** | **2m / 3m not listed** → STRAT-006 2m is a resample **HYPOTHESIS** |
| Supertrend / Hull / Power Scalper / dual ST | **Not** in annexure | Chart / Options Trader product / transcripts |
| VWAP | See [`vwap.md`](vwap.md) `average_price` / ATP | — |

Do not live-wire Conditional Trigger for scalps. Feed ATP/LTP/depth are **quotes**, not indicators.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `scalping` · tags `SCALPING` · match `any`
**Catalog hits:** 81 · **TRANSCRIPT_VERIFIED:** 6

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `qSgKA0-T7Uw` | Ultimate Guide to Super-Fast Scalping Tool Setup / Dhan Hai Toh Done Hai! | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `pvmvkiS1cx4` | The 2-Minute Scalping Strategy That Actually Works / Scalping Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `YUXJv_xBStw` | Introducing: Order Flow on DEXT T3 Trading Terminal | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `6E_K1wVkHyw` | Secret Scalping Indicators That Only Pro-Traders Know / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `mPKASwm6Oqk` | Secret Scalping Indicators That Only Pro-Traders Know / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `pUg_7sPauQA` | VWAP Scalping Setup: 3 Rules Every Trader Should Know | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `dHaKGNOY-cM` | Ultimate Scalping Trading Strategy (Power Scalper) / High-Probability Setup | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `rd3Rnh_5i9g` | First 30 Minutes Scalping Strategy for Nifty 50 (High-Probability Setup) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `x5MEUzSBEiA` | Now Live: Power Scalper for Option Trader / Dedicated Terminal for Option Scalping / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `9_XF1CkOnPk` | Dual Supertrend Alignment Scalping Trading Strategy (Dhan Power Scalper Setup) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `bwe2olO-Hhs` | Sensex Scalping Strategy Revealed / The Technique Most Traders Miss | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `i1T1QOn-KXs` | Scalping Strategy : Catch Multiple Moves With Moving Average Indicator / SMA & EMA Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ZSeYRvr8MkA` | The Scalping Strategy Every Intraday Trader Should Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `BlmC8sHRQjM` | FREE Scalping Masterclass / Mindset, Strategies & Tools to Win in Trading /Scalping Trading Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `xsTo0tPRQrY` | Live : Scalping Masterclass Ft. Himanshu Arora, SuperTrader | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Au3FtzDfqC8` | High-Probability Scalping Strategy Using Hull Suite and EMA Indicators | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `JycuWhEnlF0` | How to use TV Scalper on Dhan Charts? Scalping on tv.dhan.co Explained / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `O5MXKZM3S6A` | Scalping Like a Pro: Power Scalper Strategy (High Probability) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `WOi7DllhnM0` | Institutional Footprint Strategy Using Dhan Power Scalper | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `7WDJaqMxl1Y` | 3 Scalping Indicators on Dhan Charts Every Trader Must Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `8ydGzmamQ-I` | Scalping Hacks : Secret Indicator to Beat the Market Every Time! Best Scalping Strategies/ Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qaQR5hphedQ` | Intraday Scalping Strategy: Scalp Like a Pro with This Easy Setup! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `UsfMeZ7pMyE` | 5 Scalping Rules Pros Don’t Break / Strategy + Examples / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `qVlkK4slFjY` | Introducing: Order Flow on DEXT T3 Trading Terminal | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `xqAeX2SAeck` | FREE 1.5-Hour Advanced Scalping Masterclass: Strategy That Can Change Results | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `DVXOQGK0wio` | How to use Scalper on Charts on Options Trader App Explained in Hindi / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `16JdPj6EvOk` | Momentum Scalping Strategy You Shouldn't Miss / Momentum Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `ctjo0mXYoAQ` | 3 Secret Indicators on Dhan Charts Every Trader Must Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `9LBO9c18mD0` | The Ultimate Trend Acceleration Strategy for Scalpers (Step-by-Step) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `iLXZ6nf9H6Q` | Best 9:45 AM Scalping Strategy for INTRADAY TRADERS / Scalping Trading Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `yU6qkuw9TPc` | Best Time to Do Scalping in Intraday (High Probability Hours) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `r4jFwxqAKrA` | The Ultimate Bollinger Bands Scalping Trading Strategy for Sensex | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `77OgweNHNc4` | 3 Scalping Indicators Every Trader Must Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `GiSBvGrPFFI` | SCALPING MISTAKES: Why Your Trades Fail (Fix This) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `kRezq4pSODM` | Top 5 Golden Rules of Scalping You Should Know / Scalping Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `YNOU7-39cDI` | The 200 Day EMA Strategy Every Scalper Should Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `jhdkKmutGvA` | Footprint Charts Explained for Indian Traders! (With Real Examples) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `62AHquT50dE` | Nifty & BankNifty Scalping Strategy You Should Know! VWAP & DMI Indicators for Scalping / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `dc91MNBuDnQ` | How to Start Order Flow Trading in India (Step-by-Step Guide in English) | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `dfm9hsYSv5A` | Smart Money SCALPING STRATEGY Using Liquidity Grabs | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| … | 41 more in catalog | | | |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) if a STRAT-ID already covers this topic.

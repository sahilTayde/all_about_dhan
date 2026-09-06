# VWAP

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `STUB`  
**Layer:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`  
**Compliance:** education ≠ proof. Not investment advice. No guaranteed profits.  
See [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

Production Dhan indicators stay Dhan-only unless `config/workspace.yaml` `implementation.indicators` is not `dhan_only`. Videos tagged `EXTERNAL_RESEARCH` are ideas only. VWAP/volume on index options must use **futures or option tape**, never cash-index volume (see master plan).

## Official Dhan indicator defs (Tier 2)

Catalog: [`../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) · map: [`../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).

| Name | HQ v2 | Params in official docs |
|------|-------|-------------------------|
| Session / chart VWAP | **Not** an annexure `indicatorName` | Chart-only |
| Day VWAP snapshot | `POST /marketfeed/quote` field **`average_price`**: “Volume weighted average price of the day” | Not a bar series; identity vs chart VWAP / WS **ATP** = `UNKNOWN` |
| VWMA / AVWAP | **Not** documented as API names | Transcript / chart |

`/charts/intraday` returns `volume` per bar so a **client** can compute VWAP — that computation is VALIDATION/HYPOTHESIS, not a Dhan REST indicator.

## Catalog cluster (auto)

<!-- CLUSTER_AUTO:START -->

**Cluster:** `vwap` · tags `VWAP` · match `any`
**Catalog hits:** 20 · **TRANSCRIPT_VERIFIED:** 1

Pointers only — agents must read transcripts and write claims as `SOURCE_FACT`,
then this file stays `HYPOTHESIS` / `UNVALIDATED`. Do not paste a transcript dump here.

| video_id | title | source | band | transcript |
|---|---|---|---|---|
| `pUg_7sPauQA` | VWAP Scalping Setup: 3 Rules Every Trader Should Know | `dhanhq` / `DHAN-DERIVED` | HIGH | TRANSCRIPT_VERIFIED |
| `6EDBgspfyQM` | The Only Indicators Masterclass You'll Ever Need / Indicator Strategy / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Jk0vBgGupJo` | Master Order Flow with This Powerful VWAP Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `bwe2olO-Hhs` | Sensex Scalping Strategy Revealed / The Technique Most Traders Miss | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `BlmC8sHRQjM` | FREE Scalping Masterclass / Mindset, Strategies & Tools to Win in Trading /Scalping Trading Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `77OgweNHNc4` | 3 Scalping Indicators Every Trader Must Know | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `62AHquT50dE` | Nifty & BankNifty Scalping Strategy You Should Know! VWAP & DMI Indicators for Scalping / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `kAF642I922g` | VWAP + Price Action: The Intraday Setup That Works! | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `Z2kODqS0wdU` | The ONLY VWAP Trading Video You'll EVER Need / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `6MwHaO-SuyQ` | INTRADAY Traders Love These 3 Volume Indicators | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `E6jyntDzoWE` | CPR Trading Strategy: Breakout & Range Rules that Work / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `tA8C3rNKIvY` | How to Add Custom Formula in Watchlist / DEXT T3 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `sDWXRDZdijU` | Volume Indicators Smart Traders Use | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `GZ1hRZgFJU4` | BankNifty Intraday Strategy Using AVWAP & Pivot Points 🔥 | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `GbJd_mWBtmk` | Top 3 Indicators on Dhan Most Traders Use | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `2GyIsmRrSDI` | Scalping Trading ke Liye Sabse Zaroori Cheez Kya Hai? | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `6orcWAYiN5s` | Top Trader Reveals BEST Scalping Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `e5v-neMausw` | BankNifty Intraday Confluence Strategy | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `T4EWULsmCjE` | How to Use VWAP Trading Strategy Explained in Hindi - VWAP Indicator Strategy For Day Trading / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |
| `yGpcwJ4ot-c` | How to Use VWAP Trading Strategy? VWAP Indicator Trading Strategy For Intraday Trading / Dhan | `dhanhq` / `DHAN-DERIVED` | HIGH | DISCOVERED |

<!-- CLUSTER_AUTO:END -->

## SOURCE_FACT (team 01 — fill from transcripts)

_Empty until research extracts claims with video_id + timestamps._

## VALIDATION (teams 02/03 — books from workspace.yaml)

_Empty. Books listed in `config/workspace.yaml` `sources.books` are VALIDATION only._

## HYPOTHESIS (team 04 — per-topic spec, not one blob)

_Empty. Do not claim edge. Mark UNVALIDATED until backtest + review._

## Linked candidates

See [`../candidates/STRAT-003.md`](../candidates/STRAT-003.md) if still the VWAP candidate.

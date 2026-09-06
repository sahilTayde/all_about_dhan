# Dhan official API ↔ VALIDATION layer map

**Team:** 02_phd_math  
**Layer B:** independent math. Does **not** overwrite Dhan docs or transcripts.  
**Retrieved with:** [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md) (2026-09-01).  
**Books (VALIDATION only):** Murphy *TA of the Financial Markets*; Natenberg *Option Volatility and Pricing* — `config/workspace.yaml` `sources.books`.  
**Production:** Dhan-only indicators (`implementation.indicators: dhan_only`). Textbook formulas are **validation tags**, not a license to ship a non-Dhan Supertrend as “the Dhan indicator.”

Narrative twin (research corpus): [`research/indicator_knowledge_base.md`](../../../research/indicator_knowledge_base.md). Existing concept checks: [`VALIDATION_MATH.md`](VALIDATION_MATH.md).

Verdict vocabulary: `supported` | `partially_supported` | `context-dependent` | `unsupported` | `UNKNOWN`.

---

## How PhDs should use this

1. If a candidate needs a **named HQ trigger** (`RSI_14`, `EMA_20`, …): use only annexure names; periods are in the token. Extra knobs not in docs → `UNKNOWN`.  
2. If a candidate needs a **series** (every bar RSI/ST/VWAP): HQ v2 gives **OHLC+volume (+OI)**. Computation is **our VALIDATION implementation**, then compared to Dhan **charts** (Tier 2 UI) and spoken SOURCE_FACT — never claimed as a hidden REST field.  
3. Supertrend, session VWAP, VWMA, ADX, Hull: **chart / transcript**, not annexure. Do not invent `SUPERTREND_10_3` as an API enum.  
4. Conditional Trigger is **Equities and Indices** only (official note). Index-**options** strategies that fire on `OPTIDX` RSI: **not documented**. Prefer futures/index OHLC compute + option chain for execution hypotheses.  
5. No live trading. No profitability.

---

## Map table

| Dhan official token / field | Surface | VALIDATION definition (independent) | Match? | Strategy note |
|-----------------------------|---------|--------------------------------------|--------|----------------|
| `SMA_n` (`n` ∈ 5,10,20,50,100,200) | Conditional Trigger `indicatorName` | SMA = mean of last *n* closes (Murphy ch. on MAs) | **supported** as the usual SMA; **UNKNOWN** if Dhan uses close vs typical price | Trigger only; no series endpoint |
| `EMA_n` (same *n* set) | same | EMA with α = 2/(n+1) is the common convention | **partially_supported** — seed / Wilder vs “standard” EMA **UNKNOWN** in Dhan docs | Same |
| `RSI_14` | same | Wilder RSI, period 14 (Wilder 1978; Murphy) | **supported** as Wilder’s usual default; **UNKNOWN** if Dhan uses Wilder smoothing vs SMA-RSI (Cutler) | ScanX product copy uses **75 / 25** bands — **not** in annexure. Wilder 70/30 is VALIDATION folklore, not Dhan API |
| `ATR_14` | same | Wilder ATR, period 14 | **supported** as common default; true-range averaging method **UNKNOWN** in Dhan docs | Supertrend in literature is often ATR×multiplier — **Dhan does not name Supertrend here** |
| `BB_UPPER` / `BB_LOWER` | same | Bollinger: SMA ± k·σ (typical 20, k=2) | **context-dependent** — length and *k* **not documented** | Do not hardcode 20,2 as “Dhan official” |
| `STOCHASTIC` | same | %K / %D (typical 14,3,3) | **UNKNOWN** params | — |
| `STOCHRSI_14` | same | Stoch of RSI | **UNKNOWN** extra params | — |
| `MACD_12` | same | EMA(12) of price (fast) | **partially_supported** — “short-term component” matches Appel fast EMA **if** close-based | Appel default 12/26/9: **9 (signal) not in annexure** |
| `MACD_26` | same | EMA(26) of price (slow) | same | — |
| `MACD_HIST` | same | Usually MACD line − signal | **UNKNOWN** without documented signal length | HAUS “12 and 26” is SOURCE_FACT; hist construction `VERIFY` vs Dhan charts |
| Supertrend | **not in annexure** | Common TV-style: ATR(period)×multiplier bands, close flip | VALIDATION default 10,3 is **textbook/TV common**, **not** an HQ field. `VALIDATION_MATH.md`: common default, not unique truth | STRAT-003/011 params are **HYPOTHESIS / spoken**, not API |
| Session VWAP | **not in annexure** | Σ(P·V)/ΣV from session open | **supported** as math; **unsupported** on cash index (no tape) | Quote `average_price` = “VWAP of the day” — **UNKNOWN** vs bar VWAP / typical price |
| `average_price` (quote REST) | `/marketfeed/quote` | Docs: volume-weighted average **of the day** | **partially_supported** as a day VWAP snapshot | Not VWAP bands; not AVWAP |
| `ATP` (WS quote/full) | Live Market Feed | Average Trade Price (name only) | **UNKNOWN** vs `average_price` vs session VWAP | Do not collapse symbols |
| `volume` (charts/quote/feed) | several | Traded volume of **that instrument** | **supported** | Never use IDX_I cash-index volume as VWAP tape |
| `oi`, `oi_day_high`, `oi_day_low` | quote / full feed | Exchange OI | **supported** as OI; change-in-OI = `oi − previous_oi` on chain | Desk: OI ≠ prediction. See PERSONA |
| `previous_oi` | option chain | Previous day OI | **supported** as a lag-1 snapshot | Intraday ΔOI needs live `oi` vs a stored baseline (`UNKNOWN` if HQ exposes print-level ΔOI) |
| `greeks.*` | option chain | Hull / BSM or Black–76 ∂premium | **UNKNOWN** vendor model | Natenberg: use for **risk**, not “win probability” |
| `implied_volatility` | option chain + rolling `iv` | IV from some inversion | **UNKNOWN** methodology | — |
| Charts `open,high,low,close,volume,timestamp` | `/charts/*` | Standard candles | **supported** | Input to **our** TA; 3m interval **not** in `{1,5,15,25,60}` |
| ScanX “Overbought RSI > 75” | product support | Threshold choice | **context-dependent** heuristic, not a theorem | Do not treat 75 as Wilder law |
| ScanX “Intraday Supertrend” | product support | Unspecified ST | **UNKNOWN** period/multiplier | Chart-only |

---

## Compute path for backtests (later; not this ticket)

Official **inputs**: `POST /charts/historical` and `POST /charts/intraday` (plus chain for options).  
Official **named triggers**: `/alerts/orders` — **not** a historical series; **not** documented for F&O conditions; **do not** use for live orders in this repo.

If Dhan chart Supertrend ≠ our ATR(10)×3: record `partially_supported` / `SOURCE_UNCERTAIN`. Do not “fix” Dhan by silently swapping libraries.

---

## Open UNKNOWN (math + API)

- Bollinger length / *k*.  
- Stochastic and StochRSI extra periods.  
- MACD signal / histogram exact construction.  
- EMA seed.  
- RSI Wilder vs SMA-RSI.  
- Supertrend ATR period, multiplier, close vs HL2, and whether ScanX matches tv.dhan.co.  
- `average_price` vs ATP vs chart VWAP.  
- IV / Greeks engine.  
- Conditional Trigger evaluation on **index** (`IDX_I`) vs **futures** for the same underlier.

Handoff: 04_quant may cite this map in topic files. Still `UNVALIDATED` for any P&L.

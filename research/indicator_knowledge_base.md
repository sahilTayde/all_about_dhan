# Indicator knowledge base

**Status:** `DRAFT` / `EXTRACTED` (official API layer) / transcript columns still **partial**.  
**Layers:** do not collapse `SOURCE_FACT` / `VALIDATION` / `HYPOTHESIS`.  
**Production:** Dhan-only (`config/workspace.yaml` `implementation.indicators: dhan_only`).

Corpus twin (PLAN.md): `research/03_indicator_knowledge_base.md` — **not created**; this file is the living KB.  
Official catalog: [`teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../teams/01_research/docs/DHAN_OFFICIAL_INDICATORS.md).  
PhD map: [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md).  
JSON twin (`indicator_knowledge_base.json`): **not emitted** this pass (`DATA_INSUFFICIENT` for a full transcript-param dump).

YouTube-derived rows: fill **Dhan transcript source** only from `@DhanHQ` captions (`SOURCE_FACT` handoffs). There is **no** pre-existing YouTube indicator KB file in this repo as of 2026-09-01.

---

## Schema (ANALYSIS.md §3.6)

Each row uses: Indicator · Category · Mathematical definition · Inputs · Default parameters · Dhan parameters · Dhan transcript source · Typical interpretation · Known failure modes · Suitable / unsuitable regimes · Instruments · Timeframes · Options application · Data requirements · Backtest candidates.

**Dhan parameters** here means: annexure token **or** documented REST field — else `UNKNOWN` / chart-only.

---

## Official API indicators (Conditional Trigger names)

Category: as VALIDATION classifies them. Mathematical definition = independent (Layer B), not a Dhan formula page (Dhan does not publish SMA/RSI equations on the annexure).

| Indicator | Category | Mathematical definition (VALIDATION) | Inputs | Default parameters (VALIDATION) | Dhan parameters (official) | Dhan transcript source | Typical interpretation | Known failure modes | Suitable regimes | Unsuitable regimes | Instruments | Timeframes | Potential options application | Data requirements | Backtest candidates |
|-----------|----------|--------------------------------------|--------|----------------------------------|----------------------------|------------------------|----------------------|---------------------|------------------|--------------------|-------------|------------|-------------------------------|-------------------|---------------------|
| SMA | lagging/trend | Mean of last *n* closes | close | *n* chosen by user | `SMA_5`…`SMA_200` **names only** | *empty — extract* | Price vs MA | Whipsaw in chop | Trend | Range | Equity / index **triggers**; F&O condition **not documented** | Annexure eval: `DATE`/`ONE_MIN`/`FIVE_MIN`/`FIFTEEN_MIN`; JSON sample `DAY` (`VERIFY`) | Filter on index, execute on options (hypothesis) | OHLC if computing; else trigger API | STRAT-001 MA stack (spoken 10/30/100 — **not** all in annexure: no SMA_30) |
| EMA | lagging/trend | Exponential MA | close | α=2/(n+1) common | `EMA_5`…`EMA_200` names | *empty — extract* | Fast/slow stack | Lag vs noise | Trend | Chop | same | same | STRAT-006 EMA 10/20 | same | STRAT-004 Super Scalper EMAs **UNKNOWN** |
| RSI | momentum | Wilder RSI | close | 14; bands 30/70 (book) | **`RSI_14` only** | H_6kee (cluster); period often unspoken | OB/OS, divergence | Divergences fail in strong trend | Reversal hypotheses | Strong trend (OB can persist) | Trigger on EQ/IDX; series from OHLC | 14 locked in name | STRAT-011 | `/charts/*` or trigger | STRAT-011 |
| ATR | volatility | Wilder ATR | high, low, close | 14 | **`ATR_14` only** | *empty* | Volatility / stop width | Not a direction | All (risk) | — | same | 14 locked | Stops in points | OHLC | Supertrend input (chart) |
| Bollinger | volatility | SMA ± kσ | close | often 20, 2 | `BB_UPPER`, `BB_LOWER`; *k* **UNKNOWN** | *empty* | Band walk / squeeze | Walks in trend | Range / squeeze | Strong trend | same | **UNKNOWN** length | Scalping BB videos | OHLC | scalping cluster |
| Stochastic | momentum | %K/%D | H,L,C | often 14,3,3 | `STOCHASTIC`; params **UNKNOWN** | *empty* | OB/OS | Same as RSI | Range | Trend | same | **UNKNOWN** | — | OHLC | — |
| Stochastic RSI | momentum | Stoch of RSI | RSI | 14 + stoch params | `STOCHRSI_14`; extra **UNKNOWN** | video titles (R4KmCIubaYE) | Faster RSI | Noisier | — | — | same | 14 in name | — | OHLC | — |
| MACD | lagging + momentum | EMA_fast − EMA_slow; signal; hist | close | Appel 12/26/9 | `MACD_12`, `MACD_26`, `MACD_HIST`; **no signal name** | HAUSZx spoken 12/26; ×4 **SOURCE_UNCERTAIN** | Hist / cross | Lag | Trend | Chop | same | **UNKNOWN** signal | STRAT-001 | OHLC | STRAT-001 |

---

## Documented snapshot fields (not TA names)

| Indicator | Category | Mathematical definition | Inputs | Default parameters | Dhan parameters | Dhan transcript source | Typical interpretation | Known failure modes | Suitable regimes | Unsuitable | Instruments | Timeframes | Options application | Data requirements | Backtest candidates |
|-----------|----------|-------------------------|--------|--------------------|-----------------|------------------------|----------------------|---------------------|------------------|------------|-------------|------------|---------------------|-------------------|---------------------|
| Day VWAP snapshot | volume / activity | Docs: volume-weighted average **of the day** | trades | session | REST `average_price`; WS `ATP` (**UNKNOWN** if identical) | 2RnBT9 futures VWAP (SOURCE_FACT) | Fair-value magnet | Cash-index misuse | Intraday | Index without volume | **Futures or options tape**, not IDX_I volume | day | STRAT-003 | `/marketfeed/quote` or feed; **not** a history of VWAP bars | STRAT-003 |
| Open interest | options-specific | Exchange OI | contract | — | `oi`, `previous_oi`, `oi_day_high`, `oi_day_low` | many option-chain videos | Positioning / squeeze narratives | OI up ≠ direction | All F&O | Treating OI as a crystal ball | NSE_FNO / BSE_FNO | snapshot + chain | STRAT-010 overlay | quote / chain / feed | option_chain topic |
| Implied vol / Greeks | options-specific | Model-dependent | chain | — | `implied_volatility`, `greeks.delta|gamma|theta|vega` | HAUS / gA5 | Risk / strike pick | Vendor IV **UNKNOWN** | — | Conviction = delta (**unsupported**) | OPTIDX | snapshot | STRAT-005 | `/optionchain` | STRAT-005 |

---

## Chart-only / product-only (no HQ series)

| Indicator | Category | Mathematical definition | Inputs | Default parameters | Dhan parameters | Dhan transcript source | Notes |
|-----------|----------|-------------------------|--------|--------------------|-----------------|------------------------|-------|
| Supertrend | lagging/trend | ATR bands, close flip (common) | H,L,C | VALIDATION often 10,3 | **NONE in annexure.** ScanX names “Intraday Supertrend” without params | 2RnBT9 ST(10,3); H_6kee | **Chart-only API-wise.** Production still Dhan **charts/spoken**, not a third-party Pine |
| VWMA | volume | Volume-weighted MA | price, volume | spoken 20 | **NONE** | 2RnBT9 | Not in annexure |
| AVWAP / CPR / DMI / Hull / Power Scalper | mixed | *per transcript* | — | — | **NONE** | titles + unverified transcripts | Chart / product |
| ScanX RSI 75 / 25 | momentum | Thresholds | RSI | 75 / 25 in **support copy** | Not annexure | — | Product screener, not REST |

---

## Backtest data contract (honest)

```text
DATA_SOURCE: DhanHQ v2 POST /charts/historical | /charts/intraday  (OHLC+volume; oi optional)
             + POST /optionchain for strikes  (not TA)
INSTRUMENT: FUTIDX / OPTIDX as required; never cash-index volume for VWAP
EXCHANGE_SEGMENT: NSE_FNO or BSE_FNO (SENSEX)
CALCULATION: client-side TA unless using Conditional Trigger (EQ/IDX only; not a series)
TIMEFRAME: documented 1,5,15,25,60 min or daily; 3m = UNKNOWN / resample hypothesis
```

---

## What this file is not

- Not proof of edge.  
- Not a live-trade playbook.  
- Not a dump of 2,034 transcripts. Fill spoken params in team 01 handoffs, then update rows.

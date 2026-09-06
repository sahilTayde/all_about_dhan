# Dhan official indicators (Tier 2 docs)

**Team:** 01_research  
**Layer:** `SOURCE_FACT` of **what Dhan documents today** — not a transcript, not a strategy.  
**Retrieved:** 2026-09-01 from current official pages (listed below).  
**Status:** `EXTRACTED` / `VERIFY BEFORE IMPLEMENTATION` where the live page is incomplete or inconsistent.  
**Production rule:** `config/workspace.yaml` `implementation.indicators: dhan_only`. Do not invent API fields. Missing → `UNKNOWN`.

This file is the clubbed input for PhD / quant strategy docs. Companion map: [`research/indicator_knowledge_base.md`](../../../research/indicator_knowledge_base.md) and [`teams/02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md). Ticket: [`teams/00_orchestrator/docs/TASK_DHAN_INDICATORS.md`](../../00_orchestrator/docs/TASK_DHAN_INDICATORS.md).

**Not used as official:** blogs, TradingView public scripts, social, `docs.dhan.co` (no results on 2026-09-01). Canonical API host: [https://dhanhq.co/docs/v2/](https://dhanhq.co/docs/v2/). Marketing/MCP portal: [https://docs.dhanhq.co/](https://docs.dhanhq.co/) (does not define indicator math).

---

## One-screen verdict for later agents

| Surface | Computes / returns named TA indicators? | What it actually is |
|---------|------------------------------------------|---------------------|
| **Conditional Trigger REST** | **Yes, as trigger names** — not a time series | `condition.indicatorName` compared to a value / another indicator / close; can place orders when true |
| **Historical / intraday charts REST** | **No** | OHLC + volume (+ optional OI). Client must compute TA |
| **Market Quote REST** | **No TA names** | Snapshot LTP/OHLC/depth/OI/volume; `average_price` = “Volume weighted average price of the day” |
| **Live Market Feed WS** | **No TA names** | LTP, ATP, volume, OI, depth |
| **Option Chain REST** | **No TA names** | Strike-wise OI, IV, Greeks, bid/ask, volume |
| **Expired / rolling options REST** | **No TA names** | Rolling ATM±N OHLC/IV/OI/spot |
| **ScanX / charts / app alerts** | **Product UI only** | No scanner REST on dhanhq.co/docs/v2. Supertrend / RSI screeners are chart-or-screener, not API series |

There is **no** documented `GET /indicators/{rsi|supertrend|…}` that returns a computed series.

---

## A. Official API that names indicators

**Page:** [Conditional Trigger](https://dhanhq.co/docs/v2/conditional-trigger/)  
**Annexure names:** [Annexure — Indicator Name](https://dhanhq.co/docs/v2/annexure/)

| Method | Path |
|--------|------|
| POST | `/alerts/orders` |
| PUT | `/alerts/orders/{alertId}` |
| DELETE | `/alerts/orders/{alertId}` |
| GET | `/alerts/orders/{alertId}` |
| GET | `/alerts/orders` |

Base URL on the page: `https://api.dhan.co/v2/…`

**Scope (quoted from the page):** “Conditional Triggers are currently supported only for **Equities and Indices**.” Condition `exchangeSegment` sample enums: `NSE_EQ`, `BSE_EQ`, `IDX_I`. **`NSE_FNO` / `BSE_FNO` are not listed** on that page → index-option **contracts** cannot be assumed as the *condition* instrument. `UNKNOWN` whether an equity/index condition may fire an F&O order (orders table allows general exchange segments). **Do not live-trade this.**

**This is not an indicator data API.** Responses are `alertId` / `alertStatus` (and GET returns the stored condition + `lastPrice`). Docs do **not** return `rsi`, `sma`, `macd` numeric series.

### Documented request fields (condition object)

From the Place Conditional Trigger table (names as printed):

| Field | Required? | Sample / enums as printed |
|-------|-----------|---------------------------|
| `condition.comparisonType` | required | Annexure: `TECHNICAL_WITH_VALUE`, `TECHNICAL_WITH_INDICATOR`, `TECHNICAL_WITH_CLOSE`, `PRICE_WITH_VALUE` |
| `condition.timeframe` | required (table) | Table enums: `DATE`, `ONE_MIN`, `FIVE_MIN`, `FIFTEEN_MIN`. Sample JSON uses `"timeFrame": "DAY"` |
| `condition.exchangeSegment` | required | `NSE_EQ`, `BSE_EQ`, `IDX_I` |
| `condition.securityId` | required | string |
| `condition.indicatorName` | conditionally required | Annexure list (below) |
| `condition.operator` | required | Annexure operators |
| `condition.comparingValue` | conditionally required | number |
| `condition.comparingIndicatorName` | conditionally required | Annexure list |
| `condition.expDate` | required | date; “Default : 1 year” |
| `condition.frequency` | required | sample `ONCE` (other values: **UNKNOWN** / not tabulated) |
| `condition.userNote` | optional | string |

**VERIFY (do not guess):**

- JSON key `timeFrame` vs table `timeframe`.
- Sample value `DAY` vs table enum `DATE`.
- Whether `SIXTY_MIN` or other bars exist: **not listed** → `UNKNOWN`.
- DhanHQ-py docs fetched 2026-09-01 do **not** document a wrapper for `/alerts/orders`. REST page is the source. `packages/dhan-client` does **not** wire this path (as of this write).

### Annexure `indicatorName` (complete list on the page)

| `indicatorName` | Description as printed | Period / extra params in docs |
|-----------------|------------------------|-------------------------------|
| `SMA_5` | Simple Moving Average (5 periods) | period **baked into the name** (5) |
| `SMA_10` | Simple Moving Average (10 periods) | 10 |
| `SMA_20` | Simple Moving Average (20 periods) | 20 |
| `SMA_50` | Simple Moving Average (50 periods) | 50 |
| `SMA_100` | Simple Moving Average (100 periods) | 100 |
| `SMA_200` | Simple Moving Average (200 periods) | 200 |
| `EMA_5` | Exponential Moving Average (5 periods) | 5 |
| `EMA_10` | Exponential Moving Average (10 periods) | 10 |
| `EMA_20` | Exponential Moving Average (20 periods) | 20 |
| `EMA_50` | Exponential Moving Average (50 periods) | 50 |
| `EMA_100` | Exponential Moving Average (100 periods) | 100 |
| `EMA_200` | Exponential Moving Average (200 periods) | 200 |
| `BB_UPPER` | Upper Bollinger Band | length / stddev **not documented** → `UNKNOWN` |
| `BB_LOWER` | Lower Bollinger Band | same; **no `BB_MIDDLE` / `BB_WIDTH` in annexure** |
| `RSI_14` | Relative Strength Index | 14 baked into the name |
| `ATR_14` | Average True Range | 14 baked into the name |
| `STOCHASTIC` | Stochastic Oscillator | %K / %D / smooth **not documented** → `UNKNOWN` |
| `STOCHRSI_14` | Stochastic RSI | 14 in the name; extra stochastic params `UNKNOWN` |
| `MACD_26` | MACD long-term component | 26 in the name |
| `MACD_12` | MACD short-term component | 12 in the name |
| `MACD_HIST` | MACD histogram | signal length **not named** (no `MACD_9` / `MACD_SIGNAL` in annexure) → `UNKNOWN` |

**Not in this annexure table (therefore not official API indicator names):** Supertrend, VWAP, VWMA, AVWAP, ADX, DMI, Hull, CPR, pivots, Ichimoku, volume profile, order-flow, “Power Scalper”, custom Pine names.

### Annexure operators

`CROSSING_UP`, `CROSSING_DOWN`, `CROSSING_ANY_SIDE`, `GREATER_THAN`, `LESS_THAN`, `GREATER_THAN_EQUAL`, `LESS_THAN_EQUAL`, `EQUAL`, `NOT_EQUAL`.

### Annexure comparison types (mandatory fields as printed)

| Type | Mandatory fields |
|------|------------------|
| `TECHNICAL_WITH_VALUE` | `indicatorName`, `operator`, `timeFrame`, `comparingValue` |
| `TECHNICAL_WITH_INDICATOR` | `indicatorName`, `operator`, `timeFrame`, `comparingIndicatorName` |
| `TECHNICAL_WITH_CLOSE` | `indicatorName`, `operator`, `timeFrame` |
| `PRICE_WITH_VALUE` | `operator`, `comparingValue` |

---

## B. Chart / candle APIs (OHLC only — compute TA yourself)

**Page:** [Historical Data](https://dhanhq.co/docs/v2/historical-data/)

| Method | Path | Documented output |
|--------|------|-------------------|
| POST | `/charts/historical` | daily `open`, `high`, `low`, `close`, `volume`, `timestamp`; sample also has `open_interest` when requested |
| POST | `/charts/intraday` | same arrays; intervals `1`, `5`, `15`, `25`, `60` (minute). Max **90 days** per call. Text also says last **5 years** of availability |

Request fields (daily): `securityId`, `exchangeSegment`, `instrument`, optional `expiryCode`, optional `oi`, `fromDate`, `toDate` (toDate **non-inclusive**).  
Intraday: same plus `interval`. Sample `interval` is the string `"1"`; table says enum integer.

**No** RSI / Supertrend / MACD / VWAP keys in the response tables.

Intraday `3` minute is **not** in the interval enum → `UNKNOWN` / not documented. STRAT-003’s 3m is a **hypothesis**, not an official chart interval.

---

## C. Snapshot / feed fields that look like “indicators” but are not TA names

### Market Quote — [page](https://dhanhq.co/docs/v2/market-quote/)

| Path | Documented fields relevant to strategies |
|------|------------------------------------------|
| POST `/marketfeed/ltp` | `last_price` |
| POST `/marketfeed/ohlc` | `last_price`, `ohlc.open/high/low/close` |
| POST `/marketfeed/quote` | `average_price` **described as “Volume weighted average price of the day”**, `volume`, `oi`, `oi_day_high`, `oi_day_low` (NSE_FNO note), depth, circuits, `net_change`, OHLC, last trade |

`average_price` is the **only** official REST field whose *description* is VWAP-like. It is **not** named `vwap`. Identity vs chart session VWAP / vs WS `ATP`: **UNKNOWN**.

### Live Market Feed — [page](https://dhanhq.co/docs/v2/live-market-feed/)

Quote and Full packets include **Average Trade Price (ATP)** (bytes 19–22, float32). Full packet also has OI, OI day high/low (NSE_FNO). **No** Supertrend/RSI/MACD.

### Option Chain — [page](https://dhanhq.co/docs/v2/option-chain/)

POST `/optionchain`, `/optionchain/expirylist`. Rate: **one unique request / 3 s**.

Documented CE/PE fields: `average_price`, `greeks.delta|theta|gamma|vega`, `implied_volatility`, `last_price`, `oi`, `previous_close_price`, `previous_oi`, `previous_volume`, `security_id`, `top_ask_price`, `top_ask_quantity`, `top_bid_price`, `top_bid_quantity`, `volume`. Plus `data.last_price` (underlying LTP).

Greeks **methodology** (Black–76 vs BSM, IV solver): **not on this page** → `UNKNOWN` / `VERIFY BEFORE IMPLEMENTATION`.

### Expired options — [page](https://dhanhq.co/docs/v2/expired-options-data/)

POST `/charts/rollingoption`. Request `requiredData` enum includes `open`, `high`, `low`, `close`, `iv`, `volume`, `strike`, `oi`, `spot`. Sample response keys include those arrays. Response *parameter table* only lists OHLC/volume/timestamp — treat extra keys as **documented in the request enum + sample**, types `VERIFY`.

---

## D. Chart-only / product-only (not REST indicator APIs)

Tier 2 secondary (cannot replace `@DhanHQ` transcripts). **No scanner/screener REST** found on [dhanhq.co/docs/v2](https://dhanhq.co/docs/v2/).

| Surface | Official URL | What Dhan writes | API field? |
|---------|--------------|------------------|------------|
| Charts (TradingView-in-Dhan) | [tv.dhan.co](https://tv.dhan.co/) classified in [`DHAN_ECOSYSTEM.md`](DHAN_ECOSYSTEM.md) | Charting product. EMA zoom caveat: [support](https://dhan.co/support/platforms/tradingview/my-ema-values-change-when-i-zoom-in-out/) | **None** in HQ v2 |
| App Technical Alerts | [What types of alerts](https://dhan.co/support/platforms/market-alerts/what-types-of-alerts-can-i-set/) | “RSI, MACD, Bollinger Bands, Moving Averages, etc.” | Not a series API. May overlap conceptually with Conditional Trigger — **not proven identical** → `VERIFY` |
| ScanX technical screeners | [Which Technical Screeners](https://dhan.co/support/platforms/scanx/which-technical-screeners-are-available-in-scanx/) | Golden/Death crossover; **Overbought RSI above 75**; **Oversold RSI below 25**; R1–R3 / S1–S3; squeezing range; momentum | Product copy. **Not** annexure `comparingValue` defaults |
| ScanX how-to | [How to use Technical Screeners](https://dhan.co/support/platforms/scanx/how-to-use-scanx-s-technical-screeners/) | MA crossovers, RSI levels, S/R breakouts | Product UI |
| ScanX custom filters | [Which filters](https://dhan.co/support/platforms/scanx/which-filters-are-available-in-scanx-to-create-a-custom-screener/) | Category “Technical Indicators” — **no per-indicator param table** | `UNKNOWN` names/params |
| ScanX Intraday Supertrend | [Intraday Screeners](https://dhan.co/support/platforms/scanx/which-intraday-screeners-are-available-in-scanx/) | Support copy includes “Intraday Supertrend → Get clear buy/sell signals using Supertrend.” (live page copy can drift — `VERIFY`) | **No** ATR period / multiplier on that page |
| ScanX marketing | [dhan.co/scanx-stock-screener](https://dhan.co/scanx-stock-screener/) | Mentions “Intraday SuperTrend” | `NOT_EVIDENCE` per ecosystem (promo). Do not use as param source |

**YouTube titles** (e.g. “43 Advanced Trading Indicators”, Supertrend+RSI screener videos) are **Tier 1 transcript candidates**, not API field lists. Spoken params go to SOURCE_FACT handoffs. They do **not** create REST keys.

---

## E. Strategy-cluster cheat sheet (official vs chart-only)

| Cluster (workspace.yaml) | Official API name / field | Chart / ScanX / video only |
|--------------------------|---------------------------|----------------------------|
| RSI + Supertrend | `RSI_14` on Conditional Trigger only. **No Supertrend name in annexure.** | Supertrend: charts + ScanX screener name; ATR(10)×3 is **not** an HQ field |
| MACD | `MACD_12`, `MACD_26`, `MACD_HIST` (trigger names) | Signal line period, “×4” scaling: not in API docs |
| VWAP | Quote `average_price` (“VWAP of the day”); feed `ATP` | Session VWAP / VWMA / AVWAP on charts: no REST series |
| Option chain | `/optionchain` fields above | OI Profile / DEXT order-flow widgets: not HQ history |
| Scalping | EMA_5/10/20 etc. as **trigger names** only; 1/5/15/25/60m OHLC | Power Scalper, Hull, dual Supertrend: chart/product |
| Options buying | Chain Greeks/IV/OI + OHLC | Spoken setups remain transcripts |

---

## F. What 01_research must still do (YouTube)

Indicator KB from **transcripts** is still the ANALYSIS.md pipeline (`research/indicator_knowledge_base.md` Dhan-transcript columns). This document does **not** replace SOURCE_FACT extraction. Do not scrape blogs as Dhan official.

---

## G. Sources fetched (2026-09-01)

1. https://dhanhq.co/docs/v2/  
2. https://dhanhq.co/docs/v2/annexure/  
3. https://dhanhq.co/docs/v2/conditional-trigger/  
4. https://dhanhq.co/docs/v2/historical-data/  
5. https://dhanhq.co/docs/v2/market-quote/  
6. https://dhanhq.co/docs/v2/live-market-feed/  
7. https://dhanhq.co/docs/v2/option-chain/  
8. https://dhanhq.co/docs/v2/expired-options-data/  
9. https://dhanhq.co/docs/DhanHQ-py/ (and historical / market quote child pages — no indicator series methods found)  
10. https://docs.dhanhq.co/ (portal; not indicator definitions)  
11. Dhan support: ScanX technical / custom / intraday screener pages; market-alerts types; TradingView EMA zoom  

`packages/dhan-client/src/dhan_client/endpoints.py` (as of this write) wires quote, historical, option chain, feed, instruments — **not** `/alerts/orders`.

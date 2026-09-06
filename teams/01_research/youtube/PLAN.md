# PLAN.md
# Institutional-Grade DhanHQ + YouTube Research → Quant Strategy → Backtesting → Execution Platform

**Version:** 1.0  
**Date:** 2026-08-30  
**Primary market:** Indian index derivatives  
**Initial instruments:** NIFTY, BANKNIFTY, SENSEX index options  
**Primary broker/data platform:** Dhan / DhanHQ API  
**Primary expert-education source for transcript extraction:** Official Dhan YouTube channel only  
**Engineering objective:** Build an auditable research pipeline that converts expert education into machine-readable strategy specifications, validates them independently, backtests them, and only then considers live deployment.

---

## 0. EXECUTIVE DIRECTIVE

This project is not a request to blindly copy YouTube trading strategies.

The objective is to build a **research and decision engine** that:

1. discovers relevant Dhan educational videos,
2. ranks them by popularity and relevance,
3. obtains publicly available transcripts,
4. extracts the actual claims, rules, indicators, parameters, examples, and risk-management concepts,
5. separates Dhan's statements from our own interpretation,
6. independently validates technical concepts using authoritative sources,
7. maps every implementable concept to available DhanHQ market data,
8. converts concepts into explicit, testable hypotheses,
9. combines compatible ideas into candidate strategies,
10. backtests them without look-ahead bias,
11. performs out-of-sample and walk-forward validation,
12. stress-tests transaction costs, slippage, liquidity, volatility and regime changes,
13. ranks strategies using risk-adjusted metrics rather than headline return,
14. produces simple human-readable signals,
15. supports paper trading before any live execution,
16. maintains a complete audit trail.

### Critical financial requirement

A research objective of seeking very high returns must **never be converted into a promise of 10–30% daily returns**.

The platform must optimize for:

- positive expectancy,
- risk-adjusted return,
- drawdown control,
- robustness,
- liquidity,
- scalability,
- execution realism,
- capital preservation.

A strategy that produces 30% in a backtest but collapses after realistic slippage is a failed strategy.

A strategy that makes less money but survives different market regimes may be superior.

---

# 1. THE MASTER AI / AGENT PERSONA

Every AI agent participating in this project must behave as an:

> **Institutional Quantitative Research Architect + AI Financial Engineer + Market Microstructure Analyst + Algorithmic Trading Engineer + FinTech CTO + Red-Team Reviewer**

The agent must think like a combination of:

- quantitative researcher,
- derivatives trader,
- options-market researcher,
- data engineer,
- ML engineer,
- software architect,
- risk manager,
- portfolio manager,
- compliance-conscious financial technologist,
- research auditor.

The agent must not behave like a generic coding chatbot.

### Mandatory behavior

The agent must:

- ask whether a claim is observable from available data,
- distinguish facts from hypotheses,
- identify missing data,
- identify survivorship bias,
- identify look-ahead bias,
- identify overfitting,
- identify data leakage,
- challenge unrealistic assumptions,
- reject fabricated numbers,
- preserve source provenance,
- preserve timestamps,
- preserve original video IDs,
- never invent transcript content,
- never invent indicator parameters,
- never assume an indicator exists in DhanHQ without verification,
- never assume an API endpoint exists without checking current documentation.

---

# 2. PROJECT GOAL

Build a financial intelligence and algorithmic trading platform with long-term institutional ambitions.

The initial system should focus on:

### Market

- Indian markets

### Instruments

- NIFTY index options
- BANKNIFTY index options
- SENSEX index options

### Trading style

Priority:

1. intraday
2. opening-market analysis
3. opening-range setups
4. momentum
5. breakout/breakdown
6. scalping
7. large-move capture
8. mean reversion where statistically justified
9. options-chain-driven setups
10. price-action-driven setups

### Explicitly exclude for Phase 1

- individual stock strategies,
- long-term investing,
- stock screening,
- equity portfolio construction,
- fundamental stock valuation.

Stock-specific Dhan videos may be harvested for general educational concepts, but they must be tagged `STOCK_ONLY` and excluded from Phase-1 strategy construction unless the concept is clearly transferable to index/options trading.

---

# 3. SOURCE-OF-TRUTH HIERARCHY

The project must maintain a strict hierarchy.

## Tier 1 — Primary Dhan educational source

Only:

**Official Dhan YouTube channel**

https://www.youtube.com/@DhanHQ

For transcript extraction, do not substitute:

- other YouTube channels,
- reposted videos,
- blogs,
- social media summaries,
- third-party transcripts.

Third-party content can never silently replace the official Dhan video.

## Tier 2 — Dhan official technical/API documentation

Use current official DhanHQ documentation for:

- API endpoints,
- authentication,
- WebSocket,
- market data,
- historical data,
- option chain,
- market depth,
- instruments,
- order APIs,
- execution,
- rate limits,
- SDKs,
- releases.

Current documentation starting points:

https://dhanhq.co/docs/v2/

https://dhanhq.co/docs/v2/live-market-feed/

https://dhanhq.co/docs/v2/historical-data/

https://dhanhq.co/docs/v2/option-chain/

https://docs.dhanhq.co/api/v2/guides/sdks/python

## Tier 3 — Exchange / regulator sources

For current contract specifications, expiries, lot sizes, strike schemes, tick sizes, quantity freezes and related derivatives rules, use current official exchange/regulatory sources.

Primary:

- NSE: https://www.nseindia.com/
- BSE: https://www.bseindia.com/
- SEBI: https://www.sebi.gov.in/

Important:

SENSEX is a BSE index. Do not incorrectly treat SENSEX as an NSE instrument.

## Tier 4 — Authoritative technical references

Use recognized textbooks, original papers, exchange documentation, academic literature and established technical references to validate concepts.

Do not use these sources to overwrite what Dhan said.

Instead:

Dhan claim → independent validation → disagreement flag if necessary.

---

# 4. WHY THE YOUTUBE RESEARCH PIPELINE EXISTS

Dhan publishes educational material covering:

- options,
- option chains,
- technical indicators,
- price action,
- candlesticks,
- risk management,
- strategy construction,
- charting,
- scanners,
- trading tools,
- custom indicators,
- market analysis.

Manually watching every video is inefficient.

The project therefore requires an automated research pipeline.

The pipeline should transform:

**Videos → Metadata → Transcripts → Topics → Claims → Rules → Indicators → Parameters → Hypotheses → Backtests → Validated Strategy Components**

The output is NOT a transcript dump.

The output is a structured research corpus.

---

# 5. STAGE 1 — DISCOVER THE COMPLETE DHAN YOUTUBE CHANNEL

## Objective

Create a program that discovers:

- channel information,
- all available videos,
- all playlists,
- playlist membership,
- publication date,
- video title,
- description,
- duration,
- view count,
- like count when available,
- comment count when available,
- video ID,
- URL,
- thumbnail,
- captions/transcript availability,
- language,
- topic classification.

### Required output

`data/youtube/video_catalog.csv`

and

`data/youtube/video_catalog.json`

### Recommended fields

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

### Discovery rule

Do not assume the search engine has discovered every Dhan video.

Use an authoritative discovery method where possible, such as:

- YouTube Data API,
- channel feeds,
- playlist enumeration,
- official channel pages.

Search-engine discovery is only a supplemental validation layer.

---

# 6. STAGE 2 — POPULAR VIDEO FILTER

The user specifically requested:

> ONLY extract details from popular videos.

Therefore, the pipeline must define popularity explicitly.

Do not use a vague manual definition.

## Popularity score

Create a ranking score using available metrics.

Example:

```text
PopularityScore =
    normalized_views * 0.55
  + normalized_likes * 0.20
  + normalized_comments * 0.10
  + recency_score * 0.15
```

The exact weights are configurable.

### Important

Popularity is NOT evidence that a strategy works.

Popularity is only the criterion for selecting educational material for research.

---

# 7. RELEVANCE FILTER

After popularity ranking, apply a second filter.

### HIGH PRIORITY

Videos containing concepts related to:

- options trading,
- NIFTY,
- BANKNIFTY,
- SENSEX,
- index derivatives,
- option buying,
- option selling,
- option chain,
- strike selection,
- expiry,
- Greeks,
- IV,
- OI,
- price action,
- candlestick patterns,
- intraday,
- scalping,
- breakout,
- breakdown,
- momentum,
- opening strategy,
- market opening,
- trend identification,
- reversal,
- support/resistance,
- VWAP,
- RSI,
- Supertrend,
- moving averages,
- MACD,
- ADX,
- volume,
- volatility,
- risk management,
- stop loss,
- target,
- position sizing,
- custom indicators,
- Dhan indicators,
- leading/lagging indicators,
- strategy builder,
- market structure.

### MEDIUM PRIORITY

General technical-analysis education that can transfer to index derivatives.

### LOW PRIORITY

- long-term investing,
- stock valuation,
- stock-specific recommendations,
- mutual funds,
- SIPs,
- portfolio investing,
- unrelated product tutorials.

### EXCLUDE

If a video is exclusively about:

- a specific stock,
- stock fundamental analysis,
- long-term investing,
- unrelated financial products,

mark:

`EXCLUDED_STOCK_ONLY`

Do not delete the metadata.

---

# 8. INITIAL POPULARITY SEEDS

The research agent should verify these and then dynamically discover the full ranked catalog.

Examples found during initial validation include:

### A. Option Buying Masterclass

Title:

**The Ultimate 1-Hour Masterclass on Option Buying Strategies | Option Trading Strategy | Dhan**

Published: 2025-07-08  
Views observed during research: approximately 159,750

Topics advertised in the video:

- option basics,
- strike price,
- expiry,
- option chain,
- delta,
- theta,
- IV,
- technical indicators,
- option buying strategy,
- entry,
- exit,
- stop loss,
- risk management.

Source:

https://www.youtube.com/watch?v=HAUSZx-hYdY

### B. Auto Candlestick Patterns

Title:

**Now Live: Auto Candlestick Patterns | Automatically Detect Candlestick Patterns | Dhan**

Published: 2024-12-04  
Views observed during research: approximately 78,754

The video description states that Dhan's charting feature can automatically detect 37 recognized candlestick patterns and allows bullish/bearish filtering and timeframe selection.

Source:

https://www.youtube.com/watch?v=wDZXqzdGBDc

### C. RSI + Supertrend

Title:

**RSI + Supertrend Strategy for Positional and Swing Setups | Dhan**

Published: 2025-06-11  
Views observed during research: approximately 33,966

Relevant concept:

- combining RSI and Supertrend,
- timing,
- filtering noise,
- reversals.

This is not automatically an intraday-options strategy. The transcript must determine what is actually transferable.

Source:

https://www.youtube.com/watch?v=H_6keeRUCDM

### D. Price Action Intraday

Title:

**How to Trade Intraday Using Price Action – Complete Strategy Explained | Dhan**

Published: 2025-07-12  
Views observed during research: approximately 10,204.

Relevant topics:

- price action,
- entries,
- exits,
- risk management,
- market structure.

Source:

https://www.youtube.com/watch?v=PUkzVgVPCf0

### E. Candlestick Patterns

Title:

**5 Candlestick Patterns Every Trader MUST Know (With Live Examples) - YouTube**

Published: 2026-01-14  
Views observed during research: approximately 6,448.

The description covers:

- Hammer,
- Bullish Engulfing,
- Morning Star,
- Dark Cloud Cover,
- Inside Bar,
- timeframe selection,
- high-probability zones,
- strategy construction,
- failure/trap discussion.

Source:

https://www.youtube.com/watch?v=njqeZc_tYy8

### F. Option Strategy Builder

Title:

**Create An Option Trading Strategy in 15 Mins | Option Trading During Bear Market Strategy | Dhan**

Published: 2025-03-09.

Relevant topics:

- trend identification,
- strike selection,
- structured options strategy,
- risk management.

Source:

https://www.youtube.com/watch?v=gA5FtEnSABM

These are only initial research seeds.

The agent MUST NOT assume these are the final videos.

---

# 9. STAGE 3 — TRANSCRIPT EXTRACTION

## Objective

For every selected video:

1. retrieve public transcript/captions where available,
2. preserve timestamps,
3. preserve language,
4. preserve video ID,
5. preserve exact source URL,
6. store raw transcript,
7. normalize a second copy for model analysis.

### Required files

```text
data/transcripts/raw/<video_id>.json
data/transcripts/normalized/<video_id>.md
```

### Raw transcript format

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

### Critical rule

Never create a transcript from the title or description.

If transcript retrieval fails:

```text
TRANSCRIPT_UNAVAILABLE
```

Do not hallucinate.

---

# 10. TRANSCRIPT QUALITY CONTROL

Every transcript must be checked for:

- missing sections,
- duplicated text,
- timestamp anomalies,
- language mismatch,
- obvious speech-to-text errors,
- numbers incorrectly transcribed,
- indicator names incorrectly transcribed,
- strike prices incorrectly transcribed,
- percentages incorrectly transcribed.

Special attention:

Numbers are high-risk.

Examples:

- `20` vs `200`
- `0.5` vs `5`
- `14` vs `40`
- `20000` vs `2000`
- `9 EMA` vs `20 EMA`
- `14 RSI` vs `40 RSI`

When uncertain:

`[UNCERTAIN_TRANSCRIPT]`

Never silently correct a number based on guesswork.

---

# 11. STAGE 4 — TRANSCRIPT INTELLIGENCE EXTRACTION

The first AI analysis should NOT create a trading strategy.

It should create a **knowledge extraction record**.

For every video extract:

## Metadata

- video ID
- title
- publication date
- views
- popularity rank
- transcript confidence

## Topics

Example:

```text
OPTIONS
PRICE_ACTION
CANDLESTICKS
RSI
SUPERTREND
RISK_MANAGEMENT
OPTION_CHAIN
```

## Claims

Every substantive claim must include:

- exact transcript timestamp,
- paraphrased claim,
- claim type,
- confidence,
- whether it is a rule or general education.

## Indicators

For each indicator:

- name,
- purpose,
- category,
- parameters,
- timeframe,
- input price,
- interpretation,
- entry use,
- exit use,
- limitations.

## Strategy rules

Extract separately:

- market condition,
- setup,
- entry,
- confirmation,
- stop,
- target,
- trailing stop,
- exit,
- position sizing,
- timeframe,
- instrument.

---

# 12. THE THREE-LAYER KNOWLEDGE MODEL

Every extracted item must be placed into one of three layers.

## LAYER A — SOURCE FACT

What Dhan actually said.

Example:

```text
SOURCE_FACT:
Dhan presenter described RSI + Supertrend as a way to filter trade setups.
```

## LAYER B — INDEPENDENT VALIDATION

What authoritative sources say.

Example:

```text
VALIDATION:
RSI is a bounded momentum oscillator.
Supertrend is a volatility-based trend-following indicator.
```

## LAYER C — PROJECT HYPOTHESIS

What our research team proposes testing.

Example:

```text
HYPOTHESIS:
Use Supertrend as directional regime filter and RSI as momentum confirmation
for NIFTY option-buying setups during the first 90 minutes.
```

Never merge these layers.

---

# 13. INDICATOR KNOWLEDGE BASE

Build:

`research/indicator_knowledge_base.md`

and machine-readable:

`research/indicator_knowledge_base.json`

For each indicator document:

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

---

# 14. INDICATOR CATEGORIES

## Lagging / trend indicators

Potential examples:

- Moving Average
- EMA
- SMA
- MACD
- Supertrend

## Momentum

Potential examples:

- RSI
- Stochastic
- ROC

## Volatility

Potential examples:

- ATR
- Bollinger Bands
- IV
- IV Rank where data supports it

## Volume / market activity

Potential examples:

- Volume
- VWAP where valid
- Volume Profile
- relative volume

## Market structure / price action

- support
- resistance
- swing highs
- swing lows
- breakout
- breakdown
- range
- opening range
- liquidity zones

## Options-specific

- OI
- change in OI
- IV
- Delta
- Gamma
- Theta
- Vega
- bid/ask
- volume
- strike distance
- expiry
- PCR

---

# 15. IMPORTANT VWAP / VOLUME RULE

Do not incorrectly apply stock/futures volume concepts to a cash index.

For example:

- NIFTY index itself is an index calculation and should not be treated as a normal traded instrument with conventional exchange-traded volume simply because NIFTY futures/options have volume.
- NIFTY futures have traded volume.
- NIFTY option contracts have traded volume.
- Individual option contracts can have VWAP-style traded-price calculations.
- The appropriate volume source must be explicitly identified.

Every feature must document:

```text
DATA_SOURCE
INSTRUMENT
EXCHANGE_SEGMENT
CALCULATION
TIMEFRAME
```

---

# 16. OPTIONS RESEARCH ENGINE

Options strategies must be built using the full option context.

For each underlying:

```text
Underlying
Spot
Futures
Expiry
ATM strike
ITM strikes
OTM strikes
CE LTP
PE LTP
CE volume
PE volume
CE OI
PE OI
Change in OI
IV
Delta
Gamma
Theta
Vega
Bid
Ask
Bid quantity
Ask quantity
```

Dhan's current Option Chain API provides OI, Greeks, volume, LTP, best bid/ask and IV across strikes.

Official documentation:

https://dhanhq.co/docs/v2/option-chain/

The API currently documents a rate limit of one unique Option Chain request every three seconds. The architecture must therefore not poll the entire option chain unnecessarily at high frequency.

Instead:

- use WebSocket for streaming data where available,
- use Option Chain REST for periodic option-chain snapshots,
- cache snapshots,
- calculate deltas locally,
- timestamp every snapshot.

---

# 17. DHAN LIVE DATA ARCHITECTURE

Dhan's Live Market Feed uses WebSocket and provides tick/event-driven market data.

Current Dhan documentation indicates:

- persistent WebSocket connection,
- binary response packets,
- JSON subscription requests,
- up to five WebSocket connections per user,
- up to 5,000 instruments per connection.

Source:

https://dhanhq.co/docs/v2/live-market-feed/

The data ingestion system must therefore contain:

```text
WebSocket Collector
        ↓
Binary Decoder
        ↓
Timestamp Normalizer
        ↓
Instrument Resolver
        ↓
Tick Store
        ↓
1m Aggregator
        ↓
5m Aggregator
        ↓
15m Aggregator
        ↓
Feature Engine
        ↓
Signal Engine
```

---

# 18. HISTORICAL DATA

Dhan's current documentation states that intraday historical data is available in minute intervals and supports 1, 5, 15, 25 and 60-minute intervals, with up to five years of intraday history and OI support for F&O where applicable.

Source:

https://dhanhq.co/docs/v2/historical-data/

Do not assume this means every historical option-chain field required for advanced research is available for five years.

Before backtesting an options strategy, verify availability of:

- historical option prices,
- historical OI,
- historical volume,
- historical IV if required,
- historical Greeks if required,
- historical bid/ask if required,
- historical contract metadata,
- historical expiries,
- historical strikes.

If a required field is missing, mark the strategy:

`DATA_INSUFFICIENT`

Do not synthesize unavailable history.

---

# 19. DATA MODEL

Recommended architecture:

```text
raw_ticks
raw_quotes
option_chain_snapshots
historical_candles
instrument_master
contract_calendar
expiry_calendar
signals
orders
fills
positions
strategy_runs
backtest_runs
research_claims
video_catalog
transcripts
indicator_definitions
```

Every record must have:

```text
source
timestamp
timezone
instrument
exchange
security_id
data_version
```

---

# 20. INSTRUMENT MASTER

Create a continuously updated instrument master.

Minimum fields:

```text
security_id
exchange
segment
symbol
underlying
instrument_type
option_type
strike
expiry
lot_size
tick_size
freeze_quantity
trading_status
effective_from
effective_to
```

Do NOT hardcode lot sizes permanently.

Exchange contract specifications and lot sizes can change.

Use the latest official exchange files/circulars and maintain historical effective dates.

NSE currently publishes contract information including permitted lot size files and contract specifications.

Source:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-information

Current NSE contract specifications:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-specifications

---

# 21. SENSEX SPECIAL RULE

SENSEX is a BSE index.

Therefore:

```text
NIFTY      → NSE
BANKNIFTY  → NSE
SENSEX     → BSE
```

Do not design the system around NSE-only assumptions.

The data abstraction must support:

```text
exchange = NSE
exchange = BSE
```

and the strategy engine should be exchange-agnostic.

---

# 22. CONTRACT-SPECIFICATION VALIDATION

Before each backtest:

Validate:

- lot size,
- expiry date,
- strike interval,
- tick size,
- trading hours,
- contract availability,
- quantity freeze,
- instrument status.

Never use a current lot size against historical trades.

Historical backtests must use the lot size applicable on that historical date.

---

# 23. OPTIONS STRIKE SELECTION ENGINE

The system must not simply choose:

> ATM option.

Instead evaluate:

- ATM,
- 1 strike ITM,
- 1 strike OTM,
- 2 strikes ITM,
- 2 strikes OTM,
- delta bands.

Possible selection logic:

```text
Target delta range
Liquidity threshold
Bid/ask spread threshold
Minimum volume
Minimum OI
Expiry filter
Premium filter
Gamma exposure
Theta exposure
```

The strategy must determine whether buying:

- ATM,
- slightly ITM,
- slightly OTM

actually performs better after costs.

This must be tested, not assumed.

---

# 24. PRICE-ACTION ENGINE

Build a reusable price-action feature library.

Potential features:

### Market structure

- higher high
- higher low
- lower high
- lower low
- trend break
- structure break

### Candlestick

- hammer
- shooting star
- engulfing
- morning star
- evening star
- inside bar
- doji
- strong body candle

### Zones

- previous day high
- previous day low
- previous close
- opening price
- opening range
- weekly high
- weekly low
- VWAP where applicable
- high-volume zones

### Breakouts

- opening-range breakout
- previous high breakout
- previous low breakdown
- consolidation breakout

Every pattern must have:

```text
Definition
Detection rule
Context requirement
Confirmation
Invalidation
Backtest rule
```

---

# 25. MARKET OPENING ENGINE

Create a dedicated opening model.

Analyze:

### Previous session

- close
- high
- low
- range
- trend
- volatility
- OI structure
- option positioning

### Pre-open / global context where data is legitimately available

- global index direction
- major overnight events
- volatility
- relevant macro events

### First minutes

- opening gap
- opening range
- first 5-minute candle
- first 15-minute candle
- volume
- price acceptance/rejection
- option premium response
- OI change

Output:

```text
OPENING REGIME
Bullish
Bearish
Range
High-risk
Unclear
```

Never claim the model can know the future opening direction with certainty.

---

# 26. SCALPING ENGINE

Scalping requires a different model than swing trading.

Minimum data:

- tick or high-frequency feed where available,
- bid/ask,
- spread,
- volume,
- short timeframe candles,
- market depth if available,
- option liquidity.

Potential timeframes:

- tick
- 1-minute
- 3-minute
- 5-minute

Do not use 15-minute signals for a strategy labeled scalping unless validated.

---

# 27. BIG-MOVE CAPTURE ENGINE

The system should investigate conditions preceding large moves.

Candidate features:

- volatility compression,
- range compression,
- breakout,
- volume expansion,
- OI changes,
- IV changes,
- gamma,
- price-action confirmation,
- market breadth,
- trend alignment,
- opening range break.

The research question:

> Can measurable conditions identify a statistically elevated probability of a large move before most of the move occurs?

This must be tested using historical data.

---

# 28. STRATEGY COMBINATION FRAMEWORK

Do NOT combine every indicator.

More indicators ≠ better strategy.

Use a hierarchy:

```text
REGIME
   ↓
MARKET STRUCTURE
   ↓
PRICE ACTION
   ↓
MOMENTUM / TREND CONFIRMATION
   ↓
OPTIONS CONFIRMATION
   ↓
ENTRY
   ↓
RISK
   ↓
EXIT
```

Example candidate:

```text
Regime:
Bullish trend

Structure:
Higher highs + higher lows

Confirmation:
Supertrend bullish

Momentum:
RSI above configured threshold

Options:
Selected CE has acceptable liquidity and delta

Entry:
Break above confirmed structure

Stop:
Structure invalidation or volatility-adjusted stop

Target:
Risk multiple / trailing mechanism
```

This is a **hypothesis**, not a proven strategy.

---

# 29. CANDIDATE STRATEGY LIBRARY

The research agent should generate candidates such as:

### Strategy A
Opening Range Breakout + Price Action

### Strategy B
Opening Range Breakout + Options Confirmation

### Strategy C
Supertrend + RSI + Price Action

### Strategy D
Price Action + VWAP on appropriate traded instrument

### Strategy E
Option OI + Price Action

### Strategy F
IV + Momentum

### Strategy G
Volatility Compression + Breakout

### Strategy H
Candlestick Reversal + Support/Resistance

### Strategy I
Market Regime + Momentum + Options Liquidity

### Strategy J
Multi-factor score

Each candidate must be independently tested.

---

# 30. MULTI-FACTOR SIGNAL SCORE

If combining factors, use a transparent scoring model.

Example:

```text
Price Action              25%
Market Regime             20%
Momentum                  15%
Options Positioning       15%
Volatility                10%
Liquidity                  5%
News/Event Risk            5%
Execution Quality          5%
```

The weights are placeholders.

They must be optimized only through a proper training/validation framework.

Do not hand-tune weights on the final test set.

---

# 31. BACKTEST ENGINE

The backtester must simulate what the trader could actually know at the time.

For each trade store:

```text
signal_time
underlying
option_contract
expiry
strike
CE/PE
entry_time
entry_price
stop_price
target_price
exit_time
exit_price
quantity
lot_size
gross_pnl
fees
slippage
net_pnl
MFE
MAE
reason
strategy_version
```

---

# 32. BACKTEST BIAS CHECKLIST

Every backtest must explicitly test:

- look-ahead bias,
- survivorship bias,
- selection bias,
- data leakage,
- future contract availability,
- historical lot size,
- historical expiry,
- unrealistic fills,
- bid/ask assumptions,
- slippage,
- transaction costs,
- stale OI,
- missing data.

If any cannot be resolved:

`BACKTEST_NOT_TRUSTWORTHY`

---

# 33. WALK-FORWARD VALIDATION

Do not use one large historical dataset and call it validated.

Example:

```text
Training:
Jan 2021 → Dec 2022

Validation:
Jan 2023 → Jun 2023

Test:
Jul 2023 → Dec 2023
```

Then roll forward:

```text
Train → Validate → Test
Train → Validate → Test
Train → Validate → Test
```

Use multiple market regimes.

---

# 34. REGIME TESTING

Evaluate each strategy separately in:

- bull trend,
- bear trend,
- sideways market,
- high volatility,
- low volatility,
- gap-up,
- gap-down,
- expiry day,
- non-expiry day,
- major-event day,
- opening breakout,
- afternoon session.

A strategy that only works in one regime must be labeled accordingly.

---

# 35. MONTE CARLO / ROBUSTNESS TESTING

Perform:

- trade-order randomization,
- return perturbation,
- slippage perturbation,
- transaction-cost perturbation,
- parameter perturbation,
- entry-delay simulation,
- exit-delay simulation.

Ask:

> Does the strategy still work if real execution is worse than the backtest?

---

# 36. PARAMETER ROBUSTNESS

If Dhan recommends:

```text
RSI = 14
Supertrend = 10, 3
EMA = 20
```

do NOT automatically hardcode those parameters.

Test neighborhoods.

Example:

```text
RSI:
10, 12, 14, 16, 18, 20

Supertrend:
period 7–14
multiplier 2–4
```

The purpose is not to find the single best parameter.

The purpose is to find a **stable region**.

A strategy that works only at:

```text
RSI = 13.7
```

is suspicious.

---

# 37. STRATEGY SCORECARD

Every strategy must receive:

```text
Net Return
CAGR where applicable
Average Daily Return
Median Daily Return
Win Rate
Loss Rate
Profit Factor
Expectancy
Sharpe
Sortino
Calmar
Maximum Drawdown
Maximum Consecutive Losses
Recovery Time
MFE
MAE
Slippage Sensitivity
Cost Sensitivity
Regime Stability
Parameter Stability
Liquidity
Scalability
```

---

# 38. DO NOT RANK BY RETURN ALONE

A strategy returning:

```text
+500%
```

with:

```text
-90% drawdown
```

is not automatically superior to:

```text
+150%
```

with:

```text
-15% drawdown
```

The ranking engine must use risk-adjusted metrics.

---

# 39. STRATEGY SELECTION

The final strategy-selection model should consider:

```text
Expected Return
+
Risk-adjusted Return
+
Drawdown
+
Robustness
+
Liquidity
+
Execution Reliability
+
Regime Coverage
+
Parameter Stability
+
Out-of-Sample Performance
```

Output:

```text
STRATEGY STATUS

Candidate
Promising
Needs More Data
Fragile
Rejected
Paper Trading
Production Candidate
```

---

# 40. PAPER TRADING GATE

No strategy should immediately trade real money.

Required sequence:

```text
Research
→ Backtest
→ Out-of-Sample
→ Walk-Forward
→ Paper Trading
→ Execution Review
→ Small Capital
→ Controlled Scale
```

Paper trading should measure:

- signal latency,
- fill quality,
- slippage,
- missed trades,
- rejected orders,
- API failures,
- data gaps,
- execution timing.

---

# 41. LIVE SIGNAL FORMAT

The final interface must remain simple.

Example:

```text
NIFTY

BUY CE

Strike: XXXXX
Entry: ₹XX
Stop: ₹XX
Target 1: ₹XX
Target 2: ₹XX

Risk/Reward: X.X
Signal Quality: HIGH

Reason:
1. Bullish market structure
2. Momentum confirmation
3. Options positioning aligned

Invalidation:
Price closes below XXXXX.
```

The dashboard should not force the user to understand 20 indicators.

The complex system operates behind the simple signal.

---

# 42. SIGNAL AUDIT

Every generated signal must store:

```text
Why signal generated
What data was available
Indicator values
Options-chain state
Market regime
Model version
Strategy version
Timestamp
Latency
Entry
Stop
Target
Outcome
```

This allows the system to answer:

> Why did the model issue this trade?

---

# 43. MISSED SIGNAL TRACKING

The dashboard must explicitly track:

- valid signals generated,
- signals executed,
- signals missed,
- signals rejected,
- signals that became profitable after being missed,
- signals that would have lost,
- reason for missing execution.

This is critical for evaluating the real-world system rather than only the theoretical strategy.

---

# 44. DAILY REVIEW DASHBOARD

Create:

## Daily Summary

```text
Signals
Wins
Losses
Missed
Win Rate
Net P&L
Max Intraday Drawdown
Best Strategy
Worst Strategy
Best Time Window
Worst Time Window
```

## Time Analysis

```text
09:15–09:30
09:30–10:00
10:00–11:00
11:00–12:00
12:00–13:00
13:00–14:00
14:00–15:00
```

Measure performance by time window.

---

# 45. STRIKE-LEVEL REVIEW

The system must answer:

- Which strike performed best?
- ATM vs ITM vs OTM?
- Which delta range?
- Which expiry?
- Which premium range?
- Which option type?
- Which underlying?
- Which time of day?

This is particularly important for:

- NIFTY,
- BANKNIFTY,
- SENSEX.

---

# 46. STRATEGY COMPARISON DASHBOARD

Example:

| Strategy | NIFTY | BANKNIFTY | SENSEX | Win Rate | PF | Drawdown | OOS | Status |
|---|---:|---:|---:|---:|---:|---:|---|---|
| Strategy A | | | | | | | | |
| Strategy B | | | | | | | | |
| Strategy C | | | | | | | | |

Never populate these numbers until the backtest actually exists.

---

# 47. DHAN API ARCHITECTURE

Use DhanHQ for:

### Market data

- WebSocket
- quote APIs
- historical candles
- option chain
- market depth where available

### Execution

- order APIs
- order updates
- positions
- funds/margin
- super orders where appropriate.

### Research

Use REST APIs for snapshots and historical retrieval.

Use WebSocket for streaming.

Do not repeatedly request REST endpoints for information that should be streamed.

---

# 48. DATA INGESTION SERVICE

Recommended services:

```text
dhan-feed-service
market-data-normalizer
option-chain-service
historical-data-service
feature-engine
strategy-engine
backtest-engine
risk-engine
execution-engine
portfolio-service
signal-service
research-service
dashboard-service
audit-service
```

---

# 49. TECHNOLOGY STACK

Recommended initial stack:

## Backend

Python

- FastAPI
- Pydantic
- Pandas
- NumPy
- Polars where useful
- SciPy
- scikit-learn
- SQLAlchemy

## Database

PostgreSQL

For high-volume time-series:

- TimescaleDB or another appropriate time-series layer.

## Cache

Redis

## Streaming

WebSocket

Optional:

- Kafka/Redpanda when scale justifies it.

## Frontend

React / Next.js

Charts:

- TradingView-compatible charting or another licensed charting library.

## Deployment

Docker

Cloud infrastructure can be introduced after local validation.

---

# 50. DATABASE PRINCIPLES

Never store only final signals.

Store the underlying evidence.

The database must permit reconstruction of:

> "What did the system know at 10:31:42 on that day?"

This is essential for institutional-grade auditability.

---

# 51. RESEARCH DOCUMENT STRUCTURE

The final research corpus should contain:

```text
research/
├── 00_project_scope.md
├── 01_dhan_video_catalog.md
├── 02_transcript_index.md
├── 03_indicator_knowledge_base.md
├── 04_price_action_knowledge.md
├── 05_options_knowledge.md
├── 06_risk_management.md
├── 07_strategy_candidates.md
├── 08_validation_results.md
├── 09_backtest_results.md
├── 10_strategy_selection.md
├── 11_api_mapping.md
├── 12_data_requirements.md
└── 13_research_audit.md
```

---

# 52. TRANSCRIPT CLAIM SCHEMA

Every claim should have:

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

---

# 53. STRATEGY SPECIFICATION SCHEMA

Every strategy should eventually become machine-readable.

Example:

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

---

# 54. STRATEGY GENERATION RULE

The AI may propose new strategies only from:

1. extracted Dhan concepts,
2. independently validated concepts,
3. mathematically defined features,
4. measurable market behavior.

It must not invent a strategy and then pretend Dhan recommended it.

Label:

```text
DHAN-DERIVED
```

or

```text
PROJECT-DERIVED
```

---

# 55. EXPERT COMBINATION ENGINE

The project's key research advantage should be:

> Combine multiple independently useful concepts without blindly stacking indicators.

Example:

Dhan teaches:

- price action,
- RSI,
- Supertrend,
- candlesticks,
- option chain,
- risk management.

The system investigates:

```text
Can price action define the setup?

Can Supertrend define regime?

Can RSI confirm momentum?

Can option-chain information filter false signals?

Can volatility determine stop distance?

Can delta determine the option contract?

Can liquidity determine whether the trade is executable?
```

Then test each contribution independently.

---

# 56. ABLATION TESTING

For every multi-factor strategy:

### Full model

Price Action + RSI + Supertrend + Options

### Remove RSI

Price Action + Supertrend + Options

### Remove Supertrend

Price Action + RSI + Options

### Remove Options

Price Action + RSI + Supertrend

### Price Action only

Compare all.

If adding a factor does not improve out-of-sample performance, remove it.

This prevents indicator clutter.

---

# 57. STATISTICAL SIGNIFICANCE

Do not accept:

> "This strategy won 65% of trades."

Ask:

- How many trades?
- What is the confidence interval?
- Are wins clustered?
- Does performance persist?
- Is expectancy positive?
- Is performance driven by a few outliers?
- Does it survive costs?
- Does it work out-of-sample?

A 65% win rate from 20 trades is weak evidence.

A 55% win rate across thousands of independent trades with controlled risk can be more meaningful.

---

# 58. OPTIONS-SPECIFIC COST MODEL

Include:

- brokerage,
- exchange charges,
- statutory charges,
- taxes,
- slippage,
- bid/ask spread,
- execution delay.

Do not use only LTP-to-LTP P&L.

For buying:

```text
realistic entry ≈ ask
realistic exit ≈ bid
```

where data permits.

For selling, reverse appropriately.

---

# 59. EXPIRY-DAY MODEL

Expiry-day strategies must be evaluated separately.

Do not mix:

```text
expiry-day
```

with:

```text
non-expiry-day
```

without labeling.

Expiry can materially change:

- theta,
- gamma,
- liquidity,
- premium behavior,
- volatility,
- risk.

The research engine should compare them independently.

---

# 60. MARKET OPENING VS MIDDAY VS CLOSING

Separate strategy performance into:

```text
OPEN
09:15 onward

MORNING

MIDDAY

AFTERNOON

CLOSE
```

Do not assume a strategy works uniformly throughout the session.

---

# 61. NEWS/EVENT FILTER

Before allowing a live signal, the system should optionally detect:

- RBI events,
- major inflation releases,
- major employment/economic data,
- major global central-bank events,
- major geopolitical events,
- significant market announcements.

If an event creates abnormal risk:

```text
NO TRADE / REDUCED SIZE
```

unless a specifically validated event strategy exists.

---

# 62. RISK ENGINE RULES

The risk engine must be capable of overriding the signal engine.

Architecture:

```text
SIGNAL ENGINE
      ↓
RISK ENGINE
      ↓
EXECUTION ENGINE
```

Not:

```text
SIGNAL ENGINE
      ↓
EXECUTION
```

The risk engine can reject a valid signal.

---

# 63. CIRCUIT BREAKERS

Examples:

```text
Daily loss limit reached
→ STOP NEW TRADES

Data feed stale
→ STOP

WebSocket disconnected
→ STOP

Option spread abnormal
→ REJECT

Market volatility abnormal
→ REDUCE SIZE / STOP

Repeated API errors
→ SAFE MODE

Execution slippage exceeds threshold
→ PAUSE
```

---

# 64. MODEL DRIFT

Monitor whether the strategy is degrading.

Track:

- rolling win rate,
- rolling expectancy,
- rolling profit factor,
- drawdown,
- feature distributions,
- market regime distribution.

If performance falls below predefined thresholds:

```text
PRODUCTION
→ DEGRADED
→ PAPER
→ RESEARCH
```

---

# 65. NO AUTOMATIC SELF-OPTIMIZATION IN LIVE TRADING

Do not allow an AI model to automatically change:

- stop loss,
- leverage,
- position size,
- strategy parameters,
- entry thresholds

in live trading without a controlled validation process.

AI may recommend a new version.

The new version must pass:

```text
research
→ validation
→ approval
→ paper
→ deployment
```

---

# 66. SECURITY

Never put:

- Dhan access tokens,
- API secrets,
- client IDs,
- private credentials

inside source code.

Use:

- environment variables,
- secret managers,
- encrypted configuration.

Never give an LLM unrestricted access to live trading credentials.

Use a controlled execution service.

---

# 67. AGENT ARCHITECTURE

Use multiple specialized agents.

## Agent 1 — YouTube Discovery Agent

Responsibilities:

- discover Dhan videos,
- playlists,
- metadata,
- popularity.

## Agent 2 — Transcript Agent

Responsibilities:

- retrieve transcripts,
- timestamp,
- validate,
- normalize.

## Agent 3 — Research Extraction Agent

Responsibilities:

- extract concepts,
- indicators,
- rules,
- strategies.

## Agent 4 — Technical Validation Agent

Responsibilities:

- verify mathematical/technical concepts.

## Agent 5 — Options Research Agent

Responsibilities:

- translate concepts into index-options applications.

## Agent 6 — API Mapping Agent

Responsibilities:

- map required data to Dhan APIs.

## Agent 7 — Backtest Agent

Responsibilities:

- construct reproducible tests.

## Agent 8 — Statistical Validation Agent

Responsibilities:

- test significance,
- robustness,
- OOS performance.

## Agent 9 — Risk Agent

Responsibilities:

- challenge risk,
- sizing,
- drawdown,
- tail risk.

## Agent 10 — Red-Team Review Agent

Responsibilities:

- attempt to break the entire research conclusion.

---

# 68. RED-TEAM REVIEW AGENT

The Red-Team Agent must ask:

1. Did we actually read the transcript?
2. Did we invent any Dhan recommendation?
3. Did we misinterpret a number?
4. Did we use a stock-only concept for options?
5. Did we confuse underlying data with option data?
6. Did we use future information?
7. Did we use current lot size historically?
8. Did we use unavailable historical option data?
9. Did we optimize against the test set?
10. Did we ignore transaction costs?
11. Did we ignore bid/ask?
12. Did we assume fills?
13. Did we confuse correlation with causation?
14. Did we overfit indicators?
15. Did we select the winner because it had the highest backtest return?
16. Did we ignore losing regimes?
17. Did we ignore liquidity?
18. Did we accidentally use another YouTube channel?
19. Did we misrepresent an educational statement as expert endorsement?
20. Can another researcher reproduce the result?

If any answer is "yes":

```text
RESEARCH STATUS = FAILED REVIEW
```

---

# 69. FIVE-PASS REVIEW REQUIREMENT

Before publishing the final research document, perform five separate review passes.

## PASS 1 — Source Integrity

Verify:

- correct channel,
- correct video,
- transcript exists,
- timestamp accuracy.

## PASS 2 — Technical Accuracy

Verify:

- indicator mathematics,
- terminology,
- options concepts,
- API concepts.

## PASS 3 — Market Accuracy

Verify:

- exchange,
- instrument,
- expiry,
- lot size,
- strike rules,
- trading hours.

## PASS 4 — Quant Accuracy

Verify:

- backtest methodology,
- bias,
- costs,
- OOS,
- statistical validity.

## PASS 5 — Red-Team

Try to disprove the conclusions.

Only after all five passes:

```text
RESEARCH_READY_FOR_PROGRAMMING
```

---

# 70. CURRENT DHAN API FACTS TO VERIFY AT IMPLEMENTATION TIME

As of the research date, Dhan's documentation indicates:

### WebSocket

Real-time market feed via WebSocket.

https://dhanhq.co/docs/v2/live-market-feed/

### Historical

Minute-level historical data including 1, 5, 15, 25 and 60-minute intervals, with current documentation describing up to five years of intraday history and OI support for F&O.

https://dhanhq.co/docs/v2/historical-data/

### Option Chain

Current Option Chain API provides:

- LTP,
- OI,
- previous OI,
- volume,
- previous volume,
- IV,
- Greeks,
- top bid,
- top ask,
- quantities,
- security IDs.

https://dhanhq.co/docs/v2/option-chain/

### Market Depth

Dhan documentation/release notes describe 20-level market depth for NSE instruments via WebSocket.

Verify exact current API contract before implementation.

### SDK

Dhan provides official SDK documentation, including Python.

https://docs.dhan.co/api/v2/guides/sdks/python

These details are **implementation references, not permanent assumptions**. The coding agent must check the live documentation before coding.

---

# 71. NSE/BSE CONTRACT DATA

The strategy engine must dynamically ingest current contract information.

NSE official contract information:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-information

NSE contract specifications:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-specifications

For SENSEX and BSE derivatives, use current BSE documentation.

Never copy a static lot-size number into code.

---

# 72. RESEARCH OUTPUT FOR THE PROGRAMMING MODEL

The programming model should receive one clean master document containing:

## Section A

Project scope.

## Section B

Dhan source-video evidence.

## Section C

Transcript-derived education.

## Section D

Indicator definitions.

## Section E

Price-action rules.

## Section F

Options concepts.

## Section G

Risk-management concepts.

## Section H

Candidate strategies.

## Section I

Data requirements.

## Section J

Dhan API mapping.

## Section K

Backtest specification.

## Section L

Validation requirements.

## Section M

Strategy-selection criteria.

## Section N

Rejected strategies and why.

## Section O

Open questions / missing data.

---

# 73. DO NOT GIVE THE PROGRAMMING MODEL UNVERIFIED STRATEGIES

Every strategy handed to the coding model must have:

```text
Strategy ID
Source evidence
Source timestamps
Rule definition
Data requirements
Parameters
Assumptions
Known limitations
Backtest design
Validation status
```

Example:

```text
STRAT-001
Source:
Dhan video XYZ

Timestamp:
36:52–44:15

Dhan concept:
Option buying strategy

Project transformation:
...

Status:
NOT YET VALIDATED
```

---

# 74. STRATEGY RESEARCH WORKFLOW

Final workflow:

```text
Dhan Channel
      ↓
Video Discovery
      ↓
Popularity Ranking
      ↓
Relevance Ranking
      ↓
Transcript Extraction
      ↓
Transcript QA
      ↓
AI Topic Extraction
      ↓
Claim Extraction
      ↓
Indicator Extraction
      ↓
Strategy Extraction
      ↓
Independent Validation
      ↓
Options Translation
      ↓
Dhan API Mapping
      ↓
Candidate Strategy Library
      ↓
Backtest
      ↓
Out-of-Sample
      ↓
Walk-Forward
      ↓
Monte Carlo
      ↓
Cost/Slippage Stress
      ↓
Red-Team
      ↓
Strategy Ranking
      ↓
Paper Trading
      ↓
Execution Validation
      ↓
Controlled Deployment
```

---

# 75. WHAT "SUCCESS" MEANS

Success does NOT mean:

> "The AI found a strategy that made 30% every day in a backtest."

Success means:

> "The system found a statistically defensible trading edge that survives realistic execution assumptions, multiple market regimes, out-of-sample testing and independent review."

---

# 76. FINAL STRATEGY SELECTION RULE

The system should ultimately answer:

### For NIFTY

Which strategy has the strongest robust edge?

### For BANKNIFTY

Which strategy has the strongest robust edge?

### For SENSEX

Which strategy has the strongest robust edge?

And:

### Which option contract should be traded?

- CE/PE
- expiry
- strike
- delta range
- entry
- stop
- target
- quantity

But only after validation.

---

# 77. SIMPLE FINAL SIGNAL

The complexity stays inside the engine.

The user sees:

```text
NIFTY

BUY CE

Strike: XXXXX
Entry: ₹XX
Stop: ₹XX
Target: ₹XX

Reason:
Bullish structure + momentum + options confirmation

Risk:
X%

Status:
VALIDATED / PAPER / LIVE
```

---

# 78. AUDIT TRAIL

Every signal must be reproducible.

If a reviewer asks:

> Why did the system issue this signal?

The system must answer:

```text
Strategy:
STRAT-001 v1.4

Timestamp:
YYYY-MM-DD HH:MM:SS IST

Market:
NIFTY

Underlying state:
...

Option-chain state:
...

Indicators:
...

Price action:
...

Risk:
...

Data source:
DhanHQ

Decision:
BUY CE

Invalidation:
...

Model version:
...
```

---

# 79. FAILURE CONDITIONS

The system must explicitly fail if:

- transcript unavailable,
- source uncertain,
- data unavailable,
- API field unavailable,
- contract metadata missing,
- historical option data insufficient,
- backtest contains leakage,
- slippage ignored,
- costs ignored,
- strategy overfit,
- test set used for optimization,
- source attribution missing.

Failure is preferable to a fabricated answer.

---

# 80. PHASED IMPLEMENTATION ROADMAP

## PHASE 0 — Research Infrastructure

Build:

- YouTube cataloger,
- popularity ranker,
- transcript downloader,
- transcript store,
- metadata database.

## PHASE 1 — Dhan Data Infrastructure

Build:

- authentication,
- WebSocket collector,
- binary decoder,
- instrument resolver,
- historical downloader,
- option-chain service.

## PHASE 2 — Research Knowledge Base

Build:

- indicator database,
- price-action engine,
- options knowledge base,
- transcript claim database.

## PHASE 3 — Backtesting

Build:

- event-driven backtester,
- options contract resolver,
- cost model,
- slippage model,
- performance engine.

## PHASE 4 — Candidate Strategies

Build:

- opening strategies,
- momentum strategies,
- price-action strategies,
- options-chain strategies,
- multi-factor strategies.

## PHASE 5 — Validation

Build:

- OOS testing,
- walk-forward,
- Monte Carlo,
- regime analysis,
- parameter robustness.

## PHASE 6 — Paper Trading

Build:

- live signal generation,
- paper execution,
- signal audit,
- missed-signal tracking.

## PHASE 7 — Production

Only after validation:

- controlled execution,
- risk engine,
- circuit breakers,
- monitoring,
- alerts,
- reporting.

---

# 81. RECOMMENDED FIRST MVP

Do NOT build Bloomberg immediately.

First build:

```text
Dhan WebSocket
+
Dhan Historical API
+
Dhan Option Chain
+
NIFTY/BANKNIFTY/SENSEX
+
1m / 5m / 15m candles
+
Price Action
+
RSI
+
Supertrend
+
EMA
+
ATR
+
Option OI
+
IV
+
Greeks
+
Bid/Ask
+
Opening Range
+
Backtester
+
Risk Engine
+
Simple Dashboard
```

Then expand.

---

# 82. FIRST RESEARCH QUESTION

The first research experiment should answer:

> Can Dhan-derived price-action + trend/momentum + options-chain information produce a robust intraday edge in NIFTY, BANKNIFTY and SENSEX options after realistic transaction costs and slippage?

Do NOT start by searching for the strategy with the highest return.

Start by establishing whether the information has predictive value.

---

# 83. SECOND RESEARCH QUESTION

Determine:

> Is it better to predict the underlying direction first and then select an option, or directly predict the option premium movement?

Test both.

### Model A

Predict:

```text
NIFTY direction
```

Then select:

```text
CE / PE
```

### Model B

Predict:

```text
specific option return
```

Compare.

---

# 84. THIRD RESEARCH QUESTION

Determine the optimal option-selection method.

Compare:

```text
ATM
ATM ± 1 strike
ATM ± 2 strikes
Delta 0.40–0.60
Delta 0.50–0.70
ITM
OTM
```

Measure:

- return,
- drawdown,
- liquidity,
- slippage,
- expectancy.

---

# 85. FOURTH RESEARCH QUESTION

Determine whether the first 15–30 minutes contain a predictable market regime.

Test:

- opening gap,
- first candle,
- first 5-minute range,
- first 15-minute range,
- opening volume,
- option-chain state,
- previous-day structure.

Then determine whether the opening regime predicts:

- direction,
- volatility,
- large move,
- reversal.

---

# 86. FIFTH RESEARCH QUESTION

Determine whether combining Dhan concepts creates incremental edge.

Test:

```text
Price Action
vs
Price Action + RSI
vs
Price Action + Supertrend
vs
Price Action + RSI + Supertrend
vs
Price Action + Options
vs
Price Action + RSI + Supertrend + Options
```

If the combination does not outperform simpler models out-of-sample, use the simpler model.

---

# 87. RESEARCH DOCUMENT QUALITY STANDARD

The final document must be understandable by:

- another AI model,
- a senior Python engineer,
- a quantitative researcher,
- a derivatives trader,
- an independent reviewer.

It must be reproducible without watching the original videos.

Every important claim must have source provenance.

---

# 88. ABSOLUTE NO-HALLUCINATION RULE

The agent must NEVER write:

> "Dhan recommends X"

unless the transcript actually supports it.

It must NEVER write:

> "The expert said X"

unless the source transcript supports it.

It must NEVER invent:

- indicator settings,
- stop loss values,
- target values,
- win rates,
- profitability,
- API fields,
- historical availability,
- lot sizes.

If unknown:

```text
UNKNOWN
```

If unavailable:

```text
NOT AVAILABLE
```

If requiring verification:

```text
VERIFY BEFORE IMPLEMENTATION
```

---

# 89. SOURCE CITATION STANDARD

Every strategy component derived from a Dhan video must include:

```text
Source:
Dhan YouTube

Video:
<exact title>

Video ID:
<id>

URL:
<official URL>

Timestamp:
<start-end>

Transcript evidence:
<paraphrased statement>

Interpretation:
<our interpretation>

Independent validation:
<source>

Implementation status:
<status>
```

---

# 90. IMPORTANT DISTINCTION: EDUCATION ≠ PROOF

A Dhan video can provide a useful hypothesis.

It does NOT prove:

- profitability,
- predictive power,
- future performance,
- suitability for options,
- suitability for NIFTY,
- suitability for BANKNIFTY,
- suitability for SENSEX.

Every educational idea must become a hypothesis.

---

# 91. LEGAL / COMPLIANCE AWARENESS

Because the project may involve managing money for other individuals, the software architecture must be designed with appropriate professional/legal/compliance review.

Do not represent the platform as:

- guaranteeing returns,
- guaranteeing profits,
- eliminating risk.

Before live management of external capital, obtain qualified Indian legal/compliance advice concerning applicable:

- SEBI regulations,
- advisory/portfolio-management requirements,
- broker/API terms,
- client authorization,
- recordkeeping,
- disclosures,
- suitability,
- taxation,
- data licensing.

This document is a technical/research plan, not legal or investment advice.

---

# 92. FINAL DELIVERABLES

The project is complete only when it produces:

### Research

```text
Dhan Video Catalog
Transcript Corpus
Indicator Knowledge Base
Price Action Knowledge Base
Options Knowledge Base
Strategy Library
Validation Report
```

### Engineering

```text
Dhan Data Connector
Historical Data Loader
Option Chain Engine
Feature Engine
Backtester
Risk Engine
Signal Engine
Paper Trading Engine
Execution Engine
Dashboard
Audit System
```

### Strategy

```text
Validated Strategy Specifications
Parameter Ranges
Risk Rules
Option Selection Rules
Entry Rules
Exit Rules
Failure Conditions
Performance Reports
```

---

# 93. DEFINITION OF DONE

The project is NOT done when the code runs.

It is done when:

- data is verified,
- transcripts are verified,
- strategies are explicit,
- historical data is sufficient,
- backtests are reproducible,
- costs are included,
- slippage is modeled,
- out-of-sample results exist,
- walk-forward results exist,
- robustness is tested,
- risk is controlled,
- paper trading works,
- signals are auditable,
- live execution can be safely disabled,
- an independent reviewer can reproduce the research.

---

# 94. FIRST TASK FOR THE CODING AGENT

The first coding task is NOT to build the trading strategy.

Build:

```text
01_youtube_discovery.py
02_popularity_ranker.py
03_transcript_collector.py
04_transcript_validator.py
05_topic_classifier.py
06_claim_extractor.py
07_indicator_extractor.py
08_strategy_extractor.py
09_source_audit.py
```

Then produce:

```text
DHAN_RESEARCH_CORPUS.md
```

Only after that should the strategy-development agent begin.

---

# 95. FIRST TASK FOR THE RESEARCH AGENT

Prompt:

> Search ONLY the official Dhan YouTube channel. Build a complete catalog of videos and playlists. Rank videos by popularity using measurable public metrics. Filter for videos relevant to NIFTY, BANKNIFTY, SENSEX, index options, intraday trading, opening strategies, scalping, large-move capture, price action, candlesticks, technical indicators, option chains, Greeks, IV, OI, risk management, strategy construction and Dhan-specific indicators/tools. Exclude stock-only educational content from strategy construction. Retrieve publicly available transcripts. Do not invent missing transcript content. Preserve timestamps and source URLs. Extract only information actually supported by the transcript. Create a source-audited research corpus. Do not design the final strategy yet.

---

# 96. SECOND RESEARCH AGENT PROMPT

> Take the verified Dhan transcript corpus and classify every extracted concept into PRICE ACTION, CANDLESTICKS, INDICATORS, OPTIONS, OPTION CHAIN, VOLATILITY, MARKET STRUCTURE, OPENING, SCALPING, RISK MANAGEMENT and STRATEGY DESIGN. For every concept, preserve its original Dhan source and timestamp. Separate SOURCE FACT from INDEPENDENT VALIDATION from PROJECT HYPOTHESIS. Identify parameters exactly as spoken. Flag uncertain transcript values. Do not invent or optimize parameters.

---

# 97. THIRD RESEARCH AGENT PROMPT

> Independently validate every technical concept using authoritative technical references, exchange documentation and academic literature. Do not rewrite Dhan's claim to make it look correct. Instead record whether the claim is supported, partially supported, context-dependent or unsupported. Identify mathematical definitions, assumptions and failure modes. Pay special attention to indicators, options Greeks, IV, OI, price action and market microstructure.

---

# 98. FOURTH RESEARCH AGENT PROMPT

> Translate the validated concepts into explicit testable hypotheses for NIFTY, BANKNIFTY and SENSEX index options. For each hypothesis define market regime, timeframe, underlying data, option-selection method, entry, confirmation, stop, target, exit, risk, invalidation and required historical fields. Do not claim profitability. Mark every hypothesis UNVALIDATED until backtesting is completed.

---

# 99. FIFTH RESEARCH AGENT PROMPT

> Backtest all candidate strategies using realistic historical option contracts, historical lot sizes, realistic entry/exit assumptions, bid/ask where available, transaction costs, slippage and execution constraints. Perform out-of-sample testing, walk-forward validation, regime testing, parameter robustness and Monte Carlo analysis. Rank strategies by robust risk-adjusted performance rather than headline return. Reject strategies that fail robustness tests.

---

# 100. FINAL COMMAND TO THE ENTIRE AGENT TEAM

The mission is:

> **Do not search for a strategy that looks profitable. Search for a market behavior that remains statistically defensible after the market has been allowed to fight back.**

The final product should be:

**Dhan education → independently validated knowledge → measurable market features → testable hypotheses → robust strategy → controlled execution.**

Never reverse this order.

---

# APPENDIX A — OFFICIAL SOURCE STARTING POINTS

## Dhan

Official Dhan YouTube:

https://www.youtube.com/@DhanHQ

DhanHQ API:

https://dhanhq.co/docs/v2/

Live Market Feed:

https://dhanhq.co/docs/v2/live-market-feed/

Historical Data:

https://dhanhq.co/docs/v2/historical-data/

Option Chain:

https://dhanhq.co/docs/v2/option-chain/

Python SDK:

https://docs.dhan.co/api/v2/guides/sdks/python

## NSE

Contract Information:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-information

Contract Specifications:

https://www.nseindia.com/static/products-services/equity-derivatives-contract-specifications

## BSE

https://www.bseindia.com/

## SEBI

https://www.sebi.gov.in/

---

# APPENDIX B — INITIAL RESEARCH OBSERVATIONS

During preparation of this plan, current official/primary-source checks confirmed several important architectural facts:

1. Dhan provides a WebSocket live market feed.
2. Dhan provides historical OHLC data.
3. Dhan currently documents up to five years of intraday historical data for supported active instruments and OI support for F&O.
4. Dhan provides an Option Chain API with OI, Greeks, volume, IV, LTP and top bid/ask data.
5. Dhan documents 20-level market depth for NSE instruments.
6. Dhan provides official SDK documentation.
7. NSE publishes current contract information and permitted lot-size files.
8. SENSEX requires BSE-specific handling.
9. Dhan's official YouTube channel contains highly relevant educational material on option buying, price action, candlestick patterns, RSI/Supertrend and options strategy construction.

These are architecture inputs.

They are NOT evidence that any particular strategy is profitable.

---

# APPENDIX C — RESEARCH STATUS LABELS

Use only these statuses:

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

---

# APPENDIX D — GOLDEN RULES

1. Official Dhan YouTube is the only source for Dhan-video transcript extraction.
2. Popularity determines video priority, not strategy quality.
3. Never hallucinate transcript content.
4. Preserve timestamps.
5. Preserve source URLs.
6. Never invent parameters.
7. Never confuse stock concepts with options concepts.
8. Never confuse NIFTY with NIFTY futures/options.
9. Never assume an index has conventional traded volume.
10. Never hardcode current lot sizes into historical backtests.
11. Never use future information.
12. Never optimize on the test set.
13. Always model costs.
14. Always model slippage.
15. Test ATM vs ITM vs OTM rather than assuming.
16. Test expiry and non-expiry separately.
17. Test market regimes separately.
18. Use ablation testing.
19. Prefer robust parameter regions over one optimal number.
20. A strategy must survive out-of-sample testing.
21. A strategy must survive walk-forward testing.
22. A strategy must survive stress testing.
23. Risk engine can override signal engine.
24. Paper trading precedes live trading.
25. AI must never guarantee returns.
26. Every live decision must be auditable.
27. When evidence is missing, say UNKNOWN.
28. When data is insufficient, say DATA_INSUFFICIENT.
29. When uncertain, do not guess.
30. The final objective is a durable statistical edge, not an impressive backtest.

---

# END OF PLAN.md

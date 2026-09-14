# TradingView Editor Picks — strategies inventory

**Retrieved:** `2026-09-14T11:10:00Z` (curl SSR). **Layer:** HYPOTHESIS. **Status:** UNVALIDATED. **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`.

**KEEP_ALL.** Teacher `STRAT-001`–`014` unchanged. Listing IDs **`MIX-TV-EP-001`–`023`**. Factory calibrators **`024`–`025`** (not Editors’ Pick cards). Never `STRAT-015+`. Next listing drop = **`MIX-TV-EP-026`**. Origin: `WEB-DERIVED` / `TV-EDITOR-PICK`. Metrics **null**. No live orders. **Do not paste full Pine into git.** Rule cards: [`../../teams/01_research/docs/TV_EP_RULE_CARDS.md`](../../teams/01_research/docs/TV_EP_RULE_CARDS.md).

Listing: [Editor Picks · Strategies](https://www.tradingview.com/scripts/editors-picks/?script_type=strategies). Pointer: [`../stratigies/editor_pick.txt`](../stratigies/editor_pick.txt). Playbook: [`../../teams/01_research/docs/TV_EDITOR_PICK_INGEST.md`](../../teams/01_research/docs/TV_EDITOR_PICK_INGEST.md). MIX pointer: [`../../teams/04_quant/docs/MIX_CATALOG.md`](../../teams/04_quant/docs/MIX_CATALOG.md) §22.

## Snapshot counts

| Universe | Count |
|----------|------:|
| Unfiltered Editors’ Picks unique `/script/` slugs (32 listing pages) | 760 |
| Badge = Indicator | 656 |
| Badge = Library | 50 |
| Badge = Strategy (this catalog) | **23** |
| Strategies-filter SSR cards (page-1) | 23 |
| Factory calibrators (SMA/MACD, not listing cards) | 2 (`MIX-TV-EP-024`–`025`) |

## Blockers

- **WebFetch 409** on the strategies-filter URL; **curl HTML 200**.
- **JS pagination:** `.../page-N/?script_type=strategies` repeats page 1. Unfiltered `/scripts/editors-picks/page-N/` works and was used to confirm the 23 strategy badges.
- **Strategy Tester reports:** not on the public listing; per-chart session → `DATA_INSUFFICIENT`.
- **Not login-walled** for these 23: pine-facade returned source; we stored **inputs + summary only**.

## Status legend

| Flag | Meaning here |
|------|----------------|
| INGESTED | URL + title + author on disk |
| RULES_EXTRACTED | Public source seen; input names/defaults + rule summary stored (no Pine file) |
| PORT_PENDING | No NSE/OPTIDX adapter |
| BACKTEST_QUEUED | 06 may schedule; metrics still null |
| TESTED_FAIL / TESTED_PARK | After a scored run — **row stays** |
| NEVER_DISCARD | KEEP_ALL |

## MIX-TV-EP-001–023

| MIX | Title | Author | L/S | Asset guess | Inputs | Status |
|-----|-------|--------|-----|-------------|-------:|--------|
| `MIX-TV-EP-001` | [TASC 2026.08 An Ag Selling Model](https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/) | PineCodersTASC | short | commodity_futures_guess | 7 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-002` | [TASC 2026.03 One Percent A Week](https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/) | PineCodersTASC | long | us_equity_or_index_guess | 0 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-003` | [Trading Report Generator from CSV](https://www.tradingview.com/script/OTfw8b2a-Trading-Report-Generator-from-CSV/) | adolgov | long+short | crypto_guess | 1 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-004` | [TrendMaster Pro 2.3 with Alerts](https://www.tradingview.com/script/mVkDf8qh-TrendMaster-Pro-2-3-with-Alerts/) | everget | long+short | any_chart_guess (TV default; not NSE frozen) | 57 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-005` | [Bjorgum Double Tap](https://www.tradingview.com/script/rLkjr2sQ-Bjorgum-Double-Tap/) | Bjorgum | long+short | india_index_guess | 33 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-006` | [Traling.SL.Target](https://www.tradingview.com/script/4jxYYaGU-Traling-SL-Target/) | Sharad_Gaikwad | long+short | india_index_guess | 16 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-007` | [Template Trailing Strategy (Backtester)](https://www.tradingview.com/script/n8bgynWl-Template-Trailing-Strategy-Backtester/) | jason5480 | long+short | india_index_guess | 222 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-008` | [3Commas Bot](https://www.tradingview.com/script/MvlwAzSg-3Commas-Bot/) | Bjorgum | long+short | any_chart_guess (TV default; not NSE frozen) | 25 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-009` | [Monthly Returns in PineScript Strategies](https://www.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies/) | QuantNomad | long+short | us_equity_or_index_guess | 1 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-010` | [How to use Leverage and Margin in PineScript](https://www.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript/) | Peter_O | long+short | us_equity_or_index_guess | 3 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-011` | [Сalculation a position size based on risk](https://www.tradingview.com/script/hoCPm5UY-%D0%A1alculation-a-position-size-based-on-risk/) | adolgov | long+short | us_equity_or_index_guess | 2 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-012` | [Oscillator Evaluator (Analysis tool)](https://www.tradingview.com/script/M9taaIkp-Oscillator-Evaluator-Analysis-tool/) | mks17 | long+short | india_index_guess | 30 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-013` | [Built-in Kelly ratio for dynamic position sizing](https://www.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing/) | CryptoRox | long+short | us_equity_or_index_guess | 10 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-014` | [Ultimate Strategy Template](https://www.tradingview.com/script/2lGyzYkC-Ultimate-Strategy-Template/) | Daveatt | long+short | us_equity_or_index_guess | 29 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-015` | [Stop loss and Take Profit in $$ example](https://www.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example/) | adolgov | long+short | india_index_guess | 2 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-016` | [Stepped trailing strategy example](https://www.tradingview.com/script/jjhUHcje-Stepped-trailing-strategy-example/) | adolgov | long | india_index_guess | 4 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-017` | [PMax Explorer STRATEGY & SCREENER](https://www.tradingview.com/script/nHGK4Qtp/) | KivancOzbilgic | long+short | india_index_guess | 21 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-018` | [Grid Like Strategy](https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy/) | alexgrover | long+short | india_index_guess | 3 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-019` | [Gap Filling Strategy](https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy/) | alexgrover | long+short | india_index_guess | 1 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-020` | [inwCoin Martingale Strategy ( for Bitcoin )](https://www.tradingview.com/script/8OS1nbr8-inwCoin-Martingale-Strategy-for-Bitcoin/) | Real_inwCoin | long | crypto_guess | 11 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-021` | [LUBE](https://www.tradingview.com/script/i9tJOtjl-LUBE/) | Jomy | long+short | crypto_guess | 7 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-022` | [How To Set Backtest Time Ranges](https://www.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges/) | allanster | long | india_index_guess | 13 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-023` | [Grover Llorens Activator Strategy Analysis](https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis/) | alexgrover | long+short | us_equity_or_index_guess | 0 | RULES_EXTRACTED+PORT_PENDING+BACKTEST_QUEUED+NEVER_DISCARD |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossover | PROJECT | long+short | n/a | 2 | NEVER_DISCARD+BACKTEST_QUEUED (not a TV card) |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogram zero-cross | PROJECT | long+short | n/a | 3 | NEVER_DISCARD+BACKTEST_QUEUED (not a TV card) |

## Rule summaries (no Pine)

### MIX-TV-EP-001 — TASC 2026.08 An Ag Selling Model

- **URL:** https://www.tradingview.com/script/VFzCk3HX-TASC-2026-08-An-Ag-Selling-Model/
- **Visibility:** open-source
- **Default TF:** `1D`
- **Summary:** overlay=false/unknown; uses strategy.entry; uses strategy.close. █ OVERVIEW This strategy implements the "Ag Selling Model" as presented by Perry J. Kaufman in the August 2026 edition of the TASC Traders' Tips "Identifying The Best Price Levels For Selling Commodity Futures". The article describes a long-hold selling strategy for agricultural
- **Inputs (names+defaults, truncated):** Source=close; MA length=40; ATR length=20; ATR factor=2.5; Month of harvest=11; Delay in months after harvest=2; Days between trades=30
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-002 — TASC 2026.03 One Percent A Week

- **URL:** https://www.tradingview.com/script/nVECqIQx-TASC-2026-03-One-Percent-A-Week/
- **Visibility:** open-source
- **Default TF:** `15`
- **Summary:** strategy() title=TASC 2026.03 One Percent A Week; overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close. █ OVERVIEW This script implements "A High-Probability Weekly Trading Strategy For TQQQ" as dictated in the March 2026 edition of the TASC Traders' Tips, "Trading Snapbacks In A Leveraged ETF”. In this article the author creates a mean reversion strategy intended for systematic an
- **Inputs:** none parsed / likely hardcoded (`DATA_INSUFFICIENT` on named inputs).
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-003 — Trading Report Generator from CSV

- **URL:** https://www.tradingview.com/script/OTfw8b2a-Trading-Report-Generator-from-CSV/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** strategy() title=Trading Report Generator from CSV; overlay=true. Many people use the Trading Panel. Unfortunately, it doesn't have a Performance Report. However, TradingView has strategies, and they have a Performance Report :-D What if we combine the first and second? It's easy! This script is a special strategy that parses transactions in cs
- **Inputs (names+defaults, truncated):** Transactions CSV:="Symbol
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-004 — TrendMaster Pro 2.3 with Alerts

- **URL:** https://www.tradingview.com/script/mVkDf8qh-TrendMaster-Pro-2-3-with-Alerts/
- **Visibility:** open-source
- **Default TF:** `240`
- **Summary:** strategy() title=TrendMaster Pro 2.3 with Alerts; overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close.  Hello friends, A member of the community approached me and asked me how to write an indicator that would achieve a particular set of goals involving comprehensive trend analysis, risk management, and session-based trading controls. Here is one example method of how to create suc
- **Inputs (names+defaults, truncated):** MA Type="SMA"; Enable Higher Timeframe Trend=false; Trend MA Type="EMA"; Trend MA Length=50; Short-Term MA Length=9; Long-Term MA Length=21; Band Length=20; Band Type=2; Show Support & Resistance=false; Calculation Method="Traditional"; Timeframe="Auto"; Use Daily-Based Values=true; Number of Historical Levels=1; Show Labels=true; Show Prices=true … +42 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-005 — Bjorgum Double Tap

- **URL:** https://www.tradingview.com/script/rLkjr2sQ-Bjorgum-Double-Tap/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** overlay=true; uses strategy.entry; uses strategy.exit. █ OVERVIEW Double Tap is a pattern recognition script aimed at detecting Double Tops and Double Bottoms. Double Tap can be applied to the broker emulator to observe historical results, run as a trading bot for live trade alerts in real time with entry signals, take profit, and st
- **Inputs (names+defaults, truncated):** Use Strategy=true; Detect Bottoms=true; Detect Tops=true; Flip Trades=true; Pivot Tolerance=15; Pivot Length=50; Target Fib=100; Stop Loss Fib=0; Line Offset=30; Start Filter=timeStart; End Filter=timeEnd; Use Trail Stop=false; ATR Length=14; ATR Multiplier=1; Swing Lookback=5 … +18 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-006 — Traling.SL.Target

- **URL:** https://www.tradingview.com/script/4jxYYaGU-Traling-SL-Target/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** strategy() title=Traling.SL.Target; overlay=true; uses strategy.entry; uses strategy.close. Trailing SL and Target I have seen few requests in PineScripters telegram group asking questions about implementation of trailing stop-loss (SL) and targets. This script is one of the way to implement the same. This script is developed based on dark color theme and is best viewed
- **Inputs (names+defaults, truncated):** Pivot parameters for trade=false; Fast len=20; Slow len=50; BG color for ongoing trade SL/Target label=color.white; Method to be used for SL/Target trailing='% Based Target and SL'; % Based Target and SL=true; Inital profit %=1; Inital SL %=1; Initiate trailing %=0.5; Trail profit by %=0.3; Trail SL by %=0.3; Fix point Based Target and SL=false; Inital profit target points=100; Inital SL points=50; Initiate trailing points=60 … +1 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-007 — Template Trailing Strategy (Backtester)

- **URL:** https://www.tradingview.com/script/n8bgynWl-Template-Trailing-Strategy-Backtester/
- **Visibility:** open-source
- **Default TF:** `240`
- **Summary:** overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close. 💭 Overview + Title: Template Trailing Strategy (Backtester) + Author: Iason Nikolas (jason5480) + License: CC BY-NC-SA 4.0 💢 What is the "Template Trailing Strategy (Backtester)"❓ The "Template Trailing Strategy (Backtester)" (TTS) is a back-tester orchestration framework. It sup
- **Inputs (names+defaults, truncated):** Timezones Ref->Chart=chr.Timezone.Exchange; From=false; To=false; 01 Jan 2024 00:00=timestamp('01 Jan 2024 00:00'; 01 Jan 2025 00:00=timestamp('01 Jan 2025 00:00'; >=chr.Timezone.Exchange; Session Days=false; Sun=false; Mon=true; Tue=true; Wed=true; Thu=true; Fri=true; Sat=false; Session Time=false … +207 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-008 — 3Commas Bot

- **URL:** https://www.tradingview.com/script/MvlwAzSg-3Commas-Bot/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** strategy() title=3Commas Bot; overlay=false/unknown; uses strategy.entry; uses strategy.exit. Bjorgum 3Commas Bot A strategy in a box to get you started today With 3rd party API providers growing in popularity, many are turning to automating their strategies on their favorite assets. With so many options and layers of customization possible, TradingView offers a place no
- **Inputs (names+defaults, truncated):** Detect Long Trades=true; Detect Short Trades=true; Use Limit exit=true; Use ATR Trailing Stop=false; Allow Reversal Trades=false; Set Max Total DrawDown=false; Reward to Risk Ratio=1; Risk Adjustment=1; Swing Lookback=5; int_unnamed=20; ATR length=14; ATR Trailing Stop Multiplier=1.0; High/Low="High/Low"; R:R To Trigger Exit=0.0; EMA="EMA" … +10 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-009 — Monthly Returns in PineScript Strategies

- **URL:** https://www.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies/
- **Visibility:** open-source
- **Default TF:** `240`
- **Summary:** strategy() title=Monthly Returns in PineScript Strategies; overlay=true; uses strategy.entry. I'm not 100% satisfied with the strategy performance output I receive from TradingView. Quite often I want to see something that is not available by default. I usually export raw trades/metrics from TradingView and then do additional analysis manually. But with tables, you can bu
- **Inputs (names+defaults, truncated):** Return Precision=2
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-010 — How to use Leverage and Margin in PineScript

- **URL:** https://www.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** overlay=false/unknown; uses strategy.entry; uses strategy.exit. En route to being absolutely the best and most complete trading platform out there, TradingView has just closed 2 gaps in their PineScript language. It is now possible to create and backtest a strategy for trading with leverage. Backtester now produces Margin Calls - so recognize
- **Inputs (names+defaults, truncated):** K=13; D=3; Smooth=4
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-011 — Сalculation a position size based on risk

- **URL:** https://www.tradingview.com/script/hoCPm5UY-%D0%A1alculation-a-position-size-based-on-risk/
- **Visibility:** open-source
- **Default TF:** `1D`
- **Summary:** strategy() title=Сalculation a position size based on risk; overlay=true; uses strategy.entry; uses strategy.exit. This is an example how to calculate position size based on risk and stop loss for educational purpose.
- **Inputs (names+defaults, truncated):** Stop Loss %%=10; Risk=2
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-012 — Oscillator Evaluator (Analysis tool)

- **URL:** https://www.tradingview.com/script/M9taaIkp-Oscillator-Evaluator-Analysis-tool/
- **Visibility:** open-source
- **Default TF:** `120`
- **Summary:** overlay=false/unknown; uses strategy.entry; uses strategy.exit; uses strategy.close. Oscillator Evaluator (Analysis tool) The oscillator evaluator is a tool that will help you analyse and compare the oscillator of your choice to another 2 oscillators. By selecting the strategy with which you will analyze the oscillators, you will be able to see the behaviour of t
- **Inputs (names+defaults, truncated):** Average Returns Ratio Adjustment=1; Show Long Entries Only=false; Show Short Entries Only=false; Strategy Selector="MA Strategy"; Oscillator Selector="Oscillator 1"; Oscillator 1 Scale Adjustment=1; Oscillator 1 Timeframe Adjustment=0.2; Oscillator 2 Scale Adjustment=1; Oscillator 2 Timeframe Adjustment=0.2; Oscillator 3 Scale Adjustment=1; Oscillator 3 Timeframe Adjustment=0.2; MA Strat Length=7; MA Strat Range Threshold=0.07; MA Crossover Strat Short Length=3; MA Crossover Strat Long Length=9 … +15 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-013 — Built-in Kelly ratio for dynamic position sizing

- **URL:** https://www.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing/
- **Visibility:** open-source
- **Default TF:** `240`
- **Summary:** strategy() title=Built-in Kelly ratio for position sizing; overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close. This is the defaut keltners channel strategy with a few additions. The main purpose is to show how we include the Kelly ratio into our scripts for dynamic position sizing based on the performance of the strategy on a per trade basis. We've also included the usual take-profit and
- **Inputs (names+defaults, truncated):** Kelly Ratio Position Sizing=true; Multiplier=1.0; Source=close; Use Exponential MA=true; Bands Style=options = ["Average True Range"; ATR Length=10; use Take Profit=false; use Stop Loss=false; take profit=10.0; stop loss=1.0
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-014 — Ultimate Strategy Template

- **URL:** https://www.tradingview.com/script/2lGyzYkC-Ultimate-Strategy-Template/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close. Hello Traders As most of you know, I'm a member of the PineCoders community and I sometimes take freelance pine coding jobs for TradingView users. Off the top of my head, users often want to: - convert an indicator into a strategy, so as to get the backtesting statistics from Tra
- **Inputs (names+defaults, truncated):** Data source=close; Use Custom Close?=false; Colour Candles to Trade Order state=true; Close positions at market at the end of each session ?=false; Trading Session="0000-2345"; Open  Trading Direction="ALL"; Close Trading Direction="ALL"; Close on Opposite Signal=true; ═════════════ Date Range Filtering=false; 01 Jan 2019 13:30 +0000=timestamp("01 Jan 2019 13:30 +0000"; 30 Dec 2021 23:30 +0000=timestamp("30 Dec 2021 23:30 +0000"; ═════════════ Set Max number of consecutive loss trades=false; Max of consecutive loss trades=15; ═════════════ Set Max number of consecutive won trades=false; Max Winning Streak Length=15 … +14 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-015 — Stop loss and Take Profit in $$ example

- **URL:** https://www.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example/
- **Visibility:** open-source
- **Default TF:** `1`
- **Summary:** strategy() title=Stop loss and Take Profit in $$ example; overlay=true; uses strategy.entry; uses strategy.exit. This is a simple exit example in $$ (symbol's currency) for educational purpose.
- **Inputs (names+defaults, truncated):** Take Profit $$=200; Stop Loss $$=100
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-016 — Stepped trailing strategy example

- **URL:** https://www.tradingview.com/script/jjhUHcje-Stepped-trailing-strategy-example/
- **Visibility:** open-source
- **Default TF:** `1D`
- **Summary:** strategy() title=Stepped trailing strategy example; overlay=true; uses strategy.entry; uses strategy.exit. This is a stepped trailing exit example for educational purpose. Short brief. There are 1 stop loss and 3 profit levels. When first tp is reached we move stop loss to break-even. When second tp is reached we move stop loss to first tp. When third tp is reached we exit by profit.
- **Inputs (names+defaults, truncated):** stop loss %%=5; take profit 1 %%=5; take profit 2 %%=10; take profit 3 %%=15
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-017 — PMax Explorer STRATEGY & SCREENER

- **URL:** https://www.tradingview.com/script/nHGK4Qtp/
- **Visibility:** open-source
- **Default TF:** `1D`
- **Summary:** strategy() title=PMax Explorer; overlay=true; uses strategy.entry. Profit Maximizer - PMax Explorer STRATEGY & SCREENER screens the BUY and SELL signals (trend reversals) for 20 user defined different tickers in Tradingview charts. Simply input the name of the ticker in Tradingview that you want to screen. Terminology explanation: Confirmed Reve
- **Inputs (names+defaults, truncated):** Source=hl2; ATR Length=10; ATR Multiplier=3.0; Moving Average Type="EMA"; Moving Average Length=10; Change ATR Calculation Method ?=true; Show Moving Average?=true; Show Crossing Signals?=true; Show Price/Pmax Crossing Signals?=false; Highlighter On/Off ?=true; Show Screener Label=true; Pos. Label x-axis=20; Pos. Size Label y-axis=1; Label Color="Blue"; =Backtest Inputs==true … +6 more in catalog.json
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-018 — Grid Like Strategy

- **URL:** https://www.tradingview.com/script/oxvR5vMy-Grid-Like-Strategy/
- **Visibility:** open-source
- **Default TF:** `15`
- **Summary:** strategy() title=Grid Like Strategy; overlay=true; uses strategy.entry; uses strategy.exit. It is possible to use progressive position sizing in order to recover from past losses, a well-known position sizing system being the "martingale", which consists of doubling your position size after a loss, this allows you to recover any previous losses in a losing streak + winn
- **Inputs (names+defaults, truncated):** Order Size=1; Martingale Multiplier=2.; Anti Martingale=false
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-019 — Gap Filling Strategy

- **URL:** https://www.tradingview.com/script/ghocsiv7-Gap-Filling-Strategy/
- **Visibility:** open-source
- **Default TF:** `15`
- **Summary:** strategy() title=Gap Filling Strategy; overlay=true; uses strategy.entry; uses strategy.exit; uses strategy.close. Gaps are market prices structures that appear frequently in the stock market, and can be detected when the opening price is different from the previous closing price, this is why gaps are also called "opening price jumps". While gaps can occur frequently, some of them are more si
- **Inputs (names+defaults, truncated):** New Session="Close When:"
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-020 — inwCoin Martingale Strategy ( for Bitcoin )

- **URL:** https://www.tradingview.com/script/8OS1nbr8-inwCoin-Martingale-Strategy-for-Bitcoin/
- **Visibility:** open-source
- **Default TF:** `240`
- **Summary:** strategy() title=inwCoin Martingale Strategy ( for Bitcoin ); overlay=true; uses strategy.entry; uses strategy.close. ** Same as my previous martingale script but this version = opensource ** inwCoin Martingale Strategy is the proof of concept strategy that in the end, anyone who using martingale strategy will kaboom their portfolio. For those who don't know what is "martingale".. it's a simple
- **Inputs (names+defaults, truncated):** Start Position Logic="MACD Line > 0"; Take Profit Percent=5.0; Start Martingale if price drop with this Percent=10.0; Martingale Multiplier=2.0; Trade direction="Long Only"; From Year=2018; From Month=1; From Day=1; To Year=9999; To Month=1; To Day=1
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-021 — LUBE

- **URL:** https://www.tradingview.com/script/i9tJOtjl-LUBE/
- **Visibility:** open-source
- **Default TF:** `30`
- **Summary:** strategy() title=LUBE; overlay=false/unknown; uses strategy.entry; uses strategy.close. This is a chart meant for 30m BTCUSD but could be used for many other assets, and there are inputs to play with. I decided on the strange title "LUBE" because I was measuring how many of the previous 500 bars had the current price level already been in. I wanted to discover when
- **Inputs (names+defaults, truncated):** bars back to measure friction=500; 0-100 friction level to stop trade=50; pic lower than 0 to number selected above to initiate trade=-10; bars back to measure lowest friction=100; Source=close; leverage=2; enable shorts?=true
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-022 — How To Set Backtest Time Ranges

- **URL:** https://www.tradingview.com/script/xAEG4ZJG-How-To-Set-Backtest-Time-Ranges/
- **Visibility:** open-source
- **Default TF:** `30`
- **Summary:** overlay=true; uses strategy.entry; uses strategy.close.  Example how to set the time range window to be backtested for both entries and exits. Additional examples are also included showing how to set the date range and toggle plot visibility. By incorporating this code with your own strategy's logic, it will allow you to backtest vari
- **Inputs (names+defaults, truncated):** FastMA Length=14; SlowMA Length=28; From Month=1; From Day=1; From Year=2021; Thru Month=1; Thru Day=1; Thru Year=2112; Entry Time='0000-0000'; Exit Time='0000-0000'; Show Date Range=true; Show Time Entry=true; Show Time Exit=true
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

### MIX-TV-EP-023 — Grover Llorens Activator Strategy Analysis

- **URL:** https://www.tradingview.com/script/VuYM89Tw-Grover-Llorens-Activator-Strategy-Analysis/
- **Visibility:** open-source
- **Default TF:** `60`
- **Summary:** strategy() title=Grover Llorens Activator; overlay=false/unknown; uses strategy.entry. The Grover Llorens Activator is a trailing stop indicator deeply inspired by the parabolic SAR indicator, and aim to provide early exit points and reversal detection. The indicator was posted not so long ago, you can find it here : https://www.tradingview.com/script/UVzC9TOv-Grov
- **Inputs:** none parsed / likely hardcoded (`DATA_INSUFFICIENT` on named inputs).
- **Chart report:** DATA_INSUFFICIENT (tester is per-session).

## Files

- `ingest_schema.json` — factory schema for the next 1000 pines
- `catalog.json` — durable inventory (`entries[]`)
- `catalog.csv` — spreadsheet view
- this `INDEX.md`


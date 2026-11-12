# Dhan DEXT web terminal — map for paper research

**Status:** `SOURCE_FACT` (read from the live UI on 2026-11-12, after market close, founder's own Chrome session). **Paper only.** Nothing here is permission to place an order. Live trading is approved only in the trading system (`mode = LIMITED_LIVE` / `LIVE` + founder confirm), never in a chat or in this file.

**What this file answers:** what each DEXT panel shows, what it carries that our recorder tape lacks, how to open it fast, how to build one reusable research workspace, and where the order ticket lives (read only).

URL: `https://dext.dhan.co/dashboard`. DEXT is a widget desk: every panel is a "widget", widgets open as tabs inside a panel region, panel regions can be popped out or maximized, and the whole arrangement is a "layout" (workspace). Keyboard shortcuts are listed next to each widget in the Widgets menu.

Screenshots from the exploration stay in the session scratchpad (never in the repo: the top bar shows funds and P&L).

---

## 0. Two things to know before touching the account

1. **Workspace "Auto Save" is ON by default.** The workspace dropdown (top-left, "Default") has *My Layouts (1): Default*, an **Auto Save** toggle, *Shared Layouts (0)*, *+ Create*, and nine Dhan preset layouts (*Dext Home, Watchlist Tracker, Trade on Charts, Expiry / Options Trader, Market Scanner, Scalper Trading, Ladder Watch, Portfolio Tracker, Strategy Builder*). With Auto Save on, **every widget you open or close is written to the account's saved workspace immediately.** During this exploration the extra widgets were opened in Default and then all closed again, and the chart was set back to SENSEX index 1-minute, so Default is as it was (one Chart widget). The research template must be a **separate** workspace made with *+ Create* so Default stays untouched. That creation is the one account write this task asked permission for; it was not done because the founder had not yet said yes.
2. **One-click trading widgets exist.** *Option Scalper*, *Power Scalper*, *Floating Scalper* and the *Price Ladder* show green **Buy** / red **Sell** buttons with lot count next to every strike. A click there is an order, not a form. Do not open them during paper sessions. The watchlist and option chain also show small **B / S** buttons per row. The Chart's two coloured price boxes (red SELL, blue BUY, top-left of every chart) are order buttons too.

---

## 1. Charts (widget "Chart", F8) — TradingView engine

**How to open:** Widgets → Graphs → Chart, or F8. Symbol search: click the symbol name top-left, or just start typing while the chart has focus. The search box has tabs **All / Equity / Futures / Options / Index**.

**Loading an option chart:** type `SENSEX 81900` (or `NIFTY 25300`) with the **Options** tab selected; the list shows one row per expiry and side, named like `SENSEX 19 NOV 81900 CALL` (BSE) or `NIFTY 17 NOV 25300 CALL` (NSE). Nearest weekly expiry is the first rows. Pick the row to load it. The chart keeps whatever indicators were on it when the symbol changes.

**Loading the index:** type `SENSEX` or `NIFTY` with the **Index** tab; `SENSEX-INDEX` / `NIFTY` (IDX).

**Switching expiry or strike:** there is no expiry / strike picker on the chart itself. Re-run the symbol search with the new strike, or use the Option Scalper's strike/expiry dropdowns (that widget has buttons that trade; avoid it).

**Strike steps seen:** NIFTY 50 points (25250 / 25300 / 25350), SENSEX 100 points (81800 / 81900 / 82000).

**Intervals offered (interval button, left of "Indicators"):** 5 s, 15 s, 30 s · 1, 2, 3, 4, 5, 10, 15, 30, 45, 75, 125 minutes · 1, 2, 3, 4 hours · 1 day, 1 week, 1 month, 3, 6, 12 months · "Add custom interval". Bottom bar has quick ranges 5Y 3Y 1Y 6M 3M 1M 1W 1D.

**Bar types:** Bars, Candles, Hollow candles, Volume candles, HLC bars, Line, Line with markers, Step line, Area, HLC area.

**Indicators (the "fx Indicators" button):** a searchable list. Confirmed present by search:
- `Average Directional Index` (ADX) — search "ADX". Length is set in its settings (use 14).
- `Choppiness Index`, `Chop Zone`.
- `Moving Average` (simple), `Moving Average Exponential`, Weighted, Hull, Double, Triple, Adaptive, Channel, `Dhan ML Moving Average`, `Distance from Moving Average`.
- `Volume`, `Volume Oscillator`, `Net Volume`, `Total Rupees Volume`, `Volume Profile Fixed Range`, `Volume Profile Visible Range`, `Volume Trend Delta` (new), `Price Volume Trend`, `On Balance Volume`.
- Dhan-specific: `Dhan OI Profile` (new), `Dhan Open Interest`, `Dhan Change in Open Interest`, `Dhan Multi Open Interest`, `Dhan Delta`, `Dhan Implied Volatility`, `Dhan HalfTrend`, `Dhan AlphaTrend`, `Dhan Signal MA`, `Dhan SSA Oscillator`, `Dhan Candlestick Patterns`, `Super Scalper`.
- Also new: `True Range`, `Daily Average True Range`, `No gaps candles`, `Woodies CCI`, `Anchored VWAP With Bands`, `Pivot Points Standard`.
- **Not present:** no indicator named "Order Block" and none named "Fair Value Gap" / "FVG" (search returns nothing for "order block"; "gap" only finds "No gaps candles"). FVGs and order blocks have to be read by eye from the 5-minute candles or drawn with the rectangle tool. The founder's phrase "order blocks" most likely maps to the **Order Flow** widget's footprint clusters (section 3), not to a chart indicator.

**Founder's current chart layout ("DEXT layout"):** VPVR (Volume Profile Visible Range, 24 rows), SuperTrend 10/3, VWAP hlc3 session, EMA 21, Volume, Dhan OI Profile ×4, Dhan HalfTrend 2/2, plus Dhan's on-chart labels *Resistance strike*, *Support strike*, *Expected move* (upper/lower), *Max Pain*. Many of these are the chain-derived levels the E33 state needs (max-OI strike, expected move).

**Chart layouts vs workspaces:** the chart has its own saved layout menu (arrow next to "DEXT layout": *Save layout ⌘S, Make a copy, Rename, Open layout*), and a *Save Indicator template* button (grid icon). Chart layouts are **not** auto-saved: after a symbol or interval change a small "Save" appears under the layout name and nothing is written until ⌘S. Indicator templates are the way to stamp the same indicator set onto the CE and PE charts.

---

## 2. Options Chain (Alt+O)

**Shows:** per expiry, per strike, both sides: Price, Change, Change %, **Buildup** label (Short Buildup / Long Unwinding / Short Covering / Long Buildup), Bid, Ask, **Volume**, **OI**, **OI Chg**, **OI Chg %**, Open, High, Low, Close, Delta, Theta, IV, Gamma, Vega, Intrinsic (spot / futures), Time Value, VWAP, Breakeven, POP. Columns are chosen with the column-chooser icon (search box + checkboxes + Reset/Save). Header strip: ATM IV, ATM IV Chg %, PCR, Market Lot (SENSEX 20, NIFTY 65 seen in the scalper), Days to Expiry, Max Pain. The strike column marks **ATM**, **OI Support**, **OI Resistance**, **Max Pain**, and the top-6 strikes by OI (`OI1..OI6`), volume (`V1..V6`) and IV (`IV1..IV6`). A settings gear toggles *Insights, Active OI, Key Summary*. Qty / Lot toggle for the quantity unit.

**Expiry:** a dropdown with every listed expiry (weekly then monthly then quarterly out to 2031). **Caution:** the chain, OI Graph, Greeks Exposure and Option Scalper label expiries one day **earlier** than the contract names in symbol search (chain "18 Nov 2026" = contract "SENSEX 19 NOV"; "16 Nov 2026" = "NIFTY 17 NOV"; the SENSEX chain's first expiry read "11 Nov 2026" with Days to Expiry 1 on the 12 Nov expiry day). Looks like a UTC-midnight rendering slip. Match expiries by week, not by date, and verify once on a live session.

**Row actions:** hovering a price cell shows a "..." menu (buy/sell/chart). Do not use the trade entries.

**What this gives the tape:** the tape (`scripts/lab5y/fin1_shadow.py`, E33 state) has spot per minute and option bid/ask only. The chain adds **OI, OI change, volume, IV and greeks per strike**, which is exactly what the E33 "ATM OI flow" vote reads as `None` today. Snapshots refresh every few seconds on screen; OI itself updates on the exchange's own cadence (minutes), so a 1-minute hand log is the realistic resolution.

---

## 3. Order Flow (Shift+O) — footprint engine ("dext-chart")

A different chart engine from the main Chart (its own symbol search with All/Equity/Options/Futures/Index tabs, its own layout list, *Replay* button, *Data Window*, multi-chart grid up to 8 panes with symbol / interval / crosshair / time / date-range sync toggles).

**Shows per bar:** bid-volume × ask-volume clusters at each price (the footprint), bar **Volume**, bar **Delta** (ask minus bid volume), **Cum Δ** (cumulative delta), and a bottom pane "Vol Δ Session Histogram 14". Settings → *Clusters / Orderflow*: display mode (Delta, …), sell/buy column text (volume), fills. Indicators here: *Technicals (165)* and *Community (44)*.

**Intervals:** 5, 10, 15, 20, 25, 30, 45 minutes · 1–4 hours · 1 day · 1 week · months. **No 1-minute** footprint; 5 minutes is the floor, which matches the E33 5-minute bar.

**What this gives the tape:** signed (aggressor) volume per price per 5-minute bar. That is the E33 **tick-rule signed volume** vote without having to infer sign from bid/ask mids. A NIFTY 17 NOV 25300 CALL 5-minute footprint loaded fine after hours (12 Nov session).

**Layout menu (name dropdown, top right):** *Save layout, Rename, Make a copy, Create new layout, Export chart data, Show all layouts, Delete layout*. Changing the interval marks the layout "Save"-pending; nothing is stored until saved.

---

## 4. Depth, Price Ladder, Time and Sales

- **Depth:** per instrument: Open/High/Low/Close, Volume, Avg Price, circuits, LTQ, LTT, Last trading day, Days to Expiry, then **Buy Orders** (orders / quantity / bid) vs **Sell Orders** (ask / quantity / orders) with totals. Header has Buy / Sell buttons (order form). Level count ("max depth", 5 vs 20) could not be read after hours: the book was empty. Verify in a live session.
- **Price Ladder (Alt+L):** DOM-style ladder for one instrument with an *Exit Rules* checkbox and settings *Show empty price levels / Show prices between bid-ask / Show cumulative volume*. It is a trading ladder (clicks place orders). After hours it says "Market is closed".
- **Time And Sales (F7):** tick prints (not opened; name and shortcut from the menu).

---

## 5. Analytics widgets

- **Technicals (Alt+T):** table of **SMA** or **EMA** at periods 5 / 10 / 20 / 50 / 100 / 200 with Bullish / Bearish signal, timeframe **1 min / 5 min / 15 min / 1 Day**, plus a "Technical Indicators" mode. The **20-SMA on 1 Day** is the E33 prior-day 20-day moving-average bias, read directly (NIFTY 1-day 20-SMA was 23,500.56 on 12 Nov).
- **Straddle Chain:** per strike: straddle price, change, call/put LTP and changes, total delta, combined IV, theta, vega, gamma; expiry arrows.
- **Greeks Exposure:** *Delta Exposure* and *Gamma Exposure* by strike (call / put / net bars), with labels **Put Support**, **Call Resistance**, **Delta Flip**, **Spot**, totals and a **DEX ratio** (0.55 "Bullish" seen). Controls: expiry, ATM range (±10), bars/other graph, All Values filter. Header has Buy/Sell buttons.
- **OI Graph (Alt+G):** call OI vs put OI by strike, with increase/decrease shading, intraday replay slider 09:15 → 15:39, totals and PCR at the bottom. Needs a live session for the intraday series.
- **IV Chart, Straddle Chart, Volatility Skew, Relative Cycle Graph, Candlesticks Pattern, VWap Indicator, Heatmap, Live Scanner, Futures Chain, Fundamentals, Corporate Actions, Cyclical Trend, Movers, Indices, ETF, Trending, Custom Screens (new):** listed in the Widgets menu, not opened in this pass.

---

## 6. Watchlist (Alt+W), Alerts, Layouts

- **Watchlist:** preset lists (e.g. Nifty 50 constituents) with Symbol, **B/S buttons**, LTP, Chg, % Chg, Volume, Trade Value; *Add section*, column chooser, pencil to edit, settings. An index-options watchlist for the ATM strikes would need creating (an account write, not done).
- **Alerts (Widgets → Tools → Alerts):** *Create Alert* opens a *Set Alert* form with tabs **Price** (target or change %), **Technical** (indicator e.g. Simple Moving Average with period 5/10/20/50/100/200, condition Greater Than / …, versus Price, timeframe, expiration date, "notify on every trigger"), **Scanner**, **Candlestick**; each alert can carry **Set an Order**, **Add a Webhook**, **Add a Note**. The order and webhook hooks are the terminal's own automation path; the repo rule keeps them unused (the form was cancelled, no alert created).
- **Layouts:** see section 0. Workspace = which widgets, where. Chart layout = indicators on one Chart widget. Order Flow layout = its own.
- **Strategy Builder (Alt+B), Basket, News, Message Bar, Notifications (F9), Portfolio (F12), Positions (F4), Orders (F3), Super Orders:** account/tool widgets. Super Orders showed "Super orders when placed appear here" (empty).

---

## 7. The research template ("E33 desk") — exact recipe

Not yet saved (needs the founder's yes, then *+ Create* in the workspace dropdown, name `E33 desk`, Auto Save on). Build it like this, in order:

| # | Widget | Instrument / setting | Why (E33 state) |
|---|--------|----------------------|-----------------|
| 1 | Chart (F8) | Index (NIFTY or SENSEX), **5 minutes**, candles. Indicators: `Average Directional Index` length 14; `Choppiness Index` 14; `Volume`; `Dhan OI Profile`; keep the founder's VWAP + Expected move + Support/Resistance strike labels. Draw PDH / PDL / opening-range lines with the horizontal-line tool. | ADX-14, chop, efficiency read off the 5-minute index bars; candle shape and fair-value gaps by eye on 5-minute. |
| 2 | Chart (F8) | Same index, **1 day**, `Moving Average` length 20. | Prior-day 20-SMA bias vote (or read the Technicals table, row 20-SMA, 1 Day). |
| 3 | Chart (F8) | ATM CE, nearest weekly, **5 minutes**, same indicator template as #1 (use *Save Indicator template* once, apply twice). | Option candle shape, premium vs spot. |
| 4 | Chart (F8) | ATM PE, same. | |
| 5 | Options Chain (Alt+O) | Same index, nearest weekly; columns Price, Volume, OI, OI Chg, OI Chg %, IV, Delta; Insights + Key Summary on. | ATM OI flow vote; max-OI strike level. |
| 6 | Order Flow (Shift+O) | ATM CE on 5 minutes (second pane: ATM PE), Delta display. | Tick-rule signed volume vote. |
| 7 | Technicals (Alt+T) | Index, SMA, 1 Day. | 20-SMA bias as a number. |

Arrangement: widgets open as tabs in one region; pop one out (the "Pop Out" icon on the region header) to float it, or use a Dhan preset (*Expiry / Options Trader*) as the starting grid and swap its panels. Dragging a tab onto the page did not split the region in this pass; the preset-grid route is the reliable one. Charts #1, #3, #4 side by side across the top, chain and order flow across the bottom, Technicals as a narrow tab. ATM strike changes during the day: re-run the symbol search on charts #3/#4 and the Order Flow pane (no auto-roll).

---

## 8. Order placement path (read only; nothing was placed)

**Rule restated:** paper only until the founder enables LIMITED_LIVE / LIVE in the trading system and confirms there. No order, modify, cancel, test order, alert-order or scalper click was made during this mapping. The order ticket itself was not opened: the browser-permission layer refused the click on a **Buy** button, and no second attempt was made. Fields below come from the Dhan order API inventory the repo already holds, which the web ticket mirrors.

- **Where the ticket is:** any **Buy / Sell** header button (Depth, Technicals, Greeks Exposure), any **B / S** row button (watchlist, chain), the red/blue **SELL / BUY** price boxes on every chart, the Price Ladder cells, and the scalper widgets (one-click).
- **Fields (from `DHAN_API_END_TO_END.md` § H):** transaction type (BUY/SELL), exchange segment, **product type** (F&O: `INTRADAY` or `MARGIN`; CNC/MTF are equity only), **order type** (MARKET, LIMIT, STOP_LOSS, STOP_LOSS_MARKET), validity (DAY / IOC), quantity (lots), price, trigger price, after-market-order flag + AMO time, bracket fields `boProfitValue` / `boStopLossValue`, correlation id.
- **Super order** (`/super/orders`): one entry leg plus **target**, **stop loss** and **trailing jump** legs; each leg can be modified or cancelled separately (`ENTRY_LEG`, `TARGET_LEG`, `STOP_LOSS_LEG`). The *Super Orders* widget lists them. Order placement via API needs a static IP; the web terminal does not.
- **Exit Rules** checkbox (Price Ladder, Option Scalper) attaches the account's saved exit rules to a scalper entry.

---

## 9. What DEXT shows that the recorder tape lacks

| Tape has (per minute) | Tape lacks | DEXT panel that has it |
|---|---|---|
| Spot close | Index volume (indices have none on exchange; DEXT shows a synthetic "Volume" on the index chart, treat as derived) | Chart |
| Option bid / ask | **Option OI, OI change, volume** per strike | Options Chain, OI Graph, Dhan OI Profile on chart |
| | **Signed (aggressor) volume per price per 5 min** | Order Flow |
| | IV, greeks per strike, PCR, max pain, expected move | Options Chain header, Straddle Chain, Greeks Exposure |
| | Order-book depth (bid/ask quantities and order counts) | Depth, Price Ladder |
| | Daily SMA table | Technicals |

E33 votes marked `None` in `fin1_shadow.py` because the tape has no OI or volume: **ATM OI flow** (chain OI Chg) and **tick-rule signed volume** (Order Flow delta). The other three votes (fair-value gap, 5-minute candle shape, 20-SMA bias) are readable from the 5-minute chart and the Technicals table.

---

## 10. How Fable would use this during a paper session

1. **09:00** open the `E33 desk` workspace (once it exists). Set charts #3/#4 and Order Flow to the strike nearest spot. Note PDH / PDL from the daily chart, read 20-SMA from Technicals.
2. **09:15–09:30** watch the opening range on chart #1; note ADX-14 and chop. Regime call is written down with the numbers, not just "trending".
3. **Every 5 minutes** (bar close): log, by hand or by screenshot, ATM CE and PE **OI Chg** and **Volume** from the chain, and the bar **Delta** from Order Flow. These are the two votes the tape cannot score; the paper log gets a column each.
4. **Levels:** max-OI strike from the chain's OI1 marker; expected-move and support/resistance labels already on the founder's chart.
5. **Never** open the scalper widgets, click a B/S button, or create an alert with "Set an Order". If a ticket opens by accident, close it with its X; no Confirm.
6. **Post-market** copy the hand log next to the tape for that day so the E33 vote scoring can be re-run with real OI/volume instead of `None`.

Verify on the first live session: Depth level count, the expiry-label off-by-one, whether the Order Flow footprint streams live for weekly options, and whether workspace Auto Save also persists chart symbol changes (it did in this pass).

# Dhan DEXT web terminal — map for paper research

**Status:** `SOURCE_FACT` (read from the live UI on 2026-11-12, after market close, founder's own Chrome session). **Paper only.** Nothing here is permission to place an order. Live trading is approved only in the trading system (`mode = LIMITED_LIVE` / `LIVE` + founder confirm), never in a chat or in this file.

**What this file answers:** what each DEXT panel shows, what it carries that our recorder tape lacks, how to open it fast, how to build one reusable research workspace, and where the order ticket lives (read only).

URL: `https://dext.dhan.co/dashboard`. DEXT is a widget desk: every panel is a "widget", widgets open as tabs inside a panel region, panel regions can be popped out or maximized, and the whole arrangement is a "layout" (workspace). Keyboard shortcuts are listed next to each widget in the Widgets menu.

Screenshots from the exploration stay in the session scratchpad (never in the repo: the top bar shows funds and P&L).

---

## 0. Two things to know before touching the account

1. **Workspace "Auto Save" is ON by default.** The workspace dropdown (top-left, "Default") has *My Layouts (1): Default*, an **Auto Save** toggle, *Shared Layouts (0)*, *+ Create*, and nine Dhan preset layouts (*Dext Home, Watchlist Tracker, Trade on Charts, Expiry / Options Trader, Market Scanner, Scalper Trading, Ladder Watch, Portfolio Tracker, Strategy Builder*). With Auto Save on, **every widget you open or close is written to the account's saved workspace immediately.** During this exploration the extra widgets were opened in Default and then all closed again, and the chart was set back to SENSEX index 1-minute, so Default is as it was (one Chart widget). The research template must be a **separate** workspace made with *+ Create* so Default stays untouched. That creation was the one account write this task asked permission for; the founder said yes on 2026-11-12 and the `E33 desk` workspace now exists (section 7). *My Layouts* now lists **Default** and **E33 desk**.
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

## 7. The research template ("E33 desk") — what was built

**Saved on 2026-11-12 (founder's yes):** workspace dropdown → *+ Create* → name `E33 desk` → *Build Custom Setup*, Auto Save on. Seven widgets, in tab order: Chart ×4, Options Chain, Technicals, Order Flow. Verified by reloading the page twice: the workspace, every widget, each chart's symbol and the added indicators (ADX 14, CHOP 14, MA 20) came back. Nothing else was created (no order, alert or watchlist) and Default was not touched.

**Caveats found while building (updated after the 2026-11-12 evening tune-up):**
- **Chart indicator sets are not durable per chart or per workspace.** Tested on 12 Nov evening with the founder's yes: four chart layouts were saved (`E33 index 5m`, `E33 daily`, `E33 option 5m`, `E33 desk` = option set + ADX + CHOP) and applied to the four charts. Every full reload put **"DEXT layout"** back on all four charts (interval 1D included); the widget keeps only its symbol. Applying a saved layout by hand also overwrites the widget's symbol with the layout's saved one (the PE chart became the CALL), and the chart **autosaves** the currently open layout on any change (the founder's DEXT layout was altered at 18:36 while the daily chart was being edited; it was repaired to SENSEX, VPVR, SuperTrend, VWAP, EMA 21, Volume, OI Profile, HalfTrend, minus the four duplicate OI Profile copies, and is now on 1D instead of 1m). So the one durable place for the E33 indicator set is DEXT layout itself, which is shared with Default. **Done on the founder's second yes (13 Nov 2026, 09:33 IST, market open):** DEXT layout now holds VPVR, SuperTrend 10/3, VWAP, EMA 21, Volume, one OI Profile, Dhan HalfTrend, **ADX 14, Choppiness 14, Dhan Change in Open Interest, Dhan Open Interest**, on **1 minute**, saved explicitly. Verified by reload: all four E33 desk charts load it and keep their own symbols (NIFTY 50 ×2, 25300 CE, 25300 PE); the OI panes are simply empty on the index charts. The four extra layouts (`E33 index 5m`, `E33 daily`, `E33 option 5m`, `E33 desk`) are now redundant and can be deleted from *Open layout* (trash icon) whenever the founder likes; nothing uses them. Remaining differences from the pre-12-Nov DEXT layout: the four duplicate OI Profile copies are gone, and the four new indicators are on. The Default workspace chart shows the same layout.
- A new Chart widget opens as a copy of the *current* chart state, so chart 2 inherited ADX + CHOP from chart 1. Harmless.
- **Chart interval does not persist across reload for the index charts**: the chart set to 1 day came back at 5 minutes (indicators kept). After opening the workspace, set the 20-MA chart to **1 day** by hand (interval button → Days → 1 day), or just read the daily 20-SMA from the Technicals table, which needs no click.
- Order Flow's second pane could not be given focus (its collapsed pane ignores clicks), so Order Flow is a **single pane on the ATM CE**; swap to the PE with the symbol search when needed.
- The chart's own "DEXT layout" was left **unsaved** on purpose (it is the founder's shared chart layout; saving it would push ADX/CHOP/MA onto the Default workspace chart too). The workspace stores the indicator set anyway.

Recipe as built (re-create from this if the workspace is ever lost):

| # | Widget | Instrument / setting | Why (E33 state) |
|---|--------|----------------------|-----------------|
| 1 | Chart (F8) | NIFTY 50 index, **5 minutes**, founder's DEXT-layout indicators (VPVR, SuperTrend, VWAP, EMA 21, Volume, OI Profile, HalfTrend) plus `Average Directional Index` 14 and `Choppiness Index` 14, and (inherited) `MA 20`. Draw PDH / PDL / opening-range lines by hand. | ADX-14, chop, efficiency on 5-minute index bars; candle shape and fair-value gaps by eye. |
| 2 | Chart (F8) | NIFTY 50 index, same indicators; set **1 day** after opening (see caveat). | Prior-day 20-SMA bias vote (the MA 20 line). |
| 3 | Chart (F8) | `NIFTY 17 NOV 25300 CALL`, **5 minutes**, same indicators. | Option candle shape, premium vs spot. |
| 4 | Chart (F8) | `NIFTY 17 NOV 25300 PUT`, **5 minutes**, same. | |
| 5 | Options Chain (Alt+O) | NIFTY, nearest weekly (label "16 Nov 2026" = 17 NOV contracts); default columns Price, Change, Change %, Buildup, Bid, Ask, Volume; add OI / OI Chg via the column chooser. | ATM OI flow vote; max-OI strike level. |
| 6 | Technicals (Alt+T) | NIFTY, SMA, 1 Day. | 20-SMA bias as a number. |
| 7 | Order Flow (Shift+O) | `NIFTY 17 NOV 25300 CALL`, 5 minutes, single pane, Delta display. | Tick-rule signed volume vote. |

Arrangement: all seven are tabs in one region (the "+" at the end of the tab strip adds more). Pop a widget out with the region's "Pop Out" icon to float it beside the others; dragging a tab onto the page does not split the region. ATM strike changes during the day: re-run the symbol search on charts #3/#4 and the Order Flow pane (no auto-roll). For SENSEX days, swap the symbols (SENSEX index, `SENSEX 19 NOV 81900 CALL/PUT`) in place; Auto Save keeps the change.

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

1. **09:00** open the `E33 desk` workspace. Set chart #2 to 1 day, and charts #3/#4 and Order Flow to the strike nearest spot. Note PDH / PDL from the daily chart, read 20-SMA from Technicals.
2. **09:15–09:30** watch the opening range on chart #1; note ADX-14 and chop. Regime call is written down with the numbers, not just "trending".
3. **Every 5 minutes** (bar close): log, by hand or by screenshot, ATM CE and PE **OI Chg** and **Volume** from the chain, and the bar **Delta** from Order Flow. These are the two votes the tape cannot score; the paper log gets a column each.
4. **Levels:** max-OI strike from the chain's OI1 marker; expected-move and support/resistance labels already on the founder's chart.
5. **Never** open the scalper widgets, click a B/S button, or create an alert with "Set an Order". If a ticket opens by accident, close it with its X; no Confirm.
6. **Post-market** copy the hand log next to the tape for that day so the E33 vote scoring can be re-run with real OI/volume instead of `None`.

Verify on the first live session: Depth level count (the *Ladder Watch* preset advertises a 200-level book), the expiry-label off-by-one, and whether the Order Flow footprint streams live for weekly options. Workspace Auto Save does persist chart symbols and indicators (verified by reload); it did not persist the 1-day interval.

---

## 11. Indicator study (2026-11-12 evening): what each tool does, what the data says, what to keep

Paper research only. Two sources: the one-year ATM per-minute cache (`data/cache/expired_opts/{NIFTY,SENSEX}`: CE and PE OHLC, volume, OI, IV, spot; 229 NIFTY days and 248 SENSEX days, 2025-10-27 to 2026-10-27) run through `scripts/lab5y/dext_indicator_study.py`, and a candle-by-candle read of 12 Nov 2026 on DEXT (NIFTY 50 and the 17 NOV 25300 CE / PE). The 12 Nov recorder tape is empty (expired Dhan token), so that day is read from the terminal only.

### 11.1 What the indicators on the founder's chart are

| Indicator | What it computes | Lag | Use in a paper session |
|---|---|---|---|
| VPVR (Volume Profile Visible Range) | Volume at each price over the visible bars; POC and value area | none (recomputed) | Where most business was done; the POC is a level like PDH/PDL |
| SuperTrend 10/3 | ATR(10) band ×3 around hl2; flips when close crosses the band | high | A trailing-stop line, not a signal |
| Dhan HalfTrend 2/2 | Another ATR channel trend-flip line | high | Same job as SuperTrend; redundant |
| VWAP hlc3 session | Session volume-weighted average price | medium | Mean of the day; above/below is the "bias" |
| EMA 21 | Exponential mean of 21 closes | medium | Fast bias line |
| Volume | Bar volume (index "volume" is synthetic) | none | Only meaningful on the option charts |
| Dhan OI Profile | Open interest by strike drawn on the price axis | updates with OI feed | Max-OI strike = the level the E33 state wants |
| Resistance / Support strike, Expected move, Max Pain | Dhan's chain-derived labels | updates with chain | Levels |
| ADX 14 | Wilder trend strength from +DI/−DI | high (≈14 bars warm-up) | E33 regime tag |
| Choppiness Index 14 | log of ATR sum over range; high = range-bound | high | E33 regime tag |
| Dhan Open Interest / Change in OI | OI per candle and % change per candle on an option chart | none | The per-bar OI vote the tape lacks |

ICT tools: there is no fair-value-gap, order-block, liquidity or session indicator in either chart engine (searched "ICT", "imbalance", "smart money", "order block", "fair value", "gap", "session", "high low"); the Premium list (44) is a paid third-party marketplace (Demand & Supply by GTF, Option Selling, …). FVGs are read from three candles by eye or drawn with the rectangle tool; PDH / PDL / opening range are drawn with horizontal lines; the chain's OI1 strike and Max Pain are the only automatic "levels".

### 11.2 What one year of 5-minute bars says (NIFTY first, SENSEX in brackets)

**Option vs index, same strike, no roll.** 5-minute correlation spot↔CE +0.56 (+0.41), spot↔PE −0.63 (−0.45), CE↔PE −0.91 (−0.89). ATM option moves **0.36 pts per index point** on NIFTY (0.24 on SENSEX, read from the tape, both sides). On an up bar the PE loses **1.24×** what the CE gains (SENSEX 1.41×); on a down bar the mirror. CE and PE move the **same** way in 10% (12%) of bars: that is an IV shift, not a spot move, and it does not predict the next 15 minutes. On flat bars (|spot| ≤ 3 pts) the CE bleeds −0.43 and the PE −0.21 per 5 minutes (SENSEX −0.76 / −1.47): roughly 30 NIFTY option points a day of theta and IV decay if nothing happens.

**Direction votes, next-15-minute hit rate (50% = coin).** Close vs EMA21 49.6% (50.3), close vs session average 49.9% (51.1), SuperTrend 49.5% (49.9), candle colour 49.7% (48.6), close vs 20-bar mean 50.1% (50.6). All three trend lines agreeing: 49.5% (50.6); adding ADX > 20: 49.7% (50.6); adding CE signed volume agreeing: 48.9% (51.6); adding CE OI falling on an up bar: 49.8% (51.1). Tick-rule signed option volume alone: 49.9% / 49.5% (51.8 / 51.2). The OI build-up matrix (spot up/down × CE or PE OI up/down) gives −1.0 to +0.6 pts next 15 minutes on every cell against a −0.6 baseline. **No indicator or combination tested moves the next-15-minute coin flip by more than 1.5 points, on either index.** This matches the earlier five-year null result on price rules.

**Regime.** ADX buckets 0-15 up to 35+ all give a next-30-minute absolute move of 25-26 NIFTY points (77-92 SENSEX) and 46-52% continuation of the EMA21 side. CHOP buckets the same. ADX and CHOP describe the last hour; they do not change what the next half hour does. Keep them only because the E33 state logs them.

**Fair value gaps on 5-minute spot.** About 2,000 of each kind per year on NIFTY. Next 15 minutes continue in the gap direction 48% (bullish) / 51% (bearish); **the gap is refilled within an hour 69% / 66%** (SENSEX 76% / 69%). So an FVG is a place price tends to come back to, not a push in the gap direction. Use it as a pull-back target, not an entry trigger.

**Levels.** First touch of PDH / PDL / opening-range high or low in the day: break-through within 15 minutes 48-52% on NIFTY (48-54% SENSEX). A level is where the fight happens, not who wins it.

**Time of day.** Next-15-minute absolute move: 25.7 pts at 09:15-09:45, 20 at 09:45-10:30, 16-17 pts from 10:30 to 13:30, 21 pts after 14:30 (SENSEX 82 / 63 / 51-55 / 65). Flat-bar CE bleed is worst in the first half hour (−0.94 per 5 min on NIFTY). The clock is the strongest "regime" variable in the data.

### 11.3 12 Nov 2026, candle by candle (DEXT, 5 minutes, NIFTY 50 vs 17 NOV 25300 CE / PE)

| Time | NIFTY 50 close | VWAP | EMA21 | ADX | CHOP | 25300 CE | 25300 PE | CE OI | PE OI |
|---|---|---|---|---|---|---|---|---|---|
| 10:00 | 25,366 | 25,314 | 25,286 | 33 | 27 | 250 | – | ≈6.0 M | – |
| 10:15 | 25,353 | 25,320 | 25,301 | 30 | 34 | 242 | – | | |
| 10:30 | 25,340 | 25,322 | 25,310 | 27 | 56 | 231 | 170 | | ≈7.7 M |
| 11:00 | 25,315 | 25,325 | 25,322 | 20 | 56 | 213 | 188 | rising | falling |
| 11:30 | 25,289 | 25,321 | 25,309 | 21 | 48 | 198 | 192 | rising | |
| 12:00 | 25,247 | 25,315 | 25,290 | 24 | 43 | 177 | 212 | rising | |
| 13:00 | 25,260 | 25,300 | 25,258 | 28 | 57 | 174 | 211 | ≈9.9 M (peak) | ≈5.5 M |
| 14:30 | 25,239 | 25,290 | 25,254 | 14 | 61 | 154 | 225 | 9.6 M | 5.4 M |
| 15:15 | 25,275 | 25,285 | 25,259 | 13 | 51 | 176 | 187 | 7.1 M | 4.3 M |

(Times are to the nearest hovered candle; OI from the Dhan Open Interest pane added for the read.)

What the day shows, read against the one-year numbers:
- **10:00 → 12:00, index −119 pts.** CE −73 (0.61 per point, more than the 0.36 average because the strike went from ITM to ATM), PE +42 from 10:30 (0.45 per point). ADX fell from 33 to 20 *during* the clean down-move and CHOP rose from 27 to 56: both regime tags said "trend weakening" while the biggest trend of the day was running. That is the lag in 11.2 in one picture.
- **CE OI rose from ~6 M to ~9.9 M while the index fell, PE OI fell from ~7.7 M to ~5.5 M.** Calls were being written into the fall and puts booked; the chain's "Short Buildup" label on the CE side. In the one-year matrix that cell (spot down, CE OI up) gave +0.0 pts next 15 min, i.e. it describes what happened, not what comes next.
- **12:00 → 14:30, index −8 pts.** CE −23, PE +13: with spot flat the straddle still re-priced, the CE losing the most (ATM theta plus falling IV); that is the flat-bar bleed in 11.2.
- **14:30 → 15:15, index +36 pts.** CE +22 (0.6 per point), **PE −38 (1.07 per point)**: the put lost far more than the call gained as both OI series unwound into the close (CE 9.6 → 7.1 M, PE 5.4 → 4.3 M): short covering plus IV crush. The |PE|/CE asymmetry (1.24 average) was 1.7 on this move.
- VWAP was above price from 11:00 to the close, EMA21 the same; the three trend lines agreed "down" all afternoon and the day closed on a 36-point rally. A trend-line vote would have been on the wrong side of the last move, which is what 49-50% hit rates look like in practice.

### 11.4 Which indicators to keep, remove, add, and why

Keep on the **index chart**: VWAP, EMA 21, one Dhan OI Profile, the Dhan level labels, ADX 14 and CHOP 14 (logged, not traded), hand-drawn PDH / PDL / opening range. Remove: Dhan HalfTrend (duplicates SuperTrend), the four duplicate OI Profile copies; SuperTrend can stay as a trailing line. MA 20 belongs on the daily chart only.

Keep on the **CE and PE charts**: VWAP, EMA 21, Volume, one OI Profile, SuperTrend as the trailing stop. Add **Dhan Open Interest** and **Dhan Change in Open Interest** (per-candle OI and % change: the E33 ATM OI flow vote). Remove ADX and CHOP from the option charts (regime is an index property; on an option chart they measure IV as much as direction) and HalfTrend.

This set now lives in DEXT layout, the layout DEXT reloads onto every chart (section 7): VPVR, SuperTrend 10/3 (trailing line), VWAP, EMA 21, Volume, one Dhan OI Profile, Dhan HalfTrend (kept because it was the founder's; remove by hand for a cleaner view), ADX 14, Choppiness 14, Dhan Change in Open Interest, Dhan Open Interest. Chart interval on reload is 1 minute; switch to 5 / 15 / 30 minutes by hand per chart (interval is not kept per widget).

### 11.4a Parameter sweep (`scripts/lab5y/dext_indicator_sweep.py`, same data)

Lengths and variants, next-15-minute hit rate on 5-minute bars, NIFTY (SENSEX): EMA 9 / 21 / 50 as a side vote 49.3 / 49.6 / 49.7% (48.7 / 50.3 / 51.2); VWAP side 50.0% (51.0); SuperTrend 10/3, 10/2, 7/3, 14/2 all 49.1–49.9% (48.7–49.9); +DI over −DI at 7 / 14 / 21 / 28: 48.8–49.5% (48.9–51.2); RSI 7 / 14 / 21 over 50: 49.1–49.6% (49.1–50.1); RSI 14 below 30 / above 70 as mean reversion 48.9% (49.1); EMA 9 vs EMA 21 cross 49.5% (51.2). Three trend lines agreeing gated by ADX 7 / 14 / 21 / 28 above 15 / 20 / 25 / 30: 49.6–50.4% (50.4–51.4), none above 51.5% and the best cells change between the two halves of the year. **The one repeatable number is negative: 3-bar and 6-bar momentum (chasing the last 15 / 30 minutes) hits 47.7% / 46.4% (47.7 / 47.1)**, and "all three agree after 14:30" hits 46.6% (46.4): the afternoon trend is the thing most often reversed. So the chart tools are at best tie-breaks, and the only consistent rule is *do not chase a move that is already 15–30 minutes old, especially after 14:30*.

CE / PE premium co-movement by bar size (NIFTY, SENSEX in brackets): 1-minute correlation spot↔CE 0.88 (0.73), 5-minute 0.57 (0.42), 15-minute 0.61 (0.45), 30-minute 0.67 (0.39). Option points per index point are 0.48 at 1 minute and 0.35–0.38 at 5–30 minutes on NIFTY (0.40 / 0.24–0.26 on SENSEX): the first minute of a move is paid at nearly the full delta, the rest of the bar gives some of it back. |PE| / CE on an up bar grows with the bar size: 1.02 at 1 minute, 1.24 at 5, 1.57 at 15, 2.07 at 30 (SENSEX 1.02 / 1.41 / 1.94 / 4.21): over a longer rally the put collapses far more than the call gains, because IV falls with the rally. CE and PE moving the same way (an IV shift) happens in 9% of 1-minute bars and 20% of 30-minute bars.

**Confirmation.** Nothing in the data earns the word. The honest reading of 11.2 is: use the index chart for the regime *label* the E33 state needs, the chain and the OI panes for *what is being written where* (levels and bleed), Order Flow for *fills*, and the clock for *how much the next bar can move*. If a confirmation rule is wanted, use the one combination that is at least not negative on both indices: three trend lines agree **and** the CE signed volume agrees (50% NIFTY, 52% SENSEX, +1.5 pts), and treat it as a tie-break, not an edge.

### 11.5 Order flow, chart and depth during a paper trade

- **Before entry (chart):** regime tag from ADX/CHOP, the level in play (PDH/PDL, OR, OI1 strike, VPVR POC), the time bucket (first 30 minutes: biggest moves and worst CE bleed).
- **At entry (Order Flow + Depth):** the footprint shows which side is lifting the offer at the current price; a bar whose Delta sign agrees with the intended direction and a Depth book that is not stacked against it means the fill will be near the quote. A big opposing cluster at the next price is where the limit should sit. This is execution quality, which is the only place the one-year data lets DEXT add value.
- **In the trade (option chart):** the Change-in-OI pane says whether the strike is being written (OI up while premium falls) or covered (OI down while premium rises); SuperTrend on the option is the trailing stop; the flat-bar bleed number sets the patience limit (NIFTY ATM: ~0.4 pts per 5 min doing nothing).
- **Exit:** at the level that was the reason for entry, or when the clock bucket changes, not on an indicator flip.
- **Replay for practice:** Order Flow's *Replay* button says "Bar Replay is not available for this chart type" on the footprint; switch the Order Flow pane to the candle bar type first, then replay. The main Chart widget has no replay. A replay session is the right way to practise the 11.5 routine bar by bar on 1 / 5 / 15 / 30 minutes without an account write; it was not run in this pass (the chart-layout work used the time).


---

## 12. Live observation log 2026-11-13

**Status:** `SOURCE_FACT` read live from DEXT (founder's Chrome, `E33 desk` workspace), 13 Nov 2026 from 09:41 IST. **Paper only: nothing was placed, no Buy/Sell/B/S/alert/scalper control was touched.** Every "trade" below is a paper decision written down at the time, with its outcome read later from the chart.

**Setup changes made today (all reversible view settings):** chart 1 NIFTY 50 at 15 minutes, chart 2 NIFTY 50 at 5 minutes. At 09:44 spot was 25,181, so the option charts and Order Flow were moved off 25300 to the first ITM strikes: **CE chart → `NIFTY 17 NOV 25150 CALL`, PE chart → `NIFTY 17 NOV 25200 PUT`, Order Flow → `NIFTY 17 NOV 25150 CALL`** (5 minutes).

**Levels for the day.** 12 Nov daily candle: O 25,213.50, **PDH 25,384.80, PDL 25,142.95**, PDC 25,299.35. Today 09:15 bar O 25,209.85 H 25,209.85 L 25,107.40 C 25,122.20 (gap −90, first bar −177). 09:20 bar made the day low 25,077.55, below PDL. **Opening range (09:15–09:30): 25,077.55 – 25,209.85.** Daily SMAs (Technicals): 5-SMA 25,123, 10-SMA 24,442, 20-SMA 23,634, so the prior-day 20-SMA bias vote is **bullish** all day. Dhan labels on the daily chart: expected move 24,736 / 25,622, support strike 25,000, resistance strike 25,500, max pain 25,150.

**How the values were read.** Index O/H/L/C by hovering the 5-minute candle; ADX/CHOP from the legend; VWAP/EMA/SuperTrend from the right-axis labels (the price pane is too short for the legend to list them, so lines are identified by shape: black = session VWAP, resets at 09:15; smooth bright red = EMA 21; stepped line with Buy/Sell arrow = SuperTrend 10/3; blue/red dotted channel = HalfTrend). Chain numbers (option price, OI, OI change % vs previous day, PCR, max pain, OI1–OI3 strikes) read from the Options Chain DOM by a read-only page script. Order Flow bar Delta and cumulative delta read from the footprint labels. Caution: hovering over the OI-profile bars on the index chart opens a tooltip with **B / S buttons**; read with the cursor in the ADX pane instead.

### 12a. Observation table (5-minute bars, NIFTY 50)

| Time (bar) | O / H / L / C | VWAP | EMA21 | ADX 5m | CHOP 5m | SuperTrend | 25150 CE | 25200 PE | CE OI (vs prev day) | PE OI (vs prev day) | OF delta / cum Δ (25150 CE) | PCR | Max pain | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 09:35 | 25,155.10 / 25,196.45 / 25,149.45 / 25,172.90 | | | | | down | | | | | +677 K / −397 K | | | biggest CE buy bar of the morning, vol 10.35 M |
| 09:40 | 25,172.60 / 25,186.55 / 25,153.90 / 25,185.60 | 25,143 | 25,213 | 22.2 | 29.2 | down 25,202 | 201.3 (09:47) | 159.0 (09:47) | 48.4 L (+763%) | 80.7 L (+122%) | +48 K / −350 K | 0.90 | 25,150 | rally 25,077 → 25,196 in 25 min |
| 09:45 | 25,187.15 / 25,214.90 / 25,187.00 / 25,208.90 | 25,149 | 25,214 | 20.4 | 30.9 | **flips up** (≈25,159) | 198.0 (09:52) | 161.0 (09:52) | 42.1 L (+651%) | 94.7 L (+161%) | **−240 K** / −704 K | 0.90 | 25,150 | **OR high 25,209.85 poked by 5 pts, close back below**; 25200 CE OI 1.07 cr (OI4) |
| 09:50 | 25,208.95 / 25,211.75 / 25,191.55 / 25,203.70 | 25,150 | 25,212 | 20.4 | 31.1 | up ≈25,164 | 198.3 (1m, 09:55) | 160.0 (1m, 09:55) | 42.4 L (+0.05%/min) | 99.5 L (**+1.54%/min**) | −106 K / −695 K | 0.90 | 25,150 | second bar rejected under OR high; 25200 PE OI climbing fast = put writers under price |
| 09:55 | 25,203.70 / 25,229.40 / 25,199.35 / 25,200.05 | 25,155 | 25,212 | 19.2 | 31.9 | up ≈25,170 | 199.4 (10:00) | 158.8 (10:00) | 39.4 L (+603%) | 66.1 L (+315%) | −19 K / −714 K | 0.90 header, **1.007** from visible-strike OI | 25,150 | **third poke above OR high (25,229) closed back at 25,200**; at the poke 25200 CE OI fell 1.12 → 1.03 cr while 25200 PE OI rose 0.996 → 1.09 cr |
| 10:00 | 25,197.85 / 25,216.90 / 25,188.00 / 25,205.05 | 25,157 | 25,212 | 17.9 | 33.2 | up ≈25,170 | 201.2 (10:05) | 153.4 (10:05) | 37.4 L (+568%) | 69.1 L (+334%) | **−309 K** / −979 K | 1.034 (OI) | 25,150 | fourth failed push at the OR-high zone; 25200 PE OI now OI3 (1.18 cr): put writing right under price; CE OI at 25150 falling (37.4 L from 48.4 L at 09:47) |
| 10:05 | 25,204.10 / 25,223.10 / 25,202.35 / 25,211.00 | 25,160 | 25,211 | 16.7 | 33.2 | up ≈25,174 | 199.1 (10:10) | 155.5 (10:10) | 36.9 L (+559%) | 69.5 L (+336%) | +70 K / −952 K | 1.027 (OI) | 25,150 | fifth push into 25,215-25,230, close at EMA21; 25200 PE now OI2 (1.21 cr); ADX falling every bar (22 → 16.7) |
| 10:10 | 25,211.00 / 25,213.80 / 25,188.90 / 25,202.95 | 25,162 | 25,210 | 15.9 | 34.9 | up ≈25,174 | 201.1 (10:15) | 150.7 (10:15) | 37.1 L (+561%) | 73.9 L (+363%) | −214 K / −1.06 M | 1.042 (OI) | 25,150 | 30-minute box 25,188–25,230 under the OR high; PE OI at 25150/25200 keeps rising every read (put writers), CE OI flat |
| 10:15 | 25,203.40 / 25,216.95 / 25,186.80 / 25,187.70 | 25,164 | 25,209 | 15.0 | 36.9 | up ≈25,174 | 181.1 (10:20) | 166.8 (10:20) | 36.3 L (+548%) | 75.5 L (+374%) | **−370 K** / −1.54 M | 1.061 (OI) | 25,150 | sixth failure at 25,217; bar closes on its low at the box bottom; CE OF delta most negative of the day so far |
| 10:20 | 25,187.65 / 25,205.45 / 25,177.60 / 25,202.20 | 25,165 | 25,208 | 14.4 | **51.5** | up ≈25,174 | 195.6 (10:25) | 155.2 (10:25) | 35.8 L (+538%) | 78.1 L (+390%) | +145 K / −1.38 M | 1.072 (OI) | 25,150 | dip to 25,177.6 bought back (no VWAP touch); CHOP jumps 37 → 51.5: regime now **chop** by both tags (ADX < 15, CHOP > 50) |
| 10:25 | 25,201.95 / 25,207.95 / 25,187.35 / 25,194.60 | 25,166 | 25,206 | 13.8 | 38.5 | up ≈25,175 | 186.2 (10:30) | 160.7 (10:30) | 35.8 L (+538%) | 78.1 L (+390%) | −211 K / −1.60 M | 1.072 (OI) | 25,150 | box continues; 25150 CE + 25200 PE "straddle" 346.9 vs 359.3 at 09:47 with spot 16 pts lower |
| 10:30 | 25,194.30 / ≈25,229.8 / 25,192.75 / ≈25,228 | 25,167 | 25,208 | 12.6 | 46.9 | up ≈25,174 | 210.5 (10:35) | 143.5 (10:34) | 34.7 L (+519%) | 76.0 L (+377%) | **+411 K** / −1.19 M | 1.081 (OI) | 25,150 | full-bodied bull bar to the box top (25,229.4); 25200 CE OI 1.16 → 1.12 cr (call writers covering) |
| 10:35 | 25,228.75 / 25,229.75 / 25,202.35 / 25,207.70 | 25,168 | 25,209 | 12.6 | 49.3 | up ≈25,174 | 201.95 open of 10:40 | 145.3 (10:40) | 34.8 L (+521%) | 75.6 L (+374%) | −94 K / −1.28 M | 1.059 (OI) | 25,150 | **seventh failure at the box top**: the +411 K bar was fully reversed in one bar; 25200 CE OI back up 1.12 → 1.17 cr (writers returned) |
| 10:40 | 25,207.10 / 25,229.55 / 25,207.10 / 25,229.45 | 25,171 | 25,213 | 12.4 | 50+ | up ≈25,190 | 204.6 (10:40) → 220.3 (10:47) | 145.3 → 134.2 | 34.3 L → 32.4 L | 75.4 L → 73.2 L | **−46 K** / −1.33 M | 1.06 | 25,150 | rally bar back to the box top on **negative** CE delta |
| 10:45 | 25,229.40 / 25,245.40 / 25,228.75 / 25,242.40 | 25,173 | 25,216 | 12.1 | 52.7 | up ≈25,201 | 217.9 (10:50) | 135.7 (10:50) | 32.0 L (+470%) | 73.7 L (+363%) | +66 K / −1.26 M | 1.049 (OI) | 25,150 | **first 5m close above the 60-minute box** (8th test). 15m chart: ADX 18.1, CHOP 41.2. 25250 CE OI 75.3 L (+140%) = new writing one strike up |
| 10:50 | 25,241.00 / 25,243.80 / 25,220.40 / 25,224.70 | 25,174 | 25,216 | 11.8 | **63.0** | up ≈25,201 | 206.4 (10:55); 25200 CE 178.8 | 144.0 | 31.7 L (+466%) | 73.9 L (+364%) | −92 K / −1.36 M | 1.060 (OI) | 25,150 | breakout bar fully reversed; back inside the box; CHOP 63 = deepest chop reading of the day |
| 10:55 | 25,224.25 / 25,227.55 / 25,199.40 / 25,199.65 | 25,175 | 25,214 | 11.7 | 60+ | up | 197.4 (10:58) | 150.0 (10:58) | 31.8 L | 73.7 L | −139 K | | | |
| 11:00 | 25,200.15 / 25,203.70 / 25,185.05 / 25,189.10 | 25,176 | 25,209 | 11.3 | 62.8 | up ≈25,154 (HalfTrend flips **down**) | 180.3 (11:05) | 163.2 (11:05) | 33.7 L | 76.1 L | −219 K | | | back at box bottom |
| 11:05 | 25,189.35 / 25,192.05 / 25,167.65 / 25,188.80 | 25,176 | 25,204 | 11.9 | 57.0 | up ≈25,154 | 178.8 (11:10) | 160.4 (11:10) | **36.6 L (+552%)** | 81.0 L (+408%) | −123 K / −1.76 M | 1.025 (OI) | 25,150 | **VWAP touch** (low 25,167.65 vs VWAP 25,176) and close back at 25,188.8; on the touch 25150 CE went 180 → ≈172 → 178.8, 25200 PE 163 → ≈167 → 160.4. CE OI rising again (writers sell into the dip), 25200 PE OI 1.47 → 1.42 cr (put writers trim) |

*(Observation stopped at 11:12 IST at the founder's request.)*

### 12b. Paper decisions so far (nothing placed)

| # | Time | Instrument @ entry | Why | Stop / target | +15 min | +30 min / exit | Opposite option |
|---|---|---|---|---|---|---|---|
| D0 (tempted, skipped) | 09:47 | 25150 CE @ 201.30 (spot 25,210.8) | break of OR high after a 27-min-old rally from 25,077 | — (no-chase rule) | CE 197.60 (−3.7), spot −3 | CE 193.35 (−7.95), spot −2.6 | PE 159.0 → 156.75 (−2.25): both legs lost |
| D1 | 09:52 | 25200 PE @ 161.00 (spot 25,207.25) | failed OR-high break; CE delta −240 K; 25200 CE OI rising. Votes 4 yes / 3 no (VWAP side, SuperTrend flip up, daily 20-SMA against). Regime: ADX 20, CHOP 31 | 5m close > 25,215 / VWAP 25,149 | PE 148.40 (−12.6), spot +15 against | **closed at 30 min: PE 157.90 (−3.1)** with spot 11.5 pts *in favour* | CE 198.0 → 191.65 (−6.35) |
| D2 | 10:35 | 25150 CE @ 210.45 (spot ≈25,228) | full bull bar to the box top, CE delta +411 K, CE OI covering; 7/7 votes yes, regime tag chop (ADX 12.6, CHOP 47) | 5m close < 25,208 / 25,255–25,260 | reversed in 90 s (CE 195.30) | **stopped at 10:40 open, CE 201.95 (−8.5)**; if held: +7.4 at 10:50, −30.15 at 11:05 | PE 143.50 → 145.30 (+1.8) |
| D3 | 10:50 | 25200 CE @ 189.10 (first ITM; spot 25,242.65) | first 5m close above the 60-min box; delta weak (+66 K after −46 K); 25250 CE fresh writing | 5m close < 25,228 / 25,280 | — | **stopped at 10:55, CE 178.75 (−10.35)**; if held: −34.35 at 11:05 | 25250 PE 159.05 → 168.60 (+9.55) |
| S1 (skipped) | 11:10 | 25150 CE ref 178.80 (spot 25,187.7) | VWAP touch (low 25,167.65) and bounce; skipped because regime is chop (ADX 11.9, CHOP 57) | — | not read (paused) | not read | PE 160.35 ref |

Running paper result: D1 −3.1, D2 −8.5, D3 −10.35 = **−21.95 option points** on three trades; the two stops saved ≈ 46 points against holding to 11:05.

### 12c. Pattern candidates and verifier verdicts (batch 1 sent 10:23; verdicts from the Fable 5.1 parent session received after the pause)

1. **P1 — inside a stalled box a bought ITM option bleeds on both sides.** 25150 CE + 25200 PE fell ≈ 359 → 347 between 09:47 and 10:30 with spot within ±20; D1 lost with the index moving its way. Verdict: **SPLIT.** Mechanics confirmed: the extra bleed (≈1.6 pts per 5 min, 2.5× the one-year flat-bar average) comes from the post-gap IV crush (90-pt gap, ATM IV +7.8%), not from the box itself. The ADX gate is rejected (in the one-year data ADX below 20 does not change the next 30 minutes). Rule as reworded: after a gap open with high IV, measure the straddle bleed live (pts per 5 min) and buy only if spot can be expected to move at least bleed ÷ delta points per 15 min.
2. **P2 — the opening-range high after a 25-minute gap-fill rally acted as a lid.** Seven 5m pokes above 25,209.85 failed to hold (09:45–10:35); the one close above (10:45) reversed next bar. Verdict: **WEAK.** One day only; a first touch of the OR high breaks within 15 min 52% of the time (coin), and footprint delta scored 49.9% in the one-year data. Keep it as a note ("OR high held with negative delta on 13 Nov"), not a rule. The part with support: the rally was 25+ min old at the OR high, and chasing a 15–30-min-old move hits 46–48%. *That* is the reason to skip.
3. **P3 — the chain header PCR (0.90) and ATM IV (15.87) did not change for 30+ minutes;** PCR from summed strike OI moved 1.007 → 1.081. Verdict: **CONFIRM (operational).** The header is on a slow or stuck refresh: use PCR from summed strike OI, and check spot against the chart legend each time (the chain's spot row repeated 25,208.00 at 10:00 and 10:02). Next session: press the chain's refresh icon once and see whether the header catches up.
4. Not yet sent: **breakout entries in chop (CHOP > 45, ADX < 15) failed twice within 5 minutes; the footprint delta on the break bar was weak or negative.**
5. Logged as is (verifier): chain said "support building" (puts stacked under price) while the footprint said "calls being sold"; in the one-year OI matrix neither predicts the next 15 min, and sideways was the outcome.

### 12d. What the indicator combinations did and did not confirm (09:41–11:12)

- **ADX / CHOP (regime tags):** described the last hour correctly (trend 09:20–09:45, chop from 10:15), but every regime change showed up after the price had already changed. The verifier rejected "ADX < 20 = no trade" as a rule (no effect in one year of data); keep the tags as labels only.
- **VWAP / EMA 21 / SuperTrend / HalfTrend:** SuperTrend flipped up at 09:45, right at the top of the move; it stayed "up" through the whole 80-min box and both failed breakouts. VWAP was the one line price reacted to (11:05 touch at 25,167.65, close back at 25,188.8). The trend lines never disagreed with the 20-SMA daily "bullish" bias, and that agreement gave no edge: D2 had 7/7 votes yes and lost.
- **Footprint delta (25150 CE, 5m):** the sign matched the *next* bar's direction only loosely. The +411 K bar at 10:30 was reversed in one bar; the rally bar at 10:40 had −46 K. The one-year number (49.9%) held up today.
- **Chain OI:** put writers stacked under price all morning (25200 PE 0.81 → 1.47 cr) while 25150 CE OI fell then rose again. The chain said "support"; the footprint said "calls sold"; the index went sideways. Neither confirmed a direction.
- **Fair value gaps:** no clean 3-candle gap formed on 5m spot after 09:35 (bars overlapped all morning). None logged.
- **Levels touched:** OR high 25,209.85 (seven tests, one close above, reversed); PDL 25,142.95 reclaimed at 09:30 and not revisited; VWAP once (11:05); max-OI strikes 25,000 (PE OI1) and 25,500 / 26,000 (CE) never approached; PDH 25,384.80 far away.
- **What did confirm:** the no-chase rule (D0 −7.95 at 30 min), and fixed index stops on 5-minute closes (D2 and D3 lost 8.5 and 10.35 instead of about 30 and 34 if held to 11:05).

### 12e. Which charts were used for which decision

| Decision | Index 15m | Index 5m | Option 1m | Order Flow 5m | Chain | Technicals |
|---|---|---|---|---|---|---|
| Levels (PDH/PDL, OR) | daily candle (chart 1 at 1D for one read) | OR from the 09:15–09:25 bars | — | — | max pain, OI1–OI3 | 20-SMA bias |
| D0 skip | — | rally age, OR high | — | — | CE/PE prices | — |
| D1 PE | — | rejection bar, VWAP/EMA/ST, ADX/CHOP | per-minute OI change % (PE OI +1.54%/min) | delta −240 K / −106 K | 25200 CE OI, prices | bias (against) |
| D2 CE | — | box-top bar, stop on 5m close | — | delta +411 K | CE OI covering | bias |
| D3 CE | ADX 18 / CHOP 41 | first close above box, stop | — | delta −46 K / +66 K | 25250 CE writing, prices | bias |
| S1 skip | — | VWAP touch | — | delta −123 K | CE writing again | — |

The 15m chart was read once for regime; the 5m chart and the chain did almost all the work; the 1-minute option charts were used once, for per-bar OI change; Technicals only for the daily 20-SMA vote. **Practical note:** hovering the index chart over the OI-profile bars opens a tooltip with B / S buttons, so read with the cursor in the ADX pane.

**End of session:** charts 1 and 2 set back to 1 minute. The CE/PE charts and Order Flow were left on 25150 CE / 25200 PE (the first ITM strikes today) rather than 25300.

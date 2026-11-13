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
- **Chart indicator sets are not durable per chart or per workspace.** Tested on 12 Nov evening with the founder's yes: four chart layouts were saved (`E33 index 5m`, `E33 daily`, `E33 option 5m`, `E33 desk` = option set + ADX + CHOP) and applied to the four charts. Every full reload put **"DEXT layout"** back on all four charts (interval 1D included); the widget keeps only its symbol. Applying a saved layout by hand also overwrites the widget's symbol with the layout's saved one (the PE chart became the CALL), and the chart **autosaves** the currently open layout on any change (the founder's DEXT layout was altered at 18:36 while the daily chart was being edited; it was repaired to SENSEX, VPVR, SuperTrend, VWAP, EMA 21, Volume, OI Profile, HalfTrend, minus the four duplicate OI Profile copies, and is now on 1D instead of 1m). So the one durable place for the E33 indicator set is DEXT layout itself, which is shared with Default. Decision for the founder: either put ADX 14, CHOP 14, Dhan Open Interest and Dhan Change in OI into DEXT layout (every chart on every workspace shows them; the OI panes are empty on an index chart), or keep the four extra layouts and re-apply `E33 desk` by hand after each reload, then re-enter the CE / PE symbols. The four extra layouts exist and can be deleted from *Open layout* if unwanted.
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

These edits were made on 12 Nov and saved as chart layouts, and DEXT still reloads "DEXT layout" onto every chart (section 7 caveat). The set that should live in whichever layout DEXT reloads: VPVR, SuperTrend 10/3 (trailing line), VWAP, EMA 21, Volume, one Dhan OI Profile, ADX 14, Choppiness 14, Dhan Open Interest, Dhan Change in Open Interest. Drop Dhan HalfTrend and the duplicate OI Profiles.

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


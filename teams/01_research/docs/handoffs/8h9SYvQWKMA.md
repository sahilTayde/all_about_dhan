# SOURCE_FACT — 8h9SYvQWKMA (Dhan Charts walkthrough)

**Status:** `EXTRACTED` (layer A). Product education. `DRAFT`.  
**Not** an entry/exit strategy. Useful as **tooling** facts for index-option desks (chain-on-chart, ATM CE/PE scalper, OI indicator).

| Field | Value |
|-------|--------|
| video_id | `8h9SYvQWKMA` |
| title | The New Dhan Charts Every Trader Should Try \| Complete Walkthrough |
| url | https://www.youtube.com/watch?v=8h9SYvQWKMA |
| retrieved_at | 2026-09-01T19:55:35Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/8h9SYvQWKMA.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | none on file (still treat names/awards as marketing) |
| relevance | HIGH / OPTIONS (catalog) |

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim | type |
|----------|-----------|-------|------|
| CH-C01 | 01:12–02:00 | Deep TradingView integration (`tv.dhan.co` spoken as tv.com). Awards: Most Reliable Tech 2022; Best Broker Asia Pacific 2023; Best Broker for Options Trading 2024. | marketing |
| CH-C02 | 02:21–02:32 | Charting experience claimed free (no subscription) with a funded account. | product |
| CH-C03 | 02:34–03:13 | **Seconds** TF; India-session **25 / 75 / 275** minutes; custom TF (example **113** minutes). | product |
| CH-C04 | 03:16–04:12 | “More than 120” indicators; no indicator/template/layout cap. Custom names: Bama, Implied Volatility, Wave Trend with Crosses, Squeeze Momentum, Zurich Moving Average, Boring Candle, Explosive Candle, Chainer Exit, Smart Tronco Engine. **No parameters spoken.** Spellings `[UNCERTAIN]` | product |
| CH-C05 | 04:23–04:49 | Multi-screen up to **eight** charts. Called “particularly powerful for options”: underlying + call + put simultaneously. | product |
| CH-C06 | 04:57–05:30 | Types: candlestick, Renko, Kagi, Heikin-Ashi, Point & Figure. Anchored VWAP free (paid on TV by default). Fib / Gann / Elliott named. | product |
| CH-C07 | 05:33–08:32 | Trade on charts: buy/sell; limit, market, Super Order; instant placement (no confirm); drag-and-drop modify; TP/SL on pending + positions; Super Order = entry+target+SL in one ticket. Trade plan: risk, reward, % capital → generated plan. | product |
| CH-C08 | 08:55–10:00 | Scalper floating window (qty + buy/sell = market). Can reflect **index** view via **options**. Power Scalper tab: index/underlying + call chart + put chart. | product |
| CH-C09 | 10:00–10:49 | First-time (claimed) options on TradingView canvas. Right-click → **option chain on the option chart**: price, volume, OI, **all Greeks**; trade from there. | product / chain |
| CH-C10 | 10:52–11:17 | OI as a **chart indicator**; current + historical trail; buildup / unwind / covering vs price. | product |
| CH-C11 | 11:19–11:47 | CPR (Central Pivot Range) named for Indian swing. **Basket orders on charts** for multi-leg. | product |
| CH-C12 | 11:53–12:20 | Pine Script alert → Dhan **webhook** URL + JSON → order in Dhan account. Details “in description.” `VERIFY BEFORE IMPLEMENTATION`. **Not** a research strategy. | product |
| CH-C13 | 12:24–13:11 | Market Replay to practice on historical days (example: volatile 2024 day). | product |
| CH-C14 | 13:15–13:45 | DOM: 5-level book; settings unlock **full** depth for **NSE and MCX**. | product |
| CH-C15 | 14:08–14:29 | Alerts free “up to certain levels” (price or indicator); phone + popup. | product |
| CH-C16 | 14:48–16:19 | Mobile: stocks, futures, **options**, commodity. Scalper: underlying + **ATM Call** + **ATM Put**; scan ATM by OI or volume. Drag TP/SL. | product |
| CH-C17 | 16:22–16:56 | App / Options Trader / Charts / Web **sync** (positions, orders, baskets, watchlists, margins). Dex T3 mentioned as newer terminal. | product |
| CH-C18 | 17:23–17:28 | Statutory: investments subject to market risk. | disclaimer |

---

## What is NOT in the transcript

No strike-selection rule, no expiry weekday, no MACD/RSI params, no NIFTY/BANKNIFTY/SENSEX setup, no win rate.

Seconds / 25m / 75m / 275m are **product TFs**. HQ charts enum in official docs is 1/5/15/25/60 — **3m and seconds are not REST annexure facts from this video.** Leave `VALIDATION` to 02.

---

## Handoff

**02/07 later:** do not invent REST fields from this walkthrough. Webhook auto-orders are out of Phase-1 research.  
**04:** no new STRAT. ATM CE/PE scalper tabs are **UI**, not a tested ATM-only rule (other videos contradict ATM).

# OPTIONS_INDEX_PACKET — English SOURCE_FACT (index options)

**Coalition slice:** `OPTIONS_INDEX`  
**Team:** 01_research  
**Date:** 2026-09-03  
**Layer:** `SOURCE_FACT` only. Do **not** merge with `VALIDATION` (02/03) or `HYPOTHESIS` (04_quant).  
**Status:** `EXTRACTED` / `DRAFT` / `WAITING_FOR_EDIT`. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Transcripts:** `data/transcripts/normalized_en/<video_id>.md` (`tlang=en`, `youtube_translate`). Prefer these over Hindi ASR. Hindi `SOURCE_FACT` files were **not** overwritten.  
**QA:** YouTube English is still a translation of Hindi speech. Numbers remain high-risk. Flagged `[UNCERTAIN_TRANSCRIPT]` / `SOURCE_UNCERTAIN`. **No invented quotes. No algos. No win rates.**

Education ≠ edge. Spoken “70% / 7% / 3% / 93%” figures are **claims in a video**, not backtests.

---

## Scope of this packet

**In:** NIFTY / BANKNIFTY / SENSEX **index options**, CE/PE buy, option chain, expiry, Greeks-as-spoken, selling/hedge corpus (Phase-1 is still **buy-first**), order-flow overlay, Dhan charts features that name options.

**Out (equity agent / other slices):** `STOCK_ONLY` scanners, BTST, swing-stock masterclasses, same-stock intraday, music/brand, LOW app-setup. Listed in §Skip.

---

## Video index (English on disk)

| video_id | title (catalog) | role | English file | Per-video |
|----------|-----------------|------|--------------|-----------|
| `HAUSZx-hYdY` | Ultimate 1-Hour Masterclass on Option **Buying** | **PRIORITY** buy + chain + Greeks | `normalized_en/HAUSZx-hYdY.md` | [`HAUSZx-hYdY.en.md`](HAUSZx-hYdY.en.md); Hindi kept [`HAUSZx-hYdY.md`](HAUSZx-hYdY.md) |
| `_exmJYgFwFA` | FREE 1-Hour Masterclass on Option **Selling** | **PRIORITY** sell + OI + hedge intro | `normalized_en/_exmJYgFwFA.md` | [`_exmJYgFwFA.md`](_exmJYgFwFA.md) |
| `DzT_681GThA` | A to Z Order Flow Trading Guide | **PRIORITY** OF overlay (demo = Reliance) | `normalized_en/DzT_681GThA.md` | [`DzT_681GThA.md`](DzT_681GThA.md) |
| `8h9SYvQWKMA` | The New Dhan Charts Every Trader Should Try | **PRIORITY** product / chain-on-chart | `normalized_en/8h9SYvQWKMA.md` | [`8h9SYvQWKMA.md`](8h9SYvQWKMA.md) |
| `2RnBT9DDDNI` | FREE Option Buying Masterclass | Index OB; futures VWAP+ST; ITM/ATM | `normalized_en/2RnBT9DDDNI.md` | Hindi [`2RnBT9DDDNI.md`](2RnBT9DDDNI.md); English delta below |
| `6el9Jqnrdz8` | Hedge Like a Pro (option **selling**) | 1-3-2 call ratio; NIFTY Tue expiry **dated** | `normalized_en/6el9Jqnrdz8.md` | Hindi [`6el9Jqnrdz8.md`](6el9Jqnrdz8.md); English delta below |
| `gA5FtEnSABM` | Option strategy in 15 mins (bear / swing) | RSI divergence → **bull put** example; buy if intraday | `normalized_en/gA5FtEnSABM.md` | Hindi [`gA5FtEnSABM.md`](gA5FtEnSABM.md); English delta below |
| `pvmvkiS1cx4` | 2-Minute Scalping | NIFTY / BANKNIFTY / SENSEX; ITM CE/PE | `normalized_en/pvmvkiS1cx4.md` | Hindi [`pvmvkiS1cx4.md`](pvmvkiS1cx4.md); English delta below |
| `YUXJv_xBStw` | Order Flow on DEXT T3 | Product OF; NIFTY May futures demo | `normalized_en/YUXJv_xBStw.md` | Hindi [`YUXJv_xBStw.md`](YUXJv_xBStw.md) |
| `6WZxLShiUT8` | Pick Best Options (42s promo) | Chain UI: Greeks + order panel. **No rules.** | `normalized_en/6WZxLShiUT8.md` | this packet |

**Catalog tags (not title-guess):** HAUSZx `OPTIONS|OPTION_CHAIN|VOLATILITY|GREEKS`; `_exm` `OPTIONS|GREEKS`; DzT `VOLUME|GREEKS|STRATEGY_DESIGN` (Greeks tag is **misleading** — video delta is **volume delta**); 8h9 `OPTIONS`.

---

## Layer C — HYPOTHESIS pointers for 04 (all `UNVALIDATED`)

Do **not** treat as Dhan-proven. Existing DRAFT IDs in `MASTER_STRATEGY_PLAN.md` already map some of these. This packet does **not** add STRAT-015+.

| Spoken cluster | Existing DRAFT ID (if any) | Status |
|----------------|----------------------------|--------|
| Dual-TF MACD × MA stack, slightly OTM buy, 10:00–14:30 | STRAT-001 / 002 / 007 | `HYPOTHESIS` / `UNVALIDATED` |
| 3m futures VWAP+VWMA20+ST(10,3); ITM/ATM; mixed-index avoid | STRAT-003 / 005 / 008 / 009 | `UNVALIDATED` |
| 2m EMA10/20, ITM 100–200 pts / ~0.55–0.60 delta | STRAT-006 | `UNVALIDATED`; speaker also said beginners should **not** buy-scalp |
| OF volume-delta / POC / stacked imbalance confirm | STRAT-010 | overlay; HQ history likely `DATA_INSUFFICIENT` |
| RSI divergence → Supertrend; **intraday buy** vs swing **sell** | STRAT-011 (transfer) | `UNVALIDATED` |
| Bull put credit (gA5); 1-3-2 call ratio Mon 09:45 (6el9); `_exm` OTM call sell + cheap long hedge | STRAT-013 / 014 | **WAITING** sell; Phase-1 is CE/PE **buy first** |

**No win rates.** Spoken 70/30, 93/7, “less than 1/3 buyer”, 3% capital, 7–8% in five weeks are **SOURCE_FACT anecdotes**, not expectancy.

---

## A. `HAUSZx-hYdY` — option buying (English)

Full claim table: [`HAUSZx-hYdY.en.md`](HAUSZx-hYdY.en.md). Hindi ASR file kept.

**Guests:** Host + Himanshu Arora. Examples educational; NIFTY/stock names are examples (~09:18).

| claim_id | timestamp | SOURCE_FACT (paraphrase of English) | type |
|----------|-----------|--------------------------------------|------|
| HAUS-EN-01 | 00:07–00:14 | Buyer profit can be unlimited, loss limited; seller loss unlimited, profit limited. Game is premium appreciation. | education |
| HAUS-EN-02 | 01:41–01:45 | Host: move from “93% bracket” to “7% bracket.” **Not sourced in-video.** `[UNCERTAIN_TRANSCRIPT]` | statistic |
| HAUS-EN-03 | 00:44–00:51 | No 99% / “holy grail” strategy. | education |
| HAUS-EN-04 | 08:31–08:48 | Bullish → buy call (right to buy); bearish → buy put (right to sell). | education |
| HAUS-EN-05 | 09:29–13:14 | Hypothetical NIFTY ₹25,000; strike = deal price; **NSE decides strikes**; NIFTY strikes in **multiples of 50** (cannot pick 24,970). | contract education |
| HAUS-EN-06 | 10:51–12:04 | Screen: NIFTY ~24827; chain opened; 24600 call premium × lot. **Ephemeral.** `[UNCERTAIN_TRANSCRIPT]` | example |
| HAUS-EN-07 | 15:35–16:42 | NIFTY ETF / cash shares have **no** expiry; options do. Spoken NIFTY expiries: **19 Jun (that day)**, next **Thursday**, then 26 Jun / 3 Jul / 10 Jul / 17 Jul. Weekly + month-end “large” monthly. Speaker notes NSE/SEBI changing expiries. **Do not freeze calendar.** | dated market |
| HAUS-EN-08 | 16:57–18:20 | Buyer can exit before expiry if premium rises (₹100 → 120 spoken). Need predefined buy / stop / target. | education |
| HAUS-EN-09 | 20:05–22:33 | Premium ≈ intrinsic + time value. Longer expiry (31 Jul vs 26 Jun) → same intrinsic, more time value. | education |
| HAUS-EN-10 | 23:22–25:00 | ITM / OTM / ATM (“around the money”) defined vs spot. | education |
| HAUS-EN-11 | 30:42–31:28 | **Delta** = rate of change of premium vs underlying. Spoken 24500 call delta and ATM ~0.52. `[UNCERTAIN_TRANSCRIPT]` decimals | education |
| HAUS-EN-12 | 33:50–35:20 | **Theta** = premium vs time (long option generally decays). **IV** = implied volatility (events make options expensive). | education |
| HAUS-EN-13 | 36:50–38:29 | Buyer needs direction **and** speed; theta not linear, steeper near expiry. If long option not profitable in ~**three/four days**, chance later is “very low” (speaker). | opinion |
| HAUS-EN-14 | 42:30–42:31 | Dual TF: **hourly** parent + **5 or 10 minute** child. | rule-as-spoken |
| HAUS-EN-15 | 45:07–47:40 | Uses **MACD**; “increases the MACD parameters”; plus MA **10, 30, 100**. Recap also says 10 above 30 **and 300** (~59:26). **9 vs 10** MA on exit (~56:24–56:48, 01:02:15). `[UNCERTAIN_TRANSCRIPT]` | indicator |
| HAUS-EN-16 | 55:18–55:42, 01:00:22–01:00:35 | New entries mostly **after 10:00**; mostly **not after 14:30** (spoken “2:30”); **not after 15:00**. Best personal window ~11:00–13:00. 14:45 vs 15:00 messy. `[UNCERTAIN_TRANSCRIPT]` | session |
| HAUS-EN-17 | 57:26–01:01:05 | Speaker buys **slightly OTM**; ATM called most overvalued. Adverse-case ~**40 delta** spoken. Target ~**20–30%** option value. Conviction “equals your delta” (personal). | strike / exit |
| HAUS-EN-18 | 01:00:41–01:00:54 | Speaker does not overnight; strategy “not purely intraday”; BTST possible if chosen **before** entry. | carry |
| HAUS-EN-19 | 43:14–44:12 | Universe spoken: **NIFTY 100** liquid stocks; ~230 names have options but not all liquid; check bid-ask. **Not index-only.** | universe |

**VALIDATION (leave for 02/03):** delta/theta/IV/OI math; NIFTY strike step 50; expiry weekday **as of recording vs now**; MACD 4× params; 9 vs 10 vs 100 vs 300 MA.

---

## B. `_exmJYgFwFA` — option selling (English) — NEW

Full file: [`_exmJYgFwFA.md`](_exmJYgFwFA.md). Sequel to HAUSZx. Same guest family (Himanshu Arora). **Selling + hedge.** Phase-1 product is CE/PE **buy first** — keep as corpus; do not silently convert into a buy strategy.

| claim_id | timestamp | SOURCE_FACT | type |
|----------|-----------|-------------|------|
| EXM-C01 | 04:12–05:32 | Buyer makes money when underlying moves **enough** his way. Seller can make money if up a little, flat, or down (call-seller toy). Buyer “less than 1/3” of cases; seller “more than two thirds.” Later: buyer win probability **not more than 1/3**; “less than 30%”; “less than 3/10.” `[UNCERTAIN_TRANSCRIPT]` | education / opinion |
| EXM-C02 | 07:17–08:06 | Profitability-chaser → **buy**; probability-chaser → **sell**. Seller wants 2 of 3 market directions (up / down / sideways). | education |
| EXM-C03 | 08:31–09:47 | Seller: “Nifty will not go above this level” → sell that **call**. Wants premium → 0 (OTM expiry). Profit **capped** at premium received; loss **unlimited**. | education |
| EXM-C04 | 10:55–11:13 | Elections / budget: selling “very painful.” IV is buyer’s friend, seller’s enemy. | education |
| EXM-C05 | 13:40–14:28 | **Theta** is seller’s “biggest friend.” Same-day expiry demo: OTM LTP ~5–10 paise → treated as ~0. | education + screen |
| EXM-C06 | 15:23–17:30 | Buyer max loss ≈ premium (₹100 × lot 75 → ₹7500 spoken). Seller needs **VAR / “war” margin** (exchange, vol-based, “99% of days”). Screen margins 9672 vs 5535 vs 124793 — **messy / dated.** `[UNCERTAIN_TRANSCRIPT]` | example |
| EXM-C07 | 19:45–21:00 | Do not buy a call **only because** you cannot afford to sell the put. Match product to conviction: high conviction → buy CE/PE; low conviction “won’t crash” → put **sell**. Host cites 93% again. | opinion |
| EXM-C08 | 21:01–21:22 | “Huge margin required” is a myth if you **hedge**; margin can fall to ~1/4 or “50–60,000 / under 50,000.” `[UNCERTAIN_TRANSCRIPT]` | hedge |
| EXM-C09 | 29:21–33:37 | Chain analysis **assumption**: institutions smarter / more capital. Highest **OI** + **rising OI** on a strike ≈ level they do not expect to be breached (call OI = resistance; put OI = support). Screen NIFTY ~24790; 25000 / 25500 / 26000 / 23500 / 24000 OI numbers. **Snapshot only.** Israel–Iran / Fed / tariffs dated. `[UNCERTAIN_TRANSCRIPT]` | OI heuristic |
| EXM-C10 | 36:30–36:54 | Theta decay **not linear**; steeper near expiry (“exponential”). | education |
| EXM-C11 | 39:21–40:37 | Naked: unlimited risk. Speaker: **7 of 10** selling trades in **calls**, **3 in puts** (black-swan / crash asymmetry). If naked, call sell “relatively better” than put sell. If hedged, either. **Not a win rate.** | opinion |
| EXM-C12 | 42:39–46:04 | **Stock** example (Eternal/Zomato, Bajaj Auto) — not index-only. Williams **%R** (default 14; speaker “increases the parameter” — “140” spoken `[UNCERTAIN_TRANSCRIPT]`). Extreme bands −5 / −95 (also −20 / −80). Then MA **10, 30, 100**; later “below 30 and below **300**.” Hourly. Sell **call ~5%** from recent swing high. Target **3% of capital deployed** (explicitly **not** a return promise). | rule-as-spoken (stocks) |
| EXM-C13 | 48:01–50:30 | Bajaj Auto ~8500; sell ~9000 call (~5% OTM) next-month if near expiry (Mon/Tue margin). Naked margin ~93k vs hedged ~52k; max loss defined ~32k. Makes money down / flat / modest up. **Stock F&O example.** `[UNCERTAIN_TRANSCRIPT]` rupees | example |
| EXM-C14 | 53:48–54:56 | Hedge = buy a **cheaper** option than the one sold (caps loss). Names iron condor, bull/bear call/put spreads. Full hedge catalog **deferred** (asks comments for “hedging”). | education |
| EXM-C15 | 52:52–53:00 | Index cannot be traded “normally”; use **futures or options**. | education |

**HYPOTHESIS (04, `UNVALIDATED`):** transfer the OI max-pain / highest-OI wall and “sell ~5% OTM call + cheap long hedge” from **stocks** to NIFTY/BANKNIFTY/SENSEX. Video does **not** claim that transfer.

---

## C. `DzT_681GThA` — order flow A–Z (English) — NEW

Full file: [`DzT_681GThA.md`](DzT_681GThA.md). DEXT T3 product + four “rules.” **Demo underlying is Reliance**, not NIFTY options. Speaker says the same OF fields apply to “stock **or index**.”

**This “delta” is buy-volume minus sell-volume. It is not option Greek delta.**

| claim_id | timestamp | SOURCE_FACT | type |
|----------|-----------|-------------|------|
| OF-C01 | 00:05–00:47 | Order flow launched on Dex; this video is A–Z how to use Dex T3 OF (widgets → Order Flow). | product |
| OF-C02 | 01:35–02:29 | Per candle: left = **executed** sell volume; right = executed buy. **Not** bid/ask book. Delta = total buy − total sell. | definition |
| OF-C03 | 03:01–03:55 | **Cumulative delta** = sum of candle deltas through the day; sentiment (buyers vs sellers aggressive). Newly added on Dex T3. | product |
| OF-C04 | 04:25–06:37 | Volume = buy+sell. **POC** = price with highest **buy+sell** volume in that candle. | definition |
| OF-C05 | 07:59–08:44 | **VAH / VAL**: band with **70%** of that candle’s volume. POC expected inside. | definition |
| OF-C06 | 08:48–11:50 | **Imbalance** default: buy vol ≥ **3×** previous price’s sell vol (or sell ≥ 3× previous buy). Stacked imbalances can “validate” a chart breakout. | heuristic |
| OF-C07 | 12:21–12:51 | Settings: imbalance ratio user-set (demo 3 → 10 → 20). Higher ratio = fewer highlights. | product |
| OF-C08 | 13:17–14:00 | **Absorption:** red candle can still be buyer-dominated (positive delta). Next candle told the story. | education |
| OF-C09 | 14:04–14:12 | **VWAP** (“VIP” / “VP” in EN): volume-weighted average through the day. **On a traded name, not cash-index volume.** | product |
| OF-C10 | 15:05–16:50 | Top-down: daily S/R → 15m → 5m (also peeked 3m) for intraday/scalp **on Reliance**. | method |
| OF-C11 | 18:20–18:25 | Indian session 09:15–15:30 → **75** five-minute candles. Demo: 11 of 75 had negative delta. `[UNCERTAIN_TRANSCRIPT]` count | education |
| OF-C12 | 18:35–19:27 | Price down + aggressive buys = **bearish absorption** (passive limit sellers) **or** bullish divergence (delta higher-low vs price lower-low). **Context required.** | education |
| OF-C13 | 19:29–20:07 | Four rules: (1) price↑ delta↑ = strong bull; (2) price↓ delta↓ = strong bear; (3) price↑ delta↓ = bearish divergence / buyer absorption; (4) price↓ delta↑ = bullish divergence / seller absorption. “One cannot trade simply using just order flow and just technical analysis.” | rule-as-spoken |

**No CE/PE, strike, expiry, or option-premium rule in this video.** Overlay-only. HQ OF **history** likely `DATA_INSUFFICIENT` (see MASTER_STRATEGY_PLAN STRAT-010).

---

## D. `8h9SYvQWKMA` — Dhan Charts walkthrough (English) — NEW

Full file: [`8h9SYvQWKMA.md`](8h9SYvQWKMA.md). **Product education. No entry/stop/target.**

| claim_id | timestamp | SOURCE_FACT | type |
|----------|-----------|-------------|------|
| CH-C01 | 01:12–02:00 | Charts partnered with TradingView (`tv.dhan.co` spoken as tv.com). Awards claimed: Most Reliable Tech 2022; Best Broker APAC 2023; Best Broker for Options 2024. | product / marketing |
| CH-C02 | 02:34–03:13 | **Seconds** timeframe; India session TFs **25 / 75 / 275** minutes; custom TF (example 113 minutes). | product |
| CH-C03 | 03:16–04:07 | “More than 120” indicators; unlimited indicators/templates/layouts. Custom names spoken: Bama, Implied Volatility, Wave Trend with Crosses, Squeeze Momentum, Zurich MA, Boring/Explosive Candle, Chainer Exit, Smart Tronco Engine. **Names only — no params.** `[UNCERTAIN_TRANSCRIPT]` spellings | product |
| CH-C04 | 04:23–04:49 | Up to **eight** charts; “particularly powerful for options”: underlying + call + put on one screen. | product |
| CH-C05 | 04:57–05:19 | Chart types: candles, Renko, Kagi, Heikin-Ashi, P&F. Anchored VWAP free for Dhan users (paid on TradingView default). | product |
| CH-C06 | 06:16–08:32 | Trade on charts: limit/market/Super Order; instant click; drag-and-drop modify; TP/SL on pending + positions; Super Order = entry+target+SL in one. | product |
| CH-C07 | 09:34–10:00 | Scalper can express **index** view via **options**. Power Scalper: index/underlying + call chart + put chart. | product |
| CH-C08 | 10:00–10:49 | Right-click → **option chain on the option chart**: price, volume, **OI**, **Greeks**; place trades there. | product / chain |
| CH-C09 | 10:52–11:17 | **OI as a chart indicator**; current + historical trail; buildup / unwind / covering vs price. | product |
| CH-C10 | 11:19–11:47 | CPR named for swing. **Basket orders on charts** for multi-leg options. | product |
| CH-C11 | 11:53–12:17 | Pine Script alert → Dhan **webhook** + JSON → order. Details “in description.” `VERIFY BEFORE IMPLEMENTATION`. | product / API-adjacent |
| CH-C12 | 13:15–13:45 | DOM: 5-level book; full depth in settings for **NSE and MCX**. | product |
| CH-C13 | 15:36–16:00 | Mobile scalper: underlying + **ATM call** + **ATM put** tabs; scan ATM by OI or volume. | product |
| CH-C14 | 16:22–16:56 | App / Options Trader / Charts / Web sync. Dex T3 mentioned as newer terminal. | product |

---

## E. English deltas on earlier Hindi packets (do not overwrite Hindi files)

### `2RnBT9DDDNI` — index option **buying** (English confirms)

Guest: Dr. Gokul (surname ASR). **Index only**, not stock options this video (~22:13–22:16).

| field | English as spoken | ts |
|-------|-------------------|-----|
| Chart | **Index futures** (NIFTY June example), **3 minute** | 21:59, 20:15 |
| Ignore | **09:15–09:45** completely; start after 09:45 | 23:48–23:59 |
| Flat | All positions **before 15:15** (“3:15”); intraday; no overnight/BTST | 23:59–24:06 |
| VWAP | Default; color only | 21:40–21:46 |
| VWMA | **length 20** | 21:50–21:52 |
| Supertrend | “default … setting of **103**” — treat as **10, 3** with `[UNCERTAIN_TRANSCRIPT]` | 21:53–21:57 |
| Put buy | Price **below** VWAP **and** VWMA **and** Supertrend | 25:13–25:53 |
| Call buy | Price **above** all three | 25:58–26:07 |
| Sideways | Supertrend vs VWAP disagree → no-trade zone; “70% non-trading / 30% trading” `[UNCERTAIN]` | 24:26–24:30, 34:54+ |
| Strike | From **spot** at signal, not futures. **ITM, maximum ATM. OTM not recommended.** “Two in the money” / ATM+1 ITM | 38:06–39:20 |
| Delta | Host asks range. Guest analogizes RSI 50–75 → **60 to 75**; then “063 to 74”; puts = **minus**. Deep >0.74 “not that much logic.” `[UNCERTAIN_TRANSCRIPT]` | 01:02:42–01:03:50 |
| Mixed indices | NIFTY buy + BANKNIFTY sell → **avoid that day** or trade only **dominant** index — **not both** | 01:08:37–01:09:14 |
| Priority | (1) NIFTY (2) BANKNIFTY (3) SENSEX (4) Midcap; FinNifty/Bankex mainly expiry week; BANKNIFTY “hotspot” 1.5–2y ago, now NIFTY and Sensex. **Dated.** | 01:04:28–01:05:02 |
| Spot volume | NIFTY spot volume is **not** “how much NIFTY traded.” Analyse futures (true volume); pick strike from spot; trade **premium**. | 17:59–20:21 |

Lot-size rupee toys in Hindi file stay `[UNCERTAIN]`. **Never freeze lot 65.**

### `6el9Jqnrdz8` — hedged **selling** (English confirms)

Phase-1 = buy-first. Corpus only.

| field | English as spoken | ts |
|-------|-------------------|-----|
| Underlying | **NIFTY** | 41:29–41:31 |
| Horizon | Hold ~4–5 days; “positional”; Mon entry → next **Tuesday** expiry; speaker labels **bi-weekly** “because of that one day” | 41:31–41:54 |
| Expiry weekday | NIFTY expiry spoken as **Tuesday**. **VERIFY — SEBI weekly-expiry regime changed.** | 41:42 |
| Entry | **Monday 09:45**; rule-based; no chart discretion | 42:26–42:37 |
| Target / stop | **1%** target and **1%** stop; RR 1; “no adjustments” | 42:38–42:51 |
| Structure | Spot 26000 example: buy **1** lot 26200 call (200 pts OTM); sell **3** lots 26400; buy **2** lots 26600 hedge → **1-3-2** / “1:3 call ratio” then hedge. Execute as **basket**. | 43:00–44:16 |
| BANKNIFTY | Weekly expiry “removed in November 2020”; BANKNIFTY monthly — **dated; re-verify.** | 59:11 (Hindi file SELL-C09; EN same week) |

Spoken “success rate higher than 50%” (~42:52) is **not** a backtest. Do not copy as a win rate.

### `gA5FtEnSABM` — thought process (English confirms)

NIFTY **2-hour** chart. Swing → **will not buy** options (target 3–4 days; theta). If **intraday**, speaker **would buy**. This video **executes a sell** (market closed / swing) (~03:03–03:43).

- Falling market: skip MA; Supertrend optional for reversal; **first** RSI **divergence** (~03:56–04:18). Spoken “28°” RSI gap `[UNCERTAIN]`. Also Heikin-Ashi (~04:54).
- Bullish if taking a trade; stop a bit below marked bottom (~05:12–05:30).
- OT Web → **NSE Index → NIFTY** → pre-built **bullish** → skip same-day expiry (23 Jan); use **30 Jan** (~1 week) because **budget next week** — does not want to be a **seller** into budget (~07:30–08:01).
- Picks **bull put spread**; margin spoken **17,567**; ~1% NIFTY up → ~5.5–6% on margin; max loss “around 15” `[UNCERTAIN]` (~08:57–10:00).
- Horizon: positional → cash/futures **not** options; swing/intraday → options; **intraday or 1–2 days → option buying**; **few days → prefer selling** unless a huge stock move (~13:29–13:46).
- TF: swing 1h or 2h; intraday 15m / 5m / 10m (~13:50–13:57).

**HYPOTHESIS `UNVALIDATED`:** same RSI-divergence **view**, then **buy** CE/PE for Phase-1. That mapping is **not** the executed example.

### `pvmvkiS1cx4` — 2-minute scalp (English)

Mukul Choudhary. **Nifty 50, Sensex, Bank Nifty.** Analysis on **spot** (easier backtest); **execution on options** (~00:46–01:03).

| field | English |
|-------|---------|
| Strike | **ITM only** — not ATM, not OTM, not deep ITM. **100–200 points** ITM on all three. Delta spoken “**555 to 6**” then later **0.55** `[UNCERTAIN_TRANSCRIPT]` (~01:03–01:32, 17:15) |
| TF | **2 minutes** for this system; 3m/5m allowed; do not use 2m until confident on 5m |
| Indicators | **EMA 10 and EMA 20** only (not SMA, not DEMA) |
| Beginners | **Should not scalp by buying options**; sell-side scalp OK (~13:10–13:17) — **conflicts** with ITM buy description; keep both |

### `YUXJv_xBStw` — OF intro (already extracted)

English agrees with Hindi packet: footprint buy/sell, volume delta ≠ Greek, POC, VAH/VAL **70%** (can 50), imbalance default **3×**, VWAP on **futures**. Demo NIFTY May futures. **No strike/CE/PE rule.**

### `6WZxLShiUT8` — 42s promo

Advanced option chain on Dhan: realtime, **Greeks**, order panel. “Index is moving / thinking of buying a lot.” **No strategy.**

---

## Data requirements (later engine — not from videos)

```text
DATA_SOURCE: DhanHQ / exchange (later)
INSTRUMENT: NIFTY, BANKNIFTY, SENSEX index options CE/PE (project); speaker universes also include NIFTY-100 stocks
EXCHANGE_SEGMENT: NSE (NIFTY/BANKNIFTY); BSE (SENSEX)
CALCULATION: indicators on futures or spot as spoken; never cash-index volume as “NIFTY volume”
TIMEFRAME: as spoken per video (1h/5m, 3m, 2m, 2h)
EXPIRY / LOT: FROM_CONTRACT / instrument master — never freeze Tue NIFTY, lot 65/75/30
```

Order-flow history on HQ: `DATA_INSUFFICIENT` until proven otherwise.

---

## Skip for THIS packet (equity / other slices)

Do **not** treat as Phase-1 index-option evidence. English files exist; **equity agent owns STOCK / scanner / BTST / swing-stock.**

| id | why skipped here |
|----|------------------|
| `4TT8IV5S1_A` | Buy-the-dip **screener** |
| `_byuht38r5s` | Intraday **screener** |
| `pBQ1oVDVe3M` | Breakout **stock screener** |
| `G31RFueZLvk` | **BTST** masterclass (catalog OPTIONS tag is metadata, not this slice) |
| `dEvF8biE02M` | Swing multi-year **stock** breakout |
| `MfGUybW4O4c` `O8h44rgJ84k` `kJ5HZKzpZqQ` `ZoCD4fLKy6M` `OZRfSMg4qUY` `IvSnlbt89yw` `2YBmiyVmNNw` | scanners / same-stocks / BTST / swing compound |
| `EVk_Wa_1cm0` | 93s “old strategy” clip — not an options spec |
| `eApl0SfVBBY` `mPKASwm6Oqk` `pUg_7sPauQA` `6E_K1wVkHyw` `H_6keeRUCDM` `PUkzVgVPCf0` `njqeZc_tYy8` `wpdqqXhhq88` `wDZXqzdGBDc` | transferable TA / indicators / candles — not this OPTIONS_INDEX extract |
| `JhHkEIUznVw` `UaHdow8V8Eg` `WmJttDnvCKM` `Wmpi-BXclXw` `T9eo_YxAr9U` `PLQtDASa064` `ZPAYPwPaJzo` `dYva2rO1LOw` `eJ_gAffsLoc` `s7rxvdWTlHQ` `vxpl3yTdrZQ` `lNSmwmlUI54` `qSgKA0-T7Uw` | promo / music / LOW / tool-only |

See also [`TRANSFERABLE_AND_SKIPPED.md`](TRANSFERABLE_AND_SKIPPED.md). That file’s old line “`_exmJYgFwFA` TRANSCRIPT_PENDING — no claims” is **stale**; English + SOURCE_FACT now exist.

---

## What 02 / 03 / 04 must do

**02_phd_math (`VALIDATION` only):** delta (Greek) vs volume-delta; theta non-linearity; IV; OI; VAR/SPAN margin as spoken vs NSE; Williams %R 14 vs “140”; MACD 4×; Supertrend “103”; EMA 10/20; VWAP/VWMA on **futures**.

**03_phd_market:** NIFTY strike step 50; expiry weekdays **now** (do not freeze Tuesday NIFTY / Thursday Sensex / BANKNIFTY monthly); lot sizes from master; VWAP-on-index pitfall; option-buy vs sell; liquidity / 50-multiple NIFTY strikes.

**04_quant:** may attach `UNVALIDATED` HYPOTHESIS to existing STRAT-001–014 only. **No new IDs. No fake win rates. No algos from this packet.**

**Must not:** collapse layers; use STOCK scanners as index-option evidence; LLM-translate; hardcode lots/expiry; implement live signals.

---

## Blockers / UNKNOWN

- English is `youtube_translate` of Hindi — numbers still `[UNCERTAIN_TRANSCRIPT]`.
- MACD exact 4× of 12/26/9; MA 9 vs 10 vs 100 vs 300; Williams 140; Supertrend “103”; pvmvki “555 to 6” delta: `UNKNOWN` / `SOURCE_UNCERTAIN`.
- Expiry calendars in HAUSZx / 6el9 / gA5 / `_exm` are **recording-dated**.
- DzT / YUXJv OF history on DhanHQ: `DATA_INSUFFICIENT`.
- Pine webhook auto-order (`8h9`): `VERIFY BEFORE IMPLEMENTATION` — not a strategy.

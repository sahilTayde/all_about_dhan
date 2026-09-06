# SOURCE_FACT — equity / ETF / stock-options packet

**From:** `teams/01_research`  
**To:** `teams/04_quant` (this packet only) · **not** Phase-1 index-options construction  
**Date:** 2026-09-03 (second pass: remaining newly-verified English IDs)  
**Status:** `EXTRACTED` / `DRAFT` / `WAITING_FOR_EDIT`  
**Layer:** **A `SOURCE_FACT` only.** No `VALIDATION`. No coded algo. **No returns claimed.**  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. Do **not** merge into NIFTY / BANKNIFTY / SENSEX Phase-1 STRAT-001–014.

**Per-video claim tables (this pass):** [`_byuht38r5s.md`](_byuht38r5s.md) · [`4TT8IV5S1_A.md`](4TT8IV5S1_A.md) · [`pBQ1oVDVe3M.md`](pBQ1oVDVe3M.md) · [`G31RFueZLvk.md`](G31RFueZLvk.md) · [`dEvF8biE02M.md`](dEvF8biE02M.md) · [`EVk_Wa_1cm0.md`](EVk_Wa_1cm0.md) (Darvas **product** only). TA-owned EN files `eApl0SfVBBY` / `mPKASwm6Oqk` / `pUg_7sPauQA` stay in [`TA_STRUCTURE_PACKET.md`](TA_STRUCTURE_PACKET.md).

This file is a **separate research packet**. Catalog rows tagged `STOCK_ONLY` / `EXCLUDED_STOCK_ONLY` stay in `data/youtube/video_catalog.json` — **do not delete**. They are extracted here so they do not contaminate index-options Phase-1.

Education ≠ advice. Spoken examples and ScanX filter lists are **not** a backtested screen. [`docs/COMPLIANCE.md`](../../../../docs/COMPLIANCE.md).

---

## Firewall (read first)

| This packet | Phase-1 (other agents) |
|-------------|------------------------|
| Cash **equities**, **ETFs**, **single-stock options**, stock **futures** (catalog titles), ScanX **product** UI | NIFTY / BANKNIFTY / SENSEX **index options** |
| Tags: `EQUITY` · `ETF` · `STOCK_OPTION` | Index-only videos **skipped** below |
| Quant IDs: `EQ-*` / `ETF-*` / `SO-*` in [`EQUITY_ETF_BACKLOG.md`](../../../04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md) | `STRAT-001`–`014` stay index-only |

**Index-only / TA English transcripts — skip (other agents):** `HAUSZx-hYdY`, `2RnBT9DDDNI`, `6el9Jqnrdz8`, `gA5FtEnSABM`, `_exmJYgFwFA`, `pvmvkiS1cx4`, `YUXJv_xBStw`, `DzT_681GThA`, `6WZxLShiUT8`, `6E_K1wVkHyw`, `mPKASwm6Oqk`, `pUg_7sPauQA`, `wpdqqXhhq88`, `eApl0SfVBBY`, `8h9SYvQWKMA`, `qSgKA0-T7Uw`, `lNSmwmlUI54`, `wDZXqzdGBDc`. Product/brand/music/Diwali/app-setup also skipped. `EVk_Wa_1cm0` is **this packet** as a product clip only (no EQ slot).

Algo playlists (`Advanced Algo Trading 2026`, `Advanced Algo Trading Series`, `Algo Trading with Python`, `Introduction to Algorithmic Trading`) are **out of this packet** (no algos).

---

## Provenance

| Field | Value |
|-------|--------|
| Channel | `@DhanHQ` / Dhan ⚡ · `UCEzHCpvFWoF85UabbzKTkOQ` |
| Catalog | `data/youtube/video_catalog.json` retrieved **2026-08-31T03:15:28Z** · **2034** videos |
| English transcripts | `data/transcripts/normalized_en/<video_id>.md` · YouTube `tlang=en` unless noted · `qa_flags: UNCERTAIN_TRANSCRIPT` on auto-translate |
| Catalog tags | `STOCK_ONLY` **9** kept · `EXCLUDED_STOCK_ONLY` **50** kept · **0** of those 59 have English companions on disk |

Numbers, RSI bands, market-cap crores, and “unusual volume” tokens from Hindi ASR + YouTube English are `[UNCERTAIN_TRANSCRIPT]`. Do not silently “correct.”

---

## ScanX / stock scanners = Dhan **product**, not a backtested screen

**SOURCE_FACT of product class (Tier 2), not of edge:**

- Playlists: **How To Use Scanx \| FREE Screener Included** (`PLnuHyqUCoJsMOYV34i9_GTBxphFDJohql`, 15 items in catalog header / 14 videos enumerated) and **Use ScanX for Trading** (`PLnuHyqUCoJsMM4iyws8LpHcPvX3x2ewZu`, 8 videos).
- Titles name ScanX as a **screener / heatmap / live-feed UI** (e.g. `ugmYfiTpUsc` “Introducing ScanX”; `wCXyqT4BSFw` “ScanX is Now 100% FREE \| 200+ Stock Screeners”; `gQXaA2dPBa8` “Options Trading Strategy with ScanX Screener!”). **No English transcript on disk** for those IDs — title/playlist only.
- English videos below that **demo filters on ScanX** (`O8h44rgJ84k`, `kJ5HZKzpZqQ`, `MfGUybW4O4c`, `IvSnlbt89yw`, `_byuht38r5s`, `pBQ1oVDVe3M`, `4TT8IV5S1_A`) are **spoken walkthroughs of a Dhan product**. Sharing a ScanX link or comment-code is **not** an OOS backtest, not HQ Conditional Trigger REST, and not a production screen.
- Official HQ: no scanner REST on dhanhq.co/docs/v2. Supertrend / RSI screeners are chart-or-ScanX. See [`DHAN_OFFICIAL_INDICATORS.md`](../DHAN_OFFICIAL_INDICATORS.md) and [`DHAN_ECOSYSTEM.md`](../DHAN_ECOSYSTEM.md) (`scanx.trade` = `TIER_2_SECONDARY`).

Do **not** treat ScanX “Intraday Supertrend” / RSI 75/25 support copy as annexure fields. Do **not** live-trade `/alerts/orders`.

---

## Catalog inventory — `STOCK_ONLY` (kept, 9)

All **DISCOVERED**. Language metadata `en-IN`. **No** `normalized_en/` file. Claims below are **title + playlist + topic_tags only** — not spoken transcript.

| video_id | published | dur (s) | title (catalog) | playlist | packet tag | topic_tags |
|----------|-----------|---------|-----------------|----------|------------|------------|
| `H_-8Nzlb5dY` | 2025-12-06 | 4843 | The Ultimate Stock Options FREE Masterclass \| Unlock Pro-Level Strategies | FREE Masterclasses | `STOCK_OPTION` | OPTIONS, RISK_MANAGEMENT |
| `v1yVgvGiFxs` | 2025-03-22 | 455 | Myths About Stock Options (Debunked) \| Episode 1 \| Stock Options Trading Series | Stock Options Trading Series | `STOCK_OPTION` | OPTIONS |
| `8fkOYPwhllE` | 2025-03-26 | 722 | Intrinsic Value vs. Time Value Explained \| Episode 2 | same | `STOCK_OPTION` | OPTIONS, VOLATILITY |
| `lPwGiE1d0FU` | 2025-03-30 | 730 | Option Greeks: Delta Explained \| Episode 3 | same | `STOCK_OPTION` | OPTIONS, GREEKS, RISK_MANAGEMENT |
| `33YfPdy7ZFM` | 2025-04-03 | 862 | Option Chain Interpretation \| Episode 4 | same | `STOCK_OPTION` | OPTIONS, OPTION_CHAIN, VOLUME |
| `bq3wZ_soUJ8` | 2025-04-10 | 1373 | Options Hedging \| Episode 5 | same | `STOCK_OPTION` | OPTIONS, RISK_MANAGEMENT |
| `TygHRM6XYho` | 2025-04-13 | 780 | Bear Put Spread STRATEGY \| Episode 6 | same | `STOCK_OPTION` | OPTIONS, RISK_MANAGEMENT, STRATEGY_DESIGN |
| `tPRs6gqErAE` | 2025-10-19 | 600 | Strategy for Muhurat Trading: How to Make the Most of 1 Hour | (none named) | `EQUITY` | RISK_MANAGEMENT, STRATEGY_DESIGN |
| `r3VdWESNSy8` | 2025-05-01 | 25 | From ₹350 to Penny Stock: Can You Guess This Stock? | (none) | `EQUITY` (trivia) | — |

**Same playlist, not `STOCK_ONLY` on the row** (still `STOCK_OPTION` for this packet; catalog titles only):

| video_id | title | episode |
|----------|--------|---------|
| `V-AviEo32IY` | Covered Call Strategy | 7 |
| `S2lBSN0ak9M` | Covered Put Strategy | 8 |
| `Xxy7xpvbXHE` | Backtesting for Options Traders | 9 |
| `8b6EazctsIQ` | Risk Management for Options Traders | 10 |

Playlist id: `PLnuHyqUCoJsOMo_zyEPYTHRHlALuVg5eR` (**Stock Options Trading Series**, 10 videos). Additional title hits **not** on that playlist, still catalog-only: `CRzuVqisVo4` / `gApsIjlswDI` (intraday stock-options parts 1–2), `JOafo3S1xKs` (How to Trade Stock Options Like a Pro), `-4cOh1JbpQc` (Switch to Stock Options from Index Options After Regulation Change). **No English transcript.** Do not invent spoken rules.

---

## Catalog inventory — `EXCLUDED_STOCK_ONLY` (kept, 50)

**Do not delete.** Phase-1 already parks these as exclusive stock / long-term / MF / product. This packet **lists** them; it does **not** promote them into index STRATs.

**`ETF` (title) among excluded:** `Cl7C8bTcl6U` / `IV4wr1cqAdA` (US stocks & ETFs walkthrough; Hindi), `fFhiw6DQTQk` (Introducing US stocks & ETFs), `oxlW6BGQn2k` (ETFs for portfolio building & pledging), `dU76pTcZx1w` (SIP in stocks & ETF), `V5KuCqwou3s` (podcast: MFs, ETFs). **No English transcript.**

**`EQUITY` product / investing (excluded; not a screen):** US-stock app, sector MF inflows (`wvGPxuJouho`), gold timing, SOA vs demat MF, CAS-on-MF-units, news-in-app, fundamental masterclass, group watchlist, demat MF transfer, tech+fundamental swing, passive-income, SafeKeep, step-up SIP, MF pledging, UPI AutoPay, AMC lists, weekly SIP, Dhan Wrapped, SIP Plus+, fundamentals on Dhan, stock SIP, MF vs bonds, forex beginners (`y2RVCCGNKO0` — **not** NSE cash), MF intro/roundtable, monopoly stocks, AMC CIO talks, Reliance large-cap analysis, etc. Full 50 ids remain on the catalog `stock_tag` field.

---

## Playlists used as **catalog** evidence (titles only)

| playlist_id | catalog title | packet use |
|-------------|----------------|------------|
| `PLnuHyqUCoJsOMo_zyEPYTHRHlALuVg5eR` | Stock Options Trading Series | `STOCK_OPTION` series map |
| `PLnuHyqUCoJsOGfQZoHUy56MdTu2LcOK9k` | Swing Trading Series (10) | `EQUITY` swing curriculum; **DISCOVERED**, no EN transcript |
| `PLnuHyqUCoJsMOYV34i9_GTBxphFDJohql` | How To Use Scanx \| FREE Screener Included | ScanX **product** |
| `PLnuHyqUCoJsMM4iyws8LpHcPvX3x2ewZu` | Use ScanX for Trading | ScanX **product** |
| `PLnuHyqUCoJsPm-9uQnRs_SeqF8Cwk-E_a` | Mutual Funds on Dhan | investing product; excluded flavour |
| `PLnuHyqUCoJsPWD7wlpPmIsaC9-K8Z99v3` | FREE Masterclasses | mixed; stock-options masterclass sits here |

**Swing Trading Series (catalog titles, `EQUITY`, DISCOVERED):** Ep1 `ZGrMAHz8jXM` Introduction; Ep2 `egVzq7jWw90` Tools; Ep3 `BvhUn6W8AmI` How To Pick Stocks For Swing Trading; Ep4 `wgxKLYU2guc` Candlestick; Ep5 `ROWRA_q4I7A` Technical Indicator; Ep6 `KkdwpWRfYhg` Trend Following; Ep7 `R88PATQ13ZI` Breakout; Ep8 `49ID12EyfRw` Compression + Bollinger; Ep9 `3BuE2En66I8` Risk/Psychology; Ep10 `J2dnS8SrYTk` Blueprint.

**`ETF` titles not excluded (still no EN transcript):** `vQfWtqHTVJE` ETF Trading Strategy Explained; `TzvPlqfRpts` How to Trade Silver ETFs; `1Hy8sT94J6Q` All New ETF Experience; `mhdlO4eAyhI` ETF Investing on Dhan; `tUl9Zc1KLKo` ETFs to get pledge margin; `BDI1i5UHST8` Stocks, ETFs, and MTF; `TJLGmAAPgis` / `8erNHsLtc_w` US stocks and ETFs (Hindi). **Spoken claims: `DATA_INSUFFICIENT` until transcript.**

**Stock futures (catalog titles, `EQUITY`):** `qRNkN7eKNHI` / `dMPdRjiWx-8` Pair Trading Strategy for Stock Futures parts 1–2. No EN transcript.

---

## English transcripts — `EQUITY` (SOURCE_FACT)

All paths: `data/transcripts/normalized_en/<id>.md`. Translation: YouTube English companion (`source_language: hi` unless noted). Speakers are Dhan-hosted educators, **not** a proven desk.

### MfGUybW4O4c — 9:45 AM “Intraday Alpha” scanner · `EQUITY`

- url: https://www.youtube.com/watch?v=MfGUybW4O4c · published 2026-06-22 · ENGLISH_VERIFIED 2026-09-01
- Speaker (spoken): Dr. Priyanka; stock-market mentor / full-time trader (~01:07–01:11).
- Problem framed: hardest intraday task is **selecting the right stocks**; strategy without the “right” stock “will not make much profit” (~00:05–00:25). **Opinion / education, not a test result.**
- “Right” buy-side = strongest gainers that day; sell-side = weakest (~00:28–00:45).
- Volume must support the move; negative price–volume correlation → move “will not sustain” / “dry up” (~01:46–02:24).
- Filter spoken: volume **more than 1 million / ₹10 lakh** shares (~02:43–03:09). `[UNCERTAIN_TRANSCRIPT]` “Rs 10 lakh” vs “1 million shares.”
- Run **this** screener at **9:45 am**, not the same screener at 9:00 / 9:30 / 10:00 (~03:24–03:54). Market open spoken **9:15**; 9:45 = ~30 minutes after open (~03:58–04:03). First 15–30 minutes = high volatility / “noise” (~04:22–05:40); newcomers told to skip first **15 minutes** (~05:45–05:47).
- Name spoken: **Intraday Alpha Screener** (~06:14–06:16). Buy-side scanner (~07:42–07:47).
- Market cap **> ₹5000 crore** (below that framed as small-cap liquidity / wide bid–ask) (~07:19–07:28).
- Price **above 20 EMA** (also spoken 20 SMA as S/R) (~07:53–08:37). Speaker: above 20 EMA does **not** mean profit every day (~09:03–09:12). Nifty 50 daily used as **illustration** of 20 EMA, not as the trade universe (~09:19–09:30).
- Price **≥ Supertrend** (~10:28–10:44). Supertrend period/multiplier **not spoken** in this extract → `UNKNOWN`.
- Last filter: price % change at run time; speaker wants names **up 0.50% to 1.5%** among the 9:45 list (~12:05–12:12). `[UNCERTAIN_TRANSCRIPT]`
- Nifty 5m candle of “the 26th” high/low **23965 / 2402** (~04:38–05:01) — **screen-day snapshot**; `[UNCERTAIN_TRANSCRIPT]`.

### O8h44rgJ84k — “Intraday Momentum Blast” on ScanX · `EQUITY`

- url: https://www.youtube.com/watch?v=O8h44rgJ84k · 2026-08-28
- Product: filters added on **Scan** (spoken “scan” / “skinner”) (~01:54–02:38, 06:48). **Product UI, not a backtest.**
- Shortlist: fast **bullish** stocks **above open**, possibly near day high, **at least a few percent** intraday (~00:40–00:59). Seven-to-eight conditions (~01:06–01:09). Named: RSI “around overbought,” MACD positive, volume, Parabolic SAR, Supertrend for trail (~01:20–01:36).
- Clock: let market settle ~10–15 min / ~half hour; run ~**after 10:00**, “around **9:45**” (~02:44–02:55). **Conflict 9:45 vs 10:00;** `[UNCERTAIN_TRANSCRIPT]`. Recap: run ~10:00 or ~9:45 (~06:11–06:13).
- Spoken filters as built: **price > open** (~02:58–03:04); **today’s % change > 1%** (~03:14–03:20); **RSI > 60** (~03:33–03:38); **MACD > 0** (~03:59–04:09); **one-day unusual volume** (~04:17–04:25); **price > Supertrend** (~04:27–04:36). Supertrend params `UNKNOWN`.
- Liquidity: market cap **at least above “₹0000 crores”** then speaker practices **₹50,000 crore**; save as **₹50,000 crore**; if more names wanted change **only** market cap to **₹20,000 crore**; **do not change other parameters** (~04:53–05:16, 07:15–07:31). `[UNCERTAIN_TRANSCRIPT]` on the first crore figure.
- Optional confirmation: Dhan **OT web** futures **build-up / OI** (example DLF July future) (~03:52–03:55, 06:18–07:06). Spoken illustrative move “around 1.25 to 1.5%” (~07:06–07:08) — **anecdote, not a backtest.**
- Chart-day names (HAL, DLF) are **examples**, not recommendations (~05:21–06:04).
- Save name: **Intraday momentum blast / IMB**; comment to request ScanX share (~07:35–07:45). Paper-trade days/weeks; **one stock at a time** (~08:01–08:09).
- Disclaimer end: securities market risk (~08:21–08:27).

### kJ5HZKzpZqQ — IMB / “Momentum Blaster” variant · `EQUITY`

- url: https://www.youtube.com/watch?v=kJ5HZKzpZqQ · 2026-05-22
- Same family: **IMB Intraday Momentum Blaster** (~00:49–00:51). Live screeners on Dhan (~00:17). Usable morning **or after noon before 3:00 pm** (~00:33–00:39). Run regularly **from 10:00 am** (~02:20–02:22).
- Market cap: “no requirement” but speaker selected **> ₹10,000 crore**; later “define” **> ₹10,000** or **₹5,000–₹20,000** (~01:30–01:55, 07:39–07:48).
- Filters: **price > open** (~02:31–02:46); **one-day unusual volume** (~03:16–03:25); **RSI > 60** with spoken “90% chance uptrend” (~03:50–04:07) — **heuristic, not a measured rate**; `[UNCERTAIN_TRANSCRIPT]`; **MACD histogram** (alt: MACD line > signal) (~04:14–04:21); **5 EMA > 20 EMA** and **20 EMA > 100 EMA** (~04:44–05:06) `[UNCERTAIN_TRANSCRIPT]`.
- EMA/MACD later also spoken on **daily** and **5-minute** (~08:08–08:34) — dual-TF wording messy; `[UNCERTAIN_TRANSCRIPT]`.
- Spoken expectancy: “anything above **0.6%** after brokerage and ST”; **partial** at 0.6% (~06:48–07:05). **Not a backtest.** Chart-day % moves (Adani Ports, Solar, etc.) are **that day’s tape**, not a track record (~05:36–05:51).

### IvSnlbt89yw — BTST at ~3:15 · `EQUITY`

- url: https://www.youtube.com/watch?v=IvSnlbt89yw · 2026-08-19
- **BTST** = Buy Today Sell Tomorrow: buy near close, exit next morning on gap-up / strong open (~00:04–01:03). Overnight news / global / **gap-down** risk (~01:05–01:10). **Not a recommendation** (~02:44–02:52).
- Three checks around **3:15**: volume, momentum/trend, breakout (~00:36–00:54, 01:15–01:28, 02:23–02:28).
- Workflow spoken: some people only watch **3:00–3:30**, pick ~**3:15**, exit next day **9:30–10:00** (~02:59–03:13). Later: start analysis **3:10**, execute by **3:15**, hold to **3:30**, exit next **9:15–10:00** (~13:29–13:51). Clock **3:15 vs 3:10 vs “5:15”** appears (~00:22, 07:44, 11:04) — treat as **search range**, `[UNCERTAIN_TRANSCRIPT]`.
- Daily-chart conditions (Federal Bank walkthrough): **RSI > 65** (14-period in ScanX build) (~07:33–07:36, 12:09–12:14); **today’s open > yesterday’s open**; **today’s close > yesterday’s close** (~07:48–07:59); **today’s volume ≥ 2× last-10-day average / 10-day SMA volume × 2** (~08:02–08:21, 11:20–11:26); **today’s high ~90% of ~250-day / 1-year high** (₹100 high → stock above 90) (~08:32–08:58) — **wording messy**; `[UNCERTAIN_TRANSCRIPT]`.
- Speaker: this is a **proxy screener**, **not** “the” screener; **do not purchase from the screener alone**; shortlist then track (~10:36–10:53, 13:00–13:24). Saved name **BTST proxy**; ScanX click-through to Dhan Charts (~11:10–11:14, 13:06–13:09). Universe spoken **~2900** listed stocks (~10:55–10:58) — **dated catalog size, not a constant**.
- Chart anecdotes (Hero MotoCorp 17 Nov, Federal Bank 18 Nov, Kalyan Jewellers) with % moves — **examples**, speaker repeats **not a buy/sell recommendation** (~03:28–07:00, 12:38–12:55).
- MTF Excel promo in the middle is **product CTA**, not a rule (~04:15–05:04).

### 4TT8IV5S1_A — “Buy the dip” / pullback ScanX · `EQUITY`

- url: https://www.youtube.com/watch?v=4TT8IV5S1_A · 2026-06-16
- Thesis: pullback in an uptrend can offer closer stop / farther target (~00:14–00:38). **Unknown** whether dip is reversal vs pullback (~00:40–00:43).
- Tools: **Dhan Charts + ScanX** (~02:18–02:52). Comment CTA “pullback screener” (~01:05–01:09).
- Uptrend filters: **price > 50 EMA**; **20 EMA > 50 EMA**; **50 EMA > 200 EMA** (~03:10–04:04).
- Pullback: last-two-weeks % change example **−10% to −5%** — “no set criteria,” change the number (~04:49–04:57); optional **RSI 40–55** (also spoken 40–50) (~05:10–05:25) `[UNCERTAIN_TRANSCRIPT]`; optional **market cap ≥ ₹5000 crore** (~05:58–06:03).
- **Do not buy only because it is in pullback.** Trigger: **30-minute** chart **5 MA > 15 EMA > 50 EMA** (~06:22–06:54). RSI “not needed” at trigger (~06:41–06:43).
- Example names (SMS Pharma, “Madhya Pradesh Today Media,” “US Martin”) and “~13% in 2 days” (~08:28–09:12) — **anecdote / `[UNCERTAIN_TRANSCRIPT]` names**, not a sample study.

### _byuht38r5s — “Intraday Rockers” ScanX · `EQUITY`

- url: https://www.youtube.com/watch?v=_byuht38r5s · 2026-01-18
- **Not investment advice** (~00:26–00:28). Screener run **9:20** (~01:14–01:16). Name: **Intraday Rockers** (~02:03–02:05). Built on ScanX (“money scanix”) (~00:35–00:37).
- Filters: **close > EMA 20** (~03:01–03:27); **close > Supertrend**, default spoken **7, 3** (~03:45–03:57) — **differs from 10,3 elsewhere**; `[UNCERTAIN_TRANSCRIPT]`; **14-period RSI between 55** and (overbought; upper bound cut) (~04:09–04:23) `[UNCERTAIN_TRANSCRIPT]`; **today’s volume > 2× last-10-day average** (~05:15–05:26); **MACD histogram bullish** (~06:01–06:39); **today’s % change > 0.5%** (~07:17–07:20, 07:55).
- Also spoken “trading above the **21 EMA** in the long term” (~07:32–07:35) vs 20 EMA earlier — **conflict**.
- Exit anecdote: book ~**0.6–0.7%** intraday; partial ~**10–15%** of position; **60–65%** scale-out if 100 shares (~08:46–09:02). **Not a backtest.** Nifty “slightly positive” that day (~01:53–01:55) — regime of the recording.

### pBQ1oVDVe3M — “RLB” Rocket Launcher Breakout · `EQUITY`

- url: https://www.youtube.com/watch?v=pBQ1oVDVe3M · 2026-08-09
- Name at end: **RLB = Rocket Launcher Breakout** (~07:40–07:56). ScanX create (~03:05–03:13). Optional F&O **OI long/short build-up** on OT web (~01:37–01:42, 02:42–02:44).
- Filters: **price > previous day’s high** (not today’s high) (~03:23–03:38); **green candle: close > open** (~03:47–03:59); **close > 20 EMA and > 50 EMA** (50 SMA allowed as alt) (~04:17–04:38) `[UNCERTAIN_TRANSCRIPT]`; **RSI > 60, preferably > 65** (puts **65**) (~04:42–04:50); **today’s % change > 2%** (~05:04–05:11); **volume > 5-day SMA volume** (~05:17–05:22).
- Chart-day % / “38% in 1 month” (~07:29–07:31) — **anecdote, not a study.**
- MTF / pledge-MF / “ETF worth Rs 500” leverage story (~08:09–08:28) — **product CTA + `[UNCERTAIN_TRANSCRIPT]`**. Not a return forecast.

### OZRfSMg4qUY — same few stocks, cash, 20 EMA + VWAP · `EQUITY`

- url: https://www.youtube.com/watch?v=OZRfSMg4qUY · 2026-05-12 · speaker Mukul Choudhary (~00:51–00:53)
- Reset: pick **3–4 stocks**, work them **3–4 months** minimum; **no hopping** (~00:17–00:21, 03:22–03:54). **No Nifty, no Bank Nifty** (~03:46–03:47). **Cash market only** (~04:08–04:12).
- If already in **Nifty options**, speaker: **do not even think about stock options** — lot sizes big, less liquid; stock options framed around **quarterly results** / IV crush / selling straddles etc. (~04:12–04:40). That is **spoken opinion**, not a liquidity study.
- Indicators: **VWAP** (ASR “VVIP”/“VWP”) + **20 EMA** only (~04:56–05:03). Extra MAs “10 15 13 40 45 200” left to the viewer (~05:09–05:12).
- Example watchlist spoken: Bajaj Finance, “Trendt,” Bajaj Finserv, Titan, Maruti — then drop Bajaj Finance to leave **four** (~05:21–05:35). **Examples, not a recommended universe.**
- Long: 20 EMA cross / pullback to 20 EMA (~06:11–06:50). Short: price **below 20 EMA and VWAP**, wait pullback (~09:03–09:25). “Four stops” if four names (~07:36–07:38). `[UNCERTAIN_TRANSCRIPT]` on stop construction.
- Spoken “90% of mistakes go away” / “guarantee” (~00:29–00:33) — **rhetoric, not a measured rate.**

### ZoCD4fLKy6M — 9:08 / 9:20 pre-open sector → stock · `EQUITY`

- url: https://www.youtube.com/watch?v=ZoCD4fLKy6M · 2026-08-01 · `qa_flags: none` on EN file
- Times spoken: **9:08** and **9:20** (~00:41–00:53). Block deals **8:45–9:00** (~01:56–02:03). NSE first data ~**9:08** on sector/stock gap (~02:27–02:37). Regular open quiz: 8:45 / 9:00 / **9:15** (~01:36–01:51).
- Method: Dhan Charts **Scan watch list** of sector indices (Nifty, Bank, IT, etc.) at **9:08** to see largest **potential** gap (~03:13–03:45, 08:49–09:06). Trade **price action**; indicators optional (~01:19–01:26). Stop small, target big (~01:06–01:09) — **no numeric stop.**
- Recording-day IT gap-down illustration (~05:01–06:34). **Tape of that morning, not a sample.**
- 9:15–9:20 candle after open (~09:08–09:11). Nifty used as **index context** for **which sector/stock** to trade — still an **equity-selection** video, not an index-option spec.

### H_6keeRUCDM — RSI oversold + Supertrend child (stocks / gold) · `EQUITY`

- url: https://www.youtube.com/watch?v=H_6keeRUCDM · 2025-06-11
- Supertrend **defaults spoken 10, 3** (~09:34; quiz ~01:40–01:51).
- Parent: **RSI oversold + green candle** (weekly examples: Adani Enterprises, Info Edge); child **one step lower**; buy when price **closes above Supertrend** (~06:00–09:46). Examples are **stocks** (and gold futures in the Hindi/EN mix per transferable note) — **not** index options.
- MTF 1/4–1/3 capital, ~**12.5%** annual interest → ~**0.04%/day** example; 4% in 10 days vs 0.4% interest (~04:12–04:44) — **illustrative arithmetic, not a backtest.** Pledge demat **MF** for margin (~05:07–05:29).
- RSI period **not spoken** → `UNKNOWN` (do not assume Wilder 14 as Dhan-spoken).

### PUkzVgVPCf0 — intraday price action (stock examples) · `EQUITY`

- url: https://www.youtube.com/watch?v=PUkzVgVPCf0 · 2025-07-12
- Mix of PA + indicator. Trailing: recent **swing low**; also **VWAP**; “open = low” PA (~11:21–11:26 in transferable extract). **Stock-intraday examples.** VWAP only on a **traded** instrument. Thin extract; full EN file still `WAITING_FOR_EDIT` for remaining patterns.

### G31RFueZLvk — BTST masterclass · `EQUITY` + `STOCK_OPTION`

Full claim table: [`G31RFueZLvk.md`](G31RFueZLvk.md). Opening ~00:00–00:42 still **garbled** — ignored.

- Universe: **F&O stocks**; start **14:55**; % change rank; **close > prior-day high** (CPR); 5m **RSI ~50–75** (85+ skip); option overlay **15:15–15:20** with Supertrend **10,3** + Hull **32**; next-open exit **09:15–09:20**. SL **time-based**, not price. **UNVALIDATED** slot `SO-003`.

### 2YBmiyVmNNw / dEvF8biE02M — swing masterclasses · `EQUITY`

- `2YBmiyVmNNw` (2026-06-17, ~88 min): guest **Animesh**; MTF Excel CTA; career/psychology; “strategy plays a complete **10%** role” (~08:06). **Still no clean entry recipe** (`DATA_INSUFFICIENT` / `WAITING_FOR_EDIT`).
- `dEvF8biE02M` — full table: [`dEvF8biE02M.md`](dEvF8biE02M.md). **5-year ATH horizontal** breakout; volume + **delivery ~40%**; SL = breakout low **−1%**; T1 = range height; trail **two weekly closes below 21 EMA**. Spoken 100%/2y is **definition language, not a return.** Slot `EQ-014` `UNVALIDATED`.

Do **not** copy guest % into any performance table.

### EVk_Wa_1cm0 — Darvas Box · product only

[`EVk_Wa_1cm0.md`](EVk_Wa_1cm0.md). Sideways-zone dots; **not** a future predictor; **no** params. **No EQ slot.**

---

## English transcripts — skipped here

Index-options, order-flow, scalping tools, chart-product, candlestick **pattern education** (`njqeZc_tYy8` — general TA; other agents / transferable), commodities (`dYva2rO1LOw`), MTF-only promo (`ZPAYPwPaJzo`), brand/music/Diwali (`WmJttDnvCKM`, `Wmpi-BXclXw`, `UaHdow8V8Eg`, `T9eo_YxAr9U`, etc.).

`njqeZc_tYy8` / `wDZXqzdGBDc` remain **transferable TA / product**, not equity-selection screens — see [`TRANSFERABLE_AND_SKIPPED.md`](TRANSFERABLE_AND_SKIPPED.md).

---

## What 04_quant must do

- Read [`EQUITY_ETF_BACKLOG.md`](../../../04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md). Every slot is `HYPOTHESIS` / `UNVALIDATED`.
- Keep `EQ-*` / `ETF-*` / `SO-*` **out** of `MASTER_STRATEGY_PLAN.md` Phase-1 index book until a later charter says otherwise.
- Treat ScanX filter lists as **product-replicable hypotheses**, not proven screens.

## What 04_quant must not do

- Delete or retag catalog `STOCK_ONLY` / `EXCLUDED_STOCK_ONLY` to “clean” Phase-1.
- Invent win rates, CAGR, or “IMB returns 1.5%.”
- Write algos / ScanX bots / live scanners.
- Collapse stock-options **titles** into spoken Greeks rules.
- Transfer these recipes into NIFTY CE/PE STRATs without a **new** `HYPOTHESIS` labeled `PROJECT-DERIVED` (and still UNVALIDATED).

## Blockers

| Item | Label |
|------|--------|
| All 9 catalog `STOCK_ONLY` + stock-options series + ETF strategy titles | `TRANSCRIPT_PENDING` / no EN file |
| Supertrend length on Alpha / IMB | `UNKNOWN` |
| RSI period on H_6kee / several scanners | `UNKNOWN` unless 14 is explicitly spoken (IvSnlbt / Rockers) |
| `2YBmiyVmNNw` swing class | `DATA_INSUFFICIENT` / `WAITING_FOR_EDIT` |
| G31 RSI 5 vs 50; put band 25–45; Hull 32 “backtest” | `[UNCERTAIN_TRANSCRIPT]` / not in repo |
| ScanX “unusual volume” definition | `UNKNOWN` (product token, not annexure) |
| Live Dhan ScanX share codes | not in git; **do not scrape comments** |

**Review:** n/a · five-pass not requested on this packet.

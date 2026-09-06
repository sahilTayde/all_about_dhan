# SOURCE_FACT — TA / market structure (English transcripts)

**Team:** 01_research  
**Layer:** `SOURCE_FACT` (spoken Dhan education) only. Index-options *application* is tagged **`HYPOTHESIS` / `UNVALIDATED`** and is **not** a rule.  
**Status:** `EXTRACTED` / `DRAFT`. **Not** a strategy. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Date:** 2026-09-03  
**Corpus:** `data/transcripts/normalized_en/` (`ENGLISH_VERIFIED`; most rows `qa_flags: UNCERTAIN_TRANSCRIPT`).  
**Do not treat as advice, edge, or live params.** No live trading.

Coalition: [`TASK_TRANSCRIPT_COALITION.md`](../../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md).  
Math companion (VALIDATION vs spoken): [`teams/02_phd_math/docs/TA_FROM_TRANSCRIPTS.md`](../../../02_phd_math/docs/TA_FROM_TRANSCRIPTS.md).  
Official HQ catalog (not this packet): [`DHAN_OFFICIAL_INDICATORS.md`](../DHAN_OFFICIAL_INDICATORS.md).  
**Do not duplicate** the options-chain packet (`OPTIONS_INDEX_PACKET.md`). This file owns **TA / structure**. Strike/Greeks/OI/expiry calendars stay there.

English captions are YouTube translate of Hindi ASR. Numbers that are not trivially restated are tagged **`[UNCERTAIN_TRANSCRIPT]`**. Do not silently “correct.”

---

## One-screen (for 04 / 02)

| Need | What Dhan **said** (this packet) | What DhanHQ **returns** |
|------|----------------------------------|-------------------------|
| Supertrend / RSI / MACD / EMA **series** | Chart + spoken params | **No series REST.** Charts = OHLC (+ volume, optional OI). Compute later from OHLC. |
| Supertrend period/multiplier | Spoken **10, 3** as “default” in `H_6keeRUCDM`, `2RnBT9DDDNI`; `G31RFueZLvk` “103” | **Not** an annexure `indicatorName`. ScanX “Intraday Supertrend” = product UI. |
| RSI | Oversold ~**30** + green candle (`H_6kee`); **14-period** named in `_byuht38r5s`; bands 55–70 / 40–55 / >60 spoken in scanners | Trigger token **`RSI_14` only** (condition, not a series) |
| EMA | Spoken **9, 10, 20, 50, 200** (and 15, 21, 30, 100, 300). Super Scalper fast/slow **lengths not spoken** | Annexure EMA set **5, 10, 20, 50, 100, 200**. **`EMA_9` is not in the annexure.** |
| MACD | Spoken **12 and 26**; then **×3 or ×4** (`HAUSZx`); or **24 and 52** (`6E_K1wVkHyw`); histogram-only in HAUS | `MACD_12` / `MACD_26` / `MACD_HIST` as **trigger names**. No signal-length token. |
| VWAP | Session VWAP on **traded** instrument; **not** cash NIFTY volume (`2RnBT9`, `pUg_7sPauQA`, `YUXJv_xBStw`) | Quote `average_price` = “VWAP of the day” snapshot. **Not** a VWAP bar series. |
| Opening range | Product ORB; speaker setting **09:15–10:00**; others named 09:15–09:30 / 09:15–09:45 (`eApl0SfVBBY`) | **No** ORB REST. |

Production stays Dhan-only (`implementation.indicators: dhan_only`). Empty `packages/indicators` is **correct** until review.

---

## Scope and skips

**In:** Supertrend, RSI, EMA/SMA, MACD, VWAP/VWMA, price action, candlesticks, opening-range / first-slot structure, dual-timeframe as structure, session clocks that gate TA.

**Out (sibling packets or skip):**

| id | why skipped here |
|----|------------------|
| Options chain / Greeks / OI / strike pick as the *subject* | `OPTIONS_INDEX` packet |
| `6WZxLShiUT8`, `qSgKA0-T7Uw`, `lNSmwmlUI54`, `8h9SYvQWKMA`, `T9eo_YxAr9U` | product walkthroughs — **no TA rules** |
| `EVk_Wa_1cm0` | Darvas Box **product** demo, not a parameterized TA system |
| `UaHdow8V8Eg`, `Wmpi-BXclXw`, `WmJttDnvCKM`, `JhHkEIUznVw`, `PLQtDASa064`, `s7rxvdWTlHQ`, `ZPAYPwPaJzo` | promo / music / MTF / news — **NOT_EVIDENCE** |
| `6el9Jqnrdz8`, `_exmJYgFwFA` | option **selling**; RSI named only as a trend-failure anecdote — not extracted as a buy TA |
| `YUXJv_xBStw`, `DzT_681GThA` | order-flow product; keep only the **lagging-TA** sentence below |
| Stock scanners (`_byuht38r5s`, `4TT8IV5S1_A`, `pBQ1oVDVe3M`, `kJ5HZKzpZqQ`, `O8h44rgJ84k`, `MfGUybW4O4c`, `G31RFueZLvk`, `IvSnlbt89yw`, `ZoCD4fLKy6M`) | `STOCK_ONLY` / transferable. Spoken **params** recorded; **not** Phase-1 index rules |

Prior thin notes: [`TRANSFERABLE_AND_SKIPPED.md`](TRANSFERABLE_AND_SKIPPED.md). Per-video index-option handoffs (`HAUSZx-hYdY`, `2RnBT9DDDNI`, `pvmvkiS1cx4`, …) remain the long-form SOURCE_FACT; this packet **clubs TA** so 02/04 do not re-read 45 files.

---

## Supertrend

### SOURCE_FACT (spoken)

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| ST-01 | `H_6keeRUCDM` | 01:40–01:51, 09:31–09:44 | Quiz: default Supertrend is **10,1 / 10,2 / 10,3**. Answer spoken: **“default parameters … are 10 3”**. Buy when price **goes above** Supertrend; buy **above that high**. Child TF one step below the RSI parent. | high on 10,3 as *spoken default*; examples are **stocks** (weekly→daily) and **gold futures** (2h RSI → 45m ST) |
| ST-02 | `2RnBT9DDDNI` | 21:53–21:59, 25:09–26:09 | Supertrend **“default … 103”** kept unchanged. On **index futures**, **3-minute**. Put buy if price **below** VWAP **and** VWMA **and** Supertrend; call buy if **above all three**. Exit if 3m candle **closes** the other side of Supertrend. | high on 10,3 as spoken; “103” = 10,3 `[UNCERTAIN_TRANSCRIPT]` as digits |
| ST-03 | `2RnBT9DDDNI` | 34:54–36:01 | If Supertrend and VWAP **disagree** → **no new** entry (sideways / no-trade). | high |
| ST-04 | `HAUSZx-hYdY` | 44:51–44:56 | Supertrend named as a **trend** tool: price above = bullish, below = bearish. **No period/multiplier spoken.** | high (named only) |
| ST-05 | `gA5FtEnSABM` | 03:56–04:18 | Falling market: may use Supertrend for reversal; **first** look at **RSI divergence**. | high (named; no params) |
| ST-06 | `_byuht38r5s` | 03:45–03:57 | ScanX: close **above Supertrend**. Spoken: **“By default parameter 7 is 3.”** | **`[UNCERTAIN_TRANSCRIPT]`** — do **not** freeze 7,3; conflicts with ST-01/ST-02 |
| ST-07 | `G31RFueZLvk` | 49:32–49:42 | BTST option-chart overlay: Supertrend **“default parameter will be 103”**; 5m close above (call) / below (put). Hull “32” also spoken. | ST 10,3 spoken; Hull **32** `[UNCERTAIN_TRANSCRIPT]`; **STOCK / BTST** |

**Not spoken as HQ API:** nobody claims a Supertrend REST series.

### HYPOTHESIS UNVALIDATED (index options)

Apply ST(10,3) — **if** 02 confirms TV-style ATR bands match Dhan **charts** — on **index futures** OHLC (not cash index), then buy CE/PE. **5m Supertrend = confirm or kill, not entry** is a **desk spec**, not a quote from these videos. `STRAT-003` 3m interval is **not** in HQ `{1,5,15,25,60}` → resample hypothesis.

---

## RSI

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| RSI-01 | `H_6keeRUCDM` | 06:00–06:42, 12:14–12:24 | Parent TF: **RSI oversold** + **green candle** (rare in a fall) as reversal *candidate*. Child TF: Supertrend close-above. Oversold illustrated with values **below 30** (24.17, 27.85, 28.05, 29.85…). **Period length not named** in this video. | high on structure; printed RSI values `[UNCERTAIN_TRANSCRIPT]` |
| RSI-02 | `_byuht38r5s` | 04:09–04:35 | **“14 period RSI”** between **55 and 70** for *intraday stock momentum* (not overbought, not below 50). | high on 14 named; **STOCK screener** |
| RSI-03 | `njqeZc_tYy8` | 13:50–14:02 | Hammer confluence: RSI **already oversold**, “value is **below 30**.” | high on 30 as spoken band; period unnamed |
| RSI-04 | `4TT8IV5S1_A` | 05:10–05:25 | Pullback filter: RSI **40 to 55** (spoken “40 to let us say 50 and 55”). **Not mandatory.** | `[UNCERTAIN_TRANSCRIPT]` upper bound; **STOCK** |
| RSI-05 | `pBQ1oVDVe3M` | 04:42–04:47 | Breakout scanner: RSI **at least above 60**, **preferably above 65**. | high as spoken; **STOCK** |
| RSI-06 | `gA5FtEnSABM` | 04:10–04:22 | RSI **divergence** vs price lower-lows before a view. | high (no period) |
| RSI-07 | `YUXJv_xBStw` | 01:21–01:34 | RSI, MACD, MAs are **lagging**; order-flow is framed as real-time participation. | high as *product claim*, not a formula |
| RSI-08 | `HAUSZx-hYdY` | 44:41–44:45 | RSI named with Williams %R / CCI as **reversal/momentum** family. **Not parameterized.** | high |

### HYPOTHESIS UNVALIDATED (index options)

Wilder **RSI_14** on **futures or index** OHLC; oversold+green as WATCH; do **not** treat 55–70 stock-scanner bands as NIFTY option entry. News shock → lagging RSI/MACD **late** (persona; not a transcript theorem).

---

## EMA / SMA

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| MA-01 | `HAUSZx-hYdY` | 47:40–47:54, 59:24–59:28, 01:00:07–01:00:14 | Stack **10, 30, 100**. Bullish if **10 > 30 and 30 > 100**. Recap also says 10 above 30 **and 300**. | **100 vs 300 conflict** `[UNCERTAIN_TRANSCRIPT]` |
| MA-02 | `HAUSZx-hYdY` | 56:24–56:30 | Hold while **10-period MA above 30**. (Prior Hindi handoff also has **9 vs 10** trail language — treat as `[UNCERTAIN_TRANSCRIPT]`.) | medium |
| MA-03 | `PUkzVgVPCf0` | 06:51–06:55, 09:38–10:02, 12:00–12:05 | Intraday **open=low** stocks, **3m**: **9, 30, 100** period MAs. Trail: **9-period below 30** → exit. Also “**9 EMA** falls below 30.” | 9 vs SMA/EMA mix `[UNCERTAIN_TRANSCRIPT]`; **STOCK** |
| MA-04 | `pvmvkiS1cx4` | 02:33–02:46, 04:00–04:06 | NIFTY / BANKNIFTY / SENSEX **2-minute**: **EMA 10 and EMA 20 only**. No oscillators. Chart default spoken **“9 and 26. We don't want 10 or 20”** then **“We use 10 … and 20”** — first clause is ASR noise; **do not invent 9/26 as the system.** `[UNCERTAIN_TRANSCRIPT]` | high on 10/20 as the *intended* pair |
| MA-05 | `mPKASwm6Oqk` | 02:28–02:35, 03:25–03:32, 04:42–05:18 | Scalp: **EMA 10** (blue) + **EMA 20** (red) + **DEMA length 100** (black, “secret”) as **direction**. Wait entries **near 10/20**. NIFTY 50 examples; “follow indicators first on the **underlying**.” | high on 10/20/100 DEMA as spoken |
| MA-06 | `4TT8IV5S1_A` | 03:13–04:04, 06:32–06:54 | Trend filter: price > **EMA 50**; **20 EMA > 50 EMA**; **50 EMA > 200 EMA**. Trigger on **30m**: **5 MA** above **15 EMA** above **50 EMA**. RSI not needed at trigger. | high as spoken; **STOCK dip screener** |
| MA-07 | `_byuht38r5s` | 03:01–03:14, 07:32–07:35 | Close > **EMA 20**; later “above the **21 EMA** in the long term.” | **20 vs 21** `[UNCERTAIN_TRANSCRIPT]`; **STOCK** |
| MA-08 | `2RnBT9DDDNI` | 46:59–48:21, 51:24–52:06 | Dhan **Super Scalper** on **option premium**, **1-minute**: **Fast EMA + Slow EMA** (bands/golden signals removed). Long call: price **above** both and **fast above slow**. Stop spoken **below slow EMA**. **Numeric lengths NOT spoken → `UNKNOWN`.** | high on structure; lengths UNKNOWN |
| MA-09 | `eApl0SfVBBY` | 03:35–03:41 | Lists **9, 30, 100, 200, 50** period EMA as *examples of fixed-length MAs* vs Hull. Not a stack rule. | named only |
| MA-10 | `6E_K1wVkHyw` | 05:54, 06:33–06:42 | NIFTY chart: spoken **9-minute** then later **1-minute**. MACD MAs **24 and 52 instead of 12 and 26**. | TF **9 vs 1** `[UNCERTAIN_TRANSCRIPT]` |

**Annexure gap (docs, not transcript):** spoken **EMA 9**, **SMA/EMA 15**, **30**, **21**, **DEMA 100** are **not** Conditional Trigger names. Do not send `EMA_9` to `/alerts/orders`.

### HYPOTHESIS UNVALIDATED (index options)

- Dual-TF option-buy (HAUS): MACD + 10/30/100 on **underlying** hourly + 5m → CE/PE. **100 vs 300** must be a search range, not a frozen spec.  
- Index scalp (`pvmvkiS1cx4`): EMA 10/20 on **2m** (HQ has **1 and 5**, not 2 → resample **UNKNOWN**). Strike/ITM mapping belongs to OPTIONS_INDEX.  
- Super Scalper: **cannot** code lengths until spoken or chart-export `VERIFY`.

---

## MACD

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| MACD-01 | `HAUSZx-hYdY` | 45:07–46:51, 01:00:07–01:00:22 | Default spoken **12 and 26** period MAs. Then **“four times” / “three times or four times”** all params so fewer, larger swings. Drop MACD/signal lines; **histogram only**: green = bullish, red = bearish. Parent **hourly**, child **5m** (or 10m). Entry: child MACD bullish **and** MA stack bullish; buy **above that candle’s high**. | **×3 vs ×4** `[UNCERTAIN_TRANSCRIPT]`; signal 9 **not clearly spoken** |
| MACD-02 | `_byuht38r5s` | 06:31–06:42 | MACD histogram **above zero**; “keep whatever parameters we have **by default**.” | defaults unnamed |
| MACD-03 | `6E_K1wVkHyw` | 06:28–06:42 | Slow MACD: **24 and 52** “instead of 12” and “52 instead of 26.” | 2× of 12/26 as spoken; **not** the HAUS ×4 story |
| MACD-04 | `kJ5HZKzpZqQ` | 04:14–04:21 | Stock screener: MACD line > signal **or** histogram bullish (daily + 5m exit language). | **STOCK**; params unnamed |

### HYPOTHESIS UNVALIDATED (index options)

Compute Appel MACD from **futures/index close** OHLC. Do **not** freeze 48/104/36 or 24/52 without chart `VERIFY`. Histogram sign ≠ a complete regime classifier. **5m MACD = confirm or kill** is staging spec, not HAUS (HAUS uses MACD as **entry filter** on child TF).

---

## VWAP / VWMA / AVWAP

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| VWAP-01 | `2RnBT9DDDNI` | 17:59–19:20, 21:40–21:52, 23:48–24:03 | Analysis on **futures** because **volume exists**; **spot volume on NIFTY is not “how much NIFTY traded.”** VWAP **default** (color only). **VWMA length 20.** Ignore **09:15–09:45**. Flatten **before 15:15**. Intraday only. | high |
| VWAP-02 | `pUg_7sPauQA` | 00:23–00:46, 01:56–02:35, 02:54–03:08 | VWAP = **volume-weighted average price**. Unlike an SMA, VWAP **goes flat** as the day passes (morning volume then dies). Demo on NIFTY **spot** is **pedagogy**; **“VVP trading is done on futures”** (options, futures, stocks — where you can trade). Settings: H/L/C, step line. | high |
| VWAP-03 | `pUg_7sPauQA` | 03:22–04:12, 08:27–09:34, 13:14–14:30 | Three day types: **trend / sideways / news**. Morning **below VWAP** + open drive down → shorts on VWAP pullbacks. **Bullish engulfing / morning star** (longs) or **bearish engulfing / evening star** (shorts) **near VWAP** plus **liquidity sweep** — else sit out. Repeated VWAP crosses → **sideways, don’t trade**. Prefer VWAP work **by 12:00** / “**11 am to 12:00**”; after that VWAP flattens. RR spoken **1:2** (start). | session clocks `[UNCERTAIN_TRANSCRIPT]` 11 vs 12; **PA+VWAP**, not a numeric VWAP length |
| VWAP-04 | `PUkzVgVPCf0` | 11:11–11:58 | Optional: while price **above VWAP**, don’t panic; **below VWAP** may **partial** exit; **9 vs 30 MA** is the hard trail. | **STOCK**; VWAP as trail overlay |
| VWAP-05 | `YUXJv_xBStw` | 05:37–05:47 | On DEXT order-flow: VWAP yellow line = VWAP **through the day**. **Futures tape.** | product; no entry rule |
| VWAP-06 | `eApl0SfVBBY` | 01:30–02:20 | Session VWAP vs **anchored VWAP** from a marked swing date (stock examples). Product indicator. | named; **not** HQ REST |

### HYPOTHESIS UNVALIDATED (index options)

Session VWAP + VWMA(20) + ST(10,3) on **NIFTY/BANKNIFTY/SENSEX futures** (SENSEX = BSE F&O), execute on **OPTIDX**. **Never** VWAP the cash index. Quote `average_price` ≠ bar VWAP series (`UNKNOWN` identity). 3m bars = resample hypothesis.

---

## Price action / market structure

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| PA-01 | `wpdqqXhhq88` | 00:00–00:08, 05:15–06:08 | “Price action ultimately is the father of everything.” Golden rule: **big candles are king makers**; **small candles have no value**. Pure PA: **no indicators, no volume** — “just charts and candles.” ~99% of big candles “will have volume” even if you don’t plot it `[UNCERTAIN_TRANSCRIPT]` 99. | high on philosophy; 99 folklore |
| PA-02 | `wpdqqXhhq88` | 10:56, 21:37–21:41 | Structure: **higher high / higher low**. | high |
| PA-03 | `wpdqqXhhq88` | 24:41–25:36 | Mark **50% of the 09:15** (opening) candle; fail to hold that 50% → **short**, stop **above that candle**. Example **Bajaj Finance** (stock). | high as spoken method; **not** an index-option recipe |
| PA-04 | `wpdqqXhhq88` | 00:27–00:33, 46:24–47:08 | **VCP** (volatility contraction) named (Minervini). ScanX “squeezing range” / BB+ATR as a *finder*, not a formula dump. | named; **STOCK** flavour |
| PA-05 | `PUkzVgVPCf0` | 06:24–06:31, 09:22–09:33, 11:19–11:26 | **Open = low** (buy) or **open = high** (mirror). First **3m** candle **09:15–09:18** high is a level; trade after **09:30**. Ultimate stop = **recent swing low**. | **STOCK** F&O list |
| PA-06 | `pUg_7sPauQA` | 08:36–09:08, 10:58–11:18 | Do **not** buy a hammer alone. Need **liquidity sweep** then confirmation candle. | high |
| PA-07 | `mPKASwm6Oqk` | 01:53–02:04 | PA is “food”; indicators are “protein” (supplement). PA hard to backtest precisely. | opinion / method |
| PA-08 | `eJ_gAffsLoc` | 01:08–01:34 | Guest: mostly follows **price action** (anecdote, not a system). | skip as rule |

### HYPOTHESIS UNVALIDATED (index options)

HH/HL + opening-candle 50% on **index futures** 5m/15m as **structure WATCH**; CE/PE only after a separate confirmation layer. Open=low does **not** transfer to a cash index the way it does to a stock auction.

---

## Candlesticks

### SOURCE_FACT — five patterns (`njqeZc_tYy8`)

Speaker: patterns can be a **system** (entry / exit / stop) but **must** use confluence (trend, S/R, RSI) — **not standalone** (~12:54–14:09).

| # | pattern | structure as spoken | confluence / trade sketch |
|---|---------|---------------------|---------------------------|
| 1 | **Hammer** | Single candle; **small body**, lower wick **“two to three times”** the body (~09:05) `[UNCERTAIN_TRANSCRIPT]` | Best in **downtrend**, or near **support**, or with RSI **< 30**. Buy if later prices trade **above hammer high**; stop **just below hammer low**; min RR **1:2**. |
| 2 | **Bullish engulfing** | Two-candle bullish reversal (~17:26+) | Same confluence idea as hammer; **20 SMA** mentioned as a location filter (~07:44). Ignore in wrong trend. |
| 3 | **Morning star** | **Three**-candle bullish reversal (~25:37+) | Same confluence. |
| 4 | **Dark cloud cover** | Bearish (after uptrend / at resistance) (~32:46–35:57) | **Look in uptrends**; ignore in downtrends. |
| 5 | **Inside bar** | Two-candle; **continuation or reversal** depending on trend and zone (~35:59–36:23) | Not inherently bullish or bearish. |

Also named in passing: **marubozu**, **doji**, bullish engulfing vs **20 SMA** (~06:46–07:44).

### SOURCE_FACT — product auto-detect (`wDZXqzdGBDc`) — **tool, not a rule set**

Dhan candlestick-pattern indicator: 20–30+ patterns; trend filter **EMA 50** or **50+200**; bullish/bearish filter. **Skip as strategy evidence.**

### SOURCE_FACT — VWAP tape (`pUg_7sPauQA`)

**Bullish engulfing / morning star** vs **bearish engulfing / evening star** as the only PA triggers *in that VWAP video* (not the njqe five).

### HYPOTHESIS UNVALIDATED (index options)

Candle patterns on **futures** (or option premium only if a separate spec says so). Confluence required. Auto-detect is **UI**, not an API series.

---

## Opening range / first slot

### SOURCE_FACT

| claim_id | video | ts | spoken | confidence |
|----------|-------|----|--------|------------|
| OR-01 | `eApl0SfVBBY` | 05:11–05:57 | “Most of us trade the **opening range breakout**.” Ranges named: **09:15–09:30**; some **09:15–09:45** `[UNCERTAIN_TRANSCRIPT]` “1:45”; speaker personally **starts after 10:00**. Dhan **ORB** indicator: setting **09:15–10:00** marks the range; trade after it prints. NIFTY 5m anecdote (points) `[UNCERTAIN_TRANSCRIPT]`. | high on *speaker’s* 09:15–10:00 setting; other windows are “some people” |
| OR-02 | `2RnBT9DDDNI` | 23:48–24:03 | **Ignore 09:15–09:45** completely; start after 09:45; out before 15:15. | high (index OB class) |
| OR-03 | `HAUSZx-hYdY` | 55:21–55:52, 01:00:22–01:00:35 | New trades **after 10:00**, mostly **not after 14:30**, **not after 15:00**. Best personal window **~11:00–13:00**. 14:45 vs 15:00 wording messy `[UNCERTAIN_TRANSCRIPT]`. | high on 10:00 / 14:30 / 15:00 as intent |
| OR-04 | `PUkzVgVPCf0` | 06:16, 11:45–11:48 | Generate after **09:30**; first 3m **09:15–09:18** is the level. | **STOCK** |
| OR-05 | `MfGUybW4O4c` | 04:25–06:32 | First **5 / 15 / 30** minutes = **highest volatility / noise**, not trend. **Skip first 15 minutes** if inexperienced. Screener trades **after 09:45** because PA “settled” **first 30 minutes**. | high as *stock scanner pedagogy*; NIFTY 5m candle used as **volatility illustration** |
| OR-06 | `pUg_7sPauQA` | 13:19–13:23 | Liquidity sweep **within 1 to 1½ hours of the morning** then engulfing. | medium |

**No HQ ORB series.** Product ORB / previous-day H/L/O/C (`eApl0SfVBBY` ~10:16–10:25) are **charts**.

### HYPOTHESIS UNVALIDATED (index options)

Define an opening box on **futures** 1m/5m (IST). Do **not** freeze 15 vs 30 vs 45 vs 10:00 — transcripts **disagree by video**. Treat as a **search set**, then backtest. Flatten times must follow **03_phd_market** F&O close / CAS (`UNKNOWN` 15:30 vs 15:40 vs spoken 15:15).

---

## Dual timeframe (structure, not a coded stack)

| video | parent | child | indicators | universe as spoken |
|-------|--------|-------|------------|-------------------|
| `HAUSZx-hYdY` | **Hourly** (also 2h) | **5 or 10m** (also 15m with 2h parent) | MACD (scaled) + MA 10/30/100 | NIFTY **100 stocks** highly liquid — **not index-only** |
| `H_6keeRUCDM` | Stocks: **weekly**; gold: **2h** | Stocks: **daily**; gold: **45m** | RSI oversold+green → ST | **STOCK** / commodity |
| `pvmvkiS1cx4` | — | **2m** (3m/5m allowed) | EMA 10/20 | NIFTY, BANKNIFTY, SENSEX **spot for BT**, **options to trade** |

“Dual TF more than sufficient” for option buying (~HAUS 41:32–41:54 in Hindi handoff). English HAUS: parent hourly, child 5m.

---

## Lagging vs leading (as spoken)

- Candles **leading** vs indicators **lagging** (`njqeZc_tYy8` 00:16–00:22).  
- RSI/MACD/MA **lagging** vs order-flow (`YUXJv_xBStw` 01:21–01:34) — OF details are **not** this packet.  
- HAUS: MA and MACD **take turns** leading/lagging; take the **common** (spoken “LCM”) window (~48:15–48:21).

---

## Index-options application map (`HYPOTHESIS` / `UNVALIDATED`)

Do **not** read this table as Dhan recommending these as production NIFTY option systems. 04_quant may attach to **existing** `STRAT-001`–`014` only.

| Spoken TA | Transfer idea (unvalidated) | Do not |
|-----------|-----------------------------|--------|
| Futures VWAP+VWMA(20)+ST(10,3), 3m, skip 09:15–09:45 (`2RnBT9`) | Closest **index OB** TA in the corpus. Execute CE/PE; analysis on **FUTIDX**. | VWAP cash NIFTY; freeze lot 65; freeze 3m as HQ interval |
| MACD×? + 10/30/100, 1h/5m (`HAUS`) | Filter on **index** (or liquid underlier) → buy **1–2 OTM** as *speaker’s personal* strike — strike belongs to OPTIONS_INDEX | Freeze ×4 or 300 MA; use NIFTY-100 stock universe as Phase-1 |
| EMA 10/20, 2m (`pvm`) | Index scalp on **futures or spot-for-BT**; options execution | Invent 2m REST; mix DEMA 100 from `mPK` without a new test |
| Super Scalper fast/slow EMA on **premium** (`2RnBT9`) | Triple confirm: futures setup + premium EMAs | Invent EMA lengths; treat Super Scalper as HQ series |
| RSI oversold+green → ST (`H_6kee`) | **Swing/positional** on **index futures**, then options — **theta/horizon conflict** with HAUS “intraday buyer” | Copy weekly+daily stock recipe onto weekly NIFTY options without a horizon spec |
| VWAP + engulfing (`pUg`) | Futures VWAP mean-revert/continuation **intraday**; option as vehicle | Trade NIFTY **spot** VWAP; news-day VWAP flatten as an entry |
| ORB 09:15–T (`eApl`, `2Rn`, `HAUS`) | Opening box on futures → break → CE/PE | One true T; ORB REST |
| Five candles (`njqe`) | Pattern + S/R on futures | Standalone hammer on option LTP |
| Stock scanners (RSI 55–70, ST, MACD>0) | **Equity backlog only** | Phase-1 index book |

---

## Conflicts and `[UNCERTAIN_TRANSCRIPT]` (do not collapse)

| Topic | Conflict | Rule for later teams |
|-------|----------|----------------------|
| Supertrend default | 10,3 vs `_byuht` “7 is 3” | Prefer 10,3 as **repeated** spoken default; 7,3 stays flagged |
| MACD scale | HAUS ×3 **or** ×4; 6E **24/52**; `_byuht` “default” | Three **separate** spoken recipes. Not one “Dhan MACD.” |
| MA 100 vs 300 | HAUS recap | Search range |
| MA 9 vs 10 | HAUS trail / PUkz 9-period | Search range; **EMA_9 ≠ annexure** |
| EMA 20 vs 21 | `_byuht` | Search range |
| Opening skip | 09:15–09:45 vs after 10:00 vs skip 15m vs ORB to 10:00 | Video-specific clocks |
| 3m / 2m / 9m | Spoken; HQ intervals **1,5,15,25,60** | Resample = hypothesis |
| Super Scalper lengths | **UNKNOWN** | Do not invent |

---

## Data requirements (later engine — not this ticket)

```text
DATA_SOURCE: DhanHQ POST /charts/historical | /charts/intraday  (OHLC+volume; oi optional)
             — then CLIENT-SIDE Supertrend / RSI / MACD / EMA / session VWAP
INSTRUMENT: FUTIDX (signals) + OPTIDX (execution hypotheses)
            NEVER cash-index volume for VWAP
EXCHANGE_SEGMENT: NSE_FNO (NIFTY/BANKNIFTY); BSE_FNO (SENSEX)
CALCULATION: not Conditional Trigger series; not ScanX REST
TIMEFRAME: documented 1, 5, 15, 25, 60 min or daily; 2m/3m/9m = UNKNOWN / resample
COMPARE: Dhan chart Supertrend vs our ATR implementation → record mismatch, do not silent-swap
```

**No live `/alerts/orders`.** **No** invented `SUPERTREND_10_3` enum.

---

## What this file is not

- Not proof of edge or a win rate.  
- Not the options-chain packet.  
- Not a license to fill `packages/indicators` before review.  
- Not a product-promo catalog.

# TA from transcripts — math definitions vs spoken params

**Team:** 02_phd_math  
**Status:** `DRAFT` / concepts only. **Not** a strategy approval. **Not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Date:** 2026-09-03  
**Layers (do not collapse):**

| Layer | This file’s job |
|-------|-----------------|
| `SOURCE_FACT` | Point at spoken params in [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md). Do **not** rewrite the quote. |
| `VALIDATION` | Textbook / standard definitions + HQ annexure map. Verdict: `supported` \| `partially_supported` \| `context-dependent` \| `unsupported` \| `UNKNOWN`. |
| `HYPOTHESIS` | Index-options *application* — **`UNVALIDATED`**. 04_quant owns freeze. |

Books (`config/workspace.yaml` `sources.books`): Murphy *TA of the Financial Markets*; Natenberg (options **risk**, not TA optimality). Textbooks are **VALIDATION tags**, not a license to ship a non-Dhan Supertrend as “the Dhan indicator.”

API map (official tokens): [`DHAN_INDICATOR_API_MAP.md`](DHAN_INDICATOR_API_MAP.md).  
Prior concept checks: [`VALIDATION_MATH.md`](VALIDATION_MATH.md).  
HQ docs: [`DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md).

**Hard constraint:** DhanHQ v2 has **no Supertrend / RSI / MACD / EMA9 time-series REST**. Charts return **OHLC + volume** (+ optional OI). A later engine may **compute** from OHLC. That compute is **our VALIDATION implementation**, then compared to Dhan **charts** — never claimed as a hidden field.

No live trading. No invented parameters. `[UNCERTAIN_TRANSCRIPT]` numbers stay ranges.

---

## How to read a row

1. **Spoken** = SOURCE_FACT (video_id).  
2. **Math** = independent definition.  
3. **HQ surface** = annexure / quote field / chart-only.  
4. **Match?** = can we implement the *math* without pretending HQ already did.  
5. **Index options** = HYPOTHESIS UNVALIDATED only.

---

## Supertrend

| | |
|--|--|
| **Spoken** | Default **10, 3** (`H_6keeRUCDM` 09:34; `2RnBT9DDDNI` “103”; `G31RFueZLvk` “103”). `_byuht38r5s` “default parameter **7 is 3**” **`[UNCERTAIN_TRANSCRIPT]`**. HAUS / gA5 name Supertrend **without** params. |
| **Math (VALIDATION)** | Common TV-style: bands from ATR(*period*) × *multiplier*; flip when close crosses the band. Inputs: high, low, close. ATR usually Wilder. |
| **HQ** | **Not in annexure.** ScanX “Intraday Supertrend” = product, params **UNKNOWN**. `/charts/*` = OHLC only. |
| **Match?** | **10,3 as a common default** = `supported` as *literature/TV convention*, **not** unique truth and **not** an HQ field. Alternate 10×1 / 10×2 exist (the quiz in H_6kee). Close vs HL2, ATR seed: **UNKNOWN** until chart export. **7,3** = `SOURCE_UNCERTAIN` — do not freeze. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Compute on **FUTIDX** OHLC; use as **confirm/kill** on 5m in the staged-signal spec — that *use* is **not** a transcript theorem. Do not invent `SUPERTREND_10_3` as `indicatorName`. |

---

## RSI

| | |
|--|--|
| **Spoken** | Oversold **~30** + green candle (`H_6kee`); hammer confluence RSI **< 30** (`njqeZc_tYy8`); **14-period** named (`_byuht38r5s`); scanner bands **55–70**, **40–55**, **>60/65**. Period **unnamed** in H_6kee / njqe / HAUS. |
| **Math (VALIDATION)** | Wilder RSI (1978): RS = avg gain / avg loss over *n*; RSI = 100 − 100/(1+RS). Common *n* = **14**; OB/OS folklore **70/30**. ScanX product copy **75/25** is **not** Wilder law (`context-dependent` heuristic). |
| **HQ** | Trigger **`RSI_14` only**. Wilder vs Cutler (SMA-RSI): **UNKNOWN** in Dhan docs. |
| **Match?** | Using *n*=14 + band 30 as Wilder’s usual framing = `supported` as **default convention**. Treating 55–70 as “the Dhan RSI law” = `unsupported`. Divergence = **pattern**, not a proven predictor (`context-dependent`). Printed screen values in H_6kee = `[UNCERTAIN_TRANSCRIPT]`. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Compute RSI_14 from index/futures close. Stock-screener bands do **not** transfer. Strong trend: “overbought” can persist (`known failure`). |

---

## EMA / SMA / DEMA

| | |
|--|--|
| **Spoken** | See packet MA-01…MA-10. Recurring: **10/20**, **10/30/100**, **9/30/100**, **5 / 15 / 50**, **20/50/200**, DEMA **100**, Super Scalper **fast/slow UNKNOWN**. |
| **Math (VALIDATION)** | SMA_n = mean of last *n* closes. EMA: common α = 2/(n+1); seed = SMA or first close (**UNKNOWN** in Dhan docs). DEMA = 2·EMA − EMA(EMA) (Mulloy) — `supported` as a definition; **not** in annexure. |
| **HQ** | `SMA_n` / `EMA_n` for *n* ∈ **{5,10,20,50,100,200}** as **trigger names**. **`EMA_9` absent.** No SMA_15, SMA_30, EMA_21, DEMA. |
| **Match?** | 10>30>100 as a **trend heuristic** = `supported` as definition, **no optimality**. 9 vs 10, 100 vs 300, 20 vs 21 = `SOURCE_UNCERTAIN`. Sending `EMA_9` to Conditional Trigger = `unsupported` (not a documented token). Super Scalper lengths = `UNKNOWN`. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Compute spoken lengths from OHLC. Dual-TF HAUS stack on **underlying**, not on random OTM premium unless a separate spec says so. 2m/3m bars: HQ enum lacks them → resample `UNKNOWN`. |

---

## MACD

| | |
|--|--|
| **Spoken** | **12 and 26** (`HAUSZx` 45:54–45:56). Then **×3 or ×4** “all” params (`HAUSZx` 45:37–45:42) `[UNCERTAIN_TRANSCRIPT]`. Histogram-only after dropping lines. `6E_K1wVkHyw`: **24 and 52** instead of 12/26 (≈ **2×**). `_byuht38r5s`: histogram **> 0**, “default” params unnamed. Signal length **not clearly spoken** in HAUS. |
| **Math (VALIDATION)** | Appel: MACD = EMA_fast(close) − EMA_slow(close); signal = EMA_sig(MACD); hist = MACD − signal. Common **12/26/9**. Linear period scaling is a **filter choice**, not a theorem (`context-dependent`). Hist>0 often ≈ MACD>signal (`partially_supported` as a regime label). |
| **HQ** | `MACD_12`, `MACD_26`, `MACD_HIST`. **No** `MACD_9` / `MACD_SIGNAL`. Histogram construction **UNKNOWN** without documented signal length. |
| **Match?** | 12/26 as Appel fast/slow = `supported` **if** close-based EMA. Exact 4× (48/104/36 **if** 9×4) = `UNKNOWN`. 24/52 = a **different spoken recipe** than HAUS ×4. Do not merge them. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Compute one **named** variant per backtest ID. HAUS uses MACD as **child-TF entry filter**; desk staging uses 5m MACD as **confirm-or-kill** — those are **different hypotheses**. |

---

## VWAP / VWMA / day snapshot

| | |
|--|--|
| **Spoken** | Session VWAP on **futures** (`2RnBT9`, `pUg_7sPauQA`). VWMA **length 20** (`2RnBT9`). Spot NIFTY “VWAP” in pUg is **demo only** — speaker: trade VWAP where **volume is real**. AVWAP from a dated anchor (`eApl0SfVBBY`) = product. |
| **Math (VALIDATION)** | Session VWAP = Σ(P·V)/ΣV from session open (typical price P often HLC/3 or trade price — **UNKNOWN** which Dhan charts use). VWMA_n = Σ(P·V)/ΣV over *n* bars ≠ session VWAP. Cash **NIFTY 50 index is not a traded tape** → VWAP on cash index = **`unsupported` / misuse**. |
| **HQ** | Quote `average_price` = “Volume weighted average price **of the day**” (`partially_supported` as a **snapshot**). WS **ATP** vs `average_price` vs chart VWAP: **UNKNOWN**. No VWAP/VWMA annexure names. |
| **Match?** | Futures/option-tape VWAP math = `supported`. Index-spot volume VWAP = `unsupported`. Identity of REST snapshot vs chart session VWAP = `UNKNOWN`. |
| **Index options (HYPOTHESIS UNVALIDATED)** | ST+VWAP+VWMA(20) on **FUTIDX** (`2RnBT9`) is the only **index-named** VWAP system in the English set. 3m = resample hypothesis. |

---

## Price action / structure

| | |
|--|--|
| **Spoken** | Big candles “king makers”; HH/HL; 50% of 09:15 candle (`wpdqqXhhq88`). Open=low / open=high (`PUkzVgVPCf0`). Liquidity sweep then engulfing (`pUg_7sPauQA`). VCP named. |
| **Math (VALIDATION)** | No unique equation. HH/HL is a **definition of a swing trend**, not a predictor (`supported` as language, `unsupported` as edge). 50% of a range is a **midpoint**, not a theorem. Open=low on a **stock** is an auction/print identity; on a **cash index** it is a **constructed** first bar (`context-dependent` — 03_phd_market). |
| **HQ** | OHLC candles only. |
| **Match?** | Implementable from OHLC. No REST “PA score.” |
| **Index options (HYPOTHESIS UNVALIDATED)** | Structure on futures → option as vehicle. Do not treat stock open=low scanners as NIFTY CE/PE rules. |

---

## Candlesticks

| | |
|--|--|
| **Spoken** | Five patterns in `njqeZc_tYy8` (hammer, bullish engulfing, morning star, dark cloud cover, inside bar) with **confluence required**. Hammer wick **2–3× body** `[UNCERTAIN_TRANSCRIPT]`. Auto-detect product (`wDZXqzdGBDc`) with EMA 50 / 50+200 filter — **tool**. |
| **Math (VALIDATION)** | Pattern geometry is **definitional** (`supported` as pattern language). Predictive power = `unsupported` without a test. “Leading vs lagging” is **pedagogy**, not a sampling-theory result (`context-dependent`). Inside bar = **context-dependent** (speaker said so). |
| **HQ** | No pattern series. Charts = OHLC. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Detect on futures OHLC. Confluence (trend + S/R + optional RSI_14<30) as a **joint** hypothesis, not five independent edges. |

---

## Opening range

| | |
|--|--|
| **Spoken** | ORB product; speaker setting **09:15–10:00** (`eApl0SfVBBY`). Others: **09:15–09:30**, **09:15–09:45**. `2RnBT9`: **ignore** 09:15–09:45. `HAUS`: new entries **after 10:00**. `MfGUybW4O4c`: first 5/15/30 min = **noise**; skip 15m if new. |
| **Math (VALIDATION)** | Opening range = high/low of a **chosen IST window**. Breakout = close or trade beyond that box. **No unique window** in the corpus → `UNKNOWN` which T is “Dhan’s ORB.” |
| **HQ** | **No ORB REST.** Intraday intervals 1/5/15/25/60. |
| **Match?** | Box from 1m/5m OHLC = `supported` as construction. Treating one T as official = `unsupported`. |
| **Index options (HYPOTHESIS UNVALIDATED)** | Parameterize T ∈ {15, 30, 45, 10:00} as **separate** tests. Flatten vs CAS/F&O close = **03_phd_market** (`UNKNOWN` 15:15 spoken vs 15:30/15:40 docs). |

---

## Williams %R (named; not a Phase-1 owner)

`6E_K1wVkHyw` ~06:01–06:19: Williams %R period spoken **140**, extremes **−5** and OS `[UNCERTAIN_TRANSCRIPT]`. HAUS names Williams %R without params. **VALIDATION:** Larry Williams %R typically period 14, scale −100..0. Period 140 is a **smoothing choice**, not the textbook default (`context-dependent`). Not an annexure name. Record only so 04 does not invent 14 as “what Dhan used in 6E.”

---

## Hull / ATR trail / CPR / Darvas (product — not HQ series)

| Spoken | VALIDATION | HQ |
|--------|------------|-----|
| Hull MA “adapts” (`eApl0SfVBBY`); Hull “32” (`G31RFueZLvk`) `[UNCERTAIN_TRANSCRIPT]` | Hull MA is a defined smoother (Hull). “Adapts period automatically” as spoken is **`partially_supported`** — classic Hull uses a **fixed** length with WMA/sqrt(n), not a vol-adaptive *n*. | Not in annexure |
| ATR trailing stop, multiplier **5** as *example* (`eApl0SfVBBY` 09:08–09:10) | Wilder ATR; trail = price − k·ATR. *k*=5 is an **example**, not a default. HQ `ATR_14` is a **trigger name**. | Chart product |
| CPR daily/weekly/monthly (`eApl0SfVBBY`) | Central Pivot Range is a pivot construction (`supported` as geometry). | Chart-only |
| Darvas Box (`EVk_Wa_1cm0`) | Box/breakout **definitional**. **Skip** as promo for this TA packet. | Chart-only |

---

## Volume delta vs Greek delta

`YUXJv_xBStw`: per-candle **delta = buy volume − sell volume**. **VALIDATION:** `supported` as microstructure. **Different symbol** from option **Greek** delta. Do not collapse. OF strategy rules are **not** this file.

---

## Spoken vs VALIDATION — cheat sheet

| Item | SOURCE_FACT (spoken) | VALIDATION | Do not ship as |
|------|----------------------|------------|----------------|
| Supertrend 10,3 | Repeated “default” | Common TV default; not HQ | `indicatorName` |
| Supertrend 7,3 | One ASR line | `SOURCE_UNCERTAIN` | Frozen param |
| RSI 14 | `_byuht` named | Wilder common *n* | Series REST |
| RSI 30 / 70 | H_6kee / njqe / folklore | Wilder bands | ScanX 75/25 as law |
| MACD 12/26 | HAUS | Appel fast/slow | Signal=9 as “Dhan said” |
| MACD ×3/×4 | HAUS, conflict | Filter choice | One true scale |
| MACD 24/52 | 6E | ≈2× Appel | Same as HAUS ×4 |
| EMA 10/20 | pvm, mPK | Standard EMAs | 2m as HQ interval |
| EMA 9 | PUkz / HAUS trail | α=2/10 convention | Annexure `EMA_9` |
| MA 10/30/100 vs 300 | HAUS | Heuristic | Frozen stack |
| VWMA 20 | 2RnBT9 | Defined | Cash-index VWAP |
| Super Scalper EMA | Fast/slow, 1m premium | `UNKNOWN` lengths | Invented 9/21 or 8/21 |
| ORB window | Several IST boxes | Construction only | One official ORB |
| 3m / 2m / 9m | Spoken | Not in HQ enum | Official `interval` |

---

## Compute path (later; not this ticket)

Official **inputs:** `POST /charts/historical`, `POST /charts/intraday` (1, 5, 15, 25, 60).  
Official **named triggers:** `/alerts/orders` — **not** a historical series; **Equities and Indices** only; **do not** live-trade.

If Dhan **chart** Supertrend ≠ ATR(10)×3 close-flip: record `partially_supported` / `SOURCE_UNCERTAIN`. Do **not** silent-swap libraries.

`packages/indicators` empty is **correct** until review.

---

## Open UNKNOWN (math + speech)

- ScanX / tv.dhan.co Supertrend ATR period, multiplier, HL2 vs close.  
- `_byuht` “7 is 3” vs 10,3.  
- MACD signal length on Dhan charts; HAUS ×3 vs ×4 exact integers.  
- Super Scalper fast/slow EMA periods.  
- EMA / RSI seed and Wilder vs SMA-RSI on Dhan.  
- `average_price` vs ATP vs chart VWAP.  
- 2m / 3m / 9m resample method.  
- Which opening-range **T** (if any) to test first.

---

## Handoff

- **01** owns quotes: [`TA_STRUCTURE_PACKET.md`](../../01_research/docs/handoffs/TA_STRUCTURE_PACKET.md).  
- **03** owns clocks / SENSEX=BSE / VWAP-on-index: [`VALIDATION_MARKET.md`](../../03_phd_market/docs/VALIDATION_MARKET.md).  
- **04** may cite this as `HYPOTHESIS` / `UNVALIDATED` on **existing** STRAT-001–014. **No new STRAT IDs** from this coalition. **No win rates.**  
- Nightly `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`. A new English quote is **not** a live Supertrend/MACD retune.

Coalition ticket: [`TASK_TRANSCRIPT_COALITION.md`](../../00_orchestrator/docs/TASK_TRANSCRIPT_COALITION.md).

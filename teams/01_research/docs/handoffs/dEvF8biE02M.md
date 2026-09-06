# SOURCE_FACT — `dEvF8biE02M` (swing multi-year ATH breakout)

**Status:** `EXTRACTED` (layer A, second pass 2026-09-03). `DRAFT` / `WAITING_FOR_EDIT`.  
**Slice:** `EQUITY` **positional / swing** cash. **Not** Phase-1 index-options evidence.

| Field | Value |
|-------|--------|
| video_id | `dEvF8biE02M` |
| title | FREE Masterclass: Swing Trading Multi-Year Breakout Strategy Revealed! |
| url | https://www.youtube.com/watch?v=dEvF8biE02M |
| retrieved_at | 2026-09-01T19:51:36Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/dEvF8biE02M.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | none on EN file header; still treat % and names as high-risk |
| duration | ~54 min |
| guests | Host + **Kundan** |

Spoken **100–200% / 100% in 2 years** is **guest capability / definition language**, not a verified return. Chart names are **education**, host repeats not a buy/sell recommendation (~28:22–28:40). **No win rates.**

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim (paraphrase of English) | type |
|----------|-----------|-------------------------------|------|
| DEV-C01 | 00:06–00:36, 08:38–09:09 | Start with swing; wealth via stocks/investing. Guest: technical setups can have **up to 100–200%** “capability”; **multibagger** here = **≥100% in 2 years** (not 1000%). **Not a backtest.** | opinion |
| DEV-C02 | 06:45–07:00, 07:43–07:58 | Guest: ~**30% of capital** in swing; hold **6–8 months** possible. Distinguishes 2–5% one-week exits (called swing by others) from this **positional** hold. | process |
| DEV-C03 | 07:20–07:32 | Session agenda: selection, entry, target, SL, **trailing SL**, case studies. | process |
| DEV-C04 | 09:21–09:51 | Problem: **breakout vs fakeout**. Speaker will not claim 100% accuracy; if you had **50%**, rules might add ~**10% → 60%**. **Opinion, not a study.** | opinion |
| DEV-C05 | 10:37–10:51 | Guest: **no fancy indicators**; reads **price and volume** only (trail EMA is later). | method |
| DEV-C06 | 10:57–13:29 | Pattern: **multi-year horizontal consolidation**, **minimum ~5 years**, resistance at **all-time high** (not a crushed stock consolidating at the bottom). Entry on **ATH range breakout**, not mean-reversion. “Buy high, sell higher.” Cap-size: **any stock**. | rule-as-spoken |
| DEV-C07 | 13:52–16:07 | Breakout needs **strong volume**. Fakeouts: tiny close **10–20%** above the line; or close with **long upper wick** (profit-taking on the breakout bar); or clean body **without volume**. Spoken: body **≥ ~40%** above resistance; volume spike ~**+40%** vs average (1.0M → 1.4M toy). `[UNCERTAIN_TRANSCRIPT]` on 40% body vs 40% volume. | rule-as-spoken |
| DEV-C08 | 17:15–18:42, 19:16–19:53, 24:34–25:02 | **Delivery %** on the breakout: want **>~40–45%** of volume as delivery (NSE / bhav copy). Spike with **<40%** delivery = weaker candidate. Whole recipe nicknamed **“40%”** (~24:58). | rule-as-spoken |
| DEV-C09 | 25:41–26:03 | Prefer **wait for monthly candle close** (month-end / 30–31) rather than jumping mid-bar; missing 2–3% in two days is ok vs large targets. | clock |
| DEV-C10 | 26:12–26:40 | **Stop:** breakout-candle **low minus 1% of that low** (₹100 low → ₹99; ₹1000 → ₹990). | rule-as-spoken |
| DEV-C11 | 26:53–28:16 | Two target modes: **range-height** first target, then **trail**. At **~30–50%** open profit, exit **50%** quantity, move rest toward **cost**. First target = **width of the 5-year range** added **above the breakout**. Measure **points**, not % (~28:59). | rule-as-spoken |
| DEV-C12 | 30:07–31:00 | **Trailing SL after T1 only.** Weekly **21 EMA**: **two consecutive** weekly closes **below** 21 EMA → exit. First close below = watch only. | rule-as-spoken |
| DEV-C13 | 31:40–31:48 | Charts for structure: **monthly**; trading/trail: **weekly**. | TF |
| DEV-C14 | 39:55–40:09 | Rules “save” some fakeouts; SL will still hit; 50%→60% is **speech**. | opinion |
| DEV-C15 | 40:15–41:16 | Selection aid: **ScanX** weekend **52-week high breakout** screener (price & volume). Optional unusual-volume filter. Then **manually** check delivery on NSE/bhav — ScanX list is **not** the full 5-year ATH rule. **Product UI.** | product / process |
| DEV-C16 | 28:22–28:40 | Host: named stocks **not recommendations**; education only. | disclaimer |

---

## Indicators (params as spoken)

| Name | Params as spoken | TF | Use |
|------|------------------|----|-----|
| (none at entry) | price + volume + delivery | monthly structure | breakout |
| EMA | **21** | **weekly** | trail after T1 only |

RSI / Supertrend / MACD **not** the entry stack in this video.

---

## Data requirements

```text
DATA_SOURCE: NSE cash + delivery (bhav); ScanX only as a 52w-high shortlist
INSTRUMENT: cash equity (positional)
CALCULATION: 5y range high/low; breakout close vs ATH; volume vs ~6m average; delivery %
TIMEFRAME: monthly structure, weekly trail
```

---

## Handoff

**04:** `EQ-014` — `UNVALIDATED`. Do **not** treat as the 10-episode Swing Trading Series (`EQ-011` still `TRANSCRIPT_PENDING`). Do **not** copy 100%/2y into a performance table.  
**02/03:** 40% body vs 40% volume vs 40% delivery — three different 40s; delivery definition vs NSE series.  
**Must not:** code a ScanX bot; mix into STRAT-001–014.

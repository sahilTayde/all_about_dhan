# SOURCE_FACT — `_byuht38r5s` (Intraday Rockers ScanX)

**Status:** `EXTRACTED` (layer A). `DRAFT` / `WAITING_FOR_EDIT`.  
**Slice:** `EQUITY` / ScanX **product** walkthrough. **Not** Phase-1 index-options evidence.

| Field | Value |
|-------|--------|
| video_id | `_byuht38r5s` |
| title | Intraday Trading Strategy with FREE Screener \| Find Trades in Minutes |
| url | https://www.youtube.com/watch?v=_byuht38r5s |
| retrieved_at | 2026-09-01T19:53:55Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/_byuht38r5s.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |
| relevance | HIGH / scanner (catalog) |

Education ≠ advice. Chart-day % moves are **that morning’s tape**, not a sample. **No win rates.**

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim (paraphrase of English) | type |
|----------|-----------|-------------------------------|------|
| ROCK-C01 | 00:26–00:28 | **Not** investment advice / recommendation. | disclaimer |
| ROCK-C02 | 00:35–00:37 | Screener built on ScanX (ASR “money scanix”). **Product UI, not a backtest.** | product |
| ROCK-C03 | 01:14–01:16 | Run **intraday at 9:20**. | clock |
| ROCK-C04 | 01:53–01:55 | Recording-day Nifty “slightly positive.” **Regime of the tape, not a study.** | snapshot |
| ROCK-C05 | 02:03–02:05 | Saved name: **Intraday Rockers**. | product |
| ROCK-C06 | 03:01–03:27 | Filter: **close > EMA 20**. | rule-as-spoken |
| ROCK-C07 | 03:45–03:57 | Filter: **close > Supertrend**. Spoken default **“parameter 7 is 3.”** `[UNCERTAIN_TRANSCRIPT]` — conflicts with 10,3 elsewhere. **Do not freeze 7,3.** | indicator |
| ROCK-C08 | 04:09–04:23 | **14-period RSI** between **55** and an overbought upper bound (cut / messy). `[UNCERTAIN_TRANSCRIPT]` | indicator |
| ROCK-C09 | 05:15–05:26 | **Today’s volume > 2× last-10-day average.** | rule-as-spoken |
| ROCK-C10 | 06:01–06:39 | **MACD histogram bullish.** | indicator |
| ROCK-C11 | 07:17–07:20, 07:55 | **Today’s % change > 0.5%.** | rule-as-spoken |
| ROCK-C12 | 07:32–07:35 | Also spoken “trading above the **21 EMA** in the long term” vs EMA 20 earlier. **Conflict.** `[UNCERTAIN_TRANSCRIPT]` | indicator |
| ROCK-C13 | 08:46–09:02 | Exit anecdote: book ~**0.6–0.7%** intraday; partial ~**10–15%**; **60–65%** scale-out if 100 shares. **Not a backtest.** | anecdote |

---

## Indicators (params as spoken)

| Name | Params as spoken | TF | Use |
|------|------------------|----|-----|
| EMA | 20 (also 21 later) | unnamed / ScanX | trend filter |
| Supertrend | “7, 3” default `[UNCERTAIN]` | unnamed | close above |
| RSI | **14**; band 55–(upper cut) | unnamed | momentum |
| MACD | histogram bullish; length unnamed | unnamed | confirm |

---

## Handoff

**04:** `EQ-005` in [`EQUITY_ETF_BACKLOG.md`](../../../04_quant/docs/candidates/EQUITY_ETF_BACKLOG.md) — `UNVALIDATED`. Do **not** merge with EQ-001 (Alpha 09:45) or EQ-002 (IMB).  
**02:** Supertrend 7×3 vs 10×3; EMA 20 vs 21; RSI upper bound.  
**Must not:** treat ScanX share as HQ REST; invent the missing RSI cap; copy into STRAT-001–014.

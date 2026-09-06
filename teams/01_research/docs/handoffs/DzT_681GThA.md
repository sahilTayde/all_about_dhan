# SOURCE_FACT — DzT_681GThA (order flow A–Z)

**Status:** `EXTRACTED` (layer A). `DRAFT`. Product + four spoken “rules.”  
**Not** a complete CE/PE strategy. Demo chart is **Reliance**, not NIFTY options.

| Field | Value |
|-------|--------|
| video_id | `DzT_681GThA` |
| title | A to Z Order Flow Trading Guide: Complete Strategy REVEALED! |
| url | https://www.youtube.com/watch?v=DzT_681GThA |
| retrieved_at | 2026-09-01T19:56:52Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/DzT_681GThA.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` (volume prints) |
| relevance | HIGH / VOLUME, STRATEGY_DESIGN (catalog also tags GREEKS — **wrong sense of “delta”**) |
| platform | Dex T3 order-flow widget |

---

## Critical disambiguation

**Order-flow delta** here = executed buy volume − executed sell volume.  
**Not** option Greek delta. Do not feed this into STRAT-005 / pvmvki delta bands.

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim | type |
|----------|-----------|-------|------|
| OF-C01 | 00:05–00:54 | Follow-up after launching OF on Dex. How to use Dex T3 OF end-to-end (Widgets → Order Flow). Prior videos on footprint / profile / TA vs OF (links in description — not extracted here). | product |
| OF-C02 | 01:27–01:50 | Demo candle: **Reliance**. Left column = **executed** sell volume; right = executed buy. Explicitly **not** bid/ask. | definition |
| OF-C03 | 02:23–02:54 | Delta = total buy − total sell. Example 168−64 ≈ 105–106; also spoken “+106k.” `[UNCERTAIN]` | definition + example |
| OF-C04 | 03:01–03:55 | **Cumulative delta** newly live on Dex T3 = sum of session candle deltas. + = buyers dominated the day; − = sellers. Reliance example “plus 2.7 million.” `[UNCERTAIN]` | product |
| OF-C05 | 04:15–04:40 | Click candle: OHLC, volume. Volume = buy+sell (example 173.9+67.2 → 241.1K). Delta ≠ volume. `[UNCERTAIN]` | definition |
| OF-C06 | 05:28–06:37 | **POC** = price with highest **combined** buy+sell volume in that candle. Use: confirmation at breakout/S/R; candle may close below while volume clustered above. | definition / heuristic |
| OF-C07 | 07:12–07:44 | Volume **profile** = volume by price (vs time-wise volume on a 5m bar). Also keeps time-wise volume. | education |
| OF-C08 | 07:59–08:44 | **VAH / VAL**: **70%** of that candle’s volume between the yellow lines. POC expected inside. | definition |
| OF-C09 | 09:22–11:50 | Imbalance if buy vol ≥ **3×** previous level’s sell vol (or sell ≥ 3× previous buy). Stacked imbalances = buyers or sellers dominating; can “validate” a normal-chart breakout. | heuristic |
| OF-C10 | 12:08–12:51 | Settings can hide delta, candles, VWAP, cumulative-delta bars, volume bars. Imbalance ratio user-set (3 / 10 / 20 demo). | product |
| OF-C11 | 13:17–14:02 | **Absorption:** red candle can still be buyer-dominated. Next candle completed the story (buyers closed at high). | education |
| OF-C12 | 14:04–14:26 | VWAP on the chart = session volume-weighted average. Cumulative-delta histogram vs normal volume bars. | product |
| OF-C13 | 15:05–16:50 | Compare to “normal” chart: daily S/R → 15m → 5m (peek 3m) for intraday/scalp. Reliance downtrend / 1600 / 1255 / 1340 examples. `[UNCERTAIN]` prices | method |
| OF-C14 | 17:16–18:30 | Counted negative-delta 5m candles; claimed **11 of 75** (09:15–15:30 → 75 five-minute bars). `[UNCERTAIN]` count | example |
| OF-C15 | 18:35–19:27 | Price falling while aggressive buys hit the ask = passive limit sellers (**bearish absorption**) **or** bullish divergence (price LL, delta HL). Cannot trade OF **or** TA alone. | education |
| OF-C16 | 19:29–20:07 | Four rules (context first): price↑δ↑ strong bull; price↓δ↓ strong bear; price↑δ↓ bearish div / buyer absorption; price↓δ↑ bullish div / seller absorption. | rule-as-spoken |

---

## What is NOT in the transcript

No NIFTY/BANKNIFTY/SENSEX option, strike, expiry, CE/PE, premium stop, or lot.  
No HQ REST field list. Historical OF on DhanHQ: `DATA_INSUFFICIENT` until 02/03 prove a series exists.

---

## Data requirements

```text
DATA_SOURCE: Dex T3 order flow (product) — not proven on DhanHQ historical REST
INSTRUMENT: traded stock or index **futures** (volume exists). Not cash-index NIFTY volume.
EXCHANGE_SEGMENT: NSE cash demo (Reliance); project overlay would be index futures
CALCULATION: buy vol, sell vol, delta, cum delta, POC, VAH/VAL 70%, imbalance ratio (default 3)
TIMEFRAME: demo 5m (also 3m/15m/daily for context)
```

---

## Handoff

**02:** volume-delta math vs Greek delta; 70% value area; 3× imbalance.  
**03:** session 09:15–15:30 → 75×5m; futures vs cash volume.  
**04:** STRAT-010 overlay only; `UNVALIDATED`; do not invent an options entry from this file.

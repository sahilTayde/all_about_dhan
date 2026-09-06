# SOURCE_FACT (English) — HAUSZx-hYdY

**Status:** `EXTRACTED` (layer A). `DRAFT` / `WAITING_FOR_EDIT`.  
**Companion:** Hindi ASR packet [`HAUSZx-hYdY.md`](HAUSZx-hYdY.md) **not overwritten.** Prefer this English file for numbers.  
**Do not treat as strategy, advice, or validated edge.**

| Field | Value |
|-------|--------|
| video_id | `HAUSZx-hYdY` |
| title | The Ultimate 1-Hour Masterclass on Option Buying Strategies \| Option Trading Strategy \| Dhan |
| url | https://www.youtube.com/watch?v=HAUSZx-hYdY |
| retrieved_at (EN) | 2026-09-01T19:55:43Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/HAUSZx-hYdY.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |
| relevance | HIGH / OPTIONS, OPTION_CHAIN, VOLATILITY, GREEKS, RISK_MANAGEMENT, STRATEGY_DESIGN |
| guests | Host + Himanshu Arora (“star trader”) |

**Disclaimer spoken:** NIFTY / stock names are examples; not recommendations (~09:18).

**QA:** English is YouTube’s translation of Hindi. Numbers still `[UNCERTAIN_TRANSCRIPT]`. Do not silently “correct.”

---

## Topics (from English transcript)

OPTIONS, OPTION_CHAIN, CE/PE, ITM/ATM/OTM, INTRINSIC/TIME VALUE, DELTA, THETA, IV, OI, EXPIRY, LIQUIDITY, DUAL_TIMEFRAME, MACD, MOVING_AVERAGES, RISK, INTRADAY.

---

## Claims (layer = SOURCE_FACT)

See coalition table **HAUS-EN-01 … HAUS-EN-19** in [`OPTIONS_INDEX_PACKET.md`](OPTIONS_INDEX_PACKET.md). Highlights:

- Buyer vs seller payoff (~00:07–00:14).
- Host 93% / 7% statistic — **not independently sourced** (~01:41–01:45).
- No holy-grail 99% strategy (~00:44–00:51).
- Bullish → buy call; bearish → buy put (~08:31–08:48).
- NIFTY strikes in **50-point multiples**; exchange sets strikes (~13:10–13:14).
- Screen NIFTY ~24827 `[UNCERTAIN]` (~10:51).
- Dated expiries: 19 Jun (recording day), next Thursday, 26 Jun / 3 / 10 / 17 Jul (~15:35–16:42). **Do not freeze.**
- Dual TF: hourly parent + 5 **or** 10 minute child (~42:30).
- MACD with “increased” parameters + MA 10/30/100; recap also **300**; exit **9**-period vs 30 `[UNCERTAIN]` (~45:07–59:26, 56:24, 01:02:15).
- Session: after 10:00, mostly not after 14:30, not after 15:00 (~55:18–01:00:35).
- Slightly **OTM**; ~20–30% premium target; ~40 delta adverse case (~57:26–01:01:05).
- Universe: **NIFTY 100 stocks** + liquidity — **not index-only** (~43:14–44:12).

---

## Strategy rules as spoken (still SOURCE_FACT)

| field | spoken (English) |
|-------|------------------|
| Parent TF | Hourly |
| Child TF | 5 or 10 minutes |
| Preferred horizon | Intraday (theta “hardly” hurts); not purely forced — BTST if decided before entry |
| MACD | Default 12/26 mentioned in Hindi file; English: “increases the MACD parameters”; histogram / green-red. Exact 4× of 12/26/9 = `UNKNOWN` |
| MA stack | 10, 30, 100; also “30 and 300”; exit 9-period vs 30 |
| Entry | After 10:00 and before 14:30: child MACD bullish **and** 10/30/100 bullish; buy **above that candle’s high**; slightly OTM. Mirror for puts |
| Stop | Time stop EOD if used intraday; indicator 9/10 vs 30 or MACD flip; **ultimate stop = underlying swing low**, not option chart |
| Target | ~20–30% option value |
| Lot | Exchange-set; no eternal number |

Speaker ROI anecdotes on ~0.5–1% underlying moves are **not** backtests.

---

## Handoff

Validate: Greek definitions; strike step 50; expiry calendar now vs recording; MACD/MA conflicts. 04 may keep STRAT-001/002/007 as `UNVALIDATED` only.

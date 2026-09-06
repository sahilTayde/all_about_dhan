# SOURCE_FACT — `4TT8IV5S1_A` (pullback / buy-the-dip ScanX)

**Status:** `EXTRACTED` (layer A). `DRAFT` / `WAITING_FOR_EDIT`.  
**Slice:** `EQUITY` / ScanX **product**. **Not** Phase-1 index-options evidence.

| Field | Value |
|-------|--------|
| video_id | `4TT8IV5S1_A` |
| title | (catalog) buy-the-dip / pullback screener |
| url | https://www.youtube.com/watch?v=4TT8IV5S1_A |
| retrieved_at | 2026-09-01T19:54:00Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/4TT8IV5S1_A.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | treat numbers as `[UNCERTAIN_TRANSCRIPT]` |
| published | 2026-06-16 |

Education ≠ advice. Example names and “~13% in 2 days” are **anecdotes**. **No win rates.**

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim (paraphrase of English) | type |
|----------|-----------|-------------------------------|------|
| DIP-C01 | 00:14–00:43 | Thesis: pullback in an uptrend can offer closer stop / farther target. **Unknown** whether a dip is reversal vs pullback. | education |
| DIP-C02 | 01:05–01:09 | Comment CTA: request “pullback screener.” | product |
| DIP-C03 | 02:18–02:52 | Tools: **Dhan Charts + ScanX.** | product |
| DIP-C04 | 03:10–04:04 | Uptrend filters: **price > 50 EMA**; **20 EMA > 50 EMA**; **50 EMA > 200 EMA**. | rule-as-spoken |
| DIP-C05 | 04:49–04:57 | Pullback: last-two-weeks % change example **−10% to −5%**. Speaker: **no set criteria** — change the number. | rule-as-spoken |
| DIP-C06 | 05:10–05:25 | Optional **RSI 40–55** (also spoken 40–50). `[UNCERTAIN_TRANSCRIPT]` | indicator |
| DIP-C07 | 05:58–06:03 | Optional **market cap ≥ ₹5000 crore**. | filter |
| DIP-C08 | 06:22–06:54 | **Do not buy only because it is in pullback.** Trigger: **30-minute** chart **5 MA > 15 EMA > 50 EMA**. RSI “not needed” at trigger (~06:41–06:43). | rule-as-spoken |
| DIP-C09 | 08:28–09:12 | Example names (SMS Pharma and others) and “~13% in 2 days.” **Anecdote / `[UNCERTAIN]` names**, not a sample study. | anecdote |

---

## Indicators (params as spoken)

| Name | Params as spoken | TF | Use |
|------|------------------|----|-----|
| EMA stack | 20 > 50 > 200; price > 50 | daily / ScanX | uptrend |
| RSI | 40–55 optional | unnamed | pullback band |
| MA / EMA | 5 MA > 15 EMA > 50 EMA | **30-minute** | trigger |

---

## Handoff

**04:** `EQ-004` — `UNVALIDATED`.  
**Must not:** freeze −10/−5 two-week band; treat 13% as expectancy; transfer the 30m 5/15/50 stack into NIFTY CE/PE without a new labeled `HYPOTHESIS`.

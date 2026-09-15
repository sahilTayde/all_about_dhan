# Exam note — delta (CE/PE buy-first; not a win rate)

**Layer:** `VALIDATION`  
**Chair:** phd_math · **NO_PROMOTE**

## What the oral wants

Delta is the **first-order** sensitivity of option value to the underlying. A NIFTY CE delta is typically **positive**; a PE delta is **negative**. “1–2 strikes ITM” in teacher talk is a **spot moneyness fallback** when greeks are missing — not a probability of profit.

Delta ≠ P(win). Deep ITM “not that much logic” in a transcript is **speaker opinion**, not a theorem.

## Tokens for FTS

delta, moneyness, ITM OTM ATM, greeks.delta, win rate forbidden, spot fallback, CE positive PE negative

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| Δ ≈ N(d1) under BS | We do **not** invent BS delta without validated IV + rates + time |
| Vendor delta | Store `greeks.delta` from chain; stale between **3m** polls |
| WS / LTP | **No** greeks on WS — do not interpolate a live Δ |
| Strike pick | 005-class tickets need chain/greeks **or** documented spot-ITM fallback |
| MIX-FORM k | OLS \(k\) in return space ([`INDEX_CE_PE_EDA.md`](../../INDEX_CE_PE_EDA.md)) is **not** delta |

**Compute:** moneyness = spot vs strike (known). Hedge ratio only if 02 writes a named model **and** 06 OOS+NORMAL — not today.  
**Null HQ greeks:** leave null; spot-ITM map is the honest fallback.

## DATA_INSUFFICIENT

Trusted **delta time series** for OPTIDX sids is not a day-1 warehouse identity. Do not train ML on invented Δ. Holiday EDA used **percent returns**, not delta.

## Exam trap

Publishing “delta 0.5 so 50% chance.” That sentence **fails** the oral and the compliance desk.

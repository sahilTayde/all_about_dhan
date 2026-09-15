# Exam note — vega, implied vol vs realized vol

**Layer:** `VALIDATION` + `HYPOTHESIS`  
**Chair:** phd_math · **NO_PROMOTE**

## What the oral wants

**Vega** is sensitivity of the option mark to **implied** volatility. **IV** is the insurance price quoted **in vol units**. **Realized vol** is what the index **did** (close-to-close, Parkinson, etc.). They are **different objects**. Long premium wins when realized (and/or IV mark-up) outruns the premium paid — not when a blog says “IV crush.”

Smile/skew: two strikes are **different** IVs. One ATM number is not the surface.

## Tokens for FTS

vega, implied vol, realized vol, IV crush, MIX-FORM-STRADDLE-RET, volatility smile, DATA_INSUFFICIENT IV series

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| Need IV surface | HQ `implied_volatility` on chain snapshot — **not** a trusted continuous series |
| Vega P/L | Cannot mark vega P/L without a validated IV path |
| Realized proxy | Index 1m/5m squared returns; **not** IV |
| Dual-tape straddle | `MIX-FORM-STRADDLE-RET` = r_CE + r_PE = **crude vol-of-day proxy**, not Dupire, not vega |
| NEWS_DAY | Extreme PCR / news = **hold the ticket**, not “sell vol” (we are buy-first) |

**Compute:** realized vol from INDEX OHLC we actually have.  
**Do not invent:** IV, variance swap, or a smile fit from LTP alone.

## DATA_INSUFFICIENT

No validated **IV series** aligned to INDEX 1m on the holiday cache (INDEX ends 2026-09-03 14:19; ATM tape 09-09..11 ∩ INDEX = 0). Until chain IV is stored **and** checked against `rollingoption` / quote, any “IV vs RV” trade is `DATA_INSUFFICIENT`. Missing IV ≠ 0.

## Exam trap

`MIX-FORM-STRADDLE-RET` > 0 is **not** “IV expanded.” Both premiums can rise from a gap, sticky quotes, or a bad print.

# Exam note — intrinsic value vs time value (CE/PE)

**Layer:** `VALIDATION`  
**Chair:** phd_math · **NO_PROMOTE**

## What the oral wants

**Intrinsic** (European-style index options, cash-settled class):  
- CE: max(spot − strike, 0)  
- PE: max(strike − spot, 0)  

**Time value** (extrinsic) = premium − intrinsic (floored at 0 if the quote is through; a through-market is a **data** problem, not a free arb in this book).

OTM: premium ≈ all time value → **pure theta food**. ITM: premium = intrinsic + remaining insurance. Deep ITM still has **some** extrinsic unless expiry is immediate.

Buy-first: we pay **intrinsic + time**. A “cheap OTM” is cheap because **intrinsic is zero**, not because edge is positive.

## Tokens for FTS

intrinsic, time value, extrinsic, ITM OTM ATM, premium residual, moneyness, CE PE, NIFTY SENSEX

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| Intrinsic from spot + strike | INDEX/FUT last vs contract strike — **do** compute |
| Time value | last_price − intrinsic; if last missing → null |
| Champion ITM PE near spot | Paper board preference is **moneyness**, not a proven edge |
| Frozen CE print (23350 / 670.85) | Intrinsic math on a **stuck** last is `DATA_INSUFFICIENT` |

**HQ greeks:** unused for this split. Intrinsic/time do **not** require IV.

## DATA_INSUFFICIENT

If spot and option last are **not** the same timestamp (3m chain vs 1m INDEX), the split is stale. ATM tape without INDEX join → cannot state moneyness honestly for those minutes.

## Exam trap

Calling OTM “zero value.” OTM has **time value**. Calling ITM “delta 1.” ITM still has residual insurance until expiry.

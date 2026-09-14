# Exam note — what we can price vs HQ null greeks

**Layer:** `VALIDATION` (API facts) + `HYPOTHESIS` (local proxies)  
**Chair:** phd_math + 03 market · **NO_PROMOTE**

## What the oral wants

A **price** is a last/bid/ask on a **named** `security_id`. A **greek** is a vendor or model number attached to that quote. They are not interchangeable. Day-1 rule: **store** HQ fields; **do not invent** missing ones; **do not** treat greeks as P(win).

Black–Scholes / binomial as homework is allowed **only** as a named experiment with declared inputs. Without a validated IV, rate, and time-to-expiry series, the output is a **toy**, not a mark.

## Tokens for FTS

pricing, HQ null greeks, implied_volatility, greeks.delta theta gamma vega, optionchain, websocket no greeks, compute vs store

## Desk mapping

| Object | HQ | We may compute |
|--------|----|----------------|
| OPTIDX LTP / OHLC | rollingoption + charts | returns, MIX-FORM-*, VWAP if volume > 0 |
| Bid/ask, OI, volume | `/optionchain` (3m) | PCR, OI Δ vs previous_oi **on that snapshot** |
| `implied_volatility`, `greeks.*` | Chain JSON — store | **Nothing** if null; no fill-forward as 0 |
| WS ticks | LTP/quote — **no** IV/greeks/full OI | Tape freshness only |
| Supertrend / MACD / RSI | **No** series REST | From **our** OHLC later; confirm/kill not entry |
| Annexure EMA | 5/10/20/50/100/200 — **no EMA_9** | Do not invent EMA_9 as official |

**Honest local pricing (HYPOTHESIS):** next-bar premium change; residual ε = r_opt − k r_idx; intrinsic/time split.  
**Not a price:** cluster id, IsolationForest score, Gemini counsel.

## DATA_INSUFFICIENT

Vendor IV vs `rollingoption` `iv[]` alignment is **UNKNOWN**. Missing greeks between 3m polls are **stale**, not zero. No full smile → no local BS book.

## Exam trap

“Greeks were null so delta is 0.” That **fails**. Null means **unknown**. Spot-ITM fallback is a **documented substitute**, not a greek.

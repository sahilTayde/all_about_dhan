# Exam note — gamma (index options, buy-first)

**Layer:** `VALIDATION` + `HYPOTHESIS`  
**Chair:** phd_math · **NO_PROMOTE**

## What the oral wants

Gamma is how **delta changes** when the underlying moves. Long vanilla options are **long gamma**: a large index move in the right direction can accelerate the option’s dollar delta; a chop around strike **burns** the long via theta (the usual gamma/theta trade).

ATM weeklies have **high gamma** and **high theta**. Deep ITM behaves closer to a scaled futures; deep OTM gamma is small until a shock.

## Tokens for FTS

gamma, convexity, long gamma, ATM weekly, expiry pin, EXPIRY session, delta change, NIFTY SENSEX CE PE

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| Γ = ∂Δ/∂S | HQ `greeks.gamma` on `/optionchain` snapshot only — **not** WS |
| Pin / expiry gamma | Tag `EXPIRY`; analog memory, not SCORE_SAMPLE |
| Long gamma P/L | We only **buy** CE/PE — we own the convexity **and** the bleed |
| 5m Supertrend | Confirm/kill ([`SIGNAL_STAGING.md`](../../../../04_quant/docs/SIGNAL_STAGING.md)), **not** a gamma engine |

**Compute locally (HYPOTHESIS):** finite-difference Δpremium / Δindex on aligned 1m books — a **realized convexity proxy**, not vendor Γ.  
**Do not:** treat missing HQ gamma as 0; do not build a GEX book without a validated OI×Γ series.

## DATA_INSUFFICIENT

No continuous validated gamma history in warehouse day-1. NIFTY GEX / naive GEX construction stays `DATA_INSUFFICIENT` (catalog UNKNOWN). Cannot claim “dealers must hedge here.”

## Exam trap

“High gamma = buy.” Gamma without a **side and a clock** is a homework word. On this desk, high gamma near weekly expiry often means **faster death** if the lean is wrong.

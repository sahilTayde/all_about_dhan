# Exam note — theta decay (NIFTY / BANKNIFTY / SENSEX CE/PE buy-first)

**Layer:** `VALIDATION` (mechanics) + `HYPOTHESIS` (desk use)  
**Chair:** phd_math · **Product:** long premium first — we **pay** theta, we do not harvest it.  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING` · **NO_PROMOTE**

## What the oral wants

Theta is the **calendar haircut** on an option’s time value if the index, rates, and implied vol sit still. For a **bought** CE or PE, expected mark-to-market **drifts down** as expiry approaches, all else equal. Weekly NIFTY / SENSEX sheets die fast; Tuesday flatten (15:15 IST class) is a **forced** theta event, not a surprise.

Theta is **not** a trade signal. It is a **cost of holding** the ticket. A correct lean that is late still loses if premium melted.

## Tokens for FTS

theta decay, time decay, calendar haircut, weekly expiry, long premium, CE PE buy first, 15:15 flatten, MIX-FORM-FOLLOW-GAP

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| ∂V/∂t < 0 for long vanilla | We **buy** CE/PE → haircut is default |
| Weekend / overnight theta | NSE calendar + weekly sid death; do not invent weekend IV |
| Expiry-day gamma/theta fight | Session kind `EXPIRY` — **not** a retune sample ([`RETUNE_GATE.md`](../../../../06_backtesting/docs/RETUNE_GATE.md)) |
| “Index up so CE must pay” | False if theta + stale quote dominate 1m % returns ([`INDEX_CE_PE_EDA.md`](../../INDEX_CE_PE_EDA.md) CE follow ~0.15 on one book) |

**What we can compute:** clock-to-expiry on the **known** contract date; observed premium change vs clock (descriptive).  
**What we must not invent:** a θ series when HQ `greeks.theta` is null/stale.

## DATA_INSUFFICIENT

No trusted **IV term structure** on disk as a continuous series → cannot split “theta vs vega vs residual” on holiday EDA. Store HQ `greeks.theta` when present; treat missing as **null**, not 0. Dual-tape LTP is **not** theta.

## Exam trap

Calling a losing long-premium ticket “wrong delta” when the clock simply ran. BUY-first desk: **time is the opponent** unless the index move is large and the quote is live.

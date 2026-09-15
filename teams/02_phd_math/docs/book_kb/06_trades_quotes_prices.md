# Exam note — Bouchaud et al., *Trades, Quotes and Prices*

**Cite:** Jean-Philippe Bouchaud, Julius Bonart, Jonathan Donier, Martin Gould, *Trades, Quotes and Prices*, Cambridge. **Chair:** phd_market.

## What the oral wants

Price is an **emergent** of the order book. Impact, spread, and **staleness** dominate toy “close-to-close” P/L. A signal on a chart is not a fill.

## Tokens for FTS

microstructure, impact, spread, stale tape, next bar open, quotes, trades, DEALER_KILLED

## Desk mapping

| Book idea | We already do |
|-----------|----------------|
| Don’t assume mid fill | Paper: **next bar open**; TV tester ≠ us |
| Stale quotes | `STALE_TAPE` / after-hours HOLD |
| Impact / cost | `HYPOTHESIS_OPTION_RT_1PCT` on PREMIUM |
| Different instruments | INDEX points ≠ option ₹ |

Combine with AFML: labels must use **tradable** prices. Combine with smile: the quote you see at ATM is not the 23500 PE you think you have after expiry.

## 06 ask

When comparing to founder TV CSV, match **timestamp, bid/ask if any, and commission** — not close vs close.

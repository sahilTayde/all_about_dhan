# LIVE_PAPER_NOTES — live Data API, paper probe (not a pass)

**Team:** 09_review  
**Date:** 2026-09-03  
**Status:** `NOTES_ONLY`  
**Gate:** five-pass **not** passed. `RESEARCH_READY_FOR_PROGRAMMING` **not** issued.  
**Cite:** [`KEEP_ALL_REVIEW.md`](KEEP_ALL_REVIEW.md) · [`ENGINE_MIX_REVIEW.md`](ENGINE_MIX_REVIEW.md) · [`RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md)

Founder started Data API. Live paper-probe succeeded. Orders refused. KEEP_ALL still holds.

---

## ACCEPT

- Live Dhan **GET/POST data** for paper / backtest / chain snapshots (token + user ask). Probe success ≠ strategy validation.
- [`RATE_LIMITS.md`](../../../packages/dhan-client/docs/RATE_LIMITS.md) as the rate-limit **doc**. Honor it; do not invent HQ caps.
- KEEP_ALL: STRAT-001–014 stay on the BACKTEST_BOOK. Kill a MIX only after 06 OOS+`NORMAL`.

---

## REJECT

- **Live orders.** Execution client still refuses. Paper-probe is not `/orders`.
- **Win rates** (or expectancy / PF) from **one morning of chain LTP**. That is not a backtest.
- **`RESEARCH_READY_FOR_PROGRAMMING`.** Still not issued.
- **Waiving Q8.** 276 bars of **5m INDEX** is still not **option-fill history**. Default live ticket still needs chain greeks / option quotes 06 does not have as fills. Q8 remains FAIL ([`ENGINE_MIX_REVIEW.md`](ENGINE_MIX_REVIEW.md)). Q12 / Q19 / Q20 / Q4 on that ticket are also not waived by a data probe.

**Verdict:** `NOTES_ONLY`. Five-pass still not passed.

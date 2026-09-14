# Exam note — Derman & Miller, *The Volatility Smile* (Wiley)

**Cite:** Emanuel Derman & Michael B. Miller, *The Volatility Smile*, Wiley. **Chair:** phd_math. Also sit Natenberg / Hull already in `workspace.yaml`.

## What the oral wants

Implied vol is **not** one number. Smile/skew means two strikes are **different** insurance prices. Delta, vega, and “index moved so premium should move” are **local**.

## Tokens for FTS

volatility smile, skew, implied vol, vega, theta, residual, MIX-FORM-STRADDLE-RET

## Desk mapping

| Classroom | Our tape |
|-----------|----------|
| Need IV surface | HQ IV **not** a trusted series → store null, do not invent |
| Risk reversal / skew | ATM CE vs PE **returns** (EDA corr) as a **proxy**, not IV |
| Calendar | Expiry 15:15 flatten; weekly sid dies (47298) |
| Theta | Long premium haircut; TV-EP PREMIUM FAIL |

`MIX-FORM-STRADDLE-RET` = r_CE + r_PE is a **crude** vol-of-the-day proxy (HYPOTHESIS), not the smile book’s Dupire machinery.

## Exam trap

Fitting a smile in Python without quotes. **DATA_INSUFFICIENT** until chain IV fields are validated. Dual-tape LTP is not a smile.

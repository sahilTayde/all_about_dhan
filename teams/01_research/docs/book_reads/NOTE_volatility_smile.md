# NOTE — Volatility smile / skew (123456.pdf + Orrell companions)

**Team:** 01 research librarian  
**Layer:** `SOURCE_FACT` (file identity + readable papers) + desk map `HYPOTHESIS`  
**Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Inventory (pypdf; `pdftotext` not installed):** re-read 2026-09-14.

| File | Pages | Extractable chars | Layer |
|------|------:|------------------:|-------|
| `docs/123456.pdf` | 303 | 0 | **IMAGE** — still Bookey dump |
| `docs/ssrn-4205729.pdf` | 19 | 31 541 | **TEXT** — Orrell & Richards, *Keep on smiling* |
| `docs/ssrn-3512481.pdf` | 21 | 39 521 | **TEXT** — Orrell, *A quantum walk model of financial options* |

**Copyright:** original notes only. Do not FTS-ingest PDFs. Do not paste chapter/paper body.

---

## What is still missing (Wiley *The Volatility Smile*)

`123456.pdf` `/Title` is still *The Volatility Smile: Option Pricing & Volatility Models* (Wiley cover / Derman, Miller, Park). Selectable text remains **empty on all 303 pages**. Treat as a commercial summary dump, **not** the typeset Wiley book.

**DATA_INSUFFICIENT** for Dupire / local-vol / Heston / jump calibration that lives only in the published monograph. Do not upgrade this file to 02 VALIDATION of Wiley formulas.

02 exam stub (not these PDFs): [`book_kb/05_volatility_smile.md`](../../../02_phd_math/docs/book_kb/05_volatility_smile.md).

---

## Smile / skew — topic depth for NIFTY / SENSEX CE/PE (buy first)

We **buy** weekly premium. We do **not** run a dealer Δ book. One vol number is a **metaphor**.

**SOURCE_FACT (Orrell/Richards, full text).** Constant-σ BSM inverted on a strike grid produces a **smile** (OTM richer in IV-space than ATM) usually mixed with **skew**. Shape depends on tenor and typically **sharpens** as expiry shortens. Competing stories: crash-insurance demand, loss-aversion “anomaly,” or a **real** link between **imbalance**, **price change**, and **volatility**. Their working claim: buying a strike away from discounted spot is assuming imbalance; imbalance moves both the expected path and vol. They write a smile-shaped σ(K) from a quantum-oscillator / impact model and compare it to the empirical “square-root-of-time” surface rule (Daglish–Hull–Suo on SPX). They argue classical BSM **flattens** quoted IV vs a “true” smile.

**Equity-index skew (their SPX/DJIA tape, not NSE).** Equity indices show a **growth / put-wing** tilt that FX pairs often lack. They interpret a large IV skew partly as a **correction** for using a T-bill “risk-free” drift while equities grow faster — straddles look **shifted** vs realized payout if you force r = T-bill.

**Straddle / ATM haircut (their SPX experiment, 2004–mid-2017).** 1-month SPX straddles, many strikes in a log-moneyness band, VIX as **flat** σ into Black: ATM **pay-in > payout**. They report the flat-VIX Black cost near ATM overstates payout by a factor **near √2**, and log-returns of those ATM straddles are **negative on average**. They treat “vol risk premium” language as partly **model error** (constant-σ overprices ATM). Wings with large **intrinsic** are less about σ.

**Desk map (HYPOTHESIS).** Transferable **warnings**, not a ticket:

| Classroom / paper | NIFTY / SENSEX weekly CE/PE |
|-------------------|------------------------------|
| Smile = strike-local insurance | Same-K CE and PE are **not** “the index.” Dual-tape already treats them as two products. |
| Equity **skew** (OTM PE richer) | Do **not** invent HQ IV. Proxy only: same-session **CE vs PE returns** / residual (`INDEX_CE_PE_EDA`, `MIX-FORM-*`). |
| ATM straddle overpriced vs payout (SPX + VIX) | Long ATM CE+PE **pays theta**. `MIX-FORM-STRADDLE-RET` := r_CE + r_PE is a **crude** vol-of-day proxy, **not** IV and **not** a reason to buy both wings. Their “short ATM straddle because √2” is **short premium** → **off** customer default. |
| Tenor-sharper smile | Weekly 15:15 flatten + Tuesday expiry is **not** their 1m/3m/12m SPX grid. Do not copy coefficients. |
| Impact ↔ vol | FOLLOW-GAP / `PREMIUM_DIVERGENCE` HOLD when spot moved and the option last did not. Not Kyle λ (we do not have it). |

**Quantum walk paper (3512481).** Same author family; interference / non-classical walk as a **pricing metaphor**. **DATA_INSUFFICIENT** for Dhan fields. Do not code a quantum pricer on 1m LTP.

## Maths we may implement (`HYPOTHESIS`)

Keep named MIX / overlays. **Not** `STRAT-015+`. **Not** `/`.

| Idea | Desk stand-in |
|------|----------------|
| Smile / risk-reversal | ATM or same-K **CE vs PE** returns — proxy, not IV |
| “Daily vol” of underlier | `MIX-FORM-STRADDLE-RET` — expiry-contaminated |
| Local Δ vs index | `MIX-FORM-BETA` residual ε = r_opt − k r_idx — **OLS k**, not HQ Δ |
| Follow vs gap | `MIX-FORM-FOLLOW-GAP` → **HOLD** new CE/PE |
| Discrete hedge + costs | Next-bar fill, IST session, weekly flatten — measure haircut |

## What we cannot (no HQ IV)

- Implied-vol surface, Dupire, Heston, jump-diffusion, Breeden-Litzenberger from quoted IVs.
- Orrell Eq. (1) / β≈0.9 / α≈0.1 **coefficients** on NIFTY/SENSEX (their fit is DJIA/SPX/VIX).
- Invented Δ, vega, or “C-ratio of ATM vol vs spot.”
- Variance-swap 1/K² strip; listed var-swap.
- Treating dual-tape **LTP** as a smile.
- Promoting short-straddle / short-put from SPX ATM negative-return studies.

If rollingoption later exposes a validated IV field: store it; **do not** fill null with BS invert.

## Backtest pitfalls / overfitting

- One weekly sid as a “surface.”
- Holiday / non-overlap INDEX vs ATM tape as proof.
- Marking long premium with **BS hedge P/L** we never trade.
- Mixing SENSEX and NIFTY without a named MIX.
- Story-fitting sticky-delta vs sticky-strike on a Bookey dump plus one Orrell β.

Walk-forward + `NORMAL` + `RETUNE_PROPOSAL` only.

## Desk mapping

| Desk object | Use | Must not |
|-------------|-----|----------|
| Dual-tape | When spot and premium disagree, the one-σ metaphor failed → HOLD | Treat LTP pair as IV smile |
| MIX-FORM-* | Residuals / straddle-ret / follow-gap as **observables** | Promote to `/` or live |
| ML-001 | `DIVERGE` = “surface moved, we have no surface” | Train on invented IV |
| ML-002 | OU on **residual**, not implied vol | Call half-life a vega trade |

**NO_PROMOTE.** KEEP_ALL STRAT-001–014. Next: 02 (Wiley still DI; Orrell is a paper, not our OOS) / 06 (tape features only).

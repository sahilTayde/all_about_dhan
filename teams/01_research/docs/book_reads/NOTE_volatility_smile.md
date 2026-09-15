# NOTE — 123456.pdf (founder: Volatility Smile)

**Team:** 01 research librarian  
**Layer:** `SOURCE_FACT` (file identity) + original desk mapping (`HYPOTHESIS` only where labelled)  
**Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** none. Education ≠ edge.

## Identified title / authors

| Field | From this PDF |
|-------|----------------|
| Path | `teams/01_research/docs/123456.pdf` (~125 MB, **303** pages) |
| PDF metadata `/Title` | *The Volatility Smile: Option Pricing & Volatility Models* |
| Cover (page image) | Wiley Finance; **Emanuel Derman**, **Michael B. Miller**, contribution **David Park** |
| What the file *is* | **Bookey** commercial summary/Q&A dump (ads, “install app” pages). **Not** the Wiley typeset body. |
| Extractability | `pypdf` / selectable text = **empty on all 303 pages**. Notes below from **page images** + TOC list only. |

**DATA_INSUFFICIENT** for any formula, table, or Dupire/local-vol calibration that lives only in the published book. Do not treat this PDF as the smile textbook.

## Topics that matter for NIFTY / SENSEX CE/PE (buy first)

We **buy** premium. We do **not** run a market-maker delta book. Classroom replication is a **warning**, not a ticket.

- **One vol number is a lie.** BSM constant-σ vs strike/expiry-shaped insurance. Index weekly CE and PE at the same K are **not** the same product as “the index.”
- **1987 / crisis story:** smile as *model failed, market did not*. Maps to dealer HOLD, not to “fit a smile and buy.”
- **Relative value vs absolute value.** We already rank with tape (INDEX vs ATM CE vs ATM PE). We do **not** invent a 1-D “cheap IV” score.
- **Static vs dynamic replication, put-call parity.** Useful as a **consistency check** on expiry payoffs; not a reason to short the other wing. Buy-first desk does **not** synthesize a forward by selling CE+PE.
- **Variance-swap / 1/K² strip.** Classroom vol-of-vol hedge. We have **no** listed var-swap and **no** trusted chain IV → **cannot** implement.
- **Discrete hedge + costs.** Continuous Δ-hedge P/L is a fantasy. Our paper path: **next-bar / stale LTP / lot**, not BS P/L.
- **Smile stylized facts (summary only):** ATM often cheaper in IV-space than wings; equity index usually **skew** (OTM PE richer) not a symmetric smile. Book visualizes vs **delta**; we **do not have HQ delta**.
- **Sticky strike / sticky delta / local vol.** Rules of thumb for how the *surface* moves when spot moves. Without a surface, they are slogans.
- **Local vol vs stoch vol vs jumps.** Competing *metaphors* for the same quotes. Jump/Poisson pages in this dump are **not** implementable on 1m LTP.

## Maths we may implement (`HYPOTHESIS`)

Keep these as named MIX / overlays. **Not** `STRAT-015+`. **Not** customer default.

| Idea (classroom) | Desk-shaped stand-in |
|------------------|----------------------|
| Smile / risk-reversal | ATM (or same-K) **CE vs PE returns** already in `INDEX_CE_PE_EDA` — proxy, not IV |
| “Daily vol” of the underlier | `MIX-FORM-STRADDLE-RET` := \(r^{\mathrm{CE}}+r^{\mathrm{PE}}\) — crude, expiry-contaminated |
| Local Δ vs index | `MIX-FORM-BETA` / residual \(\varepsilon = r^{\mathrm{opt}} - k\, r^{\mathrm{idx}}\) — **OLS \(k\)**, not HQ Δ |
| Follow vs gap | `MIX-FORM-FOLLOW-GAP` / dual-tape `PREMIUM_DIVERGENCE` → **HOLD** new CE/PE |
| Discrete hedge error | Paper: next-bar fill, IST session, weekly 15:15 flatten — measure **haircut**, do not invent vega |

02 exam note (not this PDF): [`teams/02_phd_math/docs/book_kb/05_volatility_smile.md`](../../../02_phd_math/docs/book_kb/05_volatility_smile.md).

## What we cannot (no HQ IV)

- Implied-vol surface, Dupire local vol, Heston/SV calibration, jump-diffusion fit, Breeden-Litzenberger density from quoted IVs.
- Invented Δ, vega, or “C-ratio of ATM vol vs spot.”
- Variance-swap fair strike from a 1/K² strip.
- Treating dual-tape **LTP** as a smile.

If rollingoption later exposes a validated IV field: store it, **do not** silently fill null with BS invert. Until then: **DATA_INSUFFICIENT**.

## Backtest pitfalls

- Fitting any smile model on **one weekly sid** then claiming a surface.
- Using holiday or non-overlap INDEX and ATM tape as proof.
- Marking long premium with **BS hedge P/L** we never trade.
- Expiry Tuesday / 15:15 flatten treated as a continuous European book.
- SENSEX vs NIFTY mixed without a named MIX row.

## Overfitting

A 303-page **summary app** plus a handful of 1m residuals is enough to **story-fit** sticky-delta vs sticky-strike. Walk-forward + `NORMAL` + `RETUNE_PROPOSAL` only. Cluster counts and \(k\) on one window are **not** a smile.

## Desk mapping

| Desk object | Use from this PDF | Must not |
|-------------|-------------------|----------|
| **Dual-tape** | When spot and premium disagree, the BSM one-σ metaphor already failed → HOLD | Treat LTP pair as IV smile |
| **MIX-FORM-*** | Residuals / straddle-ret / follow-gap as **observable** stand-ins | Promote to `/` or live |
| **ML-001** | IsolationForest / `DIVERGE` = “surface moved, we have no surface” | Train on invented IV |
| **ML-002** | OU on **residual**, not on implied vol | Call half-life a vega trade |

**NO_PROMOTE.** KEEP_ALL STRAT-001–014. Next: 02 (do not upgrade this dump to Wiley VALIDATION) / 06 (OOS only on tape features).

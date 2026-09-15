# NOTE — SSRN 3247865 (151 taxonomy, full text layer)

```text
Source:   teams/01_research/docs/ssrn-3247865.pdf
          teams/01_research/docs/ssrn-3247865 (1).pdf  (byte-identical duplicate)
          https://ssrn.com/abstract=3247865
Title:    151 Trading Strategies
Authors:  Zura Kakushadze and Juan Andrés Serur
Date:     17 August 2018
This file: full SSRN PDF, 361 pages, selectable text
Layer:    SOURCE_FACT (identity + taxonomy) / desk map HYPOTHESIS
Date:     2026-09-14 (re-inventory)
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Inventory (pypdf)

| File | Pages | Chars | Layer |
|------|------:|------:|-------|
| `ssrn-3247865.pdf` | 361 | 833 381 | **TEXT** |
| `ssrn-3247865 (1).pdf` | 361 | 833 381 | **TEXT** (same) |

Abstract (paraphrase): pedagogical catalog of **150+** *types* across options, stocks, ETFs, FI, futures, FX, vol-as-asset, crypto, macro, …; **550+** formulas; bibliography/glossary; **R appendix** to *illustrate* OOS. Authors: body is **descriptive** and **does not** contain empirical P/L tables.

02 exam note called 151 “inferred.” **This SSRN id confirms the title.** Retraction rumor stays **VERIFY**. Springer hardcover exists; this file is the authors’ SSRN PDF.

Do not paste chapter formulas.

---

## 151 taxonomy — what the catalog actually is

**Ch.2 Options (TOC, paraphrase).** A **structure museum**: covered/protective, verticals, calendars/diagonals, synthetics/combos, ladders, long/short straddles-strangles-guts, synthetic straddles, straps/strips, ratio and backspreads, butterflies/condors/irons, box, collar, seagulls. Textbook payoffs in §2.1 assume **no transaction costs**.

**Ch.3–22 (TOC only for desk).** Stocks (momentum/value/low-vol, pairs, cluster MR, MAs, S/R, channel, KNN, stat-arb, **market-making**, alpha combos). ETFs, FI butterflies, **index** cash-and-carry / dispersion / ETF arb / vol targeting, **vol** (VIX basis, ETN carry, vol-risk-premium, **long risk-reversal**, variance swaps), FX carry, commodities, futures hedge/calendar/CTA, convertibles, distressed, RE, crypto, **global macro**, infrastructure, ML (ANN/Bayes/KNN), cash. §3.21 (paraphrase): single-name MA / S/R / channel / single-stock KNN are widely called **unscientific**; any edge is more plausible in a **cross-section**.

Intro (paraphrase): markets are **man-made and ephemeral**; strategies die when microstructure changes. Purpose is **information**, not “how to make money.”

---

## Apply to NIFTY / SENSEX CE/PE (buy first)

| Taxonomy bucket | Customer default? | Why |
|-----------------|-------------------|-----|
| Long call / long put / protective (long option) | **Maybe as named MIX**, never 57 at once | Matches **CE/PE buy first**. Still theta + 1% RT. FOLLOW-GAP HOLD if the option last does not confirm. |
| Long straddle / strangle / guts | Research overlay only | Pays two thetas. SPX ATM-straddle studies (see smile NOTE) warn **negative average** long ATM straddles. Not `/`. |
| Covered call/put, short straddle/strangle, short guts, short iron, short condor, ratio **short** more than long | **No** | Short premium / undefined risk. Off desk. |
| Vertical debit (bull call / bear put) | Named MIX only | Defined risk but two legs, two haircuts, weekly pin. |
| Vertical **credit** (bull put / bear call) | **No** | Short premium. |
| Calendar / diagonal | Unlikely | Two expiries; we flatten weeklies; **DATA_INSUFFICIENT** on Dhan multi-expiry fills. |
| Synthetics / box / combo | **No** | Arb / short-leg. Not buy-first. |
| Collar / seagull | **No** as default | Mixed short. |
| Ch.6 index cash-and-carry / dispersion | **No** | Needs basket + futures cash; FUTIDX continuous still thin. |
| Ch.7 VIX ETN / var-swap / vol-risk-premium **short** | **No** | Different product. India has no VIX futures book here. |
| Ch.7 “vol skew — long risk reversal” | **No** as default | Typically long OTM call / short OTM put (or reverse) — **one short wing**. Skew **observation** belongs in smile NOTE (CE vs PE returns), not a Super Order. |
| Ch.3 MAs / S/R / channel on **one** chart | Confirm-or-kill only | Matches §3.21 + our 5m rule. |
| Ch.19+ ML catalog rows | Overlay | ML-001 only. No STRAT-015+. |
| Ch.21 global macro types | HOLD overlay | See Gliner NOTE. Not 1m entry. |

## Microstructure / fills / leakage / model selection

| Topic | From this SSRN | Desk |
|-------|----------------|------|
| Fills | Payoffs ignore costs; MM is a **type** | **Next-bar open**. INDEX ≠ premium. No mid fantasy. |
| Costs | Faint signals only matter **after** costs / HFT slippage | `HYPOTHESIS_OPTION_RT_1PCT`. Statutory stack **UNKNOWN**. Most **structures** fail that haircut before theta. |
| Leakage | Body has **no** strategy P/L. Appendix A: quantities on day *t* from data **strictly before** *t* | Do not “backtest” 151 names on one holiday week. |
| Model selection | KNN / ANN are **entries**, not winners | One customer ticket. |

## KEEP_ALL vs 151 live books

A **taxonomy / graveyard** is useful. A live tournament of 151 books is not. Status = PARK / FAIL / WATCH. `keep_current_strategy: true` until 06 OOS+**NORMAL**.

## Next team

02 (exam stub already; this NOTE is SOURCE_FACT id + buy-first filter) · 04 (do not port Ch.2 shorts) · 06 (next-bar + 1% RT) · 09.

## UNKNOWN / DATA_INSUFFICIENT

Hardcover vs SSRN row diffs. Withdrawal rumor. OPTIDX pin/theta vs European stock-option examples. **NO_PROMOTE.**

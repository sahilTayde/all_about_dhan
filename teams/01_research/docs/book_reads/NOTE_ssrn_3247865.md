# NOTE — SSRN 3247865

```text
Source:   teams/01_research/docs/ssrn-3247865.pdf
          https://ssrn.com/abstract=3247865
Title:    151 Trading Strategies
Authors:  Zura Kakushadze and Juan Andrés Serur
Date on PDF: 17 August 2018
SSRN id:  3247865
This file: full SSRN PDF (~361 pages) on disk; this NOTE is original
Layer:    SOURCE_FACT (identity + structure) / desk map HYPOTHESIS
Date:     2026-09-14
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Identity — this **is** the “151 / Kakushadze” item

Abstract (paraphrase): pedagogical catalog of **150+** strategy *types* across options, stocks, ETFs, fixed income, futures, FX, vol, crypto, macro, etc.; **550+** formulas; bibliography and glossary; **R appendix** to *illustrate* out-of-sample backtesting. Authors state the body is **descriptive** and (intentionally) **does not** contain numeric simulations / empirical P/L tables.

02’s exam note called 151 “inferred.” **This SSRN id confirms the title.** Retraction rumor stays **VERIFY**, not SOURCE_FACT. Springer hardcover exists; this file is the authors’ SSRN PDF.

## What the catalog actually is

Ch.2 opens with **option generalities**: call/put claims at expiry, premium paid up front, many structures (covered, protective, verticals, calendars, butterflies, condors, straddles, synthetics, seagulls). Textbook payoffs in §2.1 are written **assuming no transaction costs**.

Ch.3 stocks: momentum/value/low-vol, pairs, cluster MR, 1/2/3 MAs, S/R, channel, KNN, stat-arb, **market-making**, alpha combos. §3.21 (paraphrase): single-name MA / S/R / channel / single-stock KNN are widely called **unscientific**; any edge is more plausible in a **cross-section** (correlated names), not one chart’s crossover.

Intro (paraphrase): markets are **man-made and ephemeral**; strategies die when microstructure changes (e.g. specialist → electronic). Purpose is **information**, not “how to make money.” Disclaimer: not investment advice.

## What it does **not** support

- Coding **151** (or 57 option recipes) into Dhan Super Order or `/`.
- Treating the R appendix as our OOS+NORMAL gate.
- Short premium / covered-call / iron condor as customer default (**CE/PE buy first**).
- Win rates, lots, or fills for NIFTY/BANKNIFTY/SENSEX weeklies.
- Deleting STRAT-001–014 or MIX-TV-EP rows because a catalog cousin failed (`KEEP_ALL`).

## Microstructure / fills / leakage / model selection

| Topic | From this SSRN | Desk |
|-------|----------------|------|
| Fills | Payoffs ignore costs; market-making row exists as a **type**, not a Dhan L2 model | **Next-bar open** + no mid fantasy. INDEX ≠ premium. |
| Costs | Authors say faint signals only matter **after** costs and HFT slippage | **`HYPOTHESIS_OPTION_RT_1PCT`**: 1% premium each way. Statutory **UNKNOWN**. Most listed option *structures* would fail that haircut even before theta. |
| Leakage | Body has **no** strategy P/L. Appendix A is a **generic** OOS illustration (quantities used on day *t* must be computed from data **strictly before** *t*) | Do not “backtest” 151 names on one holiday week. No look-ahead on signal close. |
| Model selection | KNN / ANN appear as **catalog entries**, not a tournament winner | One customer ticket. ML-001 overlay only. No STRAT-015+. New ideas = named **MIX-*** with origin tag. |
| FOLLOW-GAP | Not in the book. Directional option recipes assume the option **moves with** the story | If index↓ and PE last does not rise (`MIX-FORM-FOLLOW-GAP`), **HOLD**. Do not execute “buy put because index fell” from Ch.2 directional group. |

## KEEP_ALL vs 151 live books

Same spirit as Editors’ Picks: a **taxonomy / graveyard** is useful. A live tournament of 151 books is not. Status = PARK / FAIL / WATCH. Customer still sees **one** MIX. `keep_current_strategy: true` until 06 OOS+**NORMAL**.

## Next team

02 (already has exam stub; this NOTE is the SOURCE_FACT id) · 04 (do not port Ch.2 shorts) · 06 (factory stays next-bar + 1% RT) · 09.

## UNKNOWN / DATA_INSUFFICIENT

Which hardcover rows differ from this SSRN PDF. Whether any title was withdrawn. OPTIDX pin/theta vs European stock-option examples. **NO_PROMOTE.**

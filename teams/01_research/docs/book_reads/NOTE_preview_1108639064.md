# NOTE — Cambridge preview 9781108639064

```text
Source:   teams/01_research/docs/preview-9781108639064_A34411323.pdf
          (47-page Kobo/Cambridge preview; not the full monograph)
Title:    Trades, Quotes and Prices
Authors:  Jean-Philippe Bouchaud, Julius Bonart, Jonathan Donier, Martin Gould
ISBN:     978-1-108-63906-4 (preview file id A34411323)
Publisher:Cambridge University Press
Layer:    SOURCE_FACT (preview TOC + front matter + Ch.1 ecology)
Date:     2026-09-14
Status:   UNVALIDATED desk map / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Identity (this file)

PDF metadata title is **TRADES, QUOTES AND PRICES**; author field **JEAN-PHILIPPE BOUCHAUD**. Opening blurb: high-frequency **quotes and trades**, not close-to-close prices alone; models calibrated on **NASDAQ** tapes. Preview includes Contents through Part IX (optimal execution, fairness) plus Appendix A (NASDAQ data description). Body extract in this file is **front matter + early ecology / LOB intro**, not the later impact chapters.

This is **not** a DhanHQ tape. **DATA_INSUFFICIENT** for NSE OPTIDX lots, Dhan Super Order fields, or Indian tick rules.

## What the preview actually supports

| Topic | Librarian claim (paraphrase, not a lift) | Does **not** support |
|-------|------------------------------------------|----------------------|
| Microstructure / fills | The object of study is the **limit order book**: posted size at each price, cancellations, marketable hits. A chart mid or bar close is a **summary**, not a guaranteed fill. | Treating INDEX 1m close as the CE/PE fill. Inventing Dhan bid/ask REST series. |
| Spread + impact | Liquidity providers charge a **spread**; a marketable buy (sell) **moves** the quote on average. Impact is a **cost**, listed with brokerage/fees. Large parent orders split into **child / metaorders**; literature in the TOC: square-root impact, **impact decay**, **slippage**. | A 0-cost close-to-close P/L. Claiming we measured Kyle λ on NIFTY. |
| Fragile / latent liquidity | Displayed size is **thin**; much interest is **latent**. Providers pull when flow looks informed. Liquidity can vanish faster than a 1m bar. | “Always liquid ATM weekly” as SOURCE_FACT. |
| Why prices move | Random-walk primer + jumps/intermittency in Ch.2 TOC. Prices are **order-driven**, not an exogenous random number the option must follow. | Index print ⇒ option last **must** reprice 1:1. |
| Stats methods | Stochastic **queue** models, Hawkes clustering, propagator / history-dependent impact (later parts). Empirical first, then model. | A new STRAT from Santa Fe LOB. Hawkes on our holiday cache. |

## Desk map (HYPOTHESIS overlay — not a promote)

| Desk rule | Why this preview points at it |
|-----------|-------------------------------|
| **Next-bar fill** | Signal on bar *i* close is information **after** that bar’s auction of prints. We fill at bar *i+1* **open** (`simulate.py`) so we do not pretend we traded the mid of the bar that generated the lean. Still **not** a LOB walk; it only removes one look-ahead. |
| **1% RT** (`HYPOTHESIS_OPTION_RT_1PCT`) | Book: fees **plus** impact. We do not have NSE statutory stack or OPTIDX impact. 1% of **premium** each way is a **placeholder haircut**, not a measured square-root law. After-cost FAIL on MIX-TV-EP premium cells stays **FAIL**. |
| **FOLLOW-GAP** (`MIX-FORM-FOLLOW-GAP`) | Index down & PE not up (or index up & CE not up) is the desk’s **stale / non-following quote** flag. Bouchaud: the option book can fail to show the liquidity that “should” sit at the new fair. Dealer **HOLD** new CE/PE; do not buy the option because NIFTY printed. |

INDEX points ≠ option ₹. TV Strategy Tester close fills ≠ this preview and ≠ our next-bar-open engine.

## Next team

02 (VALIDATION vs smile / residual) · 03 (NSE hours, stale tape) · 06 (keep next-bar + 1% RT; do not score mid) · 09 (NOTES_ONLY).

## UNKNOWN / DATA_INSUFFICIENT

Full-book chapters 11–21 not in this 47-page extract. No Dhan L2. No measured OPTIDX impact. Statutory STT/GST still **UNKNOWN**. **NO_PROMOTE.**

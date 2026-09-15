# NOTE — oneil-derman.pdf

**Team:** 01 research librarian  
**Layer:** `SOURCE_FACT` + original desk mapping (`HYPOTHESIS` labelled)  
**Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** none.

## Identified title / authors

| Field | From this PDF |
|-------|----------------|
| Path | `teams/01_research/docs/oneil-derman.pdf` (~1.9 MB, **19** pages) |
| Title on slide 1 | **Models Behaving Badly** |
| Author | **Emanuel Derman**, Columbia University |
| Date on slide 1 | July 16, 2013 |
| Extractability | Selectable text **OK** (`pypdf`). Lecture / manifesto slides, not a monograph. |

**Filename vs contents:** `oneil-derman` does **not** contain William J. O’Neil (CAN SLIM / *How to Make Money in Stocks*). **DATA_INSUFFICIENT** for any O’Neil equity-trend claim from this file. Treat the name as a folder label only.

Related 02 exam note (book, not these slides): [`teams/02_phd_math/docs/book_kb/03_derman_models_behaving_badly.md`](../../../02_phd_math/docs/book_kb/03_derman_models_behaving_badly.md).

## Topics for NIFTY / SENSEX CE/PE (buy first)

Derman’s split: **theories** stand on their own; **models** are metaphors; **finance has only models**. Black–Scholes is likened to smoke diffusion — useful until it is not.

For a **long** weekly CE or PE:

- The ticket is a **rupee premium**, not a theory of NIFTY.
- “Index down ⇒ buy PE” is a model. Dual-tape exists to catch when the metaphor fails (spot down, PE not up).
- Big Data / correlation slides: patterns are not causes. ML-001 clusters are **counts**, not a law of 23500 PE.
- Valuation models **map an intuition (vol, yield) into a price** and interpolate illiquid from liquid. We interpolate nothing without quotes. We **pay** theta; we do not mark a replicating book.

Slide law (paraphrase): value a security from the **most similar** traded one; the rest is modeling. On this desk the “similar” print is **same-expiry ATM (or chosen K) CE/PE LTP beside INDEX** — not a fitted smile.

## Maths we may implement (`HYPOTHESIS`)

These slides are **philosophy + hygiene**, not a pricing engine.

| Slide idea | What 04/06 may code |
|------------|---------------------|
| Make the dirt explicit | Log `DATA_INSUFFICIENT`, null greeks, stale LTP, holiday = no `SCORE_SAMPLE` |
| Shallow finance > deep axiom | Keep MIX-FORM OLS residual; do not drop a utility stack on 30s |
| Gedanken experiment | Named MIX row, `customer_default: false`, paper only |
| Similar payoff ⇒ similar price | Dual-tape **follow** vs **gap**; HOLD on gap — not an arb bot |

No new STRAT. No live Super Order.

## What we cannot (no HQ IV)

- Treat BSM (or any local/stoch vol) as a **theory** of NIFTY/SENSEX options.
- Calibrate “future vol → option price” without a trusted IV field.
- Rank every strike on a 1-D “value” scale from this lecture.
- Import O’Neil CAN SLIM as if it were in the PDF.

## Backtest pitfalls

- Reporting a model win rate on **index** bars and calling it option P/L (finance semantics ≠ physics).
- Using Big Data language (KMeans clean on a holiday join) as causation.
- Dynamic-replication P/L in a backtest we never hedge.

## Overfitting

Slide conclusion, compressed: a little hubris is useful; **idolatry** is the failure mode. Fitting ML-001 / ML-002 / MIX-FORM \(k\) on one cache window and promoting is idolatry. `RETUNE_GATE`: proposal only.

## Desk mapping

| Desk object | Mapping |
|-------------|---------|
| **Dual-tape** | The *dirt*: premium ≠ index. HOLD `PREMIUM_DIVERGENCE` / FOLLOW-GAP. Zero LLM on the tick. |
| **MIX-FORM-*** | Explicit interpolation/residual — say what was swept under the rug (no Δ, no IV, same-K not ATM). |
| **ML-001** | Statistics mode of knowing: useful overlay, **not** a replacement for the dealer story. `DIVERGE` ≠ BUY. |
| **ML-002** | OU on residual is a **metaphor** for snap-back. Overlay HOLD if \(\|z\|\) large; not a theory of vol. |

**NO_PROMOTE.** KEEP_ALL. Next: 02/04 (humility language) / 09 (notes ≠ five-pass).

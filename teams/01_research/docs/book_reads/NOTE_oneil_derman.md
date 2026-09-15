# NOTE — oneil-derman.pdf (Derman slides, not full *Models Behaving Badly*)

**Team:** 01 research librarian  
**Layer:** `SOURCE_FACT` + desk map `HYPOTHESIS`  
**Status:** `UNVALIDATED` / **NO_PROMOTE**  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`

## Inventory (pypdf, 2026-09-14)

| File | Pages | Chars | Layer |
|------|------:|------:|-------|
| `docs/oneil-derman.pdf` | 19 | 11 883 | **TEXT** |

Slide 1: **Models Behaving Badly**, **Emanuel Derman**, Columbia, 16 July 2013. Lecture / manifesto slides. **Not** the 2011 monograph and **not** a full-book re-upload.

**Filename vs contents:** `oneil-derman` does **not** contain William J. O’Neil (CAN SLIM). **DATA_INSUFFICIENT** for any O’Neil claim from this file.

Related 02 exam note (book, not these slides): [`book_kb/03_derman_models_behaving_badly.md`](../../../02_phd_math/docs/book_kb/03_derman_models_behaving_badly.md).

---

## Topics for NIFTY / SENSEX CE/PE (buy first)

Derman’s split (slides): **theories** stand alone; **models** are metaphors; **finance has only models**. BSM is likened to smoke diffusion — useful until it is not.

For a **long** weekly CE or PE:

- The ticket is a **rupee premium**, not a theory of NIFTY.
- “Index down ⇒ buy PE” is a model. Dual-tape exists to catch when the metaphor fails (spot down, PE not up).
- Big Data / correlation slides: patterns are not causes. ML-001 clusters are **counts**, not a law of a strike.
- Valuation models **map an intuition (vol, yield) into a price** and interpolate illiquid from liquid. We interpolate nothing without quotes. We **pay** theta; we do not mark a replicating book.

Slide law (paraphrase): value a security from the **most similar** traded one. On this desk the “similar” print is **same-expiry ATM (or chosen K) CE/PE LTP beside INDEX** — not a fitted smile.

## Maths we may implement (`HYPOTHESIS`)

Philosophy + hygiene, not a pricing engine.

| Slide idea | What 04/06 may code |
|------------|---------------------|
| Make the dirt explicit | Log `DATA_INSUFFICIENT`, null greeks, stale LTP, holiday = no `SCORE_SAMPLE` |
| Shallow finance > deep axiom | Keep MIX-FORM OLS residual; no utility stack on 30s |
| Gedanken experiment | Named MIX, `customer_default: false`, paper only |
| Similar payoff ⇒ similar price | Dual-tape follow vs gap; HOLD on gap — not an arb bot |

No new STRAT. No live Super Order.

## What we cannot

- Treat BSM (or local/stoch vol) as a **theory** of NIFTY/SENSEX options.
- Calibrate “future vol → option price” without trusted IV.
- Rank every strike on a 1-D “value” scale from this lecture.
- Import O’Neil CAN SLIM as if it were in the PDF.
- Claim we now have “full Models Behaving Badly.”

## Backtest / overfitting

Do not report an index-bar win rate as option P/L. Do not treat KMeans on a holiday join as causation. Fitting ML-001 / MIX-FORM *k* on one window and promoting is the **idolatry** failure mode on the last slides. `RETUNE_GATE`: proposal only.

## Desk mapping

| Desk object | Mapping |
|-------------|---------|
| Dual-tape | The *dirt*: premium ≠ index. HOLD `PREMIUM_DIVERGENCE` / FOLLOW-GAP. Zero LLM on the tick. |
| MIX-FORM-* | Say what was swept under the rug (no Δ, no IV). |
| ML-001 | Statistics mode of knowing; overlay only. `DIVERGE` ≠ BUY. |
| ML-002 | OU on residual is a **metaphor**. Overlay HOLD if \|z\| large. |

**NO_PROMOTE.** KEEP_ALL. Next: 02/04 (humility language) / 09 (notes ≠ five-pass).

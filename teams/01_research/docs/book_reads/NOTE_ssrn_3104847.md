# NOTE — SSRN 3104847

```text
Source:   teams/01_research/docs/ssrn-3104847.pdf
          https://ssrn.com/abstract=3104847
Title:    Advances in Financial Machine Learning
Author:   Marcos López de Prado
ISBN:     978-1-119-48208-6 (Wiley hardcover, 2018)
SSRN id:  3104847
This file: ~61-page authorized excerpt (praise, TOC, Ch.1 + contents through HPC)
Layer:    SOURCE_FACT (excerpt) + desk map is HYPOTHESIS
Date:     2026-09-14
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Identity (this file)

PDF title metadata `SSRN_AFML.pdf`. Cover pages name **Advances in Financial Machine Learning**, Wiley 2018. Footer: reprint with permission; full book not in-repo. Workspace already lists `lopez_afml` in `config/workspace.yaml`. This note is **original**; do not FTS-ingest the PDF.

## Statistical methods the excerpt actually lists

TOC is the evidence. Claims below are **librarian paraphrase** of chapter titles + Ch.1, not copied body.

| Station (book) | What it is | Desk implication |
|----------------|------------|------------------|
| Data structures / bars | Clock bars vs information-driven bars; multi-product rolls | We use **1m INDEX / PREMIUM** clock bars. Not dollar/volume bars. INDEX ≠ OPTIDX last. |
| Labeling | Fixed-horizon labels leak; **triple-barrier**; **meta-label** = take/skip | Dual-tape **HOLD** is a skip, not a new strike. Do not treat cluster id as P(win). |
| Sample weights | Overlapping outcomes; label **uniqueness**; sequential bootstrap | Consecutive 1m holds share the same path. One session ≠ independent n. |
| Fracdiff | Stationarity vs memory | Not coded day-1. **DATA_INSUFFICIENT** to claim we fracdiff premiums. |
| Ensembles | Bagging vs boosting; observation redundancy | ML-001 is **KMeans + IsolationForest**, not a boosted live book. |
| **CV in finance** | Standard k-fold **fails** (leak across time). **Purge** overlapping labels; **embargo** a gap after test | Do not grid-search MIX on the same 1m path we score. RETUNE_GATE: no production write. |
| Feature importance | MDI / MDA; substitution | Do not promote a feature because it “explains” in-sample TV-EP. |
| Hyper-parameter search | Grid / random search **inside** purged CV | Nested search on holiday cache = research fraud if we then “OOS” the same days. |
| Bet sizing | Size from predicted probabilities; limits | Paper lots ≠ user lots. No live size. |
| **Dangers of backtesting** | Flawless backtest still often **wrong**; backtest is **not** a research tool; strategy **selection** bias | Honest 2026-09-06 after-cost **FAIL** is the correct language. Win rate in a JSON is not a gate. |
| CPCV / walk-forward | Walk-forward has pitfalls; combinatorial purged CV | We have **not** implemented CPCV. Claiming OOS+NORMAL without SCORE_SAMPLE is **DATA_INSUFFICIENT**. |
| Backtest stats | Implementation **shortfall**; Sharpe / **deflated** Sharpe | 1% RT is our shortfall **proxy**. Deflated Sharpe not computed. |
| Microstructure features (Ch.19 TOC) | Roll, Corwin–Schultz, Kyle/Amihud/Hasbrouck λ, PIN/VPIN, options-market notes | We do **not** have those series from Dhan. Do not invent λ. |

Ch.1 failure mode (paraphrase): hiring many isolated PhDs to each “find a strategy” produces **overfit backtests** (Sisyphus). The alternative is a **factory** (data → features → research → evaluation). That matches KEEP_ALL catalogs + one published ticket, not 151 live Super Orders.

## Leakage checklist for **this** desk

1. Label on bar close and fill the **same** close → look-ahead. We use **next-bar open**.
2. Overlapping 1m premiums: entry and exit share theta/path → uniqueness ≪ trade count.
3. INDEX proxy points scored as if they were option ₹ → instrument leak.
4. Fit MIX / ML on day D, report day D as OOS → selection leak.
5. News/holiday bars in the train fold, “NORMAL” score on the same week without a calendar → regime leak (`NEWS_CALENDAR` still empty).

## Desk map (HYPOTHESIS — not a promote)

| Desk rule | AFML excerpt mapping |
|-----------|----------------------|
| **Next-bar fill** | Tradable label price ≠ signal close. Matches Ch.2–3 spirit (sample at events you could have traded) without claiming we built dollar bars. |
| **1% RT** | Ch.14 lists **implementation shortfall**. 1% premium each way is a **hypothesis cost**, not López de Prado’s formula and not statutory. |
| **FOLLOW-GAP** | Closest analogue is **meta-label skip**: primary lean (index direction) is refused when the option tape does not confirm. Not coded as a second sklearn model. |

ML-001 stays an **overlay**. No deep RL on the 30s path. No embeddings day-1 (FTS5). **NO_PROMOTE.**

## Next team

02 (purged CV wording) · 04 (do not treat ML-001 k as edge) · 06 (leakage in factory harness) · 09.

## UNKNOWN / DATA_INSUFFICIENT

Pages after Ch.1 in this PDF are mostly **TOC**. Full implementations, Python listings, and CPCV math live in the paid book, not extracted here. No claim that our engine is AFML-compliant.

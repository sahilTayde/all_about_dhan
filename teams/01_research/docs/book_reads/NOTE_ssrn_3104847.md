# NOTE — AFML excerpt + Wiley bonus figures (not the full book)

```text
Source:   teams/01_research/docs/ssrn-3104847.pdf
          https://ssrn.com/abstract=3104847
          teams/01_research/docs/GIL2476_AdvancesFinancial_BonusPDF.pdf
Title:    Advances in Financial Machine Learning
Author:   Marcos López de Prado
ISBN:     978-1-119-48208-6 (Wiley, 2018)
This file: 61-page authorized excerpt (praise, TOC, Ch.1 + later TOC)
Bonus:    GIL2476 companion (tables / figures / equations / code snippets)
Layer:    SOURCE_FACT + desk map HYPOTHESIS
Date:     2026-09-14 (re-inventory)
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Inventory (pypdf)

| File | Pages | Chars | Layer |
|------|------:|------:|-------|
| `ssrn-3104847.pdf` | 61 | 118 580 | **TEXT** — excerpt, not full Wiley body |
| `GIL2476_AdvancesFinancial_BonusPDF.pdf` | 218 | 159 026 | **TEXT** — bonus deck of **tables/figures/equations/snippets** |

**This is not “full AFML.”** The bonus PDF is a **figure/equation/snippet pack** (Ch.7–12 material includes purged k-fold, embargo, CPCV commentary). It is **not** a substitute for reading every narrative chapter. Do not paste snippets or Python into FTS / notes.

Workspace already lists `lopez_afml` in `config/workspace.yaml`.

---

## AFML CV — topic depth for this desk

**SOURCE_FACT (excerpt TOC + Ch.1 + bonus headings/snippets, paraphrase).**

| Station | What it is | Desk |
|---------|------------|------|
| Bars | Clock vs information-driven; rolls | We use **1m INDEX / PREMIUM** clock bars. INDEX ≠ OPTIDX last. |
| Labels | Fixed-horizon leaks; triple-barrier; **meta-label** = take/skip | Dual-tape **HOLD** is a skip, not a new strike. Cluster id ≠ P(win). |
| Weights | Overlapping outcomes; uniqueness; sequential bootstrap | Consecutive 1m holds share one path. Session n ≪ trade count. |
| Fracdiff | Stationarity vs memory | Not coded. **DATA_INSUFFICIENT**. |
| **CV** | Standard k-fold **leaks** across time. **Purge** train rows whose labels **overlap** the test interval. **Embargo** a gap after test before the next train. Bonus names `PurgedKFold` + `pctEmbargo` and “embargo of post-test train observations.” | Do not grid-search MIX on the same 1m path we score. |
| Hyper-params | Grid / random search **inside** purged CV (bonus Ch.9 snippets) | Nested search on a holiday cache then calling the same days “OOS” is research fraud. |
| Feature importance | MDI / MDA with purged CV | Do not promote a feature because it “explains” in-sample TV-EP. |
| **CPCV** | Combinatorial purged CV: many purged paths; fewer false discoveries than one walk-forward path (bonus Ch.12 commentary) | **Not implemented.** Claiming robust OOS without SCORE_SAMPLE is **DATA_INSUFFICIENT**. |
| Backtest dangers | Flawless backtest still often wrong; backtest ≠ research tool; selection bias | After-cost FAIL language stays FAIL. JSON win rate is not a gate. |
| Stats | Implementation shortfall; deflated Sharpe | 1% RT is our **proxy** shortfall. Deflated Sharpe **not** computed. |
| Microstructure TOC | Roll, Corwin–Schultz, Kyle/Amihud/Hasbrouck, PIN/VPIN | We **do not** have those series from Dhan. Do not invent λ. |

Ch.1 failure mode (paraphrase): many isolated PhDs each “finding a strategy” → overfit (Sisyphus). Alternative = **factory** (data → features → research → evaluation). Matches KEEP_ALL + **one** published ticket, not 151 live orders.

## Leakage checklist (NIFTY / SENSEX CE/PE)

1. Label on bar close and fill the **same** close → look-ahead. Use **next-bar open**.
2. Overlapping 1m premiums: entry/exit share theta → uniqueness ≪ count.
3. INDEX proxy points scored as option ₹ → instrument leak.
4. Fit MIX / ML on day D, report day D as OOS → selection leak.
5. News/holiday in train, “NORMAL” score on the same week without a calendar → regime leak.
6. Embargo = 0 and shuffle = true on 1m options → **forbidden** even if sklearn defaults look tidy.

## Desk map (HYPOTHESIS — not a promote)

| Desk rule | AFML mapping |
|-----------|----------------|
| Next-bar fill | Tradable label ≠ signal close. |
| 1% RT | Shortfall **hypothesis**, not López de Prado’s formula. |
| FOLLOW-GAP | Meta-label **skip** analog: refuse CE/PE when the option tape does not confirm the index lean. Not a second sklearn model. |
| ML-001 | Unsupervised overlay (KMeans + IsolationForest). Not CPCV. |
| RETUNE_GATE | Proposal only. `production_params_written: false`. |

No deep RL on the 30s path. No embeddings day-1 (FTS5). **NO_PROMOTE.**

## Next team

02 (purged/embargo wording; do not treat bonus snippets as coded) · 04 (ML-001 k ≠ edge) · 06 (factory harness leakage) · 09.

## UNKNOWN / DATA_INSUFFICIENT

Full Wiley narrative + listings beyond the excerpt/bonus. CPCV / deflated Sharpe **not coded**. No claim the engine is AFML-compliant. GIL2476 is a **companion pack**, not “full AFML purchased and ingested.”

# Club — seven books (notes only, not the PDFs)

**Layer:** `HYPOTHESIS` club of `VALIDATION` exam notes  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Copyright:** Do **not** paste PDF or chapter text here. Sibling agents drop **original notes** as `book_reads/*.md`. 02 already holds exam notes under [`book_kb/`](../../../02_phd_math/docs/book_kb/INDEX.md).  
**RAG:** `python -m agent_rag rebuild` then query kind `research_book_notes` (this folder) and `phd_book_kb`.  
**Loop:** 01 [`../RESEARCH_BOSS_LOOP.md`](../RESEARCH_BOSS_LOOP.md) · 00 transition [`../../../00_orchestrator/docs/RESEARCH_BOSS_LOOP.md`](../../../00_orchestrator/docs/RESEARCH_BOSS_LOOP.md) · coverage [`../TOPIC_COVERAGE.md`](../TOPIC_COVERAGE.md)

**On disk 2026-09-14 (re-inventory):** pypdf on every PDF under `teams/01_research/` (`pdftotext` not installed). Allowlist: `book_reads/NOTE_*.md` + this file. No PDF body in FTS. **NO_PROMOTE.**

---

## Inventory (seven titles + companions)

Readable = selectable text (pypdf `extractable_chars` ≫ 0). Image = empty/sparse text layer.

| # | Cite | Sibling note | On-disk file(s) | Pages | Chars | Readable vs image |
|---|------|--------------|-----------------|------:|------:|-------------------|
| 1 | Tulchinsky — *Finding Alphas* | [`NOTE_finding_alphas.md`](NOTE_finding_alphas.md) | `Finding Alphas_ Quantitative Trading Strategies.pdf` | 321 | 61 | **Still image** (Chrome string p.1) |
| 1b | Kakushadze — *101 Formulaic Alphas* | same NOTE | `ssrn-2701346.pdf` | 22 | 48 676 | **TEXT** (companion, not the Wiley book) |
| 2 | Kakushadze/Serur — *151 Trading Strategies* | [`NOTE_ssrn_3247865.md`](NOTE_ssrn_3247865.md) | `ssrn-3247865.pdf` + `(1).pdf` (identical) | 361 | 833 381 | **TEXT** (full SSRN) |
| 3 | Derman — *Models.Behaving.Badly* | [`NOTE_oneil_derman.md`](NOTE_oneil_derman.md) | `oneil-derman.pdf` | 19 | 11 883 | **TEXT** — **slides only**, not the monograph |
| 4 | Gliner — *Global Macro Trading* | [`NOTE_L0002559656.md`](NOTE_L0002559656.md) | `L-0002559656-pdf.pdf` | 30 | 33 094 | **TEXT** — **30-page extract**, not full book |
| 5 | Derman/Miller — *The Volatility Smile* | [`NOTE_volatility_smile.md`](NOTE_volatility_smile.md) | `123456.pdf` | 303 | 0 | **Still image** (Bookey dump) |
| 5b | Orrell/Richards — *Keep on smiling* | same NOTE | `ssrn-4205729.pdf` | 19 | 31 541 | **TEXT** (SPX/VIX paper, not Wiley) |
| 5c | Orrell — *Quantum walk options* | same NOTE | `ssrn-3512481.pdf` | 21 | 39 521 | **TEXT** (adjacent; not a ticket) |
| 6 | Bouchaud et al. — *Trades, Quotes and Prices* | [`NOTE_preview_1108639064.md`](NOTE_preview_1108639064.md) | *(missing)* | — | — | **Still absent** — not full TQP |
| 7 | López de Prado — *AFML* | [`NOTE_ssrn_3104847.md`](NOTE_ssrn_3104847.md) | `ssrn-3104847.pdf` | 61 | 118 580 | **TEXT** — **excerpt**, not full Wiley |
| 7b | AFML bonus figures | same NOTE | `GIL2476_AdvancesFinancial_BonusPDF.pdf` | 218 | 159 026 | **TEXT** — tables/eqs/snippets, **not** full book |

Crosswalk: [`00_CROSSWALK.md`](../../../02_phd_math/docs/book_kb/00_CROSSWALK.md). Playbook: [`08_EXAM_DESK_PLAYBOOK.md`](../../../02_phd_math/docs/book_kb/08_EXAM_DESK_PLAYBOOK.md).

PDFs under `teams/01_research/docs/` stay **out of club FTS**. Do not quote them. Gitignore: `teams/01_research/**/*.pdf`.

---

## Filled from sibling notes (paraphrase — not PDF text)

| Note | Club take (layer) |
|------|-------------------|
| `NOTE_finding_alphas` | Factory / many small alphas / one gate. Wiley still image. **101 paper** is the readable factory companion (delay-0/1, mega-alpha). No live tournament. |
| `NOTE_L0002559656` | Macro **process + bias** excerpt (text). Regime overlay / NEWS_DAY HOLD. Not a 1m entry. Ch.3–12 **DI**. Full Gliner **not on disk**. |
| `NOTE_ssrn_3247865` | 151 is a **descriptive catalog** (no empirical P/L). KEEP_ALL inventory. Buy-first filter: long CE/PE only; shorts/credits off `/`. |
| `NOTE_oneil_derman` | Finance has **models, not theories**. BSM is a metaphor. Dual-tape FOLLOW-GAP = model failed. **Still slides**, not full Badly. |
| `NOTE_volatility_smile` | `123456.pdf` still Bookey **image**. Orrell paper: smile/skew as imbalance↔vol; SPX ATM straddles overpriced vs payout — **warning for long premium**, not a short-straddle ticket. HQ IV still `DATA_INSUFFICIENT`. |
| `NOTE_preview_1108639064` | Object is the **book** (quotes/trades/impact). File **missing** this pass. Next-bar-open + 1% RT **proxy** + FOLLOW-GAP HOLD still stand from prior preview. Not NSE L2. |
| `NOTE_ssrn_3104847` | Purged/embargoed CV; overlapping 1m labels; backtest-as-research danger. GIL2476 confirms snippet-level **PurgedKFold / embargo / CPCV**. CPCV **not** implemented → robust OOS without SCORE_SAMPLE is `DATA_INSUFFICIENT`. |

## What each title is allowed to teach this desk (`book_kb` + notes, not chapters)

| Title | Club takeaway (desk) | Must not become |
|-------|----------------------|-----------------|
| Tulchinsky + 101 | Many **small tested** expressions; **one** production gate; delay-1 ≈ next bar | Hero MIX; porting 101 operators to OPTIDX |
| Kakushadze 151 | **Inventory** / KEEP_ALL catalog + buy-first filter | 151 live Super Orders |
| Derman Badly slides | Model is a **metaphor**; fails at the boundary | “Index move ⇒ buy the option” |
| Gliner excerpt | Macro **regime** overlay; NEWS_DAY HOLD | 1m news-entry alpha; full-book claims |
| Smile + Orrell | Risk is **strike-local**; ATM straddle haircut is real on **their** SPX | Invented IV; short-straddle default |
| Bouchaud (prior) | Object is the **tape** (stale, impact, next-bar) | Touch-fill fantasy SL |
| AFML excerpt + bonus | **Leakage** / purged CV / embargo; ML is features+labels | Auto-retune / RL on 30s; “we implemented CPCV” |

---

## Combined oral (one club, four jobs)

**Strategy.** Kakushadze-style lists + Tulchinsky/101 factory → named `MIX-*` only. Teacher `STRAT-001`–`014` stay `BACKTEST_BOOK`. Customer still one ticket (`MIX-DEFAULT-BUY` until 00+06+09).

**Math.** Smile + Derman Badly + dual-tape: `MIX-FORM-BETA-RESID` ε = r_opt − k r_idx (k = OLS on a **named** book, not a greek). `MIX-FORM-FOLLOW-GAP` HOLD. `MIX-FORM-STRADDLE-RET` is a crude vol proxy, **not** IV. Topics on disk: theta / gamma / delta / vega / intrinsic — null HQ greeks ≠ 0.

**Backtest.** AFML: overlapping 1m labels leak; purge + embargo required in any CV story. 06 scores **OOS + `NORMAL` only**. NEWS_DAY / EXPIRY → `ANALOG_MEMORY`, not `SCORE_SAMPLE`. `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`. One-day paper P/L is not evidence.

**Models.** AFML + Tulchinsky: unsupervised first (`ML-001` KMeans+IsolationForest) as **overlay HOLD**, not BUY_CE/PE. Fit ≠ retune. No production param write from this club.

---

## MIX-* this club may propose (HYPOTHESIS — not new STRAT ids)

Do not mint `STRAT-015+`. If 04 needs a row, it is a **MIX** with origin `PROJECT-DERIVED` unless a Dhan video or exchange clock is the source.

| Candidate family | Why the club allows it | 06 ask |
|------------------|------------------------|--------|
| Existing `MIX-FORM-*` | Already mapped in playbook | Same-session INDEX∩CE∩PE; residual vs FOLLOW-GAP |
| New `MIX-*` from club | Only if sibling notes **or** `book_kb` cite a **testable** expression | OOS + `NORMAL` + costs; what falsifies |
| TV-EP / 151-like lists | KEEP_ALL in the drawer | Premium path TESTED_FAIL is expected, not a catalog delete |

No named new MIX id is **frozen** in this file from this re-inventory. Default: **do not add a catalog row from notes alone.**

---

## UNKNOWN / DATA_INSUFFICIENT

- Tulchinsky **Wiley body** still image; unread chapters.
- Gliner **full book** not on disk; Ch.3–12 **UNKNOWN**.
- Smile **Wiley** formulas: **DATA_INSUFFICIENT** (Bookey image).
- TQP **full + preview file** missing this pass.
- AFML **full Wiley** not on disk (excerpt + bonus only).
- Derman Badly **monograph** not on disk (19 slides).
- Implied vol / HQ greeks series: **DATA_INSUFFICIENT**.
- Kakushadze “retracted” rumor: **VERIFY**.
- CPCV / deflated Sharpe: **not coded**.
- Analog store / SCORE_SAMPLE depth: still thin.
- Live option-fill history: **UNKNOWN**.

When a sibling drops a note, append a dated row under **Sibling arrivals** and re-run `python -m agent_rag rebuild`. Do not paste the book.

---

## Sibling arrivals

| Date | File | Layer | What changed in the club |
|------|------|-------|---------------------------|
| 2026-09-14 | re-inventory (this table) | SOURCE_FACT | TEXT: 151 full, 101, Orrell smile/QW, Gliner extract, Derman slides, AFML excerpt + GIL2476. IMAGE: smile Bookey, Finding Alphas. ABSENT: TQP. Full Gliner/TQP/AFML/Badly/Wiley smile **still not on disk**. |
| 2026-09-14 | `NOTE_finding_alphas.md` | SOURCE_FACT + map | Factory vs one ticket; image-PDF DI; 101 companion |
| 2026-09-14 | `NOTE_L0002559656.md` | SOURCE_FACT + map | Gliner identity; excerpt only |
| 2026-09-14 | `NOTE_ssrn_3247865.md` | SOURCE_FACT + map | 151 title + buy-first taxonomy |
| 2026-09-14 | `NOTE_ssrn_3104847.md` | SOURCE_FACT + map | AFML excerpt + bonus CV snippets |
| 2026-09-14 | `NOTE_preview_1108639064.md` | SOURCE_FACT + DI | Prior preview; file missing now |
| 2026-09-14 | `NOTE_oneil_derman.md` | SOURCE_FACT + map | Derman Badly **slides** |
| 2026-09-14 | `NOTE_volatility_smile.md` | SOURCE_FACT + DI | Bookey still image; Orrell smile paper |

```text
HANDOFF
From:     01 RESEARCH_BOSS club
To:       00 / 02 / 04 / 06 / 09
Accepted: Re-inventory; topic-depth notes; KEEP_ALL; MIX-* only;
  RETUNE_GATE; no PDF ingest; NO_PROMOTE.
Rejected: Auto-perfect; STRAT-015+; quoting PDFs; promoting from notes;
  claiming full Wiley/Gliner/TQP/AFML/Badly from files we have.
UNKNOWN: Unread Tulchinsky chapters; Gliner Ch.3–12; smile Wiley body;
  TQP file; IV series; retraction claim; CPCV not coded.
```

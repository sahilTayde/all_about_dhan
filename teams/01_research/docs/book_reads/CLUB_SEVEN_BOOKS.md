# Club — seven books (notes only, not the PDFs)

**Layer:** `HYPOTHESIS` club of `VALIDATION` exam notes  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Copyright:** Do **not** paste PDF or chapter text here. Sibling agents drop **original notes** as `book_reads/*.md`. 02 already holds exam notes under [`book_kb/`](../../../02_phd_math/docs/book_kb/INDEX.md).  
**RAG:** `python -m agent_rag rebuild` then query kind `research_book_notes` (this folder) and `phd_book_kb`.  
**Loop:** [`../RESEARCH_BOSS_LOOP.md`](../RESEARCH_BOSS_LOOP.md)

**On disk 2026-09-14:** seven sibling notes exist (Tulchinsky sampled images, Gliner 30-page extract, Derman Badly slides, smile Bookey dump, Bouchaud preview, AFML excerpt, 151 SSRN). Club uses those notes **plus** `book_kb`. Allowlist: `book_reads/NOTE_*.md` + this file. No PDF body in FTS.

---

## Inventory (seven titles)

| # | Cite (published work) | Sibling note (`book_reads/`) | 02 exam note on disk | Status |
|---|------------------------|------------------------------|----------------------|--------|
| 1 | Tulchinsky — *Finding Alphas* | [`NOTE_finding_alphas.md`](NOTE_finding_alphas.md) **ON DISK** | `book_kb/01_tulchinsky_finding_alphas.md` | Image-PDF; sampled pages only; unread chapters **DI** |
| 2 | Kakushadze — *151 Trading Strategies* | [`NOTE_ssrn_3247865.md`](NOTE_ssrn_3247865.md) **ON DISK** | `book_kb/02_kakushadze_151.md` | SSRN confirms title; retraction still **VERIFY** |
| 3 | Derman — *Models.Behaving.Badly* | [`NOTE_oneil_derman.md`](NOTE_oneil_derman.md) **ON DISK** | `book_kb/03_derman_models_behaving_badly.md` | 2013 slides (filename is not O’Neil) |
| 4 | Gliner — *Global Macro Trading* | [`NOTE_L0002559656.md`](NOTE_L0002559656.md) **ON DISK** | `book_kb/04_gliner_global_macro.md` | 30-page extract (Ch.1 + Ch.2 open); Ch.3–12 **DI** |
| 5 | Derman/Miller — *The Volatility Smile* | [`NOTE_volatility_smile.md`](NOTE_volatility_smile.md) **ON DISK** | `book_kb/05_volatility_smile.md` | Bookey dump; **DATA_INSUFFICIENT** for Wiley formulas |
| 6 | Bouchaud et al. — *Trades, Quotes and Prices* | [`NOTE_preview_1108639064.md`](NOTE_preview_1108639064.md) **ON DISK** | `book_kb/06_trades_quotes_prices.md` | Cambridge **preview** only (NASDAQ ecology) |
| 7 | López de Prado — *AFML* | [`NOTE_ssrn_3104847.md`](NOTE_ssrn_3104847.md) **ON DISK** | `book_kb/07_afml.md` | Wiley excerpt / TOC + Ch.1 |

Crosswalk already on disk: [`00_CROSSWALK.md`](../../../02_phd_math/docs/book_kb/00_CROSSWALK.md). Playbook: [`08_EXAM_DESK_PLAYBOOK.md`](../../../02_phd_math/docs/book_kb/08_EXAM_DESK_PLAYBOOK.md).

PDFs that may sit under `teams/01_research/docs/` are **out of club**. Do not ingest them into FTS. Do not quote them.

---

## Filled from sibling notes (paraphrase — not PDF text)

| Note | Club take (layer) |
|------|-------------------|
| `NOTE_finding_alphas` | Factory / many small alphas / one gate. PDF text layer empty — club from sampled TOC + `book_kb`. No live tournament. |
| `NOTE_L0002559656` | Macro **process + bias** excerpt. Regime overlay / NEWS_DAY HOLD. Not a 1m entry. Ch.3–12 **UNKNOWN**. |
| `NOTE_ssrn_3247865` | 151 is a **descriptive catalog** (authors: no empirical P/L in the body). KEEP_ALL inventory. Do not Super-Order 151 recipes. Short-premium structures stay off customer default. |
| `NOTE_oneil_derman` | Finance has **models, not theories**. BSM is a metaphor. Dual-tape FOLLOW-GAP = model failed at the boundary. Filename ≠ O’Neil. |
| `NOTE_volatility_smile` | File is a **Bookey** dump, not Wiley body. One vol number is a lie — but we **cannot** calibrate smile from this PDF. HQ IV still `DATA_INSUFFICIENT`. |
| `NOTE_preview_1108639064` | Object is the **book** (quotes/trades/impact), not bar close. Supports next-bar-open + 1% RT **proxy** + FOLLOW-GAP HOLD. Not NSE L2. |
| `NOTE_ssrn_3104847` | Purged/embargoed CV; overlapping 1m labels; backtest-as-research is a danger. CPCV **not** implemented → claiming robust OOS without SCORE_SAMPLE is `DATA_INSUFFICIENT`. |

## What each title is allowed to teach this desk (`book_kb` + notes, not chapters)

| Title | Club takeaway (desk) | Must not become |
|-------|----------------------|-----------------|
| Tulchinsky | Many **small tested** expressions; **one** production gate | Hero MIX that wins one session |
| Kakushadze 151 | **Inventory** / KEEP_ALL catalog | 151 live Super Orders |
| Derman Badly | Model is a **metaphor**; fails at the boundary | “Index move ⇒ buy the option” |
| Gliner | Macro **regime** overlay; NEWS_DAY HOLD | 1m news-entry alpha |
| Smile | Risk is **strike-local**; we **lack** HQ IV series | Invented IV / delta as SOURCE_FACT |
| Bouchaud | Object is the **tape** (stale, impact, next-bar) | Touch-fill fantasy SL |
| AFML | **Leakage** / purged CV; ML is features+labels, not tick params | Auto-retune / RL on 30s |

---

## Combined oral (one club, four jobs)

**Strategy.** Kakushadze-style lists + Tulchinsky factory → named `MIX-*` only. Teacher `STRAT-001`–`014` stay `BACKTEST_BOOK`. Customer still one ticket (`MIX-DEFAULT-BUY` until 00+06+09).

**Math.** Smile + Derman Badly + our dual-tape: `MIX-FORM-BETA-RESID` ε = r_opt − k r_idx (k = OLS on a **named** book, not a greek). `MIX-FORM-FOLLOW-GAP` HOLD. `MIX-FORM-STRADDLE-RET` is a crude vol proxy, **not** IV. Topics on disk: theta / gamma / delta / vega / intrinsic — null HQ greeks ≠ 0.

**Backtest.** AFML: overlapping 1m labels leak. 06 scores **OOS + `NORMAL` only**. NEWS_DAY / EXPIRY → `ANALOG_MEMORY`, not `SCORE_SAMPLE`. `RETUNE_PROPOSAL` stays `BACKTEST_REQUIRED`. One-day paper P/L is not evidence.

**Models.** AFML + Tulchinsky: unsupervised first (`ML-001` KMeans+IsolationForest) as **overlay HOLD**, not BUY_CE/PE. Fit ≠ retune ([`parameter_fit_retune_gate.md`](../../../02_phd_math/docs/book_kb/topics/parameter_fit_retune_gate.md)). No production param write from this club.

---

## MIX-* this club may propose (HYPOTHESIS — not new STRAT ids)

Do not mint `STRAT-015+`. If 04 needs a row, it is a **MIX** with origin `PROJECT-DERIVED` unless a Dhan video or exchange clock is the source.

| Candidate family | Why the club allows it | 06 ask |
|------------------|------------------------|--------|
| Existing `MIX-FORM-*` | Already mapped in playbook | Same-session INDEX∩CE∩PE; residual vs FOLLOW-GAP |
| New `MIX-*` from club | Only if sibling notes **or** `book_kb` cite a **testable** expression | OOS + `NORMAL` + costs; what falsifies |
| TV-EP / 151-like lists | KEEP_ALL in the drawer | Premium path TESTED_FAIL is expected, not a catalog delete |

No named new MIX id is **frozen** in this file until a sibling note exists **and** 02 comments. Default: **do not add a catalog row from this skeleton alone.**

---

## UNKNOWN / DATA_INSUFFICIENT

- Tulchinsky / Gliner **bodies:** unread Finding Alphas chapters; Gliner Ch.3–12. Notes exist; do not invent those chapters.
- Smile Wiley formulas: **DATA_INSUFFICIENT** (Bookey dump / empty extract).
- Implied vol / HQ greeks series: **DATA_INSUFFICIENT**.
- Kakushadze “retracted” rumor: **VERIFY**, not SOURCE_FACT.
- CPCV / deflated Sharpe: **not coded**.
- Analog store / SCORE_SAMPLE depth: still thin.
- Live option-fill history: **UNKNOWN**.

When a sibling drops a note, append a dated row under **Sibling arrivals** (edit this file) and re-run `python -m agent_rag rebuild`. Do not paste the book.

---

## Sibling arrivals

| Date | File | Layer | What changed in the club |
|------|------|-------|---------------------------|
| 2026-09-14 | `NOTE_finding_alphas.md` | SOURCE_FACT + map | Factory vs one ticket; image-PDF DI |
| 2026-09-14 | `NOTE_L0002559656.md` | SOURCE_FACT + map | Gliner identity; excerpt only |
| 2026-09-14 | `NOTE_ssrn_3247865.md` | SOURCE_FACT + map | 151 title confirmed |
| 2026-09-14 | `NOTE_ssrn_3104847.md` | SOURCE_FACT + map | AFML excerpt / purged CV |
| 2026-09-14 | `NOTE_preview_1108639064.md` | SOURCE_FACT + map | Bouchaud preview → next-bar / impact |
| 2026-09-14 | `NOTE_oneil_derman.md` | SOURCE_FACT + map | Derman Badly slides |
| 2026-09-14 | `NOTE_volatility_smile.md` | SOURCE_FACT + DI | Smile identity; formulas DI |
| 2026-09-14 | `NOTE_finding_alphas.md` | SOURCE_FACT + DI | Tulchinsky 2e identity / sampled TOC |
| 2026-09-14 | `NOTE_L0002559656.md` | SOURCE_FACT + map | Gliner excerpt Ch.1 |

```text
HANDOFF
From:     01 RESEARCH_BOSS club
To:       00 / 02 / 04 / 06 / 09
Accepted: Skeleton club of seven titles from on-disk book_kb; KEEP_ALL;
  MIX-* only; RETUNE_GATE; no PDF ingest.
Rejected: Auto-perfect loop; STRAT-015+; quoting PDFs; promoting from notes.
UNKNOWN: Unread Tulchinsky/Gliner chapters; smile Wiley body; IV series;
  retraction claim; CPCV.
```

# NOTE — Finding Alphas (Tulchinsky / WorldQuant)

```text
Source:   teams/01_research/docs/Finding Alphas_ Quantitative Trading Strategies.pdf
Title:    Finding Alphas: A Quantitative Approach to Building Trading Strategies
          (2nd ed.; PDF /Title is “Finding Alphas: Quantitative Trading Strategies”)
Editors:  Igor Tulchinsky et al. (WorldQuant Virtual Research Center)
Publisher: John Wiley & Sons, 2020 (cover / chapter footers on sampled pages)
File:     321 pages, ~56 MB Chrome/Skia print; text layer empty except a
          “Download / Add Search Control” chrome string on page 1
Layer:    SOURCE_FACT (metadata + sampled page images) + desk map is HYPOTHESIS
Date:     2026-09-14
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Identity (this file)

PDF `/Title` matches the Wiley factory book. Cover image: **Finding Alphas**, subtitle **A Quantitative Approach to Building Trading Strategies**, **Second Edition**, **Edited by Igor Tulchinsky et al.**, Wiley. TOC (image OCR of print pages) is a WorldQuant researcher anthology: alpha design, data, turnover, correlation, backtest vs overfitting, biases, robustness, automated search, ML, then asset-class essays (equity, statements, news, options-on-stock, events, **intraday**, **index**, ETFs, futures/forwards) and **WebSim**.

This note is **original**. Do not FTS-ingest the PDF. Do not paste chapter text.

**Read method:** `pypdf` extract_text is **empty** on body pages (image-only print). Notes use metadata + **sampled** page images (intro, design, turnover, overfitting, automated search, WebSim TOC page). Most of the 321 pages were **not** read. Treat unread chapters as **DATA_INSUFFICIENT**.

---

## Alpha factory vs one ticket

**SOURCE_FACT (sampled intro / design / WebSim opener).** The book’s own use of “alpha” is **not** Jensen’s single portfolio statistic. It is a **small coded signal**: math + code + parameters that map data → a position/trade forecast, then many such objects are developed, tested, and (in their shop) allocated. Hypothesis space is treated as huge; most ideas are not alphas. Quality is a **bundle** (simple story, stable to data/params, works across universes/regions, decent in-sample risk-adjusted ratio) — and they still say you cannot know quality until it is **out of sample** and in production.

**WebSim** (Part IV opener, sampled): a shared simulator so many people can **submit and compare** ideas against history and peers. That is a **research tournament / factory**, not “one chartist fires live.”

**Desk map (HYPOTHESIS).** Our analog of the factory is the **catalog**: `STRAT-001`–`014` KEEP_ALL as `BACKTEST_BOOK`, plus named `MIX-*` (TV-EP, FORM, CAS, EQ). The analog of “one ticket” is customer `/` + `MIX-DEFAULT-BUY` until 00+06+09. We do **not** run 23 live votes or a WorldQuant WebSim. Education in this PDF ≠ a Dhan edge.

---

## How to invent expressions

**SOURCE_FACT (sampled Ch.1 tables + construction steps + Ch.5 opener + Ch.15 opener).** Invention is framed as: watch a **data change** that should carry information; write a **tiny expression** (difference, ratio, inverse, lag, correlation, rank with volume); attach an **economic story**; pick a **universe**; test; only then submit. Construction loop they list: analyze variables → idea of how price should react → expression that becomes positions → test → submit if favorable. Search tactics (design chapter): stay near known finds, do not over-dig, use validated cues, still spend some compute on wild theories. Automated search (Ch.15 title page): scale combinatorics, but most auto-finds are **in-sample noise** — the job is quality control, not max Sharpe on the search day.

**Desk map (HYPOTHESIS).** Invent as `MIX-FORM-*` / Python adapters on **INDEX ∩ CE ∩ PE** we actually store (1m last, PCR, ATM). Do **not** dump Pine or WebSim operators onto `/`. 5m Supertrend/MACD/RSI stay **confirm or kill**, not the expression. No invented IV/delta as SOURCE_FACT.

---

## Validation / decay

**SOURCE_FACT (sampled evaluation + Ch.9).** In-sample luck is not OOS. Outliers break models. **Multiple testing**: more search → less chance the “winner” is real. History does not repeat; compute + hindsight + cleaned data **inflate** backtests. Stat-arb assumption: many weak rules, none applies to every name every minute; prefer **ensembles of implementations** of the same idea over one fragile instance. Simulation/backtest is **necessary but not sufficient** to put money on — markets and participants change. Turnover chapter (sampled): costs scale with liquidity and horizon; a short-horizon expression can look good until spread is charged.

They do **not**, in the pages sampled, give a numeric “alpha half-life” for NSE weeklies. **DATA_INSUFFICIENT** for a decay constant.

**Desk map (HYPOTHESIS).** Decay here is **premium theta + 1% RT FAIL**, not index win rate. Score **OOS + `NORMAL`**. NEWS_DAY / EXPIRY out of `SCORE_SAMPLE`. One green paper day is decay theater, not validation.

---

## Apply to Indian index options

**SOURCE_FACT.** TOC lists **index** alphas, **intraday**, **futures/forwards**, and a **stock-options** essay. Sampled body is still **equity-cross-section / WebSim** language (multi-name universes, GOOG/AAPL case-study setup). This file does **not** specify NIFTY / BANKNIFTY / SENSEX weekly CE/PE buy-first, Dhan chain fields, or IST session.

**Desk map (HYPOTHESIS).** Universe = three indices, CE/PE **buy first**, paper/shadow only. Expression families that **might** transfer: residual of premium vs index (`MIX-FORM-*`), rank/z of same-session returns — **after** 06 costs. What does **not** transfer: US stock-factor WebSim, capacity stories, HFT, or “submit to production” language. INDEX last ≠ option last. Weekly death is our decay, not their equity IR.

---

## KEEP_ALL vs live tournament

**SOURCE_FACT.** Factory + WebSim = many candidates, harsh cull, **one** production allocation process. Cutting-losses chapter (sampled): run several theories; **cut** those that exceed a **pre-set** max loss; do not dice-roll a dead belief.

**Desk map (HYPOTHESIS).** KEEP_ALL = **keep the catalog row** (`BACKTEST_BOOK` / `WAITING` / `PARKED`) so we do not delete teacher STRATs because 02/03/09 dislike them. That is **not** a live tournament and **not** “all 14 fire Super Orders.” Kill a **MIX** only after 06 OOS+`NORMAL`. No `STRAT-015+`. WebSim-style peer ranking of MIX-TV-EP is research; it must not write the customer ticket.

---

## RETUNE_GATE

**SOURCE_FACT.** Automated search + overfitting chapters: overnight “thousands of new signals” is how you **manufacture** decay and false discovery. Robustness chapter fragment (sampled): unstable OLS on nonstationary inputs; they discuss robust/quantile-style fits — **not** a license to rewrite live knobs from one fit.

**Desk map (HYPOTHESIS).** Nightly / paper tuner may emit `RETUNE_PROPOSAL` with `status: BACKTEST_REQUIRED`, `keep_current_strategy: true`, `production_params_written: false`. No write to `MIX-DEFAULT-BUY` / `workspace.yaml` from a factory search. Fit ≠ retune. See [`RETUNE_GATE.md`](../../../06_backtesting/docs/RETUNE_GATE.md).

**NO_PROMOTE** until `RESEARCH_READY_FOR_PROGRAMMING` and 09 five-pass. Notes ≠ pass.

---

## Next team

02 (expression families + multiple-testing wording) · 03 (do not treat news/social TOC chapters as India alpha) · 04 (named MIX only) · 06 (OOS+NORMAL + costs on expression families) · 09 (KEEP_ALL).

## UNKNOWN / DATA_INSUFFICIENT

- Full text layer: **unreadable**. Body notes are from **sampled images** only.
- Unread parts: most design/eval chapters, ML, news, options-on-stock, index/ETF/futures essays, WebSim how-to, “seven habits.”
- No WebSim account, no WorldQuant IR series, no claim our paper board is their factory.
- No numeric decay, Sharpe, or capacity for OPTIDX from this file.

# NOTE — Finding Alphas (Tulchinsky) + 101 formulaic alphas companion

```text
Source:   teams/01_research/docs/Finding Alphas_ Quantitative Trading Strategies.pdf
          teams/01_research/docs/ssrn-2701346.pdf  (companion, text layer)
Title:    Finding Alphas: A Quantitative Approach to Building Trading Strategies
          (2nd ed.; PDF /Title “Finding Alphas: Quantitative Trading Strategies”)
Editors:  Igor Tulchinsky et al. (WorldQuant Virtual Research Center)
Publisher: John Wiley & Sons, 2020
Companion: Kakushadze, 101 Formulaic Alphas (SSRN 2701346; Dec 2015)
Layer:    SOURCE_FACT + desk map HYPOTHESIS
Date:     2026-09-14 (re-inventory)
Status:   UNVALIDATED / NO_PROMOTE
Gate:     not RESEARCH_READY_FOR_PROGRAMMING
```

## Inventory (pypdf)

| File | Pages | Chars | Layer |
|------|------:|------:|-------|
| `Finding Alphas_ Quantitative Trading Strategies.pdf` | 321 | 61 | **IMAGE / SPARSE** — Chrome “Download / Add Search Control” on p.1 only |
| `ssrn-2701346.pdf` | 22 | 48 676 | **TEXT** — full paper |

Wiley body is still **unreadable**. Notes on the book remain metadata + **sampled page images** from the earlier pass. Unread chapters stay **DATA_INSUFFICIENT**. The 101 paper **is** readable and is the factory companion (WorldQuant permission stated in that paper). Do not paste Appendix A formulas into FTS.

---

## Alpha factory vs one ticket

**SOURCE_FACT (book, sampled; 101 paper, full).** “Alpha” here is a **small coded object** (math + code + params + data → forecast/position), not Jensen’s single portfolio number. Hypothesis space is huge; most ideas are not alphas. Quality is a **bundle** (story, stability, universe breadth, in-sample risk-adjusted look) and still **unknown until OOS / production**.

The 101 paper makes the factory explicit: many faint, short-lived signals; automation **increases count**; the traded object is a **combined mega-alpha** (internal crossing, diversification), not 101 live Super Orders. Pairwise correlation among their 101 is **low** in their 2010–2013 equity sample (they report ~16% average). Combining many correlated copies is the usual singular-covariance problem.

**WebSim** (book TOC / Part IV, sampled): research tournament / shared simulator. We do **not** run that.

**Desk map (HYPOTHESIS).** Factory analog = catalog `STRAT-001`–`014` KEEP_ALL + named `MIX-*`. One-ticket analog = customer `/` + `MIX-DEFAULT-BUY` until 00+06+09. Education ≠ Dhan edge. Do not mint `STRAT-015+` for each formulaic line.

---

## How to invent expressions

**SOURCE_FACT (book sampled + 101 §2).** Invention: data change that should carry information → tiny expression (diff, ratio, rank, lag, industry neutralize) → economic story → universe → test. 101 alphas are mostly **daily OHLCV + VWAP**; some use cap or a **binary industry** (GICS/BICS/…) neutralize. Coarse split: **mean-reversion** (sign opposite the return used) vs **momentum**. **Delay-0** = data time equals intended trade time (their examples: near the open/close of the same bar). **Delay-1** = trade the **next** session after the last datum. Mixing both inside one expression is common.

They picked 101 for **presentability**; they say myriad **non-formulaic** coded alphas exist.

**Desk map (HYPOTHESIS).** Invent as `MIX-FORM-*` on **INDEX ∩ CE ∩ PE** we store (1m last, PCR, ATM). **Next-bar open** is our delay-1 analog — do not fill the close that generated the lean. 5m Supertrend/MACD/RSI stay **confirm or kill**. Do **not** port Appendix A operators (`correlation`, `indneutralize`, `adv20`, …) onto weekly OPTIDX. Those are **US equity cross-section** recipes. INDEX last ≠ option last.

---

## Validation / decay

**SOURCE_FACT.** In-sample luck ≠ OOS. Multiple testing: more search → winner less likely real. 101 paper: holding periods in their set ~**0.6–6.4 days**; returns **scale with volatility**; **turnover does not explain** returns or pairwise correlations well (their claim). That is **their equity book**, not our weeklies.

**DATA_INSUFFICIENT** for a numeric NSE premium half-life from either file.

**Desk map (HYPOTHESIS).** Decay here is **theta + 1% RT FAIL**, not index win rate. Score **OOS + `NORMAL`**. NEWS_DAY / EXPIRY out of `SCORE_SAMPLE`. One green paper day is not validation. “Mega-alpha” combination without uniqueness / purge is AFML leakage (see `NOTE_ssrn_3104847.md`).

---

## Apply to Indian index options

**SOURCE_FACT.** Book TOC lists index / intraday / futures / stock-options essays — **unread** (image). 101 universe is **stocks**, delay 0/1 on daily bars, industry neutralize.

**Desk map (HYPOTHESIS).** Universe = NIFTY / BANKNIFTY / SENSEX, CE/PE **buy first**, paper/shadow. Families that **might** transfer after 06 costs: residual premium vs index; rank/z of same-session returns. What does **not**: WebSim IR, HFT, industry-neutral stock MR, delay-0 on the **same** 1m close we signal. Weekly death is our decay.

---

## KEEP_ALL vs live tournament

**SOURCE_FACT.** Factory + WebSim + 101 “combine then trade one book.” Cut theories that breach a **pre-set** max loss (book, sampled).

**Desk map (HYPOTHESIS).** KEEP_ALL = keep the **catalog row**. Not 101/151 Super Orders. Kill a **MIX** only after 06 OOS+`NORMAL`. Peer ranking of MIX-TV-EP is research; it must not write `/`.

---

## RETUNE_GATE

**SOURCE_FACT.** Automated search manufactures false discovery. 101: more alphas ≠ more independent bets if you have too few dates.

**Desk map (HYPOTHESIS).** `RETUNE_PROPOSAL` / `BACKTEST_REQUIRED` / `keep_current_strategy: true` / `production_params_written: false`. No write to `MIX-DEFAULT-BUY` from a formula dump. Fit ≠ retune.

**NO_PROMOTE.** Notes ≠ 09 five-pass.

## Next team

02 (multiple-testing + delay wording) · 03 (do not treat news TOC as India alpha) · 04 (named MIX only; no 101 port) · 06 (OOS+NORMAL + costs) · 09.

## UNKNOWN / DATA_INSUFFICIENT

- Wiley text layer still empty.
- Unread book parts: most design/eval, ML, news, options-on-stock, index/ETF/futures essays, WebSim how-to.
- No WebSim account; no claim our paper board is their factory.
- No OPTIDX Sharpe/capacity from either file.

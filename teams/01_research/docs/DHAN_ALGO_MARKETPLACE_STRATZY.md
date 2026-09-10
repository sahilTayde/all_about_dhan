# Dhan Algo Marketplace — Stratzy desk study (2026-09-10)

**Layer tags:** `SOURCE_FACT` = scraped from algos.dhan.co on 2026-09-10. `WEB-DERIVED` = public research found for the concepts. `PROJECT` = our clubs. **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. NO_PROMOTE. No orders. Marketplace returns are **marketing displays, UNVALIDATED** — never customer claims.

Scraped: [algos.dhan.co/managers/stratzy](https://algos.dhan.co/managers/stratzy) · [by-trading-style/option-buying-algo](https://algos.dhan.co/by-trading-style/option-buying-algo) · [by-instrument/nifty-options-trading-algo](https://algos.dhan.co/by-instrument/nifty-options-trading-algo) (via search).

## 1. What is there (SOURCE_FACT)

Stratzy: SEBI RA **INH000009180**, 79 algos on Dhan, "deployed by 12.5K users", min amounts ₹45k–₹2.75L. Four families:

| Family | Named algos | Displayed 1y rolling (UNVALIDATED) |
|---|---|---|
| **Option buying, directional** | SkewHunter, SkewHunter TSL, Settle-Down 40% TSL, Fixed RR 1:3 (30% SL), Vacuum GRID (35% SL), Index Sniper, Seed-Fund 40% SL, Wise-Move 25% TSL, Thrifty 40% TSL, Burst RR 1:2 (25% SL), Burst GRID (30% SL), Only-Calls 40% TSL | +206.74% (Vacuum GRID) down to **−261.19%** (Index Sniper); Only-Calls −36.91% |
| **Credit spreads, hedged directional** | Zen / Curvature / Convex / Mathematician's / Damper / Delta-Leverage / V-Score / Theta-Flux Credit Spread Overnight; Delta-Rotation + Ratio-Fluxer Credit Spread Expiry | Zen +227.25%; Ratio-Fluxer +78.78% |
| **Selling, non-directional** | Expiry Short Strangle, Single Kurtosis Straddle | not shown on scraped pages |
| **Equity** | Alpha Industries Automated | out of desk scope |

**The two disclosed recipes (their own About text, near-verbatim):**

- **Delta-Rotation Credit Spread Expiry** — computes an "alpha" from IV, smile **curvature**, "**Hamiltonian**" (market energy), **eigenvalues**, **entropy**, predicted volatility; plus "alpha2" from spot returns + IV-curvature change; alpha momentum + thresholds → bullish ⇒ credit **put** spread (sell ATM put, buy ITM put), bearish ⇒ credit **call** spread; risk = margin-based SL; target = **50% of max profit** with time-based target expiry; **one open trade at a time**; time/expiry/market-hours filters.
- **Ratio-Fluxer Credit Spread Expiry** — contrarian: fades unsustainable IV states quantified by **ratios of IV entropy, curvature imbalance, skewness**; normalized alpha + skew triggers; sell near-the-money + buy further OTM same type; benefits from range-bound decay.

**SkewHunter** (buy side): "high risk option buying algo that carries trade till end-of-day"; name + family implies IV-**skew**-triggered directional CE/PE buy; TSL variant adds a trailing stop. Exact rules not disclosed.

## 2. The honest lessons in their own data (VALIDATION)

1. **Feed sensitivity flips direction.** Community threads ([431](https://community.stratzy.in/t/specific-clarification-required-on-skewhunter-trade-mismatch-between-stratzy-and-dhanhq/431), [392](https://community.stratzy.in/t/stratzy-app-vs-dhan-hq-same-strategy-taking-different-trade-at-these-two-places/392)): on 23-Jun-2026 the *same* SkewHunter took **24100 CE (loss) on Dhan** and **24200 PE (profit) on Stratzy** because the two platforms used different data feeds. Stratzy's own answer: "our data source is different… we get it via a third-party and Dhan gets it directly from exchange." Desk rule: threshold alphas need a **dead-band/hysteresis**, and our exchange-direct Dhan feed is the only tape we trust.
2. **Selection effect on the buy side.** 1-month rolling returns are negative for ~10 of 12 buying algos while 1-year numbers look shiny. Option buying is regime-dependent; a marketplace shows you the survivors.
3. **One-sided books fail.** "Only-Calls 40% TSL" is −36.91% over 1y — direction symmetry (CE and PE) matters.
4. **Shells repeat.** Every buy algo is wrapped in one of: fixed RR (1:2, 1:3) with 25–40% SL, trailing SL (25/40%), or GRID re-entry. The sell algos all use 50%-of-max-profit targets + margin SL + one-position-at-a-time. The wrapper is as much of the product as the signal.

## 3. What the concepts are, per the open literature (WEB-DERIVED)

| Concept | What we found | Sources |
|---|---|---|
| IV skew → future returns | Steep put-side smirk predicts underperformance (10.9%/yr risk-adjusted cross-sectionally); IV skew is the most predictive option-implied measure over 1w–3m horizons; OTM call−put IV difference is a weak next-day directional signal | Xing/Zhang/Zhao JFQA 2010; Fu, Arisoy, Shackleton, Umutlu 2016; Ratcliff JoD 2013; Cremers-Weinbaum 2010 |
| Skew as regime, not timing | SKEW>145 + VIX deep contango preceded 8/10 major drawdowns 2006–2025 with 2–6 week lead (in-sample) | quantdecoded.com regime study |
| "Hamiltonian / entropy" branding | Real econophysics lineage: Hamiltonian/path-integral pricing (Baaquie's quantum finance), max-entropy fits of the IV surface, HJB↔Black-Scholes. As used by Stratzy it means **statistics of the IV surface shape** (curvature, dispersion/entropy, eigenvalues) driving a normalized alpha | MDPI Entropy 22(11):1283; arXiv 2408.02064, 2307.07103, 0903.4542 |
| 50% max-profit management | 166,768-trade short-put study: per-trade return of managing at 50% is **lower** than holding; the rule only wins via **capital velocity** (redeploying freed margin). Mechanical 50%/2x-credit/21-DTE rules improve drawdown and Sharpe, not per-trade P/L | expireworthless.com 166k study; optionspilot backtests |
| India short-vol evidence | Short strangle beat long strangle at every leg on NIFTY 2007–2019; 5-yr NIFTY study (2020–24) says short strangle wins most regimes; expiry-day 0DTE framework: forecast remaining realized variance at 11:00 anchor, Student-t quantile strikes, **hard 14:30 exit** (last hour structurally adverse) | Bangur SSRN 3768498 + JoIS 2020; EEL 15(1) 2025 study; aprameyap/nifty-0dte-vrp |
| Books to read | Sinclair *Volatility Trading* / *Option Trading* / *Positional Option Trading* (simple robust systems, Kelly sizing, validate before changing rules); Natenberg *Option Volatility and Pricing* (skew, spreads); Baaquie *Quantum Finance* (the Hamiltonian math behind the branding) | — |

## 4. Can we source the inputs from DhanHQ? (03 check)

Per [`DHAN_API_END_TO_END.md`](../../03_phd_market/docs/DHAN_API_END_TO_END.md): the option chain gives **IV per strike, both sides** + OI + greeks + LTP every 3s per unique underlying. So per snapshot we can compute: ATM±k skew tilt (mean OTM-PE IV − mean OTM-CE IV), smile curvature (2nd difference across strikes), IV dispersion/entropy, and their per-tick momentum. Premium tape (1m CE+PE ATM) already persists (`premium_tape.py`). India VIX close is public NSE data. **Gap:** the paper loop persists ATM/PCR snapshots but not the full IV curve — one gather ticket (`chain_iv_stats`) unlocks the whole family. Order-flow delta stays unavailable (unchanged).

## 5. Our clubs (PROJECT — new MIX rows, no STRAT-015+)

See `MIX_CATALOG.md` §21 and [`candidates/MIX-ALGO-SKEW-BUY.md`](../../04_quant/docs/candidates/MIX-ALGO-SKEW-BUY.md):

- **`MIX-ALGO-SKEW-BUY`** — buy-first club of SkewHunter's concept with our machinery: chain IV-skew tilt + tilt momentum picks the side; entry only if the **premium tape dual gate** (MRR/VWAP/ST/EMA/volume) confirms on that side; dead-band against feed flips; EOD hard exit; 40% TSL shell. `BACKTEST_REQUIRED`.
- **`MIX-ALGO-IV-REGIME-HOLD`** — HOLD overlay: flat/low-entropy IV surface + quiet morning realized variance ⇒ decay day ⇒ suppress premium buys. Joins the PCR-hold overlay family. `WAITING`.
- **`MIX-ALGO-RR-SHELL`** — exit-shell club: fixed RR 1:2/1:3 with 25–40% SL, TSL, one-position-at-a-time, no-new-entries-after cutoff, EOD flat. Overlay for paper tickets, joins the SL/TP MIX family. `WAITING`.
- **`MIX-ALGO-CREDIT-PARK`** — the entire credit-spread / strangle / kurtosis-straddle sell family **parked** with citations (India evidence favors short-vol, but seller books are not the buy-first customer mandate; margin + tail risk unmodeled). Joins `MIX-SELL-CREDIT-PARK`. `PARKED`.

## 6. Rejected / UNKNOWN

**Rejected:** copying marketplace return numbers as expectations; deploying/subscribing to any algo; treating "Hamiltonian" branding as secret sauce (it is IV-surface statistics); one-sided books; promoting anything from this study.
**UNKNOWN / DATA_INSUFFICIENT:** exact SkewHunter trigger, strike selection, and SL; Vacuum/Burst GRID re-entry grids; Index Sniper logic (and why it lost −261%); whether Stratzy alphas survive costs on our fills; kurtosis-straddle trigger definition.

# ROUND E35 — Review of the founder's master directive against the evidence (Fable, 2026-11-13)

Reviewed document: `fable_master_prompt.rtf` (25 sections; "Chief Quantitative Researcher ... PhD-level research ... Fable owns the
thinking"). Reviewer: Fable 5.1, the same model that ran E31–E34 and acted as its own adversarial critic (second Fable pass before
every freeze). Evidence base: the registry rows R0–E34 (≈130 experiments, 247,118 priced rule variants, 59,033 priced regime-action
candles), audits A1–A2, discoveries D1–D7. Paper only. This file is the hypothesis-layer record for the round (FILE_CREATION: one
`ROUND<N>_<TOPIC>.md` per round); results stay in the registry.

## 1. Verdict in one paragraph

The directive is a sound description of how an institutional options research desk should work, and most of its methodology is already
how this repo works (frozen hypotheses, realistic fills, walk-forward, multiple-testing control, independent critic, append-only
ledger, NO-TRADE as a first-class decision, the promotion ladder). Where it will fail is not in method but in two facts it does not
yet account for: (a) the history we own cannot observe most of the market states it asks us to classify, and (b) the sample is one
year, so its 80-label regime taxonomy × 40 strategy families is 20–50× more cells than the data can discriminate. The three experiments
that tested "different strategy per regime" at increasing resolution (SC/E21 daily buckets, E31 22 gates × 25 families, E33 15
candle-level cells × 7 actions) all ended at the noise floor, and the one apparent direction signal (E33 Q2) was a 4-minute look-ahead.
The directive's own rule 3.4 — "a classifier that does not improve actual trading outcomes should be rejected" — has, on this data,
already been applied, and the classifier was rejected. The binding constraint is data, not ideas. The highest-value work is therefore
not a 24-module architecture; it is (1) forward tape uptime, (2) one specific data acquisition, and (3) a short, frozen forward
evaluation of the parked leads by the ladder that already exists.

## 2. What to keep from the directive (already in force or adopted now)

| Directive section | Status here | Where |
|---|---|---|
| 6.2 staged research: hypothesis → features before evaluation → limited variants → record failures → correct for multiple testing | in force since E12; E31 used Hansen SPA over every variant of every round | registry, `sweep_lab.py` |
| 10.1–10.3 chronological simulation, realistic fills, intrabar stop handling, look-ahead controls | in force; E33 added a scramble-the-future known-answer check (`playbook_lab.py selftest33`) after its own bug | `sell_lab.struct`, `a2_known_answer.py`, `selftest33` |
| 10.4–10.5 acceptance criteria, deflated Sharpe, bootstrap, walk-forward | in force (E31 DSR, E32–E34 day-block bootstrap, monthly walk-forward) | registry E31–E34 |
| 14.2 independent adversarial review | in force: a second Fable pass critiqued and rewrote every brief before the freeze (E32, E33) | side-session notes `E32_*`, `E33_*` |
| 17 operating modes, 17.1 promotion criteria | in force: paper DESK, rung ladder 0/1/2/5/10 lots, checkpoints 40/80/120 forward trades | `fin1_shadow.decide`, `casino_lab.promote` |
| 19 reporting tables with trades / win % / net / expectancy / drawdown / OOS | in force (E31 family table, E33 105-cell table) | registry, `OUT/sweep`, `OUT/playbook` |
| 21 / 24.9 every iteration must leave a tangible output; report "no edge" honestly | in force | every row |
| 25.2 label the evidence class (underlying-only / theoretical / premium backtest / bid-ask aware / paper / live) | adopted: every registry row states engine and bound mode; "undecidable" is a verdict | registry |

## 3. Where the directive will fail on this project, with evidence

**3.1 Observability.** Of the regime taxonomy in §3.1 and the candle features in §6.1, the following are not in any history we own:
volume profile / value area / POC (no index volume: NIFTY and SENSEX are indices), liquidity sweeps and order-flow imbalance (1-s depth
exists only on the live tape, 8–13 days: E9, E23), market breadth and constituent participation (not recorded), India VIX history
(not recorded), futures OHLCV (not recorded), news with timestamps (none; only the scheduled calendar: RBI, FOMC, expiry, budget), full
option chain beyond ATM±3 (Dhan refuses ATM±4..10 for expired weeklies: D1, 728/728 calls). Everything in §3.1 D ("liquidity and
market structure conditions") and most of §8 is therefore untestable in history and can only be logged forward. The directive must
say this, or the research will "classify" states it cannot see and fit noise to them.

**3.2 Sample size versus taxonomy size.** 246 trading days × 2 indices = 492 sym-days; at 20 decision slots that is 9,840 candle
decisions, of which perhaps 300–600 become non-overlapping trades for any one strategy. §3.1 lists ~80 labels; §4.1 ~40 families; §7.4
asks for statistics by instrument × expiry type × regime × time of day × vol regime × direction × strike method × structure × holding ×
weekday × event. That product is in the thousands of cells for a few hundred trades. E33 already showed what happens at 15 × 7 = 105
cells: the in-sample winners had 90% CIs that excluded zero and were still artefacts. A PhD reviewer's first comment on the directive
would be: state the number of effective comparisons before describing the taxonomy, and size the taxonomy to the data (here: at most
5–8 states, 3–5 actions), or buy more data first.

**3.3 The regime → strategy hypothesis has been tested three times and failed three times.**
- SC / E21 (2026-10-28): 9 and 11 day-level scenario variables × 16 and 10 strategies, learn/test; 0 cells pass after correction.
- E31 (2026-11-12): 22 day-level gates × 25 families × strikes × exits = 247,118 variants; Hansen SPA over all of them p 0.93;
  19.6% of variants t < −2, 0.47% t > +2 (noise gives 2.3% each): buying rules lose ≈ ₹1,568/trade, short vol ≈ +443.
- E32 (12 candle-level events) and E33 (5 regimes × 3 confirmation states, 7 actions incl. naked CE/PE buy and sell, super-order exits):
  events and regimes predict the SIZE of the next 45 minutes (gap reversal bigger, narrow range smaller, p ≤ 0.002), never the sign;
  after the look-ahead fix the confirmation score is null (P(up|BULL) 0.470 vs P(up|BEAR) 0.476, p 0.77); every policy design is
  INCONCLUSIVE or PARKED; E34 showed the confirmation layer is worth no more than shuffled labels.
- The deeper reason is D2 (2026-10-28): rest-of-day volatility is predictable at 09:45 (AUC 0.74–0.87) but option P&L is not (S1 win
  AUC 0.445 out of sample); option prices already carry the predictable part. A regime engine that predicts volatility therefore
  predicts what the premium already prices. That is a structural finding, not a tuning problem.

**3.4 Defined-risk selling (§4.1 C) is undecidable on this history.** Wings 2–3 steps out leave the taped window on the moves that
matter (E1, E5b, E30, E27); bounds, not data, decide the sign. §4.1 C's whole family needs full-chain history before it can be
researched honestly; the directive should list that as a data prerequisite, not as a research scenario.

**3.5 Scope creep is the directive's main risk, by its own admission (§25).** 24 modules, 6 modes, 10 research markdown files, HMMs,
gradient boosting, volume profile engines. The repo already has the minimal correct versions (recorder, panel, `struct` engine, shadow,
DESK, ladder, registry). Every hour spent on architecture is an hour not spent on the only two levers left: more data and more forward
days. Recommendation: do not build §16; do not start §13 (ML) until a feature has shown an out-of-sample effect in a simple model
(none has: E8 logistic AUC 0.445; E31 ML family rejected in round 2).

**3.6 Items the directive gets slightly wrong for Indian weekly index options.** Naked short options (§4.1 C) are the only short
structures the data can price without bounds, so for RESEARCH they must stay in the menu (they did: S1/S2/E33), with the directive's
rule that they are never enabled live before a separate risk review (DESK: rung 0, founder-only). "Volume" on an index means option
volume, which exists (1-min, per strike) and was used (E33 tick-rule flow): null. "Order flow" exists only on the live tape (E9: real at
60 s, smaller than the spread).

## 4. Section 23 — the first assignment, answered from evidence

**A. Existing system.** Implemented and verified: recorder (v2 tape, 1-s depth), 1-year option panel loader, `sell_lab.struct` fill
engine with cons/opt bounds, costs ×1.5 from `config/charges.yaml`, placebo pools, SPA/DSR, walk-forward, forward shadow with
FIN1/S2/B1/SC1/SGATE/IVS leads, DESK decision function with rung ladder and loss limits, docs auditor. Missing: full-chain history,
futures/breadth/VIX history, a news feed, any strategy with evidence, 20+ consecutive forward days (recorder down 10-30..11-12).

**B. Why strategies fail.** Not because of implementation. Because (i) after charges ×1.5 and the measured spread a random intraday ATM
buy loses ₹1.0–1.5k per trade (D4) and no rule in 247k has an edge larger than that; (ii) the predictable component (volatility) is
priced (D2); (iii) the year is one regime (down in 8 of 12 months), so every "sell CE" result is drift; (iv) long holds and wing
structures are unpriceable (D1). The honest summary: on this data, with these costs, the in-history search is exhausted.

**C. Backtesting.** Chronological, bar-by-bar, next-open fills ± p75 half-spread, charges ×1.5, bounds for off-window legs, intrabar
SL for long legs (E33 `long_leg`), stop-beats-target in the same bar, OI lagged 3 min, known-answer tests for every engine path. Two
real defects were found and fixed this week (A2 flatten time 2026-10-28; E33 closed-bar/negative-index look-ahead 2026-11-13). Remaining
limits: spread model from 13 tape days (E23 confirmed ratio 0.77–0.94); no partial fills; no latency; no margin model; the holdout is
spent, so only walk-forward + SPA + placebo remain in history.

**D. Data.** Not sufficient for institutional-quality OPTIONS research beyond ATM±3 intraday with spot exits ≤ 2.5 steps. Required and
missing: 1-min full chain (±10 strikes) with bid/ask for ≥ 2 years, futures 1-min with volume, India VIX 1-min, breadth. Dhan cannot
supply the first (D1). The capability matrix §9.3 asks for is: Dhan = live ladder ATM±5 and 1-min history ATM±3; everything else =
another vendor, to be evaluated against that exact spec before any purchase.

**E. Regime plan.** Already executed at three resolutions (3.3). The validated, useful part is the volatility-size forecast (D2, E32 Q1,
E33 Q1); the useless part is direction. The plan going forward: keep the 5-state E33 regime as a LOG field on the forward tape (PR
#127, on hold), judge it by rule 3.4 after 20+ forward days, and do not add states.

**F. Strategy discovery.** The six scenarios of §25 map onto rows already run: (1) breakout continuation = E5a/ORB grid/B1/B2 (null;
B1 the only positive shrunk stream); (2) mean reversion = E5 fade, TWAP, RSI (null); (3) compression → expansion = B6, E31 ORW gates,
E32 E6 (predicts size, not money); (4) failed breakouts / sweeps = E5b, ORBFADE, PDR (null or undecidable); (5) opening/gap = E31 GAP
family (walk-forward +1.48L p 0.21, parked), E32 E1/E2; (6) expiry = E30, E31 DTE=0 gates, E33 EVENT, IVS lead (log-only). The
remaining in-data hypotheses that are both untested and decidable are few; the three I would still run, frozen, if the founder insists
on more in-history work: (i) defined-risk selling with wings INSIDE ±2 only (decidable, small credit — likely cost-bound); (ii) sizing
by the IV − HAR forecast spread with a 1.5-step exit (E28 hedged version failed; the unhedged sized version is not tested);
(iii) a pure time-of-day theta map on non-expiry days with 1-step exits (E1/E30 covered expiry only). Expected value of all three: low.

**G. Highest-priority work, in order.** 1. Recorder uptime (founder: token) — nothing else moves without it. 2. Freeze the forward
evaluation of the parked leads (B1, SGATE, IVS, GAP-go, E33 LEVEL|BEAR, E33 regime log) by the existing ladder; no new in-sample work.
3. Vendor evaluation against the data spec in D (no purchase until confirmed). 4. Only then, defined-risk selling research (§4.1 C)
on the new data. 5. Decline §16/§13 until a strategy exists.

## 5. Stopping rule for this year's data (frozen)

No further in-history experiment on the 2025-10-27..2026-10-23 panel unless it (a) uses data not yet used (new vendor, new field) or
(b) tests a hypothesis not in the registry with a pre-registered single cell. Everything else is the forward tape.

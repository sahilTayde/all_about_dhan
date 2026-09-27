# Round 8 strategy redesign: results folded in, and the entry edge a buyer actually needs

Layer: **HYPOTHESIS / DESIGN** (paper-only). No engine, config, broker or credential change. Nothing here is a
`VALIDATION` result, a win-rate claim, or a customer ticket.

History of this document (2026-09-27): an adversarial senior-quant review of lab rounds 7 / 7-follow-up / 7B / 7C,
then three founder steers, then the round-8 lab results.
- **Buyer-only desk.** No long ATM holds. Long holds are allowed only as deep ITM or futures comparisons. The centre
  of the desk is active option buying.
- **True friction** (§4.1). ₹2,200 was the average random-entry loss, not the round-trip cost.
- **Round 8 lab report folded in.** `report.md` plus `measured_slippage.json`; preregistration sha256
  `30416a4a…a8b4`, hashed before any out-of-sample result; cumulative trials **3,841**. Paths are under
  `/workspace/dhan/output/lab_round8/` on the lab box.

**Consequence.** The active breakout design in the previous version of this document (BRK-BUY) is **closed**; §1.2
says why. The redesign now has to find **entry edge (direction × magnitude)**, not cost or exit tweaks. Sep 2025-Jul
2026 is **burned** as a holdout, so every new spec here comes with a forward-test flag: can it be evaluated from the
live paper shadow logs (tape recorder plus the depth recorder that starts Mon 28 Sep) without an engine change?

Number tags: **(lab8)** = round-8 report; **(lab)** = earlier rounds; **(arith)** = computed here from the founder's
friction, the lab8 measured decay and spreads, and stated assumptions; **VERIFY** = still to be measured.

Repo paths: engine and picker are `packages/desk-ml/src/desk_ml/paper_scalp.py` and `.../picker.py`; fees
`config/charges.yaml` (exchange 0.03503% vs the founder's 0.0355299%, VERIFY); reusable analyst helpers
`packages/analysts/src/analysts/shadow.py` (`efficiency_ratio()`, `range_over_atr()`, `dealer_gex()`). Cross-team
rules: `teams/04_quant/docs/SIGNAL_STAGING.md` (5m indicators confirm/kill only),
`teams/06_backtesting/docs/EVENT_MEMORY.md` (event days held and scored separately).

---

## 0. Now / Why / Next (plain English)

- **Now.** Round 8 tested the active option-buyer idea properly, with 120 variants, and every one lost money. That
  includes the coil breakout, 2/3/5-minute time stops, partial profit plus trail and re-entry. It lost in 2023-25 and
  on the unseen year, and **it lost before costs** (−₹400 to −₹2,100 per trade gross). Only 46% of coil breakouts go
  further in the breakout direction over 15 minutes. On the unseen year the average move after a breakout went
  *against* it. Deep-ITM and futures long holds also collapsed out of sample (−₹25L and −₹54L).
- **Why.** At measured costs and decay, a buyer must be right about direction on **55-60%** of the moves actually
  held. That covers 3 to 60 minutes and ATM through ITM200 (§2). Our analysts are right 52-53%. No cost trick closes a
  5-8 point accuracy gap. The only direction signal that held up out of sample is open-interest build inside a coil.
  It predicts *which way the coil breaks* (AUC 0.56-0.60), not whether the move continues (AUC 0.50).
- **Next.** Four exact specs, all forward-testable from the Monday shadow logs with no engine change (§3):
  - **E1 COIL-SIDE:** buy *before* the break on the side open interest predicts, and exit *at* the break.
  - **E2 P5-HV:** fade the overnight gap at 09:30 on high-volatility days (positive in both periods, post-hoc).
  - **E3 HV-GATE:** a shadow column that skips the quietest third of days (a loss reducer, not an edge).
  - **E4 QUIET-EXPIRY:** defined-risk premium selling on quiet expiry days. It is writer-side, so it needs a founder
    decision; shadow only.

  The unseen year is spent, so confirmation now takes months of forward data (§3.0). No engine change on Monday.

---

## 1. What round 8 found, and what it changes

### 1.1 Results table (lab8)

| Finding (lab8) | Number | Consequence for the design |
|---|---|---|
| Active buyer family (coil → confirmed breakout → 2/3/5-min time stop → 50% partial + trail → re-entry), 120 variants | All negative in 2023-25 (best A1 −₹10.7L, 670 trades, t −3.0). Preregistered picks on the unseen year: A1 −₹6.0L, A2 −₹10.7L, A3 −₹9.6L; random-entry placebo 1% | **BRK-BUY closed** (§1.2) |
| Losses are gross, not friction | Gross per trade −₹418 (A1, 2023-25) to −₹3,906 (A2, unseen). The S003 and R5 books are also gross-negative on the unseen year (−₹6.9L, −₹2.0L) | Slippage and charge work cannot rescue anything. **Entry edge is the binding constraint** |
| Follow-through of coil breakouts | 46% move on in the break direction over 15 min in both periods; unseen-year mean 15-min move after a break −2 to −3.7 pts (against) | Do not hold for follow-through. Fading the break is also unsupported (side-flip books negative after costs) |
| Time stop (A4) | Same setups with vs without: 2023-25 +₹4.4L, unseen −₹0.48L | Direction right, magnitude irrelevant. Exits do not create edge (optional stopping, §4.3) |
| Passive (bid) entry | 94-96% fill rate; saves ~₹355/trade in spread, loses more to adverse selection (fills cluster on failed breaks) | Maker entries on breakout-style signals are closed |
| Pre-breakout direction model | Unseen AUC **0.595** [0.556, 0.637]; ATM CE open-interest (OI) change alone 0.588; **0.561 with OI strictly before the breakout bar** | The one out-of-sample direction signal. It tells you which way the break goes, so monetise the **break itself** (E1) |
| Pre-breakout follow-through model | AUC 0.507 (2023-25) / 0.502 (unseen) | Magnitude after the break is unpredictable from coil features |
| Chop gate (no trades inside coils) on the 15-min books | S003 −11.5L → −13.4L; R5 +0.8L → −0.5L; ORB15 −30.0L → −27.1L | "Don't trade consolidation" is not a useful filter on these books. Dropped |
| Long-hold controls (deep ITM / futures to end of day) | 2023-25 up to +₹45.7L (t 1.0-1.6, best of 714); unseen: ITM rule −₹24.7L, deep ITM −₹30.6L, futures −₹54.4L | CMP-A/B/FUT **closed**. Long holds are dead in both instruments |
| Measured flat-market decay | ATM −0.072 pt/min (₹117/min at 25 lots); expiry day −0.147; 09:20-10:00 −0.159; ITM100 −0.049; ITM200 −0.036 (−0.026 after 14:00) | §2 uses measured decay. **No buying 09:20-10:00; no ATM on expiry day** |
| Measured spreads (upper bounds; no bid/ask exists in the tapes) | Half-spread ATM 0.20, ITM100 0.30, ITM200 0.35, deep ITM (5-8 strikes) 0.55, OTM 0.05; p90 ~0.65; ATM 0.20 before 12:00, 0.25 12:00-15:00, 0.30 after 15:00 | ATM has the lowest fixed cost per delta (1.28 vs 1.51-1.58 idx pts) but decays fastest. All three strikes need ~1.7 pts at 3 min; **from 5 min on, ITM200 needs the least** (1.8 vs 2.0 at 5 min; 2.2 vs 3.4 at 15 min) |
| True HARI vs other move forecasts (unseen) | Realised 30-min vol R² 0.63 vs 7B EM′ 0.61, EM formula 0.52, implied 0.44 (the ranking reverses in 2023-25) | Use true HARI for magnitude inputs; 7C's export had stored plain HAR |
| Skip the quietest third of days (true HARI) | R5 improves in every slice (2023-25 +₹25.6L, unseen +₹2.2L, Jul-Sep roll +₹5.5L, tape +₹1.6L), still negative; S003 mixed | E3 shadow overlay (a loss reducer) |
| Leads, not findings | P5 overnight reversal positive on high-HARI days in both periods (+₹3.8L / +₹4.2L, post-hoc). Quiet-expiry iron condor / credit spread +₹1.0L / +₹0.7L unseen on 12 / 11 trades | E2 and E4, forward only |

### 1.2 BRK-BUY: closed, and why we do not re-run the exact spec

The lab ran its own active family, not this document's BRK-BUY table (lab8 §L.4 says this doc was not forwarded in
time). The overlap is large: coil prerequisite, volume-burst and premium-expansion confirmations, analyst agreement,
2/3/5-minute time stops, a 50% partial, a trail and re-entry. What was not run exactly: BRK-BUY's writer-covering
confirmation (C4), the fade veto, and the chasing guard. We still do not re-run it:

1. **The losses are gross.** Our own kill rule (previous §1.8) said: "if the move after confirmed breakouts does not
   pay for long gamma, the design is dead; do not rescue it by tuning". The unseen-year mean move after a break is
   *against* the break.
2. **C4 and the fade veto are OI features.** The lab's follow-through model already contained ATM CE/PE OI change and
   the OI put-call change, and scored AUC 0.50. The prior that C4 flips the sign is too weak to justify ~11 more
   trials on a burned period.
3. What survives from BRK-BUY is carried forward: the decay arithmetic, the rule of no buying in the 09:20-10:00
   decay spike, VOLSIZE sizing, and the logged pre-breakout features (they became E1).

---

## 2. The entry-edge requirement (arith on lab8 measured decay and spreads)

### 2.1 Round trip and break-even move

Round trip = founder charges + 2 × slippage s. The table shows s = 0.05 / 0.10 / 0.20 / **MEAS** (measured upper
bound: ATM 0.20, ITM100 0.30, ITM200 0.35). Deltas 0.50 / 0.65 / 0.80 are the ones implied by lab8's break-evens.

| | Charges (pts) | Round trip (opt pts) | Round trip (₹, 25 lots) |
|---|---|---|---|
| ATM (median premium 88) | 0.24 | 0.34 / 0.44 / 0.64 / **0.64** | ₹552 / 715 / 1,040 / **1,040** |
| ITM100 (148) | 0.38 | 0.48 / 0.58 / 0.78 / **0.98** | ₹780 / 943 / 1,268 / **1,592** |
| ITM200 (226) | 0.56 | 0.66 / 0.76 / 0.96 / **1.26** | ₹1,072 / 1,235 / 1,560 / **2,048** |

Break-even index move m*(h) = (round trip + measured decay × h) / δ. Each cell is s = 0.05 / 0.10 / 0.20 / MEAS; the
MEAS column matches lab8.

| Case | Decay (pt/min) | h = 3 | h = 5 | h = 15 | h = 30 |
|---|---|---|---|---|---|
| ATM | 0.072 | 1.1 / 1.3 / 1.7 / **1.7** | 1.4 / 1.6 / 2.0 / **2.0** | 2.8 / 3.0 / 3.4 / **3.4** | 5.0 / 5.2 / 5.6 / **5.6** |
| ATM, expiry day | 0.147 | 1.6 / 1.8 / 2.2 / **2.2** | 2.1 / 2.4 / 2.8 / **2.8** | 5.1 / 5.3 / 5.7 / **5.7** | 9.5 / 9.7 / 10.1 / **10.1** |
| ATM, 09:20-10:00 | 0.159 | 1.6 / 1.8 / 2.2 / **2.2** | 2.3 / 2.5 / 2.9 / **2.9** | 5.5 / 5.7 / 6.1 / **6.1** | 10.2 / 10.4 / 10.8 / **10.8** |
| ITM100 | 0.049 | 1.0 / 1.1 / 1.4 / **1.7** | 1.1 / 1.3 / 1.6 / **1.9** | 1.9 / 2.0 / 2.3 / **2.6** | 3.0 / 3.2 / 3.5 / **3.8** |
| ITM100, 09:20-10:00 | 0.119 | 1.3 / 1.4 / 1.7 / **2.1** | 1.7 / 1.8 / 2.1 / **2.4** | 3.5 / 3.6 / 3.9 / **4.3** | 6.2 / 6.4 / 6.7 / **7.0** |
| ITM200 | 0.036 | 1.0 / 1.1 / 1.3 / **1.7** | 1.1 / 1.2 / 1.4 / **1.8** | 1.5 / 1.6 / 1.9 / **2.2** | 2.2 / 2.3 / 2.5 / **2.9** |
| ITM200, after 14:00 | 0.026 | 0.9 / 1.0 / 1.3 / **1.7** | 1.0 / 1.1 / 1.4 / **1.7** | 1.3 / 1.4 / 1.7 / **2.1** | 1.8 / 1.9 / 2.2 / **2.5** |

Cross-check: the Black-76 decay model in the previous version predicted ATM 0.050 at DTE 2 (measured 0.050), 0.066 at
DTE 1 (measured 0.062) and ITM100 0.049 (measured 0.049). It **missed the 09:20-10:00 spike** (0.16/min), which is the
market marking down the overnight-inflated premium after the open. Rule for every spec: **no option buying 09:20-10:00.**

### 2.2 How accurate must direction be?

If the sign of the move is independent of its size, the expected gross is (2p − 1) · E|ΔS_h|. Break-even therefore
needs **p* = ½ (1 + m*(h) / E|ΔS_h|)**, where p is the probability of being right about the direction of the move
actually held. E|ΔS_h| = EM30 · √(h/30), with median EM30 = 27.4. At "1.5× vol" (a high-HARI day), decay and E|ΔS|
scale by 1.5 and the round trip stays fixed. MEAS slippage throughout.

| Hold h (min) | ATM, median vol | ITM100, median | ITM200, median | ATM, 1.5× vol | ITM200, 1.5× vol | ATM, expiry day |
|---|---|---|---|---|---|---|
| 3 | 59.9% | 60.0% | 59.9% | 57.4% | 56.8% | 62.5% |
| 5 | 58.9% | 58.4% | 58.0% | 57.0% | 55.7% | 62.3% |
| 15 | 58.9% | 56.8% | 55.8% | 57.8% | 54.5% | 64.7% |
| 30 | 60.2% | 56.9% | 55.3% | 59.4% | 54.4% | 68.4% |
| 60 | 62.8% | 57.8% | 55.5% | 62.2% | 54.8% | 74.4% |

Readings:
- **A buyer needs 55-60% directional accuracy on the held move in normal conditions, and 54-57% on high-vol days.**
  Our measured 30-minute skill is 52-53%. The gap is 3-8 points of accuracy, which no cost trick closes: at s = 0.05
  the requirement falls by only about 1-4 points (most at 3-minute holds, ~1 point at 30 minutes).
- **High-vol days help short and medium holds** (fixed costs shrink relative to the move) but not long ATM holds,
  because decay scales with implied vol. That is the arithmetic behind E2 and E3.
- **ATM on expiry day needs 62-74%**: never.
- AUC is not hit rate. For a calibrated balanced classifier, AUC 0.56-0.60 corresponds to roughly 54-57% overall
  accuracy, and the confident tail can be higher. Every spec below therefore trades **only the confident tail** and
  must show its tail hit rate.

---

## 3. Proposed specs (exact, testable, with forward-test flags)

### 3.0 Common definitions

- **Cost model FC-MEAS.**
  - Charges: founder friction (Dhan ₹20/order; STT 0.15% sell; exchange 0.0355299%; SEBI 0.0001%; stamp 0.003% buy;
    GST 18% on brokerage + exchange + SEBI; lot 65).
  - Slippage: headline = **measured** per moneyness from `measured_slippage.json` (ATM 0.20, ITM100 0.30, ITM200 0.35,
    OTM 0.05), plus the time-of-day uplift (ATM 0.25 12:00-15:00, 0.30 after 15:00). Sweeps 0.05 / 0.10 / 0.20
    always reported. Stress = charges × 1.5.
  - Forward: once the depth recorder runs, fills are at the **recorded ask (buy) / bid (sell)** of the first snapshot
    after the signal, plus 0.05 impact at 25 lots. That becomes the primary; FC-MEAS stays the conservative check.
- **Sizing (all specs).** VOLSIZE-7B: lots = clip(round(25 × 27.4 / EM30), 5, 25), with EM30 = true HARI EM30 rescaled
  so its 2023-25 median is 27.4. Capped by CAPLOTS = floor(28,000 / (65 · δ · stop_pts)). Skip if lots < 2.
  Limits: ≤ 25 lots, −₹30k/trade, −₹90k/day, ≤ 3 positions.
- **Global skips.** No option buying 09:15-10:00 (decay spike); no ATM buying on expiry day; event days per
  `EVENT_MEMORY.md` (held and scored separately); no new entries after 14:45.
- **Data periods.** P0 = 2021-09..2023-08 (index only; still clean for *new* price-free rules). P1/P2 = 2023-08..2026-07
  chain (**burned** for these families: the models were fit or seen there, so P1/P2 numbers are descriptive only).
  **FWD** = shadow logs from Mon 28 Sep 2026: the only holdout.
- **Forward shadow evaluation (FWD).** The nightly offline evaluator reads the recorded tapes and depth files, emits
  the spec's hypothetical trades and prices them with FC-MEAS and with depth fills. **No orders and no engine change**
  (E1, E2, E4 need only recorded data; E3 needs only the paper ledger).
- **FWD-BAR (preregistered forward pass bar).** These are the only looks allowed; no parameter changes. A bug fix
  restarts the count.
  1. **n = 30: KILL** if mean gross per trade (before any cost) ≤ 0. Every failed book in rounds 7-8 was
     gross-negative. Otherwise continue.
  2. **n = 60: PROMISING** if net > 0 at depth fills and at FC-MEAS, both 30-trade halves are net > 0, and a side-flip
     placebo (same timestamps, random side, 2,000 draws) is ≥ 90th percentile. Otherwise KILL.
  3. **n ≥ 120: PASS to 09's five-pass** if day-clustered one-sided t ≥ **2.13** (Bonferroni over the 3 forward entry
     candidates E1, E2, E4), net > 0 at stress (charges × 1.5), worst day ≥ −₹90k, and the confident-tail hit rate is
     ≥ the p* in §2.2 for the spec's hold. Report the deflated Sharpe ratio (DSR) with N = 3,841 + round-9 trials.
- **Forward power (arith).** Trades needed for one-sided t = 2.13: 454 at an information ratio (IR) of 0.10 per trade,
  202 at 0.15, 114 at 0.20 and 51 at 0.30. **Only a strong edge can be confirmed within months.** The n = 30 gross-kill
  exists to fail weak ideas fast.
- **Pre-screens on seen or old data** are allowed only as go/no-go for *starting* a forward log. They never count as
  evidence.

### 3.1 E1 COIL-SIDE: monetise the break, not the follow-through

Thesis: open interest (OI) building inside a coil predicts which side breaks (unseen AUC 0.595; 0.561 with OI strictly
before the bar), while what happens after the break is noise or reversal. So be long **during the approach to the break
and out at the break**. Magnitude comes from requiring enough room to the box edge.

| Field | Exact rule |
|---|---|
| Coil | The lab8 coil detector in `r8_active.py`, parameters unchanged (the direction model was fit on its events). |
| Direction model | The lab8 `r8_chop_features.py` logistic regression. Features: range / EM, volume trend, ATM CE and PE OI change, OI put-call change, TWAP slope, position in the day, prior trend, DTE. **OI features lagged to the last snapshot strictly before the decision minute** (the 0.561 variant). Refit once on 2023-08..2026-07, then freeze. Hash the coefficients and the q10/q90 thresholds of in-sample p_up **before Monday**. |
| Decision | Each completed minute while a coil is active and ≥ 5 minutes old, between 10:00 and 14:45. At most **one entry per coil**. |
| Entry / side | p_up ≥ frozen q90 → buy CE; p_up ≤ frozen q10 → buy PE. Fill at the next snapshot (depth ask when available). |
| Magnitude gate | D = distance from the index at entry to the predicted-side box edge + b, with b = max(0.15 × EM30, 4 pts). **Skip if D < 12 index pts** (below that, p* ≥ 58-62%; see economics). |
| Instrument / strike | Nearest weekly expiry, **ITM100** (lower p* than ATM for holds of 10 min or more; see economics). Not on expiry day. |
| Exit | **Target:** first 1-minute close with the index beyond the predicted edge + b → exit at the next snapshot (take the break; no trail, no hold for follow-through). **Stop:** first 1-minute close beyond the opposite box edge → exit. **Time stop:** 15 minutes after entry. Flat by 15:15. |
| Sizing | min(VOLSIZE-7B, CAPLOTS(0.65, box width + b + 3)). |
| Skip | Global skips; coil younger than 5 minutes; a second signal in the same coil. |
| Economics (arith, ITM100, MEAS) | p* = ½ (1 + (0.98 + 0.049 τ) / (0.65 D)), with τ = minutes held. D = 12: 57.9% (τ 5) / 59.4% (τ 10) / 62.6% (τ 20). D = 16: 55.9 / 57.1 / 59.4%. D = 20: 54.7 / 55.7 / 57.5%. ATM needs 0.3-5 points more in each cell. |
| Pre-screen (P1/P2, descriptive only) | With the frozen thresholds: tail side-hit (index reaches the predicted edge + b before the opposite edge) ≥ **58%**, median minutes to either barrier ≤ **12**, median D ≥ 14. If any fails, **do not start** the forward log. |
| Pass bar | FWD-BAR, plus the confident-tail side-hit ≥ p* at the realised median D and τ. |
| Placebos | Side-flip on the same timestamps; random-minute entries inside the same coils with the same exits. |
| Forward-testable from Monday? | **Yes.** It needs 1-minute index bars and ATM CE/PE OI from the tape (snapshots 35-70 s apart). **VERIFY the OI update cadence** (if OI changes less often than every 3 minutes, the lag rule makes the signal stale; log the cadence from day 1). Expected rate: ~5.8 raw coils/day × ~20% tails × D-gate → roughly 0.5-1 trade/day, so n = 30 in ~6-9 weeks and n = 120 in ~6-10 months. |
| Trials | 1 (plus 1 pre-screen, descriptive). |

Tension disclosed: E1 trades *inside* consolidation, against the founder's rule (a) "don't trade consolidation". It is
the direct use of rule (a)'s own logged features, and lab8 showed the chop gate did not help anyway. The forward bar
decides.

### 3.2 E2 P5-HV: fade the overnight gap on high-volatility days

Thesis (Della Corte-Kosowski-Wang overnight-intraday reversal; 7B P5): on volatile days the overnight move partly
reverses in the morning. Post-hoc lab8: P5 positive on high-HARI days in both periods (+₹3.8L / +₹4.2L). Magnitude comes
from restricting to high-vol days, where §2.2's required accuracy is lowest.

| Field | Exact rule |
|---|---|
| Gap | g = 09:15 open − previous close. Trade only if \|g\| ≥ 0.1 × ATR14 (daily) and \|g\| ≤ 2 × ATR14 (larger gaps are news: hold per `EVENT_MEMORY.md`). |
| Vol filter (no look-ahead) | Today's HAR daily-RV forecast, computed **before the open** from daily RV up to yesterday, is in the **top tercile of the trailing 250 sessions**. Secondary report only: true HARI at 09:29. **VERIFY which timestamp lab8 used for its post-hoc high-HARI split.** If it was the 09:59 tercile, that is 29 minutes after the 09:30 entry, i.e. mild look-ahead, and the lead is weaker than it looks. |
| Entry / side | Decision on the 09:30 close; **against the gap** (gap up → PE, gap down → CE); fill at the next snapshot. This is the one sanctioned exception to the 09:20-10:00 no-buy rule, and its cost is priced in: ITM100 decay 0.119/min until 10:00. |
| Instrument / strike | As in 7B P5: engine DTE rule (ITM100 if DTE ≥ 2, else ITM200). ATM never. |
| Exit | As in 7B P5, unchanged (no re-tuning): index stop 1 × EM30 against, index target 2 × EM30, flat 15:15. |
| Sizing | min(VOLSIZE-7B, CAPLOTS(δ, EM30 + 3)). High-vol days give fewer lots (~12-18). |
| Skip | Global event skips; expiry day if the DTE rule would pick ATM (it never does); no second trade per day. |
| Economics (arith) | The W-style exit holds ~38 minutes. On a 1.5×-vol day the ITM100 p* ≈ 56% at 30 minutes (§2.2), i.e. the reversal must be right ~56% of the time. W's break-even hit rate is ~34% (lab), because winners are twice the losers. |
| Pre-screen (P0 2021-23, price-free, not used for this conditional before) | On high-HAR-forecast days: signed index move from 09:31 in the trade direction under W-style barriers has mean ≥ 0.10 EM30, day-clustered t ≥ 2.0, and ≥ 60 events. Fail → do not start the forward log. |
| Pass bar | FWD-BAR. |
| Placebos | Side-flip on the same days; the same rule on **low**-HAR days (it must be worse there). |
| Forward-testable from Monday? | **Yes.** Needs daily closes, the 09:15 open, 1-minute index bars and one option price at 09:31 from the tape. Rate ≈ one third of sessions with a qualifying gap ≈ 5-7 trades/month, so n = 30 in ~5 months and n = 120 in ~1.5-2 years. **Slow**: the n = 30 gross-kill is the realistic horizon. |
| Trials | 1 (plus 1 price-free pre-screen). |

### 3.3 E3 HV-GATE: shadow overlay on the live engine (a loss reducer, not an edge)

| Field | Exact rule |
|---|---|
| Rule | Flag every live paper-engine entry on a day whose pre-open HAR forecast is in the **bottom tercile** of the trailing 250 sessions as "would skip". Never block. |
| Evidence | lab8: skipping the quietest third improved R5 in every slice (+₹25.6L / +₹2.2L / +₹5.5L / +₹1.6L); S003 mixed (unseen −₹2.1L). |
| Forward metric | Net of flagged vs unflagged trades at depth fills. |
| Kill | After 40 flagged trades: kill if the flagged trades' mean net ≥ the unflagged trades' mean net, or if either 20-trade half disagrees. |
| Promote | Never as an "edge". If it survives 3 months it goes to the founder as a risk rule, alongside VOLSIZE-7B (which sizes down on high-vol days; the two are compatible: skip the bottom tercile, size down the top). |
| Forward-testable from Monday? | **Yes.** Needs only the paper ledger and the daily HAR forecast. |
| Trials | 1. |

### 3.4 E4 QUIET-EXPIRY: defined-risk premium selling (writer side; founder decision required)

| Field | Exact rule |
|---|---|
| Rule | lab8 T1 (iron condor on quiet-HARI NIFTY expiry days, stop at 1 × credit) and T2 (credit spread in the S003 direction, same filter and stop), **exactly as preregistered in `r8_theta.py`**, unchanged. |
| Evidence | Unseen +₹1.0L (12 trades) and +₹0.7L (11); 2023-25 ≈ 0 (+₹0.001L on 36; +₹0.3L on 23). Every-day flies and condors lost (−₹2.7L / −₹2.2L). It is the only pattern not negative in either period. |
| Conflict | The founder steer is **buyer-only**. Recommend shadow logging only, with **no capital, even in paper**, until the founder decides. |
| Pass bar | FWD-BAR (n = 30 gross-kill, n = 60 PROMISING, n = 120 PASS). |
| Forward-testable from Monday? | **Yes, but very slowly.** The tape records about ±350 pts of strikes, which covers the wings. Quiet expiry days run at ~1.2/month on NIFTY, so n = 30 takes ~2 years. SENSEX Thursday expiries would roughly double the rate if the SENSEX chain is recorded (**VERIFY**). Honest verdict: not confirmable on a useful timescale. |
| Trials | 2 (T1, T2). |

### 3.5 Closed by round 8 (do not re-run without new data or a new idea)

- **BRK-BUY and the whole coil-breakout family** (§1.2).
- **Passive entries on breakout signals** (adverse selection).
- **The chop gate as a filter.**
- **Fading breakouts** (side-flip negative after costs).
- **Deep-ITM and futures long holds** (CMP-A/B/F/FUT; −₹25L to −₹54L unseen).
- **S003 / R5 / ORB / ZAB / VWAP books** (gross-negative unseen).
- **Every-day premium selling.**
- **Side routers.**
- **Exit or time-stop tuning.**

### 3.6 Logged diagnostics (no spec, no trial until a preregistration)

The E1 evaluator also logs, outside coils, the 30-minute forward index move conditional on the OI-build lean (the same
features). If the OI signal carries direction beyond coils, that shows up here after ~60 sessions and becomes a
round-9 preregistration.

---

## 4. Preserved analysis (condensed from earlier versions)

### 4.1 Friction and instrument choice (founder friction, lab8 spreads)

- Charges at a ₹150 premium: **₹70 per round trip for 1 lot, ₹625 for 25 lots** (reproduced exactly).
- All-in at 25 lots: ₹788 / 950 / 1,275 at s = 0.05 / 0.10 / 0.20. ₹2,200 is the random-entry loss: friction
  ₹1,275-1,590 + ~38 min of decay + stop-fill losses.
- **Fixed cost per index point of delta at measured spreads:** ATM 1.28, ITM100 1.51, ITM200 1.58.
  - Including decay, all three need ~1.7 pts at 3 min; from 5 min on ITM200 needs the least (1.8 vs ATM 2.0 at 5 min;
    2.2 vs 3.4 at 15 min). ATM's cheap entry is eaten by its decay within ~3 minutes.
  - At s = 0.05 for every strike, ATM/ITM100/ITM200 are nearly equal per delta (~0.87-0.91 in the earlier Black-76
    table).
- **Futures:** ~13-14.5 index pts per round trip (futures STT 0.05% of sell value); ₹14.6k at equal exposure (lab8)
  or ₹23k at 25 full lots. Closed for intraday.
- Two repo cost models disagree 7-12× (lab 0.20 pt/side vs `costs.py` 1% of premium per side).

### 4.2 How writers and institutions position (context for E1 and E4)

- **In ranges:** writers sell strangles and straddles. OI builds at the nearest OTM strikes (a call wall above, a put
  wall below), implied vol drifts down and the straddle decays at theta.
- **At breaks:** short-gamma writers cover (OI falls, IV rises) or hedge in futures, which adds fuel. Fresh writing
  into a break signals a fade.
- **Rallies:** put writers roll up, so the floor rises.
- **Gamma sign:** the dealer convention is **UNKNOWN** (the repo's `dealer_gex()` defaults to long calls / short puts,
  a US convention). Log both.
- **Expiry day:** OI concentrates at round strikes. SEBI's 3 Jul 2025 interim order alleged expiry-day index
  manipulation, so split expiry results at that date.
- **Round-8 evidence:** ATM CE OI building before an up-break predicts the break side (AUC 0.588 alone). PE building
  leans down (0.437). None of these features predicts follow-through. That is consistent with writers defending ranges
  and breaks failing more often than they run (46% follow-through). The buyer's use is **E1: the approach to the
  break, not the run after it.**
- OI has no side and its cadence needs verifying.

### 4.3 Exits choose holding time; they do not create edge

For any exit rule τ on a drift-plus-martingale path, E[gross] ≈ δ · μ̇ · E[τ] − decay · E[τ]. Round 7 saw realised win
rate track break-even across 58 geometries. Round 8 saw the time stop help in 2023-25 and not on the unseen year. Both
are this theorem at work. **Edge has to come from the entry.**

---

## 5. Methodology red team (updated)

1. **The unseen year is burned.** Rounds 6 through 8 all selected or evaluated on Sep 2025-Jul 2026. From now on it is
   descriptive. Holdouts are **FWD** and **P0 (price-free, new rules only)**.
2. **Selection on 2023-25 is not informative at this trial count.** The best 2023-25 long-hold book (+₹45.7L, best of
   714) lost ₹35L unseen. At N = 3,841 the expected best null z is √(2 ln N) ≈ 4.1. Treat any 2023-25 "winner" with
   t < 4 as noise.
3. **Power.** Forward confirmation of an IR-0.2 edge needs ~114 trades (E1: months; E2: 1.5-2 years; E4: years). This
   is why FWD-BAR kills on gross at n = 30.
4. **Costs are not the story, and the numbers are upper-leaning.** Measured spreads are upper bounds (no bid/ask in
   any tape). Every failing round-8 book is negative **before costs**, so the verdicts do not depend on the spread
   estimate. The first depth-recorder week should measure true half-spreads by moneyness and time of day. If ATM is
   really 0.05-0.10, every m* in §2.1 moves to the s = 0.05-0.10 cells (0.2-0.6 pts lower). That lowers p* by 1-4
   points and does not change a single verdict.
5. **Look-ahead in post-hoc splits.** The E2 lead may use a 09:59 HARI tercile for a 09:30 entry (VERIFY). E1's
   original 0.595 used OI including the breakout bar; the honest figure is 0.561.
6. **LTP staleness.** Chain and tape prices are last trades, 35-70 s apart, so momentum-style entries get stale
   favourable prices. Depth-fill pricing in FWD removes this.
7. **Structure breaks inside the sample:** SEBI F&O measures (20 Nov 2024); the SEBI interim order on expiry-day
   conduct (3 Jul 2025); NIFTY expiry Thursday → Tuesday (1 Sep 2025); STT increase (1 Apr 2026); lot size 75 → 65.
   Split any expiry- or OI-conditioned result by these dates.
8. **Hit rate is not skill; AUC is not hit rate.** Specs must report the confident-tail hit rate against the p* for
   their hold (§2.2).

---

## 6. Plan from Monday (priority order)

| # | Action | Data | Decision |
|---|---|---|---|
| 1 | Freeze and hash: E1 model coefficients and thresholds, the E2/E3 HAR forecast code, E4 = the lab8 T1/T2 code; this section's FWD-BAR | lab box | Nothing forward counts before the hash |
| 2 | E1 pre-screen (descriptive) | chain P1/P2 | Go/no-go for the E1 forward log (§3.1 thresholds) |
| 3 | E2 pre-screen | P0 2021-23 index, price-free | Go/no-go for the E2 forward log |
| 4 | Depth-recorder week 1: half-spreads by moneyness × time of day × DTE; OI update cadence | recorder, tape | Replace the MEAS upper bounds; E1 is stale if OI updates less often than every 3 minutes |
| 5 | Nightly offline evaluator: E1, E2, E4 hypothetical trades; E3 flags on the paper ledger | tapes, depth, ledger | FWD-BAR checkpoints at n = 30 / 60 / 120 |
| 6 | Founder decision on E4 (writer-side) | — | Shadow-only or drop |

No engine change on Monday or until a spec passes FWD-BAR and 09's five-pass.

---

## 7. Trial budget

| Item | Trials |
|---|---|
| Cumulative after lab8 | 3,841 |
| E1 (+1 pre-screen) | 2 |
| E2 (+1 pre-screen) | 2 |
| E3 overlay | 1 |
| E4 (T1, T2) | 2 |
| **New total** | **≈ 3,848** |

Bonferroni for the forward PASS covers the 3 entry candidates (E1, E2, E4), hence z ≥ 2.13.

---

## 8. Handoff block

- **Accepted:**
  - Round-8 verdicts: the active buyer family, long holds, the chop gate, passive entries and every-day premium
    selling all fail, and the losses are gross.
  - Measured decay and upper-bound spreads.
  - True HARI as the magnitude input.
  - The founder steer (buyer-only) and the founder friction.
  - VOLSIZE-7B as sizing.
- **Rejected:**
  - Re-running BRK-BUY's exact spec (gross-negative family; OI follow-through AUC 0.50).
  - Cost or exit tweaks as the route to profit.
  - Long holds in deep ITM or futures.
  - Fading breakouts.
  - ATM buying 09:20-10:00 or on expiry day.
  - Quoting ₹2,200 as the round trip.
- **UNKNOWN / DATA_INSUFFICIENT:**
  - True bid/ask spreads (depth recorder).
  - OI update cadence.
  - The E1 confident-tail hit rate and time to barrier.
  - The E2 lead's HARI timestamp (look-ahead risk).
  - SENSEX chain availability for E4.
  - The dealer gamma sign.
  - Futures and exercise STT; the exchange rate in `charges.yaml`.
- **Cross-team citations:**
  - 04 `SIGNAL_STAGING.md`: 5m indicators confirm or kill only; E1/E2 use 1-minute index, OI and daily inputs.
  - 06 `EVENT_MEMORY.md`: event days are held and scored separately.
  - 09 five-pass before any paper book.
  - KEEP_ALL untouched: no `STRAT-*` is deleted or relabelled. E1-E4 are research IDs, not `MIX-*` rows, until one
    passes.

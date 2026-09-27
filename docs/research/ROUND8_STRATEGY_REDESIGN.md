# Round 8 strategy redesign: attack the option round-trip cost, not the side

Layer: **HYPOTHESIS / DESIGN** (paper-only). No engine, config, broker or credential change. Nothing here is a
`VALIDATION` result, a win-rate claim, or a customer ticket. Written 2026-09-27 as an adversarial senior-quant review
of lab rounds 7, 7-follow-up, 7B and 7C (uploaded reports; paths under `/workspace/dhan/output/lab_round7*/` on the
lab box). Every number marked **(arith)** is computed below from `config/charges.yaml` and stated assumptions; every
number marked **(lab)** is quoted from the round-7/7B/7C reports; every number marked **VERIFY** must be measured
(mostly by the depth recorder that starts Mon 28 Sep) before it can move a verdict.

Code paths referenced: the engine and picker are `packages/desk-ml/src/desk_ml/paper_scalp.py` and
`packages/desk-ml/src/desk_ml/picker.py` (not `packages/backtest/...`); fees are `config/charges.yaml` =
`packages/desk-ml/src/desk_ml/groww_costs.py`; the other repo cost model is
`packages/backtest/src/backtest_engine/costs.py`. Signal staging rules: `teams/04_quant/docs/SIGNAL_STAGING.md`
(5m indicators confirm/kill only). Event handling: `teams/06_backtesting/docs/EVENT_MEMORY.md`.

---

## 0. Now / Why / Next (plain English)

- **Now.** Our trend analysts really do know a little about direction (52-53% on the next 30 minutes, about 0.02-0.05
  of an expected move per trade). Every way we have tried to buy options on that skill loses, because one round trip
  costs about as much as the skill earns in 30 minutes.
- **Why.** A 30-minute option trade has to earn back about **1.2-1.7 index points** of fixed cost per unit of delta
  (arith). Our measured 30-minute skill is about **0.5-1.4 index points**. No exit rule can fix that: maths (the
  optional-stopping theorem) says an exit only chooses *how long* you hold. It cannot create edge. The only levers
  are: hold longer where the drift keeps growing, pay less per round trip, trade only the strongest signals, or be
  the side that collects the premium.
- **Next.** Run one cheap, price-free test first (§4, T1): does the analysts' drift keep growing from 30 minutes to
  2-4 hours? If yes, the best candidate is a deep-ITM, hold-to-15:15, one-trade-a-day book with small, cap-aware
  size (Family A). If no, directional option buying on these signals is dead and we should stop spending on it.

---

## 1. The cost problem from first principles

### 1.1 Assumptions for the arithmetic

| Item | Value | Source |
|---|---|---|
| NIFTY spot | 25,000 (scale linearly for futures STT) | `option_chain_poller.py` default; VERIFY live |
| Lot / paper size | 65 / 25 lots = 1,625 units | `test_event_parity.py` fixture; `paper_scalp.py` `PAPER_TARGET_LOTS` |
| Implied vol for premiums | 13% Black-76, calendar time | assumption (India VIX-like) |
| Option fees | brokerage ₹20/order, STT 0.15% sell premium, exch 0.03503% both, SEBI 0.0001%, stamp 0.003% buy, GST 18% | `config/charges.yaml` via `groww_round_trip_charges()` |
| Option slippage (lab) | 0.20 pt/side + adverse tick rounding (avg ½ tick = 0.025) | round-6/7 `fill()` (lab) |
| Futures fees | STT 0.05% sell (Budget 2026), exch 0.00173% both, stamp 0.002% buy, SEBI, GST | **not in `charges.yaml`; VERIFY** |
| EM30 | median 27.4 index pts (DEV median of 7B EM′) | lab |
| σ30 (1-sd 30-min move) | EM30 × √(π/2) = 34.3 pts | arith (normal) |
| Net decay b of a long ATM leg (theta minus realised gamma) | 0.11 (DEV) to 0.24 (OOS) option pts per 30 min | arith from lab round-7 D: seller +2.5 / +5.7 pts per straddle over 09:30→15:20 |

Note on b: 7C says implied intraday move ≈ 1.5× realised, which would imply a bleed of ~56% of Black-Scholes theta.
That ratio is inflated by 7C's trading-minute clock (it folds overnight variance into the intraday forecast; 7C says
so). The measured straddle decay above is the ground truth: the intraday variance premium a long leg pays is only
about 0.1-0.25 pt per 30 minutes. **The fixed round-trip cost, not decay, is what kills 30-minute trades.**

### 1.2 Cost per round trip, and per index point of exposure (arith, 25 lots)

| Instrument | Premium | Delta | Fees | Slip (lab 0.20) | Total (opt pts/unit) | **Per index pt of delta** | Per delta at 0.10 half-spread | at 0.50 half-spread |
|---|---|---|---|---|---|---|---|---|
| NIFTY future | — | 1.00 | 14.1 (STT 12.5) | 1.0 (0.5/side, VERIFY) | 15.1 idx pts | **15.1** | 14.3 | 15.1 |
| ATM CE, DTE 2 | 96 | 0.50 | 0.26 | 0.45 | 0.71 | **1.41** | 1.01 | 2.60 |
| ITM100 CE, DTE 2 (engine rule) | 154 | 0.66 | 0.39 | 0.45 | 0.84 | **1.27** | 0.97 | 2.17 |
| ITM200 CE, DTE 1 (engine rule) | 210 | 0.88 | 0.52 | 0.45 | 0.97 | **1.10** | 0.88 | 1.79 |
| ITM200 CE, DTE 0 at 10:00 | 200 | 0.99 | 0.50 | 0.45 | 0.95 | **0.96** | 0.76 | 1.56 |
| OTM200 CE, DTE 2 | 28 | 0.21 | 0.09 | 0.45 | 0.54 | **2.65** | 1.68 | 5.58 |
| Debit call spread ATM/+200, DTE 2 | 68 net | 0.30 | 2 legs | 2 legs | 1.25 | **4.21** | ~2.8 | ~8.2 |
| Credit put spread ATM/−200, DTE 2 | 69 credit | 0.30 | 2 legs | 2 legs | 1.25 (0.62 if both legs expire OTM) | **4.20** | ~2.8 | ~8.2 |
| Iron fly ±300, DTE 2 (4 legs) | 168 credit | ~0 | 4 legs | 4 legs | **2.89** per fly-unit | n/a | | |
| Iron fly ±200, DTE 0 at 10:00 | 85 credit | ~0 | 4 legs | 4 legs | **2.60** per fly-unit | n/a | | |

What this says:
1. **Futures are 10-15× more expensive per index point than options** because futures STT is charged on notional
   (0.05% × 25,000 = 12.5 pts) while option STT is charged on premium (0.15% × 200 = 0.30 pt). 7C's "~14 pts" matches.
   Intraday futures are dead for any signal we have (§1.4 row 1).
2. **Deep ITM near expiry is the cheapest delta we can buy** (0.96-1.10 index pts per delta at lab slippage), because
   delta is ~0.9-1.0 but STT is still on premium. The engine's DTE rule (ITM200 when DTE < 2) already leans this way;
   that is plausibly why it beat ATM and ITM100 "in every segment" (round 7 §5).
3. **Slippage, not statute, is the swing factor for options.** Fees are 0.26-0.52 pt; the lab's slippage is 0.45 pt;
   a realistic range is 0.25-1.05 pt depending on strike, DTE, time of day and 1,625-unit size. The depth recorder
   decides which column is true. The two repo cost models disagree by 7-10×: the lab uses 0.20 pt/side, while
   `costs.py` uses 1% of premium per side (1.5-2.1 pts/side at these premiums). Nobody should cite a backtest without
   saying which one it used.
4. **Spreads double the per-leg friction and cut delta**, so per index point they cost 3-4× a single ITM leg. They are
   only worth it if they remove a larger decay or vega cost than the extra leg adds (§1.5).
5. **The 4-leg fly costs 2.6-2.9 pts (arith), not the 5.4 pts/lot 7C reports.** Either 7C used wider wing slippage,
   the 1.5× stress, or double-counted a leg; it must be reconciled (§4, T7). It does not rescue the fly: 7C's raw edge
   was +0.3 to +0.9 pt.

### 1.3 The one equation: exits choose holding time, they do not create edge

For a position with delta δ on an index path with drift μ̇ (index pts per minute in the signal's direction) plus
martingale noise, the optional-stopping theorem gives, for any exit rule τ (stop, target, trail, time):

    E[gross option P&L] ≈ δ · μ̇ · E[τ]  −  b · E[τ]/30  (+ ½Γ(σ_realised² − σ_implied²)·S²·E[τ], already inside b)
    E[net] = E[gross] − c

So an exit can only change **E[τ]** (and the fill quality of the stops). That is the formal reason round 7 found
"realised win rate tracks break-even within 0-6 points across 58 geometries": a barrier exit reshapes the win/loss
distribution but leaves the mean at drift × expected holding time. Two consequences:

- **The W exit (stop 1 EM / target 2 EM) is a ~38-minute hold.** For Brownian barriers at −a and +b, E[τ] = a·b/σ²
  = (0.80 σ30)(1.60 σ30)/σ30² × 30 min ≈ 38 min (arith, ignoring the 15:15 flat). It harvests about 1.3× the 30-minute
  drift and pays the full round trip, plus extra stop-fill slippage (stops fill at the next bar's open after the
  barrier breaks).
- **Round 7's "54-59% reach +1 EM, half of those still lose" is what a driftless martingale does.** It is not
  "give-back" that a clever exit can capture.

Decomposing the ₹2,200 per random-entry trade (lab) = 1.35 option pts per unit, as a hypothesis to confirm in T2:
fees 0.39-0.52 (arith; lower in DEV at the old 0.0625%/0.10% STT) + slippage 0.45 + decay over ~38 min 0.14-0.30 +
stop-fill and −30k gap-through residual ≈ 0.1-0.35. The skilled analysts claw back ~₹1,000 (0.62 option pts ≈ 0.9
index pts ≈ 0.03 EM30), which is consistent with μ30 ≈ 0.02-0.05 EM30.

### 1.4 Break-even for each idea, and whether our skill clears it

Definitions: c = round-trip cost (option pts/unit), b = decay per 30 min, h = hold (minutes), k(h) = (c + b·h/30)/δ
= break-even mean index move in the signal's direction, p*(h) = Φ(k/σ_h) = break-even **direction** hit rate at that
horizon (the trade win rate at break-even is ~50% for a time exit). σ_h = 34.3·√(h/30).
Measured skill: μ30 = **0.05 EM30 = 1.37 pts** (DEV-like, S003/ZAB/ORB 52-53%) down to **0.02 EM30 = 0.55 pts**
(S003 OOS, t 1.7). Note 52% ⇒ μ30 = 1.72 pts and 53% ⇒ 2.58 pts under normality, but 0.05 EM ⇒ only 51.6%; the
tails are fat. **Money is linear in μ, not in hit rate; stop quoting hit rates as the skill metric.**

| # | Idea | c / δ / b | Required μ (idx pts) | Required μ (EM30) | p*(h) | Skill clears? |
|---|---|---|---|---|---|---|
| 1 | Intraday NIFTY future, 30 min | 15.1 / 1 / 0 | 15.1 | 0.55 | 67.0% | **No** (10-27× short) |
| 1b | Future held to 15:15 (4 h) | same | 15.1 | 0.55 | 56.2% | **No** |
| 2 | ATM option, 30 min | 0.71 / 0.50 / 0.15 | 1.71 | 0.062 | 52.0% | No (DEV marginal) |
| 3 | ITM100, 30 min (engine today) | 0.84 / 0.66 / 0.14 | 1.48 | 0.054 | 51.7% | **No** at 0.02; marginal at 0.05 |
| 4 | Deep ITM (ITM200, DTE ≤ 1), 30 min | 0.95 / 0.88 / 0.08 | 1.17 | 0.043 | 51.4% | DEV-like yes (+0.18 pt); OOS-like no |
| 5 | Debit spread ATM/+200, 30 min | 1.25 / 0.30 / ~0.03 | 4.3 | 0.16 | 54.9% | **No** |
| 6 | Credit spread ATM/−200, 30 min | 1.25 / 0.30 / −0.05 | 4.0 | 0.15 | 54.6% | **No** |
| 6b | Credit spread held to 15:15 (DTE 2) | 1.25 / 0.30 / −0.05 | 2.9 | 0.11 | 51.2% (225-min) | Only if drift accrues (see 7) |
| 7 | **Deep ITM held 120 min** | 0.95 / 0.88 / 0.08 | 1.44 | 0.053 | 50.8% | **Yes iff μ accrues** (linear from 0.02 ⇒ 0.08 EM30) |
| 7b | **Deep ITM held 240 min / to 15:15** | same | 1.81 | 0.066 | 50.7% | **Yes iff μ accrues**; no if flat |
| 8 | Top-decile signals only, ITM100 30 min | as row 3 | 1.48 | 0.054 | 51.7% | Needs top-decile μ ≥ 1.1-2.7× the average; **unknown** (T1) |
| 9 | Maker on both legs, ITM100 30 min, zero adverse selection (fees + tick only) | 0.44 / 0.66 / 0.14 | 0.88 | 0.032 | 51.0% | DEV-like yes; if adverse selection eats half the saving (c ≈ 0.64) ⇒ 1.18 pts, 0.043 EM30 |
| 10 | Quiet-day iron fly, 60 min (7C V3) | 2.6-2.9 (arith) / 5.4 (lab) per fly | raw ≥ 2.6-5.4 pts | n/a | n/a | **No**: measured raw +0.3 to +0.9 (3-18× short) |
| 11 | Iron fly ±200 on expiry day, 10:00→15:15 | 2.60 per fly (3.9 at 1.5×) | raw ≥ 2.6 pts ≈ 3% of an ~85-pt credit | n/a | n/a | **Unknown**: 7C's long straddles lost −8.2L on expiry days (sellers' side), never sliced for sellers (T6) |
| 12 | Deep ITM directional on expiry day (DTE 0), 30 min | 0.95 / 0.99 / ~0 | 0.96 (1.56 at 0.50 half-spread) | 0.035-0.057 | 51.1-51.8% | Plausible only if deep-ITM 0DTE spreads are tight (**VERIFY Monday**) |

How the holding-period lever behaves, deep ITM at lab cost (net option pts/unit per trade; arith):

| μ30 and how drift accrues | 30 min | 60 min | 120 min | 240 min |
|---|---|---|---|---|
| 0.02 EM30, linear (μ ∝ h) | −0.55 | −0.15 | **+0.66** | **+2.27** |
| 0.02 EM30, √h (constant information ratio) | −0.55 | −0.43 | −0.31 | −0.23 |
| 0.02 EM30, flat (all edge in first 30 min) | −0.55 | −0.63 | −0.79 | −1.11 |
| 0.05 EM30, linear | +0.18 | +1.30 | **+3.55** | **+8.05** |
| 0.05 EM30, √h | +0.18 | +0.59 | +1.14 | +1.82 |
| 0.05 EM30, flat | +0.18 | +0.10 | −0.06 | −0.38 |

**The whole redesign hinges on one measurable fact: the shape of μ(h).** The only evidence we have points the right
way but is thin: on the wide book, the move in the trade's direction was +0.02/+0.06 EM at 30 min and +0.14/+0.09 EM
at 60 min (DEV/OOS, t 1.7-4.0; round 7 §3.3), i.e. more than linear from 30 to 60 minutes. On the proxy book OOS it was
flat (+0.10 → +0.11). T1 measures it on 5 years, price-free.

### 1.5 Verdict on each lever

1. **Instrument choice.** For intraday horizons: deep ITM (δ ≥ 0.85, DTE ≤ 1) > ITM100 > ATM ≫ spreads ≫ futures, per
   index point. Futures only make sense for multi-day holds, and even then they pay 15 pts against options' ~1.
   Debit spreads are dominated intraday; their one legitimate use is if T2 shows momentum entries lose > 0.3 pt to
   IV crush (vega), which a spread neutralises. Credit spreads earn decay, but at DTE 2 the −200 wing decays ~70% as
   fast as the ATM leg (φ(0.83)/φ(0) = 0.71), so the net decay is only ~0.3 × b; they only become interesting on DTE 0-1,
   where the wing is nearly worthless.
2. **Holding-period extension.** The strongest lever if (and only if) drift accrues. It collides with the ₹30k
   per-trade cap: at 25 lots the cap is hit after **26 index pts** adverse on ITM100 (δ 0.7) and **21 pts** on
   ITM200 (δ 0.88), i.e. **< 1 EM30**. A 4-hour hold has σ ≈ 97 pts, so at 25 lots the cap is a 0.2σ stop and would
   stop out most trades long before the drift arrives. **Longer holds require smaller size:**
   CAPLOTS = floor(28,000 / (65 · δ · stop_pts)) → 4-6 lots for a 1.5σ stop to the close. Rupees per trade therefore
   do not grow; cost plus decay as a share of gross edge falls from ~100% to ~15-40% (linear accrual from 0.05 / 0.02
   EM30), which is what matters.
3. **Trade-frequency cut.** Helps only if signal strength ranks μ. Needed: top-decile μ30 ≥ 0.054 EM30 (ITM100) or
   ≥ 0.043 (deep ITM). Unknown; T1 measures μ by strength decile. Selecting on strength is one fitted threshold, so it
   is cheap in trials.
4. **Maker/limit entries.** Swing of up to 2 × half-spread per side (≈ 0.4 pt at lab slippage; 0.8 pt if both legs are
   passive). Break-even: 0.8·f − A − (1 − f)·E[missed net] > 0, where f = fill rate, A = adverse selection on
   fills. 7C shows why A is not zero: options lead the index by < 1 minute, so a resting CE bid fills exactly when the
   option flow turns against us. Only the depth recorder can measure A. The one legitimate use of 7C's 57.7%
   next-minute predictor is to **choose when to rest** a passive order, not to take liquidity.
5. **Theta-positive structures on HARI-quiet days.** Measured raw decay is 3-18× below cost on non-expiry days. Dead
   except possibly on expiry day (row 11), where all the remaining time value decays inside one session and there is
   no overnight clock bias. Capacity is small: a ±200 fly with an ~85-pt credit has max loss (200 − 85) × 65 = ₹7.5k per
   lot, so the cap allows 3 lots.
6. **Expiry-day dynamics.** Two separate effects: (a) deep ITM at DTE 0 is a synthetic future at option-premium STT
   with ~zero decay, the cheapest directional delta available (row 12); (b) 0DTE short gamma may carry a real variance
   premium (row 11). Both must be split at the regime dates in §3.9 (Nov 2024 SEBI measures, the Jul 2025 SEBI interim
   order on expiry-day trading, the Thursday→Tuesday switch on 1 Sep 2025). 7B's dte0 cells had a mean OOS direction
   t of −0.41 across its 29 models, so signal quality on expiry days is not assumed.

---

## 2. Ranked strategy families with preregistrable specs

### 2.0 Common definitions (apply to every family)

- **Index.** NIFTY for money (the minute chain exists). BANKNIFTY/SENSEX: price-free replication of the premise only,
  unless their chains exist, in which case the identical spec runs as a replication (not a new trial). SENSEX is on
  BSE (different exchange charge, VERIFY).
- **Signals** (all causal, from 7B `r7b_feat`): `S003_ST3_TWAP`, `ORB30`, `P_ZAB_NOISE`, `VWAP_DEV_MOM`.
  **CONS4** = side where ≥ 3 of 4 vote the same way and none votes the other way. **Strength**
  s = |close_t − TWAP_t| / EM30_t. The ML votes (LOGIT8, LS-GBM) are excluded: they are side-biased (7B §3).
- **EM30** = 7B walk-forward EM′ (preferred, reference 27.4). Sensitivity only: 7C HARI EM30 × 1.123 (reference 30.0).
- **VOLSIZE-7B** = clip(round(25 × 27.4 / EM30), 5, 25).
- **CAPLOTS(δ, stop_pts)** = floor(28,000 / (65 · δ · stop_pts)); ₹2k headroom for stop slippage. For defined-risk
  structures, MAXLOSSLOTS = floor(28,000 / (65 · max_loss_pts)).
- **Lots** = min(VOLSIZE-7B, CAPLOTS or MAXLOSSLOTS). **Skip if lots < 2.** One position per family per index per day.
  Book limits unchanged: ≤ 25 lots, −₹30k/trade, −₹90k/day, ≤ 3 positions.
- **Fills.** Signal on the close of bar t, fill at the option open of bar t+1 (exact-strike chain). Time exits fill
  at the open of the bar after the exit time. Skip the trade if the strike is missing from the snapshot (and log the
  miss rate).
- **Cost model FC1** (forward-looking, the same for all periods): `charges.yaml` **current** rates (STT 0.15%) for
  every period, not era rates; slippage = half-spread table HS + adverse ½ tick. Interim HS (HYPOTHESIS until the
  recorder has ≥ 10 sessions): 0.20 for |moneyness| ≤ 100 and DTE ≥ 1; 0.30 for ITM200+, DTE 0, and wings. 1.5× stress
  = fees × 1.5 and HS × 1.5. Swapping in the measured HS table later is a re-run, not a new trial.
- **Periods.** P0 = 2021-09-06..2023-08-25 (index only). P1 = 2023-08-28..2025-08-31 (chain). P2 = 2025-09-01..2026-07-02
  (chain; **seen by four rounds, now treated as validation, not holdout**). P3 = 2026-07-03..2026-09-25 (index only;
  chain only on the Sep 17-25 tape). FWD = shadow log from Mon 28 Sep 2026: the only clean holdout left.
- **Placebos** (2,000 draws each). PL-SIDE: same times, random side. PL-TIME: same count per day, random start inside
  the family's allowed window, random side, same hold rule. PL-DAY (structure families): random same-count eligible
  days, same entry time and structure.
- **Pass bar (money families).**
  (i) net > 0 at 1.5× on P1 and on P2 separately;
  (ii) pooled P1+P2 day-clustered one-sided t at 1× ≥ **2.39** (Bonferroni α = 0.05/6 families) → **PASS**;
  1.645 ≤ t < 2.39 with every other gate met → **PROMISING** (shadow-log only);
  (iii) PL-SIDE and PL-TIME (or PL-DAY) ≥ 95th percentile;
  (iv) a +1-bar delayed entry keeps ≥ 50% of net;
  (v) worst day ≥ −₹90k and worst trade ≥ −₹40k (gap-through allowance);
  (vi) for directional families, the price-free premise holds on P0 and on P3 with the same sign and t ≥ 1.5;
  (vii) report DSR with the effective trial count N_eff (§3.7) and with raw cumulative N.
  PASS still needs 09's five-pass before any paper book (gate in `.cursor/rules/expert-coalition.mdc`).

### 2.1 Ranking

| Rank | Family | Lever attacked | Why it ranks here | Capacity at ₹30k cap |
|---|---|---|---|---|
| 1 | **A. TREND-HOLD-DEEP** | holding time + cheapest delta + frequency cut | Only design where plausible skill (0.02-0.05 EM30, if it accrues) clears cost with margin; premise testable price-free on 5 years | 4-6 lots, ~1 trade/day |
| 2 | **B. TIMEX** (engine entries, time exit) | holding time | Cheapest decisive test of §1.3; reuses existing round-7 paths; falsifies the thesis fast | 6-9 lots |
| 3 | **C. EXPIRY-FLY-0DTE** | collect the variance premium where it concentrates | Our own data hint (7C expiry-day long-straddle losses); no overnight; defined risk | 2-3 lots, 1/week (NIFTY) |
| 4 | **E. MAKER-ENTRY** overlay | spread capture | Largest cost component (0.45 of ~0.95 pt); needs depth data, overnight test is a proxy only | overlay |
| 5 | **D. QUIET-CREDIT-01** (directional credit spread, DTE 0-1) | decay + direction stacked | Dominated by A at DTE ≥ 2 (§1.5); only DTE 0-1 has enough net decay | 3-4 lots |
| 6 | **F. SWING-DEEP** (1-night deep ITM on trend days) | holding time (days) | Tiny cost vs daily σ (1.1 vs ~200 pts) but gap risk forces 1-2 lots | 1-2 lots |

Rejected outright (numbers in §1.4): intraday futures; debit spreads intraday; credit spreads at 30 minutes;
non-expiry quiet-day flies/condors; long straddles on HARI > implied (lose before costs, 7C); taker trades on the
option-flow signal (edge 0.1 pt vs 0.5 pt cost, 7C); side routers (7B: side is not the binding constraint).

### 2.2 Family A: TREND-HOLD-DEEP

| Field | Spec |
|---|---|
| Premise gate (must pass first, T1) | CONS4 signed index move satisfies μ(to 15:15) ≥ **0.10 EM30** (clears FC1 at 1.5×) and μ(120) ≥ 1.6 × μ(30), day-clustered t ≥ 2.0 on P0 **and** P1, same sign on P2 and P3. If it fails, A and F are closed without a money run (B still runs: it is cheap and tests the exit claim directly). |
| Entry | Decision times {10:15, 11:30, 13:00}. Take the **first** decision of the day where CONS4 speaks and s ≥ q90(s \| CONS4 speaks, P1). q90 is the only fitted number; it is frozen from P1. |
| Side | CONS4 side: CE if up, PE if down. |
| Instrument / strike | Nearest weekly expiry, **ITM200** (NIFTY; δ ≈ 0.85-0.99 at DTE ≤ 2). If DTE ≥ 3, ITM300 (keeps δ ≈ 0.8+). |
| Exit | Time exit 15:15. Catastrophe index stop at 1.5 × EM30 × √(m/30) against, where m = minutes from entry to 15:15 (≈ 113 pts from 11:30, 87 from 13:00). **No target, no signal exit, no trail.** |
| Sizing | lots = min(VOLSIZE-7B, CAPLOTS(0.9, stop_pts)); typical 4-6. Skip if < 2. |
| Skip rule | Preregistered event calendar (RBI policy, Union Budget, election results, index rebalancing day) per `EVENT_MEMORY.md`; skip if the day's open gap > 1.0 × daily ATR14 (gap days are scored separately, not deleted). |
| Break-even | From 11:30 (225 min): μ ≥ 1.8 idx pts (lab cost), 2.0 (FC1 1×, HS 0.30), 2.65 (FC1 1.5×) = 0.066 / 0.073 / 0.097 EM30. |
| Pass bar | §2.0. |
| Placebos | PL-SIDE; PL-TIME over {10:15, 11:30, 13:00} on the same day. |
| Diagnostics (not selectable) | Split by DTE 0 / 1 / 2+; by P1 pre/post 2024-11-20; 4/4 vs 3/4 agreement; exit at 14:15 vs 15:15. |
| Trials | 1 primary. |

Rupee reality check (arith, lab cost, 240-min hold): with linear accrual from μ30 = 0.02 EM30, 4 lots earn about
+2.3 pts × 260 units ≈ ₹590 per trade; from 0.05 EM30, ≈ ₹2,100. At ~150 trades a year that is ₹0.9-3.1L on a ₹6L
account, with per-trade 1σ risk of about ₹22k (4 × 65 × 0.9 × 94 pts). That is an annual Sharpe of roughly 0.3-1.2,
at best. It is also the only design whose cost plus decay is 15-40% of its gross edge rather than 100%+.

### 2.3 Family B: TIMEX (engine entries, pure time exit)

| Field | Spec |
|---|---|
| Entries | Round-7 **wide book** (S003 3m + STRAT-007 clock + no-consolidation + 15-min loss cooldown, **no logit gate**; 1,146 trades). Proxy book (with logit_agree) as secondary report. |
| Side / instrument | Unchanged: book side, engine DTE rule (ITM100 if DTE ≥ 2, else ITM200). The exit is the only change. |
| Exit | **H90**: time exit at entry + 90 min or 15:15, whichever is first. Catastrophe stop = the cap. H90 is fixed a priori (≥ 2× W's ~38-min expected hold). |
| Sizing | lots = min(VOLSIZE-7B, CAPLOTS(δ_entry, 1.5 × EM30 × √3)); typically 6-9. **The same lots are applied to the XS and X0 comparators**, so the comparison isolates the exit. |
| Skip rule | None beyond the book's own filters. |
| Break-even | k(90) ≈ 1.9 idx pts (ITM100, lab cost) ⇒ μ(90) ≥ 0.070 EM30 (p* 51.3%). |
| Pass bar | §2.0, plus Δ vs XS > 0 and Δ vs X0 > 0 at 1.5× on P1 and on P2. |
| Placebos | PL-SIDE; random-exit-time placebo (hold drawn uniformly from 20-150 min). |
| Diagnostics (counted, not selectable) | H60, H120, EOD. |
| Trials | 1 primary + 3 diagnostics. |

### 2.4 Family C: EXPIRY-FLY-0DTE

| Field | Spec |
|---|---|
| Days | NIFTY weekly expiry days only (Thursday before 2025-09-01, Tuesday after). Verdict needs the post-2025-07-03 segment > 0 on its own (n ≈ 40 expiries to 2026-07-02; low power, disclosed). |
| Entry | 10:00 decision, fill at 10:01 option opens. Only if 7C's R = HARI EM(10:00→15:15) / straddle-implied move ≤ 0.8. On 0DTE there is no overnight, so R's clock bias vanishes. |
| Structure | Short ATM CE + ATM PE, long CE ATM+200 and PE ATM−200 (NIFTY), same expiry. |
| Exit | Close all legs at 15:15. Diagnostic only: hold to settlement (OTM legs expire with no exit cost; ITM legs pay exercise STT on intrinsic, rate VERIFY). |
| Sizing | lots = min(VOLSIZE-7B, MAXLOSSLOTS(200 − credit)); typically 2-3. Skip if credit < 40 pts. |
| Skip rule | Open gap > 0.75 × ATR14; event calendar; prior-day India VIX change ≥ +5%. |
| Break-even | raw ≥ 2.6 pts/fly (lab) and ≥ 3.9 at 1.5×; or ≥ 5.4 if 7C's cost figure survives T7. |
| Pass bar | §2.0 with PL-DAY (random eligible expiry days × same time) replacing PL-SIDE/PL-TIME. Also: worst trade ≤ max loss (by construction), and positive in ≥ 2 of the 3 regime segments (pre-2024-11-20, 2024-11-20..2025-07-03, post-2025-07-03). |
| Trials | 1 primary + 1 diagnostic (settle). |

Capacity reality: 3 lots × 65 × (say) 5 pts net ≈ ₹1k per expiry ≈ ₹0.5L/year on NIFTY alone. This is a diversifier
to learn from, not the business, unless the cap is revisited for defined-risk structures (founder decision, not ours).

### 2.5 Family E: MAKER-ENTRY overlay (on A or B signals)

| Field | Spec |
|---|---|
| Rule | On signal, rest a buy limit at the best bid (depth data) for up to 3 minutes. Cancel if unfilled (**no chase**). If 7C's OFL score says the option should dip next minute (p_up < 0.5 for CE; > 0.5 for PE), keep resting; otherwise rest one minute only. Time exits: rest at the best ask from T−10 min, cross at T. Stops always cross. |
| History proxy (overnight, labelled PROXY) | LTP only: a fill happens if a later snapshot's LTP ≤ limit − 1 tick (trade-through); limit = LTP_t − 0.05. This understates adverse selection and cannot see queue position, so it **cannot pass** on history. It only bounds the idea. |
| Break-even | 0.8·f − A − (1 − f)·E[net of missed trades] > 0; A = mean mid move against us in the 3 minutes after a fill. |
| Pass bar (depth data, ≥ 20 sessions) | Per-signal net improvement vs taker (unfilled trades count at their taker P&L as "missed") ≥ +0.2 opt pt, f ≥ 60%, both 10-session halves positive. |
| Trials | 1 (on depth data); the proxy is a diagnostic. |

### 2.6 Family D: QUIET-CREDIT-01 (directional credit spread, DTE 0-1)

| Field | Spec |
|---|---|
| Entry | 11:30 decision; CONS4 speaks; DTE ∈ {0, 1}; R ≤ 0.8. |
| Structure | Bullish: short ATM PE, long PE ATM−200. Bearish: short ATM CE, long CE ATM+200. |
| Exit | 15:15; catastrophe: close if the index moves 1.5 × EM30 × √(m/30) against. |
| Sizing | min(VOLSIZE-7B, MAXLOSSLOTS(200 − credit)); skip if credit < 30. |
| Break-even | (c − net decay)/δ ≈ (1.25 − 0.6..0.75)/0.30 ≈ 1.7-2.2 pts ⇒ μ(225 min) ≥ 0.06-0.08 EM30 (DTE 0-1 net decay is roughly double the DTE-2 value because the wing is nearly worthless). |
| Pass bar / placebos | §2.0; PL-SIDE (the short leg on the random side). |
| Trials | 1. Run only if T1 and T6 are both non-negative. |

### 2.7 Family F: SWING-DEEP (one night, deep ITM)

| Field | Spec |
|---|---|
| Premise gate (T9, price-free, 5 years) | After a "trend day" (\|C − O\| / (H − L) ≥ 0.6 and \|C − O\| ≥ 0.6 × ATR14), the next-day open→15:15 move in the trend direction has mean ≥ 0.02 × daily σ with t ≥ 2 on P0 and P1. |
| Entry | 15:20 on a trend day; buy ITM300 on the next weekly expiry that is ≥ 2 sessions away (δ ≈ 0.9). |
| Exit | Next session 15:15. Catastrophe: −₹28k mark. |
| Sizing | min(VOLSIZE-7B, CAPLOTS(0.9, 1.5 × (overnight σ + day σ) ≈ 300 pts)) ⇒ 1-2 lots. |
| Break-even | ~1.2 idx pts vs next-day σ ≈ 200 ⇒ 0.006σ. The cost bar is trivial; the risk and capacity are the problem. |
| Trials | 1 (only if the premise passes). |

### 2.8 Trial budget for round 8

6 money primaries (A, B, C, D, E, F) + 5 money diagnostics (B ×3, C ×1, E-proxy ×1) + about 40 price-free premise
estimates (T1: 5 signal sets × 7 horizons + strength deciles; T9) ⇒ **≈ 51 new trials; cumulative ≈ 2,703**.
Preregister with a sha256 hash before computing anything (the round-7 practice). The price-free estimates are the
evidence base, not selections; report them all.

---

## 3. Red team: where we are fooling ourselves, in both directions

### 3.1 The "OOS" year is burned (too lenient)
Sep 2025-Jul 2026 has now been examined by rounds 6, 7, 7-follow-up, 7B and 7C. The W exit was picked after seeing
the OOS geometry map (7B critique point 4), and "stop 1 EM / target 2 EM" was named as robust from OOS ranks (round 7
§3.2). Every later look leaks. From round 8 on, treat P2 as validation. The clean holdouts are: price-free P0 (for
horizons and consensus rules 7B never scored), price-free P3, and forward shadow.

### 3.2 The bar has almost no power for real but modest edges (too strict)
Minimum detectable edge (arith, one-sided):

| Sample | z = 1.645 | z = 2.39 (Bonferroni over 6) |
|---|---|---|
| 200 trades / 0.85 years (a typical OOS book) | IR/trade 0.116, annual SR 1.78 | IR 0.169, SR 2.59 |
| 700 trades / 2.85 years (chain window) | IR 0.062, SR 0.97 | IR 0.090, SR 1.42 |
| 1,250 days / 5 years (price-free) | IR 0.047, SR 0.74 | IR 0.068, SR 1.07 |

PF ≈ 1 + 2.5 × IR per trade (normal approximation), so **"PF > 1.2 at 1.5× costs" alone demands a net IR ≈ 0.08 per
trade, roughly an annual Sharpe of 1.8 after stressed costs at ~500 trades a year**. That is a top-decile hedge-fund
bar. For a strategy with a true full-sample t of 2 over 3 years (Sharpe ~1.2), the gates pass with roughly these
probabilities: DEV > 0 ≈ 0.95 (t 1.63), OOS > 0 ≈ 0.87 (t 1.15), both OOS halves > 0 ≈ 0.63, placebo ≥ 90th pct
≈ 0.45, PF ≥ 1.2 at 1.5× ≈ 0.25. The product is ≈ 0.06; the gates are positively correlated, so the joint pass rate is
roughly **5-15%** (arith). So "nothing passes" is partly a power ceiling, not proof of no edge. The fix is **fewer, pre-committed
trials with one primary endpoint** (§2.0), not a lower bar: with N = 2,652 trials the expected best null z is
√(2 ln N) ≈ 3.97.

### 3.3 Reduced-form P&L backtests waste the data (too strict, fixable)
Net ₹ = δ·μ·τ − c − b·τ. The noisy term is μ (direction). The cost terms c and b are **low-variance** and can be
measured precisely from the chain and the depth feed. Estimate μ(h) on 5 years of index bars (price-free, n ≈ 1,250
days × several decisions), and c and b from the chain; then the P&L follows by multiplication. That uses the 5-year
index history, which the money backtests throw away because it has no option prices. Reduced-form money runs stay as
the confirmation, not the discovery tool.

### 3.4 Biased cost model (both directions)
- **Two cost worlds in the repo:** lab 0.20 pt/side vs `costs.py` 1% of premium per side (7-10× more). Pick one per
  report and say which.
- **Flat slippage is wrong in both directions:** probably too generous for ITM200/ITM300 at DTE 0-1, at 09:15-09:30
  and 15:00+, and for 1,625 units (it may exceed top-of-book on ITM strikes), and too harsh for ATM (typically 0.05-0.10
  half-spread). The engine's DTE rule sends expiry-adjacent trades to exactly the strikes where 0.20 is most doubtful.
- **STT eras:** 0.0625% until 30 Sep 2024, 0.10% until 31 Mar 2026, 0.15% after (Budget 2024 and Budget 2026;
  `groww_costs.py` carries only the 2026 rate and says "VERIFY vs older slabs"). At a 200-pt
  premium the step from the DEV-era rate to today's is +0.175 pt per trade = ₹284 at 25 lots. DEV results priced at
  era rates overstate what the same trades would earn going forward. Use FC1 (current rates for all periods) for
  decisions.
- **Fly cost:** 7C's 5.4 pts/lot vs 2.6-2.9 by arithmetic. Reconcile (T7).
- **Missing items:** exercise STT for settle-to-expiry legs, BSE vs NSE charges for SENSEX, IPF/clearing (small).

### 3.5 Exact-strike proxy issues (direction of bias partly unknown)
- **LTP staleness favours momentum entries.** Chain prices are last trades. On thinner ITM strikes the LTP can lag
  the index by a minute or more. A trend signal fires right after an index move, so a stale LTP is a price from
  *before* the move: a favourable entry that could not really be had. 7C found options lead the index at ATM; that
  need not hold at ITM200. T3 measures it. If the bias is ≥ 0.2 pt, every momentum-entry backtest is optimistic by
  that much.
- **Strike leaves the window.** With 13-15 strikes (±350 pts), an ITM200 contract drifts off the recorded window
  after a ~150-pt move, and those trades are the biggest winners and losers. Log how each is priced (dropped? rolling
  series?).
- **"Option open at t+1"** from a 60-second LTP snapshot is not a quote. It is a trade price at an unknown time
  inside the minute.
- **Chain ends 2026-07-02**; Jul-Sep 2026 uses the rolling series with its ~2.7 pt/trade gamma bias (round-7
  errata). Never mix it into money verdicts.

### 3.6 The 1×/2× exit (W) is not neutral (too strict for trend signals)
W is a ~38-minute hold with next-bar stop fills. It tests the one horizon where our measured drift is weakest
relative to cost. Hit rates of 30-35% against a 34% break-even just restate μ ≈ 0 at that horizon. Separately, at
25 lots the ₹30k cap hits after 21 index pts on ITM200 (< 1 EM30), so on DTE < 2 trades **the cap, not W, is the real
stop**. The cap silently tightens the stop on exactly the expiry-adjacent days where moves are largest.

### 3.7 Trial-count inflation (DSR is right to be ≈ 0, for a different reason)
The raw cumulative N (2,652) counts highly correlated trials (58 geometries on one entry list; 1,450 overlapping
skill-map cells). An effective N from the trial-return correlation matrix (eigenvalues explaining 90% of variance, or
ONC clustering) is probably 100-300. That lowers the expected best null z only from 3.97 to about 3.0-3.4, and every
OOS Sharpe so far is far below that. So DSR ≈ 0 is robust to the N choice. The real inflation is adaptive reuse of one
year (§3.1), which DSR does not model.

### 3.8 Placebo and shift tests
- The +1-bar test is lenient on chain prices (a 1-minute bounce often improves the fill; 7B said so). Keep it, but it
  should never be the binding "pass".
- Random-side placebos keep the timing, so a strategy that times high-vol windows can pass PL-TIME by being long
  gamma, not by knowing direction. 7B already requires both placebos. Keep that.
- Momentum entries buy after the index has moved, often after IV has jumped. The IV mean-reversion after entry is a
  hidden vega cost that no side placebo isolates. T2 measures it; if it is > 0.3 pt, debit spreads or lower-vega deep
  ITM are the fix.

### 3.9 Market-structure breaks inside the sample (both directions)
- 20 Nov 2024 SEBI F&O measures: one weekly expiry per exchange (BANKNIFTY weekly ended), larger contracts, upfront
  premium, extra expiry-day margin on shorts. This is inside P1.
- 3 Jul 2025 SEBI interim order on alleged expiry-day index manipulation (Jan 2023-May 2025 conduct). Expiry-day
  patterns in P1 may not recur.
- 1 Sep 2025 NIFTY expiry moved from Thursday to Tuesday (SENSEX to Thursday). This is **exactly the P1/P2 boundary**,
  so every DTE- or weekday-conditioned rule changes meaning across the split.
- 1 Apr 2026 STT increase (options 0.15%, futures 0.05%). Lot size 75 → 65.
- Any expiry or DTE result must be reported by these segments.

### 3.10 Edge we may be throwing away
1. **The 60-minute drift on the wide book (t 2.5-4.0)** was only ever monetised through barrier exits and 25-lot
   sizing that the cap turns into a sub-1-EM stop. It has never been held with a pure time exit at cap-aware size.
   Families A/B test exactly this.
2. **Vol-managed sizing** passed twice with independent forecasts (round-7 B3 and 7B P7). It improves risk-adjusted
   return on any positive book. Keep it inside every spec (done).
3. **Expiry-day sellers' side:** 7C's long straddles lost −8.2L on expiry days. Nobody has priced the mirror trade
   with defined risk on 0DTE (Family C).
4. **The option-flow predictor** is worthless as a taker signal but may be worth the half-spread as a timing tool for
   passive orders (Family E).
5. **5-year direction skill is real** (S003 t 4.9 DEV, 3.7 in 2021-23). The problem is monetisation, not discovery.
   Stop building side models.

What is **not** edge: the proxy book's +4.2L OOS (PF 1.05 at 1.5×, DSR ≈ 0); P5b (38 trades, lost in DEV, side placebo
69%); the day-skip model (7B already explained why not).

---

## 4. Overnight test plan (run locally before Mon 09:15 IST, in priority order)

All tests are offline on the lab box, with no broker calls and no engine or config change. Write
`output/lab_round8/PREREGISTRATION.md` with this section's specs and hash it **before** T1.

| # | Test | Data | Method | Output | Decision rule | Compute |
|---|---|---|---|---|---|---|
| T0 | Integrity and freeze | tapes, chain, `scratch/r7` | Reproduce RAW 66 / −128,730.49, P2C 38 / +94,962, proxy 198 / +4.17L (golden hashes, per the 09-25 truncation lesson). Hash the preregistration. | `T0_baselines.csv`, `.sha256` | Any mismatch ⇒ stop and fix the data first | light |
| T1 | **μ(h) curve** (the crux) | 5-yr NIFTY 1m (+ BANKNIFTY, SENSEX), 7B `r7b_feat` votes | For S003, ORB30, ZAB, VWAP_DEV_MOM, CONS4 (≥ 3/4, 4/4) and the wide-book entry times: mean signed move in EM30 units at h ∈ {15, 30, 60, 90, 120, 180, to 15:15}; day- and week-clustered t; by P0/P1/P2/P3; by strength decile; by DTE bucket. | `T1_mu_curve.csv`, one plot | Premise for A: μ(120) ≥ 1.6 × μ(30) and μ(15:15) ≥ 0.10 EM30, t ≥ 2 on P0 and P1, same sign on P2/P3. Frequency cut is alive if top-decile μ30 ≥ 0.054 EM30. **If the premise fails, close A and D (and F if T9 also fails) and record "directional option buying on these signals is closed" as the round-8 result.** B still runs (T4). | light (price-free) |
| T2 | Random-entry loss decomposition | chain P1+P2 | 10k random ITM100 and ITM200 entries × {H30, H60, H120, 15:15, W}: split net into fees, slippage, δ × index move, and residual; split the residual into decay and vega using chain ATM IV at entry and exit. Repeat on CONS4 entry times (vega after momentum). | `T2_decomp.csv` | Confirms or refutes §1.3 (1.35 pt = fees + slip + decay + stop residual); gives measured b(h) by strike/DTE for the break-even table; vega loss > 0.3 pt ⇒ promote spreads/deeper ITM in A | medium |
| T3 | LTP staleness audit | chain P1+P2 | Per strike offset (ATM, ITM100, ITM200) and last-minute volume: lead/lag regression of option returns on index returns (lags 0/1/2); entry-price bias conditional on a trend signal (sign-aligned LTP minus a B76 synthetic from ATM IV and synchronous spot). | `T3_staleness.csv` | Bias ≥ 0.2 pt in the trade's favour ⇒ re-price every momentum backtest on the synthetic mid; report old vs new | medium |
| T4 | Family B (TIMEX H90) | round-7 wide/proxy paths | §2.3 spec, identical lots for XS/X0 comparators, FC1 costs | `T4_timex.csv` | §2.0 bar + Δ vs XS/X0 | light (paths exist) |
| T5 | Family A | chain P1+P2, P0/P3 price-free | §2.2 spec; run only if T1 passes | `T5_trendhold.csv` | §2.0 bar | medium |
| T6 | Expiry-day slice, then Family C | 7C `f2_pnl_all.parquet`, `F2_trades.parquet`, chain | First: slice existing raw straddle/fly P&L by DTE = 0 and by segment (pre-2024-11-20 / to 2025-07-03 / after). Then run the §2.4 spec. | `T6_expiry_slice.csv`, `T6_fly0dte.csv` | Slice raw < 2.6 pts/fly on post-2025-07 ⇒ close C without the full run | light, then medium |
| T7 | Cost reconciliation | lab `fees()`, `fill()`, 7C V3 legs | Recompute the 5.4 pt/lot fly cost leg by leg vs 2.6-2.9 (arith); state which STT era each round used; build FC1; re-price the headline proxy book under FC1 | `T7_costs.md` (in the lab output folder, not the repo) | Any cost ≥ 20% off ⇒ restate the affected verdicts in an errata | light |
| T8 | Family D | chain | §2.6 spec; only if T1 and T6 are non-negative | `T8_credit01.csv` | §2.0 bar | medium |
| T9 | Family F premise, then money | 5-yr index; chain | Next-day continuation after trend days (price-free), then the §2.7 spec if t ≥ 2 on P0 and P1 | `T9_swing.csv` | §2.7 gate | light |
| T10 | Monday measurement protocol (no backtest) | depth recorder from 28 Sep | Log half-spread and top-of-book size by strike offset (ATM, ITM100, ITM200, ITM300, ±200 wings) × DTE × {09:15-09:30, 09:30-14:30, 14:30-15:30}, plus the cost of sweeping 1,625 units. After 10 sessions: replace the interim HS table in FC1. After 20: run Family E on real quotes. | recorder files | Measured HS ≥ 0.4 on ITM200 at DTE 0-1 ⇒ recompute rows 4, 7, 12 and the A instrument choice (ITM100 may beat ITM200) | n/a |

What to tell the desk on Monday regardless of results: **no engine change**. Round 8's outputs are, at most, specs for
the shadow log (A/B/C as counterfactual rows next to live entries, VOLSIZE-7B as a counterfactual size column) with
written kill criteria, followed by a fresh preregistered test on forward data.

---

## 5. Handoff block

- **Accepted** (from rounds 7/7B/7C): direction skill is real but small; side is not the binding constraint; the
  exact-strike chain is the only valid money pricing; the rolling series is retired for P&L; VOLSIZE-7B is the one
  overlay that passed twice; HARI is the best move-size forecast (with 7B's scoring discrepancy still open); the
  logit side bias is a known defect.
- **Rejected:** "a better exit will fix it" (optional stopping, §1.3); futures for intraday signals (15 pts per round
  trip); debit/credit spreads at 30-minute horizons; non-expiry quiet-day flies; further side routers; the 7C 5.4-pt
  fly cost as final (it needs T7); hit rate as the skill metric.
- **UNKNOWN / DATA_INSUFFICIENT:** the shape of μ(h) beyond 60 minutes (T1); real half-spreads by strike/DTE/size
  (T10); LTP staleness bias on ITM strikes (T3); the expiry-day seller P&L after the Jul-2025 SEBI order (T6);
  adverse selection on passive fills (depth data); BANKNIFTY/SENSEX chain availability; futures and exercise STT
  rates (VERIFY; not in `charges.yaml`).
- **Cross-team citations:** 04 `SIGNAL_STAGING.md` (5m indicators confirm/kill only; CONS4 uses 3m/1m trend votes and
  ORB/ZAB/VWAP rules, no 5m entry); 06 `EVENT_MEMORY.md` (event days are held and scored separately, not deleted); 09
  five-pass gate before any paper book; KEEP_ALL untouched (no `STRAT-*` is deleted or re-labelled here; families are
  research designs, not `MIX-*` catalog entries until one passes).

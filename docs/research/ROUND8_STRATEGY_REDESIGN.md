# Round 8 strategy redesign: an active option-buyer desk, and what the round trip really costs

Layer: **HYPOTHESIS / DESIGN** (paper-only). No engine, config, broker or credential change. Nothing here is a
`VALIDATION` result, a win-rate claim, or a customer ticket. Written 2026-09-27 as an adversarial senior-quant review
of lab rounds 7, 7-follow-up, 7B and 7C (uploaded reports; lab-box paths under `/workspace/dhan/output/lab_round7*/`).

**Founder steer (takes priority over the original brief):** we are **option buyers**. No recommendation to hold ATM
options for 30-120 minutes. Longer holds appear only as a comparison, and only in futures or deep ITM options. The
centre of this document is an **active option-buyer design** as practised by skilled intraday discretionary traders,
turned into preregistrable specs. Option-writing structures (flies, condors, credit spreads) are out of scope; we study
how writers behave only so a buyer can exploit it.

Number tags: **(arith)** = computed here from `config/charges.yaml` (via `groww_round_trip_charges()`) and Black-76
with stated assumptions; **(lab)** = quoted from the round-7/7B/7C reports; **VERIFY** = must be measured (mostly by the
depth recorder starting Mon 28 Sep) before it can move a verdict.

Repo paths: engine and picker are `packages/desk-ml/src/desk_ml/paper_scalp.py` and `.../picker.py` (not
`packages/backtest/...`); fees are `config/charges.yaml` = `packages/desk-ml/src/desk_ml/groww_costs.py`; the second
cost model is `packages/backtest/src/backtest_engine/costs.py`. Reusable building blocks for the detector below already
exist in `packages/analysts/src/analysts/shadow.py`: `range_over_atr()`, `efficiency_ratio()`, `realised_vol_pct()`,
`complete_bars_3m()` and `dealer_gex()`. That file also states that **no consolidation-box detector exists yet**.
Cross-team rules: `teams/04_quant/docs/SIGNAL_STAGING.md` (5m indicators confirm/kill only),
`teams/06_backtesting/docs/EVENT_MEMORY.md` (event days held and scored separately).

---

## 0. Now / Why / Next (plain English)

- **Now.** Holding options on our analysts' slow trend drift cannot work. The drift moves the index about **0.02-0.05
  points per minute**, but an ITM100/ATM option loses **0.06-0.47 index points per minute** of time value (per unit of
  delta) when the market is quiet. Every past round lost for this reason plus the ~₹2,200 round trip.
- **Why the active design might work.** A real breakout moves the index **1.4-2.7 points per minute** (0.5 EM30 in 5-10
  minutes). That is roughly 20-50× faster than the decay of the strikes the engine buys, and it clears the round trip
  within minutes. So a buyer should be flat
  in consolidation, where quiet markets cost the full decay, and long only in the minutes after a confirmed breakout.
  If there is no follow-through within 3 minutes, get out small. The loss on a failed trade is then ~₹5-11k at
  25 lots. A trade that captures 0.75 EM30 earns ~₹17-27k. So the book breaks even if **about 29-32%** of confirmed
  breakouts follow through (arith, §1.4).
- **Next.** Tonight, measure on 5 years of index bars (no option prices needed) how often breakouts from consolidation
  boxes follow through, and whether 2+ confirmations raise that rate above ~30% (§5, TA0-TA1). Then run the full
  BRK-BUY spec (§1.6) on the 3-year chain. No engine change on Monday.

---

## 1. Active option-buyer design (founder steer)

### 1.1 The thesis, and the one reason it could be real

A long option is long gamma and short theta. Per minute its P&L is δ·ΔS + ½Γ·ΔS² − θ. With no directional view, the
buyer wins only in minutes when the index moves more than the premium implies, and loses θ in every quiet minute.
Intraday NIFTY alternates between quiet consolidation, where realised vol is far below implied, and short bursts,
where realised vol is far above it. **A buyer who is flat in consolidation and long only in bursts pays theta only
when gamma is paying it back.**

Maths caution (§2.3): the optional-stopping theorem says an exit rule cannot create edge on a martingale. The time
stop and the trail are exits, so they add value only if something is **predictable** from the path. Two things are
plausibly predictable, and both are testable:

1. **Volatility clustering** is strong and well documented. 7C's HARI forecaster has an out-of-sample R² of 0.69 for
   next-hour realised vol. A burst that has started tends to continue; a breakout that stalls tends to go back to
   quiet. Keeping a long-gamma position while realised vol stays high, and cutting it when it drops, harvests that.
2. **Direction after a confirmed breakout.** Breakout-type analysts already show 30-minute direction skill (7B: ORB15
   and ORB30 DEV direction t ≈ 3.8-3.9; ZAB noise-area t 3.9). They lost money under a ~38-minute hold with a
   1 EM stop and 2 EM target (W) and no consolidation prerequisite. They were never tested with a fast time stop.

What would kill the thesis: implied vol reprices the burst immediately. Premium expansion means we buy at a higher IV.
Round 7 idea E (buy a straddle when the vol label flips to expanding) lost money even before costs, so this is a
real risk. §5 TA2 measures realised vs implied in the 5-15 minutes after confirmed breakouts.

### 1.2 Decay per holding minute, by DTE and time of day (arith)

Gross theta = what the option loses per minute if the index does not move (the consolidation case), in ₹ per minute at
25 lots (1,625 units). In brackets: how many quiet minutes equal one ₹2,200 round trip. Assumptions: NIFTY 25,000, IV
13%, Black-76, variance clock where each overnight carries 25% of a day's variance (VERIFY from the chain). With all
decay inside the session (w = 0, harshest case), multiply by ~1.3. DTE = sessions to expiry; 0 = expiry day (Tuesday).

| Strike | DTE | 09:30 | 11:00 | 13:00 | 14:30 | 15:00 |
|---|---|---|---|---|---|---|
| ATM | 0 | ₹157 (14 min) | ₹181 (12) | ₹243 (9) | **₹385 (6)** | **₹546 (4)** |
| ITM100 | 0 | ₹132 (17) | ₹144 (15) | ₹162 (14) | ₹140 (16) | ₹72 (31) |
| ITM200 | 0 | ₹80 (28) | ₹74 (30) | ₹48 (46) | ₹7 (330) | ~₹0 |
| ATM | 1 | ₹101 (22) | ₹107 (21) | ₹116 (19) | ₹125 (18) | ₹129 (17) |
| ITM100 | 1 | ₹94 (23) | ₹99 (22) | ₹106 (21) | ₹113 (20) | ₹115 (19) |
| ITM200 | 1 | ₹76 (29) | ₹78 (28) | ₹80 (28) | ₹81 (27) | ₹82 (27) |
| ATM | 2 | ₹80 (27) | ₹83 (26) | ₹88 (25) | ₹91 (24) | ₹92 (24) |
| ITM100 | 2 | ₹77 (29) | ₹79 (28) | ₹83 (27) | ₹86 (26) | ₹87 (25) |
| ITM200 | 2 | ₹67 (33) | ₹69 (32) | ₹71 (31) | ₹72 (30) | ₹73 (30) |
| ATM | 4 | ₹61 (36) | ₹62 (35) | ₹64 (34) | ₹65 (34) | ₹66 (33) |
| ITM100 | 4 | ₹59 (37) | ₹61 (36) | ₹62 (35) | ₹63 (35) | ₹64 (35) |
| ITM200 | 4 | ₹55 (40) | ₹56 (39) | ₹57 (39) | ₹58 (38) | ₹58 (38) |
| NIFTY future | any | ₹0 | ₹0 | ₹0 | ₹0 | ₹0, but the round trip is **₹24.5k** at 25 lots (15.1 idx pts, §2.2) |

Readings:
- **A quiet 60-minute ATM hold costs 2.3-6.6× the round trip in decay alone**: ₹4,980 at DTE 2 at 11:00 and ₹14,580 on
  expiry day at 13:00. This is the founder's point, quantified.
- **For a 2-5 minute trade, the round trip dominates**: ₹110-650 of decay at DTE ≥ 1 vs ₹2,200 of cost. Decay matters
  in fast trades only for ATM on expiry afternoons (₹770-2,730 over 2-5 minutes after 14:30).
- **Deep ITM barely decays** (₹7-80 per minute; ~₹0 on expiry afternoons). That is why long holds are only compared in
  deep ITM (and futures, which pay no decay but a ₹24.5k round trip at 25 lots).
- **Gross vs average decay.** Averaged over all minutes, realised moves repay most of theta through gamma. Measured net
  decay (round-7 straddle data) is only ~0.11-0.24 pt per ATM leg per 30 minutes, vs 1.5 pts gross at DTE 2. **In a
  quiet market a buyer pays 6-14× the average decay.** That is the quantitative case for rule (a), "don't trade
  consolidation". It also means the case against long ATM holds is really three costs: flat-period theta, the worst
  cost per delta (§2.2), and stop-outs. At 25 lots, the ₹30k cap is hit after ~26 index points on ITM100, which is
  less than one EM30 (§2.5).

### 1.3 Break-even move per minute held (arith)

m*(t) = (C + θ·t) / δ = the index move in our direction that pays the round trip plus t minutes of quiet-market decay.
Gamma is ignored (conservative; it matters only for 0DTE ATM, where a 27-point move adds ~2 pts). First number:
C = ₹2,200 (1.35 option pts, the founder's figure). Second: C = 0.95 pt (my fee + slippage arithmetic; the ₹2,200 also
includes ~38 minutes of decay and stop-fill losses, §2.3).

| Case (w = 0.25) | δ | Marginal decay speed θ/δ (idx pts/min) | t = 2 | t = 3 | t = 5 | t = 10 | t = 15 | t = 30 |
|---|---|---|---|---|---|---|---|---|
| DTE 2 ITM100, 11:00 (engine rule) | 0.62 | 0.078 | 2.3 / 1.7 | 2.4 / 1.8 | 2.6 / 1.9 | 3.0 / 2.3 | 3.3 / 2.7 | 4.5 / 3.9 |
| DTE 2 ATM, 11:00 | 0.50 | 0.102 | 2.9 / 2.1 | 3.0 / 2.2 | 3.2 / 2.4 | 3.7 / 2.9 | 4.2 / 3.4 | 5.8 / 4.9 |
| DTE 1 ITM200, 11:00 (engine rule) | 0.79 | 0.061 | 1.8 / 1.3 | 1.9 / 1.4 | 2.0 / 1.5 | 2.3 / 1.8 | 2.6 / 2.1 | 3.5 / 3.0 |
| DTE 0 ITM200, 11:00 | 0.91 | 0.050 | 1.6 / 1.1 | 1.6 / 1.2 | 1.7 / 1.3 | 2.0 / 1.5 | 2.2 / 1.8 | 3.0 / 2.5 |
| DTE 0 ITM200, 14:30 | 1.00 | 0.004 | 1.4 / 1.0 | 1.4 / 1.0 | 1.4 / 1.0 | 1.4 / 1.0 | 1.4 / 1.0 | 1.5 / 1.1 |
| DTE 0 ATM, 11:00 | 0.50 | 0.222 | 3.1 / 2.3 | 3.4 / 2.6 | 3.8 / 3.0 | 4.9 / 4.1 | 6.0 / 5.2 | 9.4 / 8.6 |
| DTE 0 ATM, 14:30 | 0.50 | 0.473 | 3.7 / 2.8 | 4.1 / 3.3 | 5.1 / 4.3 | 7.4 / 6.6 | 9.8 / 9.0 | 16.9 / 16.1 |
| DTE 4 ITM100, 11:00 | 0.59 | 0.063 | 2.4 / 1.7 | 2.5 / 1.8 | 2.6 / 1.9 | 2.9 / 2.2 | 3.2 / 2.5 | 4.2 / 3.5 |
| NIFTY future (comparison) | 1.00 | 0 | 15.1 | 15.1 | 15.1 | 15.1 | 15.1 | 15.1 |
| Noise: 1σ index move over t | | | 8.9 | 10.8 | 14.0 | 19.8 | 24.3 | 34.3 |

Three speeds decide everything:

| Speed (index pts per minute) | Value |
|---|---|
| Our analysts' average trend drift (μ30 = 0.02-0.05 EM30) | **0.018-0.046** |
| Marginal decay per delta, ITM100/ATM, DTE 0-4 | **0.06-0.47** |
| Marginal decay per delta, deep ITM (DTE 0-1) | **0.004-0.06** |
| A real breakout: 0.5 EM30 (≈ 14 pts) in 5-10 min | **1.4-2.7** |

Slow drift is slower than the decay of every non-deep option, so drift-holding buyers lose by construction. Breakouts
are roughly 20-50× faster than the decay of the engine's strikes (0.05-0.08 per minute). The fixed cost of 1.4-3.1
index pts is only 0.1-0.2σ of a 5-minute move. **For the
active design, per-trade cost is not the binding constraint. The share of breakouts that follow through is.**

### 1.4 Break-even follow-through rate for the active design (arith)

There are three outcomes: time-stopped (no follow-through; exit at 3 minutes about 3 index pts adverse), failed-breakout
stop (back inside the box; about 0.45 EM30 ≈ 12 pts adverse in ~4 minutes), and winner (partial plus trail capturing an
average of 0.5, 0.75 or 1.0 EM30). Losers are assumed 70% time-stopped and 30% failed-breakout. f* is the share of
entries that must be winners. Money is at 25 lots, C = ₹2,200.

| Strike / time | Avg loser (₹) | f* at 0.5 EM30 captured | f* at 0.75 EM30 | f* at 1.0 EM30 |
|---|---|---|---|---|
| DTE 2 ITM100, 11:00 | ₹8.3k | 43% | **32%** | 26% |
| DTE 1 ITM200, 11:00 | ₹9.9k | 40% | **30%** | 24% |
| DTE 0 ITM200, 11:00 | ₹11.0k | 39% | **29%** | 23% |
| DTE 0 ATM, 14:30 (diagnostic only) | ₹8.2k | 58% | 45% | 36% |

At C = 0.95 pt, every f* drops by 1-5 points. For reference, round 7's runner geometries (0.5-1.0 EM stop, 2 EM
target) realised 28-34% wins against 22-32% break-even (lab), so the required band is not fantasy. **0DTE ATM is the
worst buyer instrument even for fast trades**: expiry-afternoon decay forces a 45% follow-through rate. It stays a
diagnostic only.

### 1.5 How writers and institutions position around consolidation and breakouts, and how a buyer exploits it

Layer: market-structure **HYPOTHESIS** unless marked. Our data: 60-second LTP, volume and OI for 13-15 strikes plus the
index. We have no futures volume history and no depth until Monday.

**Who is on the other side.** SEBI's F&O studies (Jan 2023 and Sep 2024, SOURCE_FACT, VERIFY exact figures) found that
about 9 in 10 individual F&O traders lost money, and that proprietary and FPI (largely algorithmic) accounts took most of
the gains. Individuals are mostly option buyers. So an intraday buyer is usually trading against professional writers
and market makers who price the variance premium and are, as a group, **short gamma**.

**In consolidation (writers' home ground).**
- Writers sell strangles or straddles around the range. **OI builds at the nearest OTM strikes above (a "call wall")
  and below (a "put wall")**. ATM IV drifts down, the ATM straddle decays at roughly the theta rate, and volume is
  thin.
- Buyer rule: **stand aside** (spec AB-1). This is exactly where §1.2's quiet-market decay is paid.
- One exception worth logging: if the ATM straddle decays **slower than theta** while the index is flat, someone is
  buying volatility ahead of a move. That is a pre-breakout feature (F7), not a trade.

**At the breakout (writers' pain).**
- When the index pushes through a wall, short-call (or short-put) writers are losing. They can buy back the options,
  which sends that strike's premium and IV up and its **OI down** (covering). Or they can delta-hedge by buying
  futures into strength (selling into weakness for puts). Both add fuel. That is the "gamma squeeze" mechanism a
  buyer wants to ride.
- Observable in our chain: OI at the broken-side wall strike falls; volume in that strike bursts; the option premium
  rises faster than δ × index move (IV expansion); 7C's synthetic-forward innovation leads the index.
- **Counter-signal: fresh writing into the breakout.** If OI at the next strike beyond the break rises as price
  approaches it, and ATM IV is flat or falling, writers are selling the breakout. Those breakouts should fail more
  often; this is a veto (spec AB-2).

**After a real breakout.** Put writers "roll up" in rallies: PE OI builds at higher strikes, so the floor moves up. Call
writers roll down in selloffs. A rising PE-OI floor under a CE trade (mirror for PE) is a continuation condition for
the trail.

**Gamma sign.** A short-gamma writer community amplifies moves (breakouts run); a long-gamma one dampens them
(pinning). The repo's `dealer_gex()` defaults to `DEALER_LONG_CALLS_SHORT_PUTS`, a US-market convention. For NIFTY
weeklies, "writers short both calls and puts" is at least as plausible. The sign is **UNKNOWN**, so log GEX under both
conventions. 7B called GEX "untestable (no greeks history)", but greeks can be recomputed from chain LTP and index
with Black-76, so it is testable on the 3-year chain as long as the OI cadence is usable (TA4).

**Expiry day.** OI concentrates at round strikes, and pinning around the max-OI strike is common folklore. SEBI's
3 Jul 2025 interim order alleged that a large trading firm moved the index on expiry days to profit on options
positions (SOURCE_FACT, VERIFY wording), and surveillance rose after it. Any expiry-day pattern must be split at that
date. Buyer implication: on DTE 0, a break away from the max-OI strike after 13:00 has the most gamma per rupee but the
worst decay (₹243-546 per minute ATM). Use deep ITM unless the 0DTE-ATM diagnostic passes on its own.

**Honest limits of the OI story.**
- OI does not say who wrote. "Price up and OI up = fresh longs" style rules are ambiguous.
- NSE's OI dissemination cadence may be slower than our 60-second snapshots (VERIFY, TA4).
- 7C found OI-change features have **about zero predictive power for the next 1-5 minutes** (information coefficient
  −0.001 to +0.007).
- So OI is used here only as **context**: is the range defended, and is a breakout being covered or faded? It is
  never a minute-level direction trigger. It earns a place only if TA7 shows it separates follow-through from failure.

### 1.6 Preregistrable spec: BRK-BUY (research ID; becomes a `MIX-*` only after it passes 09's five-pass)

#### 1.6.0 Common definitions (also used by §3)

- **Index and data.** NIFTY for money (the minute chain exists). BANKNIFTY/SENSEX: price-free replication only, unless
  their chains exist (then the same spec runs as a replication, not a new trial). Decisions on completed 1-minute index
  closes; option prices from the 60-second exact-strike chain (the tape from Sep 17).
- **EM30** = 7B walk-forward EM′ (reference 27.4 pts). Sensitivity only: 7C HARI EM30 × 1.123 (reference 30.0).
- **VOLSIZE-7B** = clip(round(25 × 27.4 / EM30), 5, 25).
- **CAPLOTS(δ, stop_pts)** = floor(28,000 / (65 · δ · stop_pts)). **Lots = min(VOLSIZE-7B, CAPLOTS)**; skip if < 2.
- **Fills.** Signal on the close of minute t; fill at the option price of the next snapshot (t+1) plus the half-spread.
  Exits fill at the snapshot after the exit condition. A missing strike means skip, and the miss rate is logged.
- **Cost model FC1.** `charges.yaml` **current** rates (STT 0.15%) for every period (not era rates). Plus half-spread
  HS plus an adverse half tick. Interim HS (HYPOTHESIS until ≥ 10 recorder sessions): 0.20 for |moneyness| ≤ 100 at
  DTE ≥ 1; 0.30 for ITM200+ and DTE 0. **Burst surcharge: HS × 1.5 on entries and stops in the breakout minute**
  (spreads widen exactly then). 1.5× stress = fees × 1.5 and HS × 1.5. Swapping in the measured HS table is a re-run,
  not a new trial.
- **Periods.** P0 = 2021-09..2023-08 (index only). P1 = 2023-08-28..2025-08-31 (chain). P2 = 2025-09-01..2026-07-02
  (chain; **seen by four rounds, so validation, not holdout**). P3 = 2026-07-03..2026-09-25 (index only, plus the Sep
  17-25 tape). FWD = shadow log from 28 Sep: the only clean holdout.
- **Money pass bar.**
  1. Net > 0 at 1.5× on P1 and on P2 separately.
  2. Pooled day-clustered one-sided t at 1×: ≥ 2.39 = **PASS** (Bonferroni over the 6 money primaries in §6);
     1.645-2.39 with all other gates met = **PROMISING** (shadow only).
  3. Placebos ≥ 95th percentile.
  4. A +1-snapshot delayed entry keeps ≥ 50% of net.
  5. Worst day ≥ −₹90k; worst trade ≥ −₹40k.
  6. Report the deflated Sharpe ratio (DSR) with both effective and raw trial counts.

  PASS still needs 09's five-pass before any paper book.

#### 1.6.1 The spec

| Component | Rule (one preregistered value each; diagnostics listed separately) |
|---|---|
| **AB-1 Consolidation box** | At minute t a box is active if, over the trailing **W = 20** minutes: (i) range (max high − min low) ≤ **0.9 × EM30** (a Brownian 20-min path has an expected range ≈ 1.6 EM30, so this is about the quietest fifth of windows; report the realised percentile on P1); (ii) `efficiency_ratio()` over 20 closes ≤ **0.30**; (iii) t ≥ 09:35. Box top/bottom = window high/low; it extends while price stays inside. It **dissolves** if the range grows beyond 1.3 × EM30 without a qualifying breakout. **No entries while a box is active.** |
| **AB-1 logger** (log only) | Every box minute, log: F1 close position in box (0-1); F2 minutes in box; F3 range / EM30; F4 cumulative 7C synthetic-forward innovation (x3); F5 cumulative signed option volume (7C x1); F6 wall OI build = ΔOI(nearest OTM CE above) − ΔOI(nearest OTM PE below), normalised; F7 straddle decay ratio = actual ATM straddle change / theta-expected change; F8 VWAP side and distance / EM30; F9 trend-analyst votes (S003, ORB30, ZAB, VWAP_DEV_MOM); F10 BANKNIFTY relative return over the box; F11 GEX proxy under both dealer conventions; F12 DTE, minute of day, HARI ρ. **Direction model:** logistic regression on F1-F12 predicting the first break's side, fit on P1 boxes, frozen, scored on P2 and P3. It becomes confirmation C5 only if P1 cross-validated AUC ≥ 0.55 **and** P2 AUC ≥ 0.53; otherwise it is dropped (rule fixed now). |
| **AB-2 Breakout trigger** | 1-minute close beyond the box top (bottom) by **b = max(0.15 × EM30, 4 pts)** → buy CE (PE). |
| **AB-2 Confirmations** (need **≥ 2 of 5**) | **C1 volume burst:** near-ATM (±200) option volume in the breakout minute ≥ **3×** the box's median per-minute volume. **C2 premium expansion:** the option we would buy rose ≥ **1.15 × δ × index move** in the breakout minute (IV rising), or the ATM straddle rose ≥ 1%. **C3 trend agreement:** ≥ 2 of S003, ORB30, ZAB, VWAP_DEV_MOM vote the breakout side. **C4 writer covering:** OI at the nearest strike on the broken side fell ≥ **2%** over the last 3 snapshots (counts as "unavailable", not "false", if OI is stale per TA4). **C5:** the pre-breakout model agrees (only if it qualified). |
| **AB-2 Vetoes** | **Fade flag:** OI at the next strike beyond the break rose ≥ 3% in the breakout minute **and** ATM IV fell → skip. **Chasing guard** (7C tape lesson): skip if the index is already ≥ 0.5 × EM30 beyond the box edge at the signal minute; the entry must come within the first 2 minutes of the break. |
| **Instrument / strike** | Nearest weekly expiry. Engine DTE rule: **ITM100 if DTE ≥ 2, else ITM200** (it beat ATM and ITM100 in every round-7 segment). No ATM in the primary. |
| **AB-3 Fast time stop** | At entry + **3 minutes** (three 60-second snapshots): if no 1-minute close since entry has reached **+0.25 × EM30** (≈ 7 pts) beyond the entry index level, exit at the next snapshot. **Failed-breakout stop** (any time): a 1-minute close back inside the box by ≥ 0.25 × EM30 → exit. The stop distance is ≈ b + 0.25 EM30 + slippage ≈ **0.45 EM30** (≈ 12 pts), which is used for sizing. Hard: −₹30k mark. |
| **AB-4 Partial and trail** | At **+0.5 × EM30** (≈ 14 pts) favourable: sell **50%** of lots (floor) and move the stop on the rest to the entry index level. Trail the remainder: stop = max(entry, best 1-minute close since entry − **0.5 × EM30**) (mirror for PE). Also exit the remainder if a new AB-1 box forms (the trend has paused). **Max hold: 30 minutes for ITM100; 60 minutes only when δ ≥ 0.85 (deep ITM)**. Flat by 15:15. |
| **AB-4 Re-entry** | After any exit, a new trade needs a **fresh AB-1 box (≥ 10 minutes)** and a new AB-2 breakout. Exception: after a partial-plus-trail exit, one continuation entry per move is allowed on a pullback that re-breaks the post-entry extreme with ≥ 2 confirmations. After a time-stop or failed-breakout exit, **no same-direction re-entry off the same level** until a fresh box forms. |
| **AB-5 Frequency** | Set by the market: no fixed daily count. Rails only: ≤ 6 entries per day per index; 3 consecutive losing exits → 30-minute lockout; day stop −₹90k; 1 position per index; ≤ 3 across indices. Report the trades-per-day distribution (0 on trend-from-open or chaotic days is expected). |
| **Sizing** | lots = min(VOLSIZE-7B, CAPLOTS(δ, 0.45 × EM30 + 3)). At median EM30 and δ 0.62, CAPLOTS ≈ 45, so VOLSIZE governs (~21 lots average; 5-25). |
| **Skip rules** | Event calendar per `EVENT_MEMORY.md` (held and scored separately, never deleted); no box can form before 09:35; no new entries after 15:00. |
| **Break-even** | §1.4: follow-through share f ≥ ~29-32% at 0.75 EM30 average capture (FC1 at 1×); recompute f* from the realised average loser and winner, which must be self-consistent. |
| **Placebos** (2,000 draws) | **PL-SIDE:** same breakout minutes, random side. This tests whether the break direction matters. **PL-TIME:** same number of entries per day at random non-box minutes, same exits. This tests whether box-then-break timing matters. **PL-CONF:** same breakouts, but the ≥ 2-of-5 rule is applied to randomly permuted confirmation labels. This tests whether the confirmations add value. All three must be ≥ 95th percentile. |
| **Component claims** (each must hold on P1 and P2) | Time stop: BRK-BUY beats the same entries without AB-3. Box prerequisite: out-of-box breakouts beat the same breakout rule without AB-1. Confirmations: ≥ 2-of-5 beats 0-of-5. |
| **Diagnostics** (counted, not selectable) | Time stop at 2 and 5 minutes; W = 15 and 30; ATM strike on DTE 0 after 13:00 with a 10-minute max hold; ITM200 at all DTEs. |
| **Trials** | 1 primary + 6 diagnostics + 3 component ablations + 1 direction model = **11**. |

### 1.7 What prior rounds already say about this design

For:
- Moves happen, and traders fail to keep them. 54-59% of entries reach +1 EM; median favourable excursion is 1.16-1.31
  EM vs 0.89-0.93 EM adverse; the signal exit kept only 3-8% of the best available gain (round 7 §3.3).
- The only payoff shape with a consistent cushion over break-even is asymmetric (0.5-1.0 EM stop, 2 EM target; round 7
  §3.2). BRK-BUY is that shape, with a time dimension added.
- Breakout-type analysts have real direction skill (7B ORB30 / ZAB, DEV t ≈ 3.8-3.9).

Against:
- **Chasing.** On the tape, entries made after option flow had already moved our way lost ₹116k of ₹129k (7C). On
  history the "skip chasers" rule was inconsistent. C2 (premium expansion) is a form of chasing, hence the chasing
  guard and PL-CONF.
- **The flow edge decays within one bar** (7C: AUC 0.50 with one-bar-stale features). A 60-second loop is late by
  construction; TA3 measures this "confirmation tax".
- **Round 7 idea E** (long straddle on the vol-label flip) lost before costs: vol expansion gets priced fast.
- **ZAB noise-area breakout** made +22L in DEV, −3.2L OOS, and failed the random-time placebo even in DEV. That is a
  "long options on trend days" effect. BRK-BUY differs by requiring the box, the time stop and the confirmations, but
  the same failure mode is possible.
- The engine proxy already includes a "no-consolidation" component (round 6/7 proxy book). Its marginal value was
  never isolated; the component claim above does that.

### 1.8 Red team of the active design

- **Granularity.** Snapshots are 60 seconds apart, so a 3-minute time stop is three observations and a 2-minute stop
  is two. Nothing below 2 minutes is testable until the depth recorder has data.
- **Spreads and stops in bursts.** Spreads widen and failed breakouts snap back fast. The flat 0.20 slippage is least
  credible exactly here, hence the burst surcharge. Monday's recorder must measure half-spreads in breakout minutes
  specifically.
- **Knob count.** W, the range threshold, the efficiency-ratio threshold, b, three confirmation thresholds, the time
  stop, the partial level and the trail give roughly 10 knobs. Each has one preregistered value above, and none may
  be tuned. Only the listed diagnostics run, and they are counted.
- **Crowding.** Box breakouts are the most popular retail pattern. Writers know it and fade it. The fade flag is our
  only defence, and it rests on OI data of uncertain cadence.
- **The index box may not line up with the OI walls.** Log the distance from the box edge to the nearest wall strike
  (TA7). If breakouts through a wall behave differently, that is a new trial, not a retune.
- **Optional stopping still applies.** If TA2 shows realised/implied after confirmed breakouts is not above 1, the time
  stop and trail only reshape the distribution and the design is dead. Do not rescue it by tuning.

---

## 2. The cost problem from first principles

### 2.1 Assumptions

| Item | Value | Source |
|---|---|---|
| NIFTY spot | 25,000 | `option_chain_poller.py` default; VERIFY live |
| Lot / paper size | 65 / 25 lots = 1,625 units | `test_event_parity.py` fixture; `paper_scalp.py` `PAPER_TARGET_LOTS` |
| Option fees | ₹20/order; STT 0.15% sell premium; exchange 0.03503% both sides; SEBI 0.0001%; stamp 0.003% buy; GST 18% | `config/charges.yaml` |
| Option slippage (lab) | 0.20 pt/side + adverse half tick (0.025) | round-6/7 `fill()` |
| Futures fees | STT 0.05% sell (Budget 2026); exchange 0.00173%; stamp 0.002% buy | **not in `charges.yaml`; VERIFY** |
| EM30 / σ30 | 27.4 / 34.3 index pts | lab / arith |

### 2.2 Cost per round trip, and per index point of exposure (arith, 25 lots)

| Instrument | Premium | δ | Fees | Slip | Total (opt pts) | **Per idx pt of δ** | at 0.10 half-spread | at 0.50 |
|---|---|---|---|---|---|---|---|---|
| NIFTY future | — | 1.00 | 14.1 (STT 12.5) | 1.0 (VERIFY) | 15.1 (**₹24.5k** at 25 lots) | **15.1** | 14.3 | 15.1 |
| ATM CE, DTE 2 | 96 | 0.50 | 0.26 | 0.45 | 0.71 | **1.41** | 1.01 | 2.60 |
| ITM100 CE, DTE 2 | 154 | 0.66 | 0.39 | 0.45 | 0.84 | **1.27** | 0.97 | 2.17 |
| ITM200 CE, DTE 1 | 210 | 0.88 | 0.52 | 0.45 | 0.97 | **1.10** | 0.88 | 1.79 |
| ITM200 CE, DTE 0, 10:00 | 200 | 0.99 | 0.50 | 0.45 | 0.95 | **0.96** | 0.76 | 1.56 |
| Debit spread ATM/+200, DTE 2 | 68 | 0.30 | 2 legs | 2 legs | 1.25 | **4.21** | ~2.8 | ~8.2 |

What this says:
- **Futures cost 10-15× more per index point than options.** Futures STT is on notional; option STT is on premium.
- **Deep ITM near expiry is the cheapest delta a buyer can own.**
- **Slippage is the swing factor for options.** Fees are 0.26-0.52 pt, lab slippage 0.45, and the realistic range is
  0.25-1.05 depending on strike, DTE, time of day and 1,625-unit size.
- **The two repo cost models disagree 7-10×**: the lab's 0.20 pt/side vs `costs.py`'s 1% of premium per side.
- **Debit spreads** double the per-leg friction and cut delta, so they lose intraday.

### 2.3 Exits choose holding time; they do not create edge

For any exit rule τ on a drift-plus-martingale path: E[gross] ≈ δ · μ̇ · E[τ] − (average decay) · E[τ]. An exit changes
only E[τ] (and stop-fill quality). That is why round 7 found realised win rate tracking break-even within 0-6 points
across 58 geometries. The W exit (1 EM stop / 2 EM target) is a ~38-minute hold: E[τ] = a·b/σ² ≈ 0.8 × 1.6 × 30 min.
"54-59% reach +1 EM, and half of those still lose" is what a driftless martingale does.

The ₹2,200 random-entry loss (1.35 pts) decomposes, as a hypothesis to confirm (T2), into:
- fees 0.39-0.52
- slippage 0.45
- ~38 minutes of net decay 0.14-0.30
- stop-fill and gap-through residual 0.1-0.35

The skilled analysts claw back ~₹1,000 (≈ 0.03 EM30). **§1's design is the one way around optional stopping that does
not need slow drift.** It relies on predictable volatility clustering and post-breakout direction, which must be shown
(TA2, TA1).

### 2.4 Break-even for each buyer idea (time exits)

k(h) = (c + b·h/30)/δ is the break-even mean move over a hold of h minutes, using **average** (net-of-gamma) decay b.
p*(h) = Φ(k/σ_h) is the break-even direction hit rate. Measured skill: μ30 = 0.02-0.05 EM30 (0.55-1.37 pts).
**Money is linear in μ, not in hit rate** (52% ⇒ 1.72 pts; 0.05 EM ⇒ 51.6%).

| Idea (buyer only) | c / δ / b | Required μ (pts) | EM30 | p* | Clears? |
|---|---|---|---|---|---|
| Intraday future, 30 min | 15.1 / 1 / 0 | 15.1 | 0.55 | 67.0% | **No** |
| Future held to 15:15 (comparison) | 15.1 / 1 / 0 | 15.1 | 0.55 | 56.2% | **No** |
| ITM100, 30-min hold (engine today) | 0.84 / 0.66 / 0.14 | 1.48 | 0.054 | 51.7% | No / marginal |
| Deep ITM, 30 min | 0.95 / 0.88 / 0.08 | 1.17 | 0.043 | 51.4% | DEV-like only |
| Debit spread, 30 min | 1.25 / 0.30 / 0.03 | 4.3 | 0.16 | 54.9% | **No** |
| **Deep ITM held 120 min** (comparison) | 0.95 / 0.88 / 0.08 | 1.44 | 0.053 | 50.8% | Only if drift accrues |
| **Deep ITM held to 15:15** (comparison) | same | 1.81 | 0.066 | 50.7% | Only if drift accrues |
| Maker entry and exit, ITM100, 30 min (zero adverse selection) | 0.44 / 0.66 / 0.14 | 0.88 | 0.032 | 51.0% | Only with measured adverse selection |
| Deep ITM on DTE 0, 30 min | 0.95 / 0.99 / ~0 | 0.96-1.56 | 0.035-0.057 | 51.1-51.8% | Only if 0DTE deep-ITM spreads are tight (**VERIFY**) |

Long-hold net per trade, deep ITM (option pts per unit; comparison only):

| μ30 and accrual | 30 min | 60 min | 120 min | 240 min |
|---|---|---|---|---|
| 0.02 EM30, linear | −0.55 | −0.15 | +0.66 | +2.27 |
| 0.02 EM30, flat | −0.55 | −0.63 | −0.79 | −1.11 |
| 0.05 EM30, linear | +0.18 | +1.30 | +3.55 | +8.05 |
| 0.05 EM30, flat | +0.18 | +0.10 | −0.06 | −0.38 |

### 2.5 The ₹30k cap is a hidden stop

At 25 lots the cap is hit after **26 index pts** on ITM100 (δ 0.7) and **21 pts** on ITM200 (δ 0.88), i.e. **less than
one EM30**. Long holds therefore need CAPLOTS of about 4-6 lots. BRK-BUY's structural stop (≈ 12 pts) sits well inside
the cap, which is why it can run full VOLSIZE size.

---

## 3. Comparison benchmarks (long holds only in deep ITM or futures) and overlays

These exist to answer "is the active design better than simply holding a cheap delta?" They follow §1.6.0.

| ID | Spec | Sizing | Pass bar / placebos | Trials |
|---|---|---|---|---|
| **CMP-A Trend-hold, deep ITM** | Premise gate (T1): μ(to 15:15) ≥ 0.10 EM30 and μ(120) ≥ 1.6 × μ(30), t ≥ 2 on P0 and P1. Entry: first of {10:15, 11:30, 13:00} where ≥ 3 of the 4 trend analysts agree and none dissents, and s = \|close − TWAP\| / EM30 ≥ P1 q90. ITM200 (ITM300 if DTE ≥ 3). Exit 15:15; catastrophe stop 1.5 × EM30 × √(minutes left / 30). | min(VOLSIZE, CAPLOTS(0.9, stop)) ≈ 4-6 lots | §1.6.0; PL-SIDE, PL-TIME | 1 |
| **CMP-B Engine entries, time exit, deep ITM** | Round-7 wide book (no logit gate). Strike forced to ITM200. Exit at entry + 90 min or 15:15. The same lots are applied to the signal-exit (XS) and engine-geometry (X0) comparators. | min(VOLSIZE, CAPLOTS(δ, 1.5 × EM30 × √3)) ≈ 6-9 | Also Δ vs XS and X0 > 0 at 1.5× on P1 and P2 | 1 + 3 diagnostics (60 min, 120 min, EOD) |
| **CMP-F One-night deep ITM** | After a trend day (\|C − O\| / (H − L) ≥ 0.6 and \|C − O\| ≥ 0.6 × ATR14), buy ITM300 on the next expiry ≥ 2 sessions away at 15:20; exit next day 15:15. Price-free premise first (T9). | CAPLOTS ≈ 1-2 | §1.6.0 | 1 |
| **CMP-FUT Same signal as CMP-A in futures** | Same entry and exit as CMP-A. | CAPLOTS(1.0, stop) | Reported next to CMP-A. It is expected to fail on the 15.1-pt cost; it exists to put a number on the option-vs-future choice. | 1 |
| **E Maker-entry overlay** (on BRK-BUY and CMP-A) | Rest a buy at the best bid for ≤ 2 minutes (BRK-BUY) or ≤ 3 (CMP-A). No chase: a miss counts as a missed trade at its taker P&L. Stops always cross. The history proxy (fill if a later LTP ≤ limit − 1 tick) is labelled PROXY and cannot pass. On real depth data (≥ 20 sessions): per-signal gain ≥ +0.2 pt, fill rate ≥ 60%. | overlay | Note: a breakout buyer is paying for urgency, so the passive fill rate on real breakouts may be low. That is exactly what E measures. | 1 (+1 proxy) |

**Out of scope under the buyer steer:** iron flies, condors and credit spreads (7C's expiry-day long-straddle losses of
−8.2L suggest the writers' side earns on expiry days; we use that to understand our opponent, not to trade it);
intraday futures; debit spreads intraday; long straddles on HARI > implied; taker trades on the option-flow signal;
more side routers.

---

## 4. Methodology red team (both directions)

1. **The "OOS" year is burned** (too lenient). Rounds 6, 7, 7-follow-up, 7B and 7C all examined Sep 2025-Jul 2026. W
   was picked after seeing the OOS geometry map. From round 8 on, P2 is validation; the clean holdouts are P0 for new
   rules, P3 price-free, and FWD.
2. **The bar has little power for modest real edges** (too strict). Minimum detectable edge: 200 trades → annual
   Sharpe 1.8-2.6; 700 trades over 2.85 years → 0.97-1.42; 5 years price-free → 0.74-1.07 (z 1.645-2.39). PF ≈ 1 +
   2.5 × IR, so "PF > 1.2 at 1.5×" demands IR ≈ 0.08 per trade (Sharpe ~1.8 at ~500 trades a year). A true Sharpe-1.2
   strategy passes the round-7/7B conjunction only about **5-15%** of the time. The gates pass with roughly: DEV 0.95,
   OOS 0.87, both halves 0.63, placebo 0.45, PF 0.25; they are correlated. The fix is fewer pre-committed trials with
   one primary endpoint, not a lower bar: with N = 2,652 the expected best null z is 3.97.
3. **Reduced-form money backtests waste data.** Estimate the noisy term (follow-through / direction) price-free on 5
   years. Measure the low-variance terms (cost, decay) precisely from the chain and depth. Confirm with money runs.
4. **Cost-model bias, both ways.**
   - Two cost worlds in the repo (7-10× apart).
   - Flat slippage is too generous for ITM200 at DTE 0-1, for the open and close, for burst minutes and for 1,625
     units, and too harsh for ATM.
   - STT eras: 0.0625% → 0.10% (Oct 2024) → 0.15% (Apr 2026). That is +0.175 pt = ₹284 per trade at a 200-pt premium
     vs DEV-era rates.
   - 7C's fly cost (5.4 pts) vs 2.6-2.9 by arithmetic (T7).
   - Exercise STT and BSE charges are missing.
5. **Exact-strike proxy issues.**
   - **LTP staleness flatters momentum and breakout entries.** On thin ITM strikes the last trade can predate the
     move. For breakouts this matters twice: at entry (a stale, cheap LTP) and at C2 (premium expansion
     under-measured). T3 measures it.
   - Strikes drift off the 13-15-strike window after big moves.
   - A 60-second LTP is not a quote.
   - The chain ends 2026-07-02.
6. **The W exit is not neutral.** It tests the horizon where drift is weakest relative to cost. At 25 lots on DTE < 2
   the cap, not W, is the real stop.
7. **Trial count.** Raw N (2,652) over-counts correlated trials. An effective N of 100-300 lowers the best null z only
   to 3.0-3.4. DSR ≈ 0 is robust; adaptive reuse of one year is the bigger issue.
8. **Placebos and shift.** The +1-bar test is lenient on chain prices. Random-side placebos keep timing, so long gamma
   in high-vol windows can pass PL-TIME without any direction skill. That is why BRK-BUY needs PL-SIDE **and** PL-TIME
   **and** PL-CONF.
9. **Market-structure breaks inside the sample:**
   - SEBI F&O measures (20 Nov 2024)
   - the SEBI interim order on expiry-day conduct (3 Jul 2025)
   - NIFTY expiry Thursday → Tuesday on 1 Sep 2025, **exactly the P1/P2 boundary**
   - the STT increase (1 Apr 2026)
   - lot size 75 → 65

   Split every expiry-, DTE- or OI-conditioned result by these dates.
10. **Edge we may be throwing away.**
    - The fast-exit asymmetric shape was only ever tested without a consolidation prerequisite or confirmations.
    - Vol-managed sizing passed twice.
    - Breakout analysts' direction skill was never tested with a time stop.
    - OI covering vs fresh writing at breakouts was never tested.

---

## 5. Overnight test plan (run locally before Mon 09:15 IST, in priority order)

Offline on the lab box only. No broker calls, no engine or config change. Write
`output/lab_round8/PREREGISTRATION.md` (§1.6, §3, this section) and hash it **before** TA0.

| # | Test | Data | Method | Decision rule | Compute |
|---|---|---|---|---|---|
| T0 | Integrity and freeze | tapes, chain, `scratch/r7` | Reproduce RAW 66 / −128,730.49, P2C 38 / +94,962 and proxy 198 / +4.17L against the golden hashes; hash the preregistration. | Any mismatch ⇒ stop. | light |
| **TA0** | **Box and breakout base rates** | 5-yr NIFTY 1m (+ BANKNIFTY, SENSEX) | Run AB-1 and the AB-2 trigger price-free. Report: boxes per day; box length; breakouts per day; follow-through = reaches +0.5 EM30 before failing back 0.25 EM30 inside the box; failure within 3 and 5 minutes; MFE/MAE in EM30 at 3/5/10/15/30 minutes; by P0-P3, DTE and time of day; the trades-per-day distribution. | Unconfirmed follow-through share is the baseline. If it is < 20% everywhere, confirmations must lift it ~10+ points or the design is closed. | light |
| **TA1** | **Do confirmations raise follow-through?** | index (C3) 5 yrs; chain P1-P2 (C1, C2, C4) | Follow-through rate by number of confirmations (0 / 1 / 2 / 3+) and by each confirmation alone; day-clustered CIs; PL-CONF permutation. | Need monotone improvement and ≥ 2-of-5 follow-through ≥ f* (~30%) on P1 **and** P2, same sign on P0 for C3. | light-medium |
| **TA2** | **Is long gamma paid after breakouts?** | chain P1-P2 | Realised vol over the next 5/15 minutes ÷ ATM Black-76 implied at entry, for confirmed breakouts vs random non-box minutes vs box minutes; also the ATM IV change over the same window (the vega paid for chasing). | Ratio > 1 after confirmed breakouts and < 1 in boxes ⇒ thesis alive. Ratio ≤ 1 after breakouts ⇒ close BRK-BUY without a money run. | medium |
| **TA3** | **Confirmation tax** | chain + index | Index and option move between the breakout-minute close and the next-snapshot fill; as a share of the median follow-through. | Tax > 30% of median follow-through ⇒ report BRK-BUY as latency-bound; retest on depth data. | light |
| **TA4** | **OI cadence audit** | chain, tape | Distinct OI updates per strike per hour, by strike offset and time of day. | If updates are slower than one per 3 minutes, C4 and the fade flag are "unavailable" (not tuned away). | light |
| **TA5** | **BRK-BUY money run** | chain P1-P2 (tape for P3) | Full §1.6 spec with FC1 costs; three placebos; component ablations; diagnostics. | §1.6.0 bar and the component claims. | medium |
| **TA6** | **Pre-breakout direction model** | chain P1 → P2 | Fit the F1-F12 logistic on P1 boxes, freeze, score P2 AUC and calibration. | Enters as C5 only if P1 CV AUC ≥ 0.55 and P2 ≥ 0.53. | light |
| **TA7** | **Writer-positioning study** | chain P1-P2 | In boxes: wall OI build vs later break side and follow-through. At breakouts: covering vs fresh writing vs follow-through; distance from the box edge to the wall strike; GEX-proxy sign under both conventions vs follow-through. Split at 2024-11-20, 2025-07-03 and 2025-09-01. | Informs C4 and the fade flag. Any new rule found here is a **new trial for round 9**, not a retune. | medium |
| T1 | Drift curve μ(h) (for CMP-A/B/F) | 5-yr index | Mean signed move in EM30 at 15-240 min and to 15:15 for the four trend analysts, the consensus rule and wide-book times; by period and strength decile. | CMP-A premise (§3). | light |
| T2 | Random-entry loss decomposition | chain | Split net into fees, slippage, δ × move and residual (decay vs vega from chain IV) for random ITM100/ITM200 entries at {3, 5, 15, 30 min, W}. | Confirms §2.3 and §1.2 (measured gross vs net decay by DTE and time of day). | medium |
| T3 | LTP staleness | chain | Lead/lag of ITM option returns vs index; entry-price bias conditional on a breakout or trend signal vs a Black-76 synthetic mid. | Bias ≥ 0.2 pt ⇒ re-price every breakout/momentum backtest on the synthetic mid. | medium |
| T4 | CMP-B | round-7 paths | §3 spec. | §3 bar. | light |
| T5 | CMP-A and CMP-FUT | chain | Only if T1 passes. | §3 bar. | medium |
| T7 | Cost reconciliation | lab `fees()` / `fill()` | STT era used by each round; build FC1; re-price the headline proxy. | Any ≥ 20% error ⇒ errata. | light |
| T9 | CMP-F premise, then money | index, chain | Next-day continuation after trend days. | t ≥ 2 on P0 and P1. | light |
| T10 | Monday measurement protocol | depth recorder | Half-spread and top-of-book size by strike (ATM, ITM100, ITM200, ITM300) × DTE × {09:15-09:30, normal, **breakout minutes**, 14:30+}; the cost of sweeping 1,625 units. After 10 sessions: replace interim HS. After 20: run overlay E and second-level time stops. | Burst half-spread ≥ 0.5 on the DTE-rule strike ⇒ recompute §1.3-1.4 before any BRK-BUY verdict. | n/a |

Monday regardless of results: **no engine change.** At most, BRK-BUY and CMP-A/B go into the shadow log as
counterfactual rows next to live entries, with VOLSIZE-7B as a counterfactual size column and written kill criteria.
That is followed by a fresh preregistered test on forward data.

---

## 6. Trial budget

| Block | Trials |
|---|---|
| BRK-BUY: 1 primary + 6 diagnostics + 3 ablations + 1 direction model | 11 |
| CMP-A, CMP-B (+3 diagnostics), CMP-F, CMP-FUT | 7 |
| Overlay E (+ proxy) | 2 |
| Price-free base rates and premises (TA0, TA1, TA2, T1, T9; all reported) | ~70 |
| **Total new** | **≈ 90 → cumulative ≈ 2,742** |

The money primaries for Bonferroni are BRK-BUY, CMP-A, CMP-B, CMP-F, CMP-FUT and E (6), so a PASS needs z ≥ 2.39.

---

## 7. Handoff block

- **Accepted** (from rounds 7/7B/7C):
  - Direction skill is real but small; side is not the binding constraint.
  - Money results use exact-strike chain prices only; the rolling series is retired for P&L.
  - VOLSIZE-7B is the one overlay that passed twice.
  - HARI is the best move-size forecast (7B's scoring discrepancy is still open).
  - The logit side bias is a known defect.
  - Founder steer: buyer-only desk; no long ATM holds; long holds only in deep ITM or futures, as comparisons.
- **Rejected:**
  - Holding ITM100/ATM on slow drift: drift of 0.02-0.05 pts/min is below decay of 0.06-0.47 pts/min per delta.
  - "A better exit alone fixes it" (optional stopping).
  - Intraday futures (₹24.5k per round trip at 25 lots).
  - Debit spreads intraday.
  - Writer-side structures (out of scope).
  - More side routers.
  - Hit rate as the skill metric.
- **UNKNOWN / DATA_INSUFFICIENT:**
  - Follow-through base rates of box breakouts and the lift from confirmations (TA0/TA1).
  - Realised vs implied after breakouts (TA2).
  - The confirmation tax at 60-second granularity (TA3).
  - OI dissemination cadence (TA4); who is writing, since OI has no side.
  - Half-spreads in breakout minutes (T10).
  - LTP staleness on ITM strikes (T3).
  - The GEX sign convention for NIFTY weeklies.
  - BANKNIFTY/SENSEX chain availability.
  - Futures and exercise STT rates (VERIFY; not in `charges.yaml`).
  - The overnight variance weight w used in the decay tables (VERIFY from the chain).
- **Cross-team citations:**
  - 04 `SIGNAL_STAGING.md`: 5m indicators confirm or kill, never enter. C3 uses 3m/1m trend votes and ORB/ZAB/VWAP
    rules.
  - 06 `EVENT_MEMORY.md`: event days are held and scored separately.
  - 09 five-pass gate before any paper book.
  - KEEP_ALL untouched: no `STRAT-*` is deleted or relabelled. BRK-BUY and the CMP-* entries are research IDs, not
    `MIX-*` catalogue rows, until one passes.

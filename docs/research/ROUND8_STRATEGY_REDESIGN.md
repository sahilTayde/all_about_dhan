# Round 8 strategy redesign: an active option-buyer desk, and what the round trip really costs

Layer: **HYPOTHESIS / DESIGN** (paper-only). No engine, config, broker or credential change. Nothing here is a
`VALIDATION` result, a win-rate claim, or a customer ticket. Written 2026-09-27 as an adversarial senior-quant review
of lab rounds 7, 7-follow-up, 7B and 7C (uploaded reports; lab-box paths under `/workspace/dhan/output/lab_round7*/`).

**Founder steer (takes priority over the original brief):** we are **option buyers**. No recommendation to hold ATM
options for 30-120 minutes. Longer holds appear only as a comparison, and only in futures or deep ITM options. The
centre of this document is an **active option-buyer design** as practised by skilled intraday discretionary traders,
turned into preregistrable specs. Option-writing structures (flies, condors, credit spreads) are out of scope; we study
how writers behave only so a buyer can exploit it.

**Founder correction (applied to every break-even below):** ₹2,200 is **not** the round-trip cost. It was the average
loss per random entry under the 1 EM stop / 2 EM target exit, which includes decay and stop-outs (§2.3 decomposes it).
The true friction is:
- Dhan brokerage ₹20 per order;
- STT 0.15% of sell premium;
- exchange 0.0355299% both sides;
- SEBI 0.0001%;
- stamp 0.003% on the buy;
- GST 18% on brokerage, exchange and SEBI;
- NIFTY lot 65.

At a ₹150 premium that is ₹70 per round trip for 1 lot and **₹625 for 25 lots**. Slippage s per side is shown at
**0.05, 0.10 and 0.20** points. All-in at 25 lots: ₹1,080-1,660 at s = 0.20 for premiums of 100-250, and ₹790-950 at
s = 0.05-0.10 for a 150 premium.

Number tags: **(arith)** = computed here from the founder's friction above (it reproduces ₹70.3 and ₹625.1 exactly;
`config/charges.yaml` has exchange 0.03503%, which is ₹3 lower at 25 lots, VERIFY which is current) and Black-76
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
  delta) when the market is quiet. Every past round lost for this reason plus a ₹790-1,660 round trip at 25 lots.
  (₹2,200 was the average random-entry loss, including decay and stop-outs, not the friction.)
- **Why the active design might work.** A real breakout moves the index **1.4-2.7 points per minute** (0.5 EM30 in 5-10
  minutes). That is roughly 20-50× faster than the decay of the strikes the engine buys, and it clears the round trip
  within minutes. So a buyer should be flat
  in consolidation, where quiet markets cost the full decay, and long only in the minutes after a confirmed breakout.
  If there is no follow-through within 3 minutes, get out small. A time-stopped trade then loses ~₹4.2-6.1k at 25
  lots (₹7.1-10.3k averaged with the failed-breakout stops). A trade that captures 0.75 EM30 earns ~₹18-28k. So the
  book breaks even if **about 26-29%** of confirmed breakouts follow through, from s = 0.05 to s = 0.20 (arith, §1.4).
  Slippage moves that break-even by only 1-2 points, because losers are driven by index points, not friction.
- **Next.** Tonight, measure on 5 years of index bars (no option prices needed) how often breakouts from consolidation
  boxes follow through, and whether 2+ confirmations raise that rate above ~29% (§5, TA0-TA1). Then run the full
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
25 lots (1,625 units). In brackets: **how many quiet minutes equal one all-in round trip for that option at slippage
0.05 / 0.10 / 0.20** (the round trip uses that cell's own premium). Assumptions: NIFTY 25,000, IV 13%, Black-76,
variance clock where each overnight carries 25% of a day's variance (VERIFY from the chain). With all decay inside the
session (w = 0, harshest case), multiply decay by ~1.3. DTE = sessions to expiry; 0 = expiry day (Tuesday).

| Strike | DTE | 09:30 | 11:00 | 13:00 | 14:30 | 15:00 |
|---|---|---|---|---|---|---|
| ATM | 0 | ₹157 (3/4/6) | ₹181 (2/3/5) | ₹243 (2/2/4) | **₹385 (1/1/2)** | **₹546 (1/1/1)** |
| ITM100 | 0 | ₹132 (5/7/9) | ₹144 (5/6/8) | ₹162 (4/5/7) | ₹140 (4/5/8) | ₹72 (8/11/15) |
| ITM200 | 0 | ₹80 (13/15/19) | ₹74 (14/16/20) | ₹48 (20/24/30) | ₹7 (146/170/218) | ~₹0 |
| ATM | 1 | ₹101 (6/8/11) | ₹107 (6/7/10) | ₹116 (5/6/9) | ₹125 (4/6/8) | ₹129 (4/5/8) |
| ITM100 | 1 | ₹94 (9/11/14) | ₹99 (8/10/13) | ₹106 (7/9/12) | ₹113 (7/8/11) | ₹115 (7/8/11) |
| ITM200 | 1 | ₹76 (15/17/21) | ₹78 (14/16/20) | ₹80 (13/15/20) | ₹81 (13/15/19) | ₹82 (13/15/19) |
| ATM | 2 | ₹80 (9/11/15) | ₹83 (9/10/14) | ₹88 (8/10/13) | ₹91 (7/9/13) | ₹92 (7/9/12) |
| ITM100 | 2 | ₹77 (12/14/19) | ₹79 (12/14/18) | ₹83 (11/13/17) | ₹86 (10/12/16) | ₹87 (10/12/16) |
| ITM200 | 2 | ₹67 (18/20/25) | ₹69 (17/20/24) | ₹71 (16/19/23) | ₹72 (16/18/23) | ₹73 (16/18/22) |
| ATM | 4 | ₹61 (15/17/23) | ₹62 (14/17/22) | ₹64 (13/16/21) | ₹65 (13/15/20) | ₹66 (13/15/20) |
| ITM100 | 4 | ₹59 (19/21/27) | ₹61 (18/21/26) | ₹62 (17/20/25) | ₹63 (17/19/24) | ₹64 (17/19/24) |
| ITM200 | 4 | ₹55 (24/27/33) | ₹56 (24/27/33) | ₹57 (23/26/32) | ₹58 (23/25/31) | ₹58 (22/25/31) |
| NIFTY future | any | ₹0 | ₹0 | ₹0 | ₹0 | ₹0, but the round trip is **₹23.1-23.6k** at 25 lots (14.2-14.5 idx pts, §2.2) |

All-in round trip at 25 lots by premium (arith, founder friction):

| Premium | Charges | s = 0.05 | s = 0.10 | s = 0.20 |
|---|---|---|---|---|
| 30 | ₹163 | ₹325 (0.20 pt) | ₹488 (0.30) | ₹813 (0.50) |
| 60 | ₹278 | ₹441 (0.27) | ₹603 (0.37) | ₹928 (0.57) |
| 100 | ₹432 | ₹595 (0.37) | ₹757 (0.47) | ₹1,082 (0.67) |
| **150** | **₹625** | **₹788 (0.48)** | **₹950 (0.58)** | **₹1,275 (0.78)** |
| 200 | ₹818 | ₹980 (0.60) | ₹1,143 (0.70) | ₹1,468 (0.90) |
| 250 | ₹1,010 | ₹1,173 (0.72) | ₹1,335 (0.82) | ₹1,660 (1.02) |
| 300 | ₹1,203 | ₹1,365 (0.84) | ₹1,528 (0.94) | ₹1,853 (1.14) |

Readings:
- **A quiet 60-minute ATM hold costs 4-7× the round trip in decay alone at DTE 2** (₹4,998 at 11:00 vs a ₹715-1,200
  round trip on a 130 premium). **On expiry day at 13:00 it costs 17-38×** (₹14,563 vs ₹380-870 on a 45 premium). With
  the corrected friction the founder's point is stronger, not weaker: on ATM, decay rather than friction is the
  dominant cost of any hold longer than 5-15 minutes.
- **For a 2-5 minute trade, friction and decay are the same order**: ₹110-650 of decay at DTE ≥ 1 vs a ₹790-1,660
  round trip. On ATM expiry afternoons decay overtakes the whole round trip within 1-2 minutes (₹385-546 per minute).
- **Deep ITM barely decays** (₹7-80 per minute; ~₹0 on expiry afternoons). A quiet 15-30 minutes of deep ITM costs
  about one round trip. That is why long holds are only compared in deep ITM (and in futures, which pay no decay but a
  ₹23k round trip at 25 lots).
- **Gross vs average decay.** Averaged over all minutes, realised moves repay most of theta through gamma. Measured net
  decay (round-7 straddle data) is only ~0.11-0.24 pt per ATM leg per 30 minutes, vs 1.5 pts gross at DTE 2, i.e.
  κ = net/gross ≈ 0.07-0.16. Under Black-76, θ = ½σ²S²Γ, so κ = 1 − (σ_realised/σ_implied)², the same for every
  strike; §2.4 uses κ = 0.12. **In a quiet market a buyer pays 6-14× the average decay.** That is the quantitative case
  for rule (a), "don't trade consolidation". It also means the case against long ATM holds is really three costs:
  flat-period theta, the worst cost per delta at wide spreads (§2.2), and stop-outs. At 25 lots the ₹30k cap is hit
  after ~24-30 index points (δ 0.79-0.62), about one EM30 (§2.5).

### 1.3 Break-even move per minute held (arith)

m*(t) = (C + θ·t) / δ = the index move in our direction that pays the all-in round trip C (that option's own
premium, founder friction) plus t minutes of quiet-market decay. Gamma is ignored (conservative; it matters only for
0DTE ATM, where a 27-point move adds ~2 pts). **Each cell is s = 0.05 / 0.10 / 0.20.** "Fixed" = C/δ, the move
needed with zero hold time.

| Case (w = 0.25, 11:00 unless stated) | Premium | δ | Decay speed θ/δ (idx pts/min) | Fixed C/δ | t = 3 | t = 5 | t = 15 | t = 30 |
|---|---|---|---|---|---|---|---|---|
| DTE 2 ITM100 (engine rule) | 186 | 0.62 | 0.078 | 0.91 / 1.08 / 1.40 | 1.1 / 1.3 / 1.6 | 1.3 / 1.5 / 1.8 | 2.1 / 2.2 / 2.6 | 3.3 / 3.4 / 3.7 |
| DTE 2 ATM | 130 | 0.50 | 0.102 | 0.87 / 1.07 / 1.47 | 1.2 / 1.4 / 1.8 | 1.4 / 1.6 / 2.0 | 2.4 / 2.6 / 3.0 | 3.9 / 4.1 / 4.5 |
| DTE 1 ITM200 (engine rule) | 231 | 0.79 | 0.061 | 0.86 / 0.99 / 1.24 | 1.0 / 1.2 / 1.4 | 1.2 / 1.3 / 1.5 | 1.8 / 1.9 / 2.2 | 2.7 / 2.8 / 3.1 |
| DTE 0 ITM200 | 206 | 0.91 | 0.050 | 0.68 / 0.79 / 1.01 | 0.8 / 0.9 / 1.2 | 0.9 / 1.0 / 1.3 | 1.4 / 1.5 / 1.8 | 2.2 / 2.3 / 2.5 |
| DTE 0 ITM200, 14:30 | 200 | 1.00 | 0.004 | 0.60 / 0.70 / 0.91 | 0.6 / 0.7 / 0.9 | 0.6 / 0.7 / 0.9 | 0.7 / 0.8 / 1.0 | 0.7 / 0.8 / 1.0 |
| DTE 0 ATM | 60 | 0.50 | 0.222 | 0.54 / 0.74 / 1.14 | 1.2 / 1.4 / 1.8 | 1.7 / 1.9 / 2.2 | 3.9 / 4.1 / 4.5 | 7.2 / 7.4 / 7.8 |
| DTE 0 ATM, 14:30 | 28 | 0.50 | 0.473 | 0.39 / 0.59 / 0.99 | 1.8 / 2.0 / 2.4 | 2.8 / 3.0 / 3.4 | 7.5 / 7.7 / 8.1 | 14.6 / 14.8 / 15.2 |
| DTE 4 ITM100 | 228 | 0.59 | 0.063 | 1.13 / 1.30 / 1.63 | 1.3 / 1.5 / 1.8 | 1.4 / 1.6 / 1.9 | 2.1 / 2.2 / 2.6 | 3.0 / 3.2 / 3.5 |
| NIFTY future (comparison) | — | 1.00 | 0 | 14.2 / 14.3 / 14.5 | same | same | same | same |
| Noise: 1σ index move over t | | | | | 10.8 | 14.0 | 24.3 | 34.3 |

Reading the sensitivity: going from s = 0.20 to s = 0.05 cuts the fixed move by 0.3-0.6 index pts on every option
(0.30 option pt ÷ δ). That is worth about 6 minutes of decay on the DTE-rule strikes, and **about one minute on ATM
expiry afternoons**, where decay swamps friction. Tight spreads help slow trades; they do not rescue ATM holds.

Three speeds decide everything:

| Speed (index pts per minute) | Value |
|---|---|
| Our analysts' average trend drift (μ30 = 0.02-0.05 EM30) | **0.018-0.046** |
| Marginal decay per delta, ITM100/ATM, DTE 0-4 | **0.06-0.47** |
| Marginal decay per delta, deep ITM (DTE 0-1) | **0.004-0.06** |
| A real breakout: 0.5 EM30 (≈ 14 pts) in 5-10 min | **1.4-2.7** |

Slow drift is slower than the decay of every non-deep option, so drift-holding buyers lose by construction. Breakouts
are roughly 20-50× faster than the decay of the engine's strikes (0.05-0.08 per minute). The fixed move of 0.4-1.6
index pts is only 0.03-0.12σ of a 5-minute move. **For the active design, per-trade friction is not the binding
constraint. The share of breakouts that follow through is.**

### 1.4 Break-even follow-through rate for the active design (arith)

There are three outcomes:
- **Time-stopped** (no follow-through): exit at 3 minutes, about 3 index pts adverse.
- **Failed-breakout stop** (back inside the box): about 0.45 EM30 ≈ 12 pts adverse in ~4 minutes.
- **Winner** (partial plus trail): captures an average of 0.5, 0.75 or 1.0 EM30 over 8-15 minutes.

Losers are assumed 70% time-stopped and 30% failed-breakout. f* is the share of entries that must be winners. C is the
all-in round trip on that option's premium at 25 lots.

| Strike / time | Round trip C (s = 0.05 / 0.10 / 0.20) | Time-stopped loss at s = 0.20 | Avg loser at s = 0.20 | Winner at 0.75 EM30, s = 0.20 | **f* at 0.75 EM30 (s = 0.05 / 0.10 / 0.20)** | f* at 0.5 / 1.0 EM30 (s = 0.20) |
|---|---|---|---|---|---|---|
| DTE 2 ITM100, 11:00 | ₹926 / ₹1,089 / ₹1,414 | ₹4.7k | ₹7.5k | ₹18.4k | **27.2% / 27.8% / 29.0%** | 39.0% / 23.1% |
| DTE 1 ITM200, 11:00 | ₹1,099 / ₹1,262 / ₹1,587 | ₹5.7k | ₹9.3k | ₹23.8k | **26.6% / 27.1% / 28.0%** | 37.7% / 22.3% |
| DTE 0 ITM200, 11:00 | ₹1,005 / ₹1,167 / ₹1,492 | ₹6.1k | ₹10.3k | ₹28.0k | **25.6% / 26.1% / 26.9%** | 36.2% / 21.4% |
| DTE 0 ATM, 14:30 (diagnostic only) | ₹319 / ₹481 / ₹806 | ₹4.4k | ₹6.8k | ₹11.3k | **34.9% / 35.8% / 37.6%** | 48.3% / 30.2% |

Readings:
- **Slippage moves the break-even follow-through rate by only 1-2 points** (0.05 → 0.20). A failed trade's loss is
  mostly index points (δ × 3-12 pts ≈ ₹3-18k), not friction (₹0.3-1.6k). What matters is how often breakouts follow
  through and how far winners run, not the spread.
- For reference, round 7's runner geometries (0.5-1.0 EM stop, 2 EM target) realised 28-34% wins against 22-32%
  break-even (lab), so the required 26-29% band is not fantasy.
- **0DTE ATM is still the worst buyer instrument for fast trades**, even though its friction is the lowest (₹319-806):
  expiry-afternoon decay forces a 35-38% follow-through rate. It stays a diagnostic.

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
- **Fills.** Signal on the close of minute t; fill at the option price of the next snapshot (t+1) plus slippage s.
  Exits fill at the snapshot after the exit condition. A missing strike means skip, and the miss rate is logged.
- **Cost model FC1** (founder friction). Charges are applied at **current** rates to every period (not era rates):
  - Dhan ₹20 per order;
  - STT 0.15% of sell premium;
  - exchange 0.0355299% both sides;
  - SEBI 0.0001%;
  - stamp 0.003% buy;
  - GST 18% on brokerage, exchange and SEBI.

  Slippage s per side, including tick rounding:
  - **verdict at s = 0.20** (conservative);
  - sensitivities at **s = 0.10 and 0.05** (the realistic ATM spread range), always reported;
  - **stress = fees × 1.5 and s = 0.30**. This also stands in for wider spreads in breakout minutes; a result that
    only survives at s ≤ 0.10 is PROMISING at best.

  Swapping in the measured spread table (≥ 10 recorder sessions) is a re-run, not a new trial.
- **Periods.** P0 = 2021-09..2023-08 (index only). P1 = 2023-08-28..2025-08-31 (chain). P2 = 2025-09-01..2026-07-02
  (chain; **seen by four rounds, so validation, not holdout**). P3 = 2026-07-03..2026-09-25 (index only, plus the Sep
  17-25 tape). FWD = shadow log from 28 Sep: the only clean holdout.
- **Money pass bar.**
  1. Net > 0 at s = 0.20 **and** under stress (fees × 1.5, s = 0.30) on P1 and on P2 separately.
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
| **Break-even** | §1.4: follow-through share f ≥ ~27-29% at 0.75 EM30 average capture on the DTE-rule strikes (26-28% at s = 0.05); recompute f* from the realised average loser and winner, which must be self-consistent. |
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
  credible exactly here, hence the s = 0.30 stress being binding. Monday's recorder must measure half-spreads in breakout minutes
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
| Lot / paper size | 65 / 25 lots = 1,625 units | founder; `test_event_parity.py` fixture; `paper_scalp.py` `PAPER_TARGET_LOTS` |
| Option charges | Dhan ₹20/order; STT 0.15% sell premium; exchange 0.0355299% both; SEBI 0.0001%; stamp 0.003% buy; GST 18% on brokerage + exchange + SEBI | founder (reproduces ₹70 / 1 lot and ₹625 / 25 lots at a 150 premium); `charges.yaml` exchange is 0.03503% (VERIFY) |
| Option slippage s | **0.05 / 0.10 / 0.20 pt per side** (0.20 = lab assumption; 0.05-0.10 = realistic ATM spread) | founder |
| Premiums and deltas | Black-76, IV 13%, overnight carries 25% of a day's variance, 11:00 | arith |
| Futures fees | STT 0.05% sell (Budget 2026); exchange 0.00173%; stamp 0.002% buy | **not in `charges.yaml`; VERIFY** |
| EM30 / σ30 | 27.4 / 34.3 index pts | lab / arith |
| Average net decay b | κ × gross θ, κ = 0.12 (0.07-0.16 measured) | §1.2 |

### 2.2 Cost per round trip, and per index point of exposure (arith, 25 lots)

Each cell is **s = 0.05 / 0.10 / 0.20**.

| Instrument | Premium | δ | Charges (pts) | All-in round trip (opt pts) | All-in (₹, 25 lots) | **Per index pt of δ** |
|---|---|---|---|---|---|---|
| NIFTY future | — | 1.00 | 14.1 (STT 12.5) | 14.2 / 14.3 / 14.5 idx pts | ₹23.1k / 23.3k / 23.6k | **14.2 / 14.3 / 14.5** |
| ATM CE, DTE 2 | 130 | 0.50 | 0.34 | 0.44 / 0.54 / 0.74 | ₹715 / 878 / 1,203 | **0.87 / 1.07 / 1.47** |
| ITM100 CE, DTE 2 | 186 | 0.62 | 0.47 | 0.57 / 0.67 / 0.87 | ₹926 / 1,089 / 1,414 | **0.91 / 1.08 / 1.40** |
| ITM200 CE, DTE 1 | 231 | 0.79 | 0.58 | 0.68 / 0.78 / 0.98 | ₹1,099 / 1,262 / 1,587 | **0.86 / 0.99 / 1.24** |
| ITM200 CE, DTE 0 | 206 | 0.91 | 0.52 | 0.62 / 0.72 / 0.92 | ₹1,005 / 1,167 / 1,492 | **0.68 / 0.79 / 1.01** |
| Debit spread ATM/+200, DTE 2 | 76 net | 0.23 | 2 legs | 0.70 / 0.90 / 1.30 | ₹1,138 / 1,463 / 2,113 | **3.03 / 3.90 / 5.64** |

What this says:
- **Futures cost 10-20× more per index point than options.** Futures STT is on notional; option STT is on premium.
- **At s = 0.05, ATM, ITM100 and ITM200 cost almost the same per index point (0.87-0.91).** At s = 0.20, deep ITM is
  clearly cheapest (1.01-1.24 vs 1.40-1.47). The strike choice therefore depends on the real spread of each strike.
  If Monday's recorder shows ATM at 0.05 and ITM200 at 0.20, the per-delta cost is equal (0.87 vs 1.01-1.24), and ATM's
  decay (§1.2) becomes the tie-breaker against it.
- **Slippage is half the option round trip at s = 0.20** (₹650 of ₹1,275 at a 150 premium) and a fifth at s = 0.05
  (₹163 of ₹788). STT is the largest charge (₹366 of ₹625).
- **The two repo cost models disagree 7-12×**: the lab uses 0.20 pt/side, while `costs.py` uses 1% of premium per
  side (1.3-2.3 pts/side at these premiums).
- **Debit spreads** double the per-leg friction and cut delta, so they lose intraday at every slippage level.

### 2.3 Exits choose holding time; they do not create edge

For any exit rule τ on a drift-plus-martingale path: E[gross] ≈ δ · μ̇ · E[τ] − b · E[τ]. An exit changes only E[τ]
(and stop-fill quality). That is why round 7 found realised win rate tracking break-even within 0-6 points across 58
geometries. The W exit (1 EM stop / 2 EM target) is a ~38-minute hold: E[τ] = a·b/σ² ≈ 0.8 × 1.6 × 30 min.

**Decomposing the ₹2,200 random-entry loss** (1.35 option pts at 25 lots), per the founder's correction (arith; confirm
in T2):

| Component | ₹ at 25 lots | Option pts |
|---|---|---|
| Charges (premium 150-231) | ₹625-937 | 0.38-0.58 |
| Slippage at s = 0.20 | ₹650 | 0.40 |
| **All-in friction** | **₹1,275-1,587** | **0.78-0.98** |
| Net decay over ~38 min (κ 0.07-0.16) | ₹210-480 | 0.13-0.30 |
| Residual: stop fills at the next bar after the barrier, −₹30k gap-throughs | ₹130-715 | 0.08-0.44 |
| **Total** | **₹2,200** | **1.35** |

At s = 0.05 the friction line falls to ₹788-1,100, so a random entry would lose ~₹1,710 instead of ₹2,200. That
is still a loss, because decay and stop mechanics remain. The skilled analysts claw back ~₹1,000 (≈ 0.03 EM30).
**§1's design is the one way around optional stopping that does not need slow drift.** It relies on predictable
volatility clustering and post-breakout direction, which must be shown (TA2, TA1).

### 2.4 Break-even for each buyer idea (time exits)

k(h) = (C + b·h/30)/δ is the break-even mean move over a hold of h minutes. p*(h) = Φ(k/σ_h) is the break-even
direction hit rate. Measured skill: μ30 = 0.02 EM30 (0.55 pts, OOS-like) to 0.05 EM30 (1.37 pts, DEV-like). **Money
is linear in μ, not in hit rate** (52% ⇒ 1.72 pts; 0.05 EM ⇒ 51.6%). **Each cell is s = 0.05 / 0.10 / 0.20.**

| Idea (buyer only) | δ / b per 30 min | Required μ (idx pts) | Required μ (EM30) | p* | Clears measured skill? |
|---|---|---|---|---|---|
| Intraday future, 30 min | 1 / 0 | 14.2 / 14.3 / 14.5 | 0.52 / 0.52 / 0.53 | 66.1-66.4% | **No** (10-26× short) |
| Future held to 15:15 (comparison) | 1 / 0 | same | same | 55.8-55.9% | **No** |
| ITM100 DTE 2, 30-min hold (engine today) | 0.62 / 0.18 | 1.20 / 1.36 / 1.68 | 0.044 / 0.050 / 0.061 | 51.4 / 51.6 / 52.0% | DEV-like skill clears only at s = 0.05 (break-even at 0.10); OOS-like never |
| ATM DTE 2, 30-min hold (arithmetic only; not recommended) | 0.50 / 0.18 | 1.24 / 1.44 / 1.83 | 0.045 / 0.052 / 0.067 | 51.4 / 51.7 / 52.1% | Same as ITM100, with worse quiet-market decay (§1.2) |
| Deep ITM (ITM200 DTE 0, 11:00), 30 min | 0.91 / 0.16 | 0.86 / 0.97 / 1.19 | 0.031 / 0.035 / 0.043 | 51.0 / 51.1 / 51.4% | DEV-like yes at all s; OOS-like no |
| ITM200 DTE 0 at 14:30, 30 min | 1.00 / 0.01 | 0.62 / 0.72 / 0.92 | 0.023 / 0.026 / 0.034 | 50.7 / 50.8 / 51.1% | DEV-like yes; OOS-like borderline. Only if deep-ITM 0DTE spreads are really ≤ 0.10 (**VERIFY**) |
| Debit spread ATM/+200, 30 min | 0.23 / 0.03 | 3.16 / 4.03 / 5.77 | 0.115 / 0.147 / 0.211 | 53.7 / 54.7 / 56.7% | **No** |
| Maker entry and exit, ITM100 (charges only, zero adverse selection) | 0.62 / 0.18 | 1.04 | 0.038 | 51.2% | Upper bound only; adverse selection is unmeasured |
| **Deep ITM (ITM200 DTE 1) held 120 min** (comparison) | 0.79 / 0.17 | 1.74 / 1.86 / 2.12 | 0.063 / 0.068 / 0.077 | 51.0-51.2% | Only if drift accrues |
| **Deep ITM held 225 min, 11:30 → 15:15** (comparison) | 0.79 / 0.17 | 2.51 / 2.63 / 2.89 (stress 3.51) | 0.091 / 0.096 / 0.105 (stress 0.128) | 51.1-51.2% | Only if drift accrues |
| ITM100, 90-min time exit (CMP-B-like) | 0.62 / 0.18 | 1.76 / 1.92 / 2.24 | 0.064 / 0.070 / 0.082 | 51.2-51.5% | Only if drift accrues (and ITM100 is not deep, so CMP-B forces ITM200) |

Long-hold net per trade, deep ITM (ITM200 DTE 1), option pts per unit; comparison only:

| μ30, accrual, slippage | 30 min | 60 min | 120 min | 240 min |
|---|---|---|---|---|
| 0.02 EM30, linear, s = 0.05 | −0.42 | −0.16 | +0.36 | +1.39 |
| 0.02 EM30, linear, s = 0.20 | −0.72 | −0.46 | +0.06 | +1.09 |
| 0.02 EM30, flat, s = 0.05 | −0.42 | −0.59 | −0.94 | −1.63 |
| 0.05 EM30, linear, s = 0.05 | +0.23 | +1.13 | +2.94 | +6.57 |
| 0.05 EM30, linear, s = 0.20 | −0.07 | +0.83 | +2.64 | +6.27 |
| 0.05 EM30, flat, s = 0.20 | −0.07 | −0.24 | −0.59 | −1.28 |

Slippage is a fixed 0.30 pt shift. It matters for 30-minute trades and hardly at all for long holds, where decay (κθ)
and the shape of the drift dominate.

### 2.5 The ₹30k cap is a hidden stop

At 25 lots the cap is hit after **~30 index pts** on ITM100 (δ 0.62) and **~23 pts** on ITM200 (δ 0.79), about one
EM30. Long holds therefore need CAPLOTS of about 4-6 lots. BRK-BUY's structural stop (≈ 15 pts including slippage)
sits well inside the cap, which is why it can run full VOLSIZE size (CAPLOTS ≈ 45 at δ 0.62).

---

## 3. Comparison benchmarks (long holds only in deep ITM or futures) and overlays

These exist to answer "is the active design better than simply holding a cheap delta?" They follow §1.6.0.

| ID | Spec | Sizing | Pass bar / placebos | Trials |
|---|---|---|---|---|
| **CMP-A Trend-hold, deep ITM** | Premise gate (T1): μ(to 15:15) ≥ **0.13 EM30** (clears the stress case in §2.4) and μ(120) ≥ 1.6 × μ(30), t ≥ 2 on P0 and P1. Entry: first of {10:15, 11:30, 13:00} where ≥ 3 of the 4 trend analysts agree and none dissents, and strength z = \|close − TWAP\| / EM30 ≥ P1 q90. ITM200 (ITM300 if DTE ≥ 3). Exit 15:15; catastrophe stop 1.5 × EM30 × √(minutes left / 30). | min(VOLSIZE, CAPLOTS(0.9, stop)) ≈ 4-6 lots | §1.6.0; PL-SIDE, PL-TIME | 1 |
| **CMP-B Engine entries, time exit, deep ITM** | Round-7 wide book (no logit gate). Strike forced to ITM200. Exit at entry + 90 min or 15:15. The same lots are applied to the signal-exit (XS) and engine-geometry (X0) comparators. | min(VOLSIZE, CAPLOTS(δ, 1.5 × EM30 × √3)) ≈ 6-9 | Also Δ vs XS and X0 > 0 under stress on P1 and P2 | 1 + 3 diagnostics (60 min, 120 min, EOD) |
| **CMP-F One-night deep ITM** | After a trend day (\|C − O\| / (H − L) ≥ 0.6 and \|C − O\| ≥ 0.6 × ATR14), buy ITM300 on the next expiry ≥ 2 sessions away at 15:20; exit next day 15:15. Price-free premise first (T9). | CAPLOTS ≈ 1-2 | §1.6.0 | 1 |
| **CMP-FUT Same signal as CMP-A in futures** | Same entry and exit as CMP-A. | CAPLOTS(1.0, stop) | Reported next to CMP-A. It is expected to fail on the 14.2-14.5-pt cost; it exists to put a number on the option-vs-future choice. | 1 |
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
   - **The ₹2,200 figure was being read as the round trip.** It is the random-entry loss under W, including decay and
     stop-outs (§2.3). The true all-in round trip is ₹790-1,660 at 25 lots. Any doc or prompt quoting ₹2,200 as
     "cost" overstates friction by 30-180%.
   - Two cost worlds in the repo (7-12× apart), plus a small exchange-rate mismatch: founder 0.0355299% vs
     `charges.yaml` 0.03503%.
   - A flat s = 0.20 is too generous for ITM200 at DTE 0-1, for the open and close, for burst minutes and for 1,625
     units, and too harsh for ATM (0.05-0.10). Hence every verdict is reported at 0.05 / 0.10 / 0.20 and at stress.
   - STT eras: 0.0625% → 0.10% (Oct 2024) → 0.15% (Apr 2026). That is +0.175 pt = ₹284 per trade at a 200-pt premium
     vs DEV-era rates.
   - 7C's fly cost (5.4 pts) is roughly double what the arithmetic gives (T7; flies are out of scope, but the same cost
     code may be used elsewhere).
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
| T10 | Monday measurement protocol | depth recorder | Half-spread and top-of-book size by strike (ATM, ITM100, ITM200, ITM300) × DTE × {09:15-09:30, normal, **breakout minutes**, 14:30+}; the cost of sweeping 1,625 units. After 10 sessions: replace the assumed slippage s with measured half-spreads. After 20: run overlay E and second-level time stops. | Burst half-spread > 0.30 (above the stress level) on the DTE-rule strike ⇒ recompute §1.3-1.4 before any BRK-BUY verdict. | n/a |

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
  - Founder friction: Dhan ₹20/order, STT 0.15%, exchange 0.0355299%, stamp 0.003%, GST 18%, lot 65; slippage
    0.05 / 0.10 / 0.20 per side. ₹2,200 is the random-entry loss, not the round trip.
- **Rejected:**
  - Holding ITM100/ATM on slow drift: drift of 0.02-0.05 pts/min is below decay of 0.06-0.47 pts/min per delta.
  - "A better exit alone fixes it" (optional stopping).
  - Intraday futures (₹23.1-23.6k per round trip at 25 lots).
  - Debit spreads intraday.
  - Writer-side structures (out of scope).
  - More side routers.
  - Hit rate as the skill metric.
  - Quoting ₹2,200 as the round-trip cost.
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

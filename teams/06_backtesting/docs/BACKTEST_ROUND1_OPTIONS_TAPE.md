# BACKTEST — Round 1 on the options tape (EXPLORATORY)

**Date:** 2026-10-27 · **Data:** `data/tape/v2/` 13 usable days 2026-09-29..10-22 (09-28 and 10-06 dropped: 1h tape / 59% stale), 22 sym-days (NIFTY 13, SENSEX 9). Paper research only; no broker calls.

## Now / Why / Next
- **Now:** No rule is proven. One family (OI flow on ATM strikes) made money on the tape, but a plain 15-min momentum rule did about the same, and that momentum rule **loses in every year of 5y index data**. The 13 tape days look like a lucky trending stretch.
- **Why:** Options were priced for a bigger move than happened on all 22 sym-days (median realized/implied vol 0.40–0.99), so buying premium is up against it. Short-term direction looked predictable here only because of the regime.
- **Next:** Keep `oi_flow` as a **shadow-only** rule, fixed from today, and score it against the r15-momentum control on days from 2026-10-23 on. Do not size up.

## Method (all mandatory checks on)
- Decide at a 5s snapshot. Buy at the **ask of the next snapshot**. Sell at the **bid of the snapshot after the exit trigger**, so stops gap through at the real bid. 15:15 flatten. Prices come from depth for every subscribed strike, because a strike drops out of `quote_snapshots` once ATM rolls. Using snapshot-only prices was a bug in my first pass.
- Costs: `config/charges.yaml` ×1.5, ₹20/order, STT 0.15% on the sell side, NSE 0.0355% / BSE 0.0325%, GST 18%, stamp. 10 lots (NIFTY 650, SENSEX 200).
- Walk-forward by day: the sign and threshold come from earlier days only, and trading starts after 3 training days. Late half = days ≥ 2026-10-13.
- Placebos (1000 runs each):
  - **pct/p**: the same number of trades per sym-day, at random minutes and random sides, with the same exit.
  - **p_side**: the same times with a random CE/PE flip.
  - **p_day**: the side is flipped for a whole sym-day at once. This is the honest one, because trades within a day are correlated.
- A random ITM200 15-min trade averages **−₹1,270** (spread + charges + theta).

## Results (n, avg ₹/trade net, total ₹, placebo)
| Family / variant | n | avg | total | maxDD | rand pct | p_day | late half | verdict |
|---|---|---|---|---|---|---|---|---|
| F1a ATM straddle 09:46→15:15 | 15 | +4,741 | +71k | −109k | 98.7 | – | +47k (10) | weak, n=15, 47% win |
| F1b same, only if RV/IV > prior median | 8 | −4,148 | −33k | −109k | 90.9 | – | −56k | reject |
| F1c straddle when RV/IV > q0.8, hold 30 | 74 | +398 | +29k | −80k | 85.3 | – | +39k | reject (p 0.15) |
| F2 futures depth imbalance (NIFTY) | 135 | +175 | +24k | −202k | 87.5 | 0.20 | +186k | reject |
| **F2 oi_flow (ATM PE−CE OI build, 15m)** | 149 | +3,776 | **+563k** | −142k | 100 | **0.002–0.004** | +481k (123) | see controls |
| F2 premium-vs-index divergence | 286 | −1,399 | −400k | −463k | 34 | 0.60 | −364k | reject |
| F2 r15 (sign learned) | 194 | −1,359 | −264k | −496k | 41 | 0.65 | −58k | reject |
| F2 futures basis change | 138 | −1,670 | −230k | −370k | 44 | 0.58 | −140k | reject |
| F2 straddle-premium change | 196 | −2,152 | −422k | −440k | 18 | 0.83 | −307k | reject |
| C1 control: r15 momentum, sign forced + | 198 | +2,686 | +532k | −226k | 99.9 | 0.011 | +504k | same as oi_flow |
| C2 control: buy in direction of ATM roll | 278 | +1,358 | +378k | −255k | 99.8 | 0.010 | +262k | momentum |
| C4 oi_flow when ATM did NOT roll | 96 | −1,363 | −131k | −253k | 44 | 0.47 | −150k | edge disappears |
| F4 ridge on all features (walk-forward) | 183 | +3,848 | +704k | −104k | 100 | 0.000 | +700k | uses r5/r15 → momentum |
| **5y check: C1 rule on index 1m 2021–26** | ~12k/sym | −1.4 to −2.0 bps | negative **every year** (t −1.4 to −6.5) | | | | | only 7–9% of 13-day windows > 0 |

How robust `oi_flow` is (p_day in brackets): ATM strike +398k (0.010), ITM100 +495k (0.005), NIFTY only +342k (0.013), SENSEX only +221k (0.125), after 10:00 +382k (0.033), +1 point slippage per side +446k (0.003), q0.7 +295k, q0.9 +366k, hold 5 +167k, hold 30 +539k. 14 of 19 sym-days were positive.

**F3 exits** were judged on the same oi_flow entries:

| Exit | Total |
|---|---|
| time 15 | +563k |
| time 30 | +539k |
| time 60 | +678k |
| EOD | +472k |
| SL10/TP20 | +464k |
| SL5/TP10 | +189k |
| SL15/TP30 | +467k |
| trail 8% | +250k |
| trail 15% | +324k |
| ATR×1 stop | +721k |
| ATR×2 + TP30 | +641k |

No exit rule turned **random** entries positive; the best was trail 8%/60m at −₹1,031 per trade. Tight stops and targets mostly lose money by cutting winners. With this little data, the exit differences are not significant.

**Multiple testing:** about 96 variants were tried (39 IC cells, 4 F1, 6 F2 trades, 12 robustness, 4 controls, 11 exits, 1 ridge, 18 q×hold diagnostics, 1 5y check). On the 6 F2 trade features alone, Bonferroni turns p_day 0.004 into 0.024. Across all variants it is about 0.4.

## Best candidate (shadow only, pre-registered)
- **What it is:** NIFTY and SENSEX, each minute from 09:20 to 15:00.
- **Signal:** take the current ATM CE and PE. `oi_flow = (ΔOI_PE − ΔOI_CE over the last 15 min, same instruments) / (OI_PE + OI_CE)`.
- **Entry:** if `oi_flow > +thr`, buy ITM200 CE. If `oi_flow < −thr`, buy ITM200 PE. `thr` = 80th percentile of |oi_flow| on all prior days (0.1095 now). Fill at the ask.
- **Exit:** sell at the bid after 15 min, or at 15:15.
- **Sizing:** one position per symbol, 10 lots.

**Weaknesses:**
- It only works in minutes where the ATM strike rolled.
- 80% of trades point the same way as the day's trend.
- A price-only momentum control matches it, and 5y data rejects that momentum.
- SENSEX on its own is not significant.
- It rests on 13 days and one regime.

## Data that would raise confidence most
1. **Historical 1m option OI for ATM±2 strikes (expired weeklies, ≥250 days).** This would test oi_flow against the momentum control across regimes without waiting.
2. **More tape:** at least 40 new out-of-sample days (about 2 months, with a range-bound stretch). The test: oi_flow beats C1 momentum on those days with p_day < 0.05. Today one sym-day has sd ≈ ₹58k against a mean of ₹30k, so about 16 sym-days give t≈2 if the edge holds. The real risk is the regime, not power.
3. **Daily IV per strike (`chain_iv`) on every tape day.** This would let F1 compare realized and implied vol properly.

## Files
- `scripts/lab5y/tape_cache.py` streams the tape into per-day parquet.
- `scripts/lab5y/tape_lab.py` holds the F1–F4 families, placebos, controls and exits.
- `scripts/lab5y/mom5y.py` runs the 5y momentum check.

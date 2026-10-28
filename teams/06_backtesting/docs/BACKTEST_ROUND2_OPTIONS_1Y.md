# BACKTEST — Round 2: one year of real option bars (EXPLORATORY → one shadow candidate)

**Date:** 2026-10-27. Paper research only. No broker calls (data came from `pull_expired.py`, which the founder approved).

**Data:** Dhan rolling expired options, 1m bars, nearest weekly, ATM−3..ATM+3, CE and PE. The span is 2025-10-27..2026-10-23, giving 246 days × NIFTY and SENSEX (10-27 is excluded because it is a partial day).

**Split:**
- **Dev:** before 2026-07-27, 184 days. Walk-forward by month, with Nov as training only, so the test months are Dec–Jul.
- **Holdout:** 2026-07-27..10-23, 62 days. It was run **once**, for 3 finalists named in advance.

## Now / Why / Next
- **Now:** No rule qualifies for live trading.
  - Round 1's `oi_flow` fails on a full year: −₹2.16M on dev, no better than random.
  - Every OI, IV and skew signal and both ML models lose after costs.
  - One volatility-timing rule survived both dev and holdout, but only weakly: buy the ATM straddle when the first 30 minutes moved more than IV implied. Holdout was +₹1.30L on 27 trades, p=0.03, and **all of it came in October**.
- **Why:** On a normal day, options price a bigger move than happens. Intraday realized vol is 0.50–0.69 × IV, and a straddle held to expiry returns 52–86% of its cost. The only window where buyers win is a day that has *already* started violently.
- **Next:** Run FIN1 (below) as **shadow only**, one paper straddle per day per index, for at least 40 new days. It is adopted only if its p is below 0.05 against random days **outside** October 2026. Retire `oi_flow` from shadow.

## Method
- **Contracts:**
  - Each contract series was rebuilt per (expiry, strike) from all 7 offsets, so a held contract keeps its own price after ATM rolls.
  - If the contract leaves the ±3 window, the trade exits at its last known close. This is counted in `lost%`.
  - Dropping those trades instead would delete the big winners.
- **Expiry:** NIFTY Tue and SENSEX Thu, with a holiday shift to the prior day. This is checked against the data: ATM straddle extrinsic at 15:29 has a median of about 0.01–0.02% of spot on expiry days and about 0.5–1.3% on other days. Max on an expiry day is 0.39% (SENSEX 2026-03-19); min on a non-expiry day is 0.31%. 8 expiries were holiday-shifted.
- **Fills:**
  - Decide at the close of bar i. Buy at the open of bar i+1 plus the half-spread.
  - Time exits sell at the open of the exit bar minus the half-spread.
  - A stop fills at min(stop, open). If the stop and target fall in the same bar, the stop is used.
  - Entries run 09:20–14:59, which also excludes the last 30 minutes of expiry day. All positions are flat at 15:15. iv=0 is treated as missing (1.18% of bars).
- **Spreads:**
  - Taken from the 13-day tape (`opt1y_spread.py`). The 75th percentile is applied by sym × premium bucket × time of day × expiry-day.
  - The median and p75 half-spread in points are shown below.
  - Half-spread is about 0.12–0.15% of premium. Using the median instead of p75 changes the finalists by under ₹10k.

| | ATM | ITM3 | OTM3 |
|---|---|---|---|
| NIFTY | 0.12 / 0.15 | 0.07 / 0.10 | 0.25 / 0.28 |
| SENSEX | 0.40 / 0.53 | 0.28 / 0.40 | 0.68 / 0.85 |

- **Costs:** `config/charges.yaml` ×1.5, 10 lots. Lot sizes are NIFTY 65 and SENSEX 20, held constant.
  - The data has no lot sizes, so this could not be checked.
  - My understanding is that NIFTY was 75 per lot until the Dec-2025 series. If so, Nov–Dec rupee figures are understated by about 13%. Signs do not change.
- **Placebos:** 1000 runs each.
  - **pct/p:** random minute and side on the same sym-days, with the same exit.
  - **p_day:** the whole day's side is flipped.
  - **Day-level straddle rules:** the same number of random days from the same months.
- **Controls:**
  - **mom_same:** the same entries, with the side set by 15-min index momentum.
  - **5y index:** `fade5y.py`, for the price-only effect.
- **Random baselines:** a random ATM trade averages **−₹660 (15 min) / −₹780 (30 min) / −₹1,330 (to 15:15)**. No exit rule made random entries positive.

## (a) Results — dev walk-forward (n, avg ₹ net, total ₹)
| Family / variant | n | avg | total | pct / p / p_day | mom_same | WF mo + | verdict |
|---|---|---|---|---|---|---|---|
| **F1a oi_flow frozen 0.1095, ATM, 15m** | 3479 | −619 | −2.16M | 47 / 0.53 / 0.52 | −2.34M | 3/9 | **reject** |
| F1b same, ITM1 | 3479 | −907 | −3.16M | 30 / 0.70 | −3.38M | 1/9 | reject |
| F1c / F1d: ATM not rolled / rolled | 2634 / 2615 | −835 / −503 | −2.20M / −1.32M | 12 / 64 | – | 1/9, 3/9 | reject |
| F1e oi_flow WF q0.8 | 2713 | −529 | −1.43M | 64 / 0.36 | −2.05M | 3/8 | reject |
| F1f oi_flow over ATM±3 | 2398 | −673 | −1.61M | 34 / 0.66 | −1.66M | 2/8 | reject |
| C1 15m momentum WF q0.8 | 3638 | −837 | −3.04M | 18 / 0.82 | = | 2/8 | reject |
| F2a ATM straddle 09:46→15:15, every day | 368 | −5,890 | −2.17M | – | – | 0/9 | buyers lose |
| F2a by DTE 0/1/2/3/4 | ~70 each | −14.8k / −2.6k / −6.0k / −4.9k / −0.3k | | | | | DTE0 is worst |
| F2b straddle if HAR-RV/IV > q0.7 | 69 | −4,960 | −342k | 64 / 0.36 | – | 0/8 | reject |
| **F2b straddle if first-30m RV/IV > q0.7 (FIN1)** | 61 | +1,428 | **+87k** | 99.8 / **0.002** | – | 5/8 | candidate |
| F2b prev-day RV/IV, gap/IV, cheap-IV pct | 79 / 134 / 124 | −4.9k / −6.0k / −4.6k | −390k / −799k / −570k | 59 / 40 / 72 | | ≤2/8 | reject |
| F2c ATM in 09:15–09:45 direction if or_iv high | 61 | +892 | +54k | 56 / 0.44 | −112k | 3/8 | reject |
| F3a expiry straddle 13:30 / 14:15 → 15:15 | 78 | −3.6k / −5.2k | −284k / −407k | 1 / 64 | | 2/9 | reject |
| F3b expiry straddle if morning RV/IV high | 13 | −2.5k | −33k | 60 | | 3/8 | reject |
| F3c expiry 12–13h range breakout, 30m / EOD | 78 | −2.8k / −5.1k | −218k / −394k | 10 / 25 | same | 1–2/9 | reject |
| F3d / F3e pin toward / away from max-OI strike | 29 | −410 / −1.6k | −12k / −48k | 64 / 55 | −141k | | reject |
| F4 (13 features: oi_flow(_w), PCR, skew, Δskew, IV divergence, ΔIV, long/short buildup, short covering, CE/PE volume, r15, rday), WF sign, q0.8, 30m | 1290–3508 each | −324 to −1,364 | all negative (−0.76M to −4.24M) | best 94 / 0.06 (r15 fade) | | ≤3/8 | reject |
| F5 ML logistic / gradient boosting / momentum-only, deciles, 30m | 2497 / 2065 / 2286 | −1,408 / −521 / −1,023 | −3.52M / −1.08M / −2.34M | 1 / 80 / 22 | | 1/8, 5/8, 1/8 | reject |
| R fade r15 grid, 9 q×hold cells | | all negative | | 48–94 | | | reject |
| R fade r15 q0.8 30m, decisions before 12:00 (FIN3, post-hoc) | 1239 | +191 | +237k | 99.6 / 0.004 / 0.006 | −2.46M | 5/8 | weak |
| R FIN1 robustness: q0.5 / 0.6 / 0.8 / 0.9 | 116 / 90 / 45 / 32 | −2.2k / −1.6k / +0.3k / −0.3k | −261k / −142k / +13k / −9k | | | | **fragile** |
| R FIN1 with 15m / 60m opening window | 70 / 59 | −536 / −746 | −38k / −44k | 98 / 92 | | | fragile |
| R FIN1, non-expiry days (FIN2) | 56 | +3,376 | +189k | 100 / 0.000 | | 6/8 | candidate |
| R FIN1 exits: 60m / 120m / 210m hold, OTM1 strangle | 61 | +1.8k / +0.6k / +1.2k / +4.2k | +110k / +36k / +71k / +256k | 97 / 68 / 73 / 87 | | | noisy |
| X exits on fade entries (time 15/30/60/EOD, SL/TP, trail, ATR, index stop) | 2358 | all negative, −286 to −1,995 | | | | | none helps |

**Other findings:**
- **IC study:** Δskew (IC −0.04, 0/9 months positive) and IV divergence (+0.03, 7/9) are consistent but tiny, and neither survives costs.
- **ML importance:** momentum (r30, r15), the PCR level and the CE/PE volume ratio top the logistic weights. Gradient boosting has a permutation importance of ≈0 for every feature except straddle decay.
- **5y index check of the r15 fade:** gross is +0.0 to +0.5 bps a trade in every year 2022–26, with |t| < 1.3. That is far below the cost of an option trade.

**Multiple testing:**
- About 87 trade variants, plus 52 IC cells.
- Bonferroni on FIN1's dev p=0.002 gives about 0.17. **Nothing is significant on dev after correction.**

## (b) Holdout — the 3 finalists, frozen thresholds from all dev days, run once
| Finalist | n | win | avg | total | maxDD | p (random days / minutes) | Aug / Sep / Oct |
|---|---|---|---|---|---|---|---|
| reference: straddle every day | 124 | 42% | −1,029 | −128k | −374k | – | −95k / −87k / +213k |
| **FIN1** straddle if first-30m RV/IV > 1.004 | 27 | 59% | +4,805 | **+130k** | −69k | **0.032** | −13k / −58k / **+201k** |
| FIN2 FIN1 on non-expiry days | 25 | 56% | +3,140 | +78k | −69k | 0.10 | −13k / −58k / +150k |
| FIN3 r15 fade before 12:00 | 331 | 40% | −2,171 | −719k | −808k | 0.996 | +2k / −90k / −97k / −533k |

- **FIN1 detail:**
  - All 14 winners above ₹9k were in October.
  - NIFTY made +115k and SENSEX +15k.
  - Bonferroni ×3 gives p≈0.10.
- **FIN3 fails.**

**Two disclosures.** Before naming the finalists I saw two holdout numbers:
- A descriptive realized/implied table by DTE.
- An aggregate fade gross in bps.

No parameter was set from them, but read the FIN1 holdout with that in mind.

**Bug I caught:** my first feature build wrapped `s[i-15]` to the end of the day for decisions at 09:20–09:29. That produced a fake +₹9.2L "fade" rule, which I fixed before naming any finalist.

## (c) Best rule — shadow only, it does NOT qualify for live
- **FIN1:** NIFTY and SENSEX, each day independently.
- **Signal:** at 09:45, compute `or_iv`. This is the RV of 1m spot log returns from 09:15 to 09:45, annualised ×√(252·375/30), divided by the mean ATM CE/PE IV at 09:45.
- **Entry:** if `or_iv > 1.0` (the frozen dev 70th percentile, 1.004), buy 10 lots of the ATM CE plus ATM PE (one strike) at the 09:46 open.
- **Exit:** sell both at the 15:15 open. Each leg also exits if its strike drifts more than 3 strikes from ATM.
- **Other rules:** no stop and no target. One straddle per index per day.
- **Evidence:**
  - Dev +87k (61 trades) and holdout +130k (27 trades).
  - It is fragile: other thresholds and windows lose, and the holdout gain is all from October.

## (d) Realized vs implied for buyers (dev)
- **Intraday realized vol (09:15–15:30, 1m) / ATM IV**, median by DTE 0–4:

  | | DTE0 | DTE1 | DTE2 | DTE3 | DTE4 |
  |---|---|---|---|---|---|
  | NIFTY | 0.53 | 0.53 | 0.64 | 0.69 | 0.61 |
  | SENSEX | 0.65 | 0.58 | 0.53 | 0.52 | 0.60 |

- **ATM straddle held to expiry:** pays a median 0.52–0.86 of its premium (mean 0.73–0.94), so it loses before costs at every DTE.
- **Intraday straddle:**
  - It loses on every DTE.
  - Expiry day is the worst at −₹14.8k a day.
  - DTE4 is close to break-even.
- **Cheap IV does not help buyers:** trading the low-IV-percentile days lost −570k.
- **The only useful predictor is the opening 30 minutes' realized move against IV** (Spearman 0.66 with the day's RV/IV, against 0.50 for HAR on 5y data).
- In the holdout months (seen, disclosed above), NIFTY RV/IV was 0.33–0.63.

## (e) Files (not committed)
- `scripts/lab5y/opt1y_load.py`: JSON → long parquet, plus the expiry audit.
- `scripts/lab5y/opt1y_spread.py`: tape spreads → `spreads.csv`.
- `scripts/lab5y/opt1y_lab.py`: panel, fills, placebos, and families `oi vol exp f4 ml rob exit final`, plus `--holdout`.
- `scripts/lab5y/opt1y_ml.py`: walk-forward logistic and gradient boosting (sklearn, py3.12 venv).
- `scripts/lab5y/fade5y.py`: 5y index check of the fade.
- **Rerun:** `opt1y_load.py OUT && opt1y_spread.py TAPECACHE OUT && opt1y_lab.py OUT oi vol exp f4 rob exit final`. Run `opt1y_ml.py OUT` before `opt1y_lab.py OUT ml`.

## FIN1 forward shadow (from 2026-10-27, paper log only, never an order)

- Script: `scripts/lab5y/fin1_shadow.py` (stdlib only; `selftest` included). Runs in `scripts/claude_daily.sh close`
  after `desk.sh close`; one row per sym-day in `data/recon/fin1_shadow.jsonl` (gitignored). Fridays write
  `data/recon/fin1_shadow_week.txt`; the Monday close task prints it.
- Rule frozen: threshold 1.0042 (dev 70th pct of or_iv). Fills from the live tape: ask at 09:46:00, bid nearest 15:15:00.
- The tape has no IV, so IV = Black-Scholes on the 09:45 mid, r=6.5%, T=(calendar days to expiry + 0.5)/365. On the
  492 round-2 days this matched Dhan's IV decision on 96.1% (19 flips). Expiry-day IV differs most (SENSEX 22-Oct: ours 0.93 vs Dhan 0.65, both "skip").
- Backfill from tape days with a full morning: 16, 21, 22 Oct: 4 signals, net Rs -7,512; straddle every day Rs -68,251.
- Adopt rule: 40+ new trading days and random-days p < 0.05 outside Oct-2026. Otherwise retire.

## Round 3: new information sources (2026-10-28, dev + holdout, all null)

**Question.** Does public data from outside the price feed, known before 09:15 IST, help an option buyer?
Same panel, fills, costs (x1.5), placebos and dev/holdout split as round 2. One family: `opt1y_lab.py OUT ext [--holdout]`.

**Sources (read-only, official, no keys; fetched by `scripts/lab5y/ext_fetch.py` into gitignored `data/cache/ext/`).**
- **NSE participant-wise OI**, `nsearchives.nseindia.com/content/nsccl/fao_participant_oi_DDMMYYYY.csv`.
  - 263 days were fetched (17 weekdays missing; these should be the exchange holidays).
  - Features use the day-on-day change in FII positions. They come from the file of the previous NSE day, which is published after that day's close.
  - `fii_fut`: index-futures net long ratio.
  - `fii_opt`: index-option call net minus put net.
- **FRED (St. Louis Fed).** Each feature is the last US date before the IST day.
  - `SP500`: log return.
  - `VIXCLS`: log change.
  - `DEXINUS`: rupee change; positive means the rupee got stronger.
- **Event days.**
  - RBI MPC decision days (rbi.org.in; announced at 10:00 IST): 2025-12-05, 2026-02-06, 04-08, 06-05, 08-05, 10-07.
  - FOMC (federalreserve.gov): the first NSE day after each decision day, because the decision lands around 23:30 to 00:30 IST.

**Rules.** All 9 were named, with their sign fixed, before any result was seen.
- **Direction:** buy ATM in the feature's direction from 09:46 to 15:15 on days where the feature's size is above the walk-forward 70th percentile.
- **Volatility:** buy the ATM straddle from 09:46 to 15:15 on days where the feature is above the walk-forward 70th percentile.
- **Events:** buy the straddle on every event day.

| rule | dev n | dev net | dev p | holdout n | holdout net | holdout p |
|---|---|---|---|---|---|---|
| dir by FII futures change | 104 | -854k | 0.999 | 10 | +21k | 0.30 |
| dir by FII options change | 96 | -166k | 0.64 | 52 | -93k | 0.64 |
| dir by S&P 500 overnight | 90 | -234k | 0.61 | 22 | -36k | 0.52 |
| dir by USD/INR | 144 | -431k | 0.74 | 20 | -98k | 0.74 |
| straddle if VIX jumped | 100 | -790k | 0.90 | 36 | +141k | 0.037 |
| straddle if big S&P move | 90 | -538k | 0.58 | 22 | +99k | 0.06 |
| straddle if big INR move | 144 | -946k | 0.74 | 20 | -27k | 0.53 |
| straddle on RBI days | 8 | -58k | 0.58 | 4 | -6k | 0.52 |
| straddle on FOMC next days | 12 | -81k | 0.53 | 4 | -70k | 0.98 |
| 10th, post-hoc: dir *against* FII futures | 104 | +452k | 0.038 | 10 | -29k | 0.56 |

- The p-values compare against random entries (direction rules) or random days (straddle rules). With 10 variants, Bonferroni needs p < 0.005, and nothing comes close.
- **FII contrarian.** After seeing dev, I added this rule because following FII did worse than a coin flip. It made +4.5L on dev, then lost on the holdout. It is rejected.
- **VIX straddle.** Its holdout gain is the same Aug–Oct straddle effect that FIN1 showed. On dev it lost every month (0/8), so it is not a signal.
- **RBI / FOMC.** Event days are already priced into IV: the straddle loses there as on other days. The samples are tiny (6 and 8 days).
- **Rank checks (Spearman).**
  - Against the 09:45-to-close move: |rho| ≤ 0.07 on dev for every source.
  - Against realized/implied: |INR move| gives -0.22 on dev and +0.22 on holdout. The sign flips, so it is not stable.

**Verdict.** None of these public daily sources gives an option buyer an edge after costs on this year: FII/DII positioning, US overnight returns, VIX, the rupee, and the RBI/FOMC calendar. FIN1 stays the only shadow rule.

**Not yet tested (needs data we do not have):**
- GIFT Nifty overnight, which needs a vendor history.
- Intraday news or headlines with timestamps.
- Order-book imbalance from depth, which needs more tape days. 13 days today; the recorder adds one per trading day.

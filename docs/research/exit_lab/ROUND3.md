# Exit Lab round 3b — pattern mining (paper / replay only)

**Status:** HYPOTHESIS / PAPER / **NO_PROMOTE**. **0 rules pass.** Playbook stays `enabled: false`.

This file is the round-3 report edited in place after the 3b spot-check. There is no `ROUND3B.md`.

## Reproduce (this file's only command)

```bash
python -m exitlab round3 --data .local_data --out /tmp/exitlab-r3b --seed 7 --reuse-entries /tmp/exitlab-fix/entries.json
```

Seed 7. Auto-detects `.local_data/last3d/` (`opt1m_last3d_part1-3.parquet` + `index_last3d.parquet`). Live tapes stay the final holdout. Raw JSON: `/tmp/exitlab-r3b/tables.json` plus `univariate.json`, `combos.json`, `walk_forward.json`, `holdout.json`, `as_traded.json`, `oracle.json`, `worst30.json`, `legacy_overlap.json`, `lookahead_test.json`, `peak_models.json`, `dropped_noops.json`, `time_tod.json`. Copy: `/opt/cursor/artifacts/exitlab-r3b/`.

CLI print: `n_variants_tested=654`, `n_hist_entries=3546`, `n_live_entries=419` (`random=278`, `v2_boss=60`, `legacy=81`), `n_hist_weeks=149`, `n_folds=12`, `passing=[]`, `lookahead_pass=true`, `lookahead_n=5000`.

Round-2 fixes stay on: marks use `strike_ltp` on the entry strike; missing strike is a hole; fills are LTP ± half-spread; DSR is Φ((SR−SR*)/se) in [0, 1]. V2 defaults and `config/v2/exits/exitlab_playbook.yaml` were not edited.

**Rank on 1-lot numbers** (lot size 65): `net_1lot`, `avg_pts`, `avg_inr_per_lot`. As-traded rupees are in `as_traded.json` and must not be compared across entry sets.

## Before / after the 3b fixes

| Headline | Round 3 (spot-check) | Round 3b |
|---|---|---|
| Hist source | 6 weekly `NIFTY_*.parquet` files | last3d parts 1–3 + matching index |
| Hist entries / minutes | 226 / 33,160 | **3,546 / 750,079** |
| Hist calendar | 38 sessions, ~6 expiry weeks | **444 sessions, 149 weeks** (150 expiries scanned; 154 in the files; 2 thin days) |
| Walk-forward folds | 10 (asked 12; `DATA_INSUFFICIENT`) | **12 expanding folds by expiry week** |
| Live sets reported | one mixed book (419) | **random 278 / v2_boss 60 / legacy 81**, each its own table |
| Rank unit | as-traded ₹ (25-lot MIX tails) | **1-lot ₹ + pts/trade**; as-traded kept aside |
| Hold live (mixed as-traded) | −₹13,43,070.41 | not mixed. Random 1-lot **−₹82,565.42**; v2_boss 1-lot **+₹1,738.20** (as-traded +₹3,476.39); legacy 1-lot **−₹50,559.26** (as-traded −₹12,63,981.38) |
| Peak models | never fired (`peak_*` = hold) | **fire**. Logit p10 OOS fire 12.0%; hazard p10 11.3%; tree p5 17.6%. AUC 0.50–0.55 |
| Trail vs pair | `pat_1_trail` = pair to the rupee | **412 / 202 / 405** live exits changed (`pat_0/1/2_trail`) |
| Partials / open clock | 1-lot partials + 09:15 window included | **dropped** with stated reasons |
| Look-ahead checks | 40 | **5,000** (0 mismatches; 4,475 hist + 525 live) |
| Label test | shuffle future *prices*; clock lift 1.309→1.320 | shuffle GOOD_EXIT **within day** and remine: top lift **1.212 → 1.023** (clock pair named CLOCK) |
| Clock-profit rule | not tested as its own plan | T ∈ {5,15,30,45,60}; T=45 least-bad on all three live sets; CI still crosses 0 |
| Legacy overlap | count of same-moment fires | same + **share of 1-lot gain from the 180s overlap** |
| Variants / passing | 605 / `[]` | 654 / **`[]`** |
| Oracle (as-traded) | +₹49,62,559.88 mixed | random +₹5,97,499.50; v2 +₹3,33,638.50; legacy +₹40,31,421.88 |

## Now / Why / Next

- **Now:** Nothing passes. The bar is “positive vs `hold_to_1515` on 1-lot in most walk-forward folds **and** holdout 1-lot CI_lo > 0 **and** DSR ≥ 0.9, on **every** live set”. `passing` and `passing_by_set` are empty. On random (the sanity set) the least-bad rule is `peak_hazard_p10` at **+₹58,242.81 / +4.34 pts** vs hold **−₹82,565.42**, capture 0.097 of a **+₹5,97,499.50** oracle. Bootstrap CI_lo is **−₹16,545**; DSR is **0.043**.
- **Why:** A minute is a GOOD_EXIT 8.91% of the time (66,864 / 750,079). The strongest univariate is still the clock (`mins_to_1515` low / `tod_min` high, lift 1.212). Last3d is only the last three sessions before each weekly expiry, so every hist row is an expiry-week row (`normal` hist slice is `DATA_INSUFFICIENT`). Peak models now fire, but OOS AUC is 0.50–0.55 — they are not ranking peaks. Fast time-stops still harvest a large share of their “gain” from the same moments as legacy `CANCEL_AGAINST` (`time_edge_2_0.35`: 28/32, **78%** of 1-lot gain from the 180s overlap).
- **Next:** Founder does not promote. Do not enable the playbook. Do not put any of these rules on the live engine.

## 0. What was actually studied

| Set | Entries | Minute-rows | Coverage |
|---|---:|---:|---|
| last3d hist (seeded, ≥5/day target, ATM/ITM100/ITM200, CE+PE) | 3,546 | 750,079 | 445 days scanned, 443 kept, 2 thin; 150 expiries in the scan, 149 weeks in WF; 2023-08-01 … 2026-07-02 |
| Live tapes (reused entries.json) | 419 | 64,462 | 12 dual-tape days; **final holdout** |
| Walk-forward | 12 expanding | — | train starts 29 weeks, test 10 weeks/fold (last two folds 10 then 10 on 232/224 tickets) |

Hist has no bid/ask. Fills charge the V2 half-spreads (ATM 0.20 / ITM100 0.35 / ITM200 0.55) and the same book at 2× (`spread_stress`).

Labels use hindsight only. Features use `minutes[:i]` only.

Four of the 154 attached expiries produced no kept week in the WF key (150 scanned expiries / 149 weeks with at least one ticket). That is a thin-day skip, not a silent drop of the 12-fold grid.

---

## 1. Labels

`GOOD_EXIT` = local peak, prominence ≥ 1.5 × half-spread, no higher print later in the 5 / 15 / 30 / EOD window (`r3_core.label_window`). Holes stay `HOLD`.

On hist 15-minute labels: **base GOOD rate = 0.0891** (750,079 minutes). Features never include `label_*` / `GOOD_EXIT` / `HOLD` (`test_r3_features.py`).

---

## 2. Features (known before the candle)

Same feature set as round 3. Option: return since entry, peak-to-now DD, mom 1/3/5/10, body/wick, range expansion, minutes since last high, volume / OI change. Index: 1/5/15 move, VWAP and day high/low distance, first-hour break, round 100/50. Clock: `mins_to_1515`, `tod_min`, `age_min`, expiry flag. Opposite-strike 3-minute momentum. Delta proxy = option mom_1 / index mom_1.

Day index for VWAP / first-hour is the session series truncated to `available_ts < now`.

---

## 3. What differs: univariate + top 20 combinations

Base GOOD rate 0.0891. Lift = P(GOOD | tail) / base.

### Univariate (hist, label_15; top 12)

| feat | n | q25 | q75 | P(GOOD\|high) | P(GOOD\|low) | best | lift |
|---|---:|---:|---:|---:|---:|---|---:|
| mins_to_1515 | 750079 | 34 | 158 | 0.084 | 0.108 | low | 1.212 |
| tod_min | 750079 | 757 | 881 | 0.108 | 0.084 | high | 1.212 |
| mom_1 | 746533 | −1.70 | 1.75 | 0.100 | 0.074 | high | 1.121 |
| lower_highs_4 | 750079 | 1 | 2 | 0.082 | 0.099 | low | 1.112 |
| mom_10 | 714619 | −6.10 | 5.25 | 0.098 | 0.081 | high | 1.099 |
| mom_5 | 732349 | −4.15 | 3.80 | 0.096 | 0.079 | high | 1.078 |
| opp_mom3 | 739441 | −1.25 | 1.00 | 0.079 | 0.096 | low | 1.077 |
| mom_3 | 739441 | −3.20 | 2.90 | 0.096 | 0.079 | high | 1.075 |
| age_min | 750079 | 47 | 171 | 0.096 | 0.084 | high | 1.073 |
| ret_since_entry | 750079 | −0.198 | 0.128 | 0.094 | 0.090 | high | 1.059 |
| pts_since_entry | 750079 | −23.9 | 16.3 | 0.094 | 0.088 | high | 1.052 |
| mins_since_high | 750079 | 13 | 116 | 0.094 | 0.088 | high | 1.050 |

Clock is still first. A one-minute up-print and “not making lower highs” are the first path features.

### Top 20 two- and three-feature combinations

From `/tmp/exitlab-r3b/combos.json`. `clock=true` means every named column is in `{tod_min, mins_to_1515, age_min}`.

| # | feats | n | fire | hit | lift | clock | pts vs hold |
|---:|---|---:|---:|---:|---:|---|---:|
| 1 | mins_to_1515:low+tod_min:high | 188470 | 0.251 | 0.108 | 1.212 | **yes** | +0.10 |
| 2 | ret_since_entry:high+pts_since_entry:high | 168746 | 0.225 | 0.094 | 1.059 | no | −0.84 |
| 3 | lower_highs_4:low+mom_5:high | 127868 | 0.170 | 0.101 | 1.134 | no | +2.21 |
| 4 | lower_highs_4:low+mom_3:high | 126667 | 0.169 | 0.101 | 1.135 | no | +1.89 |
| 5 | mom_1:high+lower_highs_4:low | 105884 | 0.141 | 0.110 | 1.233 | no | +2.20 |
| 6 | mom_5:high+mom_3:high | 121443 | 0.162 | 0.098 | 1.099 | no | +1.45 |
| 7 | lower_highs_4:low+opp_mom3:low | 114326 | 0.152 | 0.100 | 1.118 | no | +1.43 |
| 8 | lower_highs_4:low+mom_10:high | 103565 | 0.138 | 0.104 | 1.171 | no | +2.13 |
| 9 | mins_to_1515:low+age_min:high | 92098 | 0.123 | 0.110 | 1.230 | **yes** | +0.17 |
| 10 | tod_min:high+age_min:high | 92098 | 0.123 | 0.110 | 1.230 | **yes** | +0.17 |
| 11 | mom_10:high+mom_5:high | 113064 | 0.151 | 0.099 | 1.105 | no | +2.61 |
| 12 | opp_mom3:low+mom_3:high | 117167 | 0.156 | 0.095 | 1.060 | no | +1.29 |
| 13 | age_min:high+mins_since_high:high | 115374 | 0.154 | 0.095 | 1.063 | no | +0.03 |
| 14 | mom_1:high+mom_3:high | 101091 | 0.135 | 0.101 | 1.134 | no | +1.60 |
| 15 | mins_to_1515:low+lower_highs_4:low | 74541 | 0.099 | 0.117 | 1.317 | no | +0.45 |
| 16 | tod_min:high+lower_highs_4:low | 74541 | 0.099 | 0.117 | 1.317 | no | +0.45 |
| 17 | mins_to_1515:low+tod_min:high+lower_highs_4:low | 74541 | 0.099 | 0.117 | 1.317 | no | +0.45 |
| 18 | mom_1:high+mom_5:high | 92162 | 0.123 | 0.104 | 1.165 | no | +1.80 |
| 19 | lower_highs_4:low+ret_since_entry:high | 88780 | 0.118 | 0.104 | 1.166 | no | −0.81 |
| 20 | mom_10:high+mom_3:high | 96765 | 0.129 | 0.100 | 1.116 | no | +2.08 |

Combo 1 CE/PE/trend/chop fire rates sit in 0.249–0.253. Hist `normal` is empty (last3d is expiry-week only).

---

## 4. Time-to-first-edge grid

Best hist proxy (1-lot): exit if not up **0.35 pts by minute 2** (`proxy_net_1lot` +₹24,723). Same N=2, X≈0.35–0.70 fills the next three slots. This is still a “get out if it doesn’t pop” rule, not a peak rule.

By TOD (hist):

| bucket | n | best N | best X | proxy 1-lot |
|---|---:|---:|---:|---:|
| open before 11:00 | 820 | 2 | 1.10 | +1,02,744 |
| mid 11:00–14:00 | 2175 | 2 | 0.35 | −36,793 |
| late after 14:00 | 551 | 10 | 0.20 | +30,584 |
| expiry-week (all last3d) | 3546 | 2 | 0.35 | +24,723 |
| normal (non-expiry week) | 0 | — | — | DATA_INSUFFICIENT |

---

## 5. Walk-forward (12 expanding expiry-week folds)

Train starts at 29 weeks / 690 tickets. Each test window is 10 weeks (~240 tickets; last two 232 and 224). Per fold: remine time grid + top pairs on **train only**, calibrate `peak_tree` thresh on train scores, replay test on 1-lot.

Folds where the rule’s 1-lot net beat hold:

| rule | folds vs hold |
|---|---|
| atr_opt_1.2 | **10/12** |
| peak_tree_p10 | **9/12** |
| pat_1_pair / pat_2_pair / pat_3_pair | **9/12** |
| other_side | 8/12 |
| pat_4_pair | 8/12 |
| pat_0_pair / divergence / theta_vs_move | 7/12 |
| clock_profit_30 | 6/12 |
| time_edge_* (N/X refit each fold) | 6/7 + 3/4 + 1/1 (name changes with the fit) |
| v2_default | 0/12 (equals hold on these 1-lot hist tickets) |

Peak-tree **minute** fire rate on each test fold (p5 / p10 / p20): 20%/20%/31%, 39/39/39, 37/37/37, 21/21/21, 6.5/39/39, 22/22/22, 42/42/42, 35/35/35, 1.1/12/69, 6.8/35/35, 35/35/35, 34/34/34. They fire. Discrete CART leaves make p5 and p10 the same thresh on most folds.

No fold-fit rule plus holdout CI clears the pass bar.

---

## 6. Live holdout — three entry sets (rank on 1-lot)

Oracle (hindsight best exit after half-spread, not a signal):

| set | n | oracle as-traded | oracle 1-lot |
|---|---:|---:|---:|
| random | 278 | +5,97,499.50 | +5,97,499.50 |
| v2_boss | 60 | +3,33,638.50 | +1,66,819.25 |
| legacy | 81 | +40,31,421.88 | +1,61,256.88 |

### Random (278 tickets, 1 lot already)

| plan | net_1lot | avg pts | vs hold | DSR | CI_lo | note |
|---|---:|---:|---:|---:|---:|---|
| peak_hazard_p10 | **+58,243** | +4.34 | +1,40,808 | 0.043 | −16,545 | least-bad; capture 0.097 |
| peak_hazard_p5 | +36,461 | +3.13 | +1,19,026 | 0.008 | −54,900 | |
| peak_logit_p5 | +36,039 | +3.10 | +1,18,605 | 0.008 | −51,255 | |
| pat_7_pair | +17,718 | +2.09 | +1,00,284 | 0.027 | −11,430 | |
| clock_profit_45 | +10,063 | +1.66 | +92,629 | 0.002 | −70,103 | |
| pat_2_trail | +3,945 | +1.32 | +86,511 | 0.002 | −22,892 | trail ≠ pair (405 exits) |
| time_edge_2_0.35 | −13,292 | +0.36 | +69,274 | ~0 | −43,679 | |
| clock_profit_30 | −50,624 | −1.72 | +31,941 | ~0 | −1,28,744 | |
| hold_to_1515 | **−82,565** | −3.50 | 0 | ~0 | −1,58,817 | |
| v2_default | −82,565 | −3.50 | 0 | ~0 | −1,58,817 | equals hold on 1-lot random |
| ladder_2step | −82,565 | −3.50 | 0 | ~0 | −1,58,817 | 1-lot cannot partial |
| clock_profit_5 | −1,01,253 | −4.54 | −18,688 | ~0 | −1,74,840 | |

Hold slices (random, 1-lot): CE −₹1,00,806 (170); PE **+₹18,240** (107); trend −₹75,191 (209); chop −₹7,375 (68); expiry-day −₹27,547 (36); normal −₹55,018 (241).

### V2 boss (60 tickets, mostly 2 lots — ranked per lot)

Hold 1-lot **+₹1,738** (as-traded +₹3,476). Best 1-lot: `peak_logit_p5` +₹49,499 (vs hold +₹47,761, DSR 0.091, CI_lo −₹8,892). `peak_hazard_p10` +₹46,025 (DSR 0.136, CI_lo −₹1,316). Clock-profit 45 +₹31,902. Nothing with CI_lo > 0.

### Legacy fills (81 tickets, mixed lots — ranked per lot)

Hold 1-lot **−₹50,559** (as-traded **−₹12,63,981** — this is the mixed-lot book the spot-check saw). Best 1-lot: `peak_hazard_p10` +₹16,570 (vs hold +₹67,130, DSR 0.008, CI_lo −₹22,607). `time_edge_2_0.35` −₹9,393 (vs hold +₹41,167) with **28/32 CANCEL_AGAINST** same-moment fires.

### As-traded (do not rank, do not mix sets)

| set | hold as-traded | v2_default as-traded |
|---|---:|---:|
| random | −82,565.42 | −82,565.42 |
| v2_boss | +3,476.39 | +3,476.39 |
| legacy | −12,63,981.38 | −12,26,921.24 |

---

## 7. Clock-profit (“exit T min before 15:15 if in profit”)

| T | random 1-lot | v2 1-lot | legacy 1-lot | vs hold (random) |
|---:|---:|---:|---:|---:|
| 5 | −1,01,253 | −3,397 | −55,438 | worse than hold |
| 15 | −81,910 | +3,804 | −46,132 | ~flat |
| 30 | −50,624 | +11,521 | −38,214 | +31,941 |
| **45** | **+10,063** | **+31,902** | **−17,249** | +92,629 |
| 60 | −36,381 | +13,766 | −22,491 | +46,184 |

T=45 is the only clock-profit that is green on random and v2. CI crosses zero on every set. This is theta / late-day mean-reversion of premium, not a path shape. On last3d (all expiry-week) that is the expected bias.

---

## 8. Peak models (item 14, actually done)

Thresh = percentile of **train/hist scores** at 100−X, X ∈ {5,10,20}. OOS = last 20% of expiry weeks (148,409 minutes).

| model | OOS AUC | p5 fire | p10 fire | p20 fire | score p50 / p90 |
|---|---:|---:|---:|---:|---|
| tree | 0.503 (WF 0.528) | 17.6% | 17.6% | 100% | 0.197 / 0.213 |
| logit | **0.549** | 7.6% | 12.0% | 20.8% | 0.207 / 0.225 |
| boost | 0.503 | 19.3% | 19.3% | 19.3% | 0.236 / 0.241 |
| hazard (5-min label) | 0.546 | 7.6% | 11.3% | 18.9% | — |

Logit calibration (10 equal-n bins): mean_pred 0.175→0.238 vs mean_label 0.060→0.109 — slope is in the right direction, intercept is high (model is over-confident). Tree/boost are almost flat (two leaves). `peak_tree_p10/p20` and all `peak_boost_*` were **dropped as identical** to `peak_tree_p5` on the live holdout (same discrete scores). They still **fired**; they did not add a new exit set.

CART on hist: `delta_proxy<=-2.667 → p=0.213 n=15939` else `p=0.197 n=64061`. That is a 1.6 pp gap, not a peak detector.

---

## 9. No-ops: fixed or dropped

| plan | action | evidence |
|---|---|---|
| pat_*_partial | dropped before run | 1-lot cannot PARTIAL (`remaining_qty >= 2*lot_size`) |
| clock_open_0915_0930 | dropped before run | entries start after 09:50; window never fires |
| pat_0/1/2_trail | **fixed** (ARM then HARD_STOP) | 412 / 202 / 405 live exits ≠ pair |
| pat_9_pair | dropped after run | identical to `pat_8_pair` on live |
| peak_tree_p10/p20, peak_boost_* | dropped after run | identical to `peak_tree_p5` on live |
| ladder_2step | kept for as-traded ≥2-lot; no-op on random 1-lot | equals hold on random |

`test_r3b_fixes.py::test_trail_does_not_exit_on_pattern` : pair returns `PATTERN`, trail arms `trail_stop` and returns `""`.

---

## 10. The other side / 11. Theta vs move / 12. Clock windows / 13. Shapes / 15. ATR + ladder

- `other_side`: 8/12 WF vs hold; live random still a loss vs the peak/hazard ranks; 10/32 CANCEL_AGAINST overlap, 33% of 1-lot gain from those moments.
- `theta_vs_move`: 7/12 WF; 0 legacy overlaps (near-expiry decay vs spread). Not enough to pass CI.
- Clock windows `mid_1130` / `eu_1330` / `expiry_1430_1515` / `freeze_1515_1528`: freeze equals hold on random (square-off already 15:15). Live GOOD_EXIT share: other 58%, expiry 14:30–15:15 20%, freeze 14%, eu 4.9%, mid 3.4%.
- Shapes: k=5 on 3,546 hist tickets; 4/5 clusters prefer EXIT_NOW on a 8-minute proxy. Early recognise min3 0.495 / min5 0.647. `shape_exit` overlap share 80% with legacy bail-outs — not a new idea.
- `atr_opt_1.2`: **10/12** WF vs hold, 23/32 CANCEL_AGAINST, **55%** of 1-lot gain from the 180s overlap. Desk stop with a new name.
- Ladder: no-op on 1-lot; not ranked.

---

## 16. Legacy overlap + share of gain

32 `CANCEL_AGAINST`, 22 `COVER_LONG_UNWIND`. Share = (rule − hold) on the 180s overlap / total (rule − hold), 1-lot.

| plan | CA same-moment | n overlap 180s | share of 1-lot gain from overlap |
|---|---:|---:|---:|
| time_edge_2_0.35 | **28/32** | 56 | **0.783** |
| shape_exit | 12/32 | 38 | 0.804 |
| atr_opt_1.2 | 23/32 | 49 | 0.555 |
| peak_tree_* / boost_* | 20/32 | 33 | 0.483 |
| pat_0_pair | 4/32 | 7 | 0.202 |
| peak_hazard_p10 | 7/32 | 12 | 0.093 |
| clock_profit_45 | 1/32 | 3 | 0.034 |
| hold_to_1515 | 0/32 | 0 | — |

`time_edge` is still the desk’s fast bail-out. Clock-profit and hazard take almost none of their (still non-passing) lift from those stamps.

---

## 17. Simplicity and DSR N

Every sweep cell is in `n_variants_tested=654` (time grid, TOD grid, per-fold remine, peak X×kind, clock-profit T, patterns). DSR uses that N. Max 4 params per `PlanSpec`. No sklearn / numpy / LightGBM.

---

## Spread stress (V2 half-spread ×1 and ×2)

| book | n | base as-traded | ×2 as-traded | base 1-lot | ×2 1-lot |
|---|---:|---:|---:|---:|---:|
| live (mixed lots) | 80 | −3,26,803 | −3,46,220 | −37,058 | −38,187 |
| hist (1-lot) | 80 | −18,816 | −19,685 | −18,816 | −19,685 |

×2 is worse than base on both books. Hist moves without a tape book because `SlippageModel` uses the V2 moneyness table.

---

## 30 worst 1-lot trades (best random rule `peak_hazard_p10`)

Worst tickets are 2026-09-22 CE random entries, −109 to −81 pts, exit `PEAK_MODEL` — the model sold a dump, not a peak. Full 30 + first-40 candles: `/tmp/exitlab-r3b/worst30.json`.

---

## Look-ahead + label permutation

- **5,000** random minutes (4,475 hist + 525 live): `features_before(i)` vs `shift_minutes` tail, **0 mismatches**.
- Labels after the cut change **196 / 200**.
- Within-day GOOD_EXIT shuffle + remine: top combo lift **1.212 → 1.023**. The remine #1 is still `mins_to_1515:low+tod_min:high` and is tagged **`clock: true`**. Other remine pairs sit at lift 1.02–1.05. Clock is named; path features collapse.

---

## Mandatory self-audit

| Point | Result | Evidence |
|---|---|---|
| No feature uses data at or after the minute it predicts | **PASS** | `features_before` takes `minutes[:i]`. 5,000/5,000 feature vectors unchanged after rotating the tail (`lookahead_test.json` `mismatches=0`, `n_hist=4475`, `n_live=525`). Unit: `test_r3_features.py::test_features_ignore_future_shuffle`. |
| Shuffled / permuted labels collapse the signal | **PASS (with named clock)** | Within-day label permutation remine: top lift 1.212 → 1.023. Remine #1 is a pure clock pair (`clock: true`, feats `tod_min` / `mins_to_1515`). Non-clock remine lifts ≤ 1.05. |
| Labels are never features | **PASS** | `test_r3_features.py::test_label_keys_are_not_features`. |
| Marks stay on the entry strike; missing = hole | **PASS** | `live_minutes` → `strike_ltp(..., strike=entry.strike)`. `test_r3_fills.py::test_live_minutes_missing_strike_is_hole`. |
| Fills pay the spread; spread_x2 moves | **PASS** | Unit 100 → buy 100.20 / sell 99.80; ×2 sell 99.60. Hist 80 tickets 1-lot −18,816 → −19,685. Live 80 as-traded −3,26,803 → −3,46,220. |
| 1-lot rank; as-traded kept | **PASS** | `pack_trades` + `test_r3b_fixes.py::test_pack_trades_ranks_on_one_lot`. Legacy as-traded hold −₹12.64L vs 1-lot −₹50.6k. Rank tables are `ranked_1lot_by_set`. |
| Random / v2 / legacy separate | **PASS** | `n_live_by_set` 278/60/81. `holdout.json` keyed by set. |
| ≥12 expiry-week folds on last3d | **PASS** | `n_folds=12`, `n_hist_weeks=149`, `hist_meta.source=last3d`. `test_r3b_fixes.py::test_expiry_folds_at_least_12`. |
| Peak models fire; AUC + calibration reported | **PASS** | Fire rates above; `peak_models.json`. They are weak (AUC ≈ 0.55), not silent. |
| Trail changes ≥1 exit; no-ops dropped | **PASS** | 412/202/405. `dropped_noops.json`. Unit `test_trail_does_not_exit_on_pattern`. |
| Params on train; N in DSR | **PASS** | Per-fold remine + peak thresh on train scores. `n_variants_tested=654` in every `summarize`. |
| Results split CE/PE, trend/chop, expiry | **PASS** | `pack_trades` slices in `holdout.json` / `walk_forward.json` / combo slices. Hist `normal` is DATA_INSUFFICIENT (last3d is expiry-week only) — stated. |
| Report states when nothing works | **PASS** | **0 rules pass. Do not enable anything.** |

Unit tests this turn: `pytest packages/exitlab/tests` **52 passed** (7 new in `test_r3b_fixes.py`). `ruff` + `mypy --strict` on the r3 modules: clean.

Playbook: `config/v2/exits/exitlab_playbook.yaml` line 9 `enabled: false`. `config/v2/exits/defaults.yaml` not touched.

---

## Handoff block (section 106)

### Accepted

- Round-2 contract: fixed-strike marks, holes, half-spread fills, DSR in [0, 1].
- All nine 3b fixes, rerun on last3d + live holdout.
- Live tapes remain the last holdout; hist expanding WF by expiry week.

### Rejected

- Promote. Enable playbook. Edit live V2 defaults.
- Treat clock lift 1.21, clock-profit T=45, or peak_hazard_p10 as an edge (CI crosses 0; DSR ≪ 0.9).
- Keep `time_edge` / `atr_opt_1.2` / `shape_exit` (legacy CANCEL_AGAINST clones; 55–80% of 1-lot gain from the overlap).

### Unknown / Data Insufficient

- Hist `normal` (non-expiry-week) slice: last3d is last-3-days-before-expiry only.
- 4 of 154 attached expiries produced no WF week (150 scanned, 149 weeks with tickets).
- V2 bid/ask size imbalance and quote staleness on dual-tape days (no book).
- sklearn HistGradientBoosting / LightGBM (not in the env; hand CART/boost used).
- Live-at-entry regime classifier (day’s first 30 minutes, labelled after the open).

### Gap addressed

- Founder 3b spot-check: mixed lots, missing random set, 6 expiry weeks, peak models never fired, trail no-ops, n=40 look-ahead.

### Evidence

- Command output: `passing=[]`, `lookahead_pass=true`, `lookahead_n=5000`, `n_folds=12`, `n_hist_entries=3546`.
- `/tmp/exitlab-r3b/tables.json` and `/opt/cursor/artifacts/exitlab-r3b/`.
- `pytest packages/exitlab/tests` 52 passed.

### Known risks

- Peak models fire but do not rank peaks (AUC 0.50–0.55). A green random-set point estimate is still a failed CI.
- Last3d is expiry-week only; a clock / theta story is over-represented versus a normal week.
- Discrete CART scores collapse several peak_* plans into one live exit set.

### Next steps

- Keep the playbook off.
- Do not ship `time_edge_*` or `atr_opt_*`.
- If there is a fourth round, drop clock-only rules and require a path feature that still lifts after a **label** permutation, with CI_lo > 0 on the random 1-lot set.

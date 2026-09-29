# Exit Lab round 3 — pattern mining (paper / replay only)

**Status:** HYPOTHESIS / PAPER / **NO_PROMOTE**. **0 rules pass.** Playbook stays `enabled: false`.

## Reproduce (this file's only command)

```bash
python -m exitlab round3 --data .local_data --out /tmp/exitlab-r3 --seed 7 --reuse-entries /tmp/exitlab-fix/entries.json
```

Seed 7. Raw JSON: `/tmp/exitlab-r3/tables.json` plus `univariate.json`, `combos.json`, `walk_forward.json`, `holdout.json`, `oracle.json`, `worst30.json`, `legacy_overlap.json`, `lookahead_test.json`, `time_tod.json`. Copy: `/opt/cursor/artifacts/exitlab-r3/`. CLI print: `n_variants_tested=605`, `n_hist_entries=226`, `n_live_entries=419`, `n_folds=10`, `passing=[]`, `lookahead_pass=true`.

Round-2 fixes stay on: marks use `strike_ltp` on the entry strike; missing strike is a hole; fills are LTP ± half-spread; DSR is Φ((SR−SR*)/se) in [0, 1]. V2 defaults and `config/v2/exits/exitlab_playbook.yaml` were not edited.

**Do not compare rupee totals across entry sets.** Legacy 25 lots, V2-boss 2 lots, random / hist 1 lot.

## Now / Why / Next

- **Now:** Nothing passes. The bar was “positive vs `hold_to_1515` in most walk-forward folds **and** holdout CI_lo > 0 **and** DSR ≥ 0.9”. `passing` is `[]`. Oracle best-exit on the same 419 live tickets is **+₹49,62,559.88**. Every tested rule is still a large loss. The least-bad holdout net is `pat_0_trail` at **−₹93,172.37** (capture −0.019). `hold_to_1515` is **−₹13,43,070.41**.
- **Why:** A minute is a GOOD_EXIT only 8.77% of the time. The strongest mined “pattern” is the clock (`mins_to_1515` low / `tod_min` high, lift 1.31) — late-day local peaks, not a path shape. Peak models never fire. Fast time-stops and late-day clocks cut the hold loss but the bootstrap CI still crosses or sits below zero after 605 variants, and the 1-minute time-stop repeats 30/32 legacy `CANCEL_AGAINST` exits.
- **Next:** Founder does not promote. Do not enable the playbook. Do not put any of these rules on the live engine.

## 0. What was actually studied

| Set | Entries | Minute-rows (held 1m bars) | Sessions |
|---|---:|---:|---:|
| hf_opt1m hist (6 tickets / day, all week files) | 226 | 33,160 | 38 |
| Live tapes (legacy + v2_boss + random, reused) | 419 | 64,462 | 12 dual-tape days |
| Walk-forward folds | 10 expanding | — | 38 hist days; fold size 3 |

The brief asked for ≥12 hist folds. With 38 sessions, expanding train from day 8 and a 3-day test window yields **10 folds, not 12**. That is `DATA_INSUFFICIENT` for a 12-fold grid, not a skip. Live tapes stay the final holdout.

Labels use hindsight only. Features use `minutes[:i]` only. Replay charges the half-spread fill (`SlippageModel`, moneyness table ATM 0.20 / ITM100 0.35 / ITM200 0.55).

---

## 1. Labels

`GOOD_EXIT` = local peak, prominence ≥ 1.5 × half-spread, no higher print later in the 5 / 15 / 30 / EOD window (`r3_core.label_window`). Holes stay `HOLD`.

On hist 15-minute labels: **base GOOD rate = 0.0877** (2,910 / 33,160 minutes). That is the target. Features never include `label_*` / `GOOD_EXIT` / `HOLD` (`test_r3_features.py`).

---

## 2. Features (known before the candle)

Option: return since entry, peak-to-now DD, mom 1/3/5/10, body/wick, range expansion, minutes since last high, volume / OI change. Index: 1/5/15 move, VWAP and day high/low distance, first-hour break, round 100/50. Greeks proxies: moneyness, minutes to 15:15, expiry flag, IV change when present. Book: spread on the path (V2 bid/ask size is `DATA_INSUFFICIENT` on dual-tape). TOD + first-30-minute trend/chop of the **day** (not of the hold). Opposite-strike 3-minute momentum. Delta proxy = option mom_1 / index mom_1.

Day index for VWAP / first-hour is the session series truncated to `available_ts < now`, not the first 30 minutes after entry.

---

## 3. What differs: univariate + top 20 combinations

Base GOOD rate 0.0877. Lift = P(GOOD | tail) / base.

### Univariate (hist, label_15; top 12)

| feat | n | q25 | q75 | P(GOOD\|high) | P(GOOD\|low) | best | lift |
|---|---:|---:|---:|---:|---:|---|---:|
| mins_to_1515 | 33160 | 31 | 157 | 0.077 | 0.115 | low | 1.309 |
| tod_min | 33160 | 758 | 884 | 0.115 | 0.077 | high | 1.309 |
| mom_10 | 30913 | −7.65 | 6.80 | 0.100 | 0.073 | high | 1.135 |
| age_min | 33160 | 46 | 172 | 0.099 | 0.079 | high | 1.125 |
| peak_dd | 33160 | −0.178 | −0.030 | 0.098 | 0.091 | high | 1.112 |
| mom_3 | 32482 | −3.95 | 3.80 | 0.097 | 0.078 | high | 1.110 |
| oi_chg | 14625 | −33 | 31 | 0.084 | 0.096 | low | 1.097 |
| opp_mom3 | 32070 | −2.35 | 2.20 | 0.077 | 0.096 | low | 1.092 |
| mom_5 | 32030 | −5.25 | 4.80 | 0.095 | 0.081 | high | 1.085 |
| peak_dd_pts | 33160 | −42.8 | −8.05 | 0.095 | 0.087 | high | 1.079 |
| ret_since_entry | 33160 | −0.098 | 0.084 | 0.090 | 0.094 | low | 1.075 |
| dist_vwap | 33160 | −39.5 | 34.2 | 0.091 | 0.094 | low | 1.075 |

Late session and a 10-minute up-print are the only lifts above 1.13. Regime / CE flags did not outrank the clock.

### Top 20 two- and three-feature combinations

From `/tmp/exitlab-r3/combos.json`. Fire rate = n / 33,160. `pts vs hold` is the first-fire premium minus the last mark (hist proxy, not a fill).

| # | feats | n | fire | hit | lift | pts vs hold |
|---:|---|---:|---:|---:|---:|---:|
| 1 | mins_to_1515:low + tod_min:high | 8309 | 0.251 | 0.115 | 1.309 | +2.46 |
| 2 | peak_dd:high + peak_dd_pts:high | 7533 | 0.227 | 0.098 | 1.114 | +3.31 |
| 3 | mom_3:high + opp_mom3:low | 5688 | 0.172 | 0.096 | 1.096 | +2.85 |
| 4 | mins_to_1515:low + age_min:high | 3854 | 0.116 | 0.117 | 1.331 | +2.06 |
| 5 | tod_min:high + age_min:high | 3854 | 0.116 | 0.117 | 1.331 | +2.06 |
| 6 | mins_to_1515:low + tod_min:high + age_min:high | 3854 | 0.116 | 0.117 | 1.331 | +2.06 |
| 7 | mom_3:high + mom_5:high | 5292 | 0.160 | 0.099 | 1.127 | +2.00 |
| 8 | mom_10:high + mom_5:high | 4795 | 0.145 | 0.104 | 1.182 | +2.90 |
| 9 | mins_to_1515:low + dist_vwap:low | 2766 | 0.083 | 0.126 | 1.434 | +2.98 |
| 10 | tod_min:high + dist_vwap:low | 2766 | 0.083 | 0.126 | 1.434 | +2.98 |
| 11 | opp_mom3:low + mom_5:high | 4456 | 0.134 | 0.097 | 1.110 | +3.46 |
| 12 | mom_10:high + peak_dd:high | 3868 | 0.117 | 0.103 | 1.179 | +4.70 |
| 13 | mins_to_1515:low + ret_since_entry:low | 2803 | 0.085 | 0.121 | 1.383 | +0.66 |
| 14 | tod_min:high + ret_since_entry:low | 2803 | 0.085 | 0.121 | 1.383 | +0.66 |
| 15 | mom_10:high + mom_3:high | 4021 | 0.121 | 0.100 | 1.142 | +2.72 |
| 16 | mom_10:high + peak_dd_pts:high | 3780 | 0.114 | 0.102 | 1.158 | +4.21 |
| 17 | peak_dd:high + mom_5:high | 3628 | 0.109 | 0.102 | 1.166 | +3.08 |
| 18 | mom_10:high + opp_mom3:low | 3432 | 0.103 | 0.103 | 1.179 | +4.26 |
| 19 | mom_5:high + peak_dd_pts:high | 3547 | 0.107 | 0.102 | 1.157 | +2.89 |
| 20 | peak_dd:high + mom_3:high | 3466 | 0.105 | 0.102 | 1.164 | +3.00 |

CE vs PE hit rates stay within ~2 points on every combo (`combos.json` `slices`). Expiry fire-rate is higher on the clock pairs. Chop days fire the late-day clock more than trend days. None of the hit rates clear 13%. Highest lift (1.43) is late-session + below VWAP on only 8.3% of minutes.

### Shallow tree (depth ≤ 3) and logit

Tree splits almost only on `delta_proxy` then `idx_15`. Leaf GOOD rates 0.046–0.125 versus base 0.088. That is noise-sized.

Logit bias −2.05 (matches the 8.8% base). Largest weights: `mom_3` +0.015, `mom_5` +0.010, `mom_1` +0.010. No coefficient is large enough to push P(GOOD) to the 0.35 fire threshold used on holdout — peak models therefore equal `hold_to_1515`.

---

## 4. Rules built from the top 10 patterns

| plan_id | meaning (≤4 params) |
|---|---|
| pat_0_pair / _partial / _trail | late clock (mins_to_1515 low ∧ tod high); trail gives 2 pts after +2 |
| pat_1_* | same clock + age high |
| pat_2_* | mom_10 high ∧ mom_5 high |
| pat_3 / pat_4 | clock ∧ age (fold-stable twins of pat_1) |
| pat_5_triple | clock triple |
| pat_6 | mom_5 ∧ mom_3 |
| pat_7 | late + below VWAP |
| pat_8 / pat_9 | late + losing since entry |

Plus the desk extras in §7–15. Every sweep cell is a DSR trial (605 unique IDs).

---

## 5. Honest test: walk-forward + live holdout

Folds are expanding: train sessions[:t], test the next 3 days, never reverse. Pattern thresholds and the time-stop (N, X) are refit on **that fold's train only**. Live holdout uses the fit on all hist (hist ends 2026-08; live is 2026-09).

### Live holdout (same 418 closed / 419 tickets; 1 skip)

| plan | n | WR | net ₹ | vs hold | vs V2 | CI lo | CI hi | DSR | max DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hold_to_1515 | 418 | 0.433 | −1,343,070 | — | — | −2,637,032 | −124,064 | 0.000 | −1,521,193 |
| v2_default | 418 | 0.397 | −1,306,010 | — | — | −2,048,103 | −586,417 | 0.000 | −1,478,294 |
| pat_0_pair | 418 | 0.464 | −931,999 | +411,072 | +374,012 | −2,134,526 | +281,134 | 0.000 | −1,252,735 |
| pat_0_partial | 418 | 0.462 | −938,559 | +404,512 | +367,452 | −2,156,159 | +259,193 | 0.000 | −1,252,884 |
| pat_0_trail | 418 | 0.541 | −93,172 | +1,249,898 | +1,212,838 | −725,906 | +492,475 | 0.000 | −502,221 |
| pat_1_pair | 418 | 0.285 | −165,975 | +1,177,095 | +1,140,035 | −320,856 | −9,167 | 0.000 | −208,540 |
| pat_1_partial | 418 | 0.285 | −97,044 | +1,246,026 | +1,208,966 | −311,104 | +111,966 | 0.000 | −146,593 |
| pat_1_trail | 418 | 0.285 | −165,975 | +1,177,095 | +1,140,035 | −320,856 | −9,167 | 0.000 | −208,540 |
| pat_2_pair | 418 | 0.483 | −528,164 | +814,907 | +777,847 | −1,382,964 | +278,341 | 0.000 | −742,703 |
| pat_2_partial | 418 | 0.474 | −553,902 | +789,168 | +752,108 | −1,399,537 | +236,952 | 0.000 | −763,569 |
| pat_2_trail | 418 | 0.490 | −460,707 | +882,364 | +845,304 | −1,061,984 | +4,641 | 0.000 | −553,856 |
| pat_3_pair | 418 | 0.433 | −1,240,198 | +102,873 | +65,813 | −2,495,631 | +221 | 0.000 | −1,461,448 |
| pat_4_pair | 418 | 0.433 | −1,240,198 | +102,873 | +65,813 | −2,495,631 | +221 | 0.000 | −1,461,448 |
| pat_5_triple | 418 | 0.433 | −1,240,198 | +102,873 | +65,813 | −2,495,631 | +221 | 0.000 | −1,461,448 |
| pat_6_pair | 418 | 0.529 | −329,951 | +1,013,120 | +976,059 | −852,558 | +213,165 | 0.000 | −518,804 |
| pat_7_pair | 418 | 0.560 | −386,428 | +956,643 | +919,583 | −953,417 | +250,706 | 0.000 | −535,486 |
| pat_8_pair | 418 | 0.438 | −1,258,960 | +84,111 | +47,051 | −2,596,694 | −21,807 | 0.000 | −1,448,843 |
| pat_9_pair | 418 | 0.438 | −1,258,960 | +84,111 | +47,051 | −2,596,694 | −21,807 | 0.000 | −1,448,843 |
| time_edge_1_0.35 | 418 | 0.048 | −336,409 | +1,006,662 | +969,602 | −551,255 | −132,321 | 0.000 | −412,280 |
| divergence | 418 | 0.589 | −1,291,245 | +51,825 | +14,765 | −2,598,253 | −71,667 | 0.000 | −1,510,427 |
| other_side | 418 | 0.340 | −323,596 | +1,019,474 | +982,414 | −726,382 | +90,339 | 0.000 | −470,154 |
| theta_vs_move | 418 | 0.447 | −1,202,778 | +140,293 | +103,232 | −2,511,400 | −4,012 | 0.000 | −1,429,751 |
| atr_opt_1.2 | 418 | 0.120 | −500,988 | +842,083 | +805,023 | −781,716 | −214,774 | 0.000 | −558,878 |
| ladder_2step | 418 | 0.440 | −1,184,096 | +158,974 | +121,914 | −2,500,682 | +17,273 | 0.000 | −1,369,538 |
| shape_exit | 418 | 0.404 | −143,240 | +1,199,831 | +1,162,770 | −437,217 | +132,709 | 0.000 | −243,058 |
| peak_tree / logit / boost / hazard | 418 | 0.433 | −1,343,070 | 0 | −37,060 | −2,637,032 | −124,064 | 0.000 | −1,521,193 |
| clock_open_0915_0930 | 418 | 0.433 | −1,343,070 | 0 | −37,060 | −2,637,032 | −124,064 | 0.000 | −1,521,193 |
| clock_mid_1130 | 418 | 0.368 | −1,443,173 | −100,102 | −137,162 | −2,170,256 | −647,890 | 0.000 | −1,451,567 |
| clock_eu_1330 | 418 | 0.361 | −869,800 | +473,271 | +436,210 | −1,864,276 | −110,754 | 0.000 | −878,541 |
| clock_expiry_1430_1515 | 418 | 0.438 | −1,297,885 | +45,186 | +8,125 | −2,575,511 | −89,069 | 0.000 | −1,477,216 |
| clock_freeze_1515_1528 | 418 | 0.433 | −1,343,070 | 0 | −37,060 | −2,637,032 | −124,064 | 0.000 | −1,521,193 |

No holdout CI_lo is above zero. Max DSR on this holdout is 0.0003 (`pat_0_trail`). Peak models and the 09:15–09:30 / freeze clocks never fire (entries start after 09:50).

### Walk-forward vs_hold by fold (₹)

| rule family | f0 | f1 | f2 | f3 | f4 | f5 | f6 | f7 | f8 | f9 | #+ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| hold_to_1515 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| v2_default | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | — |
| time_edge (refit) | +1943 | +8742 | +2222 | +10237 | +3445 | −1933 | +1411 | +25506 | −20715 | +3948 | 8/10 |
| pat_0 (remined) | 0 | +610 | −2040 | −1048 | 0 | +5978 | −3828 | +14237 | −3993 | +5031 | 5/10 |
| pat_1 (remined) | −1265 | −1032 | +1268 | −7208 | +2151 | +5196 | +1823 | +11820 | −5226 | +6864 | 6/10 |
| divergence | −1544 | +11240 | −5943 | +22145 | −10763 | −256 | +12041 | +28467 | −17964 | +12047 | 5/10 |
| other_side | +3451 | +14999 | +2738 | +18399 | −2563 | −120 | +2790 | +23893 | −25259 | +8041 | 7/10 |
| theta_vs_move | 0 | −1236 | +5832 | 0 | −934 | 0 | −1479 | +6500 | 0 | +1252 | 3/10 |
| atr_opt_1.2 | −496 | +9209 | +10682 | +7075 | +3889 | −5965 | −3159 | +25428 | −13818 | +6118 | 6/10 |
| ladder_2step | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/10 |

v2_default equals hold on hist (1-lot books almost never hit the ₹30k catastrophic stop). Ladder never partials (hist lots=1). Full per-fold n / WR / CI / DSR / slices: `/tmp/exitlab-r3/walk_forward.json`.

`time_edge` and `other_side` beat hold in most folds. Both fail the holdout CI and DSR legs. `time_edge` holdout CI is entirely negative.

### Holdout slices (CE/PE, trend/chop, expiry)

| plan | CE n/net | PE n/net | trend n/net | chop n/net | expiry n/net | normal n/net |
|---|---:|---:|---:|---:|---:|---:|
| hold_to_1515 | 241 / −5.39L | 177 / −8.04L | 317 / −14.33L | 101 / +0.90L | 50 / −3.40L | 368 / −10.03L |
| v2_default | 241 / −5.93L | 177 / −7.13L | 317 / −12.01L | 101 / −1.05L | 50 / −2.94L | 368 / −10.12L |
| pat_0_trail | 241 / −1.13L | 177 / +0.20L | 317 / +1.56L | 101 / −2.49L | 50 / +0.15L | 368 / −1.08L |
| time_edge_1_0.35 | 241 / −1.77L | 177 / −1.60L | 317 / −3.04L | 101 / −0.33L | 50 / −0.34L | 368 / −3.03L |
| other_side | 241 / −2.60L | 177 / −0.64L | 317 / −3.52L | 101 / +0.28L | 50 / −2.39L | 368 / −0.84L |
| shape_exit | 241 / −2.03L | 177 / +0.60L | 317 / −0.84L | 101 / −0.60L | 50 / +0.05L | 368 / −1.48L |

Chop `hold_to_1515` is the only clearly green slice (+₹90k on 101). Trend and expiry bleed. CE is not a leftover roll-strike artifact (holes are omitted; see self-audit).

---

## 6. Thirty worst trades under the best holdout rule (`pat_0_trail`)

Best holdout net is still −₹93,172. The 30 worst closed trades:

| entry_id | session | side | net ₹ | reason | entry | exit | holes in first 40 |
|---|---|---|---:|---|---:|---:|---:|
| paper-MIX-DEFAULT-BUY-…-1790323495-PE | 2026-09-25 | PE | −137,767 | PATTERN | 216.2 | 131.8 | 0 |
| …-1790227875-CE | 2026-09-24 | CE | −127,201 | PATTERN | 252.2 | 174.4 | 0 |
| …-1790224757-CE | 2026-09-24 | CE | −125,250 | PATTERN | 251.0 | 174.4 | 0 |
| …-1789976272-PE | 2026-09-21 | PE | −74,817 | PATTERN | 210.8 | 165.2 | 0 |
| …-1790325281-CE | 2026-09-25 | CE | −65,293 | PATTERN | 306.8 | 267.3 | 0 |
| …-1789719294-PE | 2026-09-18 | PE | −53,566 | PATTERN | 209.7 | 177.2 | 0 |
| …-1790145769-CE | 2026-09-23 | CE | −50,891 | PATTERN | 273.0 | 242.3 | 0 |
| …-1790056347-CE | 2026-09-22 | CE | −14,683 | HARD_STOP | 199.5 | 190.95 | 0 |
| …-1790586820-PE | 2026-09-28 | PE | −13,816 | PATTERN | 184.85 | 176.8 | 0 |
| …-1789981552-PE | 2026-09-21 | PE | −11,664 | PATTERN | 215.7 | 209.05 | 0 |
| …-1790067051-CE | 2026-09-22 | CE | −11,513 | HARD_STOP | 197.55 | 190.95 | 0 |
| …-1789979847-CE | 2026-09-21 | CE | −11,191 | PATTERN | 219.25 | 212.9 | 0 |
| …-1790241938-CE | 2026-09-24 | CE | −10,413 | PATTERN | 291.0 | 285.3 | 0 |
| v2-2026-09-28-83 | 2026-09-28 | CE | −9,284 | PATTERN | 184.55 | 113.8 | 0 |
| …-1790154880-PE | 2026-09-23 | PE | −9,243 | PATTERN | 239.8 | 234.7 | 0 |
| v2-2026-09-25-207 | 2026-09-25 | PE | −8,442 | PATTERN | 147.65 | 83.3 | 0 |
| …-1790050670-CE | 2026-09-22 | CE | −8,247 | HARD_STOP | 212.85 | 208.3 | 0 |
| v2-2026-09-28-135 | 2026-09-28 | CE | −7,801 | PATTERN | 173.15 | 113.8 | 0 |
| v2-2026-09-24-173 | 2026-09-24 | CE | −5,450 | PATTERN | 185.6 | 144.4 | 0 |
| v2-2026-09-21-54 | 2026-09-21 | PE | −5,336 | PATTERN | 132.05 | 91.6 | 18 |
| …-1789637704-PE | 2026-09-17 | PE | −5,283 | PATTERN | 243.45 | 240.8 | 0 |
| …-1789969090-CE | 2026-09-21 | CE | −4,911 | HARD_STOP | 210.0 | 207.5 | 0 |
| rnd-2026-09-28-7-13 | 2026-09-28 | CE | −4,597 | PATTERN | 183.5 | 113.8 | 2 |
| …-1790580463-PE | 2026-09-28 | PE | −4,176 | HARD_STOP | 208.75 | 206.7 | 0 |
| rnd-2026-09-24-7-7 | 2026-09-24 | CE | −3,928 | PATTERN | 177.5 | 118.1 | 0 |
| rnd-2026-09-24-7-10 | 2026-09-24 | CE | −3,902 | PATTERN | 177.1 | 118.1 | 0 |
| …-1790232805-PE | 2026-09-24 | PE | −3,846 | HARD_STOP | 228.2 | 226.4 | 0 |
| rnd-2026-09-28-7-12 | 2026-09-28 | CE | −3,451 | PATTERN | 114.9 | 62.7 | 2 |
| …-1790156458-PE | 2026-09-23 | PE | −3,422 | PATTERN | 202.5 | 200.9 | 0 |
| rnd-2026-09-24-11-1 | 2026-09-24 | CE | −3,295 | PATTERN | 194.0 | 144.4 | 0 |

What the rule missed: the late-day clock fires **after** a 25-lot MIX ticket has already dropped 40–80 pts. The trail (2 pts after +2) never arms on these paths (`seen_high` never clears entry+2). `HARD_STOP` rows are the trail/stop leftover, not the mined pattern. `v2-2026-09-21-54` has 18 holes in the first 40 minutes — the path is gappy, not a clean peak. Full candles: `/tmp/exitlab-r3/worst30.json`.

---

## 7. Oracle bound and capture (item 7)

Hindsight best sell = max(ltp − half-spread) on the fixed strike.

| | |
|---|---:|
| live tickets with a path | 419 |
| oracle gross sum | **+₹49,62,559.88** |
| mean MFE | +34.18 pts (median +20.55), reached at minute 63 |
| mean MAE | −31.95 pts (median −24.50), reached at minute 83 |

| plan | realized net | capture (realized / oracle) |
|---|---:|---:|
| hold_to_1515 | −1,343,070 | −0.271 |
| v2_default | −1,306,010 | −0.263 |
| pat_0_trail | −93,172 | −0.019 |
| shape_exit | −143,240 | −0.029 |
| pat_1_partial | −97,044 | −0.020 |
| time_edge_1_0.35 | −336,409 | −0.068 |
| other_side | −323,596 | −0.065 |
| peak_* | −1,343,070 | −0.271 |

No rule captures a positive fraction of the oracle. MFE ≈ |MAE| and MFE arrives earlier than MAE on average — there is a peak to take, and the mined rules still leave it on the table or exit after MAE. Plot: `/tmp/exitlab-r3/mfe_mae.svg`.

---

## 8. Time stops (item 8)

Hist proxy grid N ∈ 1..10, X ∈ {0, 0.5, 1, 1.5, 2}× spread. Best on all hist: **N=1, X=0.35 pts**, proxy +₹11,417 (then it still loses −₹3.36 L on live after costs).

| slice | n | best N | best X | hist proxy |
|---|---:|---:|---:|---:|
| open before 11:00 | 49 | 4 | 0.20 | +12,937 |
| 11:00–14:00 | 135 | 1 | 0.35 | +7,546 |
| after 14:00 | 42 | 1 | 0.00 | −268 |
| expiry | 51 | 4 | 0.55 | −6,739 |
| normal | 175 | 1 | 0.35 | +39,063 |

Best N **does** move: 4 minutes near the open and on expiry, 1 minute midday and on normal days. That is a real split. It does not survive the live holdout CI.

Live `time_edge_1_0.35`: WR 4.8%, CI entirely negative, DSR ≈ 0. It is a “cut losers in 60 seconds” rule, not an edge.

---

## 9. Option vs index divergence (item 9)

Exit when the index is still our way (`index_signed` ≥ 6) and option `mom_5` ≤ 0.4. Holdout −₹12.91 L, vs hold +₹52k, CI crosses zero from below, DSR ≈ 0. WF 5/10. **Fails.**

---

## 10. The other side (item 10)

Exit when same-strike opposite `opp_mom3` ≥ 0.8. Holdout −₹3.24 L, vs hold +₹10.19 L, CI −7.26 L to +0.90 L, DSR ≈ 0. WF 7/10. Closest extra idea to “usually beats hold,” still not a pass. Repeats 10/32 `CANCEL_AGAINST` and 12/22 `COVER_LONG_UNWIND` — too close to the legacy mistakes.

---

## 11. Theta vs expected move (item 11)

Near expiry, last 90 minutes: realized 10-minute move vs crude theta + spread. Almost never fires on non-expiry. Holdout −₹12.03 L (near hold). WF 3/10. **Fails.**

---

## 12. Clock windows (item 12)

Share of live GOOD_EXIT minutes: other 74.9%, freeze 15:15–15:28 13.7%, Europe 13:30 4.9%, 11:30 3.4%, expiry 14:30–15:15 3.2%. Open 09:15–09:30 is empty (no-new-entry before 09:50).

Forced exit in the window, else hold:

| window | holdout net | vs hold |
|---|---:|---:|
| 09:15–09:30 | −1,343,070 | 0 (no fire) |
| 11:30 | −1,443,173 | −100,102 |
| 13:30 Europe | −869,800 | +473,271 (CI still < 0) |
| expiry 14:30–15:15 | −1,297,885 | +45,186 |
| freeze 15:15–15:28 | −1,343,070 | 0 |

11:30 is actively worse than hold. 13:30 cuts some bleed and still fails the CI.

---

## 13. Price-path shapes (item 13)

k-means k=5 on the first 10 normalized returns, 222 hist paths. Every cluster’s hist proxy preferred `EXIT_NOW` at minute 8 versus hold — that is “get out of a random ticket,” not a shape. Recognition by minute 3 vs the 10-minute assignment: **39.6%**. By minute 5: **41.9%**. Chance at k=5 is 20%, so there is a weak silhouette, not a usable early read.

Live `shape_exit` −₹1.43 L, CI crosses zero, DSR ≈ 0. **Fails.**

---

## 14. Peak prediction models (item 14)

No sklearn / LightGBM in this env (complexity budget). Hand CART depth 3, logistic GD, 8-round residual boost, and a 5-minute hazard logit. Purged embargo is the live-after-hist split (hist ≤ 2026-08, live Sep 2026). All four equal `hold_to_1515` on holdout — predicted P(GOOD) never reached 0.35. **Fails. Not kept.**

---

## 15. ATR stops and ladders (item 15)

`atr_opt_1.2`: holdout −₹5.01 L, CI entirely negative, WF 6/10. Repeats 23/32 `CANCEL_AGAINST`. **Fails.**

`ladder_2step` at +40% / +90% of entry: 1-lot tickets skip partials (spec). On live 2-lot / 25-lot books it still tracks hold (−₹11.84 L). WF all zeros on hist 1-lot. **Fails / DATA_INSUFFICIENT on hist partials.**

---

## 16. Legacy counter-examples (item 16)

32 `CANCEL_AGAINST` (−3.12 L on the desk) and 22 `COVER_LONG_UNWIND` (−2.18 L). A fire within 180s of the desk exit, other than flatten/catastrophic, counts as a repeat.

| plan | CANCEL_AGAINST 32 | COVER_LONG_UNWIND 22 |
|---|---:|---:|
| hold / v2 / peak_* / divergence / theta / ladder / pat_2..7 | 0 | 0 |
| time_edge_1_0.35 | **30** | **17** |
| pat_1_pair / trail | **24** | **14** |
| atr_opt_1.2 | **23** | **17** |
| pat_1_partial | 23 | 13 |
| shape_exit | 12 | 9 |
| other_side | 10 | 12 |
| pat_0_trail | 7 | 3 |
| pat_0_pair | 3 | 2 |

`time_edge`, `pat_1_*`, and `atr_opt_1.2` **repeat the legacy mistakes**. They are failures under item 16 even before the CI/DSR bar.

---

## 17. Simplicity and DSR N (item 17)

Every rule uses at most 4 tunable parameters. `n_variants_tested=605` (time grid 50 + TOD grids + per-fold time grids + remine IDs + extras + baselines). That N is what `deflated_sharpe` saw. With N=605 a holdout Sharpe would have to be extreme to print DSR ≥ 0.9. None came close.

---

## Passing list

**0 of 3.** Empty.

`time_edge` wins 8/10 folds and still has holdout CI (−5.51 L, −1.32 L) and DSR ≈ 0, and it is the legacy `CANCEL_AGAINST` clone. `pat_0_trail` has the best live net and a CI that crosses zero (DSR 0.0003). `other_side` wins 7/10 folds and still fails CI + DSR + the legacy-overlap test.

---

## Mandatory self-audit

| Point | Result | Evidence |
|---|---|---|
| No feature uses data at or after the minute it predicts | **PASS** | `features_before` takes `minutes[:i]` (`r3_core.py:243-253`). Shuffled-future: 40/40 feature vectors unchanged after rotating the tail (`/tmp/exitlab-r3/lookahead_test.json` `mismatches=0`). Unit: `test_r3_features.py::test_features_ignore_future_shuffle`. |
| Shuffled future collapses the *label* signal | **PASS on labels, FAIL on the top combo** | Labels after the cut change 40/40. Top-combo lift 1.309 → 1.320 — it does **not** collapse because that combo is the clock, which the shuffle does not move. That is the finding, not a leak. |
| Labels are never features | **PASS** | `test_r3_features.py::test_label_keys_are_not_features`. `FeatRow.feats` is only the `features_before` dict. |
| Marks stay on the entry strike; missing = hole | **PASS** | `live_minutes` calls `strike_ltp(..., strike=entry.strike)` (`r3_core.py:70`). `minutes_to_series` drops `ltp is None` (`r3_core.py:157-159`). `test_r3_fills.py::test_live_minutes_missing_strike_is_hole`. |
| Fills pay the spread; spread_x2 moves | **PASS** | `test_r3_fills.py::test_minutes_to_series_fill_pays_half_spread` (100 → buy 100.20 / sell 99.80; x2 sell 99.60). Live stress 40 tickets: base **−35,865.71**, spread_x2 **−44,945.03** (`tables.json` `spread_stress`). |
| Params chosen on train; N in DSR | **PASS** | Per-fold remine + time grid on `train_e` only (`r3_run.py` fold loop). Holdout uses hist-only fit. `n_variants_tested=605` in every `summarize(...)`. DSR is Φ((SR−SR*)/se) (`stats.py:69-92`). |
| Results split CE/PE, trend/chop, expiry | **PASS** | Holdout and WF `_pack_trades` slices in the tables above and `holdout.json` / `walk_forward.json`. Combo slices in `combos.json`. |
| Report states when nothing works | **PASS** | This file: **0 rules pass. Do not enable anything.** |

Unit tests this turn: `pytest packages/exitlab/tests` **45 passed**. `ruff` + `mypy --strict` on the r3 modules: clean.

Playbook: `config/v2/exits/exitlab_playbook.yaml` line 9 `enabled: false`. `config/v2/exits/defaults.yaml` not touched.

---

## Handoff block (section 106)

### Accepted

- Round-2 contract: fixed-strike marks, holes, half-spread fills, DSR in [0, 1].
- Study every held minute, not a fixed exit menu.
- Desk extras 7–16 each get a result row, including failures.
- Live tapes as the last holdout; hist expanding WF for fit.

### Rejected

- Promote. Enable playbook. Edit live V2 defaults.
- Treat lift 1.3 on the clock as an edge.
- Keep peak models (they never fire).
- Keep `time_edge` / `pat_1` / `atr_opt_1.2` (legacy CANCEL_AGAINST clones).

### Unknown / Data Insufficient

- 12 WF folds (38 hist sessions → 10).
- V2 bid/ask size imbalance and quote staleness on dual-tape days (no book).
- Hist ladder partials (1-lot tickets skip).
- sklearn HistGradientBoosting / LightGBM (not in the env; hand boost used).
- Live-at-entry regime classifier (day’s first 30 minutes, labelled after the open).

### Gap addressed

- Founder note on round 2: “tested a fixed menu instead of studying the data.” This round labels every held minute, mines combinations, and only then builds rules.

### Evidence

- Command output: `passing=[]`, `lookahead_pass=true`, `n_variants_tested=605`.
- `/tmp/exitlab-r3/tables.json` and the copy under `/opt/cursor/artifacts/exitlab-r3/`.
- `pytest packages/exitlab/tests` 45 passed.

### Known risks

- 25-lot MIX tickets dominate rupee tails. A 1-lot-only cut would change nets, not the pass bar.
- Top combo is the clock; shuffling prices will not deflate it.
- 10 folds, not 12.

### Next steps

- Keep the playbook off.
- Do not ship `time_edge_1_*` — it is the desk’s `CANCEL_AGAINST` with a new name.
- If there is a fourth round, drop clock-only rules and require a path feature that still lifts after a timestamp shuffle.

# Exit Lab report (paper / replay only)

**Status:** HYPOTHESIS / PAPER / NO_PROMOTE. Every number in the tables comes from

```bash
python -m exitlab research --data .local_data --out /tmp/exitlab-audit --seed 7 --max-hist-days 24 --extra-seeds 11,19 --reuse-entries /tmp/exitlab-run/entries.json
```

run on 2026-09-28. Raw JSON: `/tmp/exitlab-audit/tables.json`, `entries.json`, `trades.json`, `oos_sweep.json`, `measure_live.json`, `measure_history.json`, `partial_fill_addon.json`. Copy of tables: `/opt/cursor/artifacts/exitlab-audit-tables.json`. If a cell is missing, this file says `DATA_INSUFFICIENT`.

First-pass seed-7-only run (`/tmp/exitlab-run`, 51 variants, 4,545 trades) is superseded by this audit run (68 variants, 14,944 trades). Measure files are the same tapes.

**Owner:** `packages/exitlab` + this file. V2 defaults are unchanged. Playbook: `config/v2/exits/exitlab_playbook.yaml` (`enabled: false`).

## Now / Why / Next

- **Now:** The lab replayed 32 named exit plans (plus 36 sweep variants = 68) on 467 entries: 278 random 1-lot (seeds 7/11/19), 81 legacy 25-lot, 60 V2-boss 2-lot, 48 history 1-lot. 14,944 trade results after costs. Playbook stays off.
- **Why:** The live desk's own 81 fills lost ₹1,51,497.43 after costs. Cancels-against and cover-unwinds ate the target winners. This file measures that as a baseline; it does not copy those overlays as the answer.
- **Next:** Founder reads the OOS + stress tables. Not a promote. Do not turn the playbook on from this report alone.

**Do not compare rupee totals across entry sets.** Legacy tickets are 25 lots (VOLSIZE). V2-boss tickets are 2 lots. Random and history tickets are 1 lot.

## Data used

| Set | Path (local, gitignored) | What | Sessions / days | Notes |
|-----|--------------------------|------|-----------------|-------|
| Live dual-tape | `.local_data/tape/YYYY-MM-DD.jsonl` | Legacy recorder ticks (index + ATM/ITM + wings) | 2026-09-14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 28 | 12 files, 4,986 ticks. 19–20 weekend / off-session. |
| V2 recorder | `.local_data/tape/v2/2026-09-28/` | Depth + quote snapshots | 2026-09-28 only | `v2_spread_sample` empty (`[]`). Bid/ask spread on V2: **DATA_INSUFFICIENT**. |
| Option 1m | `.local_data/NIFTY_*.parquet` | Weekly NIFTY option 1m OHLC | Weeks 2025-10-14, 2026-04-28, 2026-05-26, 2026-06-02, 2026-07-07, 2026-08-04 | Entries matched only the first week (2025-10-06..14, 48 tickets). Later weeks: **DATA_INSUFFICIENT**. |
| Index 1m | `.local_data/index_NIFTY.parquet` | NIFTY 1m | 66,062 bars / 178 sessions labelled 177 | Regime labels + history entries. Session filter 09:15–15:30 IST. |

**Split:** sweep parameters chosen on random live tickets with `session <= 2026-09-22` (142 unique entries; seeds 7+11+19). Reported on later untouched live days `2026-09-23..28` (136 unique entries). History `<= 2026-05-31` was the intended train cut; this run produced no history tickets after 2025-10-14, so history OOS is **DATA_INSUFFICIENT**.

**Fills:** buy at ask when the book exists; else LTP/close × (1 + 0.40% stated slip). Sell at bid / (1 − 0.40%). Costs: `ledger.charges` + `config/charges.yaml` (NSE). Lot 65. Same-bar stop+target: stop wins (`SAME_BAR_STOP`). Whole-lot fills only (`int(lots * frac)`; 1-lot half-fill = REJECT).

**No look-ahead:** 1m bar known only at `available_ts` (close). Tape rows by `as_of_ist` / `available_ts`. Honest clock: `python -m exitlab prove-lookahead` → `HONEST_OK`. Injected future read: `INJECT_RAISED`. Tests: `packages/exitlab/tests/test_lookahead.py` (7 passed).

## Reproduce

From a checkout with the archives extracted to `.local_data/` (do not commit data):

```bash
python -m pip install --no-deps -e packages/exitlab packages/oms packages/contracts
# history parquet needs: pip install 'pyarrow>=14'
python -m exitlab measure --data .local_data --out /tmp/exitlab-audit
python -m exitlab research --data .local_data --out /tmp/exitlab-audit --seed 7 --max-hist-days 24 --extra-seeds 11,19
# or reuse reconstructed entries:
python -m exitlab research --data .local_data --out /tmp/exitlab-audit --seed 7 --max-hist-days 24 --extra-seeds 11,19 --reuse-entries /tmp/exitlab-run/entries.json
python -m exitlab prove-lookahead
python -m exitlab list-plans
python -m exitlab playbook --path config/v2/exits/exitlab_playbook.yaml
```

`n_variants_tested = 68` (32 library plans + 36 sweep variants). Seeds 7, 11, 19. `n_trade_results = 14944`. `n_low_confidence_cells` (any Summary with n<30) = 352.

## Market measurements

Source: `measure_live.json` + `measure_history.json` from the same run.

### Live dual-tape sessions

| Session | Weekday | Scenario | Tags | Index open → close | Range pts | ER | Freeze | Ticks | Index 1m |
|---------|---------|----------|------|--------------------|-----------|----|--------|-------|----------|
| 2026-09-14 | Monday | DATA_INSUFFICIENT | — | — | — | — | no | 473 | 0 (after-hours; no index bars in session window) |
| 2026-09-15 | Tuesday | expiry_chop | expiry, chop | 23576.15 → 23221.55 | 397.55 | 0.120 | no | 1030 | 330 |
| 2026-09-16 | Wednesday | mixed | feed_freeze, mixed | 23191.45 → 23217.60 | 87.30 | 0.390 | yes | 258 | 179 |
| 2026-09-17 | Thursday | chop | feed_freeze, chop | 23337.85 → 23270.60 | 119.50 | 0.000 | yes | 664 | 389 |
| 2026-09-18 | Friday | chop | feed_freeze, chop | 23270.60 → 23346.40 | 117.70 | 0.000 | yes | 731 | 417 |
| 2026-09-19 | Saturday | mixed | mixed | 23346.40 → 23346.40 | 0.00 | — | no | 161 | 1 (weekend; skipped for entries) |
| 2026-09-21 | Monday | trend_up | day_before_expiry, feed_freeze, trend_up | 23373.70 → 23414.30 | 93.15 | 0.717 | yes | 255 | 231 |
| 2026-09-22 | Tuesday | expiry_trend_down | expiry, feed_freeze, trend_down | 23438.70 → 23329.00 | 173.25 | 0.467 | yes | 292 | 276 |
| 2026-09-23 | Wednesday | chop | feed_freeze, chop | 23379.65 → 23431.35 | 106.70 | 0.041 | yes | 277 | 273 |
| 2026-09-24 | Thursday | chop | chop | 23260.55 → 23088.00 | 225.85 | 0.136 | no | 256 | 253 |
| 2026-09-25 | Friday | chop | feed_freeze, chop | 23116.50 → 23128.10 | 132.70 | 0.117 | yes | 311 | 308 |
| 2026-09-28 | Monday | mixed | day_before_expiry, feed_freeze, mixed | 22864.40 → 22788.25 | 107.50 | 0.228 | yes | 278 | 275 |

Freeze flag = any tick with IST hour 15 and minute ≥ 15 on that file (8 of 12 files). That is “tape still printing in the freeze window”, not a measured quote stall. ATR printed 0.0 on 16, 17, 18 — those days start late / have broken 1m ATR, so `atr_stop` is degenerate there.

**Late starts (DATA_INSUFFICIENT for the cash open):** 14 after-hours; 15 is expiry (random produced 3 tickets across seeds 7/11/19); 16 mixed with 258 ticks; several weekdays begin after 09:15.

### Time-of-day MAE (ATM CE print-to-print, live tape)

Session-hours only (IST). `mae_p50` / `mae_p80` are the median / 80th percentile of down-prints in that 30-minute bucket. Overnight / after-hours buckets (00:00–02:00, 16:00–22:30) print ~70 pt artifacts and are ignored for plan design.

| Bucket IST | n prints | MAE p50 | MAE p80 |
|------------|----------|---------|---------|
| 09:00 | 15 | 1.05 | 2.55 |
| 09:30 | 132 | 1.85 | 3.05 |
| 10:00 | 172 | 1.70 | 3.25 |
| 10:30 | 213 | 1.85 | 4.55 |
| 11:00 | 223 | 1.70 | 4.80 |
| 11:30 | 216 | 1.65 | 3.60 |
| 12:00 | 227 | 1.65 | 2.95 |
| 12:30 | 203 | 1.75 | 3.85 |
| 13:00 | 200 | 1.75 | 3.35 |
| 13:30 | 245 | 1.90 | 4.55 |
| 14:00 | 255 | 2.15 | 5.30 |
| 14:30 | 238 | 2.15 | 4.30 |
| 15:00 | 205 | 1.40 | 3.50 |
| 15:30 | 73 | 1.60 | 3.05 |

Session TOD MAE p80 sits about 2.5–5.3 pts. That is the noise band the `noise_1.6` stop is built from (stop = entry − 1.6 × bucket MAE, fallback 8 pts when the bucket is empty).

### Recovery after −8 ATM CE

On the live dual-tape ATM CE path (not a trade): 1,469 prints where the next 40 prints dropped at least 8 pts; 693 of those later printed ≥ entry+8. Rate **47.2%** (`693 / 1469`). A hard −8 stop on ATM CE is coin-flip recovery on this sample.

### History index labels (177 sessions)

| Scenario | n sessions |
|----------|----------|
| chop | 87 |
| mixed | 42 |
| expiry_mixed | 17 |
| expiry_chop | 16 |
| trend_up | 9 |
| trend_down | 5 |
| expiry_trend_up | 1 |

News / event-day tags: **DATA_INSUFFICIENT** (no news feed in the sample). VIX: not in the sample; IV used when the tape had `atm_ce_iv`. Gap-open % is on the index parquet when prior close exists; live dual-tape `gap_pct` is null.

## Scenario map (how a day is labelled)

From **that day's** index path only (known by the close; the router freezes `regime_at_entry` from the session label already assigned to the tape day — see risk below):

- `trend_up` / `trend_down` / `chop` / `mixed` from Kaufman ER + signed close-to-open.
- Prefix `expiry_` on weekly expiry Tuesday; tag `day_before_expiry` the Monday.
- `feed_freeze` if any tick sits in 15:15+.
- Weekend files are skipped for entries.

**Router risk:** `regime_at_entry` on this run is the **day label**, not a live-at-entry classifier. A plan that keys off “chop vs trend” here is using information that a live desk would only know at the close. Treat router results as an upper bound. A live router must use only bars with `available_ts <= t`.

## Entry sets

| Set | n | Lots | Side | Moneyness / notes | Sessions | How |
|-----|---|------|------|-------------------|----------|-----|
| `random` | 278 | 1 | CE 171 / PE 107 | seed 7: 146; seed 11: 66; seed 19: 66 | 15 (3), 16 (3), 17–18/21–25/28 (34 each) | Uniform in 09:50–14:45. Extra seeds 11 and 19. |
| `legacy` | 81 | 25 | CE 41 / PE 40 | ITM200 81 | 17 (3), 18 (7), 21 (13), 22 (6), 23 (14), 24 (11), 25 (18), 28 (9) | `replay_paper_scalp(..., write=False)`. 14/15/16: 0 fills |
| `v2_boss` | 60 | 2 | CE 30 / PE 30 | ITM100 60 | 17 (5), 18 (7), 21–25 + 28 (8) | BossSelector proxy: 1m direction + real holds, 30 min spacing, max 8 / session |
| `random_hist` | 48 | 1 | CE 28 / PE 20 | ATM 18, ITM100 18, ITM200 12 | 2025-10-06..09, 13, 14 (8 each) | Same random rule on 1m parquet. Later weeks: DATA_INSUFFICIENT |

Random scenario mix (278): chop 170, mixed 37, trend_up 34, expiry_trend_down 34, expiry_chop 3. Chop dominates.

Legacy cancelled entries (never filled), from `/tmp/exitlab-run/legacy_replay_meta.json`: SKIP_SUM 3450; HOLD_MAJORITY 992; NO_NEW_AFTER_1516 929; PATH_KIND_HOLD 611; SOD_ONE_OPEN 311; NO_NEW_BEFORE_0930 168; REGIME_UNKNOWN_WAIT 158; NIFTY_WAIT_STRENGTH 111; FOLLOW_GAP 103; BIN_SIDE_MISMATCH 47; SAME_TICK_REOPEN 12; BIN_LONG_UNWIND 7; ITM_ONLY_NO_QUOTE 1. Filled 81.

## Exit library (every brief category mapped)

Baselines: `hold_to_1515`, `fixed_stop_target` (25% / 40%), `v2_default` (catastrophic ₹30k + flatten 15:15), `legacy_overlay` (constants copied from `paper_scalp.py`, file not edited).

| Brief category | Plan replayed | n trades |
|---|---|---:|
| `pretrade_implied_move_straddle` | `implied_move` | 467 |
| `pretrade_atr_stop` | `atr_stop` | 467 |
| `pretrade_premium_vs_index_stop` | `index_stop` | 467 |
| `pretrade_time_budget` | `time_and_stop` | 467 |
| `pretrade_mae_budget` | `noise_band` | 467 |
| `pretrade_skip_wide_spread_iv_near_square` | `implied_move` | 467 |
| `after_hard_stop_premium` | `fixed_stop_target` | 467 |
| `after_hard_stop_index_pts` | `index_stop` | 467 |
| `after_hard_stop_atr` | `atr_stop` | 467 |
| `after_structure_swing` | `structure_stop` | 467 |
| `after_vol_adjusted_noise` | `noise_band` | 467 |
| `after_time_stop` | `time_and_stop` | 467 |
| `after_no_progress` | `legacy_overlay` | 467 |
| `after_stall` | `legacy_overlay` | 467 |
| `after_breakeven` | `breakeven_move` | 467 |
| `after_trail_chandelier` | `chandelier` | 467 |
| `after_trail_mfe` | `mfe_trail` | 467 |
| `after_trail_step` | `step_trail` | 467 |
| `after_trail_index` | `index_trail` | 467 |
| `after_scale_out` | `scale_out` | 467 |
| `after_target_extend` | `target_extend` | 467 |
| `after_reversal` | `reversal` | 467 |
| `after_momentum_fade_vwap_slope` | `momentum_fade` | 467 |
| `after_iv_crush` | `iv_crush` | 467 |
| `after_iv_spike` | `iv_spike` | 467 |
| `after_theta_bleed` | `theta_budget` | 467 |
| `after_expiry_cliff` | `expiry_cliff` | 467 |
| `after_lunch_chop` | `lunch_chop` | 467 |
| `after_gap` | `gap_against` | 467 |
| `after_stale_feed` | `stale_and_flat` | 467 |
| `after_1515_freeze` | `hold_to_1515` | 467 |
| `after_max_loss_trade` | `v2_default` | 467 |
| `after_max_loss_day` | `day_loss` | 467 |
| `own_quote_persistence` | `quote_persistence` | 467 |
| `own_tod_two_speed` | `tod_two_speed` | 467 |
| `own_elasticity_die` | `elasticity_die` | 467 |

| Skipped category | Why |
|---|---|
| `pretrade_har_realised_vol` | No HAR estimator in-repo; used ATR + implied straddle instead. |
| `pretrade_position_size_from_stop` | Live/legacy lots are given (25 / 2 / 1). Not resized in this run. |
| `after_reentry_after_stop` | Re-entry is an entry rule. Not generated as a new ticket in this run. |
| `after_order_not_filled` | Entries are already filled tickets. Rejects run only in stress.reject_p15. |

Own new ideas (not in the brief list), all replayed on all four entry sets:

1. `quote_persistence` — trail only after 3 upticks in a row.
2. `tod_two_speed` — before 12:00 IST use a wide TOD-MAE stop; after 12:00 a 12-minute time-stop.
3. `elasticity_die` — exit a green ticket when |dPremium|/|dIndex| collapses.

`iv_crush` and `iv_spike` matched `fixed_stop_target` on live random (no 20% IV move on the path). Label: IV trigger is **DATA_INSUFFICIENT** on this tape; the numbers are the underlying stop/target.

`v2_default` matched `hold_to_1515` on 1-lot random and 2-lot V2 (₹30k house stop never hit). They differ on 25-lot legacy.

## Results

`n_trade_results = 14944`. `n_variants_tested = 68`. All nets are after `ledger.charges`.

Every library plan ran on every entry set: random 278 / legacy 81 / v2_boss 60 / random_hist 48.

### Low-confidence cells (n < 30)

Any Summary with n<30 is flagged `low_confidence`. Count in `tables.json`: **352**. Scenario-labelled cells (scenario ≠ ALL, split=all): 480 cells, **288 LOW**, **192 ok**.

n is the same for every plan on a given entry-set × scenario:

| Entry set | Scenario | n (every plan) | flag |
|---|---|---:|---|
| `random` | `expiry_chop` | 3 | LOW (n<30) |
| `random` | `mixed` | 37 | ok |
| `random` | `chop` | 170 | ok |
| `v2_boss` | `chop` | 36 | ok |
| `legacy` | `chop` | 53 | ok |
| `random` | `trend_up` | 34 | ok |
| `v2_boss` | `trend_up` | 8 | LOW (n<30) |
| `legacy` | `trend_up` | 13 | LOW (n<30) |
| `random` | `expiry_trend_down` | 34 | ok |
| `v2_boss` | `expiry_trend_down` | 8 | LOW (n<30) |
| `legacy` | `expiry_trend_down` | 6 | LOW (n<30) |
| `random_hist` | `chop` | 24 | LOW (n<30) |
| `random_hist` | `expiry_chop` | 8 | LOW (n<30) |
| `random_hist` | `mixed` | 8 | LOW (n<30) |
| `random_hist` | `expiry_mixed` | 8 | LOW (n<30) |

Ignore LOW cells for ranking. History OOS does not exist; every history scenario cell is LOW.

### Random 1-lot early vs late (cut 2026-09-22)

Early = session ≤ 2026-09-22 (142 tickets). Late = session > 2026-09-22 (136 tickets). Same unique tickets used for the sweep choose / OOS report.

| Plan | Early n | Early net ₹ | Late n | Late net ₹ | All n | All net ₹ |
|---|---:|---:|---:|---:|---:|---:|
| `quote_persistence` | 142 | 187,313.29 | 136 | 203,934.82 | 278 | 391,248.11 |
| `structure_stop` | 142 | 202,124.26 | 136 | 175,003.75 | 278 | 377,128.01 |
| `noise_band` | 142 | 208,034.44 | 136 | 164,798.83 | 278 | 372,833.27 |
| `momentum_fade` | 142 | 192,253.41 | 136 | 175,950.94 | 278 | 368,204.35 |
| `fixed_stop_target` | 142 | 203,736.49 | 136 | 164,072.31 | 278 | 367,808.80 |
| `iv_crush` | 142 | 203,736.49 | 136 | 164,072.31 | 278 | 367,808.80 |
| `iv_spike` | 142 | 203,736.49 | 136 | 164,072.31 | 278 | 367,808.80 |
| `tod_two_speed` | 142 | 202,351.30 | 136 | 165,087.48 | 278 | 367,438.78 |
| `breakeven_move` | 142 | 182,940.74 | 136 | 183,554.25 | 278 | 366,494.99 |
| `regime_router` | 142 | 199,023.15 | 136 | 165,528.63 | 278 | 364,551.78 |
| `reversal` | 142 | 189,885.60 | 136 | 173,790.57 | 278 | 363,676.17 |
| `time_and_stop` | 142 | 191,698.90 | 136 | 171,961.05 | 278 | 363,659.95 |
| `elasticity_die` | 142 | 199,490.41 | 136 | 163,264.70 | 278 | 362,755.11 |
| `chandelier` | 142 | 203,382.88 | 136 | 147,817.99 | 278 | 351,200.87 |
| `index_stop` | 142 | 188,507.00 | 136 | 162,671.10 | 278 | 351,178.10 |
| `legacy_overlay` | 142 | 184,770.21 | 136 | 164,886.42 | 278 | 349,656.63 |
| `expiry_cliff` | 142 | 202,468.14 | 136 | 145,822.81 | 278 | 348,290.95 |
| `step_trail` | 142 | 190,891.12 | 136 | 156,799.71 | 278 | 347,690.83 |
| `lunch_chop` | 142 | 187,647.39 | 136 | 157,390.26 | 278 | 345,037.65 |
| `asymmetric_ce_pe` | 142 | 199,149.80 | 136 | 145,213.14 | 278 | 344,362.94 |
| `implied_move` | 142 | 196,606.76 | 136 | 128,572.51 | 278 | 325,179.27 |
| `stale_and_flat` | 142 | 185,256.68 | 136 | 138,054.33 | 278 | 323,311.01 |
| `theta_budget` | 142 | 177,056.51 | 136 | 144,587.11 | 278 | 321,643.62 |
| `index_trail` | 142 | 162,654.02 | 136 | 155,972.72 | 278 | 318,626.74 |
| `atr_stop` | 142 | 157,136.62 | 136 | 157,409.68 | 278 | 314,546.30 |
| `gap_against` | 142 | 161,081.12 | 136 | 132,948.66 | 278 | 294,029.78 |
| `day_loss` | 142 | 157,811.36 | 136 | 134,126.17 | 278 | 291,937.53 |
| `target_extend` | 142 | 171,221.13 | 136 | 117,998.16 | 278 | 289,219.29 |
| `hold_to_1515` | 142 | 159,371.50 | 136 | 128,910.18 | 278 | 288,281.68 |
| `v2_default` | 142 | 159,371.50 | 136 | 128,910.18 | 278 | 288,281.68 |
| `mfe_trail` | 142 | 165,998.43 | 136 | 122,192.27 | 278 | 288,190.70 |
| `scale_out` | 142 | 127,112.42 | 136 | 132,711.81 | 278 | 259,824.23 |

Sweep winner chosen on early only: `noise_2.2`. OOS report on late only: `sweep_winner_noise_2.2` n=136 net 152,135.16 CI 98,013.41 … 201,492.30 DSR 8.39 (`n_variants=68`).

On the same late 136 tickets, `quote_persistence` net ₹203,934.82 and `breakeven_move` ₹183,554.25 beat the sweep winner ₹152,135.16. The sweep is honest (chosen on early only) but it is not the best OOS plan.

### Best library plan per random scenario (n≥30 only)

| Scenario | n | Best plan | Net ₹ | vs hold ₹ | flag |
|---|---:|---|---:|---:|---|
| `chop` | 170 | `quote_persistence` | 254,475.09 | 61,848.54 | ok |
| `trend_up` | 34 | `index_stop` | 68,543.16 | 7,830.50 | ok |
| `expiry_trend_down` | 34 | `chandelier` | 70,325.74 | 42,159.16 | ok |
| `mixed` | 37 | `elasticity_die` | 47,546.56 | 42,353.61 | ok |
| `expiry_chop` | 3 | — | — | — | LOW (n<30) |

### Own new ideas (replayed, all entry sets)

| Plan | Entry set | n | Win | Net ₹ | Bootstrap CI ₹ | DSR |
|---|---|---:|---:|---:|---|---:|
| `quote_persistence` | `random` | 278 | 51.4% | 391,248.11 | 318,015.96 … 470,073.39 | 17.43 |
| `quote_persistence` | `legacy` | 81 | 24.7% | -829,398.68 | -1,238,149.22 … -391,365.56 | -19.42 |
| `quote_persistence` | `v2_boss` | 60 | 35.0% | -721.12 | -38,892.53 … 39,778.50 | -18.62 |
| `quote_persistence` | `random_hist` | 48 | 39.6% | -4,408.81 | -16,276.84 … 8,837.35 | -19.00 |
| `tod_two_speed` | `random` | 278 | 54.3% | 367,438.78 | 290,492.62 … 441,916.66 | 17.28 |
| `tod_two_speed` | `legacy` | 81 | 37.0% | -278,284.03 | -635,789.65 … 122,535.26 | -24.19 |
| `tod_two_speed` | `v2_boss` | 60 | 30.0% | -7,571.99 | -32,316.81 … 23,632.03 | -20.96 |
| `tod_two_speed` | `random_hist` | 48 | 37.5% | -2,520.98 | -15,526.92 … 12,544.96 | -18.36 |
| `elasticity_die` | `random` | 278 | 50.0% | 362,755.11 | 275,597.64 … 446,994.18 | 16.00 |
| `elasticity_die` | `legacy` | 81 | 38.3% | -1,146,881.45 | -2,287,916.90 … -45,692.23 | -22.89 |
| `elasticity_die` | `v2_boss` | 60 | 36.7% | 25,241.86 | -58,350.01 … 104,589.41 | -12.52 |
| `elasticity_die` | `random_hist` | 48 | 35.4% | 10,314.56 | -23,379.48 … 51,253.15 | -11.96 |

### Headline: plan × entry set (scenario ALL)

| Plan | Entry set | n | Win | Net ₹ | Avg ₹ | Max DD ₹ | Bootstrap CI ₹ | DSR | flag |
|---|---|---:|---:|---:|---:|---:|---|---:|---|
| `quote_persistence` | `random` | 278 | 51.4% | 391,248.11 | 1,407.37 | -3,103.61 | 318,015.96 … 470,073.39 | 17.43 | |
| `structure_stop` | `random` | 278 | 45.3% | 377,128.01 | 1,356.58 | -1,479.11 | 303,707.52 … 452,611.72 | 17.54 | |
| `noise_band` | `random` | 278 | 43.9% | 372,833.27 | 1,341.13 | -2,956.45 | 297,419.01 … 453,857.34 | 16.87 | |
| `momentum_fade` | `random` | 278 | 52.2% | 368,204.35 | 1,324.48 | -1,753.03 | 297,031.20 … 445,706.09 | 17.38 | |
| `fixed_stop_target` | `random` | 278 | 58.3% | 367,808.80 | 1,323.05 | -10,029.62 | 273,307.44 … 451,023.79 | 15.70 | |
| `iv_crush` | `random` | 278 | 58.3% | 367,808.80 | 1,323.05 | -10,029.62 | 273,307.44 … 451,023.79 | 15.70 | |
| `iv_spike` | `random` | 278 | 58.3% | 367,808.80 | 1,323.05 | -10,029.62 | 273,307.44 … 451,023.79 | 15.70 | |
| `tod_two_speed` | `random` | 278 | 54.3% | 367,438.78 | 1,321.72 | -3,014.84 | 290,492.62 … 441,916.66 | 17.28 | |
| `breakeven_move` | `random` | 278 | 48.6% | 366,494.99 | 1,318.33 | -7,558.41 | 279,683.26 … 457,568.86 | 15.90 | |
| `regime_router` | `random` | 278 | 56.1% | 364,551.78 | 1,311.34 | -4,630.25 | 287,595.86 … 441,343.85 | 16.90 | |
| `reversal` | `random` | 278 | 48.9% | 363,676.17 | 1,308.19 | -2,100.10 | 292,079.52 … 438,987.81 | 17.34 | |
| `time_and_stop` | `random` | 278 | 57.6% | 363,659.95 | 1,308.13 | -3,038.73 | 286,301.63 … 444,639.29 | 17.12 | |
| `elasticity_die` | `random` | 278 | 50.0% | 362,755.11 | 1,304.87 | -6,544.97 | 275,597.64 … 446,994.18 | 16.00 | |
| `chandelier` | `random` | 278 | 54.7% | 351,200.87 | 1,263.31 | -5,929.53 | 259,500.83 … 450,268.36 | 15.62 | |
| `index_stop` | `random` | 278 | 54.7% | 351,178.10 | 1,263.23 | -7,808.22 | 259,885.77 … 445,177.70 | 15.35 | |
| `legacy_overlay` | `random` | 278 | 59.0% | 349,656.63 | 1,257.76 | -4,254.60 | 272,408.28 … 428,642.86 | 16.58 | |
| `expiry_cliff` | `random` | 278 | 56.5% | 348,290.95 | 1,252.85 | -8,764.58 | 265,633.11 … 434,619.25 | 15.96 | |
| `step_trail` | `random` | 278 | 64.7% | 347,690.83 | 1,250.69 | -7,981.94 | 272,389.12 … 426,299.67 | 16.18 | |
| `lunch_chop` | `random` | 278 | 52.2% | 345,037.65 | 1,241.14 | -7,246.92 | 267,365.00 … 433,032.42 | 16.28 | |
| `asymmetric_ce_pe` | `random` | 278 | 56.8% | 344,362.94 | 1,238.72 | -8,003.57 | 253,864.13 … 431,841.91 | 15.00 | |
| `implied_move` | `random` | 278 | 55.8% | 325,179.27 | 1,169.71 | -6,006.87 | 243,190.62 … 402,100.65 | 15.45 | |
| `stale_and_flat` | `random` | 278 | 57.9% | 323,311.01 | 1,162.99 | -8,356.65 | 236,759.79 … 411,640.71 | 15.07 | |
| `theta_budget` | `random` | 278 | 36.3% | 321,643.62 | 1,156.99 | -10,296.07 | 229,981.58 … 416,922.44 | 14.59 | |
| `index_trail` | `random` | 278 | 58.6% | 318,626.74 | 1,146.14 | -13,458.55 | 226,907.61 … 421,919.13 | 14.36 | |
| `atr_stop` | `random` | 278 | 23.7% | 314,546.30 | 1,131.46 | -2,133.31 | 236,312.06 … 402,712.51 | 15.32 | |
| `gap_against` | `random` | 278 | 53.6% | 294,029.78 | 1,057.66 | -12,394.77 | 187,978.35 … 393,231.46 | 12.51 | |
| `day_loss` | `random` | 278 | 55.4% | 291,937.53 | 1,050.13 | -14,081.50 | 181,170.27 … 396,303.46 | 12.24 | |
| `target_extend` | `random` | 278 | 53.6% | 289,219.29 | 1,040.36 | -12,041.20 | 193,633.19 … 384,616.46 | 13.00 | |
| `hold_to_1515` | `random` | 278 | 56.5% | 288,281.68 | 1,036.98 | -14,895.71 | 184,679.24 … 390,792.00 | 11.96 | |
| `v2_default` | `random` | 278 | 56.5% | 288,281.68 | 1,036.98 | -14,895.71 | 184,679.24 … 390,792.00 | 11.96 | |
| `mfe_trail` | `random` | 278 | 70.1% | 288,190.70 | 1,036.66 | -8,154.05 | 212,391.84 … 369,208.70 | 15.13 | |
| `scale_out` | `random` | 278 | 50.0% | 259,824.23 | 934.62 | -11,444.87 | 157,267.03 … 362,093.66 | 11.15 | |
| `step_trail` | `legacy` | 81 | 55.6% | -109,689.57 | -1,354.19 | -537,585.54 | -851,166.86 … 613,225.60 | -23.49 | |
| `reversal` | `legacy` | 81 | 33.3% | -160,373.44 | -1,979.92 | -273,116.94 | -411,783.12 … 185,196.22 | -24.64 | |
| `momentum_fade` | `legacy` | 81 | 32.1% | -216,895.98 | -2,677.73 | -335,072.76 | -517,654.96 … 130,500.78 | -24.17 | |
| `tod_two_speed` | `legacy` | 81 | 37.0% | -278,284.03 | -3,435.61 | -361,140.81 | -635,789.65 … 122,535.26 | -24.19 | |
| `structure_stop` | `legacy` | 81 | 25.9% | -300,017.15 | -3,703.92 | -365,291.85 | -601,911.43 … 69,842.56 | -23.07 | |
| `mfe_trail` | `legacy` | 81 | 66.7% | -305,774.70 | -3,775.00 | -537,682.29 | -918,690.16 … 289,564.40 | -24.84 | |
| `regime_router` | `legacy` | 81 | 37.0% | -414,359.63 | -5,115.55 | -489,051.67 | -941,572.49 … 173,106.34 | -24.25 | |
| `time_and_stop` | `legacy` | 81 | 37.0% | -547,272.80 | -6,756.45 | -690,330.03 | -1,035,901.17 … -82,503.23 | -22.39 | |
| `day_loss` | `legacy` | 81 | 12.3% | -720,408.30 | -8,893.93 | -808,075.38 | -1,018,978.21 … -387,064.04 | -18.67 | |
| `noise_band` | `legacy` | 81 | 13.6% | -769,389.03 | -9,498.63 | -841,323.87 | -1,079,470.89 … -410,506.63 | -19.01 | |
| `theta_budget` | `legacy` | 81 | 13.6% | -779,120.37 | -9,618.77 | -845,196.61 | -1,209,111.21 … -398,445.10 | -19.64 | |
| `quote_persistence` | `legacy` | 81 | 24.7% | -829,398.68 | -10,239.49 | -845,621.90 | -1,238,149.22 … -391,365.56 | -19.42 | |
| `expiry_cliff` | `legacy` | 81 | 35.8% | -876,838.50 | -10,825.17 | -1,224,574.20 | -1,964,297.05 … 241,229.11 | -24.10 | |
| `stale_and_flat` | `legacy` | 81 | 40.7% | -936,118.27 | -11,557.02 | -1,128,663.70 | -1,695,617.32 … -137,849.86 | -22.05 | |
| `legacy_overlay` | `legacy` | 81 | 27.2% | -967,663.89 | -11,946.47 | -1,032,848.00 | -1,521,017.78 … -429,307.30 | -20.02 | |
| `chandelier` | `legacy` | 81 | 23.5% | -990,694.58 | -12,230.80 | -1,227,699.43 | -1,529,317.19 … -324,321.77 | -20.16 | |
| `implied_move` | `legacy` | 81 | 38.3% | -1,036,431.48 | -12,795.45 | -1,331,375.00 | -2,251,064.14 … 97,292.17 | -23.48 | |
| `lunch_chop` | `legacy` | 81 | 30.9% | -1,113,876.18 | -13,751.56 | -1,115,478.17 | -1,681,375.11 … -589,181.88 | -19.14 | |
| `breakeven_move` | `legacy` | 81 | 33.3% | -1,131,068.10 | -13,963.80 | -1,260,215.58 | -2,206,344.48 … -158,896.27 | -22.33 | |
| `elasticity_die` | `legacy` | 81 | 38.3% | -1,146,881.45 | -14,159.03 | -1,400,710.35 | -2,287,916.90 … -45,692.23 | -22.89 | |
| `scale_out` | `legacy` | 81 | 37.0% | -1,255,106.89 | -15,495.15 | -1,520,734.08 | -2,314,200.90 … -278,262.92 | -21.84 | |
| `fixed_stop_target` | `legacy` | 81 | 39.5% | -1,301,122.23 | -16,063.24 | -1,526,487.13 | -2,525,308.58 … -120,375.90 | -22.58 | |
| `iv_crush` | `legacy` | 81 | 39.5% | -1,301,122.23 | -16,063.24 | -1,526,487.13 | -2,525,308.58 … -120,375.90 | -22.58 | |
| `iv_spike` | `legacy` | 81 | 39.5% | -1,301,122.23 | -16,063.24 | -1,526,487.13 | -2,525,308.58 … -120,375.90 | -22.58 | |
| `asymmetric_ce_pe` | `legacy` | 81 | 44.4% | -1,316,530.00 | -16,253.46 | -1,336,625.86 | -2,154,003.09 … -395,405.94 | -20.92 | |
| `v2_default` | `legacy` | 81 | 21.0% | -1,527,536.51 | -18,858.48 | -1,751,563.90 | -2,036,444.68 … -936,181.59 | -18.02 | |
| `hold_to_1515` | `legacy` | 81 | 39.5% | -1,594,358.01 | -19,683.43 | -1,823,980.89 | -2,906,850.49 … -510,766.03 | -21.34 | |
| `atr_stop` | `legacy` | 81 | 39.5% | -1,594,358.01 | -19,683.43 | -1,823,980.89 | -2,906,850.49 … -510,766.03 | -21.34 | |
| `index_stop` | `legacy` | 81 | 39.5% | -1,604,819.15 | -19,812.58 | -1,834,442.03 | -2,862,859.54 … -556,620.27 | -21.28 | |
| `target_extend` | `legacy` | 81 | 35.8% | -1,865,455.03 | -23,030.31 | -2,066,695.04 | -2,893,974.40 … -956,765.59 | -19.55 | |
| `index_trail` | `legacy` | 81 | 37.0% | -1,963,578.80 | -24,241.71 | -2,157,195.98 | -3,034,549.09 … -905,101.81 | -19.60 | |
| `gap_against` | `legacy` | 81 | 37.0% | -2,036,563.36 | -25,142.76 | -2,226,369.11 | -3,122,564.73 … -906,885.86 | -19.52 | |
| `fixed_stop_target` | `v2_boss` | 60 | 51.7% | 81,040.99 | 1,350.68 | -28,789.10 | -16,804.26 … 170,413.45 | -3.16 | |
| `iv_crush` | `v2_boss` | 60 | 51.7% | 81,040.99 | 1,350.68 | -28,789.10 | -16,804.26 … 170,413.45 | -3.16 | |
| `iv_spike` | `v2_boss` | 60 | 51.7% | 81,040.99 | 1,350.68 | -28,789.10 | -16,804.26 … 170,413.45 | -3.16 | |
| `implied_move` | `v2_boss` | 60 | 48.3% | 64,698.91 | 1,078.32 | -27,452.67 | -28,176.87 … 156,593.24 | -5.22 | |
| `chandelier` | `v2_boss` | 60 | 35.0% | 35,167.87 | 586.13 | -24,376.70 | -41,160.24 … 120,806.12 | -9.56 | |
| `expiry_cliff` | `v2_boss` | 60 | 45.0% | 32,793.27 | 546.55 | -29,244.41 | -50,849.71 … 113,038.39 | -10.14 | |
| `scale_out` | `v2_boss` | 60 | 46.7% | 29,383.95 | 489.73 | -33,182.77 | -54,947.83 … 110,996.23 | -11.15 | |
| `elasticity_die` | `v2_boss` | 60 | 36.7% | 25,241.86 | 420.70 | -27,822.47 | -58,350.01 … 104,589.41 | -12.52 | |
| `asymmetric_ce_pe` | `v2_boss` | 60 | 46.7% | 20,201.04 | 336.68 | -37,947.23 | -60,157.10 … 108,542.07 | -13.91 | |
| `step_trail` | `v2_boss` | 60 | 53.3% | 14,050.87 | 234.18 | -21,444.40 | -46,218.60 … 83,498.66 | -14.19 | |
| `noise_band` | `v2_boss` | 60 | 16.7% | 7,861.91 | 131.03 | -19,971.68 | -36,618.01 … 64,318.14 | -15.84 | |
| `breakeven_move` | `v2_boss` | 60 | 33.3% | 7,005.46 | 116.76 | -36,641.26 | -71,185.69 … 97,014.43 | -16.88 | |
| `gap_against` | `v2_boss` | 60 | 46.7% | 5,772.87 | 96.21 | -63,660.68 | -76,215.63 … 97,163.77 | -17.22 | |
| `structure_stop` | `v2_boss` | 60 | 25.0% | 4,702.45 | 78.37 | -12,495.44 | -23,266.50 … 32,354.89 | -15.62 | |
| `index_trail` | `v2_boss` | 60 | 56.7% | 4,157.41 | 69.29 | -31,775.61 | -61,633.21 … 72,103.86 | -17.29 | |
| `reversal` | `v2_boss` | 60 | 25.0% | 3,456.80 | 57.61 | -11,961.03 | -21,906.20 … 26,164.73 | -16.15 | |
| `momentum_fade` | `v2_boss` | 60 | 28.3% | 238.95 | 3.98 | -15,120.45 | -22,705.57 … 26,836.03 | -18.23 | |
| `hold_to_1515` | `v2_boss` | 60 | 46.7% | 63.91 | 1.07 | -64,802.43 | -85,483.01 … 91,351.34 | -18.36 | |
| `v2_default` | `v2_boss` | 60 | 46.7% | 63.91 | 1.07 | -64,802.43 | -85,483.01 … 91,351.34 | -18.36 | |
| `quote_persistence` | `v2_boss` | 60 | 35.0% | -721.12 | -12.02 | -23,926.46 | -38,892.53 … 39,778.50 | -18.62 | |
| `mfe_trail` | `v2_boss` | 60 | 66.7% | -1,460.73 | -24.35 | -20,772.95 | -52,168.98 … 56,504.18 | -18.79 | |
| `time_and_stop` | `v2_boss` | 60 | 40.0% | -2,031.62 | -33.86 | -13,652.86 | -37,500.38 … 38,081.69 | -19.12 | |
| `day_loss` | `v2_boss` | 60 | 46.7% | -2,362.46 | -39.37 | -67,948.93 | -89,476.10 … 90,501.09 | -18.78 | |
| `regime_router` | `v2_boss` | 60 | 31.7% | -5,521.92 | -92.03 | -18,174.67 | -36,813.41 … 28,424.49 | -20.24 | |
| `tod_two_speed` | `v2_boss` | 60 | 30.0% | -7,571.99 | -126.20 | -14,014.72 | -32,316.81 … 23,632.03 | -20.96 | |
| `index_stop` | `v2_boss` | 60 | 35.0% | -7,604.30 | -126.74 | -48,434.41 | -78,487.17 … 67,856.55 | -19.78 | |
| `target_extend` | `v2_boss` | 60 | 41.7% | -7,941.71 | -132.36 | -61,967.44 | -92,364.94 … 79,121.84 | -19.68 | |
| `atr_stop` | `v2_boss` | 60 | 0.0% | -15,428.32 | -257.14 | -15,428.32 | -16,097.69 … -14,829.14 | -11.41 | |
| `legacy_overlay` | `v2_boss` | 60 | 36.7% | -15,804.63 | -263.41 | -30,826.11 | -53,412.24 … 28,473.94 | -21.30 | |
| `theta_budget` | `v2_boss` | 60 | 13.3% | -17,861.09 | -297.68 | -28,510.82 | -70,206.83 … 34,368.32 | -21.23 | |
| `lunch_chop` | `v2_boss` | 60 | 38.3% | -19,528.43 | -325.47 | -32,943.19 | -55,244.77 … 23,006.43 | -21.30 | |
| `stale_and_flat` | `v2_boss` | 60 | 43.3% | -33,593.35 | -559.89 | -43,341.61 | -88,466.37 … 22,472.16 | -20.94 | |
| `breakeven_move` | `random_hist` | 48 | 33.3% | 22,014.80 | 458.64 | -13,070.38 | -11,870.48 … 60,523.78 | -6.08 | |
| `chandelier` | `random_hist` | 48 | 37.5% | 16,143.59 | 336.32 | -13,972.19 | -10,354.81 … 48,590.21 | -7.04 | |
| `lunch_chop` | `random_hist` | 48 | 52.1% | 13,830.85 | 288.14 | -13,336.35 | -10,443.13 … 43,799.91 | -7.42 | |
| `mfe_trail` | `random_hist` | 48 | 79.2% | 13,461.03 | 280.44 | -5,435.98 | -2,589.94 … 33,013.38 | -3.38 | |
| `step_trail` | `random_hist` | 48 | 66.7% | 11,008.71 | 229.35 | -5,896.59 | -7,283.28 … 28,230.92 | -5.63 | |
| `elasticity_die` | `random_hist` | 48 | 35.4% | 10,314.56 | 214.89 | -23,059.91 | -23,379.48 … 51,253.15 | -11.96 | |
| `index_trail` | `random_hist` | 48 | 64.6% | 9,545.78 | 198.87 | -6,700.71 | -10,827.02 … 32,216.50 | -9.04 | |
| `asymmetric_ce_pe` | `random_hist` | 48 | 47.9% | 9,338.17 | 194.55 | -19,315.12 | -25,769.17 … 47,233.38 | -12.22 | |
| `expiry_cliff` | `random_hist` | 48 | 41.7% | 5,718.13 | 119.13 | -26,057.18 | -24,405.14 … 39,725.01 | -13.57 | |
| `implied_move` | `random_hist` | 48 | 41.7% | 4,783.97 | 99.67 | -27,957.98 | -31,803.26 … 47,767.68 | -14.51 | |
| `fixed_stop_target` | `random_hist` | 48 | 43.8% | 3,295.13 | 68.65 | -27,544.32 | -31,343.97 … 50,731.16 | -15.19 | |
| `iv_crush` | `random_hist` | 48 | 43.8% | 3,295.13 | 68.65 | -27,544.32 | -31,343.97 … 50,731.16 | -15.19 | |
| `iv_spike` | `random_hist` | 48 | 43.8% | 3,295.13 | 68.65 | -27,544.32 | -31,343.97 … 50,731.16 | -15.19 | |
| `index_stop` | `random_hist` | 48 | 31.2% | 2,506.83 | 52.23 | -24,857.97 | -25,806.61 … 41,515.59 | -15.27 | |
| `gap_against` | `random_hist` | 48 | 39.6% | -1,057.99 | -22.04 | -30,950.26 | -36,285.39 … 42,871.49 | -16.75 | |
| `target_extend` | `random_hist` | 48 | 35.4% | -1,327.26 | -27.65 | -30,810.50 | -37,195.44 … 41,560.91 | -16.84 | |
| `legacy_overlay` | `random_hist` | 48 | 22.9% | -1,846.27 | -38.46 | -6,497.47 | -13,029.22 … 11,909.92 | -17.99 | |
| `hold_to_1515` | `random_hist` | 48 | 43.8% | -1,963.01 | -40.90 | -33,588.99 | -43,413.69 … 46,371.40 | -17.00 | |
| `v2_default` | `random_hist` | 48 | 43.8% | -1,963.01 | -40.90 | -33,588.99 | -43,413.69 … 46,371.40 | -17.00 | |
| `tod_two_speed` | `random_hist` | 48 | 37.5% | -2,520.98 | -52.52 | -11,500.54 | -15,526.92 … 12,544.96 | -18.36 | |
| `theta_budget` | `random_hist` | 48 | 16.7% | -2,572.86 | -53.60 | -18,513.20 | -26,143.82 … 26,469.40 | -17.61 | |
| `scale_out` | `random_hist` | 48 | 35.4% | -3,438.96 | -71.64 | -30,941.97 | -37,930.71 … 37,224.10 | -17.49 | |
| `day_loss` | `random_hist` | 48 | 39.6% | -4,363.38 | -90.90 | -34,255.65 | -40,288.15 … 40,896.02 | -17.65 | |
| `quote_persistence` | `random_hist` | 48 | 39.6% | -4,408.81 | -91.85 | -9,667.06 | -16,276.84 … 8,837.35 | -19.00 | |
| `time_and_stop` | `random_hist` | 48 | 50.0% | -5,881.56 | -122.53 | -13,407.56 | -20,937.57 … 9,500.59 | -19.02 | |
| `momentum_fade` | `random_hist` | 48 | 31.2% | -6,059.94 | -126.25 | -8,764.18 | -12,521.81 … 1,025.57 | -17.98 | |
| `atr_stop` | `random_hist` | 48 | 0.0% | -7,321.71 | -152.54 | -7,321.71 | -8,011.27 … -6,602.93 | -10.77 | |
| `stale_and_flat` | `random_hist` | 48 | 0.0% | -7,321.71 | -152.54 | -7,321.71 | -8,011.27 … -6,602.93 | -10.77 | |
| `reversal` | `random_hist` | 48 | 25.0% | -7,944.50 | -165.51 | -9,471.44 | -13,882.73 … -1,625.93 | -16.65 | |
| `noise_band` | `random_hist` | 48 | 18.8% | -8,216.95 | -171.19 | -17,734.61 | -25,109.93 … 10,792.85 | -19.00 | |
| `structure_stop` | `random_hist` | 48 | 14.6% | -11,045.56 | -230.12 | -13,176.44 | -16,458.26 … -4,721.61 | -15.07 | |
| `regime_router` | `random_hist` | 48 | 35.4% | -17,228.22 | -358.92 | -24,599.67 | -37,748.32 … 1,693.22 | -17.73 | |

Full plan × entry × scenario rows (673 summaries) stay in `/tmp/exitlab-audit/tables.json` → `summaries`. Each row has `n_trades` and `low_confidence`.

### Sweep choose nets (random entries, sessions ≤ 2026-09-22, 36 variants)

| Variant | Choose net ₹ |
|---|---:|
| `noise_2.2` | 215,971.96 |
| `noise_1.6` | 214,911.20 |
| `noise_1.2` | 206,217.81 |
| `fixed_0.15_0.55` | 204,336.53 |
| `fixed_0.15_0.35` | 203,979.74 |
| `fixed_0.15_0.45` | 203,791.62 |
| `fixed_0.20_0.55` | 200,229.90 |
| `fixed_0.20_0.35` | 199,873.11 |
| `fixed_0.20_0.45` | 199,684.99 |
| `fixed_0.15_0.25` | 199,065.42 |
| `fixed_0.25_0.55` | 198,260.99 |
| `fixed_0.25_0.45` | 197,716.08 |
| `fixed_0.25_0.35` | 197,242.49 |
| `time_1800` | 196,953.84 |
| `fixed_0.30_0.55` | 196,194.71 |
| `fixed_0.30_0.45` | 195,649.80 |
| `fixed_0.20_0.25` | 195,224.77 |
| `fixed_0.30_0.35` | 195,176.21 |
| `time_1200` | 194,793.43 |
| `time_720` | 194,634.49 |
| `fixed_0.40_0.55` | 192,736.83 |
| `fixed_0.25_0.25` | 192,467.64 |
| `fixed_0.40_0.45` | 192,191.92 |
| `fixed_0.40_0.35` | 191,718.33 |
| `fixed_0.30_0.25` | 190,589.50 |
| `fixed_0.40_0.25` | 187,481.95 |
| `time_2700` | 185,337.87 |
| `trail_0.25_8` | 177,961.40 |
| `trail_0.25_4` | 177,215.37 |
| `trail_0.25_12` | 172,320.50 |
| `trail_0.35_4` | 166,812.65 |
| `trail_0.35_8` | 165,998.43 |
| `trail_0.35_12` | 158,579.92 |
| `trail_0.50_4` | 150,898.75 |
| `trail_0.50_8` | 147,933.94 |
| `trail_0.50_12` | 140,992.25 |

36 sweep variants + 32 library plans = 68. DSR on every Summary uses `n_variants_tested=68` as the multiple-testing correction.

## Stress

Plan `regime_router`, n_sample=80, seed 7. From `tables.json` → `stress`. gap_1s/2s/30s, 1% index gap, and IV crush 20% are SYNTHETIC (quotes mutated or dropped). partial_fill_half and reject_p15 use harness flags.

| Case | n | closed | skipped | Net ₹ | note |
|---|---:|---:|---:|---:|---|
| `base` | 80 | 80 | 0 | 135,912.58 | base (same fill model) |
| `spread_x2` | 80 | 80 | 0 | 135,912.58 | spread ×2 (no bid/ask on dual-tape → same as base) |
| `slip_x2` | 80 | 80 | 0 | 132,704.46 | stated slip ×2 |
| `gap_1s_synthetic` | 40 | 40 | 0 | 62,377.20 | feed gap 1s SYNTHETIC |
| `gap_2s_synthetic` | 40 | 40 | 0 | 62,377.20 | feed gap 2s SYNTHETIC |
| `gap_30s_synthetic` | 40 | 40 | 0 | 62,377.20 | feed gap 30s SYNTHETIC |
| `partial_fill_half` | 40 | 0 | 40 | 0.00 | half-fill on 1-lot (whole-lot REJECT) |
| `reject_p15` | 40 | 33 | 7 | 58,955.74 | reject_prob=0.15 |
| `index_gap_1pct_synthetic` | 40 | 40 | 0 | -11,431.25 | 1% adverse index gap SYNTHETIC |
| `iv_crush_20_synthetic` | 40 | 40 | 0 | 8,368.57 | IV crush 20% SYNTHETIC |
| `partial_fill_half_v2_2lot` | 40 | 40 | 0 | -3,013.75 | half-fill addon: V2 2-lot |
| `partial_fill_half_legacy_25lot` | 20 | 20 | 0 | 1,496.89 | half-fill addon: legacy 25-lot |
| `mc_resample` | 200 | — | — | p05 100,525.68 / p50 134,731.39 / p95 174,089.15 | resample of the 80-trade base nets |

`spread_x2` equals `base` because dual-tape quotes in this sample have no bid/ask; the spread multiplier has nothing to widen. `slip_x2` is the priced 2× stated-slip case. Gap 1s/2s/30s produced the same net on this sample (the dropped window is the same first-second hole after entry). 1-lot half-fill is correctly REJECT (whole lots). The 2-lot / 25-lot addon is the actual partial-fill table.

## Legacy comparison

Two different numbers. Do not mix them.

### A. Desk's own recorded exits (`replay_paper_scalp` extras on the 81 tickets)

Net **−₹1,51,497.43** (gross −₹75,562.50, charges ₹75,934.93). All 25 lots. ITM200.

| Desk reason | n | Net ₹ | What |
|-------------|---|------:|------|
| CANCEL_AGAINST | 32 | −312,386.95 | noise / against-path stop-outs |
| COVER_LONG_UNWIND | 22 | −218,234.11 | early overlay unwind |
| CANCEL_NO_PROGRESS | 12 | −15,785.36 | no-progress overlay |
| CANCEL_STALL | 4 | +36,008.26 | stall overlay |
| CANCEL_BOOK_NEAR | 5 | +97,394.89 | book-near overlay |
| TARGET | 6 | +261,505.84 | target |
| **Total** | **81** | **−151,497.43** | |

Rupees lost to noise stop-outs: CANCEL_AGAINST **−₹3,12,386.95** (32). Rupees lost to early overlays: COVER_LONG_UNWIND + CANCEL_NO_PROGRESS + CANCEL_STALL + CANCEL_BOOK_NEAR = **−₹1,00,616.32** (43). Targets +₹2,61,505.84 (6) did not cover those.

Cancelled entries (never filled): 3,450 skips vs 81 fills. HOLD_MAJORITY 992, NO_NEW_AFTER_1516 929, PATH_KIND_HOLD 611 are the large buckets. Those skips have no ticket P&L (they are not fills).

By session (desk own): 17 +46,484.58 (3); 18 +22,402.36 (7); 21 −12,850.59 (13); 22 +656.18 (6); 23 −80,259.13 (14); 24 −37,958.88 (11); 25 −110,147.41 (18); 28 +20,175.46 (9).

### B. Lab `legacy_overlay` re-sim on the same 81 tickets

Net **−₹9,67,663.89** (CI −₹15.21 L … −₹4.29 L). Ticket-by-ticket the lab overlay does **not** match the desk. Use (A) for “what the desk did”; use (B) for “what this rule-set does in the harness”.

Hold-to-15:15 on those same 81 tickets: **−₹15,94,358.01**. The desk overlays cut that bleed versus hold, and still lost ₹1.51 L.

## Cost hand-work (one trade)

Trade `rnd-2026-09-15-7-0`, plan `hold_to_1515`, 1 lot × 65, CE. Entry 40.6 → exit 59.75.

- Buy turnover 40.6 × 65 = 2,639.00. Brokerage 20.00, STT 0.00 (buy), exchange 0.94, stamp 0.08, GST 3.77, buy total 24.79.
- Sell turnover 59.75 × 65 = 3,883.75. Brokerage 20.00, STT 5.83, exchange 1.38, stamp 0.00, GST 3.85, sell total 31.06.
- Hand total 24.79 + 31.06 = **55.85**. Trade `charges_inr` 55.85. MATCH True vs `ledger.charges` NSE (`config/charges.yaml`).
- Gross (59.75 − 40.6) × 65 = 1,244.75. Net 1,244.75 − 55.85 = 1,188.90.

Evidence: `/opt/cursor/artifacts/exitlab-cost-handwork.txt`.

## Edge cases (synthetic unit tests)

`packages/exitlab/tests/test_edges.py` — 6 passed (`/opt/cursor/artifacts/exitlab-edges.txt`):

| Case | Test | Result |
|---|---|---|
| Expiry day after 14:30 | `test_expiry_after_1430_cliff` | `EXPIRY_CLIFF` |
| 15:15 freeze | `test_1515_freeze_flattens_hold` | `FLATTEN_EOD` at 15:15 |
| No quotes for 60 s | `test_no_quotes_for_60s_stale` | `STALE_FEED` / flatten / stop |
| Stop and target inside the same bar | `test_stop_and_target_same_bar_stop_wins` | `SAME_BAR_STOP` |
| Zero-lot partial | `test_zero_lot_partial_is_reject` | `REJECT`, net 0 |
| CE/PE flip | `test_ce_pe_flip_uses_side` | PE ticket, side preserved |

## Look-ahead

```
python -m exitlab prove-lookahead
# HONEST_OK
# INJECT_RAISED look-ahead: injected_future 2026-09-17 15:20:00+05:30 > clock 2026-09-17 10:05:00+05:30
pytest packages/exitlab/tests/test_lookahead.py   # 7 passed
```

Evidence: `/opt/cursor/artifacts/exitlab-lookahead.txt`.

## What failed / what is not a promote

- **V2-boss (60 × 2 lots):** hold / V2 default +₹63.91, CI −₹85,483 … +₹91,351, DSR −18.36. `fixed_stop_target` +₹81,041 but CI crosses 0 and DSR −3.16. Do not promote from this set.
- **`atr_stop` on V2-boss:** 0% win, avg time 0 s, net −₹15,428. ATR was 0.0 on several late-start days — degenerate.
- **History OOS:** no tickets after 2025-10-14. Intended 2026-06+ holdout is DATA_INSUFFICIENT. On the 48 Oct-2025 tickets, `regime_router` lost more than hold (−₹17,228 vs −₹1,963).
- **Sweep vs OOS:** winner `noise_2.2` (choose ₹2,15,971.96) is OOS-positive (₹1,52,135.16, CI ₹98,013.41–₹2,01,492.30, DSR 8.39, 68 variants) but `quote_persistence` late ₹2,03,934.82 beats it. DSR is the multiple-testing correction.
- **Router uses the day label**, not a live-at-entry classifier.
- **V2 spread sample empty.** `spread_x2` == base. Stated 0.40% slip is the fill model when the book is missing.
- **`iv_crush` == `fixed_stop_target`** on live random/V2 — no 20% IV drop observed. The synthetic stress is the IV-crush table.
- **random expiry_chop n=3** — LOW. Ignore that cell.
- **1-lot half-fill** is REJECT by design; use the 2-lot / 25-lot addon for partials.

## Recommended playbook (paper only, OFF)

See `config/v2/exits/exitlab_playbook.yaml`. Off unless `enabled: true` **and** `load_exitlab_playbook(enabled=True)`. V2 `ExitPlan` has no noise-band / quote-persistence field, so the mapping stays: flatten 15:15, catastrophic ₹8,000, time stop 1,500 s unless +8 pts, 90 s grace. Trail / target / partials stay null.

Evidence for a time-stop mapping: `time_and_stop` late 136 trades ₹1,71,961.05. Evidence for the sweep file name: `sweep_winner_noise_2.2` late 136 trades ₹1,52,135.16 (CI ₹98,013.41–₹2,01,492.30, DSR 8.39, 68 variants).

Do not enable this as the V2 default. Do not use 25-lot desk P&L to pick a 1-lot playbook.

## Handoff

### Accepted
- Paper/replay harness in `packages/exitlab` (ask-in / bid-out, `ledger.charges`, no look-ahead).
- Every brief exit category mapped and replayed except the four skips listed above.
- All three entry sets × every library plan; random seeds 7, 11, 19.
- Opt-in playbook file, default off. `load_exitlab_playbook()` returns None.
- Honest time split 2026-09-22 + 68 variants for DSR. Tables copied from `/tmp/exitlab-audit`.

### Rejected
- Shipping any plan as the live default.
- Editing `paper_scalp.py`, `desk.sh`, recorder, or `config/v2/exits/defaults.yaml`.
- Inventing bid/ask on 1m history (stated slip instead).
- Filling empty V2 spread or 2026 history OOS cells.
- Treating n<30 cells as ranked evidence.

### Unknown / data insufficient
- News/event tags; V2 book spread; 2026 history OOS; IV-crush trigger on the real tape; live-at-entry regime (router used the day label).
- Thin 2026-08-04 week; 2026-09-14 after-hours; late-start live days; ATR=0 on 16/17/18.

### Gap addressed
- Exit research gap: a replayable, costed, no-look-ahead exit lab on real tapes, with baselines, stress, OOS, and an opt-in V2 mapping that does not change live defaults.

### Known risks
- V2 entry set is a selector proxy (1m direction + real holds), not the full plugin room.
- Sweep winner is not the best OOS plan.
- 25-lot vs 1-lot rupee totals are not comparable.
- Lab overlay ≠ desk overlay ticket-by-ticket.

### Next steps
- Re-run on a larger tape once more V2 days and more matched history weeks exist.
- If a live-at-entry regime classifier is added, re-score `regime_router` without the day label.
- Founder paper-session only if a later OOS table stays non-negative after costs and DSR. Not this PR.


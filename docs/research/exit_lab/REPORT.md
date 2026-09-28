# Exit Lab report (paper / replay only)

**Status:** HYPOTHESIS / PAPER / NO_PROMOTE. Every number in the tables comes from

```bash
python -m exitlab research --data .local_data --out /tmp/exitlab-run --seed 7 --max-hist-days 24
```

run on 2026-09-28. Raw JSON: `/tmp/exitlab-run/tables.json`, `entries.json`, `trades.json`, `oos_sweep.json`, `measure_live.json`, `measure_history.json`. If a cell is missing, this file says `DATA_INSUFFICIENT` — it was not filled in.

**Owner:** `packages/exitlab` + this file. V2 defaults are unchanged. Playbook: `config/v2/exits/exitlab_playbook.yaml` (`enabled: false`).

## Now / Why / Next

- **Now:** The lab replayed 15 named exit plans (plus 36 sweep variants) on 335 entries: 146 random 1-lot, 81 legacy 25-lot, 60 V2-boss 2-lot, 48 history 1-lot. 4,545 trade results after costs. Playbook stays off.
- **Why:** The live desk's own 81 fills lost ₹1,51,497.43 after costs. Cancels-against and cover-unwinds ate the target winners. This file measures that as a baseline; it does not copy those overlays as the answer.
- **Next:** Founder reads the OOS + stress tables. Not a promote. Do not turn the playbook on from this report alone.

**Do not compare rupee totals across entry sets.** Legacy tickets are 25 lots (VOLSIZE). V2-boss tickets are 2 lots. Random and history tickets are 1 lot. Same plan, different size.

## Data used

| Set | Path (local, gitignored) | What | Sessions / days | Notes |
|-----|--------------------------|------|-----------------|-------|
| Live dual-tape | `.local_data/tape/YYYY-MM-DD.jsonl` | Legacy recorder ticks (index + ATM/ITM + wings) | 2026-09-14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 28 | 12 files, 4,986 ticks. 19–20 weekend / off-session. |
| V2 recorder | `.local_data/tape/v2/2026-09-28/` | Depth + quote snapshots | 2026-09-28 only | `v2_spread_sample` in this run is empty (`[]`). Bid/ask spread on V2: **DATA_INSUFFICIENT**. |
| Option 1m | `.local_data/NIFTY_*.parquet` | Weekly NIFTY option 1m OHLC | Weeks 2025-10-14, 2026-04-28, 2026-05-26, 2026-06-02, 2026-07-07, 2026-08-04 | Entries matched only the first week (2025-10-06..14, 48 tickets). Later weeks: **DATA_INSUFFICIENT** (no matched ATM/ITM path in this run). 2026-08-04 week is thin (2,646 bars). |
| Index 1m | `.local_data/index_NIFTY.parquet` | NIFTY 1m | 66,062 bars / 178 sessions labelled 177 | Regime labels + history entries. Session filter 09:15–15:30 IST. |

**Split:** sweep parameters chosen on random live tickets with `session <= 2026-09-22` (74 trades). Reported on later untouched live days `2026-09-23..28` (72 trades). History `<= 2026-05-31` was the intended train cut; this run produced no history tickets after 2025-10-14, so history OOS is **DATA_INSUFFICIENT**.

**Fills:** buy at ask when the book exists; else LTP/close × (1 + 0.40% stated slip). Sell at bid / (1 − 0.40%). Costs: `ledger.charges` + `config/charges.yaml` (NSE). Lot 65.

**No look-ahead:** 1m bar known only at `available_ts` (close). Tape rows by `as_of_ist` / `available_ts`. Test: `packages/exitlab/tests/test_lookahead.py`.

## Reproduce

From a checkout with the archives extracted to `.local_data/` (do not commit data):

```bash
python -m pip install --no-deps -e packages/exitlab packages/oms packages/contracts
# history parquet needs: pip install 'pyarrow>=14'
python -m exitlab measure --data .local_data --out /tmp/exitlab-run
python -m exitlab research --data .local_data --out /tmp/exitlab-run --seed 7 --max-hist-days 24
python -m exitlab list-plans
python -m exitlab playbook --path config/v2/exits/exitlab_playbook.yaml
```

`n_variants_tested = 51` (15 library plans + 36 sweep variants). Seed 7.

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

**Late starts (DATA_INSUFFICIENT for the cash open):** 14 after-hours; 15 is expiry but random only produced 1 ticket; 16 mixed with 258 ticks; several weekdays begin after 09:15.

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

| Set | n | Lots | Side | Moneyness | Sessions | How |
|-----|---|------|------|-----------|----------|-----|
| `random` | 146 | 1 | CE 106 / PE 40 | ATM 50, ITM100 48, ITM200 48 | 15 (1), 16 (1), 17–18, 21–25, 28 (18 each) | Uniform in 09:50–14:45, seed 7 |
| `legacy` | 81 | 25 | CE 41 / PE 40 | ITM200 81 | 17 (3), 18 (7), 21 (13), 22 (6), 23 (14), 24 (11), 25 (18), 28 (9) | `replay_paper_scalp(..., write=False)` on each dual-tape day. 14/15/16: 0 fills |
| `v2_boss` | 60 | 2 | CE 30 / PE 30 | ITM100 60 | 17 (5), 18 (7), 21–25 + 28 (8) | BossSelector proxy: 1m direction + real holds, 30 min spacing, max 8 / session |
| `random_hist` | 48 | 1 | CE 28 / PE 20 | ATM 18, ITM100 18, ITM200 12 | 2025-10-06..09, 13, 14 (8 each) | Same random rule on 1m parquet. Later weeks: DATA_INSUFFICIENT |

Random scenario mix (live): chop 90, mixed 19, trend_up 18, expiry_trend_down 18, expiry_chop 1. Chop dominates.

Legacy replay skip counts (desk did not enter): HOLD_MAJORITY and PATH_KIND_HOLD dominate every day; 14 is after-hours (`n_entries=0`); 15/16 also 0 fills.

## Exit library

Baselines: `hold_to_1515`, `fixed_stop_target` (25% / 40%), `v2_default` (catastrophic ₹30k + flatten 15:15), `legacy_overlay` (constants copied from `paper_scalp.py`, file not edited).

Also run: `atr_stop`, `mfe_trail`, `time_and_stop` (25 min / 20% stop), `scale_out`, `breakeven_move`, `iv_crush`, `stale_and_flat`, plus own ideas:

1. `noise_band` — stop outside the measured TOD MAE band (mult 1.6, target 45%).
2. `theta_budget` — exit when premium bleeds while the index is flat (≥20 min, 12 pt index band).
3. `regime_router` — freeze a plan from the (day) regime at entry: MFE trail on trend, tight fixed on expiry, time+stop on chop, noise-band otherwise.
4. `asymmetric_ce_pe` — tighter PE trail before noon; wider CE trail on trend days.

Pre-trade skips (`SKIP_WIDE_SPREAD`, `SKIP_NEAR_SQUARE`, `SKIP_EVENT_WINDOW`, `SKIP_IV_RICH`) are in the library. This run did not tag those extras on entries, so they did not fire. Event windows: **DATA_INSUFFICIENT**.

`iv_crush` matched `fixed_stop_target` on live random and V2 (no IV drop of 20% on the path). Label: IV-crush as a *trigger* is **DATA_INSUFFICIENT** on this tape; the numbers below are the underlying stop/target.

`v2_default` matched `hold_to_1515` on 1-lot random and 2-lot V2 (₹30k house stop never hit). They differ on 25-lot legacy.

## Results

`n_trade_results = 4545`. `n_variants_tested = 51`. All nets are after `ledger.charges`.

Early vs late on **random 1-lot only** (computed from `trades.json`, same run; cut `2026-09-22`):

| Plan | Early n=74 net ₹ | Late n=72 net ₹ | All n=146 net ₹ |
|------|------------------:|------------------:|------------------:|
| `regime_router` | 123,401.29 | 98,158.30 | 221,559.59 |
| `time_and_stop` | 113,683.00 | 102,093.02 | 215,776.02 |
| `noise_band` | 118,626.52 | 92,455.75 | 211,082.27 |
| `legacy_overlay` | 108,720.00 | 92,663.39 | 201,383.39 |
| `fixed_stop_target` | 123,868.44 | 65,075.25 | 188,943.69 |
| `atr_stop` | 84,735.69 | 101,940.60 | 186,676.29 |
| `theta_budget` | 92,621.24 | 91,070.78 | 183,692.02 |
| `breakeven_move` | 100,467.96 | 77,404.71 | 177,872.67 |
| `asymmetric_ce_pe` | 118,548.66 | 54,808.77 | 173,357.43 |
| `mfe_trail` | 96,166.61 | 71,319.50 | 167,486.11 |
| `stale_and_flat` | 91,213.52 | 67,719.11 | 158,932.63 |
| `hold_to_1515` / `v2_default` | 86,931.73 | 59,849.68 | 146,781.41 |
| `scale_out` | 74,148.07 | 57,124.90 | 131,272.97 |
| `sweep_winner_noise_1.6` | (choose only) | 86,908.92 | — |

On late days `time_and_stop` (₹1,02,093.02) and `regime_router` (₹98,158.30) beat the sweep winner (₹86,908.92). The sweep is honest (chosen on early only) but it is not the best OOS plan.

Why `regime_router` wins on random: chop is 90/146. The router sends chop to time+stop (18 min / 16%), which is the same family as the late winner. It saves vs hold on chop (₹1,35,394 vs ₹1,02,701) and on expiry_trend_down (₹26,479 vs −₹2,338). It gives up some trend_up (₹35,682 vs hold ₹46,542) because it switches to an MFE trail.

Where it fails: V2-boss (₹−5,522, DSR −19.4, CI crosses 0) and legacy 25-lot (₹−4.14 L — still the *least bad* library plan on that set, but still a loss). History week: ₹−17,228 vs hold ₹−1,963.

The tables below are copied from `tables.json`.

## Full result tables (from /tmp/exitlab-run/tables.json)

### Headline: plan × entry set (scenario ALL)

| Plan | Entry set | n | Win | Net ₹ | Avg ₹ | Max DD ₹ | Avg win ₹ | Avg loss ₹ | Bootstrap CI ₹ | DSR | Avg time s | Source |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---|
| `hold_to_1515` | `random` | 146 | 58.9% | 146,781.41 | 1,005.35 | -14,895.71 | 3,220.44 | -2,169.60 | 63,895.81 … 227,661.45 | 4.97 | 12144 | legacy_dual_tape / all |
| `v2_default` | `random` | 146 | 58.9% | 146,781.41 | 1,005.35 | -14,895.71 | 3,220.44 | -2,169.60 | 63,895.81 … 227,661.45 | 4.97 | 12144 | legacy_dual_tape / all |
| `fixed_stop_target` | `random` | 146 | 60.3% | 188,943.69 | 1,294.13 | -7,155.49 | 3,355.52 | -1,833.48 | 116,890.58 … 253,584.19 | 9.24 | 5717 | legacy_dual_tape / all |
| `legacy_overlay` | `random` | 146 | 59.6% | 201,383.39 | 1,379.34 | -3,316.78 | 2,899.46 | -862.20 | 136,736.53 … 255,590.33 | 10.78 | 2142 | legacy_dual_tape / all |
| `noise_band` | `random` | 146 | 46.6% | 211,082.27 | 1,445.77 | -2,203.31 | 3,814.01 | -618.85 | 148,406.74 … 269,030.30 | 11.03 | 3041 | legacy_dual_tape / all |
| `time_and_stop` | `random` | 146 | 57.5% | 215,776.02 | 1,477.92 | -2,272.18 | 3,043.76 | -643.55 | 151,558.07 … 266,630.49 | 11.28 | 1281 | legacy_dual_tape / all |
| `regime_router` | `random` | 146 | 60.3% | 221,559.59 | 1,517.53 | -2,272.18 | 2,985.69 | -710.03 | 156,044.32 … 274,569.41 | 11.22 | 1552 | legacy_dual_tape / all |
| `atr_stop` | `random` | 146 | 26.0% | 186,676.29 | 1,278.60 | -2,133.31 | 5,354.46 | -155.49 | 123,164.60 … 251,173.57 | 9.60 | 3685 | legacy_dual_tape / all |
| `mfe_trail` | `random` | 146 | 71.2% | 167,486.11 | 1,147.17 | -8,154.05 | 2,263.78 | -1,617.79 | 96,177.98 … 229,968.36 | 9.01 | 4597 | legacy_dual_tape / all |
| `theta_budget` | `random` | 146 | 39.0% | 183,692.02 | 1,258.16 | -10,296.07 | 4,109.69 | -568.09 | 105,833.41 … 254,077.37 | 8.67 | 7120 | legacy_dual_tape / all |
| `scale_out` | `random` | 146 | 51.4% | 131,272.97 | 899.13 | -11,444.87 | 3,243.73 | -1,577.56 | 51,918.58 … 206,187.77 | 4.34 | 11330 | legacy_dual_tape / all |
| `breakeven_move` | `random` | 146 | 48.6% | 177,872.67 | 1,218.31 | -7,558.41 | 3,741.42 | -1,170.25 | 106,919.96 … 237,201.77 | 8.93 | 4978 | legacy_dual_tape / all |
| `iv_crush` | `random` | 146 | 60.3% | 188,943.69 | 1,294.13 | -7,155.49 | 3,355.52 | -1,833.48 | 116,890.58 … 253,584.19 | 9.24 | 5717 | legacy_dual_tape / all |
| `stale_and_flat` | `random` | 146 | 58.9% | 158,932.63 | 1,088.58 | -14,081.50 | 3,220.44 | -1,967.08 | 77,765.48 … 235,468.08 | 6.16 | 10372 | legacy_dual_tape / all |
| `asymmetric_ce_pe` | `random` | 146 | 58.2% | 173,357.43 | 1,187.38 | -8,003.57 | 3,262.32 | -1,703.94 | 101,273.61 … 237,505.70 | 8.20 | 5904 | legacy_dual_tape / all |
| `sweep_winner_noise_1.6` | `random` | 72 | 38.9% | 86,908.92 | 1,207.07 | -1,600.97 | 4,083.78 | -623.56 | 47,742.31 … 130,825.59 | 5.07 | 2318 | legacy_dual_tape / oos_live_later |
| `hold_to_1515` | `v2_boss` | 60 | 46.7% | 63.91 | 1.07 | -64,802.43 | 4,934.26 | -4,315.48 | -85,483.01 … 91,351.34 | -17.53 | 10895 | legacy_dual_tape / all |
| `v2_default` | `v2_boss` | 60 | 46.7% | 63.91 | 1.07 | -64,802.43 | 4,934.26 | -4,315.48 | -85,483.01 … 91,351.34 | -17.53 | 10895 | legacy_dual_tape / all |
| `fixed_stop_target` | `v2_boss` | 60 | 51.7% | 81,040.99 | 1,350.68 | -28,789.10 | 6,424.34 | -4,072.88 | -16,804.26 … 170,413.45 | -2.64 | 7689 | legacy_dual_tape / all |
| `legacy_overlay` | `v2_boss` | 60 | 36.7% | -15,804.63 | -263.41 | -30,826.11 | 2,616.41 | -1,930.67 | -53,412.24 … 28,473.94 | -20.56 | 2349 | legacy_dual_tape / all |
| `noise_band` | `v2_boss` | 60 | 16.7% | 7,861.91 | 131.03 | -19,971.68 | 7,229.94 | -1,288.75 | -36,618.01 … 64,318.14 | -15.03 | 2433 | legacy_dual_tape / all |
| `time_and_stop` | `v2_boss` | 60 | 40.0% | -2,031.62 | -33.86 | -13,652.86 | 2,147.61 | -1,488.17 | -37,500.38 … 38,081.69 | -18.30 | 1545 | legacy_dual_tape / all |
| `regime_router` | `v2_boss` | 60 | 31.7% | -5,521.92 | -92.03 | -18,174.67 | 2,562.01 | -1,321.95 | -36,813.41 … 28,424.49 | -19.43 | 1679 | legacy_dual_tape / all |
| `atr_stop` | `v2_boss` | 60 | 0.0% | -15,428.32 | -257.14 | -15,428.32 | — | -257.14 | -16,097.69 … -14,829.14 | -11.38 | 0 | legacy_dual_tape / all |
| `mfe_trail` | `v2_boss` | 60 | 66.7% | -1,460.73 | -24.35 | -20,772.95 | 1,855.05 | -3,783.13 | -52,168.98 … 56,504.18 | -17.96 | 3682 | legacy_dual_tape / all |
| `theta_budget` | `v2_boss` | 60 | 13.3% | -17,861.09 | -297.68 | -28,510.82 | 6,695.34 | -1,373.53 | -70,206.83 … 34,368.32 | -20.47 | 4031 | legacy_dual_tape / all |
| `scale_out` | `v2_boss` | 60 | 46.7% | 29,383.95 | 489.73 | -33,182.77 | 5,159.70 | -3,596.49 | -54,947.83 … 110,996.23 | -10.41 | 8073 | legacy_dual_tape / all |
| `breakeven_move` | `v2_boss` | 60 | 33.3% | 7,005.46 | 116.76 | -36,641.26 | 6,144.59 | -2,897.16 | -71,185.69 … 97,014.43 | -16.06 | 6267 | legacy_dual_tape / all |
| `iv_crush` | `v2_boss` | 60 | 51.7% | 81,040.99 | 1,350.68 | -28,789.10 | 6,424.34 | -4,072.88 | -16,804.26 … 170,413.45 | -2.64 | 7689 | legacy_dual_tape / all |
| `stale_and_flat` | `v2_boss` | 60 | 46.7% | -2,362.46 | -39.37 | -67,948.93 | 4,934.26 | -4,391.30 | -89,476.10 … 90,501.09 | -17.95 | 9634 | legacy_dual_tape / all |
| `asymmetric_ce_pe` | `v2_boss` | 60 | 46.7% | 20,201.04 | 336.68 | -37,947.23 | 4,879.64 | -3,638.41 | -60,157.10 … 108,542.07 | -13.12 | 5898 | legacy_dual_tape / all |
| `hold_to_1515` | `legacy` | 81 | 39.5% | -1,594,358.01 | -19,683.43 | -1,823,980.89 | 45,332.15 | -62,142.59 | -2,906,850.49 … -510,766.03 | -20.88 | 9463 | legacy_dual_tape / all |
| `v2_default` | `legacy` | 81 | 21.0% | -1,527,536.51 | -18,858.48 | -1,751,563.90 | 39,712.07 | -34,416.28 | -2,036,444.68 … -936,181.59 | -17.75 | 4523 | legacy_dual_tape / all |
| `fixed_stop_target` | `legacy` | 81 | 39.5% | -1,301,122.23 | -16,063.24 | -1,526,487.13 | 53,352.85 | -61,396.19 | -2,525,308.58 … -120,375.90 | -22.03 | 8027 | legacy_dual_tape / all |
| `legacy_overlay` | `legacy` | 81 | 27.2% | -967,663.89 | -11,946.47 | -1,032,848.00 | 29,380.58 | -27,356.55 | -1,521,017.78 … -429,307.30 | -19.64 | 2279 | legacy_dual_tape / all |
| `noise_band` | `legacy` | 81 | 13.6% | -769,389.03 | -9,498.63 | -841,323.87 | 36,481.02 | -16,724.00 | -1,079,470.89 … -410,506.63 | -18.69 | 2135 | legacy_dual_tape / all |
| `time_and_stop` | `legacy` | 81 | 37.0% | -547,272.80 | -6,756.45 | -690,330.03 | 19,693.05 | -22,314.99 | -1,035,901.17 … -82,503.23 | -21.85 | 1463 | legacy_dual_tape / all |
| `regime_router` | `legacy` | 81 | 37.0% | -414,359.63 | -5,115.55 | -489,051.67 | 25,106.87 | -22,893.45 | -941,572.49 … 173,106.34 | -23.55 | 1460 | legacy_dual_tape / all |
| `atr_stop` | `legacy` | 81 | 39.5% | -1,594,358.01 | -19,683.43 | -1,823,980.89 | 45,332.15 | -62,142.59 | -2,906,850.49 … -510,766.03 | -20.88 | 9463 | legacy_dual_tape / all |
| `mfe_trail` | `legacy` | 81 | 66.7% | -305,774.70 | -3,775.00 | -537,682.29 | 16,146.45 | -43,617.88 | -918,690.16 … 289,564.40 | -24.03 | 2850 | legacy_dual_tape / all |
| `theta_budget` | `legacy` | 81 | 13.6% | -779,120.37 | -9,618.77 | -845,196.61 | 35,974.76 | -16,783.47 | -1,209,111.21 … -398,445.10 | -19.29 | 2572 | legacy_dual_tape / all |
| `scale_out` | `legacy` | 81 | 37.0% | -1,255,106.89 | -15,495.15 | -1,520,734.08 | 45,522.12 | -51,387.66 | -2,314,200.90 … -278,262.92 | -21.35 | 7899 | legacy_dual_tape / all |
| `breakeven_move` | `legacy` | 81 | 33.3% | -1,131,068.10 | -13,963.80 | -1,260,215.58 | 50,078.34 | -45,984.88 | -2,206,344.48 … -158,896.27 | -21.80 | 7527 | legacy_dual_tape / all |
| `iv_crush` | `legacy` | 81 | 39.5% | -1,301,122.23 | -16,063.24 | -1,526,487.13 | 53,352.85 | -61,396.19 | -2,525,308.58 … -120,375.90 | -22.03 | 8027 | legacy_dual_tape / all |
| `stale_and_flat` | `legacy` | 81 | 39.5% | -1,604,819.15 | -19,812.58 | -1,834,442.03 | 45,332.15 | -62,356.08 | -2,862,859.54 … -556,620.27 | -20.82 | 8505 | legacy_dual_tape / all |
| `asymmetric_ce_pe` | `legacy` | 81 | 44.4% | -1,316,530.00 | -16,253.46 | -1,336,625.86 | 27,997.43 | -51,654.17 | -2,154,003.09 … -395,405.94 | -20.49 | 5973 | legacy_dual_tape / all |
| `hold_to_1515` | `random_hist` | 48 | 43.8% | -1,963.01 | -40.90 | -33,588.99 | 2,710.23 | -2,180.66 | -43,413.69 … 46,371.40 | -16.26 | 10486 | opt1m_sample_train / all |
| `v2_default` | `random_hist` | 48 | 43.8% | -1,963.01 | -40.90 | -33,588.99 | 2,710.23 | -2,180.66 | -43,413.69 … 46,371.40 | -16.26 | 10486 | opt1m_sample_train / all |
| `fixed_stop_target` | `random_hist` | 48 | 43.8% | 3,295.13 | 68.65 | -27,544.32 | 2,794.21 | -2,051.23 | -31,343.97 … 50,731.16 | -14.46 | 6382 | opt1m_sample_train / all |
| `legacy_overlay` | `random_hist` | 48 | 22.9% | -1,846.27 | -38.46 | -6,497.47 | 1,339.75 | -448.20 | -13,029.22 … 11,909.92 | -17.26 | 766 | opt1m_sample_train / all |
| `regime_router` | `random_hist` | 48 | 35.4% | -17,228.22 | -358.92 | -24,599.67 | 1,053.88 | -1,133.68 | -37,748.32 … 1,693.22 | -17.28 | 1926 | opt1m_sample_train / all |

### Plan × entry set × scenario (all labelled cells from this run)

| Plan | Entry set | Scenario | Split | n | Win | Net ₹ | Avg ₹ | Max DD ₹ | CI ₹ | DSR |
|---|---|---|---|---:|---:|---:|---:|---:|---|---:|
| `hold_to_1515` | `random` | `chop` | all | 90 | 62.2% | 102,700.56 | 1,141.12 | -14,707.40 | 43,165.55 … 168,707.52 | 3.36 |
| `hold_to_1515` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,188.90 | 1,188.90 | 0.00 | 1,188.90 … 1,188.90 | — |
| `hold_to_1515` | `random` | `expiry_trend_down` | all | 18 | 22.2% | -2,338.12 | -129.90 | -14,895.71 | -34,667.14 … 35,021.74 | -9.88 |
| `hold_to_1515` | `random` | `mixed` | all | 19 | 47.4% | -1,312.19 | -69.06 | -10,307.01 | -35,764.75 … 32,214.55 | -9.99 |
| `hold_to_1515` | `random` | `trend_up` | all | 18 | 88.9% | 46,542.26 | 2,585.68 | -1,579.12 | 25,317.80 … 67,214.91 | 2.24 |
| `v2_default` | `random` | `chop` | all | 90 | 62.2% | 102,700.56 | 1,141.12 | -14,707.40 | 43,165.55 … 168,707.52 | 3.36 |
| `v2_default` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,188.90 | 1,188.90 | 0.00 | 1,188.90 … 1,188.90 | — |
| `v2_default` | `random` | `expiry_trend_down` | all | 18 | 22.2% | -2,338.12 | -129.90 | -14,895.71 | -34,667.14 … 35,021.74 | -9.88 |
| `v2_default` | `random` | `mixed` | all | 19 | 47.4% | -1,312.19 | -69.06 | -10,307.01 | -35,764.75 … 32,214.55 | -9.99 |
| `v2_default` | `random` | `trend_up` | all | 18 | 88.9% | 46,542.26 | 2,585.68 | -1,579.12 | 25,317.80 … 67,214.91 | 2.24 |
| `fixed_stop_target` | `random` | `chop` | all | 90 | 60.0% | 103,641.16 | 1,151.57 | -6,198.26 | 49,228.12 … 165,680.65 | 4.84 |
| `fixed_stop_target` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `fixed_stop_target` | `random` | `expiry_trend_down` | all | 18 | 44.4% | 24,614.29 | 1,367.46 | -2,922.19 | -3,171.84 … 50,068.13 | -1.46 |
| `fixed_stop_target` | `random` | `mixed` | all | 19 | 47.4% | 10,530.73 | 554.25 | -7,155.49 | -20,090.66 … 38,950.16 | -6.09 |
| `fixed_stop_target` | `random` | `trend_up` | all | 18 | 88.9% | 48,926.43 | 2,718.14 | -1,419.22 | 31,520.73 … 65,298.27 | 3.23 |
| `legacy_overlay` | `random` | `chop` | all | 90 | 61.1% | 118,176.41 | 1,313.07 | -3,316.78 | 71,596.70 … 167,747.90 | 6.89 |
| `legacy_overlay` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,415.97 | 1,415.97 | 0.00 | 1,415.97 … 1,415.97 | — |
| `legacy_overlay` | `random` | `expiry_trend_down` | all | 18 | 38.9% | 27,848.31 | 1,547.13 | -1,504.68 | 4,133.76 … 52,225.72 | -0.29 |
| `legacy_overlay` | `random` | `mixed` | all | 19 | 52.6% | 21,419.95 | 1,127.37 | -2,385.21 | -729.07 … 43,187.52 | -0.99 |
| `legacy_overlay` | `random` | `trend_up` | all | 18 | 77.8% | 32,522.75 | 1,806.82 | -1,344.60 | 11,818.16 … 50,598.75 | 1.39 |
| `noise_band` | `random` | `chop` | all | 90 | 44.4% | 112,931.29 | 1,254.79 | -2,203.31 | 71,090.63 … 163,739.17 | 6.52 |
| `noise_band` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `noise_band` | `random` | `expiry_trend_down` | all | 18 | 38.9% | 31,623.99 | 1,756.89 | -1,444.50 | 8,345.18 … 55,340.58 | 0.32 |
| `noise_band` | `random` | `mixed` | all | 19 | 36.8% | 22,204.98 | 1,168.68 | -1,723.23 | 790.92 … 43,315.88 | -0.72 |
| `noise_band` | `random` | `trend_up` | all | 18 | 72.2% | 43,090.93 | 2,393.94 | -1,266.08 | 23,386.54 … 60,633.75 | 2.61 |
| `time_and_stop` | `random` | `chop` | all | 90 | 58.9% | 131,887.76 | 1,465.42 | -2,032.25 | 85,654.80 … 178,829.13 | 7.74 |
| `time_and_stop` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,331.63 | 1,331.63 | 0.00 | 1,331.63 … 1,331.63 | — |
| `time_and_stop` | `random` | `expiry_trend_down` | all | 18 | 50.0% | 27,948.89 | 1,552.72 | -2,272.18 | 3,994.92 … 51,609.40 | -0.32 |
| `time_and_stop` | `random` | `mixed` | all | 19 | 47.4% | 25,539.57 | 1,344.19 | -1,885.66 | 3,756.80 … 47,655.36 | -0.11 |
| `time_and_stop` | `random` | `trend_up` | all | 18 | 66.7% | 29,068.17 | 1,614.90 | -1,412.73 | 8,019.77 … 47,940.94 | 0.70 |
| `regime_router` | `random` | `chop` | all | 90 | 62.2% | 135,394.27 | 1,504.38 | -2,243.92 | 91,667.86 … 181,903.72 | 7.83 |
| `regime_router` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `regime_router` | `random` | `expiry_trend_down` | all | 18 | 44.4% | 26,479.45 | 1,471.08 | -2,272.18 | 1,285.14 … 51,255.82 | -0.80 |
| `regime_router` | `random` | `mixed` | all | 19 | 36.8% | 22,772.63 | 1,198.56 | -1,580.50 | 1,286.66 … 44,162.57 | -0.54 |
| `regime_router` | `random` | `trend_up` | all | 18 | 88.9% | 35,682.16 | 1,982.34 | -1,419.22 | 12,215.51 … 59,418.32 | 0.84 |
| `atr_stop` | `random` | `chop` | all | 90 | 25.6% | 116,684.31 | 1,296.49 | -1,525.76 | 70,053.85 … 176,441.18 | 5.83 |
| `atr_stop` | `random` | `expiry_chop` | all | 1 | 0.0% | -72.92 | -72.92 | -72.92 | -72.92 … -72.92 | — |
| `atr_stop` | `random` | `expiry_trend_down` | all | 18 | 16.7% | 14,286.12 | 793.67 | -2,133.31 | -2,562.07 … 32,215.47 | -2.17 |
| `atr_stop` | `random` | `mixed` | all | 19 | 31.6% | 24,553.50 | 1,292.29 | -435.44 | 5,246.87 … 48,184.79 | -0.80 |
| `atr_stop` | `random` | `trend_up` | all | 18 | 33.3% | 31,225.28 | 1,734.74 | -237.80 | 8,456.35 … 56,412.27 | 0.15 |
| `mfe_trail` | `random` | `chop` | all | 90 | 71.1% | 92,959.46 | 1,032.88 | -8,154.05 | 43,475.48 … 147,795.73 | 4.24 |
| `mfe_trail` | `random` | `expiry_chop` | all | 1 | 100.0% | 17.91 | 17.91 | 0.00 | 17.91 … 17.91 | — |
| `mfe_trail` | `random` | `expiry_trend_down` | all | 18 | 55.6% | 14,607.27 | 811.51 | -2,272.18 | -944.21 … 30,376.37 | -1.85 |
| `mfe_trail` | `random` | `mixed` | all | 19 | 68.4% | 21,549.71 | 1,134.20 | -4,451.48 | -419.05 … 42,390.87 | -0.90 |
| `mfe_trail` | `random` | `trend_up` | all | 18 | 88.9% | 38,351.76 | 2,130.65 | -1,419.22 | 14,929.57 … 62,280.64 | 1.19 |
| `theta_budget` | `random` | `chop` | all | 90 | 40.0% | 111,251.03 | 1,236.12 | -9,131.37 | 62,812.90 … 171,987.67 | 5.17 |
| `theta_budget` | `random` | `expiry_chop` | all | 1 | 0.0% | -95.63 | -95.63 | -95.63 | -95.63 … -95.63 | — |
| `theta_budget` | `random` | `expiry_trend_down` | all | 18 | 22.2% | 14,432.07 | 801.78 | -10,296.07 | -15,911.14 … 47,376.46 | -5.07 |
| `theta_budget` | `random` | `mixed` | all | 19 | 36.8% | 22,717.54 | 1,195.66 | -1,269.10 | 2,141.89 … 47,338.15 | -1.34 |
| `theta_budget` | `random` | `trend_up` | all | 18 | 55.6% | 35,387.01 | 1,965.95 | -1,579.12 | 11,774.77 … 59,630.07 | 0.72 |
| `scale_out` | `random` | `chop` | all | 90 | 50.0% | 62,542.88 | 694.92 | -11,444.87 | 6,098.76 … 134,077.95 | -1.30 |
| `scale_out` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,188.90 | 1,188.90 | 0.00 | 1,188.90 … 1,188.90 | — |
| `scale_out` | `random` | `expiry_trend_down` | all | 18 | 22.2% | 13,647.15 | 758.17 | -11,418.38 | -18,223.35 … 52,086.74 | -5.82 |
| `scale_out` | `random` | `mixed` | all | 19 | 47.4% | 9,025.60 | 475.03 | -7,098.93 | -21,398.17 … 40,115.27 | -6.80 |
| `scale_out` | `random` | `trend_up` | all | 18 | 88.9% | 44,868.44 | 2,492.69 | -1,419.22 | 24,930.76 … 65,680.74 | 2.26 |
| `breakeven_move` | `random` | `chop` | all | 90 | 43.3% | 85,693.40 | 952.15 | -7,558.41 | 35,554.53 … 144,013.76 | 3.08 |
| `breakeven_move` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `breakeven_move` | `random` | `expiry_trend_down` | all | 18 | 38.9% | 25,691.23 | 1,427.29 | -2,511.68 | -1,712.96 … 52,536.91 | -1.22 |
| `breakeven_move` | `random` | `mixed` | all | 19 | 47.4% | 20,469.56 | 1,077.35 | -4,756.41 | -8,646.75 … 45,264.24 | -1.98 |
| `breakeven_move` | `random` | `trend_up` | all | 18 | 83.3% | 44,787.40 | 2,488.19 | -1,419.22 | 27,307.73 … 60,445.88 | 2.86 |
| `iv_crush` | `random` | `chop` | all | 90 | 60.0% | 103,641.16 | 1,151.57 | -6,198.26 | 49,228.12 … 165,680.65 | 4.84 |
| `iv_crush` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `iv_crush` | `random` | `expiry_trend_down` | all | 18 | 44.4% | 24,614.29 | 1,367.46 | -2,922.19 | -3,171.84 … 50,068.13 | -1.46 |
| `iv_crush` | `random` | `mixed` | all | 19 | 47.4% | 10,530.73 | 554.25 | -7,155.49 | -20,090.66 … 38,950.16 | -6.09 |
| `iv_crush` | `random` | `trend_up` | all | 18 | 88.9% | 48,926.43 | 2,718.14 | -1,419.22 | 31,520.73 … 65,298.27 | 3.23 |
| `stale_and_flat` | `random` | `chop` | all | 90 | 62.2% | 103,031.50 | 1,144.79 | -13,981.48 | 43,372.30 … 171,725.39 | 3.39 |
| `stale_and_flat` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,188.90 | 1,188.90 | 0.00 | 1,188.90 … 1,188.90 | — |
| `stale_and_flat` | `random` | `expiry_trend_down` | all | 18 | 22.2% | 5,122.56 | 284.59 | -14,081.50 | -26,263.80 … 39,835.47 | -8.04 |
| `stale_and_flat` | `random` | `mixed` | all | 19 | 47.4% | 2,995.49 | 157.66 | -9,311.19 | -29,929.25 … 35,134.88 | -8.86 |
| `stale_and_flat` | `random` | `trend_up` | all | 18 | 88.9% | 46,594.18 | 2,588.57 | -1,527.20 | 25,473.56 … 67,266.83 | 2.25 |
| `asymmetric_ce_pe` | `random` | `chop` | all | 90 | 57.8% | 91,045.68 | 1,011.62 | -8,003.57 | 39,285.96 … 152,191.36 | 3.95 |
| `asymmetric_ce_pe` | `random` | `expiry_chop` | all | 1 | 100.0% | 1,231.08 | 1,231.08 | 0.00 | 1,231.08 … 1,231.08 | — |
| `asymmetric_ce_pe` | `random` | `expiry_trend_down` | all | 18 | 38.9% | 28,344.62 | 1,574.70 | -3,138.82 | -2,682.46 … 66,741.00 | -1.74 |
| `asymmetric_ce_pe` | `random` | `mixed` | all | 19 | 47.4% | 12,447.75 | 655.14 | -5,586.54 | -16,305.73 … 39,515.29 | -5.12 |
| `asymmetric_ce_pe` | `random` | `trend_up` | all | 18 | 88.9% | 40,288.30 | 2,238.24 | -1,419.22 | 14,952.76 … 64,775.13 | 1.18 |
| `hold_to_1515` | `v2_boss` | `chop` | all | 36 | 50.0% | 24,185.66 | 671.82 | -40,291.64 | -41,328.26 … 93,146.31 | -8.57 |
| `hold_to_1515` | `v2_boss` | `expiry_trend_down` | all | 8 | 37.5% | -13,830.57 | -1,728.82 | -13,830.57 | -41,745.62 … 10,609.99 | -7.10 |
| `hold_to_1515` | `v2_boss` | `mixed` | oos | 8 | 62.5% | -2,345.78 | -293.22 | -23,411.09 | -37,244.43 … 25,826.38 | -6.36 |
| `hold_to_1515` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -7,945.40 | -993.18 | -18,445.98 | -28,094.14 … 15,068.56 | -7.07 |
| `v2_default` | `v2_boss` | `chop` | all | 36 | 50.0% | 24,185.66 | 671.82 | -40,291.64 | -41,328.26 … 93,146.31 | -8.57 |
| `v2_default` | `v2_boss` | `expiry_trend_down` | all | 8 | 37.5% | -13,830.57 | -1,728.82 | -13,830.57 | -41,745.62 … 10,609.99 | -7.10 |
| `v2_default` | `v2_boss` | `mixed` | oos | 8 | 62.5% | -2,345.78 | -293.22 | -23,411.09 | -37,244.43 … 25,826.38 | -6.36 |
| `v2_default` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -7,945.40 | -993.18 | -18,445.98 | -28,094.14 … 15,068.56 | -7.07 |
| `fixed_stop_target` | `v2_boss` | `chop` | all | 36 | 50.0% | 49,370.14 | 1,371.39 | -37,028.55 | -22,191.74 … 128,598.11 | -4.32 |
| `fixed_stop_target` | `v2_boss` | `expiry_trend_down` | all | 8 | 75.0% | 25,885.98 | 3,235.75 | -4,520.72 | -3,455.39 … 48,328.76 | -0.57 |
| `fixed_stop_target` | `v2_boss` | `mixed` | oos | 8 | 62.5% | 14,443.90 | 1,805.49 | -19,920.81 | -26,846.80 … 44,010.58 | -3.67 |
| `fixed_stop_target` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -8,659.03 | -1,082.38 | -19,717.53 | -30,477.19 … 16,075.52 | -7.07 |
| `legacy_overlay` | `v2_boss` | `chop` | all | 36 | 36.1% | -2,594.82 | -72.08 | -15,801.17 | -37,290.10 … 32,093.74 | -14.31 |
| `legacy_overlay` | `v2_boss` | `expiry_trend_down` | all | 8 | 37.5% | -4,112.30 | -514.04 | -9,091.29 | -20,065.39 … 15,147.04 | -6.83 |
| `legacy_overlay` | `v2_boss` | `mixed` | oos | 8 | 37.5% | -3,331.90 | -416.49 | -9,897.90 | -16,371.98 … 11,558.83 | -6.88 |
| `legacy_overlay` | `v2_boss` | `trend_up` | all | 8 | 37.5% | -5,765.61 | -720.70 | -9,512.66 | -15,354.74 … 4,865.10 | -7.09 |
| `noise_band` | `v2_boss` | `chop` | all | 36 | 16.7% | 4,606.39 | 127.96 | -18,747.17 | -34,816.10 … 44,413.16 | -12.09 |
| `noise_band` | `v2_boss` | `expiry_trend_down` | all | 8 | 25.0% | 3,186.14 | 398.27 | -8,452.41 | -18,013.83 … 28,057.79 | -5.31 |
| `noise_band` | `v2_boss` | `mixed` | oos | 8 | 12.5% | -16.77 | -2.10 | -8,040.06 | -10,044.03 … 18,708.41 | -6.05 |
| `noise_band` | `v2_boss` | `trend_up` | all | 8 | 12.5% | 86.15 | 10.77 | -7,855.27 | -10,122.05 … 19,121.27 | -6.02 |
| `time_and_stop` | `v2_boss` | `chop` | all | 36 | 41.7% | 4,249.50 | 118.04 | -13,394.81 | -25,089.80 … 33,469.69 | -11.69 |
| `time_and_stop` | `v2_boss` | `expiry_trend_down` | all | 8 | 37.5% | 5,255.69 | 656.96 | -5,675.39 | -13,336.92 … 26,794.28 | -4.49 |
| `time_and_stop` | `v2_boss` | `mixed` | oos | 8 | 50.0% | -6,497.78 | -812.22 | -7,238.01 | -14,255.02 … 301.48 | -6.77 |
| `time_and_stop` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -5,039.03 | -629.88 | -6,226.94 | -9,200.45 … 750.56 | -6.66 |
| `regime_router` | `v2_boss` | `chop` | all | 36 | 27.8% | -4,722.73 | -131.19 | -17,692.10 | -28,051.96 … 22,007.69 | -15.22 |
| `regime_router` | `v2_boss` | `expiry_trend_down` | all | 8 | 62.5% | 14,117.61 | 1,764.70 | -3,411.35 | -7,828.50 … 33,970.10 | -2.12 |
| `regime_router` | `v2_boss` | `mixed` | oos | 8 | 0.0% | -8,126.15 | -1,015.77 | -8,126.15 | -9,075.42 … -7,132.95 | -4.30 |
| `regime_router` | `v2_boss` | `trend_up` | all | 8 | 50.0% | -6,790.65 | -848.83 | -8,150.30 | -16,099.69 … 2,282.63 | -6.96 |
| `atr_stop` | `v2_boss` | `chop` | all | 36 | 0.0% | -10,159.22 | -282.20 | -10,159.22 | -10,461.51 … -9,833.56 | -8.67 |
| `atr_stop` | `v2_boss` | `expiry_trend_down` | all | 8 | 0.0% | -1,569.20 | -196.15 | -1,569.20 | -1,685.46 … -1,453.84 | -4.10 |
| `atr_stop` | `v2_boss` | `mixed` | oos | 8 | 0.0% | -1,924.07 | -240.51 | -1,924.07 | -2,125.01 … -1,752.13 | -4.19 |
| `atr_stop` | `v2_boss` | `trend_up` | all | 8 | 0.0% | -1,775.83 | -221.98 | -1,775.83 | -1,858.19 … -1,700.33 | -3.94 |
| `mfe_trail` | `v2_boss` | `chop` | all | 36 | 69.4% | 2,160.51 | 60.01 | -18,699.52 | -37,554.63 … 44,472.92 | -12.90 |
| `mfe_trail` | `v2_boss` | `expiry_trend_down` | all | 8 | 75.0% | 3,847.88 | 480.99 | -3,411.35 | -10,403.69 … 15,330.84 | -4.32 |
| `mfe_trail` | `v2_boss` | `mixed` | oos | 8 | 62.5% | -1,547.81 | -193.48 | -11,675.15 | -22,929.47 … 18,072.34 | -6.39 |
| `mfe_trail` | `v2_boss` | `trend_up` | all | 8 | 50.0% | -5,921.31 | -740.16 | -8,020.55 | -15,722.98 … 3,534.41 | -7.07 |
| `theta_budget` | `v2_boss` | `chop` | all | 36 | 16.7% | -7,343.64 | -203.99 | -20,222.48 | -53,453.17 … 41,390.72 | -14.91 |
| `theta_budget` | `v2_boss` | `expiry_trend_down` | all | 8 | 12.5% | -2,866.69 | -358.34 | -9,064.79 | -13,962.15 … 13,388.80 | -6.76 |
| `theta_budget` | `v2_boss` | `mixed` | oos | 8 | 0.0% | -8,288.34 | -1,036.04 | -8,288.34 | -12,961.87 … -4,560.14 | -5.75 |
| `theta_budget` | `v2_boss` | `trend_up` | all | 8 | 12.5% | 637.58 | 79.70 | -5,480.85 | -7,815.52 … 15,540.15 | -5.79 |
| `scale_out` | `v2_boss` | `chop` | all | 36 | 47.2% | 20,081.95 | 557.83 | -36,911.77 | -42,049.85 … 83,413.90 | -9.09 |
| `scale_out` | `v2_boss` | `expiry_trend_down` | all | 8 | 50.0% | 12,204.08 | 1,525.51 | -4,048.20 | -9,846.95 … 37,976.31 | -2.87 |
| `scale_out` | `v2_boss` | `mixed` | oos | 8 | 62.5% | 5,573.00 | 696.62 | -16,858.69 | -23,602.21 … 30,113.49 | -4.89 |
| `scale_out` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -8,475.08 | -1,059.38 | -17,777.76 | -26,997.73 … 11,977.28 | -7.10 |
| `breakeven_move` | `v2_boss` | `chop` | all | 36 | 33.3% | -2,289.93 | -63.61 | -37,119.25 | -61,031.88 … 63,233.47 | -13.91 |
| `breakeven_move` | `v2_boss` | `expiry_trend_down` | all | 8 | 50.0% | 14,454.94 | 1,806.87 | -9,564.88 | -14,325.73 … 45,093.58 | -3.11 |
| `breakeven_move` | `v2_boss` | `mixed` | oos | 8 | 37.5% | 956.38 | 119.55 | -12,453.65 | -23,165.74 … 25,939.32 | -5.85 |
| `breakeven_move` | `v2_boss` | `trend_up` | all | 8 | 12.5% | -6,115.93 | -764.49 | -14,057.35 | -21,043.21 … 18,498.75 | -7.00 |
| `iv_crush` | `v2_boss` | `chop` | all | 36 | 50.0% | 49,370.14 | 1,371.39 | -37,028.55 | -22,191.74 … 128,598.11 | -4.32 |
| `iv_crush` | `v2_boss` | `expiry_trend_down` | all | 8 | 75.0% | 25,885.98 | 3,235.75 | -4,520.72 | -3,455.39 … 48,328.76 | -0.57 |
| `iv_crush` | `v2_boss` | `mixed` | oos | 8 | 62.5% | 14,443.90 | 1,805.49 | -19,920.81 | -26,846.80 … 44,010.58 | -3.67 |
| `iv_crush` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -8,659.03 | -1,082.38 | -19,717.53 | -30,477.19 … 16,075.52 | -7.07 |
| `stale_and_flat` | `v2_boss` | `chop` | all | 36 | 50.0% | 23,887.22 | 663.53 | -41,997.88 | -40,999.41 … 91,446.57 | -8.64 |
| `stale_and_flat` | `v2_boss` | `expiry_trend_down` | all | 8 | 37.5% | -16,568.33 | -2,071.04 | -19,630.42 | -37,592.24 … 6,803.25 | -6.96 |
| `stale_and_flat` | `v2_boss` | `mixed` | oos | 8 | 62.5% | -1,028.81 | -128.60 | -22,094.12 | -35,674.20 … 26,284.94 | -6.20 |
| `stale_and_flat` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -8,652.54 | -1,081.57 | -19,153.12 | -28,801.28 … 14,508.95 | -7.08 |
| `asymmetric_ce_pe` | `v2_boss` | `chop` | all | 36 | 47.2% | 26,780.62 | 743.91 | -32,091.56 | -35,404.78 … 102,123.78 | -8.23 |
| `asymmetric_ce_pe` | `v2_boss` | `expiry_trend_down` | all | 8 | 62.5% | 10,542.97 | 1,317.87 | -3,833.04 | -11,903.44 … 30,564.63 | -2.95 |
| `asymmetric_ce_pe` | `v2_boss` | `mixed` | oos | 8 | 50.0% | -723.91 | -90.49 | -17,107.72 | -27,423.98 … 25,139.00 | -6.16 |
| `asymmetric_ce_pe` | `v2_boss` | `trend_up` | all | 8 | 25.0% | -16,398.64 | -2,049.83 | -17,330.12 | -26,550.09 … -6,659.74 | -5.97 |
| `hold_to_1515` | `legacy` | `chop` | all | 53 | 35.8% | -1,215,730.49 | -22,938.31 | -1,257,097.75 | -2,117,221.48 … -118,231.99 | -17.20 |
| `hold_to_1515` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -302,821.17 | -50,470.19 | -302,821.17 | -623,085.51 … -20,111.42 | -5.63 |
| `hold_to_1515` | `legacy` | `mixed` | oos | 9 | 33.3% | -256,960.89 | -28,551.21 | -332,278.70 | -666,200.00 … 201,294.03 | -7.53 |
| `hold_to_1515` | `legacy` | `trend_up` | all | 13 | 61.5% | 181,154.54 | 13,934.96 | -128,745.74 | -147,912.45 … 465,210.33 | -3.22 |
| `v2_default` | `legacy` | `chop` | all | 53 | 13.2% | -1,397,137.64 | -26,361.09 | -1,397,137.64 | -1,742,649.34 … -1,005,060.73 | -13.16 |
| `v2_default` | `legacy` | `expiry_trend_down` | all | 6 | 0.0% | -257,003.06 | -42,833.84 | -257,003.06 | -343,670.19 … -206,413.48 | -4.24 |
| `v2_default` | `legacy` | `mixed` | oos | 9 | 22.2% | -115,857.39 | -12,873.04 | -190,202.06 | -334,058.02 … 139,157.72 | -7.59 |
| `v2_default` | `legacy` | `trend_up` | all | 13 | 61.5% | 242,461.58 | 18,650.89 | -67,438.70 | -7,579.62 … 487,864.60 | -1.02 |
| `fixed_stop_target` | `legacy` | `chop` | all | 53 | 35.8% | -1,066,679.82 | -20,126.03 | -1,151,432.35 | -1,893,840.43 … 10,961.39 | -17.50 |
| `fixed_stop_target` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -84,272.94 | -14,045.49 | -151,624.07 | -575,151.26 … 421,789.92 | -5.63 |
| `fixed_stop_target` | `legacy` | `mixed` | oos | 9 | 33.3% | -316,402.73 | -35,155.86 | -391,720.54 | -761,533.36 … 181,666.66 | -7.46 |
| `fixed_stop_target` | `legacy` | `trend_up` | all | 13 | 61.5% | 166,233.26 | 12,787.17 | -143,667.02 | -176,387.96 … 465,210.33 | -3.80 |
| `legacy_overlay` | `legacy` | `chop` | all | 53 | 20.8% | -875,135.82 | -16,512.00 | -910,460.29 | -1,305,427.16 … -428,965.61 | -15.55 |
| `legacy_overlay` | `legacy` | `expiry_trend_down` | all | 6 | 16.7% | -142,822.76 | -23,803.79 | -142,822.76 | -265,523.34 … -31,092.35 | -5.35 |
| `legacy_overlay` | `legacy` | `mixed` | oos | 9 | 33.3% | -51,549.91 | -5,727.77 | -77,805.83 | -194,197.85 … 105,032.77 | -7.54 |
| `legacy_overlay` | `legacy` | `trend_up` | all | 13 | 53.8% | 101,844.60 | 7,834.20 | -61,549.33 | -78,110.45 … 310,474.17 | -3.48 |
| `noise_band` | `legacy` | `chop` | all | 53 | 9.4% | -582,954.19 | -10,999.14 | -590,165.63 | -770,573.03 … -345,831.59 | -14.52 |
| `noise_band` | `legacy` | `expiry_trend_down` | all | 6 | 0.0% | -177,855.37 | -29,642.56 | -177,855.37 | -298,469.07 … -95,003.36 | -5.07 |
| `noise_band` | `legacy` | `mixed` | oos | 9 | 11.1% | -68,498.53 | -7,610.95 | -89,503.26 | -139,812.92 … 35,783.74 | -7.45 |
| `noise_band` | `legacy` | `trend_up` | all | 13 | 38.5% | 59,919.06 | 4,609.16 | -77,257.02 | -106,308.03 … 284,070.25 | -5.49 |
| `time_and_stop` | `legacy` | `chop` | all | 53 | 32.1% | -476,883.34 | -8,997.80 | -577,488.46 | -865,498.13 … -59,191.30 | -17.58 |
| `time_and_stop` | `legacy` | `expiry_trend_down` | all | 6 | 50.0% | -85,246.06 | -14,207.68 | -86,730.54 | -235,148.13 … 32,997.39 | -5.94 |
| `time_and_stop` | `legacy` | `mixed` | oos | 9 | 33.3% | 7,567.59 | 840.84 | -40,908.06 | -125,054.64 … 179,678.21 | -6.19 |
| `time_and_stop` | `legacy` | `trend_up` | all | 13 | 53.8% | 7,289.01 | 560.69 | -43,951.94 | -127,966.82 … 154,313.05 | -7.54 |
| `regime_router` | `legacy` | `chop` | all | 53 | 34.0% | -286,555.77 | -5,406.71 | -347,495.13 | -622,961.00 … 94,764.30 | -18.90 |
| `regime_router` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -44,212.49 | -7,368.75 | -140,757.46 | -410,426.87 … 338,816.25 | -5.49 |
| `regime_router` | `legacy` | `mixed` | oos | 9 | 11.1% | -67,444.29 | -7,493.81 | -88,449.02 | -138,648.48 … 36,481.26 | -7.46 |
| `regime_router` | `legacy` | `trend_up` | all | 13 | 69.2% | -16,147.08 | -1,242.08 | -73,681.72 | -203,238.41 … 144,440.94 | -8.44 |
| `atr_stop` | `legacy` | `chop` | all | 53 | 35.8% | -1,215,730.49 | -22,938.31 | -1,257,097.75 | -2,117,221.48 … -118,231.99 | -17.20 |
| `atr_stop` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -302,821.17 | -50,470.19 | -302,821.17 | -623,085.51 … -20,111.42 | -5.63 |
| `atr_stop` | `legacy` | `mixed` | oos | 9 | 33.3% | -256,960.89 | -28,551.21 | -332,278.70 | -666,200.00 … 201,294.03 | -7.53 |
| `atr_stop` | `legacy` | `trend_up` | all | 13 | 61.5% | 181,154.54 | 13,934.96 | -128,745.74 | -147,912.45 … 465,210.33 | -3.22 |
| `mfe_trail` | `legacy` | `chop` | all | 53 | 62.3% | -361,973.04 | -6,829.68 | -409,717.23 | -932,778.90 … 226,667.84 | -19.14 |
| `mfe_trail` | `legacy` | `expiry_trend_down` | all | 6 | 66.7% | -109,574.25 | -18,262.38 | -117,446.41 | -330,927.26 … 41,604.54 | -5.95 |
| `mfe_trail` | `legacy` | `mixed` | oos | 9 | 88.9% | 102,204.32 | 11,356.04 | -32,872.58 | -52,466.37 … 243,869.33 | -1.90 |
| `mfe_trail` | `legacy` | `trend_up` | all | 13 | 69.2% | 63,568.27 | 4,889.87 | -73,681.72 | -156,452.76 … 257,763.11 | -5.36 |
| `theta_budget` | `legacy` | `chop` | all | 53 | 11.3% | -639,314.58 | -12,062.54 | -650,742.88 | -943,599.15 … -307,095.48 | -15.39 |
| `theta_budget` | `legacy` | `expiry_trend_down` | all | 6 | 0.0% | -134,388.99 | -22,398.16 | -134,388.99 | -222,923.88 … -52,200.59 | -5.15 |
| `theta_budget` | `legacy` | `mixed` | oos | 9 | 11.1% | -60,064.74 | -6,673.86 | -60,064.74 | -153,660.87 … 52,236.21 | -7.57 |
| `theta_budget` | `legacy` | `trend_up` | all | 13 | 30.8% | 54,647.94 | 4,203.69 | -52,685.57 | -99,524.20 … 269,240.46 | -5.62 |
| `scale_out` | `legacy` | `chop` | all | 53 | 32.1% | -1,057,128.54 | -19,945.82 | -1,163,020.98 | -1,854,052.62 … -223,948.33 | -16.97 |
| `scale_out` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -168,364.25 | -28,060.71 | -168,364.25 | -418,716.59 … 47,301.74 | -5.86 |
| `scale_out` | `legacy` | `mixed` | oos | 9 | 33.3% | -221,498.12 | -24,610.90 | -317,729.34 | -651,908.08 … 253,952.08 | -7.59 |
| `scale_out` | `legacy` | `trend_up` | all | 13 | 61.5% | 191,884.02 | 14,760.31 | -143,667.02 | -163,621.39 … 507,218.03 | -3.41 |
| `breakeven_move` | `legacy` | `chop` | all | 53 | 32.1% | -621,798.22 | -11,732.04 | -676,699.59 | -1,405,355.25 … 357,001.96 | -18.82 |
| `breakeven_move` | `legacy` | `expiry_trend_down` | all | 6 | 0.0% | -345,233.31 | -57,538.89 | -345,233.31 | -451,445.81 … -227,374.35 | -4.35 |
| `breakeven_move` | `legacy` | `mixed` | oos | 9 | 33.3% | -258,177.30 | -28,686.37 | -330,898.69 | -659,052.55 … 188,931.93 | -7.52 |
| `breakeven_move` | `legacy` | `trend_up` | all | 13 | 53.8% | 94,140.73 | 7,241.59 | -143,667.02 | -223,657.63 … 406,855.98 | -5.47 |
| `iv_crush` | `legacy` | `chop` | all | 53 | 35.8% | -1,066,679.82 | -20,126.03 | -1,151,432.35 | -1,893,840.43 … 10,961.39 | -17.50 |
| `iv_crush` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -84,272.94 | -14,045.49 | -151,624.07 | -575,151.26 … 421,789.92 | -5.63 |
| `iv_crush` | `legacy` | `mixed` | oos | 9 | 33.3% | -316,402.73 | -35,155.86 | -391,720.54 | -761,533.36 … 181,666.66 | -7.46 |
| `iv_crush` | `legacy` | `trend_up` | all | 13 | 61.5% | 166,233.26 | 12,787.17 | -143,667.02 | -176,387.96 … 465,210.33 | -3.80 |
| `stale_and_flat` | `legacy` | `chop` | all | 53 | 35.8% | -1,233,490.08 | -23,273.40 | -1,272,343.42 | -2,131,217.94 … -112,174.87 | -17.16 |
| `stale_and_flat` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -295,522.72 | -49,253.79 | -295,522.72 | -572,661.46 … -38,938.12 | -5.49 |
| `stale_and_flat` | `legacy` | `mixed` | oos | 9 | 33.3% | -256,960.89 | -28,551.21 | -332,278.70 | -666,200.00 … 201,294.03 | -7.53 |
| `stale_and_flat` | `legacy` | `trend_up` | all | 13 | 61.5% | 181,154.54 | 13,934.96 | -128,745.74 | -147,912.45 … 465,210.33 | -3.22 |
| `asymmetric_ce_pe` | `legacy` | `chop` | all | 53 | 43.4% | -664,372.53 | -12,535.33 | -843,495.00 | -1,432,965.99 … 130,604.90 | -18.35 |
| `asymmetric_ce_pe` | `legacy` | `expiry_trend_down` | all | 6 | 33.3% | -282,709.86 | -47,118.31 | -282,709.86 | -473,015.11 … -89,645.71 | -5.27 |
| `asymmetric_ce_pe` | `legacy` | `mixed` | oos | 9 | 33.3% | -315,672.90 | -35,074.77 | -324,980.22 | -655,252.28 … 77,738.03 | -7.25 |
| `asymmetric_ce_pe` | `legacy` | `trend_up` | all | 13 | 61.5% | -53,774.71 | -4,136.52 | -143,667.02 | -308,570.20 … 161,327.74 | -9.01 |
| `hold_to_1515` | `random_hist` | `chop` | all | 24 | 50.0% | 10,245.95 | 426.91 | -21,060.94 | -18,904.89 … 49,895.93 | -7.29 |
| `hold_to_1515` | `random_hist` | `expiry_chop` | all | 8 | 25.0% | -8,194.26 | -1,024.28 | -14,007.62 | -21,509.33 … 5,875.72 | -7.07 |
| `hold_to_1515` | `random_hist` | `expiry_mixed` | all | 8 | 50.0% | -6,300.25 | -787.53 | -12,528.05 | -23,346.36 … 9,858.96 | -7.08 |
| `hold_to_1515` | `random_hist` | `mixed` | all | 8 | 37.5% | 2,285.55 | 285.69 | -4,016.06 | -8,811.83 … 14,624.03 | -4.98 |
| `v2_default` | `random_hist` | `chop` | all | 24 | 50.0% | 10,245.95 | 426.91 | -21,060.94 | -18,904.89 … 49,895.93 | -7.29 |
| `v2_default` | `random_hist` | `expiry_chop` | all | 8 | 25.0% | -8,194.26 | -1,024.28 | -14,007.62 | -21,509.33 … 5,875.72 | -7.07 |
| `v2_default` | `random_hist` | `expiry_mixed` | all | 8 | 50.0% | -6,300.25 | -787.53 | -12,528.05 | -23,346.36 … 9,858.96 | -7.08 |
| `v2_default` | `random_hist` | `mixed` | all | 8 | 37.5% | 2,285.55 | 285.69 | -4,016.06 | -8,811.83 … 14,624.03 | -4.98 |
| `fixed_stop_target` | `random_hist` | `chop` | all | 24 | 50.0% | 14,787.22 | 616.13 | -17,937.19 | -12,472.01 … 55,057.97 | -5.50 |
| `fixed_stop_target` | `random_hist` | `expiry_chop` | all | 8 | 25.0% | -9,079.80 | -1,134.97 | -14,581.75 | -22,200.24 … 4,995.15 | -7.02 |
| `fixed_stop_target` | `random_hist` | `expiry_mixed` | all | 8 | 50.0% | -4,350.75 | -543.84 | -10,924.34 | -17,287.83 … 8,108.52 | -7.04 |
| `fixed_stop_target` | `random_hist` | `mixed` | all | 8 | 37.5% | 1,938.46 | 242.31 | -4,019.36 | -10,297.47 … 15,683.92 | -5.27 |
| `legacy_overlay` | `random_hist` | `chop` | all | 24 | 12.5% | -3,407.05 | -141.96 | -6,946.86 | -10,246.20 … 6,315.56 | -12.86 |
| `legacy_overlay` | `random_hist` | `expiry_chop` | all | 8 | 37.5% | 709.86 | 88.73 | -982.51 | -2,620.95 … 4,480.72 | -4.94 |
| `legacy_overlay` | `random_hist` | `expiry_mixed` | all | 8 | 37.5% | -185.78 | -23.22 | -3,973.11 | -5,859.59 … 6,792.36 | -6.17 |
| `legacy_overlay` | `random_hist` | `mixed` | all | 8 | 25.0% | 1,036.70 | 129.59 | -2,102.66 | -3,411.93 … 7,087.59 | -4.87 |
| `regime_router` | `random_hist` | `chop` | all | 24 | 41.7% | -2,291.21 | -95.47 | -7,533.56 | -8,916.01 … 4,914.18 | -12.75 |
| `regime_router` | `random_hist` | `expiry_chop` | all | 8 | 25.0% | -7,438.45 | -929.81 | -11,805.09 | -17,723.84 … 3,300.13 | -6.99 |
| `regime_router` | `random_hist` | `expiry_mixed` | all | 8 | 50.0% | -5,041.71 | -630.21 | -9,341.55 | -15,182.51 … 6,126.08 | -7.10 |
| `regime_router` | `random_hist` | `mixed` | all | 8 | 12.5% | -2,456.85 | -307.11 | -4,278.37 | -5,208.58 … 2,675.55 | -7.09 |

### Sweep choose nets (random entries, sessions ≤ 2026-09-22)

| Variant | Choose net ₹ |
|---|---:|
| `noise_1.6` | 129,457.39 |
| `noise_2.2` | 127,459.24 |
| `fixed_0.15_0.35` | 126,528.27 |
| `fixed_0.15_0.25` | 126,061.16 |
| `noise_1.2` | 124,925.81 |
| `fixed_0.20_0.35` | 123,352.62 |
| `fixed_0.20_0.25` | 122,885.51 |
| `fixed_0.25_0.35` | 121,396.68 |
| `fixed_0.25_0.25` | 120,929.57 |
| `fixed_0.15_0.45` | 119,025.51 |
| `time_720` | 118,830.83 |
| `fixed_0.15_0.55` | 118,778.97 |
| `fixed_0.30_0.35` | 117,153.83 |
| `fixed_0.30_0.25` | 116,686.72 |
| `time_1200` | 116,047.69 |
| `fixed_0.20_0.45` | 115,849.86 |
| `fixed_0.20_0.55` | 115,603.32 |
| `fixed_0.40_0.35` | 115,593.57 |
| `fixed_0.40_0.25` | 115,126.46 |
| `time_1800` | 114,834.57 |
| `fixed_0.25_0.45` | 113,893.92 |
| `fixed_0.25_0.55` | 113,647.38 |
| `fixed_0.30_0.45` | 109,651.07 |
| `fixed_0.30_0.55` | 109,404.53 |
| `fixed_0.40_0.45` | 108,090.81 |
| `trail_0.25_4` | 107,928.47 |
| `fixed_0.40_0.55` | 107,844.27 |
| `time_2700` | 105,664.43 |
| `trail_0.35_4` | 103,241.25 |
| `trail_0.25_8` | 101,278.75 |
| `trail_0.25_12` | 98,022.00 |
| `trail_0.35_8` | 96,166.61 |
| `trail_0.50_4` | 94,015.98 |
| `trail_0.35_12` | 92,338.95 |
| `trail_0.50_8` | 85,874.13 |
| `trail_0.50_12` | 82,036.73 |

## Stress

Plan `regime_router`, n=80 sample of live tickets, seed 7. From `tables.json` → `stress`.

| Case | Net ₹ | Label |
|------|------:|-------|
| base | 135,912.58 | same fill model |
| spread ×2 | 132,704.46 | stated slip/spread doubled |
| slip ×2 | 132,704.46 | same model as spread ×2 in this run |
| 30 s quote gap | 62,377.20 | **synthetic** (quotes dropped) |
| Monte Carlo resample of trade nets (n=200) | p05 100,525.68 / p50 134,731.39 / p95 174,089.15 | resample of the 80-trade nets, not new paths |

IV crush 20% and 1% open index gap: **synthetic / not run as a priced path on this tape**. Partial fills and rejects: modelled in the harness types, not fired on this research grid — **DATA_INSUFFICIENT** for a fill/reject table.

30 s synthetic gap cut the sample net from ₹1,35,913 to ₹62,377. A feed hole is more expensive than 2× slip on this sample.

## Legacy comparison

Two different numbers. Do not mix them.

### A. Desk's own recorded exits (`replay_paper_scalp` extras on the 81 tickets)

Net **−₹1,51,497.43** (gross −₹75,562.50, charges ₹75,934.93). All 25 lots. ITM200.

| Desk reason | n | Net ₹ | Gross ₹ | Charges ₹ |
|-------------|---|------:|--------:|----------:|
| CANCEL_AGAINST | 32 | −312,386.95 | −282,343.75 | 30,043.20 |
| COVER_LONG_UNWIND | 22 | −218,234.11 | −197,681.25 | 20,552.86 |
| CANCEL_NO_PROGRESS | 12 | −15,785.36 | −5,118.75 | 10,666.61 |
| CANCEL_STALL | 4 | +36,008.26 | +39,975.00 | 3,966.74 |
| CANCEL_BOOK_NEAR | 5 | +97,394.89 | +102,131.25 | 4,736.36 |
| TARGET | 6 | +261,505.84 | +267,475.00 | 5,969.16 |
| **Total** | **81** | **−151,497.43** | **−75,562.50** | **75,934.93** |

By session (desk own): 17 +46,484.58 (3); 18 +22,402.36 (7); 21 −12,850.59 (13); 22 +656.18 (6); 23 −80,259.13 (14); 24 −37,958.88 (11); 25 −110,147.41 (18); 28 +20,175.46 (9).

In plain words: 6 targets (+₹2.62 L) and 5 book-near (+₹0.97 L) did not cover 32 cancels-against (−₹3.12 L) and 22 cover-unwinds (−₹2.18 L). No-progress was a small net loss with charges larger than the gross. Stall was net positive on 4 tickets.

### B. Lab `legacy_overlay` re-sim on the same 81 tickets

Net **−₹9,67,663.89** (CI −₹15.21 L … −₹4.29 L). Reasons the copied constants actually fired:

| Lab reason | n | Net ₹ |
|------------|---|------:|
| CANCEL_ADVERSE | 18 | −905,138.98 |
| FLATTEN_1516 | 8 | −85,433.39 |
| FLATTEN_EOD | 3 | −57,916.53 |
| TIME | 52 | +80,825.01 |

Ticket-by-ticket the lab overlay does **not** match the desk (CANCEL_AGAINST vs lab TIME / FLATTEN / CANCEL_ADVERSE). The copied constants are a reference rule-set, not a bit-exact replay of `paper_scalp.py`'s BIN unwind / overlay path. Use (A) for “what the desk did”; use (B) for “what this rule-set does in the harness”.

Hold-to-15:15 on those same 81 tickets: **−₹15,94,358.01**. The desk overlays cut that bleed by about ₹14.4 L versus hold, and still lost ₹1.51 L. 25-lot size makes every rupee table look like a different product from the 1-lot random set.

## What failed / what is not a promote

- **V2-boss (60 × 2 lots):** hold / V2 default +₹63.91, CI −₹85,483 … +₹91,351, DD −₹64,802, DSR −17.53. `fixed_stop_target` +₹81,041 but CI crosses 0 (−₹16,804 … +₹1,70,413) and DSR −2.64. `legacy_overlay` −₹15,805. Do not promote from this set.
- **`atr_stop` on V2-boss:** 0% win, avg time 0 s, net −₹15,428. ATR was 0.0 on several late-start days — degenerate, not a real ATR test.
- **History OOS:** no tickets after 2025-10-14. Intended 2026-06+ holdout is DATA_INSUFFICIENT. On the 48 Oct-2025 tickets, `regime_router` lost more than hold (−₹17,228 vs −₹1,963).
- **Sweep vs OOS:** winner `noise_1.6` (choose ₹1,29,457.39) is OOS-positive (₹86,908.92, CI ₹47,742.31–₹1,30,825.59, DSR 5.07) but `time_and_stop` and `regime_router` beat it on the same late days. 51 variants; DSR is the multiple-testing correction already in the table.
- **Router uses the day label**, not a live-at-entry classifier.
- **V2 spread sample empty.** Stated 0.40% slip is the fill model when the book is missing.
- **`iv_crush` == `fixed_stop_target`** on live random/V2 — no 20% IV drop observed.
- **Random CE/PE imbalance** (106 vs 40) — PE-specific claims are thin.
- **expiry_chop random n=1** — ignore that cell.

## Recommended playbook (paper only, OFF)

See `config/v2/exits/exitlab_playbook.yaml`. Off unless `enabled: true` **and** `load_exitlab_playbook(enabled=True)`. V2 `ExitPlan` has no noise-band field, so the mapping is: flatten 15:15, catastrophic ₹8,000, time stop 1,500 s unless +8 pts, 90 s grace. Trail / target / partials stay null until a larger OOS supports them.

Per scenario, from this run only (random 1-lot live, after costs):

| Scenario at entry | n (random) | Best library plan on that cell | Net ₹ | vs hold ₹ | OOS note |
|-------------------|----------:|--------------------------------|------:|----------:|----------|
| chop | 90 | `regime_router` | 135,394.27 | +32,693.71 | Late days are also mostly chop; `time_and_stop` late ₹1,02,093 |
| trend_up | 18 | `fixed_stop_target` | 48,926.43 | +2,384.17 | Router trails and gives some back (₹35,682) |
| expiry_trend_down | 18 | `noise_band` | 31,623.99 | +33,962.11 | CI still wide; DSR 0.32 |
| mixed | 19 | `time_and_stop` | 25,539.57 | +26,851.76 | CI ₹3,757–₹47,655 |
| expiry_chop | 1 | — | — | — | DATA_INSUFFICIENT |

Evidence for the mapped time-stop: `time_and_stop` (25 min / 20%) late 72 trades ₹1,02,093.02. Evidence for the sweep file name: `sweep_winner_noise_1.6` late 72 trades ₹86,908.92 (CI ₹47,742.31–₹1,30,825.59, DSR 5.07, 51 variants).

Do not enable this as the V2 default. Do not use 25-lot desk P&L to pick a 1-lot playbook.

## Handoff

### Accepted
- Paper/replay harness in `packages/exitlab` (ask-in / bid-out, `ledger.charges`, no look-ahead).
- Three entry sets plus history random on the first parquet week.
- Opt-in playbook file, default off. `load_exitlab_playbook()` returns None.
- Honest time split + variant count for DSR. Tables copied from `/tmp/exitlab-run`.

### Rejected
- Shipping any plan as the live default.
- Editing `paper_scalp.py`, `desk.sh`, recorder, or `config/v2/exits/defaults.yaml`.
- Inventing bid/ask on 1m history (stated slip instead).
- Filling empty V2 spread or 2026 history OOS cells.

### Unknown / data insufficient
- News/event tags; V2 book spread; 2026 history OOS; IV-crush trigger; partial fill / reject table; live-at-entry regime (router used the day label).
- Thin 2026-08-04 week; 2026-09-14 after-hours; late-start live days; ATR=0 on 16/17/18.

### Gap addressed
- Exit research gap: a replayable, costed, no-look-ahead exit lab on real tapes, with baselines and an opt-in V2 mapping that does not change live defaults.

### Known risks
- V2 entry set is a selector proxy (1m direction + real holds), not the full plugin room.
- Sweep winner is not the best OOS plan.
- 25-lot vs 1-lot rupee totals are not comparable.
- Lab overlay ≠ desk overlay ticket-by-ticket.

### Next steps
- Re-run on a larger tape once more V2 days and more matched history weeks exist.
- If a live-at-entry regime classifier is added, re-score `regime_router` without the day label.
- Founder paper-session only if a later OOS table stays non-negative after costs and DSR. Not this PR.

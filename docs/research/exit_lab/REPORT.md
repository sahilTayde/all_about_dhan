# Exit Lab report (paper / replay only)

**Status:** HYPOTHESIS / PAPER / NO_PROMOTE. Every number below comes from

```bash
python -m exitlab research --data .local_data --out /tmp/exitlab-fix --seed 7 --max-hist-days 24 --extra-seeds 11,19 --reuse-entries /tmp/exitlab-run/entries.json
```

run after the strike / spread / DSR fixes (2026-09-28). Raw JSON: `/tmp/exitlab-fix/tables.json`, `entries.json`, `trades.json`, `oos_sweep.json`, `hold_sanity.json`, `measure_live.json`. Copy: `/opt/cursor/artifacts/exitlab-fix-tables.json`. If a cell is missing, this file says `DATA_INSUFFICIENT`.

The prior audit (`/tmp/exitlab-audit`, same 419 live + 48 hist tickets, 14,944 trades) is **invalid**. It marked the rolling ATM/ITM when the fixed strike was missing, priced random ITM200 entries on the rolling ITM, applied no book spread, and printed DSR as a z-score. Those headline nets are not used below except in the “what changed” table.

**Owner:** `packages/exitlab` + this file. V2 defaults are unchanged. Playbook: `config/v2/exits/exitlab_playbook.yaml` (`enabled: false`).

## Now / Why / Next

- **Now:** After locking marks to the entry strike and buying/selling LTP ± half the measured V2 spread, random 1-lot `hold_to_1515` is **−₹82,477.86** on 277 closed trades (−₹297.75 / trade, 43.0% wins). That is break-even-minus-costs-and-theta, not a money machine. The OOS sweep winner (`noise_1.6`) is **−₹31,338.61** on the later live days (CI crosses zero; DSR ≈ 0 after 68 trials). Playbook stays off.
- **Why:** The old +₹2.88 L hold figure was a mark bug. ITM200 tickets were entered at the rolling ITM price (~₹193) then marked on the 200-pt-ITM wing (~₹267). Trails and locks harvested fake jumps. `spread_x2` equalled `base` because dual-tape quotes have no book.
- **Next:** Founder does not promote. Do not turn the playbook on from this report.

**Do not compare rupee totals across entry sets.** Legacy tickets are 25 lots. V2-boss tickets are 2 lots. Random and history tickets are 1 lot.

## What changed vs the audit run

| Cell | Audit (`/tmp/exitlab-audit`) | This run (`/tmp/exitlab-fix`) | Delta |
|---|---:|---:|---:|
| random `hold_to_1515` net | +288,281.68 (n=278, WR 56.5%, DSR 11.96) | −82,477.86 (n=277, WR 43.0%, DSR 0.0000) | −370,759.54 |
| random `quote_persistence` | +391,248.11 (DSR 17.43) | +12,580.57 (DSR 0.0385) | −378,667.54 |
| random `noise_band` | +372,833.27 (DSR 16.87) | +1,077.94 (DSR 0.0094) | −371,755.33 |
| sweep winner / OOS | `noise_2.2` +152,135.16 (DSR 8.39) | `noise_1.6` −31,338.61 (DSR 0.0000) | −183,473.77 |
| stress `base` | 135,912.58 | 4,095.30 | −131,817.28 |
| stress `spread_x2` | 135,912.58 (= base) | 3,174.01 (≠ base, −921.29) | spread now priced |
| stress `slip_x2` | 132,704.46 | −2,301.61 | now a real extra cost |
| legacy `legacy_overlay` | −967,663.89 (DSR −20.02) | −884,704.76 (DSR 0.0000) | +82,959.13 |
| legacy `hold_to_1515` | −1,594,358.01 | −1,263,738.10 | +330,619.91 |
| v2_boss `hold_to_1515` / `v2_default` | +63.91 (DSR −18.36) | +3,567.19 (DSR 0.0104) | +3,503.28 |

Every DSR in the audit that sat outside [0, 1] was the raw test statistic, not Bailey / Lopez de Prado’s probability. This run’s DSR values are all in [0, 1] (min 0.0000, max 0.3803 across 673 summaries).

## 1. Wrong instrument — counts

Old path (`research._series_for_live`): if `wing_ltp(entry.strike)` was missing, call `premium_quote` on the **current** ATM/ITM. That strike rolls with the index.

New path: `strike_ltp` only. Same strike via wings or matching ATM/ITM fields. Else skip the tick (stale / no mark). Random / V2 entries with no fixed-strike LTP at or after entry are dropped, not repriced.

### Before (old 419-entry file, old fallback fired)

Source: `/opt/cursor/artifacts/exitlab-missing-strike-before.txt` counted on `/tmp/exitlab-run/entries.json`.

| Entry set | Entries | Ticks after entry | Ticks where fallback fired | Trades that hit ≥1 fallback |
|---|---:|---:|---:|---:|
| random | 146 (seed 7 only in that probe; audit used 278) | 40,558 | 640 | 58 |
| v2_boss | 60 | 14,294 | 110 | 17 |
| legacy | 81 | 15,212 | 204 | 17 |

Entry-time bug (separate from tick fallback): all 48 seed-7 ITM200 random tickets stored the intended 200-pt-ITM strike but `premium_quote(..., moneyness="ITM")` priced the rolling ITM (often 100-pt). Example `rnd-2026-09-17-7-2`: strike 23150, wing LTP 267.9, entry_price 194.05 (rolling ITM). Instant fake MFE.

### After (this run)

Source: `tables.json` → `missing_strike.after_fix`. Those ticks are holes, not marks. Random rebuilt; 0 entries dropped at the at-or-after-entry gate (legacy opened_ts sits between tape rows; first tick ≥ entry is used).

| Entry set | Entries | Ticks after entry | Ticks missing fixed strike | Trades that hit ≥1 hole |
|---|---:|---:|---:|---:|
| random | 278 | 72,703 | 1,127 | 103 |
| v2_boss | 60 | 14,294 | 110 | 17 |
| legacy | 81 | 15,212 | 204 | 17 |

Random 278 = seeds 7 (146) + 11 (66) + 19 (66). One `hold_to_1515` skip: `SKIP_NEAR_SQUARE` (n_closed=277).

## 2. Fills — V2 spread, not silent LTP

Dual-tape JSONL has LTP only (`bid`/`ask` null). V2 `quote_snapshots.jsonl` on 2026-09-28 (n=4,698 option prints, 10:00–11:00 IST only) measured full bid/ask spread:

| Rule | n | p50 pts | p80 pts | mean pts |
|---|---:|---:|---:|---:|
| ATM | 1,566 | 0.20 | 0.25 | 0.21 |
| ITM100 | 1,566 | 0.35 | 0.45 | 0.34 |
| ITM200 | 1,566 | 0.55 | 0.70 | 0.54 |

TOD p50 is flat inside that 10:00–11:00 window (ATM 0.20 every bucket). Later-day TOD is **DATA_INSUFFICIENT**; the no-book fill uses the moneyness p50 for the whole session.

No-book fill: buy `LTP + 0.5 × spread(moneyness)`, sell `LTP − 0.5 × spread`. `spread_x2` doubles that spread. Extra `slip_frac` is 0 unless a stress sets it.

Stress on `regime_router`, 80 random tickets (same harness as the grid):

| Case | n | closed | skipped | Net ₹ |
|---|---:|---:|---:|---:|
| `base` | 80 | 80 | 0 | 4,095.30 |
| `spread_x2` | 80 | 80 | 0 | 3,174.01 |
| `slip_x2` | 80 | 80 | 0 | −2,301.61 |
| `gap_1s_synthetic` | 40 | 40 | 0 | 6,469.11 |
| `gap_2s_synthetic` | 40 | 40 | 0 | 6,469.11 |
| `gap_30s_synthetic` | 40 | 40 | 0 | 6,469.11 |
| `partial_fill_half` | 40 | 0 | 40 | 0.00 |
| `reject_p15` | 40 | 33 | 7 | 3,351.22 |
| `index_gap_1pct_synthetic` | 40 | 40 | 0 | −67,277.83 |
| `iv_crush_20_synthetic` | 40 | 40 | 0 | −47,335.18 |

`spread_x2` is **−₹921.29 vs base**. That is the required proof that spread is applied. Gaps 1s/2s/30s match on this sample (same first-second hole). 1-lot half-fill is REJECT (whole lots). 2-lot / 25-lot addon from the audit was not re-run this pass (`DATA_INSUFFICIENT` for that addon table).

## 3. DSR is a probability

Bailey / Lopez de Prado (2014) eq. 8–11:

`DSR = Phi((SR_hat − SR*) / se_SR)` with `SR* = se_SR × [(1−γ) Φ⁻¹(1−1/N) + γ Φ⁻¹(1−1/(N e))]`.

`SR_hat` is mean/std of trade nets (per-period), not a t-stat. Unit test `test_dsr_is_probability_worked_example`: SR=0.15, n=100, N=20, skew=0, kurtosis=3 → DSR **0.3385**, and `0 ≤ DSR ≤ 1` for huge/tiny SR. Evidence: `packages/exitlab/tests/test_stats.py`.

## 4. Sanity — random `hold_to_1515`

Not clearly positive. 277 closed 1-lot buys, hold to 15:15, costs on.

| Slice | n | Net ₹ | Avg ₹ | WR |
|---|---:|---:|---:|---:|
| All | 277 | −82,477.86 | −297.75 | 43.0% |
| CE | 170 | −100,747.31 | −592.63 | 47.1% |
| PE | 107 | +18,269.45 | +170.74 | 36.4% |
| ATM | 102 | −52,866.10 | −518.30 | 39.2% |
| ITM100 | 95 | −12,482.35 | −131.39 | 45.3% |
| ITM200 | 80 | −17,129.41 | −214.12 | 45.0% |

By session (index path from `measure_live.json`):

| Session | Scenario | Index | n | Net ₹ | CE net | PE net |
|---|---|---|---:|---:|---:|---:|
| 2026-09-15 | expiry_chop | 23576 → 23222 (−354) | 3 LOW | +467 | −700 | +1,167 |
| 2026-09-16 | mixed | 23191 → 23218 | 3 LOW | −1,643 | −2,234 | +592 |
| 2026-09-17 | chop | 23338 → 23271 | 34 | −17,130 | −17,467 | +336 |
| 2026-09-18 | chop | 23271 → 23346 | 34 | −2,132 | +16,631 | −18,763 |
| 2026-09-21 | trend_up | 23374 → 23414 | 34 | +8,983 | +32,876 | −23,893 |
| 2026-09-22 | expiry_trend_down | 23439 → 23329 | 33 | −28,004 | −43,572 | +15,568 |
| 2026-09-23 | chop | 23380 → 23431 | 34 | −9,230 | +141 | −9,371 |
| 2026-09-24 | chop | 23261 → 23088 (−173) | 34 | −5,230 | −70,155 | +64,926 |
| 2026-09-25 | chop | 23116 → 23128 | 34 | +13,353 | +52,048 | −38,695 |
| 2026-09-28 | mixed | 22864 → 22788 | 34 | −41,913 | −68,316 | +26,403 |

Trend days do move one side: 21 CE wins, 22/24/28 PE wins as the index falls. CE still loses more in rupees because the random set is CE-heavy (171 vs 107 — ITM PE wings miss more often, so more PE candidates are dropped) and chop/mixed days bleed premium. That is option-buyer economics, not a leftover roll-strike mark.

History 1-lot `hold_to_1515` (48 tickets, week of 2025-10-06..14 only): **−₹551.99**. 2026 history OOS: **DATA_INSUFFICIENT**.

## 5. Recomputed tables

`n_variants_tested = 68` (32 library + 36 sweep). Seeds 7, 11, 19. `n_entries_live = 419`. `n_entries_hist = 48`. `n_trade_results = 14,944`. `n_low_confidence_cells = 352`. Sweep choose: random live `session <= 2026-09-22` (142 tickets). Report: `2026-09-23..28` (136 tickets).

DSR on every Summary uses N=68. Cells with n<30 are LOW.

### Random 1-lot (scenario ALL)

One skip on every plan (`SKIP_NEAR_SQUARE`). Ranked by net.

| Plan | n | WR | Net ₹ | Avg | Max DD | CI | DSR |
|---|---:|---:|---:|---:|---:|---|---:|
| `quote_persistence` | 277 | 37.2% | 12,580.57 | 45.42 | −13,298.64 | −19,931 … 59,431 | 0.0385 |
| `noise_band` | 277 | 22.4% | 1,077.94 | 3.89 | −23,803.24 | −49,217 … 49,631 | 0.0094 |
| `chandelier` | 277 | 37.2% | −4,030.88 | −14.55 | −28,169.34 | −64,683 … 61,449 | 0.0059 |
| `structure_stop` | 277 | 25.3% | −7,865.06 | −28.39 | −17,078.27 | −27,129 … 14,519 | 0.0007 |
| `momentum_fade` | 277 | 40.8% | −12,114.38 | −43.73 | −16,502.52 | −28,200 … 4,491 | 0.0000 |
| `tod_two_speed` | 277 | 36.8% | −17,956.54 | −64.83 | −34,920.39 | −47,660 … 14,358 | 0.0002 |
| `reversal` | 277 | 35.0% | −18,332.53 | −66.18 | −21,567.79 | −33,811 … −3,122 | 0.0000 |
| `index_stop` | 277 | 35.7% | −19,743.50 | −71.28 | −45,757.20 | −79,668 … 47,477 | 0.0015 |
| `time_and_stop` | 277 | 41.5% | −20,431.33 | −73.76 | −28,938.78 | −48,455 … 13,420 | 0.0001 |
| `theta_budget` | 277 | 15.9% | −23,863.28 | −86.15 | −41,183.72 | −69,911 … 23,505 | 0.0003 |
| `expiry_cliff` | 277 | 40.4% | −24,245.93 | −87.53 | −51,714.09 | −97,582 … 50,352 | 0.0012 |
| `breakeven_move` | 277 | 32.1% | −24,950.03 | −90.07 | −56,785.44 | −95,664 … 63,181 | 0.0013 |
| `atr_stop` | 277 | 0.7% | −25,731.73 | −92.89 | −25,731.73 | −30,107 … −21,160 | 0.0000 |
| `step_trail` | 277 | 53.4% | −25,994.45 | −93.84 | −44,159.21 | −76,448 … 30,179 | 0.0004 |
| `lunch_chop` | 277 | 39.0% | −31,466.62 | −113.60 | −40,884.33 | −67,998 … 10,125 | 0.0000 |
| `iv_crush` | 277 | 42.6% | −31,729.30 | −114.55 | −54,139.11 | −113,907 … 59,149 | 0.0010 |
| `regime_router` | 277 | 42.6% | −31,800.68 | −114.80 | −44,621.15 | −68,214 … 4,919 | 0.0000 |
| `fixed_stop_target` | 277 | 42.6% | −34,402.15 | −124.20 | −56,460.31 | −117,661 … 55,755 | 0.0008 |
| `mfe_trail` | 277 | 65.0% | −35,203.25 | −127.09 | −47,347.98 | −80,655 … 9,561 | 0.0000 |
| `legacy_overlay` | 277 | 42.6% | −36,049.95 | −130.14 | −41,644.17 | −72,191 … 8,899 | 0.0000 |
| `iv_spike` | 277 | 41.5% | −39,167.22 | −141.40 | −61,225.38 | −123,042 … 54,621 | 0.0005 |
| `stale_and_flat` | 277 | 42.2% | −41,191.06 | −148.70 | −56,275.88 | −94,223 … 15,667 | 0.0000 |
| `implied_move` | 277 | 37.5% | −44,542.36 | −160.80 | −58,549.39 | −96,669 … 8,792 | 0.0000 |
| `elasticity_die` | 277 | 32.5% | −48,872.73 | −176.44 | −66,748.65 | −120,276 … 34,444 | 0.0001 |
| `scale_out` | 277 | 39.4% | −73,849.60 | −266.61 | −90,470.18 | −153,493 … 12,838 | 0.0000 |
| `index_trail` | 277 | 44.8% | −78,092.52 | −281.92 | −84,901.79 | −145,617 … −12,156 | 0.0000 |
| `target_extend` | 277 | 39.4% | −79,600.74 | −287.37 | −96,270.95 | −153,859 … 7,775 | 0.0000 |
| `hold_to_1515` | 277 | 43.0% | −82,477.86 | −297.75 | −98,174.96 | −158,743 … −2,849 | 0.0000 |
| `v2_default` | 277 | 43.0% | −82,477.86 | −297.75 | −98,174.96 | −158,743 … −2,849 | 0.0000 |
| `day_loss` | 277 | 41.9% | −87,103.37 | −314.45 | −100,918.16 | −164,932 … −9,165 | 0.0000 |
| `gap_against` | 277 | 40.1% | −92,591.86 | −334.27 | −106,027.12 | −171,336 … −11,953 | 0.0000 |
| `asymmetric_ce_pe` | 277 | 41.2% | −97,003.46 | −350.19 | −117,185.69 | −165,643 … −23,350 | 0.0000 |

`quote_persistence` is the only random plan with a clearly positive point estimate. DSR 0.0385 after 68 trials is not a promote. Its CI crosses zero.

Random `hold_to_1515` by scenario: expiry_chop n=3 LOW +467; mixed n=37 −43,555; chop n=170 −20,369; trend_up n=34 +8,983; expiry_trend_down n=33 −28,004.

### OOS sweep

Choose (≤ 2026-09-22) top: `noise_1.6` +31,187.20; `noise_2.2` +30,830.32; `noise_1.2` +26,733.46; `fixed_0.15_0.35` +18,607.93.

Winner **`noise_1.6`** on later days 2026-09-23..28: n=136, net **−₹31,338.61**, avg −230.43, WR 11.8%, CI −60,412.57 … +9,083.41, DSR 0.000008. Multiple-testing correction: 68 variants.

### V2-boss 2-lot (selector proxy, not live alpha)

Best point estimate `fixed_stop_target` +84,849.25 (DSR 0.2688). CI −13,437 … +174,429 crosses zero. `hold_to_1515` / `v2_default` +3,567.19 (DSR 0.0104). Not a promote.

### Legacy 25-lot (lab re-sim)

Every plan is negative. Least-bad `step_trail` −22,919.16 (CI crosses zero, DSR 0.0071). Lab `legacy_overlay` −884,704.76. Lab `hold_to_1515` −1,263,738.10.

Desk’s own recorded exits on the same 81 fills (unchanged; from `replay_paper_scalp` extras, not this mark path): **−₹1,51,497.43**. CANCEL_AGAINST 32 / −₹3,12,386.95. Early overlays (COVER_LONG_UNWIND + CANCEL_NO_PROGRESS + CANCEL_STALL + CANCEL_BOOK_NEAR) 43 / −₹1,00,616.32. TARGET 6 / +₹2,61,505.84. Cancelled never-filled: 3,450 skips. Use the desk extras for “what the desk did”; use the lab column for “what this rule-set does in the harness”.

### History 1-lot (2025-10-06..14 only)

`hold_to_1515` −551.99 (DSR 0.0078). Several trail/chop plans print positive point estimates (`breakeven_move` +23,526, DSR 0.1316; `mfe_trail` +14,937, DSR 0.2636) with n=48 and no 2026 holdout. DATA_INSUFFICIENT for history OOS.

Full plan × entry × scenario rows stay in `/tmp/exitlab-fix/tables.json` → `summaries`.

## Data used

| Set | Path | What | Notes |
|-----|------|------|-------|
| Live dual-tape | `.local_data/tape/YYYY-MM-DD.jsonl` | Index + ATM/ITM LTP + wings | 12 files, 4,986 ticks. No bid/ask. |
| V2 recorder | `.local_data/tape/v2/2026-09-28/` | Quote snapshots + depth | Spread table from 4,698 option prints, 10:00–11:00 only. |
| Option 1m | `.local_data/NIFTY_*.parquet` | Weekly OHLC | Entries matched the first week only (48 tickets). Later weeks DATA_INSUFFICIENT. |
| Index 1m | `.local_data/index_NIFTY.parquet` | NIFTY 1m | Regime labels. |

Live session labels (same tapes as the audit): 14 after-hours DATA_INSUFFICIENT; 15 expiry_chop; 16 mixed; 17/18/23/24/25 chop; 21 trend_up; 22 expiry_trend_down; 19 weekend skipped; 28 mixed.

**Fills:** book ask in / bid out when present. Else LTP ± half V2 spread by moneyness. Costs: `ledger.charges` + `config/charges.yaml` (NSE). Lot 65. Same-bar stop+target: stop wins. Whole-lot fills only.

**No look-ahead:** `python -m exitlab prove-lookahead` → `HONEST_OK` then `INJECT_RAISED`. Tests: `packages/exitlab/tests/test_lookahead.py`.

## Reproduce

```bash
python -m pip install --no-deps -e packages/exitlab packages/oms packages/contracts
python -m exitlab research --data .local_data --out /tmp/exitlab-fix --seed 7 --max-hist-days 24 --extra-seeds 11,19 --reuse-entries /tmp/exitlab-run/entries.json
python -m exitlab prove-lookahead
python -m exitlab playbook --path config/v2/exits/exitlab_playbook.yaml
python -m pytest -q packages/exitlab/tests
```

`--reuse-entries` keeps legacy + v2_boss + hist and **rebuilds random** (old random files priced ITM200 off the rolling ITM).

## Cost hand-work (one trade)

`rnd-2026-09-17-7-0`, `hold_to_1515`, 1 lot × 65, CE. Entry 141.40 → exit 148.75.

- Buy turnover 141.40 × 65 = 9,191.00. Brokerage 20.00, STT 0, exchange 3.27, SEBI 0.01, stamp 0.28, GST 4.19, buy 27.75.
- Sell turnover 148.75 × 65 = 9,668.75. Brokerage 20.00, STT 14.50, exchange 3.44, SEBI 0.01, stamp 0, GST 4.22, sell 42.17.
- Hand 27.75 + 42.17 = **69.92**. Trade `charges_inr` 69.92. MATCH True vs `ledger.charges` NSE.
- Gross (148.75 − 141.40) × 65 = 477.75. Net 477.75 − 69.92 = 407.83.

Evidence: `/opt/cursor/artifacts/exitlab-cost-handwork.txt`.

## Edge cases / look-ahead / suite

`packages/exitlab/tests`: 37 passed (was 32). Added `test_strike_lock.py`, DSR worked example, `spread_x2` fill test.

`python -m ruff check packages/exitlab` and `python -m mypy --strict packages/exitlab/src`: green.

`python -m exitlab prove-lookahead`: HONEST_OK / INJECT_RAISED. `/opt/cursor/artifacts/exitlab-lookahead.txt`.

`python -m exitlab playbook`: `enabled: false`, mapping null.

`git diff origin/main -- config/v2/exits/defaults.yaml`: empty (defaults unchanged). Playbook file is new and stays `enabled: false`. Notes in that file now point at this run (old DSR 8.39 text removed).

Edges in `test_edges.py`: expiry after 14:30, 15:15 freeze, 60 s quote hole, same-bar stop+target, zero-lot partial, CE/PE flip.

## Five findings (this run)

1. **Random long options held to 15:15 lose money after costs** (−₹82k / 277, CI does not contain +₹2.88 L). The old plus was a wrong-instrument mark plus ITM200 entry on the rolling ITM.
2. **No exit in the library has a usable DSR on random live tickets.** Best DSR is `quote_persistence` 0.0385. After 68 trials that is not evidence of edge.
3. **The OOS sweep failed.** Choose liked `noise_1.6` (+₹31k in-sample). Later days: −₹31k, WR 11.8%, DSR ≈ 0.
4. **`spread_x2` now hurts** (−₹921 vs base on the 80-ticket stress). Dual-tape still has no live book; the V2 p50 table is the stated fill when the book is missing. Only one V2 session (28 Sep, morning) — later-day spread is DATA_INSUFFICIENT.
5. **Do not promote.** Desk 25-lot fills still lost ₹1.51 L on their own exits. Lab overlay on those tickets is worse. V2-boss `fixed_stop_target` +₹85k has CI through zero and DSR 0.27.

## Recommended playbook (paper only, OFF)

`config/v2/exits/exitlab_playbook.yaml`. Off unless `enabled: true` **and** `load_exitlab_playbook(enabled=True)`. Mapping is still flatten 15:15 / catastrophic ₹8,000 / time stop 1,500 s — a conservative paper stub, not an OOS winner. The OOS table does not support enabling it.

## Handoff

### Accepted
- Review findings 1–4. Fixed-strike marks, V2 half-spread fills, DSR as Φ(z), random hold sanity.
- Paper/replay harness. Playbook default off. Live V2 defaults unchanged.

### Rejected
- The audit headline nets (+₹2.88 L hold, +₹1.52 L OOS, DSR 8–17, `spread_x2` == base).
- Promote / enable playbook / edit `paper_scalp.py` / `defaults.yaml`.
- Repricing a missing strike onto the rolling ATM/ITM.

### Unknown / data insufficient
- V2 book after 11:00 and on days other than 2026-09-28.
- 2026 history OOS (entries only 2025-10-06..14).
- Live-at-entry regime (router still uses the day label).
- News/event tags; ATR=0 on 16/17/18; 14 after-hours; random expiry_chop n=3 LOW.
- 2-lot / 25-lot partial-fill addon (not re-run this pass).

### Gap addressed
- The four review bugs that invalidated the first Exit Lab headlines.

### Known risks
- Random set is CE-heavy (wing coverage). That is disclosed in the sanity table, not hidden.
- V2 entry set is a 1m-direction selector proxy.
- 25-lot vs 1-lot rupees are not comparable.

### Next steps
- More V2 days with bid/ask before trusting the spread table out of the morning bucket.
- More matched history weeks before any history OOS claim.
- Keep the playbook off.

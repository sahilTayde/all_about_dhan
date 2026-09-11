# Signal Lab — timeframe / gate / overlay grid on real premium tape (2026-09-11)

**Layer:** `VALIDATION` (measured on persisted SOURCE_FACT tape) · **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING` · NO_PROMOTE · no orders.
**Founder ask:** test the strategies across timeframes (1/3/5/10m), indexes, premiums, trends, volume profile, support/resistance; make our own permutations; validate; report what improved.

**Harness:** `trading_agents_india/signal_lab.py` + `scripts/run_signal_lab.py`. Replays persisted rolling ATM 1m CE+PE tape (`data/recon/premium_tape/`), resamples to 1/3/5/10m, emits rising-edge signals per combination, enters at the **next 1m bar open** (no lookahead), and scores each signal three ways: fixed-horizon forward return (15m/30m), max adverse excursion (30m), and an SL25%/TP50% shell replayed to EOD (stop-first on same-bar touch).

**Data:** 2026-09-09 (full session, 385 bars) + 2026-09-10 (to 14:36 IST, 262 bars) × NIFTY/BANKNIFTY/SENSEX × CE/PE. 1,764 signals across the grid. ITM tape untested — Dhan token expired the morning of 2026-09-11 before the ITM probe could run (founder must regenerate; live gather blocked that day).

## Grid

- **Timeframes:** 1m, 3m, 5m, 10m (resampled from 1m, IST-clock aligned).
- **Gates:** `dual_full` (MIX-DUAL 6-condition baseline) · `dual_novol` · `mrr_vwap` · `ema_trend` · `pullback` (our new permutation: EMA9>EMA21 + above VWAP + close pulled back to/below EMA9 — buy the dip, not the breakout).
- **Overlays:** `none` · `sr` (session S/R: entry only above opening-range high) · `vp` (entry only above session volume-profile POC) · `sr+vp`.

## Measured results (both days, all indices, gross)

Control first: **unconditional** 15m forward drift from every bar was near zero (−0.14% to +1.11% per index-side, SENSEX CE worst at −1.46% on its post-expiry day). Against that control:

| Rank (by shell P/L) | tf | gate | overlay | n | avg %15m | shell % |
|---|---|---|---|---:|---:|---:|
| 1 (least bad) | 1m | dual_full | none | 32 | −3.70 | **−3.61** |
| 2 | 1m | dual_full | vp | 22 | −3.95 | −7.29 |
| 3 | 1m | mrr_vwap | none | 286 | −2.72 | −8.10 |
| … | | | | | | |
| worst | 10m | mrr_vwap | vp | 9 | −3.72 | −14.52 |

Full table: `data/recon/signal_lab/signal_lab_2026-09-11_0930.json`. Every combination was negative on these two days; MAE within 30m was −10% to −16% everywhere.

## What the numbers actually say (the improvement)

1. **Breakout entries on ATM premium bought local tops.** Signals averaged −3.5% per 15m against a ~0% unconditional drift — the gates *selected* bad entries on these days. This is a measured anti-edge at fixed horizons, not noise: it held across 21 combos, 3 indices, both sides.
2. **MIX-DUAL's strictness is validated, not refuted.** The full 6-condition gate traded least (32 signals) and lost least (−3.6% shell vs −8 to −14% for every relaxation). Each condition we removed made it worse. The gate is a good *filter*; the problem is the day type.
3. **The two days were flat-IV decay days — and our own IV gather flagged it.** Chain IV entropy on 2026-09-10 measured ~0.999 (near-perfectly flat surface) across all three indices. Flat surface + near-zero drift + all-long-premium-entries-bleeding is exactly the day type `MIX-ALGO-IV-REGIME-HOLD` exists to suppress. This grid is its first supporting evidence: the improvement lever is **regime gating (don't buy premium on decay days)**, not entry tuning.
4. **Volume profile and opening-range S/R overlays hurt as implemented.** "Above POC" made every gate worse (above value = extended = deeper reversion); OR-breakout fired 22 times total at −5.3%. On chop days, breakout-of-breakout top-ticks. Parked as measured, revisit only on trend days.
5. **Pullback entries did not rescue decay days** (dips kept dipping), but 3m pullback was the only combo with a positive 15m average (+0.14%, n=14 — too small to claim anything). Worth re-measuring when trend-day tape exists.
6. **No timeframe rescued a bad day.** Higher timeframes reduced signal count but not the bleed.

## Accepted / Rejected / UNKNOWN

**Accepted:** signal_lab harness (12 tests total with premium-tape suite green); dual_full stays the MIX-DUAL spec unchanged; IV-entropy decay-day HOLD moves from HYPOTHESIS to "first supporting measurement"; VP/SR overlays recorded as measured-harmful on chop days.
**Rejected:** tuning entries on 2 decay days (overfit bait); promoting any combo; treating gross points as customer results; deleting the VP/SR ideas (they need trend-day tape before a verdict).
**UNKNOWN / DATA_INSUFFICIENT:** trend-day behavior (no trending session in the tape yet); ITM tape (token expired before probe); spot-side trend/S-R joins (index 1m bars not persisted per day); costs/slippage/fills; whether 3m-pullback's positive 15m survives more days.

**Next:** accumulate more tape days (ticker daily once token refreshed), rerun grid split by day type (IV entropy high/low), then let 02/06 formalize the HOLD threshold.

## Day-type split addendum (2026-09-11, 13:54 IST — includes a real down day)

Token refreshed; tickers ran live. 2026-09-11 was a trending down day (NIFTY PE session +53% at midday; skew tilt 1.3–1.8 vs 0.3–0.9 on the flat days). `scripts/run_signal_lab_daysplit.py` compared all three days, ATM plus (for 09-11) ATM+1/ATM-1 tape:

- **The anti-edge is regime-robust:** signals-minus-drift stayed negative on ALL three days, both sides, all moneyness: −1.9% to −3.7% per 15m. Even on the trend day, rising-edge breakout entries bought local premium tops. This is now a three-day, ~2,800-signal measurement, not a decay-day artifact.
- **3m beats 1m consistently** (pooled edge: 3m pullback −0.48% vs 1m pullback −3.62%; same ordering for ema_trend and mrr_vwap). The 1m timeframe chases noise. MIX-DUAL is specified on 1m — a 3m variant belongs in the next backtest grid.
- **The only green cells cluster on PE side + 3m + trend/pullback gates on falling days** (e.g. 09-10 NIFTY PE 3m pullback +4.4% @15m / +37% shell; 09-10 BANKNIFTY PE dual_novol shell +15.6%). Skew tilt was elevated exactly then — directional support for MIX-ALGO-SKEW-BUY's side-selection thesis (tilt picks PE), though every n is small.
- 12 of 139 combo-rows positive; none survive as a rule yet (n=3–11 each). No promote. What is promoted: **negative knowledge** — 1m breakout-chasing is measurably anti-edged on this product and should be excluded from future candidate designs.

Result files: `data/recon/signal_lab/daysplit_2026-09-11_1354.json` (+ partial-day run `daysplit_2026-09-11_1138.json`).

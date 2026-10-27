# BACKTEST — 5-year index price rules (2026-10-27)

**Now:** No price-only intraday rule tested here has an edge after option-buying costs. **Why:** ~230 variants, none significant (t>2) in both the in-sample half (2021-09..2024-12) and the out-of-sample half (2025-01..2026-09) with the same sign. **Next:** Stop mining candle patterns. Collect daily chain IV (Dhan has no IV backfill) and test volatility timing (buy premium only when the forecast move beats the implied move).

## Setup
- Data: `data/recon/ohlc/INDEX_IDX_I_{13,25,51}_1_*.json`, NIFTY / BANKNIFTY / SENSEX 1m, ~1240 days each.
- Code: `scripts/lab5y/lab.py` (engine + ORB, gap, VWAP-trend, morning momentum), `lab2.py` (prior-day high/low, NR7, reversion, trailing stops), `lab3.py` (ORB filtered by opening-range width).
- Fill: signal on bar close, entry next bar open. Stop/target on 1m high/low; both in one bar = stop.
- Cost (ITM option, delta ~0.75): 0.0133% of index per round trip (spread + charges) + 0.0045%/hour theta. That is ~3 NIFTY points per trade.

## Results (best of each family; full output from the scripts)
| Family | Best IS | Same rule OOS | Verdict |
|---|---|---|---|
| Opening-range breakout 15/30/60m, fixed or trailing stop | +1.5bp t=+0.8 | -4.5bp t=-2.2 | no edge |
| ORB only on wide-opening-range days | -0.3bp | -2.0bp | no edge |
| VWAP trend at 11:00 (SENSEX) | +5.0bp t=+2.2 | -1.4bp t=-0.6 | failed OOS |
| Gap follow 0.8% (SENSEX) | +13.5bp t=+2.0 | -12.4bp t=-1.5 | failed OOS |
| Gap fade 0.4/0.8% | negative | negative | no edge |
| Morning move → last-hour follow | negative t to -4.5 | ~0 | fading it is in-sample only |
| Prior-day high/low breakout (+NR7) | +6.0bp t=+1.9 (BANKNIFTY) | +1.3bp | no edge |
| 11:00 reversion after ±0.6/1% move | n too small | — | no edge |

Useful fact: the opening 30-min range predicts the rest-of-day range (corr 0.40 NIFTY, 0.47 SENSEX). Size of the move is forecastable; direction is not.

## Grok paper runs (Oct 13-22) — context
`data/recon/paper_extra/<day>.json`: 157 rows, +₹1.8L gross. Oct 13-19 rows filled 1m open→1m close (no spread). Oct 22, the first day with true ask entry / bid exit, lost ₹4.76L (2 of 24 wins). No placebo or random baseline was run. The early profit is not evidence of edge.

## Bugs fixed alongside (same PR)
1. `backtest_engine` never flattened at end of day (dead-band drop removed the 15:15 bar). Positions carried overnight. Fix: `clocks.flatten_at` flattens on the session's last bar and blocks entries there.
2. `simulate_sltp._hit_levels` filled gapped stops at the stop price. Now fills at the bar open when the bar gapped through it.
3. `paper_scalp`: a soft cancel (SIDEWAYS/ROLL) after 15:16 kept the ticket via the trail path. Now forced to FLATTEN_1516.
4. `paper_scalp`: `seen_low` (lowest since entry) was never reset when the stop moved. An old dip fired and priced the new stop. Now reset on every stop move.
5. `research_rules`: price-exited frozen-rule trades kept `spec_exit_min=15:14`. They held a slot and blocked the other side all day. Now `spec_exit_min = exit_min`.

Tests: `packages/backtest/tests/test_session_flatten.py`, `packages/desk-ml/tests/test_paper_scalp.py::test_trail_move_resets_seen_low_so_old_dip_cannot_stop`. Both fail on old code.

## Open items for founder
- `config/desk_risk.yaml` `day_stop_off_from: 2026-10-15` turns the paper daily loss stop off. Oct 22 lost ₹4.76L with no stop.
- Code uses STT 0.15% on option sell premium (`config/charges.yaml`). Confirm against the current Dhan charge sheet.
- Repo `.venv` is Python 3.9, but code needs 3.10+/3.11 (`str | X`, `datetime.UTC`). `tests/` and desk-ml tests cannot run there. Rebuild the venv on 3.12.

# MIX-DUAL-INDEX-MASTER — SENSEX CALL premium high-confluence scalp

**Team:** 04 · **Status:** `BACKTEST_REQUIRED` / `UNVALIDATED` / `customer_default: false` / `NO_PROMOTE`  
**Origin:** `PROJECT-DERIVED` founder Pine hypothesis, not a DhanHQ recipe and not `STRAT-015+`  
**Layer:** `HYPOTHESIS` until 06/09 review, realistic fills/costs, and live OHLC paper-watch replay.

This candidate is a current-testing/backtest book only. The market-hours loop may write paper-watch and `CANDIDATE_OBSERVATION` audit rows for it, but it must not rewrite `MIX-DEFAULT-BUY`, must not place orders, and must not publish a customer signal without the gate.

```yaml
mix_id: MIX-DUAL-INDEX-MASTER
origin: PROJECT-DERIVED
styles: [OPTION_BUYER, SCALPER]
markets: [SENSEX]
excluded_markets:
  NIFTY: "FAIL in 1m CALL premium cache pass"
  BANKNIFTY: "not part of the dual-index spec; avoid until separate risk/spot rules exist"
chart: "1m SENSEX CALL option premium"
spot_alignment:
  source: "SENSEX INDEX 1m previous completed bar"
  rule: "spot_close > spot_vwap and spot_close > spot_ema21"
premium_entry:
  all:
    - "premium close > premium MRR(VWMA20)"
    - "premium close > session VWAP"
    - "SuperTrend(10,3) bullish"
    - "EMA9 > EMA21"
    - "volume > SMA20(volume) * 1.3"
    - "time in 09:20-11:00 or 13:30-15:10 IST"
risk:
  SENSEX: {stop_points: 15, target_points: 30}
fills: "PROJECT backtest: next-bar open entry; stop/target from signal close; stop-first if one bar touches both"
status: BACKTEST_REQUIRED
paper_watch: true
paper_watch_role: "audit/blocker observation only"
customer_default: false
NO_PROMOTE: true
research_ready_for_programming: false
orders: REFUSED
```

## Latest Measured Shadow Backtest

Source report: `teams/06_backtesting/docs/MRR_BACKTEST_2026-09-10.md`.

| Market | Series | Trades | Win Rate | OOS Win Rate | Expectancy | OOS Expectancy |
|---|---:|---:|---:|---:|---:|---:|
| SENSEX CALL premium | 3 | 1,934 | 31.80% | 37.11% | 1.2809 | 4.8399 |
| NIFTY CALL premium | 3 | 5,439 | 19.12% | 22.59% | -4.5732 | -3.3988 |

These are gross premium points before brokerage, spread, slippage, taxes, liquidity, lot sizing, and Dhan fill validation. The positive SENSEX result is a research lead, not a claim.

## Accepted

- Keep only SENSEX in the working path for the current candidate.
- Keep NIFTY as a recorded failed arm, not a customer path.
- Avoid BANKNIFTY until a separate BANKNIFTY-specific design is written and tested.
- Record market-hours audit rows now so the candidate is not forgotten.
- Require live-loop option-premium OHLC persistence before any same-day paper-watch signal evaluation.

## Rejected

- Promoting measured win rate as a customer claim.
- Adding this to `MIX-DEFAULT-BUY`.
- Treating the Pine strategy as deployed code or an order path.
- Reusing this risk model for BANKNIFTY without separate evidence.

## UNKNOWN / DATA_INSUFFICIENT

- Real option fills, slippage, spread, brokerage, taxes, and depth-aware execution.
- Whether SENSEX result survives walk-forward by expiry week, strike bucket, and volatility regime.

## Premium tape (resolved 2026-09-10)

Current-day replay was blocked because paper-watch files did not persist OHLC arrays.
`trading_agents_india/premium_tape.py` now persists rolling ATM 1m CE+PE bars per day
(`data/recon/premium_tape/{UND}_ATM_1m_{day}.json`) and `score_dual_index_master`
evaluates the full premium gate (MRR/VWAP/SuperTrend/EMA/volume/window — identical math
to `scripts/backtest_mrr.py`) when the tape is present. First live validation
2026-09-10 ~13:36 IST: 262 bars, gate honestly FAILED (premium below MRR/VWAP,
SuperTrend bearish) → HOLD. Still `BACKTEST_REQUIRED` / `NO_PROMOTE`.

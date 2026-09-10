# MIX-ALGO-SKEW-BUY — chain IV-skew tilt directional CE/PE buy

**Team:** 04 (recipe from 01 research study) · **Status:** `BACKTEST_REQUIRED` / `UNVALIDATED` / `customer_default: false` / `NO_PROMOTE`  
**Origin:** `WEB-DERIVED` concept (Stratzy SkewHunter family + published IV-skew literature) rebuilt as a `PROJECT` club on our own Dhan-direct inputs. Not a copy of any marketplace algo — SkewHunter's exact trigger is `DATA_INSUFFICIENT`.  
**Layer:** `HYPOTHESIS` until the `chain_iv_stats` gather ticket lands, 06 backtests OOS, and 09 five-pass reviews.

Source study: [`DHAN_ALGO_MARKETPLACE_STRATZY.md`](../../../01_research/docs/DHAN_ALGO_MARKETPLACE_STRATZY.md). Marketplace returns cited there are marketing displays, never expectations here.

```yaml
mix_id: MIX-ALGO-SKEW-BUY
origin: WEB-DERIVED concept / PROJECT construction
styles: [OPTION_BUYER, INTRADAY]
markets: [NIFTY, SENSEX]
excluded_markets:
  BANKNIFTY: "no premium-tape/spot rules written; avoid until separate spec"
inputs:
  chain_iv_stats: "per-snapshot ATM±k skew tilt, smile curvature, IV entropy — chain_iv.py, live-validated 2026-09-10 14:22 IST; history accumulates only while a ticker/loop runs it (no Dhan backfill)"
  premium_tape: "rolling ATM 1m CE+PE bars (premium_tape.py, already persisting)"
  spot: "INDEX 1m previous completed bar"
side_pick:
  rule: "skew tilt beyond dead-band + tilt momentum in same direction"
  bullish: "put-side IV richening reverses / call demand firming -> candidate BUY_CE"
  bearish: "put-side smirk steepening with momentum -> candidate BUY_PE"
  dead_band: "REQUIRED — no signal inside the band; hysteresis before flipping side (feed-sensitivity lesson: SkewHunter took CE on Dhan and PE on Stratzy same day, 23-Jun-2026)"
entry_confirm:
  rule: "premium tape dual gate on the picked side must pass (MRR/VWAP/SuperTrend/EMA9>21/volume, window 09:20-11:00 or 13:30-15:10 IST) — skew picks the side, tape confirms the entry"
risk_shell:
  stop: "40% of entry premium, trailing (marketplace-common shell; parameter, not truth)"
  eod: "hard flat before close; no overnight long premium"
  positions: "one open evaluation at a time"
status: BACKTEST_REQUIRED
paper_watch: false
customer_default: false
NO_PROMOTE: true
research_ready_for_programming: false
orders: REFUSED
```

## Why this club (evidence, not vibes)

- **IV skew predicts direction in the literature:** Xing/Zhang/Zhao (JFQA 2010) — steep put smirk precedes underperformance; Fu et al. (2016) — IV skew the most predictive option-implied measure at 1w–3m; Ratcliff (JoD 2013) — OTM call−put IV difference carries weak next-day signal; Cremers-Weinbaum (2010) — deviations from put-call parity predict returns. Horizon caveat: most evidence is weekly+, our use is intraday — that gap is exactly what 06 must test.
- **Dhan sources every input directly:** option chain gives IV per strike, both sides, every 3s per unique underlying; premium tape already persists. No third-party feed — which is the point, given the feed-mismatch incident.
- **The wrapper matters:** the marketplace's own book shows the shell (TSL/RR/EOD flat) is half the product; we take the shell as explicit parameters instead of hidden defaults.

## Accepted

- Skew tilt + momentum as **side selection only**; the existing premium-tape dual gate remains the entry condition.
- Dead-band + hysteresis mandatory before any threshold flip (23-Jun-2026 CE/PE flip lesson).
- Both sides (CE and PE) always evaluated — one-sided books rejected (Only-Calls −36.91% 1y on the marketplace's own display).
- EOD hard exit; no overnight long premium.
- `chain_iv_stats` gather landed 2026-09-10 (`trading_agents_india/chain_iv.py` + `scripts/run_chain_iv_ticker.py`): parses `implied_volatility` per strike both sides from the documented `POST /optionchain` payload (desk_intel `parse_oc` drops it), computes skew tilt / curvature / normalized IV entropy over ATM±5, persists per-day snapshots to `data/recon/chain_iv/{UND}_iv_stats_{day}.json`. First live run (founder-invoked 5-min ticker, 14:22 IST): NIFTY tilt +0.68, BANKNIFTY and SENSEX ticking, IV present on all strikes. Remaining blocker is **history depth**: snapshots exist only while a ticker/loop runs; backtest needs weeks of accumulation.

## Rejected

- Copying SkewHunter parameters (undisclosed) or its displayed returns as expectations.
- Trading the raw skew threshold without dead-band.
- Promoting to `MIX-DEFAULT-BUY` or any customer surface before 06 OOS + 09 five-pass.
- Any order path.

## UNKNOWN / DATA_INSUFFICIENT

- SkewHunter's actual trigger, strike selection, SL logic, and why Index Sniper lost −261%.
- Whether weekly-horizon skew predictability survives at intraday horizon on NIFTY/SENSEX after costs.
- Correct k for ATM±k tilt, dead-band width, momentum lookback — all backtest grid parameters, not decisions.
- Intraday IV history depth: chain snapshots start when the gather ticket starts; no vendor backfill.

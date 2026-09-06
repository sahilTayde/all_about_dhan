# BACKTEST_SLTP — NIFTY named exits (2026-09-06)

**Team:** 06_backtesting  
**Status:** `HYPOTHESIS` / **UNVALIDATED** / **not a promote**  
**Command:** `python -m backtest_engine --dry-run --years 2 --interval 1 sltp`  
**JSON:** `data/recon/BACKTEST_SLTP_2026-09-06.json`  
**Cites:** [`MIX_CATALOG.md`](../../04_quant/docs/MIX_CATALOG.md) §9 · [`SL_TP_EXTERNAL_HARVEST.md`](../../01_research/docs/SL_TP_EXTERNAL_HARVEST.md)

**Entry (shared):** STRAT-003-style `all_three` lean on **INDEX** 1m→3m (equal-weight VWAP). **Not FUTIDX.**  
**Exit overlays under test:** ATR stop + R×2 target (`MIX-DESK-IQ-ATR-RR2`) vs Supertrend flip (`MIX-SLTP-ST-FLIP`).  
**GEX filter:** not applied — `DATA_INSUFFICIENT` on NIFTY.  
**Option RT cost:** not applied on INDEX proxy (would be nonsense vs premium %).

## Headline (honest)

| Book | OOS n | OOS wr | OOS exp | Rating |
|------|------:|-------:|--------:|--------|
| MIX-DESK-IQ-ATR-RR2 ATR14×1.5 R2 | 2144 | 30.0% | +0.29 | **FAIL** |
| MIX-DESK-IQ-ATR-RR2 ATR14×2.0 R2 | 1887 | 28.6% | −0.13 | **FAIL** |
| MIX-SLTP-ST-FLIP ST10×3 | 1430 | 43.2% | +1.16 | **FAIL** (IS weak; not promote) |
| Option cost overlay | — | — | — | **DATA_INSUFFICIENT** |

Keep `MIX-DEFAULT-BUY`. Do **not** promote ATR or ST-flip overlays. KEEP_ALL teacher STRATs.

ATR×1.5 reason mix (all): mostly `stack_exit` then `rr_target` / `atr_stop` — lean flip still dominates; SL/TP overlay is not a free edge on this INDEX proxy.

```text
HANDOFF
From: 06
To:   00 / 04 / 09
Accepted: named MIX SL/TP sims on NIFTY INDEX 3m; FAIL ratings; GEX skipped honestly;
  option-cost path marked DATA_INSUFFICIENT on index proxy.
Rejected: promote; invent wr for UI confidence; STRAT-015+; silent STOP_PTS as strategy.
UNKNOWN: FUTIDX continuous; NIFTY GEX; OPTIDX premium% path for MIX-SLTP-PREM-PCT.
```

# BACKTEST_SIDEWAYS_REGIME — INDEX 1m chop HOLD on 2026-09-16 tape

**Team:** 06 · **Overlay:** paper `index_regime` TREND | SIDEWAYS | UNKNOWN  
**Layer:** `HYPOTHESIS` · **NO_PROMOTE** · gate not `RESEARCH_READY_FOR_PROGRAMMING`  
**CLI:** `python -m desk_ml paper-scalp --replay --source dual-tape --live-session --session-date 2026-09-16`

Same dual-tape IST session as the Groww+STT board. SIDEWAYS skips **new** paper opens only (dealer + logit + TV-EP + clones). Flatten/cancel still run. Not a MIX-DEFAULT-BUY write. Not a promote.

Kaufman efficiency + 1m direction flips + tight high-low vs mean |close change|. INDEX path only. Not option L2. Not MIX-ML-LOGIT-XR (that is 3m ATR expansion AND logit; with `deny_model_signals=false` XR cloned dealer when the XR filter skipped).

## Prior board (no SIDEWAYS skip, same day after Groww+STT)

From `ML_PAPER_DASHBOARD.md` before this overlay: filled **659** · W 168 / L 491 · paper wr **25.49%**. Gross ₹35289.75 · charges ₹42422.65 · **net ₹−7132.9**. Unique books net ₹4584.78 (NIFTY ₹4456.86 · BANKNIFTY ₹5337.33 · SENSEX ₹−5209.41). MIX-ML-LOGIT unique winner ₹5957.62. MIX-ML-GREEKS 0 fills. Exact prior `n_sl_hit` **DATA_INSUFFICIENT** (board did not publish the count).

Founder ~**57%** wr during live cash hours is their in-session PAPER observation. It is **not** this EOD filled hit rate after Groww+STT.

## After SIDEWAYS_HOLD (this run)

| Metric | Value |
|--------|-------|
| n_filled | 276 |
| n_cancelled | 129 |
| W / L | 70 / 206 |
| paper wr% | 25.36 |
| n_skip_sideways (book×bar) | 1987 |
| n_sideways_bars | 266 |
| n_sl_hit (filled) | 150 |
| Gross ₹ | 23069.00 |
| Charges ₹ (Groww+GST+STT VERIFY) | 18031.08 |
| **Net ₹ (8 books)** | **5037.92** |
| Unique net ₹ | 4899.76 |
| Unique NIFTY / BANKNIFTY / SENSEX | −4720.76 / 7664.82 / 1955.70 |
| MIX-ML-LOGIT net ₹ (filled 39) | 4577.74 |
| MIX-DEFAULT-BUY net ₹ (filled 40) | 34.54 |
| MIX-ML-GREEKS | 0 fills |

Filled tickets by stamped regime: UNKNOWN 158 · TREND 118 · SIDEWAYS 0 (skip held).

## Verdict

`BACKTEST_REQUIRED`. All-books net flipped green mostly because clone books stopped opening in chop (same dealer P/L copied 4×). Unique net only **+315 ₹** vs prior. Paper wr stayed ~25% — **not** the founder 57% live-hours print. Unique NIFTY flipped red; unique SENSEX flipped green. **NO_PROMOTE.** Do not retune MIX-DEFAULT-BUY.

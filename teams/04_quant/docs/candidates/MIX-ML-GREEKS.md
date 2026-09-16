# MIX-ML-GREEKS — Dhan chain greeks paper book (TOKEN_ML ML-2 stand-in)

**Team:** 04_quant · **Code:** `packages/desk-ml` (`greeks_ml.py`, `LIVE_BOOKS`)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **NO_PROMOTE**  
**Origin:** `PROJECT-DERIVED` (Natenberg/McMillan/HAUS use of **vendor** greeks; fields are Dhan `SOURCE_FACT`)  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`  
**Not:** `STRAT-015+`. Does **not** rewrite `ml001-v1`. Not customer default.

## What 04 accepted

Greeks go into **ML-2 / ticket overlay**, not KMeans. Side still from INDEX vs premium tape. Missing Dhan greeks → this book **skips** (`GREEKS_MISSING`), it does not clone the dealer.

| Greek / IV | Quant use | Paper rule (`ml-greeks-v1`) |
|------------|-----------|------------------------------|
| **delta** | Moneyness; skip cheap-delta longs (HAUS ~40Δ) | Skip \|delta\| &lt; 0.45; strike pick 0.45–0.70 already on tickets |
| **IV** | Do not buy rich vol | Skip IV ≥ 20 or IV ≥ 1.15× session median; flat wing IV → `IV_FLAT_REGIME_HOLD` (cousin of `MIX-ALGO-IV-REGIME-HOLD`) |
| **theta** | Long premium pays decay | Skip if \|theta\|/entry ≥ 0.06 **and** clock ≥ 14:00 IST |
| **gamma** | Path speed | Note only unless stacked with cheap delta (delta skip already fires) |

## Bind

Parallel paper book `MIX-ML-GREEKS` on dual-tape `--paper-scalp`. Tomorrow: same CLI. **NO_PROMOTE.**

## HANDOFF

```text
MIX / STRAT: MIX-ML-GREEKS
Origin tags: PROJECT-DERIVED overlay. Dhan greeks = SOURCE_FACT fields.
Entry hypothesis: none. Uses dealer/index side. Greeks HOLD/skip only.
Confirm-or-kill: IV rich / late theta / missing chain / low delta.
Hold / veto rules: this book only. Does not veto MIX-DEFAULT-BUY.
Feasibility rules: dealer still kills fantasy SL. Existing path stop/target.
Parameters to grid: IV_RICH_ABS {18,20,22}; THETA_BLEED {0.04,0.06,0.08}; late clock 13:30/14:00.
Backtest request: paper-scalp --source dual-tape --live-session on 2026-09-16 tape vs MIX-DEFAULT-BUY.
Customer copy allowed: none (internal paper book).
Internal-only: ml-greeks-v1 reasons.
UNKNOWN / DATA_INSUFFICIENT: ticks before greeks parser had null wings; SENSEX |theta|/entry often large.
```

# Exam note — levels (S/R, round strikes, session extremes)

**Layer:** `HYPOTHESIS` unless the print is a **measured** high/low on a named series  
**Chair:** phd_math · **NO_PROMOTE**

## What the oral wants

A **level** is a price we **name** and **test**. Round NIFTY 50/100 strikes, prior day H/L, opening range, VWAP, and max-OI strikes are **different constructors**. None is a law of motion. Crossing a level without a **side, clock, and fill model** is chart decoration.

Exchange circuit / halt levels are **SOURCE_FACT** when published. Teacher “liquidity pools” without a tape are folklore.

## Tokens for FTS

levels, support resistance, opening range, round strike, max OI strike, VWAP, session high low, HYPOTHESIS

## Desk mapping

| Constructor | Status on this desk |
|-------------|---------------------|
| Prior session H/L from INDEX OHLC | Measurable; still HYPOTHESIS as **edge** |
| Opening-range S/R overlay | Signal-lab: **hurt** as implemented on one cache |
| Round strike / ATM | Contract geometry — good for **sid pick**, not alpha |
| Max OI strike | Chain snapshot language (see smart-money note) |
| Chart Fib / ICT pool | EXTERNAL / PARKED unless a named MIX + OOS |

**Compute:** min/max, OR high/low, session VWAP (volume>0; else equal-weight **assume**).  
**Must not:** invent SGX/GIFT levels as NSE fact (`VERIFY`).

## DATA_INSUFFICIENT

No HQ ORB/CPR series API. DOM / heatmap levels: not served. Continuous FUTIDX for some MIX still `DATA_INSUFFICIENT`.

## Exam trap

Stacking five levels on `/` (indicator soup). Customer ticket: **one** lean + chain + news. Engine may keep a graveyard of MIX-level ideas (KEEP_ALL / named MIX).

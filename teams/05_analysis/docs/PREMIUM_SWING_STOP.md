# MIX-SLTP-SWING-STOP — PAPER option stop (underlying swing)

**Team:** 05 talk · 04 levels · 06 backtest  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / PAPER only  
**Code:** `backtest_engine.levels.recent_swing_underlying_stop` + `bind_option_premium_levels`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** No live orders.

## Layers

| Claim | Layer |
|-------|-------|
| Teacher ultimate stop = recent swing of **underlying**, not option-premium chart | `SOURCE_FACT` (HAUSZx-hYdY) |
| Fractal wing=2 confirmation on INDEX/FUTIDX bars | `HYPOTHESIS` PAPER placeholder |
| Mapping swing → option premium rupees (greeks) | `DATA_INSUFFICIENT` — refused |

## Rule (minimal PAPER)

1. When ATM option LTP binds: Entry = LTP; Target = entry×1.25 (`MIX-SLTP-PREM-PCT` / STRAT-002).
2. When bars exist: `index_stop` = `stop_underlying` = last confirmed fractal swing  
   - BUY CE → swing **low**  
   - BUY PE → swing **high**
3. Customer ticket **premium** `stop` stays `DATA_INSUFFICIENT` unless an explicit `stop_pct` is passed. Do **not** invent a silent 20–30% premium stop.
4. Chart / research may show `index_stop`. Orders refused.

## Why premium Stop can still read DI

Teacher rejected premium-% auto-stops (wick then recover). Without a greek map, putting index points into the premium Stop slot would fail `INDEX_AS_PREMIUM` validation. Honest PAPER: swing bound on underlying; premium Stop DI with `stop_gap` citing `MIX-SLTP-SWING-STOP`.

## Done-when (not claimed)

- [ ] Greek / delta map validated (02/03) for optional premium Stop mirror  
- [ ] OOS + NORMAL backtest on swing wing (06) before any promote  
- [ ] Customer `/` copy shows “Stop on underlying” without index masquerade

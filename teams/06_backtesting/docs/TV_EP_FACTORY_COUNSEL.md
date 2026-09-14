# TV-EP factory design — joint counsel (one shot)

**Scope:** factory design only. Not each Editor Pick. **NO_PROMOTE.**

**Status:** keys present — model text is REVIEW, not a promote.

## gemini

```text
1) AGREE. Registry + Cartesian grid (TFs, underlyings, tapes) + stub rows scale ~1000 MIX-TV-EP-* tests cleanly.
2) Index spot/future tape vs option PREMIUM tape MUST remain strictly separated; mixing spot direction with option fills creates illusory P/L.
3) Quant rule: Port public underlying signals (sma_cross, macd_hist) via delta-weighted or synthetic forward volatility pricing to test premium tapes without spot-bias leaks.
4) NEVER claim live readiness, guaranteed alpha, or statutory fee accuracy from paper scores.
5) PRESERVE STRAT-001–014; new runs use MIX-TV-EP-* IDs exclusively.
6) EMPTY NEWS_CALENDAR defaults status to DATA_INSUFFICIENT.
7) COSTS: HYPOTHESIS_OPTION_RT_1PCT applied; statutory costs unknown.
8) REGIME: SMA50 slope threshold defines TREND vs RANGE.
9) NO live Dhan execution or promotion; paper artifacts route to `tv_ep_leaderboard.json`.
10) NO Pine Script code dumps allowed.
11) NO customer-facing promises.
12) NO STRAT-015+ IDs generated.
```

## openai

```text
1) AGREE: using a registry + grid + adapter “stub” scaffolding is the right way to scale hundreds–thousands of TV EPs while keeping backtests reproducible and paper-only.  
2) INDEX vs PREMIUM MUST stay separate: treat them as different market-data feeds/instruments (and therefore different option-implied/P&L logic if PREMIUM is derived); never reuse INDEX OHLC for PREMIUM-based returns or costs.  
3) Port-effectiveness (01/04): enforce a single “tape abstraction” layer—normalize timestamps, symbol mapping, and return/cost models per tape; then make PREMIUM testable by routing its feed through the same adapter interface (but with its own price/mark conventions and any derived fields).  
4) MUST NOT be claimed: any implied accuracy/win-rate, statistical edge, “tested_pass”, live deployability, statutory/real cost correctness, event/news impact, or any strategy performance—this board is PAPER + “SCORE_SAMPLE DATA_INSUFFICIENT” for event days.
```

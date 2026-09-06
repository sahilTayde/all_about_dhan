# 02 — Math notes on Usman Ashraf + Brando/Leaf CF binds (Phase-9)

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` on computability — **not** a veto of guest recipes  
**Binds:** [`6Bdv-_YUQ0s_BIND.md`](../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md), [`yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)

## Usman Ashraf (`6Bdv-_YUQ0s`)

| Piece | Verdict | Note |
|-------|---------|------|
| CE/PE buyer payoff (max loss = premium) | `supported` as identity | Education |
| Delta / gamma / theta / vega definitions | `supported` as greek taxonomy | Needs series to trade |
| IV expands premium | `supported` qualitatively | Numeric IV surface DI |
| Strike pick by OI/volume | `DATA_INSUFFICIENT` without chain | Do not invent OI |
| 0DTE gamma velocity | `context-dependent` | Calendar + greeks required |
| Mon–Fri weekly size by theta | `partially_supported` as management math | Illustrative % not frozen |
| Price/level stop vs premium % stop | `supported` as management preference | Entry LOI missing |
| Scale 30/20/20/30 / ITM 50% | `context-dependent` | Discretion |
| Reject size-to-zero (his) | `supported` as preference | KEEP_ALL vs Brando |
| % return / seven-figure anecdotes | `unsupported` as product metrics | |

## Brando / Leaf (`yLuH8YZXORQ`)

| Piece | Verdict | Note |
|-------|---------|------|
| HTF S/R map (daily/weekly) | `supported` as level class | “Major” ID heuristic |
| Reclaim prior major after selloff | `supported` as OHLC predicate | Multi-year majors ADD |
| Round-number break | `partially_supported` | Grid step HYPOTHESIS |
| News/data catalyst align | `DATA_INSUFFICIENT` without event join | |
| Quick bounce at HTF level | `partially_supported` | Touch+reject grid |
| Size-for-zero options risk | `supported` as management identity | Premium ledger DI |
| $6k→$10M / “80%+” rhetoric | `unsupported` as product metrics | |
| 5m/10m as prime | `unsupported` per teacher | |

## ADD (HYPOTHESIS params for proxy only)

- Brando reclaim: `swing_days` ∈ {10,20,40}; `confirm_bars` 4–12.  
- Brando round: `round_step` ∈ {50,100,500} on NIFTY.  
- Brando bounce: `touch_frac` / `bounce_frac` grid.  
- ATR(14)×1.5 / R2 when teacher stop unknown.  
- Do **not** ADD synthetic OI/gamma from OHLC.

## Do not

- Veto / delete `MIX-CF-USMAN-*` or `MIX-CF-BRANDO-*`.  
- Club Usman price-stop with Brando size-zero into one row.  
- Invent OPTIDX greeks/OI or India Fed-tariff headlines.  
- Promote title equity curve into confidence UI.

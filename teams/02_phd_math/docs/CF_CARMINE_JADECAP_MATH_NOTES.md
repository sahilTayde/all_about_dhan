# 02 — Math notes on Carmine Rosato + Jadecap CF binds (Phase-8)

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` on computability — **not** a veto of guest recipes  
**Binds:** [`UhkRRqO1gQM_BIND.md`](../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md), [`8OX-mcSHWhg_BIND.md`](../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md)

## Carmine Rosato (`UhkRRqO1gQM`)

| Piece | Verdict | Note |
|-------|---------|------|
| Passive vs aggressive auction | `supported` as taxonomy | Not an entry signal alone |
| Absorption (aggressors, no follow-through) | `DATA_INSUFFICIENT` without tape | Needs delta/DOM/footprint |
| CLC (context/location/confirm) | `context-dependent` | Location = LOI predicate |
| Sweep PDH/PDL then reclaim | `supported` as OHLC predicate | Volume-tail ADD optional |
| Hold opening print after pullback | `partially_supported` | Needs session open + early clock |
| P/B footprint shape | `DATA_INSUFFICIENT` without VAP | |
| Constant dollar risk / RR focus | `supported` as management math | Not entry |
| May $203k / 33% wr anecdotes | `unsupported` as product metrics | |

## Jadecap (`8OX-mcSHWhg`)

| Piece | Verdict | Note |
|-------|---------|------|
| PDH/PDL raid + close reclaim | `supported` as OHLC predicate | Confirm-bar grid |
| Asia/London range before NY | `DATA_INSUFFICIENT` for NSE clocks | Session boxes unmapped |
| Midnight open ±1–2× Asia range | `DATA_INSUFFICIENT` | US clock multiples |
| 3-candle FVG after liq taken | `partially_supported` | Classic imbalance; ICT stack not frozen |
| Time-exit ~11–12 ET | `context-dependent` | Management, not entry |
| Apex payout records | `unsupported` as product metrics | |

## ADD (HYPOTHESIS params for proxy only)

- Carmine fail-break / Jade swing-fail: `confirm_bars` 3–8.  
- Carmine open-hold: early IST window; `hold_frac`.  
- Jade FVG: require prior same-day PDH/PDL sweep before FVG lean.  
- ATR(14)×1.5 / R2 when teacher stop unknown.

## Do not

- Veto / delete `MIX-CF-CARMINE-*` or `MIX-CF-JADECAP-*`.  
- Invent synthetic delta/DOM or NSE Asia/London boxes.  
- Club geometry with Marco/Kane/TG into one row (KEEP_ALL separate).  
- Promote dollar P/L / payout ads into confidence UI.

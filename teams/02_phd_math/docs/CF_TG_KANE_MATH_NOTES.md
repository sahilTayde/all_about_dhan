# 02 — Math notes on TG Capital + Trader Kane CF binds (Phase-6)

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` on computability — **not** a veto of guest recipes  
**Binds:** [`ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md), [`HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)

## TG Capital (`ADnslyKOwFE`)

| Piece | Verdict | Note |
|-------|---------|------|
| 3-candle FVG + CE (50%) | `partially_supported` | Classic imbalance geometry; exact wick rules HYPOTHESIS |
| Doji + next close below doji high | `partially_supported` | Doji = small body / range ratio grid |
| London 2:30–3:00 preference | `context-dependent` | Clock filter separate from pattern |
| EMA 5/9/13\|15/21 stack | `partially_supported` | 13 vs 15 ASR UNKNOWN — ADD both in ablation |
| 200 EMA bias | `supported` as filter math | HQ annexure includes EMA200 |
| Min 1:20 RR / “90% wr” | `unsupported` as product metrics | Title marketing |
| Gold close-below SL | `context-dependent` | Event-driven wick regime |
| ATR stops | `HYPOTHESIS` add-on | **Not** spoken — proxy only |

## Trader Kane (`HNuRp9Z1bMs`)

| Piece | Verdict | Note |
|-------|---------|------|
| 50% EQ of swing range | `partially_supported` | Midpoint of confirmed swing H–L |
| Nested 50%-of-50% | `context-dependent` | Redraw / fail-EQ rules discretionary |
| PO3 / AMD sweep→reverse | `partially_supported` | Structurally similar to sweep-reclaim |
| Multi-TF PO3 boxes | `context-dependent` | Needs daily/H4/H1 state machine |
| SMT NQ vs ES | `DATA_INSUFFICIENT` on single NIFTY series | Do not fake second symbol |
| Inversion of imbalance | `partially_supported` | Needs prior gap definition |
| Aggressive BE | `supported` as management rule | Not an entry signal |
| Host payout / week wr | `unsupported` as product metrics | |

## ADD (HYPOTHESIS params for proxy only)

- TG: `ema_mid ∈ {13,15}`; doji `body/range ≤ 0.35`; FVG min gap as fraction of ATR.  
- Kane: swing lookback; EQ touch tolerance; PO3 confirm_bars (reuse sweep grid).  
- ATR(14)×1.5 / R2 when teacher pip/tick stop unknown.

## Do not

- Veto / delete `MIX-CF-TG-*` or `MIX-CF-KANE-*`.  
- Invent NIFTY GEX/OF or synthetic ES SMT from noise.  
- Promote title “90%” into confidence UI.

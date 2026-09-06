# 02 — Math notes on Umar Ashraf + Forest Knight CF binds (Phase-7)

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` on computability — **not** a veto of guest recipes  
**Binds:** [`IUo5AwmsE9A_BIND.md`](../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md), [`q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)

## Umar Ashraf (`IUo5AwmsE9A`)

| Piece | Verdict | Note |
|-------|---------|------|
| Gap-down vs prior close | `supported` as OHLC predicate | Gap % threshold ADD grid |
| Early-session failed bounce → short | `partially_supported` | Needs session clock + lower-high / close rule |
| “No follow-through” volume/activity | `context-dependent` | OF tape preferred; bar volume is stand-in |
| Opening drive full recipe | `DATA_INSUFFICIENT` | Named only |
| R-multiple tracking / ≤1R loss | `supported` as management math | Not an entry signal |
| Dynamic size staircase 20–30% | `supported` as sizing rule | Not entry |
| ATR stops | `HYPOTHESIS` add-on | **Not** spoken — proxy only |
| Host payout / “profitable” ads | `unsupported` as product metrics | |

## Forest Knight (`q_MdVlZ1SH4`)

| Piece | Verdict | Note |
|-------|---------|------|
| Relative volume > prior bar | `partially_supported` | Needs volume series; INDEX volume UNKNOWN quality |
| Doji / hammer / shooting star | `partially_supported` | Body/wick ratio grid |
| Wait for candle close | `supported` | No look-ahead |
| PDH/PDL touch confluence | `supported` as level math | Overnight H/L map DI |
| True volume-at-price POC/VA | `partially_supported` via bin proxy | Equal-weight if vol=0 — honesty gap |
| VA ≈ 70% | `context-dependent` | Textbook default; not teacher-proof |
| “100% react at shelf” | `unsupported` as product metric | Rhetoric |
| Options OI histogram | `partially_supported` conceptually | Separate data path; not this OHLC book |

## ADD (HYPOTHESIS params for proxy only)

- Umar: `gap_frac`; early window minutes (IST stand-in); bounce fail = lower high within N bars.  
- Forest: doji `body/range ≤ 0.35`; wick frac; profile `bins=24`, `va_frac=0.70` ablation.  
- ATR(14)×1.5 / R2 when teacher stop unknown.

## Do not

- Veto / delete `MIX-CF-UMAR-*` or `MIX-CF-FOREST-*`.  
- Invent opening-drive geometry or synthetic VAP ticks.  
- Promote rhetoric “100%” / payout ads into confidence UI.

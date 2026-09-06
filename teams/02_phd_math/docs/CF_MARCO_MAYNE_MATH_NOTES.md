# 02 — Math notes on Marco + Mayne CF binds (Phase-4)

**Team:** 02_phd_math  
**Date:** 2026-09-06  
**Layer:** `VALIDATION` on computability — **not** a veto of guest recipes  
**Binds:** [`DAnXM7C16h0_BIND.md`](../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md), [`coBMd1vk2Lo_BIND.md`](../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md)

## Marco (`DAnXM7C16h0`)

| Piece | Verdict | Note |
|-------|---------|------|
| Resting-stop / sweep-reclaim language | `partially_supported` | OHLC can proxy sweep+close-back; “respect/induce” narrative underdefined |
| Equal highs/lows pools | `partially_supported` | Needs epsilon HYPOTHESIS |
| Strict opposing-sweep wait | `context-dependent` | State machine possible; many paths = SKIP |
| Retail OB/FVG as induce only | `context-dependent` | Not required for proxy arms |
| Guest/host payout claims | `unsupported` as product metrics | |
| ATR stops | `HYPOTHESIS` add-on | **Not** spoken — proxy only |

## Mayne (`coBMd1vk2Lo`)

| Piece | Verdict | Note |
|-------|---------|------|
| 3-candle swing + close MSB | `partially_supported` | Computable on OHLC |
| Range 50% premium/discount | `partially_supported` | Classic midpoint |
| Order-block candle combine | `context-dependent` | Last down vs multi-candle = grid |
| Breaker sweep+MSB | `partially_supported` | Structure proxy; HTF OB gate often missing on single TF |
| Min 2:1 RR filter | `partially_supported` as ticket preference | Not expectancy proof |
| FVG “sponsorship” | `context-dependent` | Gap detection possible; not frozen |
| Guest wr / $10M marketing | `unsupported` as product metrics | |

## ADD (HYPOTHESIS params for proxy only)

- Marco equal-high epsilon: fraction of ATR or pts grid.  
- Mayne swing lookback N∈{3,5} ablation.  
- ATR(14)×1.5 / R2 when teacher stop distance unknown.

## Do not

- Veto / delete `MIX-CF-MARCO-*` or `MIX-CF-MAYNE-*`.  
- Invent NIFTY GEX/OF filters for these recipes.

# Classic SL/TP methods (citable free sources)

**Team:** 01_research (+ 02 VALIDATION later)  
**Date:** 2026-09-06  
**Origin:** `WEB-DERIVED` / `EXTERNAL` — not Dhan video recipes.  
**Use:** parameter grids for `MIX-SLTP-*` only. Not proof of edge.

| Method | Formula / rule | Typical params | Cite (free) | Well-defined? |
|--------|----------------|----------------|-------------|---------------|
| ATR stop from entry | `stop = entry ± k × ATR(n)` | Wilder ATR **n=14**, k∈{1.0,1.5,2.0,3.0} | Wilder ATR (standard TA); StockCharts ATR pages | **YES** if n,k, bar TF fixed |
| Chandelier exit | Long: `HH(n) − k×ATR(n)`; short: `LL(n)+k×ATR` | n=22, k=3.0 (StockCharts default) | [StockCharts Chandelier Exit](https://school.stockcharts.com/doku.php?id=technical_indicators:chandelier_exit) (Le Beau) | **YES** with ratchet rule |
| R-multiple target | `target = entry ± R × |entry−stop|` | R=2 common | Van Tharp-style R framing (education) | **YES** once stop defined |
| Swing high/low | Stop beyond prior swing | Lookback UNDERDEFINED | Classic PA / Murphy-style | **UNDERDEFINED** without swing rule |
| Premium % TP | Exit when option LTP ≥ entry×(1+p) | p=0.20–0.30 | Teacher STRAT-002 | **YES** on option tape |
| Supertrend flip | Exit when close crosses ST | ATR(10)×3 (STRAT-003 WEAK) | Teacher STRAT-003 | **YES** as compute; param WEAK |

**02 note:** Prefer ATR Wilder recursive seed. Do not silently swap SMA-TR for Wilder.

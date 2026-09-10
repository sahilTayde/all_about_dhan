# MRR Pine Shadow Backtest

Generated: `2026-09-10T12:27:49+05:30`

This is a measured shadow backtest only. `validated=false`, `promote=false`, and orders stay refused.

## Assumptions
- Pine files are indicators, not strategies; this harness defines entries/exits for measurement only.
- Only regular-session chart bars are used: 09:15-15:30 IST.
- Trend-gated variants are PROJECT-derived: EMA9/EMA21/EMA50 alignment plus 5-bar MRR slope on 1m candles.
- Fills use next bar open after the signal close to reduce look-ahead bias.
- MRR Pine 1 index proxy: bullish crossover = CE proxy, bearish crossunder = PE proxy; exit/reverse on opposite signal.
- MRR Pine 1 premium chart: bullish crossover buys that option premium; bearish crossunder exits.
- Combined script: any SWEEP/BREAKOUT/FIB marker enters long; close below MRR exits; no target/SL was present in Pine.
- MRR V2 high-confluence: MRR retest + EMA9>EMA21 + volume > SMA20*1.3 + 09:20-11:00/13:30-15:10 windows; 12-point stop and 24-point target anchored to signal close.
- MRR V2 spot-aligned premium variant: CALL premium entries require index close > index MRR and EMA9>EMA21; PUT premium entries require index close < index MRR and EMA9<EMA21 on the same 1m bucket.
- Master Option Scalper is tested on CALL premium charts only: close > MRR/VWAP, SuperTrend bullish, EMA9>EMA21, RSI>50, previous completed 5m close > 5m EMA21, volume spike or bull sweep, and the same time windows.
- Dual-Index Master is tested on NIFTY and SENSEX CALL premium charts only: option close > MRR/VWAP, SuperTrend bullish, EMA9>EMA21, volume spike, time window, and previous 1m spot close > spot VWAP and EMA21.
- Dual-Index Master risk uses NIFTY 10/20 points and SENSEX 15/30 points exactly as requested.
- MRR V2 bracket ambiguity is conservative: if a bar touches both stop and target, stop is counted first.
- Positions flatten after 15:15 IST; no new entries after 15:00 IST.
- Premium results are gross premium points before brokerage, spread, slippage, fills, taxes, lot sizing, and liquidity filters.

## Historical Index Proxy
| Underlying | Bars | Script | Trades | Win Rate | OOS Win Rate | Expectancy Pts | OOS Expectancy |
|---|---:|---|---:|---:|---:|---:|---:|
| NIFTY | 464524 | mrr_pine_1 | 51928 | 0.2634 | 0.2635 | 0.0978 | 0.3604 |
| NIFTY | 464524 | mrr_pine_1_trend | 3853 | 0.4093 | 0.3956 | 2.8924 | -1.5881 |
| NIFTY | 464524 | mrr_combined | 5987 | 0.2941 | 0.2763 | -0.3435 | 0.3473 |
| NIFTY | 464524 | mrr_combined_trend | 1644 | 0.3017 | 0.2979 | -0.3071 | 0.0795 |
| NIFTY | 464524 | mrr_v2_high_confluence | 327 | 0.3150 | 0.3030 | -0.9104 | -1.7258 |
| BANKNIFTY | 463178 | mrr_pine_1 | 55146 | 0.2504 | 0.2646 | -1.6633 | 0.5076 |
| BANKNIFTY | 463178 | mrr_pine_1_trend | 4118 | 0.3813 | 0.3677 | -0.9667 | -4.6191 |
| BANKNIFTY | 463178 | mrr_combined | 7014 | 0.2794 | 0.2986 | -3.8202 | 2.9781 |
| BANKNIFTY | 463178 | mrr_combined_trend | 2078 | 0.2945 | 0.2957 | -6.0995 | 3.3016 |
| BANKNIFTY | 463178 | mrr_v2_high_confluence | 572 | 0.3182 | 0.2957 | -0.6906 | -1.8604 |
| SENSEX | 463213 | mrr_pine_1 | 52740 | 0.2561 | 0.2468 | -0.3104 | -1.6907 |
| SENSEX | 463213 | mrr_pine_1_trend | 3989 | 0.3913 | 0.3822 | 1.0885 | -11.3510 |
| SENSEX | 463213 | mrr_combined | 6354 | 0.2852 | 0.2675 | -1.7960 | -1.9335 |
| SENSEX | 463213 | mrr_combined_trend | 1812 | 0.2826 | 0.2865 | -1.1615 | -1.0390 |
| SENSEX | 463213 | mrr_v2_high_confluence | 479 | 0.3841 | 0.3438 | 1.3768 | -0.0073 |

## Historical Option Premium Summary
| Underlying | Script | Series | Trades | Win Rate | OOS Win Rate | Expectancy Pts | OOS Expectancy |
|---|---|---:|---:|---:|---:|---:|---:|
| BANKNIFTY | master_option_scalper | 3 | 10478 | 0.2306 | 0.2632 | -0.1806 | 1.5733 |
| BANKNIFTY | master_option_scalper_spot_aligned | 3 | 4366 | 0.2302 | 0.2746 | -0.1129 | 2.6506 |
| BANKNIFTY | mrr_combined | 6 | 118158 | 0.2907 | 0.3156 | -7.5737 | -6.6416 |
| BANKNIFTY | mrr_combined_trend | 6 | 47708 | 0.2939 | 0.3175 | -8.7372 | -8.1923 |
| BANKNIFTY | mrr_pine_1 | 6 | 323914 | 0.2997 | 0.3203 | -7.4116 | -6.5867 |
| BANKNIFTY | mrr_pine_1_trend | 6 | 60506 | 0.3025 | 0.3278 | -7.9673 | -7.1189 |
| BANKNIFTY | mrr_v2_high_confluence | 6 | 23071 | 0.2427 | 0.2522 | -2.2535 | -1.6633 |
| BANKNIFTY | mrr_v2_spot_aligned | 6 | 12022 | 0.2674 | 0.2668 | -1.4806 | -1.2046 |
| NIFTY | dual_index_master | 3 | 5439 | 0.1912 | 0.2259 | -4.5732 | -3.3988 |
| NIFTY | master_option_scalper | 3 | 7791 | 0.1708 | 0.1647 | -6.8774 | -7.0063 |
| NIFTY | master_option_scalper_spot_aligned | 3 | 4309 | 0.1541 | 0.1645 | -7.3346 | -6.8960 |
| NIFTY | mrr_combined | 6 | 92949 | 0.2569 | 0.2551 | -4.0235 | -4.2420 |
| NIFTY | mrr_combined_trend | 6 | 35378 | 0.2673 | 0.2686 | -4.8263 | -5.0199 |
| NIFTY | mrr_pine_1 | 6 | 270936 | 0.2737 | 0.2761 | -3.8829 | -4.0226 |
| NIFTY | mrr_pine_1_trend | 6 | 46683 | 0.2709 | 0.2723 | -4.2475 | -4.2609 |
| NIFTY | mrr_v2_high_confluence | 6 | 13859 | 0.1854 | 0.1802 | -6.2767 | -6.3958 |
| NIFTY | mrr_v2_spot_aligned | 6 | 7815 | 0.2019 | 0.1909 | -5.8531 | -6.0653 |
| SENSEX | dual_index_master | 3 | 1934 | 0.3180 | 0.3711 | 1.2809 | 4.8399 |
| SENSEX | master_option_scalper | 3 | 3027 | 0.3010 | 0.3201 | 1.8440 | 3.4111 |
| SENSEX | master_option_scalper_spot_aligned | 3 | 1241 | 0.3199 | 0.3720 | 3.4256 | 7.4002 |
| SENSEX | mrr_combined | 6 | 44287 | 0.2433 | 0.2832 | -8.9185 | -9.7198 |
| SENSEX | mrr_combined_trend | 6 | 13851 | 0.2714 | 0.2872 | -11.8067 | -11.3399 |
| SENSEX | mrr_pine_1 | 6 | 101832 | 0.2923 | 0.2905 | -9.8465 | -11.6138 |
| SENSEX | mrr_pine_1_trend | 6 | 16297 | 0.2906 | 0.2983 | -11.9436 | -13.6644 |
| SENSEX | mrr_v2_high_confluence | 6 | 6882 | 0.3082 | 0.3234 | 0.1188 | 1.3327 |
| SENSEX | mrr_v2_spot_aligned | 6 | 3675 | 0.3268 | 0.3365 | 1.3535 | 3.2942 |

## Current Loop
- Latest paper signal file day: `2026-09-10` updated `2026-09-10T12:26:22+05:30`.
- Lean counts: `{"BUY_CE": 10, "BUY_PE": 87, "HOLD": 65}`.
- MRR current-chart status: `DATA_INSUFFICIENT: today's paper-watch/probe files do not persist OHLC arrays needed to reproduce Pine indicators`.

## Required Next Step
- Persist current OHLC arrays from the running loop if you want true intraday MRR replay for today. Current paper-watch files store decisions/reasons, not enough candle data to recompute Pine.

# MIX-CF-TG-TRIDENT — Chart Fanatics TG Capital London FVG trident

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC FVG+doji proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `ADnslyKOwFE` · guest **TG Capital / Tyler**  
**Bind:** [`../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Marco / Mayne / Marci / Tori / Kane / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
title_90pct_wr: MARKETING_NOT_PRODUCT_METRIC
```

---

## Teacher recipe (SOURCE_FACT summary)

1. **London killzone only** (~3:00–6:30 a.m. NY); prefer FVG on 2:30/3:00 30m candles.  
2. After killzone **FVG**, want a **doji** that wicks consequent encroachment (50% of FVG).  
3. Next candle must **close below** doji high (long) — close above = invalidate.  
4. SL below pattern low (~10 pip FX spoken); gold prefers close-below; TP daily / min 1:20 personal.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_TG_TRIDENT_FVG` | 3-bar FVG + small-body wick into mid-gap + confirm close back through | No London clock; doji subjective; 30m→3m resample stand-in |
| London KZ → NSE | **Not mapped** | `DATA_INSUFFICIENT` |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS when pip SL unknown — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-TG-TRIDENT
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: ADnslyKOwFE, channel: chart-fanatics, guest: TG Capital / Tyler}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: FX_GOLD_NQ
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MARCI-RIZZY, MIX-CF-TORI-TL-BOUNCE, MIX-CF-TG-EMA-WAVE, MIX-CF-KANE-EQ50, MIX-CF-KANE-PO3-SMT, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike US→India transfer or title marketing wr.

# MIX-CF-TG-EMA-WAVE — Chart Fanatics TG Capital EMA stack + 200 bias

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC EMA-stack proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `ADnslyKOwFE` · guest **TG Capital / Tyler**  
**Bind:** [`../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md)  
**Separate theme** from `MIX-CF-TG-TRIDENT`. **Not** clubbed into Fabio / Marco / Mayne / Marci / Tori / Kane / STRAT / IQ / DEFAULT.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
```

---

## Teacher recipe (SOURCE_FACT summary)

1. EMAs **5 / 9 / 13-or-15 / 21** stacked as a “wave” (not intertwining) = bullish momentum filter.  
2. **200 EMA:** above = long bias; below = short bias / cut longs early.  
3. Same stack on **daily** for narrative; 30m entry “inside” strong daily candle.  
4. Exit cues: EMA cross, large opposing candle, IFVG — discretionary.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_TG_EMA_WAVE` | Close > EMA200 and EMA5>9>13>21 (or inverse); lean with stack after shallow pullback | ASR 13 vs 15; no TV “bull trading” candle paint; London window unmapped |

---

## YAML stub

```yaml
mix_id: MIX-CF-TG-EMA-WAVE
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TG-TRIDENT, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF, MIX-CF-KANE-EQ50, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not PhD transfer dislike.

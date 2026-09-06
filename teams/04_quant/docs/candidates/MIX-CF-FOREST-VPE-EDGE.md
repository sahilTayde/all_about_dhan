# MIX-CF-FOREST-VPE-EDGE — Chart Fanatics Forest Knight VPE signal at edge

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC + bar-volume proxy; not true VAP)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `q_MdVlZ1SH4` · guest **Forest Knight / Forest**  
**Bind:** [`../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF guests / STRAT / IQ / `MIX-DEFAULT-BUY`.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
rhetoric_100pct_react: MARKETING_NOT_PRODUCT_METRIC
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Mark PDH/PDL + overnight H/L; want confluence with VP **HVN edge**.  
2. Signal = candle with volume **> prior bar** + doji/hammer/shooting star in trade direction.  
3. Wait for **close**; SL beyond signal/node; TP edge-to-edge / next key level.  
4. HTF weekly/daily bias preferred.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_FOREST_VPE_EDGE` | Touch PDH/PDL (overnight DI) + relative-volume rejection candle | True VAP shelves; RTH clocks → NSE DI |
| INDEX volume | Bar volume / equal-weight if zero | Cash INDEX volume quality UNKNOWN |

Stops/targets: ATR(14)×1.5 / R×2 desk HYPOTHESIS when teacher ticks unknown.

---

## YAML stub

```yaml
mix_id: MIX-CF-FOREST-VPE-EDGE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: q_MdVlZ1SH4, channel: chart-fanatics, guest: Forest Knight}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: NQ_ES
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FOREST-POC-RETEST, MIX-CF-FABIO-MR-RANGE, MIX-CF-KANE-EQ50, MIX-CF-UMAR-MORNING-TOP, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because true VAP is unavailable on INDEX.

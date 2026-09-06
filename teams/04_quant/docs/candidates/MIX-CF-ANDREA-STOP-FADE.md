# MIX-CF-ANDREA-STOP-FADE — Chart Fanatics Andrea Cimi stop-run book-resilience fade

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC PDH/PDL sweep+fade proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `TvoQr6ObjnU` · guest **Andrea Cimi**  
**Bind:** [`../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md`](../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md)  
**Not** clubbed into Fabio / Carmine fail-break / Marco liq-trap / STRAT / IQ. No STRAT-015+.

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

1. Sweep daily high/low triggers stop cascade.  
2. Book emptied → path of least resistance often fades back.  
3. Fade spike for **short-term** mean reversion — **not** assume full-day reverse (~1/10).  
4. OF distinguishes stop-run vs absorption vs exhaustion (same shape).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_ANDREA_STOP_FADE` | Sweep PDH/PDL then quick close back through | No cascade tape; fade horizon ADD |

---

## YAML stub

```yaml
mix_id: MIX-CF-ANDREA-STOP-FADE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: TvoQr6ObjnU, channel: chart-fanatics, guest: Andrea Cimi}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: ES_NY
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-ANDREA-FAIL-AUCTION, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-JADECAP-SWING-FAIL]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL`. Guest “8/10” fade talk is **not** a product metric.

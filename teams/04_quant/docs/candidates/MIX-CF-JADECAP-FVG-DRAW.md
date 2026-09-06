# MIX-CF-JADECAP-FVG-DRAW — Chart Fanatics Jadecap liquidity→inefficiency / FVG

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC FVG-after-sweep proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `8OX-mcSHWhg` · guest **Jadecap** (Kyle)  
**Bind:** [`../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md`](../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / Carmine / `MIX-DEFAULT-BUY`.

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

1. Daily thesis: after major liquidity taken, draw toward **inefficiency** (FVG) or remaining opposing liquidity.  
2. Execution often FVG (his most-repped model); also MSS / turtle soup / breaker (not frozen here).  
3. Prefer buying weakness inside the developing daily candle when bullish draw intact.  
4. Invalidation: close beyond swing / daily low.  
5. TP often time/discretion — not always full equal highs.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_JADECAP_FVG_DRAW` | After PDH/PDL sweep, lean into 3-candle FVG in draw direction | Full ICT stack / breaker / turtle soup not modeled; daily narrative discretionary |

Stops/targets: ATR(14)×1.5 / R×2 desk HYPOTHESIS.

---

## YAML stub

```yaml
mix_id: MIX-CF-JADECAP-FVG-DRAW
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 8OX-mcSHWhg, channel: chart-fanatics, guest: Jadecap}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: NQ_ES_NY
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-JADECAP-SESSION-LIQ, MIX-CF-TG-TRIDENT, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MAYNE-BREAKER, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not because TG/Mayne also use FVG language (KEEP_ALL separate).

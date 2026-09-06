# MIX-CF-JADECAP-SWING-FAIL — Chart Fanatics Jadecap PDH/PDL swing failure

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC raid+reclaim proxy)  
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

1. Map prior-day (and recent untaken) highs/lows as stop pools.  
2. Wait for **raid** of PDL (or PDH).  
3. Do nothing until **close** back above PDL (long) / below PDH (short).  
4. SL beyond new extreme; TP opposing prior-day extreme.  
5. Do **not** short the first tick through PDH without reaction.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_JADECAP_SWING_FAIL` | Sweep PDH/PDL then close back through same day | 15m–1H teacher TF → 3m INDEX stand-in; ET session DI |

Stops/targets: ATR(14)×1.5 / R×2 when distance unknown — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-JADECAP-SWING-FAIL
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SESSION-LIQ, MIX-CF-JADECAP-FVG-DRAW, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-KANE-PO3-SMT, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not because Marco/Kane also have sweep themes (KEEP_ALL separate rows).

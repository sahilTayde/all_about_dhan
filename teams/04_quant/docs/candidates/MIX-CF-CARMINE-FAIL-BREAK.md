# MIX-CF-CARMINE-FAIL-BREAK — Chart Fanatics Carmine Rosato failed breakdown / stop hunt

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC sweep+reclaim proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `UhkRRqO1gQM` · guest **Carmine Rosato**  
**Bind:** [`../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md`](../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / Jadecap / `MIX-DEFAULT-BUY`.

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

1. Consolidate / build near a low (or high).  
2. Market **sweeps** consolidating extreme or prior-day low (liquidity / stop hunt).  
3. Lack of interest / volume tail below; reclaim — long (inverse for failed breakout short).  
4. Teacher prefers OF for confirmation; **structure sweep+reclaim** still spoken.  
5. Target opposing clear LOI / LVN class levels.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_CARMINE_FAIL_BREAK` | Sweep PDH/PDL or recent swing then close back through | No volume-tail / delta; no LVN target math |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-CARMINE-FAIL-BREAK
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: UhkRRqO1gQM, channel: chart-fanatics, guest: Carmine Rosato}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: ES_NQ_NY
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-ABSORB, MIX-CF-CARMINE-OPEN-HOLD, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-KANE-PO3-SMT, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not because 02/03 dislike missing OF.

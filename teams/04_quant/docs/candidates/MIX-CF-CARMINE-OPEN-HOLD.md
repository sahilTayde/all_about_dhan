# MIX-CF-CARMINE-OPEN-HOLD — Chart Fanatics Carmine Rosato hold opening print

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC open-hold proxy)  
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

1. Early NY session: pullback after open.  
2. Aggressive selling on pullback but price **holds above opening print**.  
3. Long near open; tight stop under day low / under open; TP nearby upside magnet.  
4. OF preferred for “aggression without follow-through”; open-hold structure still spoken.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_CARMINE_OPEN_HOLD` | Early session pullback holds session open then bounce → CE (inverse PE) | No OF aggression; ET 9:30 → NSE 09:15 stand-in DI |

Stops/targets: ATR(14)×1.5 / R×2 desk HYPOTHESIS.

---

## YAML stub

```yaml
mix_id: MIX-CF-CARMINE-OPEN-HOLD
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-ABSORB, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-UMAR-MORNING-TOP, MIX-CF-FABIO-TREND-NY, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not for ET→NSE clock risk alone.

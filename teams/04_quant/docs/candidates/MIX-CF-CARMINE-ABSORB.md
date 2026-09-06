# MIX-CF-CARMINE-ABSORB — Chart Fanatics Carmine Rosato absorption (OF)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (true OF — no India tape)  
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
of_status: PARKED_NO_INDIA_TAPE
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Mark levels of interest (any strategy’s S/R / supply / Fib / FVG).  
2. At LOI, watch aggressors vs passive wall (DOM / heat map / footprint delta).  
3. **Absorption:** heavy aggressive volume, **no** price follow-through → fade with passive side.  
4. CLC required — mid-range noise rejected.  
5. Needs true OF — not inventable from INDEX OHLC alone.

---

## Computable proxy

| Proxy id | Status | Gap |
|----------|--------|-----|
| True absorb | `DATA_INSUFFICIENT` | No Dhan DOM/footprint/delta series claimed |

Do **not** invent synthetic delta from bar OHLC and call it Carmine absorption.

---

## YAML stub

```yaml
mix_id: MIX-CF-CARMINE-ABSORB
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: UhkRRqO1gQM, channel: chart-fanatics, guest: Carmine Rosato}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: ES_NQ_NY
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: true
of_parked: true
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-CARMINE-OPEN-HOLD, MIX-CF-FABIO-TREND-NY, MIX-CF-FOREST-VPE-EDGE, MIX-CF-JADECAP-SWING-FAIL, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** tape-backed book — not because OF is unavailable today. Keep row PARKED; do not delete.

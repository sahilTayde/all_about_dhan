# MIX-CF-JADECAP-SESSION-LIQ — Chart Fanatics Jadecap Asia/London session liquidity

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (US session clocks → NSE unmapped)  
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

1. Draw Asian range (~8 p.m.–midnight spoken) and London range.  
2. On classic bull day prefer Asia or London **low** taken before NY upside.  
3. If both sides of session ranges already taken → lean consolidation.  
4. Midnight open + 1–2× Asia-range multiples as stall zones (personal).  
5. Untaken Asia low = elevated risk for early longs.

---

## Computable proxy

| Proxy id | Status | Gap |
|----------|--------|-----|
| True Asia/London/NY raid sequence | `DATA_INSUFFICIENT` | No honest NSE map for those clocks; do not invent Globex→cash boxes |

Keep named row; do **not** invent ORB from other guests.

---

## YAML stub

```yaml
mix_id: MIX-CF-JADECAP-SESSION-LIQ
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 8OX-mcSHWhg, channel: chart-fanatics, guest: Jadecap}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: NQ_ES_NY
india_transfer: DATA_INSUFFICIENT
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-JADECAP-FVG-DRAW, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Stay DI until a **named** session map exists; do not delete the recipe row.

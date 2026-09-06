# MIX-CF-BRANDO-SIZE-ZERO — Chart Fanatics Brando/Leaf size-for-zero options risk

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (management; premium path)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `yLuH8YZXORQ` · guest **Brando / Leaf**  
**Bind:** [`../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Usman price-stop / prior CF / STRAT / IQ / `MIX-DEFAULT-BUY`.

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

1. For **options**, set max risk = full premium paid (“size for zero”).  
2. Example: risk $1k → buy $1k premium, **not** $5k with a 20% premium stop.  
3. Gives room for −60% then +300–400% premium paths on weeklies/0DTE.  
4. Explicitly **not** for shares. Conflicts with Usman’s seatbelt/stop preference — KEEP_ALL both.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| *(none)* | — | Needs OPTIDX premium ledger — **DATA_INSUFFICIENT** as entry book |

---

## YAML stub

```yaml
mix_id: MIX-CF-BRANDO-SIZE-ZERO
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: yLuH8YZXORQ, channel: chart-fanatics, guest: Brando Leaf}]
styles: [OPTION_BUYER]
teacher_asset: US_WEEKLY_0DTE_OPTIONS
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
management_only: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-PRICE-STOP, MIX-CF-USMAN-WEEKLY-SIZE, MIX-CF-BRANDO-HTF-RECLAIM, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** premium-risk book — not because Usman disagrees (KEEP_ALL).

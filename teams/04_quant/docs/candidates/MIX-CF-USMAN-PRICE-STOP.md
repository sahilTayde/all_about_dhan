# MIX-CF-USMAN-PRICE-STOP — Chart Fanatics Usman Ashraf price/level stops + scale-out

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (management; entry LOI not frozen)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `6Bdv-_YUQ0s` · guest **Usman Ashraf** (ASR Osman Astra)  
**Bind:** [`../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md`](../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / Brando / `MIX-DEFAULT-BUY`.

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

1. Prefer **stops on underlying price/levels**, not premium % auto-stops (theta can stop you sideways).  
2. Reject **size-to-zero** as *his* substitute for a seatbelt (KEEP_ALL conflict vs `MIX-CF-BRANDO-SIZE-ZERO`).  
3. Scale-out **30/20/20/30**; day-trade ITM ~**50%** then slow; no Dogecoin-style fixed $ target.  
4. Chart must still make sense for direction — **entry pattern not frozen** this transcript.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| *(none)* | — | Exit overlay without frozen entry = **DATA_INSUFFICIENT** as standalone book |

Do **not** invent ORB/PDH entry from other guests to attach this stop.

---

## YAML stub

```yaml
mix_id: MIX-CF-USMAN-PRICE-STOP
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 6Bdv-_YUQ0s, channel: chart-fanatics, guest: Usman Ashraf}]
styles: [OPTION_BUYER]
teacher_asset: US_EQUITY_OPTIONS
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
management_only: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-WEEKLY-SIZE, MIX-CF-BRANDO-SIZE-ZERO, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** entry+price-stop pair — not because it conflicts with Brando size-zero (KEEP_ALL both).

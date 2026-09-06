# MIX-CF-USMAN-WEEKLY-SIZE — Chart Fanatics Usman Ashraf weekly Mon–Fri size

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (management; needs premium path)  
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

1. Trade **weekly** options with theta awareness.  
2. **Mon–Wed:** premiums hold better vs his stop (~10–15% premium example).  
3. **Thu–Fri:** same stop can be ~20–30%+ premium loss — **size down** so $ risk matches Monday.  
4. Fri / de-facto 0DTE: same stock move can move premium much more — still need **chart direction**.  
5. Buyer max loss = premium; illustrative % are education, not product wr.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| *(none)* | — | Sizing overlay needs OPTIDX premium% + NSE weekly weekday map — **DATA_INSUFFICIENT** |

Do **not** invent “Friday CE lean” as an INDEX entry signal.

---

## YAML stub

```yaml
mix_id: MIX-CF-USMAN-WEEKLY-SIZE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 6Bdv-_YUQ0s, channel: chart-fanatics, guest: Usman Ashraf}]
styles: [OPTION_BUYER]
teacher_asset: US_WEEKLY_OPTIONS
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
management_only: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-0DTE-GAMMA, MIX-CF-USMAN-PRICE-STOP, MIX-CF-BRANDO-SIZE-ZERO, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** premium-sizing overlay — not because weekday transfer is hard.

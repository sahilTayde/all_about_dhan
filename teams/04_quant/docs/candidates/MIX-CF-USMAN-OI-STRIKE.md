# MIX-CF-USMAN-OI-STRIKE — Chart Fanatics Usman Ashraf chain liquidity strike pick

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (needs OPTIDX OI/volume)  
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

1. Open options chain; read **open interest** (prior open contracts) and **volume** (day resets).  
2. Pick strikes with enough OI for intended size (avoid consuming most of thin OI).  
3. Direction (CE vs PE) still needs chart/thesis — liquidity alone ≠ entry.  
4. Prefer liquid names (SPY-class rhetoric) over mid-cap thin books.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| *(none)* | — | No historical OPTIDX OI/volume book in this runner — **DATA_INSUFFICIENT** |

Do **not** invent OI from INDEX OHLC.

---

## YAML stub

```yaml
mix_id: MIX-CF-USMAN-OI-STRIKE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 6Bdv-_YUQ0s, channel: chart-fanatics, guest: Usman Ashraf}]
styles: [OPTION_BUYER]
teacher_asset: US_EQUITY_OPTIONS_CHAIN
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
optidx_oi_required: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-0DTE-GAMMA, MIX-CF-USMAN-WEEKLY-SIZE, MIX-CF-USMAN-PRICE-STOP, MIX-CF-BRANDO-HTF-RECLAIM, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** OPTIDX-OI path — not because 02/03 dislike missing chain.

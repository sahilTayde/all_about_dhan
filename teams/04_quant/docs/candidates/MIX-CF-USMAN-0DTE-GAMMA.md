# MIX-CF-USMAN-0DTE-GAMMA — Chart Fanatics Usman Ashraf 0DTE gamma + IV

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DATA_INSUFFICIENT` (needs greeks + expiry calendar)  
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

1. Understand **delta** (premium vs $1 underlying) and **gamma** (delta’s rate of change).  
2. Near expiry / **0DTE**, gamma dominates → large % premium moves in minutes.  
3. Prefer names with more aggressive gamma for the same underlying move; IV expands premiums.  
4. US SPY/SPX daily 0DTE; other weeklies often Fri = de-facto 0DTE — **not** auto NIFTY.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| *(none)* | — | No OPTIDX greek series / true 0DTE map — **DATA_INSUFFICIENT** |

Do **not** invent gamma from INDEX OHLC. Do **not** treat NSE weekly Thursday as US Friday 0DTE.

---

## YAML stub

```yaml
mix_id: MIX-CF-USMAN-0DTE-GAMMA
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: 6Bdv-_YUQ0s, channel: chart-fanatics, guest: Usman Ashraf}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: US_0DTE_SPY_SPX
india_transfer: HYPOTHESIS
customer_default: false
status: DATA_INSUFFICIENT
proxy_status: DATA_INSUFFICIENT
of_required: false
greeks_required: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-USMAN-OI-STRIKE, MIX-CF-USMAN-WEEKLY-SIZE, MIX-CF-BRANDO-SIZE-ZERO, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** greeks+expiry book — not PhD dislike of transfer risk.

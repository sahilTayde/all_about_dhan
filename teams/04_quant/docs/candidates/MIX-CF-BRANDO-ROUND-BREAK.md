# MIX-CF-BRANDO-ROUND-BREAK — Chart Fanatics Brando/Leaf round-number break

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC round break proxy; news DI)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `yLuH8YZXORQ` · guest **Brando / Leaf**  
**Bind:** [`../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / Usman / `MIX-DEFAULT-BUY`.

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

1. Round numbers are magnets (SPX 6000 class).  
2. Prefer break **with** news/data catalyst (Fed, tariffs, sentiment) — bare technical breakout weaker.  
3. Example: **puts on 6000 break** in cascade.  
4. React; don’t need the first print of the crash.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_BRANDO_ROUND_BREAK` | Close beyond nearest round grid (e.g. 100 pts) | **No news/catalyst filter** — structure only |

---

## YAML stub

```yaml
mix_id: MIX-CF-BRANDO-ROUND-BREAK
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: yLuH8YZXORQ, channel: chart-fanatics, guest: Brando Leaf}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: SPX_ROUND
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
news_teacher_preferred: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-HTF-RECLAIM, MIX-CF-BRANDO-NEWS-ALIGN, MIX-CF-TORI-TL-BREAK, MIX-CF-USMAN-0DTE-GAMMA]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not because news arm is DI.

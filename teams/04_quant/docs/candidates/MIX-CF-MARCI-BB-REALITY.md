# MIX-CF-MARCI-BB-REALITY — Chart Fanatics Marci Bollinger “reality” filter

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC BB mid-reclaim proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `AVVM-FyewLg` · guest **Marci Silfrain**  
**Bind:** [`../../01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md`](../../01_research/docs/chart_fanatics/AVVM-FyewLg_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Marco / Mayne / Tori / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

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

1. Bollinger **2σ** as “reality”: middle = reality; outer = out of reality.  
2. Prefer short rizies when near **upper/middle** BB; fade late when near lower band.  
3. Crash/long timing: projected bottom **or** wait **close above middle** BB.  
4. Location filter for the rizzie model — not a standalone indicator soup for customers.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MARCI_BB_REALITY` | After lower-band touch, close back above mid → CE; after upper-band touch, close back below mid → PE | No rizzie TL; period length HYPOTHESIS (20) |
| Mainstream-news “priced in” | **Not coded** | Soft process only |

---

## YAML stub

```yaml
mix_id: MIX-CF-MARCI-BB-REALITY
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: AVVM-FyewLg, channel: chart-fanatics, guest: Marci Silfrain}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: US_INDEX_EQUITY_BTC
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCI-RIZZY, MIX-CF-FABIO-TREND-NY, MIX-CF-TORI-TL-BOUNCE, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike BB defaults.

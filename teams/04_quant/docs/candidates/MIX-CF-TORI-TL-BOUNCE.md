# MIX-CF-TORI-TL-BOUNCE — Chart Fanatics Tori trendline bounce

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC swing-line touch proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `VTEQ2fhGLqE` · guest **Tori Trades**  
**Bind:** [`../../01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md`](../../01_research/docs/chart_fanatics/VTEQ2fhGLqE_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Marco / Mayne / Marci / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

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

1. Naked chart; thick discretionary trendlines; no indicators.  
2. **Bounce:** action line = safety line; buy/sell when price respects TL.  
3. A+: ~2–3 touches; ~week of data (4H); low risk (at/near line).  
4. Trail stop with TL; exit on break. Guest now prefers breaks but bounce remains a distinct playbook.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_TORI_TL_BOUNCE` | ≥2 ascending/descending swing touches; price tags extrapolated line then closes back on side of trend | No thick-line breathing room; no alert workflow; week-data filter approximated by bar span |
| Platinum instrument edge | **Not transferable as law** to NIFTY | Transfer HYPOTHESIS |

---

## YAML stub

```yaml
mix_id: MIX-CF-TORI-TL-BOUNCE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: VTEQ2fhGLqE, channel: chart-fanatics, guest: Tori Trades}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: COMMODITY_FUTURES_SWING
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TORI-TL-BREAK, MIX-CF-MARCI-RIZZY, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike commodity→index transfer.

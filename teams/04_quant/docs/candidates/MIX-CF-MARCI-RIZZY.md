# MIX-CF-MARCI-RIZZY — Chart Fanatics Marci little-rizzie measured move

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC measured-move proxy)  
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

1. **Little rizzie:** after impulse, wait bounce; draw TL on bounce structure.  
2. Measure low→TL (downtrend) or high→TL (uptrend) on the extreme candle; project that distance for the next leg.  
3. Prefer early 1–2 rizies after trend flip; invalidation = **close** beyond TL.  
4. Fib-like without drawing Fibs; discretionary TL (self-taught names).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MARCI_RIZZY_EXT` | Dual swing lower-high / higher-low then lean with the measured-move direction | No hand-drawn TL; no Fib confluence |
| NY-open avoid | **Not mapped** to NSE | `DATA_INSUFFICIENT` |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS when guest stop distance unknown — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-MARCI-RIZZY
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-ICT-HTF, MIX-CF-TORI-TL-BOUNCE, MIX-CF-TORI-TL-BREAK, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike US→India transfer.

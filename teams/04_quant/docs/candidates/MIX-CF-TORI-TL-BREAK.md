# MIX-CF-TORI-TL-BREAK — Chart Fanatics Tori trendline break

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC break + opposing-safety proxy)  
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

1. **Break** is current bread-and-butter; requires **action** (broken TL) **and** opposing **safety** TL.  
2. Playbooks: **2-touch** vs **3+ touch**; week-of-data; skip when break is far from safety (high risk).  
3. Fan / top-down; pivot point B→new A; no forced 4H close confirmation.  
4. Pass range / ATH-without-safety / FOMO breaks.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_TORI_TL_BREAK` | Break of multi-touch swing line only if opposing swing line exists nearby (risk gate) | Fan pivots / thick-line / discretionary conviction not modeled |
| 2-touch vs 3-touch separate wr | Single proxy arm; ablation later | Guest stats ≠ product metrics |

---

## YAML stub

```yaml
mix_id: MIX-CF-TORI-TL-BREAK
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-TORI-TL-BOUNCE, MIX-CF-MARCI-RIZZY, MIX-CF-MARCO-LIQ-TRAP, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike platinum→NIFTY transfer.

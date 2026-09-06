# MIX-CF-FABIO-MR-RANGE — Chart Fanatics guest mean-revert / balance scalp

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `PARKED` (OF trigger) + OHLC proxy arm `BACKTEST_BOOK`  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `tvERE-Beu2U` · guest **Fabio Valentini**  
**Bind:** [`../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md`](../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md)  
**Separate theme** from [`MIX-CF-FABIO-TREND-NY.md`](MIX-CF-FABIO-TREND-NY.md) — do **not** soup into one default.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
```

---

## Teacher recipe (SOURCE_FACT summary)

1. **Session / regime:** London / balanced indices; summer compression months (spoken).  
2. **State:** Consolidation — profile holding both sides.  
3. **Setup:** Excursion to discount/premium → wait **first** breakout evidence → trade **second** swing **back toward POC**.  
4. **Target:** POC / max-volume node — **not** opposite range extreme.  
5. **Trigger:** Aggression bubble aligning with mean-revert direction.  
6. **Stop:** Tight / wrong immediately; 1–2 ticks inside obvious stop runs.  
7. **Cons:** Many small stops in chop (guest).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MR_TO_POC` | Prior-day volume-profile POC/VA; lean when price outside VAL/VAH then closes back toward POC | INDEX volume may be equal-weight / thin |
| London session clock | **Not mapped** to NSE | `DATA_INSUFFICIENT` |
| OF aggression | Missing | `PARKED` |

---

## YAML stub

```yaml
mix_id: MIX-CF-FABIO-MR-RANGE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: tvERE-Beu2U, channel: chart-fanatics, guest: Fabio Valentini}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: NQ_FUTURES
india_transfer: HYPOTHESIS
customer_default: false
status: PARKED
proxy_status: BACKTEST_BOOK
of_required: true
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

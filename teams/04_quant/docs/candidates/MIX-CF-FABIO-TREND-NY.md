# MIX-CF-FABIO-TREND-NY — Chart Fanatics guest trend / imbalance scalp

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `PARKED` (OF trigger) + OHLC proxy arm `BACKTEST_BOOK`  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `tvERE-Beu2U` · guest **Fabio Valentini**  
**Bind:** [`../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md`](../../01_research/docs/chart_fanatics/tvERE-Beu2U_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into `MIX-DEFAULT-BUY` / IQCapital MIXes / STRAT-001–014.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
```

---

## Teacher recipe (SOURCE_FACT summary)

1. **Session:** New York equities/NASDAQ futures — no overnight.  
2. **State:** Out of balance / imbalance only.  
3. **Location:** Volume profile LVN on swing; VAH/VAL/POC context.  
4. **Trigger:** Large executed-order aggression (bubbles); NQ filter ~20–40 contracts (spoken).  
5. **Entry:** Break + test / second drive; 5m context, 1m execution; full-body close common in live.  
6. **Stop:** Beyond aggression (tight); optional 1–2 ticks inside stop-cluster highs/lows.  
7. **Target:** Prior balance / POC (full exit common); PDH as high-probability first target when applicable.  
8. **Manage:** BE fast; CVD helps early BE; risk ~0.25–0.5%/trade; ~2% day cap (guest).

---

## Computable proxy (PROJECT_MIX — honesty)

Without Dhan OF/CVD/footprint history, **teacher trigger cannot run**. Proxy arms (INDEX OHLC fixtures only):

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_FAILED_AUCTION` | Sweep prior-day high/low then close back inside (failed auction language) | No OF confirmation |
| `CF_BREAK_RETEST_PD` | Close beyond prior-day range, retest edge, continue | No aggression bubble |
| Session NY clock | **Not mapped** to NSE | `DATA_INSUFFICIENT` |

Stops/targets on proxy: ATR(14)×1.5 stop + R×2 target is **desk HYPOTHESIS** when aggression distance unknown — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-FABIO-TREND-NY
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: tvERE-Beu2U, channel: chart-fanatics, guest: Fabio Valentini}]
styles: [SCALPER, OPTION_BUYER]   # OPTION_BUYER = desk universe tag only; recipe is futures scalp
teacher_asset: NQ_FUTURES
india_transfer: HYPOTHESIS
customer_default: false
status: PARKED                    # OF tape missing
proxy_status: BACKTEST_BOOK       # OHLC structure only
of_required: true
gex: NOT_IN_RECIPE
attached_strats: []               # KEEP_ALL separate — do not attach 001–014
not_merged_into: [MIX-DEFAULT-BUY, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy or OF-capable book — not because 02/03 dislike US→India transfer.

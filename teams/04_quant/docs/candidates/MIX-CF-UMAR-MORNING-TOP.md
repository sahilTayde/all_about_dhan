# MIX-CF-UMAR-MORNING-TOP — Chart Fanatics Umar Ashraf morning top

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC gap+weak-bounce proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `IUo5AwmsE9A` · guest **Umar Ashraf** (TradeZella)  
**Bind:** [`../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md`](../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Marco / Mayne / Marci / Tori / TG / Kane / Forest / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
guest_asr_name: Buma_Ashraf_UNKNOWN_garble
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Prior session close; next open **gaps down**.  
2. In first ~5–60 minutes, watch first upside attempt.  
3. Want **no follow-through** (weak volume/activity) then slowdown / light selling → short.  
4. Skip when multi-day sell already overextended / major speaker imminent.  
5. Full OF tape is *his* tool — proxy uses OHLC weakness only.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_UMAR_MORNING_TOP` | Gap-down open vs prior close; early-session failed bounce (lower high / close back down) → PE | No OF tape; ET window → NSE = DI |
| Opening drive sibling | Separate MIX | DI |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-UMAR-MORNING-TOP
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: IUo5AwmsE9A, channel: chart-fanatics, guest: Umar Ashraf}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: ES_NQ_NY
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MARCI-RIZZY, MIX-CF-TORI-TL-BOUNCE, MIX-CF-TG-TRIDENT, MIX-CF-KANE-EQ50, MIX-CF-UMAR-OPENING-DRIVE, MIX-CF-FOREST-VPE-EDGE, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike US→India transfer or missing OF.

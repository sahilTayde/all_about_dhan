# MIX-CF-KANE-EQ50 — Chart Fanatics Trader Kane 50% equilibrium base-hit

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC EQ proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `HNuRp9Z1bMs` · guest **Trader Kane**  
**Bind:** [`../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Marco / Mayne / Marci / Tori / TG / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

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

1. Mark dealing-range high/low; focus on **~50% (EQ)**.  
2. Want price to redeliver into EQ (nested 50% of 50% OK); take the **base hit**, not mandatory extreme.  
3. Market Maker / fair-value framing — not breakout retest.  
4. Default TP ≈ first logical liquidity / mid-range; optional aggressive trail on monster days.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_KANE_EQ50` | After swing range, touch mid then lean with prior impulse (continuation base-hit) | Nested EQ / redraw rules discretionary; no ES SMT |
| EST session | **Not mapped** to NSE | `DATA_INSUFFICIENT` |

---

## YAML stub

```yaml
mix_id: MIX-CF-KANE-EQ50
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: HNuRp9Z1bMs, channel: chart-fanatics, guest: Trader Kane}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: NQ_ES_CRYPTO
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MARCI-RIZZY, MIX-CF-TORI-TL-BOUNCE, MIX-CF-TG-TRIDENT, MIX-CF-KANE-PO3-SMT, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not host-payout skepticism alone.

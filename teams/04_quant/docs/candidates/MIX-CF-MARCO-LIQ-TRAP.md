# MIX-CF-MARCO-LIQ-TRAP — Chart Fanatics Marco liquidity trap

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC sweep/reclaim proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `DAnXM7C16h0` · guest **Marco**  
**Bind:** [`../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md`](../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into Fabio / Mayne / `MIX-DEFAULT-BUY` / IQCapital / STRAT-001–014.

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

1. Liquidity = resting stops; only after respect + move-away does a high/low “have” liquidity.  
2. **Buy below lows / sell above highs** after that liquidity is taken.  
3. Retail BOS/OB/FVG/Fib used as **induce** context — reactions opposite the planned sweep treated as false.  
4. **Strict rule:** no buy until planned low taken if highs ran first (inverse for sells).  
5. Stop beyond swept extreme; target opposing engineered liquidity (not random R).  
6. Patience / sit on hands; fractal HTF→LTF.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MARCO_SWEEP_RECLAIM` | Sweep recent swing high/low then close back through (trap reclaim) | No “respect then induce” narrative; no retail OB context |
| Session NY 9:30 | **Not mapped** to NSE | `DATA_INSUFFICIENT` |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS when guest stop distance unknown — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-MARCO-LIQ-TRAP
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: DAnXM7C16h0, channel: chart-fanatics, guest: Marco}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: US_INDEX_FUTURES_FX
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-FABIO-MR-RANGE, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MAYNE-BREAKER, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because 02/03 dislike US→India transfer.

# MIX-CF-KANE-PO3-SMT — Chart Fanatics Trader Kane PO3 + SMT/inversion

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC PO3-sweep proxy; SMT **DATA_INSUFFICIENT** on single INDEX)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `HNuRp9Z1bMs` · guest **Trader Kane**  
**Bind:** [`../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)  
**Separate theme** from `MIX-CF-KANE-EQ50`. **Not** clubbed into Fabio / Marco / Mayne / Marci / Tori / TG / STRAT / IQ / DEFAULT.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
smt_arm: DATA_INSUFFICIENT_ON_SINGLE_NIFTY
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Align **daily / H4 / H1 Power of Three** (AMD): manipulate beyond prior period extreme, then distribute opposite.  
2. Prefer ~**10 AM EST** manipulate of prior 9 AM high (session preference).  
3. Entry: **SMT** (NQ vs ES) + **inversion** of imbalance; sell-stop / limit into wick — not naked sweep.  
4. Aggressive BE when HTF candle flips; Asia = low probability.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_KANE_PO3_SWEEP` | Sweep recent swing extreme then close back (AMD manipulation stand-in) | No multi-TF PO3 boxes; **no ES SMT**; EST window unmapped |
| Full SMT+inversion | Requires correlated second series | `DATA_INSUFFICIENT` on NIFTY-only |

---

## YAML stub

```yaml
mix_id: MIX-CF-KANE-PO3-SMT
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-KANE-EQ50, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-BREAKER, MIX-CF-TG-TRIDENT, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because SMT cannot run on single INDEX alone (keep book; mark gap).

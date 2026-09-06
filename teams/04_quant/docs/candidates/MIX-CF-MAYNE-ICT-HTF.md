# MIX-CF-MAYNE-ICT-HTF — Chart Fanatics Trader Mayne HTF ICT bias

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (MSB + discount OB pullback proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `coBMd1vk2Lo` · guest **Trader Mayne**  
**Bind:** [`../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md`](../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md)  
**Not** clubbed into Fabio / Marco / STRAT / IQ / `MIX-DEFAULT-BUY`. No STRAT-015+.

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

1. ≥2 time frames; HTF for bias, LTF for execution.  
2. 3-candle swings; MSB = **close** through swing.  
3. After MSB mark range (immediate swing low→high); find **order block** that fueled the break.  
4. Wait pullback into OB in **discount** (longs) / **premium** (shorts) vs ~50% of range.  
5. Draw: external → internal OB → external again.  
6. Optional HTF entry at OB if RR ≥ guest min **2:1**.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MAYNE_MSB_DISCOUNT` | Close beyond N-bar swing then lean on pullback into prior opposing half-range | OB candle-combine discretionary; weekly/H12 not on 3m INDEX |
| Fib OTE | **Not required** by guest | Skip |

---

## YAML stub

```yaml
mix_id: MIX-CF-MAYNE-ICT-HTF
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: coBMd1vk2Lo, channel: chart-fanatics, guest: Trader Mayne}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: CRYPTO_FX_FUTURES
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-MAYNE-BREAKER, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

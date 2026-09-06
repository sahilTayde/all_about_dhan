# MIX-CF-MAYNE-BREAKER — Chart Fanatics Trader Mayne LTF breaker entry

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (sweep + structure-break proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `coBMd1vk2Lo` · guest **Trader Mayne**  
**Bind:** [`../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md`](../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md)  
**Separate theme** from `MIX-CF-MAYNE-ICT-HTF`. **Not** clubbed into Fabio / Marco / STRAT / IQ / DEFAULT.

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

1. Inside HTF POI / discount: do **not** long first bounce.  
2. Engineer liquidity → **sweep** LTF swing → **close-break** the swing that made it (breaker / double confirm).  
3. Stop beyond stop-run extreme; min **2:1** RR or skip.  
4. Ideally hold to HTF external; often de-risk ~2R (half / BE).  
5. Displacement / FVG in direction = confidence tell (qualitative).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MAYNE_BREAKER` | Sweep recent swing then close beyond opposite swing within lookback | No HTF OB gate; FVG sponsorship not required in proxy |
| Crypto NY open | Optional guest note — **not** NSE map | `DATA_INSUFFICIENT` |

---

## YAML stub

```yaml
mix_id: MIX-CF-MAYNE-BREAKER
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: coBMd1vk2Lo, channel: chart-fanatics, guest: Trader Mayne}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: CRYPTO_FX_FUTURES
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MAYNE-ICT-HTF, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-FABIO-TREND-NY]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

# MIX-CF-MARCO-INT-EXT — Chart Fanatics Marco internal→external + NY session

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (equal-extreme / internal sweep proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `DAnXM7C16h0` · guest **Marco**  
**Bind:** [`../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md`](../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md)  
**Separate theme** from `MIX-CF-MARCO-LIQ-TRAP`. **Not** clubbed into Fabio / Mayne / STRAT / IQ / DEFAULT.

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

1. Prefer entries off **internal** liquidity taken; **target external** range liquidity.  
2. Equal highs / equal lows as explicit pools (Dow NY live).  
3. NY session focus; mark stock open 9:30; London/Asia often engineer liquidity for NY.  
4. Trail under structure; partials optional at near pool then hold HTF external.  
5. Same strict wait / induce language as LIQ-TRAP — this row isolates int→ext + session framing.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_MARCO_EQ_SWEEP` | Near-equal prior highs/lows then sweep + reclaim | Epsilon HYPOTHESIS; no Asia/London clock |
| NY open window | **Not mapped** to NSE | `DATA_INSUFFICIENT` |

---

## YAML stub

```yaml
mix_id: MIX-CF-MARCO-INT-EXT
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-FABIO-TREND-NY, MIX-CF-MAYNE-ICT-HTF]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

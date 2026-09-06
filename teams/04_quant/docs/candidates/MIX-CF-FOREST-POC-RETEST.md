# MIX-CF-FOREST-POC-RETEST — Chart Fanatics Forest Knight prior POC/VAL retest

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (session-bin VP proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `q_MdVlZ1SH4` · guest **Forest Knight / Forest**  
**Bind:** [`../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF guests / STRAT / IQ / `MIX-DEFAULT-BUY`.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
va_frac_070: TEXTBOOK_DEFAULT_NOT_TEACHER_FROZEN
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Prior session **POC** (max volume price) and **VAL/VAH** (~70% participation spoken).  
2. In uptrend, wait for pullback to prior POC or VAL → long; TP highs / next shelf (inverse for downtrend).  
3. Distinct from VPE signal-candle edge entry — same guest, separate theme.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_FOREST_POC_RETEST` | Reuse prior-session bin POC/VAL (Fabio-style PROJECT profile) + touch + trend filter | Not exchange VAP; overnight H/L unused here |
| Shape P/B | Not coded this turn | Narrative only |

---

## YAML stub

```yaml
mix_id: MIX-CF-FOREST-POC-RETEST
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: q_MdVlZ1SH4, channel: chart-fanatics, guest: Forest Knight}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: NQ_ES
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FOREST-VPE-EDGE, MIX-CF-FABIO-MR-RANGE, MIX-CF-KANE-EQ50, MIX-CF-UMAR-MORNING-TOP, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** proxy — not because bin VP ≠ true VAP.

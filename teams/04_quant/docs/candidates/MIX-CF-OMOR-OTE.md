# MIX-CF-OMOR-OTE — Chart Fanatics Omor/NBB Optimal Trade Entry fib

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC 62% retrace proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `IB-fyWI5j8w` · guest **Omor / NBB Trader**  
**Bind:** [`../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**Not** clubbed into Kane EQ50 / Mayne / prior CF / STRAT / IQ. No STRAT-015+.

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

1. After distribution-side swing forms, anchor fib on graded external swing.  
2. Enter ~0.62 retrace (50% filter / first-leg ≤50% ditch-62 spoken).  
3. SL at swing (refine ~0.9); TP at origin (0); manage BE at ~0.2.  
4. RR anecdotes are **not** product metrics.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_OMOR_OTE` | After swing, touch ~62% of prior swing range then continue | Swing grading discretionary; 0.9 SL refine not modeled |

---

## YAML stub

```yaml
mix_id: MIX-CF-OMOR-OTE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: IB-fyWI5j8w, channel: chart-fanatics, guest: Omor / NBB Trader}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: FX_ICT
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-KANE-EQ50, MIX-CF-MAYNE-BREAKER, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL`. Do not promote fib RR table from podcast.

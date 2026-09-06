# MIX-CF-OMOR-PDH-REVERSAL — Chart Fanatics Omor/NBB open-near PDH/PDL sweep reverse

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC open-near + sweep reverse proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `IB-fyWI5j8w` · guest **Omor / NBB Trader**  
**Bind:** [`../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**Not** clubbed into Jade swing-fail / Carmine / Kane / prior CF. No STRAT-015+.

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

1. Only take days opening **near** PDH/PDL (or HTF PD array).  
2. Predetermined bias → expect manipulation sweep then reverse.  
3. Classic sell-day: Asia accumulate, London manip PDH, distribute.  
4. Separate from full OTE fib entry row.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_OMOR_PDH_REVERSAL` | Session open within frac of PDH/PDL; sweep then close reverse | “Near” grid ADD; Asia/London profile missing |

---

## YAML stub

```yaml
mix_id: MIX-CF-OMOR-PDH-REVERSAL
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-MMM-FRAME, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-KANE-PO3-SMT]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this named proxy.

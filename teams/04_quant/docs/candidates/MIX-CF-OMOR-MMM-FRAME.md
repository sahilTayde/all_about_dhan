# MIX-CF-OMOR-MMM-FRAME — Chart Fanatics Omor/NBB Market Maker Model framework

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC PDH/PDL sweep+displacement proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `IB-fyWI5j8w` · guest **Omor / NBB Trader**  
**Bind:** [`../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**Not** clubbed into Mayne/Kane/Jade ICT / prior CF / STRAT / IQ. No STRAT-015+.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
guest_asr: Omore_MBB_UNKNOWN_to_Omor_NBB
```

---

## Teacher recipe (SOURCE_FACT summary)

1. HTF bias + key PD arrays (PDH/PDL/PWH/PWL; 4H+ FVG/breaker/OB).  
2. Expect MMM/PO3 at those levels: accumulation → manipulation → **distribution**.  
3. Confirm SMR/breaker with displacement / CISD (prefer body close on 15m).  
4. Framework ≠ entry (entry is OTE row).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_OMOR_MMM_FRAME` | Bias from prior-day direction; PDH/PDL sweep then displace close | No true 4H PD array catalog; Asia/London clocks missing |

---

## YAML stub

```yaml
mix_id: MIX-CF-OMOR-MMM-FRAME
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-OMOR-OTE, MIX-CF-MAYNE-ICT-HTF, MIX-CF-KANE-PO3-SMT, MIX-CF-JADECAP-FVG-DRAW, MIX-CF-JADECAP-SWING-FAIL]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this named proxy. Host 30M/1.1M rhetoric ≠ metric.

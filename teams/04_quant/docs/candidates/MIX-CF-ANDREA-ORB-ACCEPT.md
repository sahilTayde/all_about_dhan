# MIX-CF-ANDREA-ORB-ACCEPT — Chart Fanatics Andrea Cimi ORB with acceptance

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC OR break+hold proxy; teacher OF preferred)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `TvoQr6ObjnU` · guest **Andrea Cimi**  
**Bind:** [`../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md`](../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md)  
**Not** clubbed into Fabio / prior CF / STRAT / IQ / `MIX-DEFAULT-BUY`. No STRAT-015+.

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

1. Build opening range from early NY candles.  
2. Break OR only when aggressors **accept** (body control / FV built outside) — not wick effort then reverse.  
3. May anticipate break when bubbles show control.  
4. Stop below POC/swing; target session magnets / heatmap.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_ANDREA_ORB_ACCEPT` | First N IST minutes as OR; close break + hold confirm bars | No OF acceptance; ET→NSE clock DI |

---

## YAML stub

```yaml
mix_id: MIX-CF-ANDREA-ORB-ACCEPT
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: TvoQr6ObjnU, channel: chart-fanatics, guest: Andrea Cimi}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: ES_NY
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
of_teacher_preferred: true
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-FABIO-TREND-NY, MIX-CF-ANDREA-FAIL-AUCTION, MIX-CF-UMAR-OPENING-DRIVE, MIX-CF-CARMINE-OPEN-HOLD]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this named proxy — not for missing Deep Charts bubbles.

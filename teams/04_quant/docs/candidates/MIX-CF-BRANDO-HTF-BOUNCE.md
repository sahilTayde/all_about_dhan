# MIX-CF-BRANDO-HTF-BOUNCE — Chart Fanatics Brando/Leaf HTF level defend / bounce

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC touch+reject proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `yLuH8YZXORQ` · guest **Brando / Leaf**  
**Bind:** [`../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / Usman / `MIX-DEFAULT-BUY`.

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

1. Identify major HTF support/resistance from prior large moves.  
2. Ideal: price hits level and **bounces / defends quickly**.  
3. Take the shot with options (calls at support; puts at resistance).  
4. Gap-fill bounce in uptrend also spoken as related opportunity.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_BRANDO_HTF_BOUNCE` | Touch prior swing ±ε then strong close away | “Quick” not clocked; gap-fill not required; no news |

---

## YAML stub

```yaml
mix_id: MIX-CF-BRANDO-HTF-BOUNCE
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: yLuH8YZXORQ, channel: chart-fanatics, guest: Brando Leaf}]
styles: [POSITION, OPTION_BUYER]
teacher_asset: SPX_HTF
india_transfer: HYPOTHESIS
customer_default: false
status: BACKTEST_BOOK
proxy_status: BACKTEST_BOOK
of_required: false
asr_caveat: true
attached_strats: []
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-HTF-RECLAIM, MIX-CF-TORI-TL-BOUNCE, MIX-CF-KANE-EQ50, MIX-CF-USMAN-PRICE-STOP]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not clubbing with Tori TL-bounce geometry.

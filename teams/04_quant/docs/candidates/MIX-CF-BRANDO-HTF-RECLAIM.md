# MIX-CF-BRANDO-HTF-RECLAIM — Chart Fanatics Brando/Leaf HTF major-level reclaim

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (OHLC multi-day swing reclaim proxy)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `yLuH8YZXORQ` · guest **Brando / Leaf** (Elite Options; ASR brand-a-k-a-leaf)  
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

1. Map **daily/weekly** major supports/resistances from large selloffs.  
2. Do **not** require buying the absolute low.  
3. Wait for **reclamation** of the prior major level → **buy calls** (puts inverse at failed reclaim of resistance).  
4. Longer-dated options OK for learners; he trades weeklies personally.  
5. Title $6k→$10M / “80%” rhetoric ≠ product metrics.

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_BRANDO_HTF_RECLAIM` | Sweep prior multi-day swing then close reclaim | Not multi-year “major”; no SPX history; no options tenor |

Stops/targets on proxy: ATR(14)×1.5 / R×2 desk HYPOTHESIS — **not** spoken ATR.

---

## YAML stub

```yaml
mix_id: MIX-CF-BRANDO-HTF-RECLAIM
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
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-BRANDO-ROUND-BREAK, MIX-CF-BRANDO-HTF-BOUNCE, MIX-CF-CARMINE-FAIL-BREAK, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-MARCO-LIQ-TRAP, MIX-CF-USMAN-OI-STRIKE]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on this **named** proxy — not because transfer from SPX is hard.

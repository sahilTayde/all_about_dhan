# MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE — India adaptation (Marco (DaVinci return))

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `T_djSNBmV00` (Marco (DaVinci return))  
**Teacher book:** MIX-CF-MARCO-DAV  
**Bind:** [`../../01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md`](../../01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family MARCO-DAV` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
**Not** STRAT-015+. **Not** NQ/US auto-inherit. **NO_PROMOTE.** Catalog `win_rate=null`.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
india_decision: PARTIAL
of_required: true
observation_gated: true
NO_PROMOTE: true
```

## One-line

{
  "claim": "Engineered Liquidity gate: only trade after price respects/engineers a liquidity pool (liquidity above highs for longs, liquidity below lows for shorts). Then enter on the sweep/take of the opposite-side low/high with a tight 

## YAML stub

```yaml
mix_id: MIX-CF-MARCO-DAV-IN-OHLC-SWEEP-CEPE
origin: PROJECT_MIX
teacher_video: T_djSNBmV00
guest: Marco (DaVinci return)
guest_slug: MARCO-DAV
customer_default: false
status: BACKTEST_BOOK
paper_enable: false
founder_paper_accept: false
win_rate: null
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
of_required: true
india_decision: PARTIAL
promote: false
NO_PROMOTE: true
docs:
  - teams/01_research/docs/chart_fanatics/T_djSNBmV00_BIND.md
  - data/recon/CF_OPENAI_MARCO-DAV_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

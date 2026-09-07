# MIX-CF-CARMINE-IN-OPENHOLD-OHLC — India adaptation (Carmine Rosato)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `UhkRRqO1gQM` (Carmine Rosato)  
**Teacher book:** MIX-CF-CARMINE  
**Bind:** [`../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md`](../../01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_CARMINE_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_CARMINE_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family CARMINE` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Orderflow as auction read: identify where aggressive intent hits passive liquidity (DOM/heat/footprint/volume profile), then execute thesis at Level of Interest (LOI) using absorption (aggressors without follow-through) and stop-hunt/failur

## YAML stub

```yaml
mix_id: MIX-CF-CARMINE-IN-OPENHOLD-OHLC
origin: PROJECT_MIX
teacher_video: UhkRRqO1gQM
guest: Carmine Rosato
guest_slug: CARMINE
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
  - teams/01_research/docs/chart_fanatics/UhkRRqO1gQM_BIND.md
  - data/recon/CF_OPENAI_CARMINE_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

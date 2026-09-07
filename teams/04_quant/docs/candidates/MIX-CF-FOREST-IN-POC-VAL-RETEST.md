# MIX-CF-FOREST-IN-POC-VAL-RETEST — India adaptation (Forest Knight)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `q_MdVlZ1SH4` (Forest Knight)  
**Teacher book:** MIX-CF-FOREST  
**Bind:** [`../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md`](../../01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_FOREST_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_FOREST_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family FOREST` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Volume Profile Edges (HVN shelves) + auction trapped-participant levels (ONH/ONL/PDH/PDL) + high-volume signal candle at the edge; wait for candle close (no front-run) and trade toward the next shelf, with drawdown bounded by signal-candle 

## YAML stub

```yaml
mix_id: MIX-CF-FOREST-IN-POC-VAL-RETEST
origin: PROJECT_MIX
teacher_video: q_MdVlZ1SH4
guest: Forest Knight
guest_slug: FOREST
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
  - teams/01_research/docs/chart_fanatics/q_MdVlZ1SH4_BIND.md
  - data/recon/CF_OPENAI_FOREST_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

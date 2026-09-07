# MIX-CF-JADECAP-IN-LIQTOINEFF-FVGDRAW — India adaptation (Jadecap)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `8OX-mcSHWhg` (Jadecap)  
**Teacher book:** MIX-CF-JADECAP  
**Bind:** [`../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md`](../../01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_JADECAP_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_JADECAP_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family JADECAP` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

A disciplined, observation-gated intraday framework: wait for liquidity raids (PDH/PDL and/or session range extremes) to engage resting orders, then enter only on confirmation/reclaim (swing failure) or on a liquidity→inefficiency draw (oft

## YAML stub

```yaml
mix_id: MIX-CF-JADECAP-IN-LIQTOINEFF-FVGDRAW
origin: PROJECT_MIX
teacher_video: 8OX-mcSHWhg
guest: Jadecap
guest_slug: JADECAP
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
  - teams/01_research/docs/chart_fanatics/8OX-mcSHWhg_BIND.md
  - data/recon/CF_OPENAI_JADECAP_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

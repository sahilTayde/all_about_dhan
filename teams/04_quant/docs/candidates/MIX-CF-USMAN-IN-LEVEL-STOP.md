# MIX-CF-USMAN-IN-LEVEL-STOP — India adaptation (Usman Ashraf)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `6Bdv-_YUQ0s` (Usman Ashraf)  
**Teacher book:** MIX-CF-USMAN  
**Bind:** [`../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md`](../../01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family USMAN` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Education-gated framework: pick liquid strikes using chain OI/volume; understand premium velocity via Greeks/IV (time + volatility), and manage exits with underlying price/level stops (not premium-only choke). Win_rate remains null (no back

## YAML stub

```yaml
mix_id: MIX-CF-USMAN-IN-LEVEL-STOP
origin: PROJECT_MIX
teacher_video: 6Bdv-_YUQ0s
guest: Usman Ashraf
guest_slug: USMAN
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
  - teams/01_research/docs/chart_fanatics/6Bdv-_YUQ0s_BIND.md
  - data/recon/CF_OPENAI_USMAN_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

# MIX-CF-YUSH-IN-RETRY-RETEST — India adaptation (Trader Yush)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `hvyf6frvCcA` (Trader Yush)  
**Teacher book:** MIX-CF-YUSH  
**Bind:** [`../../01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md`](../../01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_YUSH_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_YUSH_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family YUSH` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Observation-gated value areas (developing RTH volume profile), confirmed by orderflow (big trades + delta) at market-generated levels (PDH/PDL, overnight high/low, ORB high/low). Trade only after 2+ confirmations define an 'area of interest

## YAML stub

```yaml
mix_id: MIX-CF-YUSH-IN-RETRY-RETEST
origin: PROJECT_MIX
teacher_video: hvyf6frvCcA
guest: Trader Yush
guest_slug: YUSH
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
  - teams/01_research/docs/chart_fanatics/hvyf6frvCcA_BIND.md
  - data/recon/CF_OPENAI_YUSH_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

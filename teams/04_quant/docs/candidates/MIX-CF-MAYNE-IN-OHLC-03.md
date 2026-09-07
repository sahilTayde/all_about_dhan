# MIX-CF-MAYNE-IN-OHLC-03 — India adaptation (Trader Mayne)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `coBMd1vk2Lo` (Trader Mayne)  
**Teacher book:** MIX-CF-MAYNE  
**Bind:** [`../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md`](../../01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_MAYNE_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_MAYNE_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family MAYNE` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Use an observation-gated ICT-style framework to (1) set HTF directional bias via MSB + range, (2) define the optimal LTF execution zone inside HTF POIs using premium/discount + liquidity oscillation, and (3) enforce a min 2:1 R:R so early/l

## YAML stub

```yaml
mix_id: MIX-CF-MAYNE-IN-OHLC-03
origin: PROJECT_MIX
teacher_video: coBMd1vk2Lo
guest: Trader Mayne
guest_slug: MAYNE
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
  - teams/01_research/docs/chart_fanatics/coBMd1vk2Lo_BIND.md
  - data/recon/CF_OPENAI_MAYNE_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

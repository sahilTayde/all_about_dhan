# MIX-CF-UMAR-IN-02 — India adaptation (Umar Ashraf)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `IUo5AwmsE9A` (Umar Ashraf)  
**Teacher book:** MIX-CF-UMAR  
**Bind:** [`../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md`](../../01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_UMAR_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_UMAR_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family UMAR` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
**Not** STRAT-015+. **Not** NQ/US auto-inherit. **NO_PROMOTE.** Catalog `win_rate=null`.

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
india_decision: PARTIAL
of_required: false
observation_gated: true
NO_PROMOTE: true
```

## One-line

A stage-based process mindset: early stages optimize risk/skill/process (not money), emotions are a size problem, and selection is gated by environment/order-flow activity—then later phases introduce dynamic risk and tighter operational dis

## YAML stub

```yaml
mix_id: MIX-CF-UMAR-IN-02
origin: PROJECT_MIX
teacher_video: IUo5AwmsE9A
guest: Umar Ashraf
guest_slug: UMAR
customer_default: false
status: BACKTEST_BOOK
paper_enable: false
founder_paper_accept: false
win_rate: null
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
of_required: false
india_decision: PARTIAL
promote: false
NO_PROMOTE: true
docs:
  - teams/01_research/docs/chart_fanatics/IUo5AwmsE9A_BIND.md
  - data/recon/CF_OPENAI_UMAR_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

# MIX-CF-ANDREA-STOPRUN-PARTIAL-IN-03 — India adaptation (Andrea Cimi)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `TvoQr6ObjnU` (Andrea Cimi)  
**Teacher book:** MIX-CF-ANDREA  
**Bind:** [`../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md`](../../01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_ANDREA_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_ANDREA_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family ANDREA` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Auction/liquidity mechanics (failed auction + OF acceptance, plus stop-run fade ≠ always-reversal) used as discretionary gating to avoid “late on the party” entries; relies on liquidity participation and absorption/initiative rather than ju

## YAML stub

```yaml
mix_id: MIX-CF-ANDREA-STOPRUN-PARTIAL-IN-03
origin: PROJECT_MIX
teacher_video: TvoQr6ObjnU
guest: Andrea Cimi
guest_slug: ANDREA
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
  - teams/01_research/docs/chart_fanatics/TvoQr6ObjnU_BIND.md
  - data/recon/CF_OPENAI_ANDREA_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

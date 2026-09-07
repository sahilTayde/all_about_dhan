# MIX-CF-OMOR-OTE-SILVERBULLET-15M-IN-01 — India adaptation (Omor / NBB)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `IB-fyWI5j8w` (Omor / NBB)  
**Teacher book:** MIX-CF-OMOR  
**Bind:** [`../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md`](../../01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_OMOR_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_OMOR_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family OMOR` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Observation-gated trade selection: only allow the Market Maker Model (MMM / Power-of-Three) to be actionable when the market opens near HTF PD arrays (PDH/PDL and related PD arrays) and the bias is bearish (sell-side distribution). Use MMM 

## YAML stub

```yaml
mix_id: MIX-CF-OMOR-OTE-SILVERBULLET-15M-IN-01
origin: PROJECT_MIX
teacher_video: IB-fyWI5j8w
guest: Omor / NBB
guest_slug: OMOR
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
  - teams/01_research/docs/chart_fanatics/IB-fyWI5j8w_BIND.md
  - data/recon/CF_OPENAI_OMOR_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

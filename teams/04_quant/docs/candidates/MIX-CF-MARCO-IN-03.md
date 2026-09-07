# MIX-CF-MARCO-IN-03 — India adaptation (Marco)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `DAnXM7C16h0` (Marco)  
**Teacher book:** MIX-CF-MARCO  
**Bind:** [`../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md`](../../01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_MARCO_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_MARCO_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family MARCO` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

Liquidity (resting stop orders) is the primary driver of bias + trade direction; entries are taken only after the intended liquidity is swept/taken, using strict opposing-sweep rules to avoid buying/selling into the wrong side of a trap.

## YAML stub

```yaml
mix_id: MIX-CF-MARCO-IN-03
origin: PROJECT_MIX
teacher_video: DAnXM7C16h0
guest: Marco
guest_slug: MARCO
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
  - teams/01_research/docs/chart_fanatics/DAnXM7C16h0_BIND.md
  - data/recon/CF_OPENAI_MARCO_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

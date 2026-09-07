# MIX-CF-KANE-IN-PO3AMD-OHLCONLY — India adaptation (Trader Kane)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `HNuRp9Z1bMs` (Trader Kane)  
**Teacher book:** MIX-CF-KANE  
**Bind:** [`../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md`](../../01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_KANE_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_KANE_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family KANE` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

EQ (50% dealing-range redelivery/base-hit) + fractal HTF alignment (Daily/H4/H1 PO3/AMD-style 'manipulation then distribution') with SMT/inversion confirmation; trade is often risk-managed to break-even quickly (“right or right out”).

## YAML stub

```yaml
mix_id: MIX-CF-KANE-IN-PO3AMD-OHLCONLY
origin: PROJECT_MIX
teacher_video: HNuRp9Z1bMs
guest: Trader Kane
guest_slug: KANE
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
  - teams/01_research/docs/chart_fanatics/HNuRp9Z1bMs_BIND.md
  - data/recon/CF_OPENAI_KANE_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

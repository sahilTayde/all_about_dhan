# MIX-CF-BRANDO-IN-02-ROUNDBREAK-CATALYST-PUTS — India adaptation (Brando / Leaf)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `yLuH8YZXORQ` (Brando / Leaf)  
**Teacher book:** MIX-CF-BRANDO  
**Bind:** [`../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md`](../../01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_BRANDO_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_BRANDO_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family BRANDO` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

HTF support/resistance levels + catalyst alignment (news/data) with disciplined mindset (no FOMO/chasing) + options-specific risk control via size-for-zero; entries are reaction-based at major levels rather than prediction-based.

## YAML stub

```yaml
mix_id: MIX-CF-BRANDO-IN-02-ROUNDBREAK-CATALYST-PUTS
origin: PROJECT_MIX
teacher_video: yLuH8YZXORQ
guest: Brando / Leaf
guest_slug: BRANDO
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
  - teams/01_research/docs/chart_fanatics/yLuH8YZXORQ_BIND.md
  - data/recon/CF_OPENAI_BRANDO_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

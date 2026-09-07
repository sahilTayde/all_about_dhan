# MIX-CF-TG-IN-INDEX-FVG-DOJI-CE — India adaptation (TG Capital)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK`  
**Origin:** `PROJECT_MIX` — observation-gated India port of Chart Fanatics `ADnslyKOwFE` (TG Capital)  
**Teacher book:** MIX-CF-TG  
**Bind:** [`../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md`](../../01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md)  
**OpenAI aid:** [`../../../../data/recon/CF_OPENAI_TG_BIND_SUGGEST_2026-09-07.md`](../../../../data/recon/CF_OPENAI_TG_BIND_SUGGEST_2026-09-07.md) — HYPOTHESIS only; does **not** fix WR  
**Runner:** `python -m backtest_engine cf-india --family TG` (sibling to `okala-in`; does **not** rewrite `okala_in_proxy`)  
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

An observation-gated, long-bias London-killzone entry: wait for 30m Fair Value Gap (FVG) printing, then require a doji/CE (50%) rejection style before entering; align with stacked EMA “wave” + daily trend narrative for large TP capture, and

## YAML stub

```yaml
mix_id: MIX-CF-TG-IN-INDEX-FVG-DOJI-CE
origin: PROJECT_MIX
teacher_video: ADnslyKOwFE
guest: TG Capital
guest_slug: TG
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
  - teams/01_research/docs/chart_fanatics/ADnslyKOwFE_BIND.md
  - data/recon/CF_OPENAI_TG_BIND_SUGGEST_2026-09-07.md
```

KEEP_ALL — do not merge into `MIX-DEFAULT-BUY`, STRAT-001–014, IQCapital, or prior guest MIX rows without founder ask.

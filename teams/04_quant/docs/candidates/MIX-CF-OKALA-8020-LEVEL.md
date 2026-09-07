# MIX-CF-OKALA-8020-LEVEL — Chart Fanatics Okala observed-magnet level reversion

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `BACKTEST_BOOK` (catalog only — **no** 06 evaluator yet; **not** in CF×8 runners)  
**Origin:** `EXTERNAL_RESEARCH` — Chart Fanatics `jsUTbjwpFVk` · guest **Okala**  
**Bind:** [`../../01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md`](../../01_research/docs/chart_fanatics/jsUTbjwpFVk_BIND.md)  
**Not** `DHAN-DERIVED`. **Not** STRAT-015+. **Not** clubbed into prior CF / STRAT / IQ / `MIX-DEFAULT-BUY`.  
**Title “65% WR” / spoken “70%” / “mid-low 70s” = claims only** → `win_rate=null`. **NO_PROMOTE.**

```text
layer: HYPOTHESIS
metrics: win_rate=null expectancy=null profit_factor=null max_drawdown=null
customer_default: false
research_ready_for_programming: false
live_code: forbidden
source_caveat: ASR_WHISPER_[ASR]
evaluator: CATALOG_ONLY_UNTIL_06_BINDS
```

---

## Teacher recipe (SOURCE_FACT summary)

1. Treat **xx80** / **xx20** as **observed** NQ reaction magnets (not sacred universals) — desk may discover analogs per market.  
2. Prefer mean-reversion reaction at magnet (not trend chase); stack with structure when possible.  
3. Structure TF **10m**; execution TF **200s**.  
4. SL **10 pts**; TP1 **~15 pts** (sometimes ~12.5); then BE; runners discretionary.  
5. Prefer NY open; avoid lunch / dead conditions.  
6. **Miss / recovery:** next magnet after miss; **no chase** after near-miss reaction; early offsets on speed (see BIND).

**Honesty:** `magnet_modulus=observable|searchable` · `market_scope=teacher_examples_NQ;portability=observation_gated` · `win_rate=null` · **NO_PROMOTE**. BT search grid in BIND. India = separate adaptation MIX later (not auto-inherit).

---

## Computable proxy (PROJECT_MIX — honesty)

| Proxy id | What it approximates | Gap |
|----------|----------------------|-----|
| `CF_OKALA_8020_LEVEL` | Reaction at observed magnets on INDEX | NQ digit→NIFTY map **DI** until observation MIX; 200s→3m remap |

Stops/targets: teacher 10/15 NQ pts — **do not** invent NIFTY point equivalents without 02/03; ATR-scale = searchable HYPOTHESIS only.

---

## YAML stub

```yaml
mix_id: MIX-CF-OKALA-8020-LEVEL
origin: EXTERNAL_RESEARCH
origin_videos: [{video_id: jsUTbjwpFVk, channel: chart-fanatics, guest: Okala}]
styles: [SCALPER, OPTION_BUYER]
teacher_asset: NQ_NY
india_transfer: HYPOTHESIS
magnet_modulus: observable|searchable
market_scope: teacher_examples_NQ;portability=observation_gated
customer_default: false
status: BACKTEST_BOOK
proxy_status: WAITING
of_required: false
gex: NOT_IN_RECIPE
asr_caveat: true
attached_strats: []
evaluator_bound: false
# future 06: okala_magnet_modulus_search=true · okala_no_chase=true — BACKTEST_BOOK only; NO_PROMOTE
not_merged_into: [MIX-DEFAULT-BUY, MIX-CF-JADECAP-SWING-FAIL, MIX-CF-OMOR-PDH-REVERSAL, MIX-CF-OKALA-FORK, MIX-DESK-IQ-ATR-RR2]
metrics: {win_rate: null, expectancy: null, profit_factor: null, max_drawdown: null}
```

## Invalidation / kill rule

Kill only after 06 OOS+`NORMAL` on a **named** evaluator for this MIX — not because title WR marketing fails (KEEP_ALL). CF×8 FAILs are other books — not this catalog row.

# STRAT-002 — Slightly OTM, 20–30% premium target

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` (`HAUSZx-hYdY` EN 57:40–01:02:19)  
**Overlay on STRAT-001-alt ONLY. Never overlay on STRAT-003.** (`CONFLICT` — Gokul `2RnBT9DDDNI` 38:06: OTM **not recommended**.)  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Not standalone. Not claimed profitable.**

```yaml
strategy_id: STRAT-002
attaches_to: [STRAT-001]          # never STRAT-003
option_selection:
  moneyness: 1_or_2_strikes_OTM
  spoken_delta_adverse: ~0.40     # CONFIRMED as spoken; still education
target: 20_to_30_percent_of_entry_premium
stop_underlying: recent_swing
stop_beginner_rupee: 1500_to_1700_vs_2500_target  # WEAK [UNCERTAIN_TRANSCRIPT]
trail: MA_9_or_10_vs_30_cross_against
```

Speaker: ATM most “pumped”; slightly OTM (one or two strikes); adverse-case ~**40 delta**; target ~**20–30%** of option value.  
**Conflict:** 2RnBT9 (005) / pvmvki (006) prefer ITM — do **not** merge into one “Dhan strike.” Ablate OTM vs ATM vs ITM on **separate** primaries. Strike follows the **primary’s video**.

## Invalidation

OTM underperforms ATM/ITM after spread on the **same** 001 signal set. Attaching this overlay to a 003 ticket is a spec fail (not a test).

## Risk

OTM can expire worthless on a “correct” but slow move (theta). Illiquid 50-point strikes. Beginner rupee stop is **WEAK**.

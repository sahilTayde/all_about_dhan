# Research sprint summary — paper-only NIFTY option buyer

**Date:** 2026-10-04. **Layer:** HYPOTHESIS / DESIGN. **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`.  
**PAPER only. NO_PROMOTE.** Playbook stays off. Live V2 defaults stay as they are.

Owner write-up: [`ROUND9_IMPROVEMENT_SPRINT.md`](ROUND9_IMPROVEMENT_SPRINT.md).

---

## Now

Exits are the drain. On the documented 2026-09-25 paper book, 43 fills made ₹80,763 gross and paid ₹41,287 in charges (51% of gross). The last 20 closed tickets in that same file show 15/20 exits from `CANCEL_AGAINST` / `COVER_LONG_UNWIND` / other cancels, summing to **−₹97,205**. Four `TARGET` hits in that slice sum to +₹138,596. Legacy those cancels are comparison tape only — they are not the design base.

Exit Lab PR #69 already ran the honest replay: **0 / 654** variants pass OOS. Clock / theta is the strongest univariate (GOOD-exit lift 1.212). The least-bad live rule (`peak_hazard_p10`) is +₹58,243 vs hold −₹82,565 on the random 1-lot set, but **CI_lo = −₹16,545** and **DSR = 0.043**. Fast bail-outs reprint `CANCEL_AGAINST` (78% of `time_edge` 1-lot gain; 55% of `atr_opt_1.2`; 80% of `shape_exit`). V2 defaults stay: native invalidation + ₹30k house stop, every other primitive off.

Round 8 already closed breakout-follow-through and long ATM holds. A buyer still needs **55–60%** direction on the held move after measured costs and decay. Analysts sit at 52–53%. Harvest leads **H18 / S07 / H22 / H19** are founder-stated as failed on deep1 OOS bars. This checkout has **no** `HOLDOUT_SPEC` file and **no** primary H18/S07/H22/H19 tables — those IDs stay burned. The operating holdout is the frozen Exit Lab 3b + Round 8 FWD-BAR contract (see §0 of the sprint file).

This cloud box has **no** last3d parquets and **no** dual-tape sqlite. The remine below is a no-peeking re-rank of published Exit Lab tables plus the committed 2026-09-25 ticket log. It is not a new 750k-minute run.

## Why

Cost is binding. Clock-only and early-bailout rules look green because they harvest theta on expiry-week last3d or they fire at the same minute as the old cancel cluster. Label permutation already collapsed non-clock lift from 1.212 to 1.023. Promoting any of that reprints the drain.

## Next

Run **four** non-clock Exit Lab cells on Sat 10 Oct. Rank only on random 1-lot. Pass only if **CI_lo > 0**, DSR ≥ 0.9 at N = 654 + new cells, and ≥ 8/12 expanding folds beat hold. Anything clock-named, `time_edge_*`, `atr_opt_*`, or `shape_exit` is banned. Do not enable the playbook even if a cell is green. Full grid, commands, and kill rules: sprint file §3.

## What this PR is / is not

| Is | Is not |
|----|--------|
| Research + analysis | An engine change |
| A frozen Oct 10 lab card | A playbook enable |
| A remine of published tables + one paper day | A claim that a path feature now works |
| Honest `DATA_INSUFFICIENT` on missing tapes / harvest IDs | A retest of H18/S07/H22/H19 on burned bars |

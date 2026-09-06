# RESEARCH_REVIEW_NOTES — Team 09

**Status:** Open issues only. **Not a pass.**  
**Gate:** `RESEARCH_READY_FOR_PROGRAMMING` = **not issued**.  
**Date:** 2026-08-30

This is a **pre-five-pass** scratch list so tomorrow’s reviewer does not start from zero. No red-team verdict.

---

## PASS 1 — Source integrity (preview)

- Channel is `@DhanHQ` for all extracted IDs. Good.
- Transcripts exist on disk for extracted IDs; ASR Hindi; `qa_flags: UNCERTAIN_TRANSCRIPT` on the long classes.
- **English missing** (32/33). Do not treat English paraphrases in team docs as the transcript.
- Not extracted: remaining verified HIGH (stock scanners, swing 2YBmiy, music). Honest skip vs silent omit — listed in `TRANSFERABLE_AND_SKIPPED.md`.
- **Cannot** use `_exmJYgFwFA` (selling masterclass) — `TRANSCRIPT_PENDING`.

## PASS 2 — Technical (preview)

- Volume-delta vs Greek-delta collision (YUXJv) — must stay labelled.
- MACD×4, 9 vs 10 MA, 100 vs 300: unresolved ASR.
- Super Scalper periods UNKNOWN.
- “Conviction = delta” **unsupported** (02).
- Intrinsic/exercise story vs **European index options** (03).

## PASS 3 — Market (preview)

- Expiry weekday **changed** after some recordings (Thu vs Tue).
- Lots changed Jan 2026 (secondary sources). No circular in repo.
- F&O close 15:30 vs 15:40 (Aug 2026 press) unverified in-repo.
- HAUS universe is **NIFTY-100 stocks**, transferred to index by 04 — **must stay PROJECT vs DHAN**.
- VWAP on cash index = fail if anyone codes it.

## PASS 4 — Quant (preview)

- No backtest yet. Any UI number would be invented → fail Q4.
- 14 candidates include filters; do not count 14 independent edges.
- 013–014 selling vs Phase-1 buy-first.

## PASS 5 — Red-team (preview questions already “at risk”)

3 numbers ASR; 4 stock concept → index; 5 underlying vs option; 7 lot history; 11–12 fills; 19 education as endorsement; 20 reproducibility without English.

---

## Open issues (owners)

| ID | Issue | Owner |
|----|--------|--------|
| R-01 | timedtext 429 / ENGLISH_PENDING | 01 |
| R-02 | Official lot + session circulars in repo | 03 |
| R-03 | Super Scalper EMA lengths | 01 + Tier 2 charts |
| R-04 | njqeZc patterns 2–5 | 01 |
| R-05 | DhanHQ historical options / footprint | 01/07 later |
| R-06 | Do not implement strategies | 07 — blocked |
| R-07 | Staged EARLY must not be coded as 1-minute omniscience or a guaranteed fill; live `DHAN_*` desk_intel/chain is **TODO** on `TASK_STAGED_SIGNALS.md` | 04/07 — blocked; 00 token TODO |

**Verdict:** none. Packet is `DRAFT`. Missed-PE owner case: [`MISSED_TRADE_POSTMORTEM.md`](MISSED_TRADE_POSTMORTEM.md) (not a pass).

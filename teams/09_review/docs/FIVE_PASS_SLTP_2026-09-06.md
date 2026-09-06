# FIVE-PASS — SL/TP MIX overlays (2026-09-06)

**Team:** 09_review  
**Status:** **FAILED REVIEW** (expected)  
**Gate:** `RESEARCH_READY_FOR_PROGRAMMING` **not issued**  
**Source:** [`BACKTEST_SLTP_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_SLTP_2026-09-06.md) · [`SL_TP_EXTERNAL_HARVEST.md`](../../01_research/docs/SL_TP_EXTERNAL_HARVEST.md)

```text
verdict:                FAILED REVIEW
five_pass:              PERFORMED — FAILED
research_ready_for_programming: false
profitability:          NOT CLAIMED
```

| Pass | Call | Gap |
|------|------|-----|
| 1 Source | **PARTIAL** | IQCapital transcripts on disk are real; GEX→NIFTY not SOURCE_FACT |
| 2 Technical | **FAIL** | INDEX equal-weight VWAP ≠ FUTIDX; ATR seed OK; OF absent |
| 3 Market | **FAIL** | No India GEX; OPTIDX premium% not scored |
| 4 Quant | **FAIL** | OOS books FAIL / not promote; high trade count / stack_exit dominated |
| 5 Red-team | **FAIL** | Q4 fills, Q8 costs, Q12 live path unanswered |

**Accepted:** KEEP_ALL; named `MIX-DESK-IQ-ATR-RR2` / `MIX-SLTP-*`; hardcoded STOP_PTS gated as deprecated placeholder; honest FAIL.  
**Rejected:** Promote; fake certainty; STRAT-015+.  
**UNKNOWN:** NIFTY GEX construction; continuous FUTIDX; premium-% TP fills.

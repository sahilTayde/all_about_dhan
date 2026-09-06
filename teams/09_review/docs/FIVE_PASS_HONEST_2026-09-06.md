# FIVE-PASS — costs + NORMAL strip + FUTIDX 003 (2026-09-06)

**Team:** 09_review  
**Status:** **FAILED REVIEW**  
**Gate:** `RESEARCH_READY_FOR_PROGRAMMING` **not issued**  
**Source:** [`BACKTEST_HONEST_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md) · [`docs/REVIEW.md`](../../../docs/REVIEW.md)  
**This is a five-pass.** It does **not** pass.

```text
verdict:                FAILED REVIEW
five_pass:              PERFORMED — FAILED
research_ready_for_programming: false
profitability:          NOT CLAIMED
live code / orders:     forbidden
keep_current_strategy:  true
```

---

## PASS 1 — Source integrity

| Check | Call |
|-------|------|
| Channel `@DhanHQ` for STRAT bind | **PASS** — spoken rules still [`TRANSCRIPT_STRATEGY_BIND.md`](../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md) |
| Transcripts not invented | **PASS** for the bind packet |
| This run did not invent a new teacher recipe | **PASS** — frozen club leans only |
| Cost % as SOURCE_FACT | **FAIL** — 1% each-way is `HYPOTHESIS`, not a circular |

**Pass 1: FAIL** (cost model is not source).

## PASS 2 — Technical accuracy

| Check | Call |
|-------|------|
| Annexure RSI/MACD/EMA from INDEX OHLC | **PASS** — still no HQ series REST |
| Long option P/L = premium change | **PASS** |
| Statutory STT / brokerage math | **FAIL** — UNKNOWN, zeroed |
| Supertrend 10,3 on FUTIDX stitch | **FAIL** if treated as Gokul identity — tape is 64 days, not 3m native |

**Pass 2: FAIL.**

## PASS 3 — Market accuracy

| Check | Call |
|-------|------|
| NSE vs BSE isolated | **PASS** |
| Lots not hardcoded | **PASS** |
| EXPIRY weekday FROM_CONTRACT | **FAIL** — ISO-week last-session proxy is not the sheet date |
| Continuous FUTIDX | **FAIL** — live CSV only; expired-month IDs missing |
| F&O 15:30 vs 15:40 | still **VERIFY** |

**Pass 3: FAIL.**

## PASS 4 — Quant accuracy

| Check | Call |
|-------|------|
| No look-ahead on signal close | **PASS** (next option open) |
| Did not retune after seeing after-cost wr | **PASS** |
| Costs modeled | **PARTIAL** — hypothesis band only |
| OOS + NORMAL | **FAIL** — SCORE_SAMPLE empty (`news_filter: DATA_INSUFFICIENT`) |
| CLUB-GR 69% | **killed by costs** — after-cost wr 44.4% **FAIL**. Good. |
| MIX-CLUB-GXR 50% / +1.83 | **WEAK** only; SENSEX FAIL; not a promote |
| Multiple testing | still open (club after a scan after a clock) |

**Pass 4: FAIL.**

## PASS 5 — Red-team (yes = failure)

| # | Question | Yes? |
|---|---------|------|
| 1 | Skip or invent a transcript? | no |
| 2 | Invent a Dhan recommendation? | no |
| 3 | Misinterpret a number? | no — 69% → 44% is labeled |
| 4 | Stock-only concept for options? | no this run |
| 5 | Confuse underlying with option? | **yes** on FUTIDX-STITCH (points proxy, not premium) |
| 6 | Future information? | no |
| 7 | Current lot size historically? | no |
| 8 | Unavailable historical option *fills*? | **yes** — next-bar-open |
| 9 | Optimize against the test set? | no this run (frozen leans) |
| 10 | Ignore transaction costs? | **yes** for statutory; hypothesis slip only |
| 11 | Ignore bid/ask? | **yes** |
| 12 | Assume fills? | **yes** |
| 13 | Correlation as causation? | no claim |
| 14 | Overfit indicators? | prior club was winner-soup; this run did not add more |
| 15 | Pick winner by highest return? | **would be yes** if GXR WEAK were promoted — **REJECT** |
| 16 | Ignore losing regimes? | SENSEX FAIL named |
| 17 | Ignore liquidity? | **yes** — no volume/reject model |
| 18 | Other YouTube channel? | no |
| 19 | Education as live endorsement? | no |
| 20 | Another researcher cannot reproduce? | cache + command exists; statutory still unreproducible as official |

**Red-team: FAILED** (Q5, Q8, Q10, Q11, Q12, Q17).

---

## Verdicts

| Item | Call |
|------|------|
| After-cost CLUB-GR NIFTY 44% | **FAIL**. 69% was optimistic soup. |
| MIX-CLUB-GXR WEAK | **not CANDIDATE**. SENSEX FAIL. Hypothesis cost. |
| SCORE_SAMPLE / NORMAL-only | **DATA_INSUFFICIENT** |
| Continuous FUTIDX 003 | **DATA_INSUFFICIENT** (span ~64d) |
| Swap MIX-DEFAULT-BUY | **REJECT** |
| Live orders | **REJECT** |
| KEEP_ALL | **ACCEPT** |
| `RESEARCH_READY_FOR_PROGRAMMING` | **not set** |

```text
HANDOFF
From: 09
To:   00
Accepted: five-pass performed on the honest leftover. 69% named dead after cost.
  FUTIDX continuous marked DATA_INSUFFICIENT. SCORE_SAMPLE empty.
Rejected: RESEARCH_READY; promote GXR; waive Q8/Q10/Q11/Q12.
UNKNOWN: statutory circulars; FROM_CONTRACT expiry book; expired FUTIDX IDs.
```

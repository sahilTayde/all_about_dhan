# BACKTEST_REVIEW — 2026-09-03 (notes only)

**Team:** 09_review  
**Status:** `NOTES_ONLY` — **not** a five-pass  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`

06 ran `python -m backtest_engine --live --years 5 --interval 1`. Evidence: [`BACKTEST_BOOKS_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_BOOKS_2026-09-03.md).

## Verdicts

| Item | Call |
|------|------|
| Paper algo code (003/001/006 + 007/008/009) | **ACCEPT** as backtest/paper only |
| Live `place_order` | **REJECT** — still refused |
| Proxy win rates as customer edge | **REJECT** |
| Promote MIX-DEFAULT-BUY / any STRAT | **REJECT** — all coded books **FAIL** on OOS win_rate rule |
| Swap default 003 → 001 because ~42% vs ~28% | **REJECT** this session — still FAIL; 001 is PROJECT_MIX; not NORMAL-only |
| Q8 option-fill history | **not waived** — INDEX/FUTIDX points ≠ OPTIDX premium |
| KEEP_ALL catalog | **ACCEPT** — FAIL ≠ delete |
| Five-pass | **not passed** |
| Research-ready | **not set** |

## Red-team

- Equal-weight VWAP on INDEX when used is **PROJECT**, not FUTIDX tape (02).
- Current-month FUTIDX ≠ 5-year futures continuous.
- 348 mixed-index veto days scored in; news days **not** excluded.
- Next-bar-open fills ignore option spread and lots.
- Customer `/ws/signals` is **paper copy**. EARLY/CONFIRMED ≠ fill.

```text
HANDOFF
From: 09
To:   00
Accepted: engine exists; FAIL ratings; KEEP_ALL; orders refused.
Rejected: RESEARCH_READY; promote; invented option P/L.
UNKNOWN: NORMAL-only score; option history.
```

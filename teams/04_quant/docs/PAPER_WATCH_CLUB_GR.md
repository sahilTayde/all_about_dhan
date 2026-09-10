# PAPER_WATCH — MIX-CLUB-GR (KEEP_ALL; PARKED working path)

**Team:** 04_quant (name) · 06 (ledger) · 07 (WS)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **PARKED working path** — **not** customer default  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.** **NO_PROMOTE.**

## Simple English

This is the **gap + range-expansion** club. Optimistic NIFTY wr was **69%** (WEAK). After-cost the same book is **44.4% FAIL promote**. SCORE_SAMPLE is **empty** (no news calendar) so 06 cannot **kill** the MIX. Working-path rule: **PARK** it off customer scoring and paper-watch events so it does not drown the default ticket.

We are **not deleting** the ID.

## Recipe (frozen — do not retune after paper days)

```text
mix_id:     MIX-CLUB-GR
origin:     PROJECT_MIX
working_path: PARKED
rule:       GAP lean AND range-expansion lean (same 3m bar, same CE/PE side)
tape:       cash INDEX 1m → resample 3m (not FUTIDX — history insufficient)
clock:      founder dead band 09:00–09:30 and 15:00–15:30 IST (same as club backtest)
flatten:    session end (before CAS window)
strike:     paper lean only — strike overlay not claimed here
```

Code: `lean_gap` ∧ `lean_range_exp` in `packages/backtest`. Snapshot still lists `books.MIX-CLUB-GR` with `working_path: PARKED` / `paper_watch: false`. Confidence does **not** use the club row.

## Recorded marks (do not collapse)

| Label | What it is | Number | Call |
|-------|------------|--------|------|
| Optimistic backtest | 2y NIFTY option premium, **no** cost haircut | **69.4%** wr, n=36, exp +4.40 | **WEAK** — not a promote ([`BACKTEST_CLUB_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_CLUB_2026-09-03.md)) |
| After hypothesis cost | same book, 1% premium each way | **44.4%** wr, n=36, exp +0.80 | **FAIL** as promote ([`BACKTEST_HONEST_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)) |
| SENSEX | same recipe | ~32–40% | **FAIL** |
| SCORE_SAMPLE (`NORMAL`) | news calendar empty | **n=0** | **DATA_INSUFFICIENT** — not a MIX kill |

**Keep both wr rows.** The 44% is why we do **not** promote. Empty SCORE_SAMPLE is why we **PARK** instead of kill.

## Must not

- Delete this MIX because after-cost FAIL.  
- Kill it without OOS + SCORE_SAMPLE (`NORMAL`).  
- Swap it onto customer `/` as the default ticket.  
- Score it into desk confidence.  
- Place live orders.

```text
HANDOFF
From: 04 / 00
To:   06 / 07 / 09 / founder
Accepted: MIX-CLUB-GR KEEP_ALL + PARKED working path; 69% optimistic recorded; 44% after-cost FAIL promote; SCORE_SAMPLE empty → not kill.
Rejected: promote; customer_default; live orders; lose the book; invent OOS+NORMAL kill.
UNKNOWN: true OOS+NORMAL until a news calendar exists.
```

# PAPER_WATCH — MIX-CLUB-GR (keep; paper in market hours)

**Team:** 04_quant (name) · 06 (ledger) · 07 (WS)  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / **PAPER_WATCH** — **not** customer default  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.**

## Simple English

This is the **gap + range-expansion** club we saw at **69% win rate** on a small NIFTY sample.

We are **not deleting it**. Futures history is too short for a fair futures backtest, so the honest next step is:

1. Keep the recipe written down.  
2. **Paper-trade it in market hours** next to the default ticket.  
3. Compare shadow P/L later — still not a live order.

## Recipe (frozen — do not retune after paper days)

```text
mix_id:     MIX-CLUB-GR
origin:     PROJECT_MIX
rule:       GAP lean AND range-expansion lean (same 3m bar, same CE/PE side)
tape:       cash INDEX 1m → resample 3m (not FUTIDX — history insufficient)
clock:      founder dead band 09:00–09:30 and 15:00–15:30 IST (same as club backtest)
flatten:    session end (before CAS window)
strike:     paper lean only — strike overlay not claimed here
```

Code: `lean_gap` ∧ `lean_range_exp` in `packages/backtest` · live parallel book in `live_signals.py`.

## Recorded marks (do not collapse)

| Label | What it is | Number | Call |
|-------|------------|--------|------|
| Optimistic backtest | 2y NIFTY option premium, **no** cost haircut | **69.4%** wr, n=36, exp +4.40 | **WEAK** — keep for paper; not a promote ([`BACKTEST_CLUB_2026-09-03.md`](../../06_backtesting/docs/BACKTEST_CLUB_2026-09-03.md)) |
| After hypothesis cost | same book, 1% premium each way | **44.4%** wr, n=36, exp +0.80 | **FAIL** as promote ([`BACKTEST_HONEST_2026-09-06.md`](../../06_backtesting/docs/BACKTEST_HONEST_2026-09-06.md)) |
| SENSEX | same recipe | ~32–40% | **FAIL** |
| Live paper | market-hours shadow | **null until sessions run** | PAPER_WATCH |

**Keep both rows.** The 69% is the reason we paper-watch. The 44% is why we do **not** promote or go live.

## Parallel paper (market hours)

Customer default stays **`MIX-DEFAULT-BUY`**.  
**MIX-CLUB-GR** rides in parallel on `/ws/signals?live=1` under `books.MIX-CLUB-GR`.

```bash
# API with tokens in .env — no npm restart required for this path
# Client connects: /ws/signals?live=1
# Snapshot: GET /paper/live-signals
# Shadow log: data/recon/paper_watch/MIX-CLUB-GR/YYYY-MM-DD.jsonl
```

Orders stay **refused**. Browser never holds Dhan tokens.

## Must not

- Delete this MIX because after-cost FAIL.  
- Swap it onto customer `/` as the default ticket.  
- Treat one paper day as a backtest.  
- Place live orders.  
- Invent a new win rate from paper until 06 scores a real ledger.

```text
HANDOFF
From: 04 / 00
To:   06 / 07 / 09 / founder
Accepted: MIX-CLUB-GR KEEP + PAPER_WATCH; 69% optimistic recorded; 44% after-cost recorded.
Rejected: promote; customer_default; live orders; lose the book.
UNKNOWN: live paper expectancy until sessions accumulate.
```

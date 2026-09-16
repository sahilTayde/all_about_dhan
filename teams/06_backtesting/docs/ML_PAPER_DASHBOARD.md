# ML / paper scalper monitoring board

**As of (IST):** `2026-09-16T13:26:55+05:30`  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. paper win_rate=0.0% (0/14 closed). ₹10000.0 / book.

Parallel independent books: one OPEN per (`book_id` × underlying). A HOLD on ML-001 does **not** block MIX-DEFAULT-BUY.

## Leaderboard (CLOSED premium P/L only)

| book | underlying | n | wins | losses | wr% | sum pts | sum ₹ |
|------|------------|---|------|--------|-----|---------|-------|
| `MIX-DEFAULT-BUY` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `MIX-ML-LOGIT` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `MIX-ML-LOGIT-XR` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `MIX-TV-EP-024` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `ML-001` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `ML-002` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |
| `ML-1` | NIFTY | 2 | 0 | 2 | 0.0 | -5.35 | -347.75 |

PAPER cache replay only (aligned INDEX∩ATM 1m on disk, typically 2026-09-09..10). Not fills. Rank ≠ promote. `MIX-ML-LOGIT*` trains on INDEX 3m before the ATM session. `win_rate` = paper closed hit rate (pnl>0), not a promote. `MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.


## Models / steps

| id | closed | W | L | wr% | equity ₹ | last run |
|----|--------|---|---|-----|----------|----------|
| `MIX-DEFAULT-BUY` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `ML-001` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `ML-002` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `ML-1` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `MIX-ML-LOGIT` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `MIX-ML-LOGIT-XR` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |
| `MIX-TV-EP-024` | 2 | 0 | 2 | 0.0 | 9652.25 | `2026-09-16T13:26:55+05:30` |

## Closed tickets (strike / limit / target / SL)

| model | und | side | strike | limit | target | stop | sl_hit | sl_loss ₹ | pnl ₹ | result |
|-------|-----|------|--------|-------|--------|------|--------|-----------|-------|--------|
| `MIX-DEFAULT-BUY` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `ML-001` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `ML-002` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `ML-1` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `MIX-ML-LOGIT` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `MIX-ML-LOGIT-XR` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `MIX-TV-EP-024` | NIFTY | PE | 23500.0 | 109.4 | 112.0125 | 107.5 | True | -172.25 | -172.25 | LOSS |
| `MIX-DEFAULT-BUY` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `ML-001` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `ML-002` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `ML-1` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `MIX-ML-LOGIT` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `MIX-ML-LOGIT-XR` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |
| `MIX-TV-EP-024` | NIFTY | CE | 23500.0 | 163.25 | 166.165 | 161.13 | True | -175.5 | -175.5 | LOSS |

## DATA_INSUFFICIENT

- (none on this inventory pass)

## How to watch

```bash
python -m desk_ml paper-scalp --replay
# opt-in loop (does not start paper_ops / npm):
python -m desk_ml paper-scalp --loop --tick-seconds 45
touch data/recon/ml_paper_scalp_STOPPED.flag
```

JSON: `data/recon/ml_paper_dashboard.json` (gitignored) · mock: `apps/web/public/mock/ml_paper_dashboard.json`  
UI: `/pm` and `/desk` (existing Vite; do not restart npm). API: `GET /paper/ml-books`.

KEEP_ALL STRAT-001–014. No STRAT-015+.


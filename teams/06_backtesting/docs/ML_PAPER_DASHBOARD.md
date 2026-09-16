# ML / paper scalper monitoring board

**As of (IST):** `2026-09-16T13:06:53+05:30`  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. paper `win_rate`=0.437 (2218/5076 closed, pnl>0).

Parallel independent books: one OPEN per (`book_id` × underlying). A HOLD on ML-001 does **not** block MIX-DEFAULT-BUY.

## Leaderboard (CLOSED premium P/L only)

| book | underlying | n_closed | sum premium P/L | win_rate |
|------|------------|----------|-----------------|----------|
| `MIX-TV-EP-024` | SENSEX | 446 | 1941.45 | 0.5247 |
| `MIX-TV-EP-024` | BANKNIFTY | 459 | 1131.25 | 0.5054 |
| `MIX-ML-LOGIT` | NIFTY | 389 | 112.9 | 0.5141 |
| `MIX-ML-LOGIT-XR` | SENSEX | 17 | 97.15 | 0.5882 |
| `MIX-TV-EP-024` | NIFTY | 420 | 46.75 | 0.4786 |
| `MIX-ML-LOGIT-XR` | BANKNIFTY | 14 | 23.1 | 0.5 |
| `MIX-ML-LOGIT-XR` | NIFTY | 14 | -1.6 | 0.5 |
| `ML-1` | NIFTY | 7 | -37.55 | 0.2857 |
| `MIX-ML-LOGIT` | SENSEX | 385 | -346.8 | 0.4623 |
| `MIX-DEFAULT-BUY` | NIFTY | 273 | -405.45 | 0.4139 |
| `ML-002` | NIFTY | 262 | -425.9 | 0.4046 |
| `ML-001` | NIFTY | 270 | -430.9 | 0.4111 |
| `MIX-ML-LOGIT` | BANKNIFTY | 440 | -435.65 | 0.4591 |
| `ML-002` | BANKNIFTY | 285 | -1167.5 | 0.386 |
| `MIX-DEFAULT-BUY` | BANKNIFTY | 292 | -1732.35 | 0.3664 |
| `ML-001` | BANKNIFTY | 292 | -1732.35 | 0.3664 |
| `ML-002` | SENSEX | 261 | -2186.5 | 0.3716 |
| `MIX-DEFAULT-BUY` | SENSEX | 275 | -2674.4 | 0.3527 |
| `ML-001` | SENSEX | 275 | -2674.4 | 0.3527 |

PAPER cache replay only (aligned INDEX∩ATM 1m on disk, typically 2026-09-09..10). Not fills. Rank ≠ promote. `MIX-ML-LOGIT*` trains on INDEX 3m before the ATM session. `win_rate` = paper closed hit rate (pnl>0), not a promote. `MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.


## Models / steps

| id | what | closed | wr | last run |
|----|------|--------|----|----------|
| `MIX-DEFAULT-BUY` | Dealer CE/PE from INDEX vs ATM CE/PE deltas. Customer default ID; PAPER only. | 840 | 0.3774 | `2026-09-16T13:06:53+05:30` |
| `ML-001` | KMeans+IsolationForest overlay. SKIP if HOLD/FOLLOW-GAP. Does not invent CE/PE. | 837 | 0.3763 | `2026-09-16T13:06:53+05:30` |
| `ML-002` | OU residual |z|≥2 or FOLLOW-GAP SKIP. Windows 40/60/90. Does not invent CE/PE. | 808 | 0.3874 | `2026-09-16T13:06:53+05:30` |
| `ML-1` | Meta-label take/skip on closed paper labels. Else DATA_INSUFFICIENT. | 7 | 0.2857 | `2026-09-16T13:06:53+05:30` |
| `MIX-ML-LOGIT` | INDEX 3m walk-forward logit (ml_leans.py). Scan book. Not customer default. | 1214 | 0.4778 | `2026-09-16T13:06:53+05:30` |
| `MIX-ML-LOGIT-XR` | Logit AND range-expansion. Scan book. Not customer default. | 45 | 0.5333 | `2026-09-16T13:06:53+05:30` |
| `MIX-TV-EP-024` | Factory SMA20 INDEX calibrator → ATM CE/PE. KEEP_ALL lab. Not a promote. | 1325 | 0.5034 | `2026-09-16T13:06:53+05:30` |

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


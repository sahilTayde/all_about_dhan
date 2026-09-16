# ML / paper scalper monitoring board

**As of (IST):** `2026-09-16T12:48:31+05:30`  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **NO_PROMOTE.** Orders refused. `win_rate=null`.

Parallel independent books: one OPEN per (`book_id` × underlying). A HOLD on ML-001 does **not** block MIX-DEFAULT-BUY.

## Leaderboard (CLOSED premium P/L only)

| book | underlying | n_closed | sum premium P/L | win_rate |
|------|------------|----------|-----------------|----------|
| `MIX-TV-EP-024` | BANKNIFTY | 159 | 516.7 | null |
| `MIX-TV-EP-024` | SENSEX | 147 | 327.8 | null |
| `MIX-TV-EP-024` | NIFTY | 138 | 70.15 | null |
| `ML-1` | NIFTY | 6 | -11.35 | null |
| `ML-002` | NIFTY | 92 | -186.8 | null |
| `MIX-DEFAULT-BUY` | NIFTY | 94 | -191.45 | null |
| `ML-001` | NIFTY | 94 | -191.45 | null |
| `MIX-DEFAULT-BUY` | BANKNIFTY | 102 | -604.05 | null |
| `ML-001` | BANKNIFTY | 102 | -604.05 | null |
| `ML-002` | BANKNIFTY | 98 | -624.7 | null |
| `ML-002` | SENSEX | 92 | -918.3 | null |
| `MIX-DEFAULT-BUY` | SENSEX | 94 | -988.75 | null |
| `ML-001` | SENSEX | 94 | -988.75 | null |

PAPER cache replay only (aligned INDEX∩ATM 1m on disk, typically 2026-09-09..10). Not fills. Rank ≠ promote. `MIX-ML-LOGIT*` 0 rows when 3m train < 200. `MIX-TV-EP-024` SMA lab is KEEP_ALL, not customer default.


| id | what | closed | open | last run |
|----|------|--------|------|----------|
| `MIX-DEFAULT-BUY` | Dealer CE/PE from INDEX vs ATM CE/PE deltas. Customer default ID; PAPER only. | 290 | 0 | `2026-09-16T12:48:31+05:30` |
| `ML-001` | KMeans+IsolationForest overlay. SKIP if HOLD/FOLLOW-GAP. Does not invent CE/PE. | 290 | 0 | `2026-09-16T12:48:31+05:30` |
| `ML-002` | OU residual |z|≥2 or FOLLOW-GAP SKIP. Windows 40/60/90. Does not invent CE/PE. | 282 | 0 | `2026-09-16T12:48:31+05:30` |
| `ML-1` | Meta-label take/skip on closed paper labels. Else DATA_INSUFFICIENT. | 6 | 0 | `2026-09-16T12:48:31+05:30` |
| `MIX-ML-LOGIT` | INDEX 3m walk-forward logit (ml_leans.py). Scan book. Not customer default. | 0 | 0 | `2026-09-16T12:48:31+05:30` |
| `MIX-ML-LOGIT-XR` | Logit AND range-expansion. Scan book. Not customer default. | 0 | 0 | `2026-09-16T12:48:31+05:30` |
| `MIX-TV-EP-024` | Factory SMA20 INDEX calibrator → ATM CE/PE. KEEP_ALL lab. Not a promote. | 444 | 0 | `2026-09-16T12:48:31+05:30` |

## DATA_INSUFFICIENT

- DATA_INSUFFICIENT: NIFTY INDEX 1m cache last_ist=2026-09-03 — no fabricate for 2026-09-11..16
- DATA_INSUFFICIENT: BANKNIFTY INDEX 1m cache last_ist=2026-09-03 — no fabricate for 2026-09-11..16
- DATA_INSUFFICIENT: SENSEX INDEX 1m cache last_ist=2026-09-03 — no fabricate for 2026-09-11..16

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


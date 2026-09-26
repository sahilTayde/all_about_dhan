# risk-engine (PR-003)

Deterministic veto before any order. Fail closed: any exception, unreadable config, missing
ledger or failed audit write is a veto (`ENGINE_ERROR`, critical).

`RiskEngine(ledger).check_entry(intent)` runs these checks in order and returns the first veto:

| Code | Rule (from `config/risk_limits.yaml`) |
|---|---|
| `MODE_NOT_ENABLED` | mode `limited_live`/`live` without `ALL_ABOUT_DHAN_LIVE_CONFIRM=I_UNDERSTAND_REAL_MONEY` |
| `KILL_SWITCH` | `kill_switch: true` or the `kill_switch_file` exists (critical) |
| `RECON_MISMATCH` | last broker reconciliation had a mismatch (critical) |
| `TIME_GATE` | before `entry_start_ist` (09:15) or at/after `entry_cutoff_ist` (15:00) IST |
| `DUPLICATE` | same symbol+side+lots within `idempotency_seconds`, or reused client order id |
| `MAX_LOTS` / `MAX_OPEN_POSITIONS` | per-mode limits |
| `MAX_LOSS_PER_TRADE` | (entry − stop) × qty; a long with no stop risks the whole premium |
| `MAX_DAILY_LOSS` | today's net P&L already at the limit (critical) or this trade's risk would cross it |
| `COOLDOWN` | a losing exit less than `cooldown_after_loss_minutes` (15) ago |

`check_exit(intent, action)` (EXIT / MODIFY / CANCEL) and `check_flatten()` only apply the mode
gate (and duplicate-exit check), so positions can always be closed under the kill switch.

Config is re-read on every check. State (open positions, today's net P&L, last losing exit,
recent approvals, last reconciliation) is rebuilt from the ledger on every entry check, so a
restart loses nothing. Every decision is written to `risk_decisions`; health alarms on critical
ones. Measured latency with an on-disk ledger: p50 ~5 ms, p99 ~9 ms.

Tests (from repo root):
`PYTHONPATH=packages/ledger/src:packages/risk-engine/src python -m pytest packages/risk-engine -q`

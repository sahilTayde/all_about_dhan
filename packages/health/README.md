# health (PR-004)

Small, read-only monitor. Every 60 s it checks:

| Check | Source | Alarm when |
|---|---|---|
| `recorder` | `data/recon/recorder_heartbeat.jsonl` (data-recorder, PR-001) | last beat > 5 min old, missing, or `DATA_STALE`, during market hours |
| `paper_engine` | `data/recon/ml_paper_dashboard.json` `heartbeat.as_of_ist` (rewritten by the desk_ml paper-scalp loop; engine not modified) | same 5-minute rule |
| `reconciliation` | ledger `recon_runs` (brokers.reconcile) | latest run had a mismatch (clears on the next clean run) |
| `risk_vetoes` | ledger `risk_decisions` where `critical = 1` | any new critical veto today (kill switch, daily loss hit, recon halt, engine error) |
| `disk` | free space on the `data/` volume | below `--min-free-gb` (default 2 GB) |

Market hours = 09:15–15:30 IST, Monday–Friday (exchange holidays are not modelled). Outside
them, stale data is reported but not alarmed.

Output: `data/health/alerts.jsonl` (append-only; one `ALERT` per failing check, repeated every
15 min while it stays bad, plus `RECOVERED`) and `data/health/status.json` (latest snapshot).
`apps/api` serves both read-only at `GET /health/status` and `GET /health/alerts?limit=50`.
Telegram push only if both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set (stdlib
`urllib`, no new dependency); otherwise file + API only.

```bash
PYTHONPATH=packages/health/src python -m health --once   # one pass, prints status JSON
PYTHONPATH=packages/health/src python -m health          # loop every 60 s
```

Tests: `PYTHONPATH=packages/ledger/src:packages/health/src python -m pytest packages/health -q`

## V2-14 (paper only)

`V2HealthMonitor` adds section 5.4 checks on a snapshot (engine heartbeat, feed
status, consumer lag, outbox backlog, checkpoint age, protective stop, restart
breaker, backup age, token expiry, depth coverage) plus a loopback
`127.0.0.1/metrics` endpoint (`prometheus-client`). Alerts are queued: a slow or
failing Telegram sink cannot stall `MemoryBus.publish`. Alert text is sanitised
so tokens never appear. REG-02d / REG-09a (alarm half) live in
`packages/health/tests/test_v2_health.py`.

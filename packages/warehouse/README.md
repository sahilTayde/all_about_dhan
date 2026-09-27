# warehouse (DATA-001)

Append-only SQLite store for paper/shadow desk events.

- Default path: `data/knowledge/warehouse.sqlite` (do **not** git-add)
- Never opens `transcripts.sqlite` or `trading_agents_india.sqlite`
- WAL on; raw rows are insert-only
- No live orders, no invented LTP

```bash
python -m warehouse init
python -m warehouse status
```

## Nightly ETL (PR-013)

Separate derived file: `data/warehouse/analytics.sqlite` (gitignored, rebuildable). Reads only.

| Source (under `--root`) | Loaded into |
|---|---|
| `data/recon/paper_booked/<day>.jsonl` (per-day paper book) | `trades_raw` (priority 1) |
| `data/recon/ml_paper_dashboard.json` (board; one unit per session day) | `trades_raw` (2), `trade_models`, boss skip counts |
| `data/ledger/*.sqlite`, `data/events/*.sqlite` (ledger and/or event audit) | `trades_raw` (3), `fills`, `charges`, risk decisions, recon runs, `analyst_votes`, stage counts |
| `data/recon/ml_paper_model_logs.jsonl` (+ `archive/*.pre_slate`) | `model_log` |
| `data/recon/EOD_RECON_<day>.json` | `recon_reports` |

- Idempotent: every row carries `src_file`; a changed file's rows are replaced in one transaction.
- Incremental: JSONL files are tail-loaded from the last consumed byte (a rewritten prefix reloads
  the file); other files reload only when their bytes change. `run --full` rebuilds.
- Bad input is quarantined, never fatal: a bad field is stored as NULL, a bad line or file is
  skipped, and each gets a `rejects` row (file, line number, field, reason, sample;
  `python -m warehouse.etl query rejects`). Re-runs skip unchanged files, so the same rejects are
  not re-read every night. Only transient read failures count as `errors` (exit 1) and are retried.
- Rollups are views: `trades` (one row per trade id, best source wins), `pnl_daily|weekly|monthly`,
  `exit_reasons`, `model_attribution`, `stage_attribution`, `analyst_vote_summary`.
- Read-only helpers for the Founder page: `warehouse.queries` (`pnl`, `exit_reasons`,
  `model_attribution`, `stage_attribution`, `analyst_votes`, `slippage`, `charges`, `etl_status`).

```bash
python -m warehouse.etl run                     # or scripts/nightly_warehouse_etl.sh [--root DIR] (cron)
python -m warehouse.etl query pnl --period week
python -m warehouse.etl status
```

Spec: [`docs/PRODUCT_ARCHITECTURE_STANDARDS.md`](../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md) § Data Standard.
Dealer rules: `warehouse.feasibility` (DEALER-001).

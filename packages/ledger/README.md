# ledger (PR-005)

Persistent, append-only trade ledger plus an Indian index-option charges calculator.

- Storage: stdlib `sqlite3` at `data/ledger/ledger.sqlite` (gitignored). SQLite, not DuckDB:
  this is a single-writer operational store (docs/02_TARGET_ARCHITECTURE.md recommends SQLite
  for orders/positions/ledger) and it adds no dependency. DuckDB can read the file for analytics.
- Tables: `orders`, `order_events` (every state transition), `fills` (slippage = fill price −
  decision price), `positions`, `trades` (entry/exit price, entry/exit slippage, exit reason
  code, cancel reason code, gross, charges, net), `charges` (per fill), `risk_decisions`,
  `recon_runs`. `daily_pnl` is a view over closed trades (gross, charges, net).
- Append-only: SQLite triggers abort any DELETE (and any UPDATE on fills, events, charges,
  decisions, recon runs).
- Charges: `config/charges.yaml`, the same rates as the paper desk's
  `desk_ml/groww_costs.py` (₹20/order, STT 0.15% sell, exchange 0.03503%, SEBI 0.0001%,
  stamp 0.003% buy, GST 18%). Brokerage is charged once per order, not per partial fill.

```python
from ledger import Ledger
led = Ledger()                       # data/ledger/ledger.sqlite, rates from config/charges.yaml
led.daily_pnl("2026-09-28")          # {'n_trades', 'gross_pnl', 'charges', 'net_pnl'}
```

Tests (from repo root): `PYTHONPATH=packages/ledger/src python -m pytest packages/ledger -q`

## V2-21 Postgres (M2, paper only)

Default engine stays SQLite-WAL (`config/v2/store.yaml`). Postgres is the customer-milestone store
(architecture §3.2): same `LedgerStore` methods, fail-closed migrations, health ping, and
`python -m ledger export --to postgres --from data/state/aad.sqlite`.

- Set `STATE_DSN=postgresql://...` (never commit it). Rollback = flip `STATE_DSN` back; the
  SQLite file is untouched.
- Shared DDL: `packages/ledger/migrations/NNN_name.sql`. Append-only triggers for Postgres:
  `NNN_name.pg.sql`. A failed migration does not record `schema_version`.
- Dual-engine CI: sqlite tests always run; postgres tests run when `STATE_DSN` is set.
- Optional extra: `pip install -e packages/ledger[postgres]` (`psycopg`). No live broker.

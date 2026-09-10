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

Spec: [`docs/PRODUCT_ARCHITECTURE_STANDARDS.md`](../../docs/PRODUCT_ARCHITECTURE_STANDARDS.md) § Data Standard.
Dealer rules: `warehouse.feasibility` (DEALER-001).

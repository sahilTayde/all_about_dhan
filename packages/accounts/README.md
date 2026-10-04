# accounts (V2-22)

Fail-closed paper/shadow account model. `account_id` isolates ledger partition, positions, sizing, and `pos:<account>` streams. Shared `runtime signal` vs per-account `runtime exec --account`.

**Paper only. No live broker. No Dhan credentials. No customer live execution.**

```bash
python -m accounts list
python -m runtime signal --once --state-dir /tmp/v2-signal
python -m runtime exec --account founder --once --state-dir /tmp/v2-exec
```

| Path | Owner |
|------|--------|
| `config/v2/accounts.yaml` | Paper `founder` + shadow `v2-shadow` |
| `ledger:<account_id>` | Per-account ledger partition |
| `pos:<account_id>` | Per-account position stream |

Fail closed: unknown / disabled / halted account, live broker name, missing config, or a cross-account read/write/size.

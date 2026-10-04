# accounts (V2-22 / C5-01)

Fail-closed paper/shadow account model. `account_id` isolates ledger partition, positions, sizing, and `pos:<account>` streams. Shared `runtime signal` vs per-account `runtime exec --account`.

**Paper only. No live broker. No Dhan credentials. No customer live execution.**

This launch cut lists **5 customer paper books** (`customer-01` … `customer-05`). They stay **disabled** until the founder enables one. Isolation stays fail-closed: account A cannot read, write, or size account B. Unknown ids fail closed. Live broker names refuse the whole directory. Customer count is **capped at 5**.

Founder book is buying-only paper (~₹1–2L product capital). `risk_budget_inr` on the founder row is the isolated paper stop budget (₹30,000). Customers get `signals:public` later — this package is directory + isolation + listing only.

```bash
python -m accounts list
python -m accounts enable --account customer-01
python -m accounts disable --account customer-01
python -m accounts show --account customer-01
python -m runtime signal --once --state-dir /tmp/v2-signal
python -m runtime exec --account founder --once --state-dir /tmp/v2-exec
```

Enable writes `status: active` on that row in `config/v2/accounts.yaml` (or `--config`). `--mode live` / broker `dhan` is refused. A disabled customer still appears on `list` and fails `require_active` / `runtime exec`.

| Path | Owner |
|------|--------|
| `config/v2/accounts.yaml` | Paper `founder`, shadow `v2-shadow`, disabled `customer-01`…`customer-05` |
| `config/v2/accounts/customers.example.yaml` | Optional overlay template. Copy to gitignored `customers.yaml` and set `AAD_CUSTOMERS` only if the main file does not already list those ids |
| `ledger:<account_id>` | Per-account ledger partition |
| `pos:<account_id>` | Per-account position stream |

Fail closed: unknown / disabled / halted account, live broker name, missing config, more than 5 customer rows, or a cross-account read/write/size.

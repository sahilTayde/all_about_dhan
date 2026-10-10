# accounts (V2-22 / C5-01 / C5-07)

Fail-closed paper/shadow account model. `account_id` isolates ledger partition, positions, sizing, and `pos:<account>` streams. Shared `runtime signal` vs per-account `runtime exec --account`.

**Paper only. No live broker. No Dhan credentials. No customer live execution.**

This launch cut lists **5 customer paper books** (`customer-01` … `customer-05`). They stay **disabled** until the founder enables one. Isolation stays fail-closed: account A cannot read, write, or size account B. Unknown ids fail closed. Live broker names refuse the whole directory. Customer count is **capped at 5**.

**C5-07 slots:** each launch book has one placeholder slot + `journal_tag`. `strategy_id` and `basket` stay **unset** (`slot_armed: false`) until desk lead assigns a real registry id or paper/shadow basket name. Slot labels are journal tags, not claimed edge.

| portal JWT `sub` | `account_id` | `slot` | `journal_tag` | registry `strategy_id` (unset until desk lead writes it) |
|---|---|---|---|---|
| `c1` | `customer-01` | CONTROL | `SLOT-CONTROL` | `R01_PDIV_5_ALL_H20` |
| `c2` | `customer-02` | CANDLE_GEOM | `SLOT-CANDLE_GEOM` | `R01_B3A_VOL` |
| `c3` | `customer-03` | LOCATION | `SLOT-LOCATION` | `B8B_B3A_EX_CHOPPY` |
| `c4` | `customer-04` | SKLEARN | `SLOT-SKLEARN` | `R07_MOM3_TREND` |
| `c5` | `customer-05` | HYBRID_OR_ROUTER | `SLOT-HYBRID_OR_ROUTER` | `B8A_R07_NO_PRE1030` |

Portal seats are C5-02 JWT `sub` values (`AAD_PAPER_CUSTOMERS=c1,c2,c3,c4,c5`). They were not bound to paper books before this ticket. `python -m accounts list` prints `portal_map`. `runtime exec --account` now reads `slot` / `journal_tag` / `strategy_id` / `basket` from the account row.

Founder book is buying-only paper (~₹1–2L product capital). `risk_budget_inr` on the founder row is the isolated paper stop budget (₹30,000). Customers get `signals:public` later — this package is directory + isolation + listing + slot tags only.

```bash
python -m accounts list
python -m accounts enable --account customer-01
python -m accounts disable --account customer-01
python -m accounts show --account customer-01
python -m runtime signal --once --state-dir /tmp/v2-signal
python -m runtime exec --account founder --once --state-dir /tmp/v2-exec

# C5-04 founder ops (paper/shadow only; never live)
./scripts/desk.sh c5-start --dry-run
./scripts/desk.sh c5-start             # one shared signal + <=5 customer execs
./scripts/desk.sh c5-status
./scripts/desk.sh c5-backup
./scripts/desk.sh c5-restore --dry-run --snapshot data/c5-backups/c5-paper.tgz
./scripts/desk.sh c5-stop
```

Enable writes `status: active` on that row in `config/v2/accounts.yaml` (or `--config`). `--mode live` / broker `dhan` is refused. A disabled customer still appears on `list` and fails `require_active` / `runtime exec`.

## Market ops — enable one account at a time

Tonight ops does **not** auto-enable five books. Desk lead assigns first. Then enable **one** row:

1. Confirm `python -m accounts list` — all five customers `status: disabled`, `slot_armed: false`.
2. Desk lead writes **one** of `strategy_id` (registry id already in `config/v2/strategies/registry.yaml`) or `basket` (paper/shadow basket stem such as `approved_paper_shadow`) on that customer row only. Leave the other four unset.
3. `python -m accounts enable --account customer-01` (or `customer-02` … `05`). Never `--mode live`.
4. `mkdir -p data/c5/signal data/c5/exec/customer-01`
5. `./scripts/desk.sh c5-start --dry-run` — expect `live_broker: false`, that exec's `journal_tag` / `slot`, and `slot_armed: true` only on the assigned book.
6. Start paper night only after the dry-run looks right. Disable with `python -m accounts disable --account customer-01` before enabling a second book.

Empty `strategy_id` + empty `basket` means the exec path can bind the book and stamp `journal_tag`, but it does **not** arm a plugin (no invented trades). Global V2 shadow still uses `config/v2/baskets/approved_paper_shadow.yaml` on `v2-shadow` and is unchanged.

| Path | Owner |
|------|--------|
| `config/v2/accounts.yaml` | Paper `founder`, shadow `v2-shadow`, disabled `customer-01`…`customer-05` with C5-07 slots (`strategy_id`/`basket` unset) |
| `config/v2/accounts/customers.example.yaml` | Optional overlay template. Copy to gitignored `customers.yaml` and set `AAD_CUSTOMERS` only if the main file does not already list those ids |
| `ledger:<account_id>` | Per-account ledger partition |
| `pos:<account_id>` | Per-account position stream |
| `data/c5/signal` | Shared C5 `runtime signal` state (not the legacy book) |
| `data/c5/exec/<id>` | Per-account C5 `runtime exec` state |

Fail closed: unknown / disabled / halted account, live broker name, missing config, more than 5 customer rows, a cross-account read/write/size, **C5 live mode**, **>5 active customer execs**, missing `data/c5` state dirs, or a C5 state path under `data/recon` / `data/shadow` / `paper_watch`. Founder + `v2-shadow` execs are opt-in (`--with-founder` / `--with-shadow`) and do not count toward the 5-customer cap. Night checklist: root `README.md` § 5-customer paper night.

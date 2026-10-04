# shadow (V2 paper-only launcher)

Log-only V2 book that runs **beside** the legacy dual-tape desk. Legacy keeps the live paper book. This package writes isolated decision and P&L rows under `data/shadow/v2/` for a daily side-by-side compare.

**Paper only. No live orders. No Dhan execution. No shared broker with the legacy path.**

```bash
# Mac: isolated 3.11+ venv (never the legacy .venv)
./scripts/mac_setup_v2.sh
./scripts/desk.sh shadow-start    # optional; failure does not stop legacy
./scripts/desk.sh shadow-status
./scripts/desk.sh shadow-stop

# Dry-run (fixture tape + dry-run basket, no network)
.venv-v2/bin/python -m shadow dry-run
```

Mac — basket + shadow beside dual-tape (does **not** replace the legacy desk):

```bash
# 1) Confirm the founder-approved paper/shadow basket (or write a dated override)
ls config/v2/baskets/approved_paper_shadow.yaml
# optional same-day override (session must match IST date):
#   config/v2/baskets/YYYY-MM-DD.yaml

# 2) Legacy dual-tape stays the live paper book
./scripts/desk.sh watch-open

# 3) V2 shadow journals beside it (failure only warns)
./scripts/desk.sh shadow-start
./scripts/desk.sh shadow-status
.venv-v2/bin/python -m shadow dry-run   # ENTER or an explicit V2 abstain (never HOLD-only)
```

| Path | Owner |
|------|--------|
| `config/v2/baskets/approved_paper_shadow.yaml` | Founder-approved paper/shadow fallback (no `TEST-CROSS`) |
| `config/v2/baskets/dry_run.yaml` | Dry-run only (`TEST-CROSS`) |
| `config/v2/exits/defaults.yaml` | Round-11 exits hashed onto every journal row |
| `data/shadow/v2/YYYY-MM-DD/decisions.jsonl` | V2 shadow decisions (`ENTER` or explicit abstain) |
| `data/shadow/v2/YYYY-MM-DD/pnl.jsonl` | Isolated paper marks (`account=v2-shadow`) |
| `data/shadow/<YYYY-MM-DD>.jsonl` | Legacy `desk_ml` shadow-v1 — do not write here |

Fail closed: missing tape, missing basket, missing registry/exit defaults, live mode, or a path that would mutate the legacy book → no new entries. Exits are V2 `SHADOW_FLAT` only; legacy `CANCEL` / `COVER_LONG_UNWIND` stay the comparison baseline and are not copied. Approved-basket R8 rows that are `PENDING_LAB` log that reason instead of a silent `HOLD`.

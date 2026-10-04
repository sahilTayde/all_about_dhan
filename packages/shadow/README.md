# shadow (V2 paper-only launcher)

Log-only V2 book that runs **beside** the legacy dual-tape desk. Legacy keeps the live paper book. This package writes isolated decision and P&L rows under `data/shadow/v2/` for a daily side-by-side compare.

**Paper only. No live orders. No Dhan execution. No shared broker with the legacy path.**

```bash
# Mac: isolated 3.11+ venv (never the legacy .venv)
./scripts/mac_setup_v2.sh
./scripts/desk.sh shadow-start    # optional; failure does not stop legacy
./scripts/desk.sh shadow-status
./scripts/desk.sh shadow-stop

# Dry-run (fixture tape, no network)
.venv-v2/bin/python -m shadow dry-run
```

| Path | Owner |
|------|--------|
| `data/shadow/v2/YYYY-MM-DD/decisions.jsonl` | V2 shadow decisions (HOLD by default) |
| `data/shadow/v2/YYYY-MM-DD/pnl.jsonl` | Isolated paper marks (`account=v2-shadow`) |
| `data/shadow/<YYYY-MM-DD>.jsonl` | Legacy `desk_ml` shadow-v1 — do not write here |

Fail closed: missing tape, live mode, or a path that would mutate the legacy book → no new entries. Exits are V2 `SHADOW_FLAT` only; legacy `CANCEL` / `COVER_LONG_UNWIND` stay the comparison baseline and are not copied.

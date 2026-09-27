# V2-01 Contracts Foundation — HANDOFF

**Branch:** `cursor/v2-01-foundation-rebased-396a`  
**Base:** `origin/main` at `6cae481` (PR #33 recorder), merged in with a merge commit (no rebase).  
**This note:** written after the B1–B7 verification fixes. Do not treat the PR as merge-ready until all 6 GitHub CI checks are green on the head this note names.

## What this PR adds

`packages/contracts` is the V2-01 foundation: envelope, section 4.4 payloads + JSON Schema, SimClock/LiveClock, deterministic IDs, India market adapter, REG-11 test guard in root `conftest.py`.

## B1–B7 (this pass)

| ID | Fix |
|----|-----|
| B1 | Took `requirements/ci.txt` and `requirements/ci.in` from `origin/main` unchanged. `scripts/ci/install.sh` installs **marketdata** and **contracts**. |
| B2 | Holiday **dates** unchanged (17). Labels corrected (municipal election / Holi / Ram Navami / Mahavir Jayanti / Bakri Id / Diwali-Balipratipada / Guru Nanak Dev). Removed the “verified against circulars” claim. Tests pin every date+label and that 2026-08-27, 2026-10-27, 2026-10-28 are trading days. |
| B3 | `signal_id` rejects `\|` in every string input, validates underlying and `n`, hashes the full accepted tuple. Hypothesis: distinct accepted inputs → distinct ids. |
| B4 | `FEED_STATUS` optional `detail`; statuses include `AUTH_FAILED` (and recorder `FRESH` / `DISCONNECT`). Test uses a recorder-shaped AUTH_FAILED row (`status`, `since`, `detail`). |
| B5 | Invalid-stage fixture copies a valid `strike_choice` (3 alternatives) so only `stage` is wrong. Added garbage `strike_choice` rejection test. |
| B6 | Removed the `type: ignore` on `events.schema.Event`. `events` has `py.typed`; contracts mypy path includes `../events/src`. |
| B7 | This HANDOFF rewritten. README example uses Tuesday 2026-09-29. `jsonschema` is a **runtime** dependency in `packages/contracts/pyproject.toml`. |

## Not claimed

- Not merge-ready until CI on the new head is green.
- No live broker, no secrets, no writes to repo `data/` / `config/` from tests.
- Legacy paper replay numbers are unchanged by this package (IDs/schemas only).

## How to check

```bash
bash scripts/ci/install.sh
python -m pytest -q -p no:cacheprovider
cd packages/contracts && ruff check src tests && ruff format --check src tests && mypy --strict src tests
python scripts/ci/scan_repo.py
```

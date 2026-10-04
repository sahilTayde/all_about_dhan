"""Load config/v2/accounts.yaml. Missing, empty, or live rows refuse the whole file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import STATUSES, Account
from accounts.safety import assert_active, assert_paper_only, refuse_broker_name

_REPO_ROOT = Path(__file__).resolve().parents[4]
MAX_CUSTOMER_ACCOUNTS = 5
PAPER_LAUNCH_CUSTOMER_IDS = tuple(f"customer-{i:02d}" for i in range(1, MAX_CUSTOMER_ACCOUNTS + 1))
CUSTOMER_TEMPLATE_BUDGET_INR = 1000
_WRITE_HEADER = (
    "# V2 C5-01 paper/shadow accounts. Fail closed. No live broker. No secrets.\n"
    "# Enable: python -m accounts enable --account customer-01\n"
    "# Disable: python -m accounts disable --account customer-01\n"
)


def default_config_path() -> Path:
    env = os.environ.get("AAD_ACCOUNTS")
    if env:
        return Path(env)
    return _REPO_ROOT / "config" / "v2" / "accounts.yaml"


def optional_customers_path() -> Path | None:
    env = os.environ.get("AAD_CUSTOMERS")
    if not env or not env.strip():
        return None
    return Path(env.strip())


def _yaml() -> Any:
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError as exc:  # pragma: no cover - CI lock always has PyYAML
        raise AccountClosed("YAML_UNAVAILABLE") from exc
    return yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = _yaml()
    if not path.is_file():
        raise AccountClosed(f"ACCOUNTS_CONFIG_MISSING:{path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AccountSafetyError("V2 accounts fail-closed: config root must be a mapping")
    return raw


def _account_rows(raw: dict[str, Any], *, label: str) -> list[dict[str, Any]]:
    rows = raw.get("accounts")
    if not isinstance(rows, list) or not rows:
        raise AccountSafetyError(f"V2 accounts fail-closed: {label} accounts must be a non-empty list")
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise AccountSafetyError("V2 accounts fail-closed: account row must be a mapping")
        out.append(row)
    return out


def assert_customer_cap(accounts: list[Account]) -> None:
    n = sum(1 for acc in accounts if acc.kind == "customer")
    if n > MAX_CUSTOMER_ACCOUNTS:
        raise AccountSafetyError(
            f"V2 accounts fail-closed: customer cap is {MAX_CUSTOMER_ACCOUNTS} for this paper launch (got {n})"
        )


def merge_account_rows(base: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for row in (*base, *extra):
        aid = str(row.get("account_id") or "").strip()
        if not aid:
            raise AccountSafetyError("V2 accounts fail-closed: account_id is required")
        if aid in seen:
            raise AccountSafetyError(f"V2 accounts fail-closed: duplicate account_id {aid!r}")
        seen.add(aid)
        merged.append(row)
    return merged


def load_account_rows(path: str | Path | None = None) -> tuple[list[dict[str, Any]], str, Path]:
    src = Path(path) if path is not None else default_config_path()
    raw = _load_yaml(src)
    rows = _account_rows(raw, label="config")
    overlay = optional_customers_path()
    if overlay is not None:
        extra_raw = _load_yaml(overlay)
        extra = _account_rows(extra_raw, label="overlay")
        rows = merge_account_rows(rows, extra)
    default = str(raw.get("default_account") or "").strip()
    return rows, default, src


def write_accounts_yaml(path: Path, default_account: str, rows: list[dict[str, Any]]) -> None:
    yaml = _yaml()
    payload = {"default_account": default_account, "accounts": rows}
    text = _WRITE_HEADER + yaml.safe_dump(payload, sort_keys=False)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _owning_file(account_id: str, config_path: Path) -> tuple[list[dict[str, Any]], str, Path]:
    raw = _load_yaml(config_path)
    rows = _account_rows(raw, label="config")
    default = str(raw.get("default_account") or "").strip() or "founder"
    if any(str(row.get("account_id") or "").strip() == account_id for row in rows):
        return rows, default, config_path
    overlay = optional_customers_path()
    if overlay is not None and overlay.resolve() != config_path.resolve():
        extra_raw = _load_yaml(overlay)
        extra = _account_rows(extra_raw, label="overlay")
        extra_default = str(extra_raw.get("default_account") or default).strip() or default
        if any(str(row.get("account_id") or "").strip() == account_id for row in extra):
            return extra, extra_default, overlay
    raise AccountClosed(f"UNKNOWN_ACCOUNT:{account_id}")


def set_account_status(
    account_id: str,
    status: str,
    *,
    path: str | Path | None = None,
    mode: str = "paper",
) -> Account:
    """Flip one paper/shadow row. Refuses live mode/broker and a customer count above the launch cap."""
    assert_paper_only(mode)
    aid = (account_id or "").strip()
    if not aid:
        raise AccountClosed("ACCOUNT_ID_REQUIRED")
    wanted = (status or "").strip().lower()
    if wanted not in STATUSES:
        raise AccountSafetyError(f"V2 accounts fail-closed: status {status!r} is not active|disabled|halted")
    src = Path(path) if path is not None else default_config_path()
    rows, default, dest = _owning_file(aid, src)
    updated: dict[str, Any] | None = None
    preview: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("account_id") or "").strip() != aid:
            preview.append(row)
            continue
        refuse_broker_name(str(row.get("broker") or ""))
        changed = dict(row)
        changed["status"] = wanted
        preview.append(changed)
        updated = changed
    if updated is None:
        raise AccountClosed(f"UNKNOWN_ACCOUNT:{aid}")
    overlay = optional_customers_path()
    if dest.resolve() == src.resolve() and overlay is not None and overlay.resolve() != src.resolve():
        extra = _account_rows(_load_yaml(overlay), label="overlay")
        accounts = [Account.from_mapping(row) for row in merge_account_rows(preview, extra)]
    elif dest.resolve() != src.resolve():
        base = _account_rows(_load_yaml(src), label="config")
        accounts = [Account.from_mapping(row) for row in merge_account_rows(base, preview)]
    else:
        accounts = [Account.from_mapping(row) for row in preview]
    assert_customer_cap(accounts)
    if not default:
        raise AccountSafetyError("V2 accounts fail-closed: default_account is required")
    write_accounts_yaml(dest, default, preview)
    return Account.from_mapping(updated)


class AccountRegistry:
    """Named paper/shadow books. Lookup is fail-closed (no implicit founder fallback)."""

    def __init__(self, accounts: list[Account], default_account: str) -> None:
        if not accounts:
            raise AccountSafetyError("V2 accounts fail-closed: registry is empty")
        seen: dict[str, Account] = {}
        for acc in accounts:
            refuse_broker_name(acc.broker)
            if acc.account_id in seen:
                raise AccountSafetyError(f"V2 accounts fail-closed: duplicate account_id {acc.account_id!r}")
            seen[acc.account_id] = acc
        assert_customer_cap(accounts)
        if default_account not in seen:
            raise AccountSafetyError(
                f"V2 accounts fail-closed: default_account {default_account!r} is not in the registry"
            )
        self._accounts = seen
        self.default_account = default_account

    @classmethod
    def load(cls, path: str | Path | None = None) -> AccountRegistry:
        rows, default, _src = load_account_rows(path)
        if not default:
            raise AccountSafetyError("V2 accounts fail-closed: default_account is required")
        accounts = [Account.from_mapping(row) for row in rows]
        return cls(accounts, default)

    def get(self, account_id: str) -> Account:
        aid = (account_id or "").strip()
        if not aid:
            raise AccountClosed("ACCOUNT_ID_REQUIRED")
        found = self._accounts.get(aid)
        if found is None:
            raise AccountClosed(f"UNKNOWN_ACCOUNT:{aid}")
        return found

    def require_active(self, account_id: str) -> Account:
        return assert_active(self.get(account_id))

    def get_default(self) -> Account:
        return self.require_active(self.default_account)

    def ids(self) -> tuple[str, ...]:
        return tuple(self._accounts)

    def customer_ids(self) -> tuple[str, ...]:
        return tuple(acc.account_id for acc in self._accounts.values() if acc.kind == "customer")

    def all(self) -> tuple[Account, ...]:
        return tuple(self._accounts[i] for i in self._accounts)

"""Load config/v2/accounts.yaml. Missing, empty, or live rows refuse the whole file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from accounts.errors import AccountClosed, AccountSafetyError
from accounts.model import Account
from accounts.safety import assert_active, refuse_broker_name

_REPO_ROOT = Path(__file__).resolve().parents[4]


def default_config_path() -> Path:
    env = os.environ.get("AAD_ACCOUNTS")
    if env:
        return Path(env)
    return _REPO_ROOT / "config" / "v2" / "accounts.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - CI lock always has PyYAML
        raise AccountClosed("YAML_UNAVAILABLE") from exc
    if not path.is_file():
        raise AccountClosed(f"ACCOUNTS_CONFIG_MISSING:{path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AccountSafetyError("V2 accounts fail-closed: config root must be a mapping")
    return raw


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
        if default_account not in seen:
            raise AccountSafetyError(
                f"V2 accounts fail-closed: default_account {default_account!r} is not in the registry"
            )
        self._accounts = seen
        self.default_account = default_account

    @classmethod
    def load(cls, path: str | Path | None = None) -> AccountRegistry:
        src = Path(path) if path is not None else default_config_path()
        raw = _load_yaml(src)
        rows = raw.get("accounts")
        if not isinstance(rows, list) or not rows:
            raise AccountSafetyError("V2 accounts fail-closed: accounts must be a non-empty list")
        accounts = [Account.from_mapping(row) for row in rows]
        default = str(raw.get("default_account") or "").strip()
        if not default:
            raise AccountSafetyError("V2 accounts fail-closed: default_account is required")
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

    def all(self) -> tuple[Account, ...]:
        return tuple(self._accounts[i] for i in self._accounts)

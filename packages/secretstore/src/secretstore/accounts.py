"""Account directory Protocol stub (V2-22 may land in parallel — do not import it)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from secretstore.errors import SecretClosed

ALLOWED_KINDS = frozenset({"founder", "customer"})
ALLOWED_STATUS = frozenset({"active"})


class AccountRef(Protocol):
    """Minimal account handle. V2-22 should satisfy this structurally."""

    @property
    def account_id(self) -> str: ...

    @property
    def kind(self) -> str: ...

    @property
    def status(self) -> str: ...


@dataclass(frozen=True)
class AccountStub:
    account_id: str
    kind: str = "customer"
    status: str = "active"


class AccountDirectory(Protocol):
    def require(self, account_id: str) -> AccountRef: ...


class MemoryAccounts:
    """In-process directory for tests and paper wiring. Fail closed on unknown ids."""

    def __init__(self, accounts: list[AccountStub]) -> None:
        self._by_id = {a.account_id: a for a in accounts}

    def require(self, account_id: str) -> AccountStub:
        row = self._by_id.get(account_id)
        if row is None:
            raise SecretClosed("unknown_account")
        if row.kind not in ALLOWED_KINDS or row.status not in ALLOWED_STATUS:
            raise SecretClosed("unknown_account", "inactive")
        return row

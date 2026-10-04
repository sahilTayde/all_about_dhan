"""Fail-closed errors for the V2 accounts layer. Paper/shadow only."""

from __future__ import annotations


class AccountSafetyError(ValueError):
    """Hard refuse: live broker, illegal kind, or poisoned config."""


class AccountClosed(RuntimeError):
    """Fail closed: unknown, disabled, halted, or over-budget. No fallback account."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class AccountIsolationError(PermissionError):
    """Account A cannot read, write, size, or stream as account B."""

    def __init__(self, owner: str, other: str, action: str) -> None:
        super().__init__(f"account {owner!r} cannot {action} account {other!r}")
        self.owner = owner
        self.other = other
        self.action = action

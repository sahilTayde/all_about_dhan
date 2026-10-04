"""Fail-closed errors. Never attach credential values."""

from __future__ import annotations


class SecretClosed(RuntimeError):
    """Refuse to open a broker session. Reason is a stable token, never a secret."""

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        text = reason if not detail else f"{reason}: {detail}"
        super().__init__(text)

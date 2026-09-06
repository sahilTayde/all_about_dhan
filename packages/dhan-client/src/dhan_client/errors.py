"""Errors. Messages must never include tokens or env values."""

from __future__ import annotations


class DhanClientError(Exception):
    """Base error for this package."""


class CredentialsError(DhanClientError):
    """Missing or unusable credentials (values are never included)."""


class DhanApiError(DhanClientError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_type: str | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.error_code = error_code


class DecodeError(DhanClientError):
    """Binary feed frame could not be parsed."""


class SafeModeError(DhanClientError):
    """Order / execution APIs are refused in this pass."""


class NotImplementedInSkeleton(DhanClientError):
    """Documented capability left unwired until VERIFY FROM DOCS."""

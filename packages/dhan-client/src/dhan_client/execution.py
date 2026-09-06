"""Execution surface — present so callers have a module, always refuses.

This pass does **not** place, modify, or cancel orders. Official order APIs
exist on https://dhanhq.co/docs/v2/; they are not imported or called here.
"""

from __future__ import annotations

from dhan_client.config import Settings
from dhan_client.errors import SafeModeError


class ExecutionClient:
    """SafeMode: every mutating trading method raises."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def place_order(self, *_args: object, **_kwargs: object) -> None:
        self._refuse("place_order")

    def modify_order(self, *_args: object, **_kwargs: object) -> None:
        self._refuse("modify_order")

    def cancel_order(self, *_args: object, **_kwargs: object) -> None:
        self._refuse("cancel_order")

    def super_order(self, *_args: object, **_kwargs: object) -> None:
        self._refuse("super_order")

    def forever_order(self, *_args: object, **_kwargs: object) -> None:
        self._refuse("forever_order")

    def _refuse(self, name: str) -> None:
        raise SafeModeError(
            f"{name} is refused. Live order placement is disabled in this skeleton "
            f"(dry_run={self._settings.dry_run})."
        )

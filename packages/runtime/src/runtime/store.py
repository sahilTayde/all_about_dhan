"""Ledger store stub for V2-04. V2-10 replaces this with SQLite/Postgres."""

from __future__ import annotations

import logging
from typing import Self

from contracts.envelope import Envelope

from runtime.kernel import LedgerTransaction

log = logging.getLogger("runtime.store")


class InMemoryLedgerStore:
    """In-memory ledger store. Not durable across processes."""

    def __init__(self) -> None:
        self._checkpoint: tuple[str, str] | None = None
        self._in_transaction = False

    def transaction(self) -> LedgerTransaction:
        """Begin transaction."""
        return InMemoryTransaction(self)

    def checkpoint(self, envelope: Envelope) -> None:
        """Record checkpoint."""
        if not self._in_transaction:
            raise RuntimeError("checkpoint outside transaction")
        self._checkpoint = (envelope.event_id, envelope.available_ts)
        log.debug("Checkpoint: %s @ %s", envelope.event_id, envelope.available_ts)

    def get_last_checkpoint(self) -> tuple[str, str] | None:
        """Return (event_id, available_ts) of last checkpoint, or None."""
        return self._checkpoint


class InMemoryTransaction:
    """Transaction context for the in-memory store."""

    def __init__(self, store: InMemoryLedgerStore) -> None:
        self.store = store

    def __enter__(self) -> Self:
        if self.store._in_transaction:
            raise RuntimeError("nested transaction")
        self.store._in_transaction = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.store._in_transaction = False
        if exc_type is not None:
            log.debug("Transaction rolled back")
        else:
            log.debug("Transaction committed")

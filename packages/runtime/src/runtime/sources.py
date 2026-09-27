"""
Event sources for the engine.

Spec: V2_BUILD_PLAN.md V2-04
"""

from __future__ import annotations

from collections.abc import Iterator

from contracts.envelope import Envelope


class ListSource:
    """
    In-memory event source from a list of envelopes.

    Envelopes must be pre-sorted by (available_ts, stream_priority, seq).
    """

    def __init__(self, envelopes: list[Envelope]) -> None:
        self.envelopes = envelopes
        self._iter: Iterator[Envelope] | None = None

    def __iter__(self) -> ListSource:
        self._iter = iter(self.envelopes)
        return self

    def __next__(self) -> Envelope:
        if self._iter is None:
            raise StopIteration
        return next(self._iter)

    def ack(self, envelope: Envelope) -> None:
        """No-op for list source."""

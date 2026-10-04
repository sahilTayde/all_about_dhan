"""Engine-facing envelope iterators.

V2-03 owns ``marketdata.sources.ListSource`` (ticks + CLOCK). This package does
not define a second ListSource. Kernel tests feed ``Envelope`` objects through
``EnvelopeSource``. ``envelopes_from_list_source`` wraps the marketdata source.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from contracts.envelope import Envelope
from contracts.ids import event_id
from marketdata.sources import ListSource
from marketdata.types import Tick


class EnvelopeSource:
    """In-memory iterator of pre-built envelopes for the engine kernel."""

    def __init__(self, envelopes: list[Envelope]) -> None:
        self.envelopes = envelopes
        self._iter: Iterator[Envelope] | None = None

    def __iter__(self) -> EnvelopeSource:
        self._iter = iter(self.envelopes)
        return self

    def __next__(self) -> Envelope:
        if self._iter is None:
            raise StopIteration
        return next(self._iter)

    def ack(self, envelope: Envelope) -> None:
        """No-op: list is already in memory."""


def envelopes_from_list_source(
    source: ListSource,
    *,
    stream: str = "md:list",
    src: str = "marketdata",
) -> list[Envelope]:
    """Convert V2-03 ``ListSource`` ticks into kernel envelopes.

    CLOCK heartbeats are skipped: ``EventType`` has no CLOCK member, and the
    kernel publishes every envelope onto the bus.
    """
    out: list[Envelope] = []
    for index, event in enumerate(source.events()):
        if event.event_type != "TICK":
            continue
        tick = event.payload
        if not isinstance(tick, Tick):
            continue
        ts = event.available_ts.isoformat()
        payload: dict[str, Any] = {
            "instrument_id": tick.instrument_id,
            "ltp": tick.ltp,
            "ltq": tick.ltq,
            "volume": tick.volume,
            "oi": tick.oi,
            "exchange_ts": tick.exchange_ts,
        }
        out.append(
            Envelope(
                v=2,
                event_type="MARKET_TICK",
                event_id=event_id("engine", f"list-{index}", 0),
                stream=stream,
                source=src,
                event_ts=tick.exchange_ts,
                available_ts=ts,
                timestamp=ts,
                account_id=None,
                correlation_id=None,
                causation_id=None,
                payload=payload,
            )
        )
    return out

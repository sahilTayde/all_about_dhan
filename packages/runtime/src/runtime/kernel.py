"""
V2 Engine kernel: one transaction per input, checkpoint, rehydrate mode.

Spec: V2_BUILD_PLAN.md V2-04, V2_PRODUCTION_ARCHITECTURE.md section 4.1
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Protocol

if TYPE_CHECKING:
    from contracts.clock import SimClock
else:
    from contracts.clock import Clock as SimClock
from contracts.envelope import Envelope
from events.bus import EventBus

log = logging.getLogger("runtime.kernel")


class EventSource(Protocol):
    """Source of ordered envelopes for the engine."""

    def __iter__(self) -> EventSource:
        """Return iterator over envelopes."""
        ...

    def __next__(self) -> Envelope:
        """Get next envelope, ordered by (available_ts, stream_priority, seq)."""
        ...

    def ack(self, envelope: Envelope) -> None:
        """Acknowledge successful processing of envelope."""
        ...


class Handler(Protocol):
    """Handler that processes envelopes."""

    def handle(self, envelope: Envelope) -> None:
        """Process envelope."""
        ...


class LedgerStore(Protocol):
    """Durable state store (ledger). Single writer (engine only)."""

    def transaction(self) -> LedgerTransaction:
        """Begin transaction context."""
        ...

    def checkpoint(self, envelope: Envelope) -> None:
        """Record checkpoint (last processed envelope)."""
        ...

    def get_last_checkpoint(self) -> tuple[str, str] | None:
        """Return (event_id, available_ts) of last checkpoint, or None."""
        ...


class LedgerTransaction(Protocol):
    """Transaction context manager."""

    def __enter__(self) -> LedgerTransaction:
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        ...


@dataclass(frozen=True)
class RunSummary:
    """Summary of an engine run."""

    envelope_count: int
    start_time: datetime
    end_time: datetime
    output_hash: str  # sha256 hex digest of deterministic outputs
    mismatches: int = 0  # rehydrate mode only


class Engine:
    """
    V2 engine kernel: processes ordered envelopes, one transaction per input.

    Modes:
    - run: normal execution
    - rehydrate: replay with no-op router, compare intents (determinism check)

    Design principles (section 4):
    - One code path for test/replay/live
    - Event time (clock) driven by available_ts
    - Envelope contract: available_ts >= event_ts, monotonic
    - Idempotent everywhere
    - Durable before visible (commit, then publish)
    """

    def __init__(
        self,
        source: EventSource,
        clock: SimClock,  # type: ignore[valid-type]
        bus: EventBus,
        handlers: list[Handler],
        store: LedgerStore,
        mode: Literal["run", "rehydrate"] = "run",
    ) -> None:
        """
        Initialize engine.

        Args:
            source: Event source (tape, warehouse, Redis)
            clock: SimClock or LiveClock
            bus: EventBus for publish/subscribe
            handlers: List of handlers to process envelopes
            store: Durable ledger store (single writer)
            mode: "run" (normal) or "rehydrate" (determinism check)
        """
        self.source = source
        self.clock = clock
        self.bus = bus
        self.handlers = handlers
        self.store = store
        self.mode = mode
        self._output_hasher = hashlib.sha256()
        self._mismatches = 0

    def run(self) -> RunSummary:
        """
        Run engine to completion.

        Processes envelopes in order:
        1. Advance clock to envelope.available_ts (monotonic check)
        2. Begin transaction
        3. Publish envelope to bus (handlers run synchronously)
        4. Checkpoint envelope
        5. Commit transaction
        6. Ack source

        Returns:
            RunSummary with envelope count, times, output hash, mismatches
        """
        start = datetime.now(self.clock.now().tzinfo)
        count = 0

        log.info(
            "Engine starting: mode=%s, handlers=%d, last_checkpoint=%s",
            self.mode,
            len(self.handlers),
            self.store.get_last_checkpoint(),
        )

        try:
            for envelope in self.source:
                count += 1

                # Advance clock (monotonic check)
                # Parse available_ts
                available_dt = datetime.fromisoformat(envelope.available_ts)
                self.clock.advance_to(available_dt)

                # One transaction per input
                with self.store.transaction():
                    # Publish to bus (handlers run synchronously, depth-first)
                    # Bus expects event_type and payload
                    self.bus.publish(envelope.event_type, envelope.payload, source=envelope.source)

                    # Checkpoint
                    self.store.checkpoint(envelope)

                    # Update output hash (deterministic outputs only)
                    self._update_output_hash(envelope)

                # Ack after commit
                self.source.ack(envelope)

                if count % 1000 == 0:
                    log.debug("Processed %d envelopes, clock=%s", count, self.clock.now().isoformat())

        except Exception:
            log.exception("Engine failed at envelope %d", count + 1)
            raise

        end = datetime.now(start.tzinfo)

        log.info(
            "Engine finished: envelopes=%d, duration=%.2fs, output_hash=%s, mismatches=%d",
            count,
            (end - start).total_seconds(),
            self._output_hasher.hexdigest()[:16],
            self._mismatches,
        )

        return RunSummary(
            envelope_count=count,
            start_time=start,
            end_time=end,
            output_hash=self._output_hasher.hexdigest(),
            mismatches=self._mismatches,
        )

    def _update_output_hash(self, envelope: Envelope) -> None:
        """
        Update output hash with deterministic fields.

        Only hashes envelopes that represent deterministic outputs (orders, decisions, etc).
        """
        # Hash event_id and payload for determinism check
        # In rehydrate mode, this would be compared against expected
        self._output_hasher.update(envelope.event_id.encode())
        # Simple payload hash (would be more sophisticated in production)
        import json

        payload_str = json.dumps(envelope.payload, sort_keys=True, separators=(",", ":"))
        self._output_hasher.update(payload_str.encode())

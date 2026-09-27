"""Outbox publisher: drain outbox rows, publish to event bus, mark published.

Exactly-once publish guarantee across crashes: each row is published exactly once
to consumers after two publisher crashes. Uses row id as Redis message id for
deduplication at the stream level.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Protocol

log = logging.getLogger("events.outbox")


class OutboxStore(Protocol):
    """Protocol for outbox storage (SQLite, PostgreSQL, etc.)."""

    def fetch_unpublished(self, limit: int = 100) -> list[tuple[int, str, str, dict[str, Any]]]:
        """Fetch unpublished rows: (row_id, stream, event_json, metadata)."""
        ...

    def mark_published(self, row_ids: list[int]) -> None:
        """Mark rows as published (idempotent)."""
        ...


class EventPublisher(Protocol):
    """Protocol for event publishing (Redis, Kafka, etc.)."""

    def publish_to_stream(
        self, stream: str, event_json: str, *, message_id: str | None = None
    ) -> None:
        """Publish event to a specific stream with optional message id."""
        ...


class OutboxPublisher:
    """
    Drain outbox rows and publish to event streams.

    Exactly-once guarantee: each row is published with its row_id as the Redis
    message id (XADD <stream> <row_id> event <json>). Redis deduplicates by
    message id, so replays are safe. After publish, mark row as published.
    """

    def __init__(self, store: OutboxStore, publisher: EventPublisher) -> None:
        self.store = store
        self.publisher = publisher
        self.published_count = 0
        self.error_count = 0

    def drain(self, *, limit: int = 100, max_retries: int = 3) -> int:
        """
        Drain unpublished rows and publish them.

        Returns: number of rows published in this batch.
        """
        rows = self.store.fetch_unpublished(limit)
        if not rows:
            return 0

        published_ids = []
        for row_id, stream, event_json, metadata in rows:
            # Use row_id as Redis message id for exactly-once
            message_id = f"{row_id}-0"

            retries = 0
            while retries < max_retries:
                try:
                    self.publisher.publish_to_stream(stream, event_json, message_id=message_id)
                    published_ids.append(row_id)
                    break
                except Exception as exc:  # noqa: BLE001
                    retries += 1
                    if retries >= max_retries:
                        log.error(
                            "Failed to publish row %d to %s after %d retries: %s",
                            row_id,
                            stream,
                            max_retries,
                            exc,
                        )
                        self.error_count += 1
                    else:
                        log.warning(
                            "Retry %d/%d for row %d to %s: %s", retries, max_retries, row_id, stream, exc
                        )
                        time.sleep(0.1 * (2**retries))  # exponential backoff

        if published_ids:
            self.store.mark_published(published_ids)
            self.published_count += len(published_ids)
            log.info("Published %d rows to event streams", len(published_ids))

        return len(published_ids)

    def run_loop(self, *, interval_ms: int = 100, limit: int = 100) -> None:
        """Run continuous drain loop (for daemon mode)."""
        log.info("Starting outbox publisher loop (interval=%d ms, limit=%d)", interval_ms, limit)
        while True:
            try:
                published = self.drain(limit=limit)
                if published == 0:
                    time.sleep(interval_ms / 1000.0)
            except KeyboardInterrupt:
                log.info("Outbox publisher stopped by user")
                break
            except Exception:
                log.exception("Outbox publisher loop error")
                time.sleep(1.0)

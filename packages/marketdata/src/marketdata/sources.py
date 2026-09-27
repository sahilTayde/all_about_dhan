"""Event sources: ListSource, TapeSource, RecorderTapeSource.

CLOCK heartbeats are synthesized every 5 s when a SimClock is provided.
JSONL readers skip bad lines (truncated, non-JSON, wrong schema) and keep
loading the lines before and after (REG-06a, REG-08a).
"""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol, TextIO

from marketdata.types import SimClock, Tick, bucket_start, parse_ts

logger = logging.getLogger(__name__)

_CLOCK_INTERVAL = timedelta(seconds=5)


@dataclass(frozen=True)
class SourceEvent:
    event_type: str  # "TICK" | "CLOCK"
    payload: Any
    available_ts: datetime


class EventSource(Protocol):
    def events(self) -> Iterator[SourceEvent]: ...


def _tick_from_obj(obj: dict[str, Any]) -> Tick:
    """Accept a flat tick, a V2 envelope (data/tape/v2 depth_quotes), or a recorder row."""
    payload = obj.get("payload")
    row: dict[str, Any] = payload if isinstance(payload, dict) else obj
    instrument_id = row.get("instrument_id")
    if not isinstance(instrument_id, str) or not instrument_id:
        raise ValueError("missing instrument_id")
    exchange_ts = row.get("exchange_ts") or row.get("timestamp") or obj.get("event_ts") or obj.get("timestamp")
    if not isinstance(exchange_ts, str) or not exchange_ts:
        raise ValueError("missing exchange_ts")
    return Tick(
        instrument_id=instrument_id,
        ltp=_opt_float(row.get("ltp")),
        ltq=_opt_int(row.get("ltq")),
        volume=_opt_int(row.get("volume")),
        oi=_opt_int(row.get("oi")),
        exchange_ts=exchange_ts,
    )


def _opt_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _opt_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _iter_clocks(
    last_clock: datetime | None,
    event_ts: datetime,
    clock: SimClock | None,
) -> tuple[datetime | None, list[SourceEvent]]:
    if clock is None:
        return last_clock, []
    clock.advance_to(event_ts)
    out: list[SourceEvent] = []
    cursor = last_clock if last_clock is not None else bucket_start(event_ts)
    while cursor + _CLOCK_INTERVAL <= event_ts:
        cursor += _CLOCK_INTERVAL
        out.append(SourceEvent(event_type="CLOCK", payload={"ts": cursor.isoformat()}, available_ts=cursor))
    return cursor, out


class ListSource:
    """Yield TICK events from an in-memory list, optionally with CLOCK heartbeats."""

    def __init__(self, ticks: list[Tick], clock: SimClock | None = None) -> None:
        self._ticks = ticks
        self._clock = clock

    def events(self) -> Iterator[SourceEvent]:
        if not self._ticks:
            return
        last_clock: datetime | None = None
        for tick in self._ticks:
            if not tick.exchange_ts:
                continue
            event_ts = parse_ts(tick.exchange_ts)
            last_clock, clocks = _iter_clocks(last_clock, event_ts, self._clock)
            yield from clocks
            yield SourceEvent(event_type="TICK", payload=tick, available_ts=event_ts)
        if self._clock is not None and last_clock is not None:
            # Drain two extra minutes so the last 1m bar can finalize on CLOCK.
            final_ts = parse_ts(self._ticks[-1].exchange_ts) + timedelta(minutes=2)
            last_clock, clocks = _iter_clocks(last_clock, final_ts, self._clock)
            yield from clocks


class _JsonlSource:
    """Shared per-line guarded JSONL reader."""

    def __init__(self, path: Path, clock: SimClock | None = None, record_errors: bool = True) -> None:
        self._path = path
        self._clock = clock
        self._record_errors = record_errors
        self._parse_errors: list[dict[str, Any]] = []

    @property
    def parse_errors(self) -> list[dict[str, Any]]:
        return self._parse_errors

    def events(self) -> Iterator[SourceEvent]:
        last_clock: datetime | None = None
        for tick, event_ts in self._read_ticks():
            last_clock, clocks = _iter_clocks(last_clock, event_ts, self._clock)
            yield from clocks
            yield SourceEvent(event_type="TICK", payload=tick, available_ts=event_ts)

    def _open(self) -> TextIO:
        if self._path.suffix == ".gz" or self._path.name.endswith(".jsonl.gz"):
            return gzip.open(self._path, "rt", encoding="utf-8")
        return self._path.open(encoding="utf-8")

    def _read_ticks(self) -> Iterator[tuple[Tick, datetime]]:
        try:
            with self._open() as handle:
                for line_no, raw in enumerate(handle, start=1):
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if not isinstance(obj, dict):
                            raise ValueError("row is not a JSON object")
                        tick = _tick_from_obj(obj)
                        yield tick, parse_ts(tick.exchange_ts)
                    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
                        if self._record_errors:
                            self._parse_errors.append(
                                {
                                    "path": str(self._path),
                                    "line_no": line_no,
                                    "error": str(exc),
                                    "line": line[:100],
                                }
                            )
                            logger.warning("Skipped bad line in %s:%d: %s", self._path, line_no, exc)
        except (OSError, EOFError) as exc:
            if self._record_errors:
                logger.error("Error reading %s: %s", self._path, exc)


class TapeSource(_JsonlSource):
    """Read ``data/tape/v2/YYYY-MM-DD/*.jsonl`` (envelope v2 or flat ticks)."""


class RecorderTapeSource(_JsonlSource):
    """Read a recorder-shaped JSONL (depth_quotes / recon rows). Same guarded parser."""

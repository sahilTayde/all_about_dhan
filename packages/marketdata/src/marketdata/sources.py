"""Event sources: ListSource, TapeSource, RecorderTapeSource."""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from contracts.clock import IST, SimClock
from contracts.payloads import Tick

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceEvent:
    """Event from a source with its available timestamp."""

    event_type: str  # "TICK" | "CLOCK"
    payload: Any
    available_ts: datetime


class EventSource(Protocol):
    """Protocol for event sources."""

    def events(self) -> Iterator[SourceEvent]:
        """Yield events with their available timestamps."""
        ...


class ListSource:
    """Source that yields events from a list."""

    def __init__(self, ticks: list[Tick], clock: SimClock | None = None):
        """
        Initialize from tick list.

        Args:
            ticks: list of ticks (must be sorted by exchange_ts)
            clock: optional clock to advance (if None, no CLOCK events emitted)
        """
        self._ticks = ticks
        self._clock = clock

    def events(self) -> Iterator[SourceEvent]:
        """
        Yield TICK events with CLOCK heartbeats.

        available_ts is set to exchange_ts for ticks.
        CLOCK events are synthesized every 5s.
        """
        if not self._ticks:
            return

        last_clock: datetime | None = None
        clock_interval = timedelta(seconds=5)

        for tick in self._ticks:
            if tick.exchange_ts is None:
                continue

            event_ts = self._parse_ts(tick.exchange_ts)

            # Advance clock if we have one
            if self._clock is not None:
                self._clock.advance_to(event_ts)

            # Synthesize CLOCK heartbeats
            if self._clock is not None:
                if last_clock is None:
                    last_clock = self._bucket_start(event_ts)

                while last_clock + clock_interval <= event_ts:
                    last_clock += clock_interval
                    yield SourceEvent(
                        event_type="CLOCK",
                        payload={"ts": last_clock.isoformat()},
                        available_ts=last_clock,
                    )

            # Yield tick
            yield SourceEvent(
                event_type="TICK",
                payload=tick,
                available_ts=event_ts,
            )

        # Final clock event if needed
        if self._clock is not None and last_clock is not None:
            final_ts = self._parse_ts(self._ticks[-1].exchange_ts)
            final_bucket = self._bucket_start(final_ts) + timedelta(minutes=2)
            while last_clock + clock_interval <= final_bucket:
                last_clock += clock_interval
                yield SourceEvent(
                    event_type="CLOCK",
                    payload={"ts": last_clock.isoformat()},
                    available_ts=last_clock,
                )

    def _bucket_start(self, ts: datetime) -> datetime:
        """Compute minute bucket start."""
        return ts.replace(second=0, microsecond=0)

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse ISO-8601 timestamp."""
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt


class TapeSource:
    """
    Source that reads from tape files (data/tape/v2/YYYY-MM-DD/*.jsonl).

    Per-line guarded parsing: bad lines are skipped and logged (REG-06a, REG-08a).
    """

    def __init__(
        self,
        tape_path: Path,
        clock: SimClock | None = None,
        record_errors: bool = True,
    ):
        """
        Initialize from tape file.

        Args:
            tape_path: path to JSONL tape file (may be gzipped)
            clock: optional clock to advance
            record_errors: if True, log parse errors
        """
        self._tape_path = tape_path
        self._clock = clock
        self._record_errors = record_errors
        self._parse_errors: list[dict[str, Any]] = []

    def events(self) -> Iterator[SourceEvent]:
        """
        Yield events from tape with CLOCK heartbeats.

        Bad lines are skipped and logged. Lines before and after still load (REG-06a).
        """
        last_clock: datetime | None = None
        clock_interval = timedelta(seconds=5)

        for tick, event_ts in self._read_ticks():
            # Advance clock
            if self._clock is not None:
                self._clock.advance_to(event_ts)

            # Synthesize CLOCK heartbeats
            if self._clock is not None:
                if last_clock is None:
                    last_clock = self._bucket_start(event_ts)

                while last_clock + clock_interval <= event_ts:
                    last_clock += clock_interval
                    yield SourceEvent(
                        event_type="CLOCK",
                        payload={"ts": last_clock.isoformat()},
                        available_ts=last_clock,
                    )

            # Yield tick
            yield SourceEvent(
                event_type="TICK",
                payload=tick,
                available_ts=event_ts,
            )

    def _read_ticks(self) -> Iterator[tuple[Tick, datetime]]:
        """Read and parse ticks from file, skipping bad lines."""
        open_fn = gzip.open if self._tape_path.suffix == ".gz" else open

        try:
            with open_fn(self._tape_path, "rt", encoding="utf-8") as f:
                line_no = 0
                for line in f:
                    line_no += 1
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                        tick = self._parse_tick(obj)
                        if tick.exchange_ts is None:
                            continue
                        event_ts = self._parse_ts(tick.exchange_ts)
                        yield tick, event_ts
                    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                        # Skip bad line (REG-06a, REG-08a)
                        if self._record_errors:
                            error = {
                                "path": str(self._tape_path),
                                "line_no": line_no,
                                "error": str(e),
                                "line": line[:100],
                            }
                            self._parse_errors.append(error)
                            logger.warning(
                                "Skipped bad line in %s:%d: %s", self._tape_path, line_no, e
                            )
                        continue
        except (OSError, EOFError) as e:
            # File errors: log and continue (REG-08a)
            if self._record_errors:
                logger.error("Error reading tape %s: %s", self._tape_path, e)

    def _parse_tick(self, obj: dict[str, Any]) -> Tick:
        """Parse tick from JSON object."""
        return Tick(
            instrument_id=obj["instrument_id"],
            ltp=obj.get("ltp"),
            ltq=obj.get("ltq"),
            volume=obj.get("volume"),
            oi=obj.get("oi"),
            exchange_ts=obj["exchange_ts"],
        )

    def _bucket_start(self, ts: datetime) -> datetime:
        """Compute minute bucket start."""
        return ts.replace(second=0, microsecond=0)

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse ISO-8601 timestamp."""
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt

    @property
    def parse_errors(self) -> list[dict[str, Any]]:
        """Return parse errors encountered."""
        return self._parse_errors


class RecorderTapeSource:
    """
    Source that reads from recorder files (data/recon/*/YYYYMMDD.jsonl).

    This is for the existing PR-001 recorder format (depth_quotes rows).
    Per-line guarded parsing (REG-06a, REG-08a).
    """

    def __init__(
        self,
        recorder_path: Path,
        clock: SimClock | None = None,
        record_errors: bool = True,
    ):
        """
        Initialize from recorder file.

        Args:
            recorder_path: path to recorder JSONL file
            clock: optional clock to advance
            record_errors: if True, log parse errors
        """
        self._recorder_path = recorder_path
        self._clock = clock
        self._record_errors = record_errors
        self._parse_errors: list[dict[str, Any]] = []

    def events(self) -> Iterator[SourceEvent]:
        """
        Yield events from recorder with CLOCK heartbeats.

        Bad lines are skipped and logged (REG-06a, REG-08a).
        """
        last_clock: datetime | None = None
        clock_interval = timedelta(seconds=5)

        for tick, event_ts in self._read_ticks():
            # Advance clock
            if self._clock is not None:
                self._clock.advance_to(event_ts)

            # Synthesize CLOCK heartbeats
            if self._clock is not None:
                if last_clock is None:
                    last_clock = self._bucket_start(event_ts)

                while last_clock + clock_interval <= event_ts:
                    last_clock += clock_interval
                    yield SourceEvent(
                        event_type="CLOCK",
                        payload={"ts": last_clock.isoformat()},
                        available_ts=last_clock,
                    )

            # Yield tick
            yield SourceEvent(
                event_type="TICK",
                payload=tick,
                available_ts=event_ts,
            )

    def _read_ticks(self) -> Iterator[tuple[Tick, datetime]]:
        """Read and parse ticks from recorder file, skipping bad lines."""
        try:
            with open(self._recorder_path, encoding="utf-8") as f:
                line_no = 0
                for line in f:
                    line_no += 1
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                        # Recorder format: depth_quotes row
                        tick = self._parse_recorder_tick(obj)
                        if tick.exchange_ts is None:
                            continue
                        event_ts = self._parse_ts(tick.exchange_ts)
                        yield tick, event_ts
                    except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
                        # Skip bad line (REG-06a, REG-08a)
                        if self._record_errors:
                            error = {
                                "path": str(self._recorder_path),
                                "line_no": line_no,
                                "error": str(e),
                                "line": line[:100],
                            }
                            self._parse_errors.append(error)
                            logger.warning(
                                "Skipped bad line in %s:%d: %s", self._recorder_path, line_no, e
                            )
                        continue
        except OSError as e:
            if self._record_errors:
                logger.error("Error reading recorder file %s: %s", self._recorder_path, e)

    def _parse_recorder_tick(self, obj: dict[str, Any]) -> Tick:
        """
        Parse tick from recorder depth_quotes row.

        Recorder format has: instrument_id, ltp, timestamp, etc.
        """
        exchange_ts = obj.get("timestamp") or obj.get("exchange_ts", "")
        if not isinstance(exchange_ts, str):
            exchange_ts = str(exchange_ts) if exchange_ts else ""
        return Tick(
            instrument_id=obj["instrument_id"],
            ltp=obj.get("ltp"),
            ltq=obj.get("ltq"),
            volume=obj.get("volume"),
            oi=obj.get("oi"),
            exchange_ts=exchange_ts,
        )

    def _bucket_start(self, ts: datetime) -> datetime:
        """Compute minute bucket start."""
        return ts.replace(second=0, microsecond=0)

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse ISO-8601 timestamp."""
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        return dt

    @property
    def parse_errors(self) -> list[dict[str, Any]]:
        """Return parse errors encountered."""
        return self._parse_errors

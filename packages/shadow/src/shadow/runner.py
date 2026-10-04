"""Wire recorded / live-tailed marketdata into V2 decision logging.

Uses the existing kernel + TapeSource. Does not construct a broker.
Default live/follow path is HOLD (fail closed, no invented edge).
``demo_fills`` is dry-run only and writes isolated SHADOW_OPEN / SHADOW_FLAT marks.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from contracts.clock import IST, SimClock
from contracts.envelope import Envelope
from events.bus import MemoryBus
from events.schema import Event
from marketdata.sources import ListSource, TapeSource
from marketdata.types import Tick
from runtime.kernel import Engine, RunSummary
from runtime.sources import EnvelopeSource, envelopes_from_list_source
from runtime.store import InMemoryLedgerStore

from shadow.journal import SCHEMA, ShadowJournal
from shadow.safety import (
    ACCOUNT_ID,
    ShadowClosed,
    ShadowSafetyError,
    assert_no_live_modules,
    assert_paper_only,
    closed,
)

SleepFn = Callable[[float], None]


def ist_day(now: datetime | None = None) -> str:
    stamp = now if now is not None else datetime.now(IST)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=IST)
    return stamp.astimezone(IST).date().isoformat()


def tape_paths(tape: Path) -> list[Path]:
    if tape.is_file():
        return [tape]
    if not tape.is_dir():
        return []
    out = sorted(p for p in tape.glob("*.jsonl") if p.is_file())
    out.extend(sorted(p for p in tape.glob("*.jsonl.gz") if p.is_file()))
    return out


def ticks_from_tape(path: Path) -> list[Tick]:
    ticks: list[Tick] = []
    for event in TapeSource(path).events():
        if event.event_type == "TICK" and isinstance(event.payload, Tick):
            ticks.append(event.payload)
    return ticks


def envelopes_from_ticks(ticks: Sequence[Tick]) -> list[Envelope]:
    return envelopes_from_list_source(ListSource(list(ticks)), stream="md:shadow", src="shadow")


def _underlying(instrument_id: str) -> str:
    raw = instrument_id.upper()
    for name in ("NIFTY", "BANKNIFTY", "SENSEX"):
        if name in raw:
            return name
    return raw.split(":")[0] if raw else "UNKNOWN"


@dataclass
class PaperLot:
    instrument_id: str
    qty: int
    entry: float
    opened_ts: str


@dataclass
class ShadowBook:
    """In-process paper marks. Never a broker. Never the legacy sqlite book."""

    lots: list[PaperLot] = field(default_factory=list)
    realized_pts: float = 0.0

    def open_lot(self, instrument_id: str, qty: int, price: float, ts: str) -> PaperLot:
        lot = PaperLot(instrument_id=instrument_id, qty=qty, entry=price, opened_ts=ts)
        self.lots.append(lot)
        return lot

    def flatten(self, price: float) -> list[tuple[PaperLot, float]]:
        closed_lots: list[tuple[PaperLot, float]] = []
        for lot in self.lots:
            closed_lots.append((lot, (price - lot.entry) * lot.qty))
        self.realized_pts += sum(pnl for _lot, pnl in closed_lots)
        self.lots = []
        return closed_lots


@dataclass
class ShadowRun:
    journal: ShadowJournal
    day: str
    mode: str
    demo_fills: bool = False
    book: ShadowBook = field(default_factory=ShadowBook)
    decisions: int = 0
    holds: int = 0
    opens: int = 0
    flats: int = 0
    closed_reason: str | None = None
    output_hash: str = ""
    envelopes: int = 0

    def on_tick(self, event: Event) -> None:
        payload = event.payload
        instrument_id = str(payload.get("instrument_id") or "")
        raw_ltp = payload.get("ltp")
        ltp = float(raw_ltp) if raw_ltp is not None else None
        ts = str(payload.get("exchange_ts") or event.timestamp)
        underlying = _underlying(instrument_id)
        if self.demo_fills and ltp is not None and not self.book.lots and self.opens == 0:
            self.book.open_lot(instrument_id, 1, ltp, ts)
            self.journal.log_pnl(
                day=self.day,
                ts=ts,
                kind="SHADOW_OPEN",
                instrument_id=instrument_id,
                qty=1,
                price=ltp,
                realized=0.0,
                reason="DEMO_ONLY",
            )
            self.journal.log_decision(
                day=self.day,
                ts=ts,
                underlying=underlying,
                action="ENTER",
                side="CE",
                reason="DEMO_ONLY",
                ltp=ltp,
                instrument_id=instrument_id,
                extra={"demo": True},
            )
            self.opens += 1
            self.decisions += 1
            return
        self.journal.log_decision(
            day=self.day,
            ts=ts,
            underlying=underlying,
            action="HOLD",
            side="",
            reason="NO_SIGNAL_PLUGIN" if not self.demo_fills else "DEMO_HOLD",
            ltp=ltp,
            instrument_id=instrument_id,
        )
        self.holds += 1
        self.decisions += 1

    def flatten_open(self, ts: str, price: float | None, reason: str = "SHADOW_FLAT") -> None:
        if not self.book.lots:
            return
        mark = price if price is not None else self.book.lots[-1].entry
        for lot, pnl in self.book.flatten(mark):
            self.journal.log_pnl(
                day=self.day,
                ts=ts,
                kind="SHADOW_FLAT",
                instrument_id=lot.instrument_id,
                qty=lot.qty,
                price=mark,
                realized=pnl,
                reason=reason,
            )
            self.flats += 1


def run_envelopes(shadow: ShadowRun, envelopes: Sequence[Envelope]) -> RunSummary:
    assert_no_live_modules()
    if not envelopes:
        raise closed("FEED_DOWN")
    first = datetime.fromisoformat(envelopes[0].available_ts)
    if first.tzinfo is None:
        first = first.replace(tzinfo=IST)
    bus = MemoryBus(raise_errors=True)
    bus.subscribe(["MARKET_TICK"], shadow.on_tick)
    summary = Engine(
        EnvelopeSource(list(envelopes)),
        SimClock(first),
        bus,
        [],
        InMemoryLedgerStore(),
    ).run()
    shadow.output_hash = summary.output_hash
    shadow.envelopes += summary.envelope_count
    return summary


def load_tape_envelopes(tape: Path) -> list[Envelope]:
    ticks: list[Tick] = []
    for path in tape_paths(tape):
        ticks.extend(ticks_from_tape(path))
    ticks.sort(key=lambda tick: tick.exchange_ts or "")
    return envelopes_from_ticks(ticks)


def run_once(
    *,
    tape: Path,
    state_dir: Path,
    mode: str = "paper",
    day: str | None = None,
    demo_fills: bool = False,
) -> ShadowRun:
    assert_paper_only(mode)
    assert_no_live_modules()
    journal = ShadowJournal(state_dir)
    session = day or ist_day()
    shadow = ShadowRun(journal=journal, day=session, mode=mode, demo_fills=demo_fills)
    try:
        envelopes = load_tape_envelopes(tape)
        run_envelopes(shadow, envelopes)
        last = envelopes[-1]
        last_px = last.payload.get("ltp")
        shadow.flatten_open(
            last.available_ts,
            float(last_px) if last_px is not None else None,
            reason="DEMO_ONLY" if demo_fills else "SHADOW_FLAT",
        )
    except ShadowClosed as exc:
        shadow.closed_reason = exc.reason
    shadow.journal.write_status(
        session,
        datetime.now(IST),
        mode=mode,
        decisions=shadow.decisions,
        holds=shadow.holds,
        opens=shadow.opens,
        flats=shadow.flats,
        envelopes=shadow.envelopes,
        output_hash=shadow.output_hash,
        closed_reason=shadow.closed_reason,
        demo_fills=demo_fills,
        tape=str(tape),
    )
    return shadow


def follow_tape(
    *,
    tape: Path,
    state_dir: Path,
    stop_flag: Path,
    mode: str = "paper",
    day: str | None = None,
    poll_s: float = 1.0,
    sleep: SleepFn = time.sleep,
    max_idle_polls: int | None = None,
) -> ShadowRun:
    """Tail a recorder tape directory. Missing tape → fail closed, no invented ticks."""
    assert_paper_only(mode)
    assert_no_live_modules()
    if poll_s < 0:
        raise ShadowSafetyError("poll_s must be >= 0")
    journal = ShadowJournal(state_dir)
    session = day or ist_day()
    shadow = ShadowRun(journal=journal, day=session, mode=mode, demo_fills=False)
    seen = 0
    idle = 0
    while not stop_flag.is_file():
        try:
            envelopes = load_tape_envelopes(tape)
        except OSError:
            envelopes = []
        if len(envelopes) > seen:
            run_envelopes(shadow, envelopes[seen:])
            seen = len(envelopes)
            idle = 0
        else:
            if not envelopes:
                shadow.closed_reason = "FEED_DOWN"
            idle += 1
            if max_idle_polls is not None and idle >= max_idle_polls:
                break
        shadow.journal.write_status(
            session,
            datetime.now(IST),
            mode=mode,
            decisions=shadow.decisions,
            holds=shadow.holds,
            envelopes=shadow.envelopes,
            output_hash=shadow.output_hash,
            closed_reason=shadow.closed_reason,
            following=True,
            tape=str(tape),
        )
        if stop_flag.is_file():
            break
        sleep(poll_s)
    if shadow.book.lots:
        shadow.flatten_open(datetime.now(IST).isoformat(timespec="seconds"), None)
    return shadow


def compare_day(
    *,
    state_dir: Path,
    day: str,
    legacy_path: Path | None = None,
) -> dict[str, Any]:
    journal = ShadowJournal(state_dir)
    files = journal.files(day)
    decisions = list(journal.iter_jsonl(files.decisions))
    pnl_rows = list(journal.iter_jsonl(files.pnl))
    realized = sum(float(row.get("realized_pts") or 0) for row in pnl_rows if row.get("kind") == "SHADOW_FLAT")
    legacy_rows = 0
    legacy_note = "DATA_INSUFFICIENT"
    if legacy_path is not None and legacy_path.is_file():
        legacy_rows = sum(1 for _ in journal.iter_jsonl(legacy_path))
        legacy_note = "read-only; legacy owns the live paper book"
    body: dict[str, Any] = {
        "schema": f"{SCHEMA}-compare",
        "day": day,
        "account_id": ACCOUNT_ID,
        "orders": "REFUSED",
        "promote": False,
        "v2": {
            "decisions": len(decisions),
            "holds": sum(1 for row in decisions if row.get("action") == "HOLD"),
            "opens": sum(1 for row in pnl_rows if row.get("kind") == "SHADOW_OPEN"),
            "flats": sum(1 for row in pnl_rows if row.get("kind") == "SHADOW_FLAT"),
            "closed_pnl_pts": realized,
        },
        "legacy": {
            "path": str(legacy_path) if legacy_path is not None else None,
            "rows": legacy_rows,
            "note": legacy_note,
        },
    }
    journal.write_json(files.compare, body)
    return body


def write_fixture_tape(path: Path) -> Path:
    """Synthetic NIFTY prints for dry-run. No credentials. No live tape."""
    rows = [
        {
            "instrument_id": "NIFTY",
            "ltp": 22000.0,
            "ltq": 100,
            "volume": 100,
            "oi": 1000,
            "exchange_ts": "2026-10-04T10:00:00+05:30",
        },
        {
            "instrument_id": "NIFTY",
            "ltp": 22010.0,
            "ltq": 50,
            "volume": 150,
            "oi": 1000,
            "exchange_ts": "2026-10-04T10:00:05+05:30",
        },
        {
            "instrument_id": "NIFTY",
            "ltp": 22025.0,
            "ltq": 75,
            "volume": 225,
            "oi": 1000,
            "exchange_ts": "2026-10-04T10:00:10+05:30",
        },
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path

"""Founder picks which indices may get NEW paper fills today.

Dual-tape still records every index for replay. Boss / dealer / analysts
do not choose the book. An already-OPEN ticket is never flattened here.

Human manage of an OPEN paper fill (required TARGET + STOP, SET_LEVELS) lives
in desk_ml.paper_scalp.save_human_override — not a naked EXIT.

START/STOP is an append-only, timestamped log (``founder_commands.jsonl``). The live loop
re-replays the whole day every cycle, so a command applies to ticks at or after its own
timestamp and never to trades booked before it. ``founder_trade_underlyings.json`` stays as the
current view for the UI. Without a log (older installs, offline replay roots that only carry the
JSON file) the JSON view is read exactly as before.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional
from zoneinfo import ZoneInfo

from desk_ml.persist import repo_root
from desk_ml.reliability import append_line, atomic_write_json, read_jsonl

KNOWN = ("NIFTY", "BANKNIFTY", "SENSEX")
# Default STOP TRADE on every index. Founder START is the only way NEW fills begin.
DEFAULT: tuple[str, ...] = ()
FILE_NAME = "founder_trade_underlyings.json"
LOG_NAME = "founder_commands.jsonl"
STOP_REASON = "FOUNDER_STOP_TRADING_ON_INDEX"
UNREADABLE_REASON = "FOUNDER_STATE_UNREADABLE"
START_ACTION = "START"
STOP_ACTION = "STOP"
BASELINE_SOURCE = "baseline"  # state carried over from the JSON file when the log was created
IST = ZoneInfo("Asia/Kolkata")


class FounderStateError(RuntimeError):
    """The founder state cannot be trusted. Callers must block new fills (fail closed)."""


def session_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / "data" / "recon" / FILE_NAME


def log_path(root: Path) -> Path:
    return Path(root) / "data" / "recon" / LOG_NAME


def _clean(names: Iterable[Any]) -> list[str]:
    out: list[str] = []
    for raw in names or []:
        u = str(raw or "").strip().upper().replace(" ", "")
        if u in KNOWN and u not in out:
            out.append(u)
    return out


def load_founder_book(root: Optional[Path] = None) -> dict[str, Any]:
    path = session_path(root)
    if not path.is_file():
        return _payload(list(DEFAULT), source="default")
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _payload(list(DEFAULT), source="unreadable", ok=False)
    if not isinstance(blob, dict) or not isinstance(blob.get("trade_underlyings", []), (list, tuple)):
        return _payload(list(DEFAULT), source="unreadable", ok=False)
    names = _clean(blob.get("trade_underlyings") if "trade_underlyings" in blob else DEFAULT)
    return _payload(
        names,
        source="file",
        as_of_ist=blob.get("as_of_ist"),
        note=blob.get("note"),
    )


def _index_status(names: list[str]) -> dict[str, str]:
    started = set(names)
    return {n: (START_ACTION if n in started else STOP_ACTION) for n in KNOWN}


def _payload(
    names: list[str],
    *,
    source: str,
    ok: bool = True,
    as_of_ist: Any = None,
    note: Any = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "trade_underlyings": names,
        "stopped_underlyings": [n for n in KNOWN if n not in names],
        "known_underlyings": list(KNOWN),
        "index_status": _index_status(names),
        "apply_new_fills_only": True,
        "tape_records_all": True,
        "default_action": STOP_ACTION,
        "as_of_ist": as_of_ist,
        "source": source,
        "orders": "REFUSED",
        "promote": False,
        "note": note
        or "Founder START/STOP per index. Default STOP TRADE. Dual-tape still records all.",
    }


# ------------------------------------------------------------------ command log


def read_commands(root: Path) -> Optional[list[dict[str, Any]]]:
    """Validated log rows, or None when there is no log. Raises FounderStateError if corrupt."""
    try:
        rows = read_jsonl(log_path(root))
    except (OSError, ValueError) as exc:
        raise FounderStateError(f"founder command log unreadable: {exc}") from exc
    if rows is None:
        return None
    out: list[dict[str, Any]] = []
    for n, row in enumerate(rows):
        und = str(row.get("underlying") or "").upper()
        act = str(row.get("action") or "").upper()
        try:
            ts = float(row["ts"])
        except (KeyError, TypeError, ValueError):
            raise FounderStateError(f"founder command log row {n + 1} has no timestamp") from None
        if und not in KNOWN or act not in {START_ACTION, STOP_ACTION} or ts != ts:
            raise FounderStateError(f"founder command log row {n + 1} is not a START/STOP for a known index")
        out.append({**row, "underlying": und, "action": act, "ts": ts})
    return out


def _latest_state(rows: list[dict[str, Any]], *, until: Optional[float] = None) -> set[str]:
    started: set[str] = set()
    for row in sorted(rows, key=lambda r: r["ts"]):
        if until is not None and row["ts"] > until:
            break
        if row["action"] == START_ACTION:
            started.add(row["underlying"])
        else:
            started.discard(row["underlying"])
    return started


def started_at(rows: list[dict[str, Any]], ts: float) -> set[str]:
    """Indices STARTed as of unix ``ts``.

    Sessions before the first real (non-baseline) command's IST date predate the log: they use
    the log's current state, which is what the JSON file said (today's behaviour for historical
    replays). From that date on a command applies to ticks at or after its own timestamp.
    """
    real = [r for r in rows if r.get("source") != BASELINE_SOURCE]
    if not real:
        return _latest_state(rows)
    first_day = datetime.fromtimestamp(min(r["ts"] for r in real), IST).date()
    if datetime.fromtimestamp(float(ts), IST).date() < first_day:
        return _latest_state(rows)
    return _latest_state(rows, until=float(ts))


def _now_ts() -> float:
    return datetime.now(IST).timestamp()


def _write_view(root: Optional[Path], names: list[str], ts: float) -> dict[str, Any]:
    payload = _payload(
        _clean(names),
        source="file",
        as_of_ist=datetime.fromtimestamp(ts, IST).isoformat(timespec="seconds"),
        note="Founder START/STOP for NEW paper fills only. Open tickets stay. Dual-tape records all.",
    )
    atomic_write_json(session_path(root), payload, indent=2)
    return payload


def _ensure_log(root: Path) -> list[dict[str, Any]]:
    """Existing rows, or a new log seeded with the JSON view's state at ts=0 (the baseline)."""
    rows = read_commands(root)
    if rows is not None:
        return rows
    book = load_founder_book(root)
    if not book.get("ok", True):
        raise FounderStateError("founder JSON view is unreadable; cannot seed the command log")
    seeded = []
    for und in book.get("trade_underlyings") or []:
        row = {"ts": 0.0, "underlying": und, "action": START_ACTION, "source": BASELINE_SOURCE}
        append_line(log_path(root), json.dumps(row))
        seeded.append(row)
    if not seeded:
        log_path(root).parent.mkdir(parents=True, exist_ok=True)
        log_path(root).touch()
    return seeded


def append_commands(root: Path, names: Iterable[Any], *, ts: float, source: str) -> list[dict[str, Any]]:
    """Append the START/STOP rows that move the current state to ``names``. Returns the new rows."""
    rows = _ensure_log(root)
    want = set(_clean(names))
    have = _latest_state(rows)
    new = []
    for und in KNOWN:
        if (und in want) != (und in have):
            row = {"ts": float(ts), "underlying": und, "action": START_ACTION if und in want else STOP_ACTION,
                   "session": datetime.fromtimestamp(float(ts), IST).date().isoformat(), "source": source}
            append_line(log_path(root), json.dumps(row))
            new.append(row)
    return new


def save_founder_book(
    names: Iterable[Any], *, root: Optional[Path] = None, ts: Optional[float] = None, source: str = "api"
) -> dict[str, Any]:
    base = Path(root) if root is not None else repo_root()
    stamp = _now_ts() if ts is None else float(ts)
    _ensure_log(base)  # seed the baseline from the view as it was before this command
    # View first, then the log: a crash in between leaves a view the live loop ingests as an
    # edit (same intent, stamped a moment later), never a log the view silently reverts.
    payload = _write_view(base, _clean(names), stamp)
    append_commands(base, names, ts=stamp, source=source)
    return payload


def set_index_trade(
    underlying: Any, action: Any, *, root: Optional[Path] = None, ts: Optional[float] = None
) -> dict[str, Any]:
    """START or STOP NEW fills on one index. Other indices keep their state."""
    u = str(underlying or "").strip().upper().replace(" ", "")
    act = str(action or "").strip().upper()
    if act in {"START TRADE", "START_TRADE", "RESTART"}:
        act = START_ACTION
    if act in {"STOP TRADE", "STOP_TRADE"}:
        act = STOP_ACTION
    if u not in KNOWN:
        book = load_founder_book(root)
        book["ok"] = False
        book["error"] = "UNKNOWN_UNDERLYING"
        return book
    if act not in {START_ACTION, STOP_ACTION}:
        book = load_founder_book(root)
        book["ok"] = False
        book["error"] = "UNKNOWN_ACTION"
        return book
    base = Path(root) if root is not None else repo_root()
    names = sorted(_latest_state(_ensure_log(base)))
    if act == START_ACTION:
        if u not in names:
            names.append(u)
    else:
        names = [n for n in names if n != u]
    saved = save_founder_book(names, root=base, ts=ts)
    saved["last_underlying"] = u
    saved["last_action"] = act
    return saved


def ingest_view_edits(root: Path, *, ts: float) -> list[dict[str, Any]]:
    """Live loop only: a hand edit of the JSON view becomes log rows stamped when first seen.

    Creates the log (baseline = the JSON state) on the first live cycle after the upgrade.
    Raises FounderStateError when the JSON view is unreadable, so the caller blocks entries.
    """
    book = load_founder_book(root)
    if not book.get("ok", True):
        raise FounderStateError("founder JSON view is unreadable")
    had_log = log_path(root).exists()
    rows = _ensure_log(root)
    if not had_log or book.get("source") == "default":
        return []
    view = set(book.get("trade_underlyings") or [])
    if view == _latest_state(rows):
        return []
    return append_commands(root, view, ts=ts, source="json_edit")


def allows_new_fill(underlying: str, *, root: Optional[Path] = None) -> bool:
    book = load_founder_book(root)
    names = book.get("trade_underlyings") if "trade_underlyings" in book else list(DEFAULT)
    return str(underlying or "").upper() in set(names or [])


def new_fill_decision(underlying: str, *, root: Optional[Path] = None) -> dict[str, Any]:
    u = str(underlying or "").upper()
    allow = allows_new_fill(u, root=root)
    return {
        "allow": allow,
        "underlying": u,
        "reason": None if allow else STOP_REASON,
        "note": "Tape still records this index; founder stopped NEW paper fills only.",
    }


def fill_decision_at(underlying: str, *, root: Optional[Path], ts: float, rows: Any = None) -> dict[str, Any]:
    """The founder gate for one entry at tick ``ts``. Raises FounderStateError when untrustworthy.

    ``rows`` are the command rows the live cycle read for this cycle (``"unknown"`` = no trustworthy
    state). Otherwise they are read from ``root``. No data root is an error (never fall back to
    this checkout). Without a command log the legacy JSON path runs unchanged
    (``new_fill_decision`` → ``allows_new_fill``).
    """
    if rows == "unknown":
        raise FounderStateError("founder command log unreadable and no earlier good copy")
    if root is None:
        raise FounderStateError("no data root: founder state unknown")
    if rows is None:
        rows = read_commands(Path(root))
    if rows is None:
        book = load_founder_book(root)
        if not book.get("ok", True):
            raise FounderStateError("founder JSON view is unreadable")
        return new_fill_decision(underlying, root=root)
    u = str(underlying or "").upper()
    allow = u in started_at(rows, ts)
    return {
        "allow": allow,
        "underlying": u,
        "reason": None if allow else STOP_REASON,
        "note": "Founder command log as of this tick; earlier booked trades are never changed.",
    }

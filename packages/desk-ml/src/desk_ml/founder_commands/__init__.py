"""Founder command bus (roadmap step 14). PAPER only: nothing here talks to a broker.

``log`` stores commands durably; ``book`` says what they mean as of a tick. The API appends,
the engine reads the log at the start of every replay (every live-loop cycle).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Sequence, Union

from desk_ml.founder_commands.book import (
    CONFIRM_KINDS,
    EXIT_KINDS,
    KINDS,
    POSITION_KINDS,
    CommandBook,
    State,
    make_row,
    session_of,
    validate_args,
    validate_row,
)
from desk_ml.founder_commands.log import (
    anchor_first_seen,
    append_command,
    append_statuses,
    log_path,
    read_commands,
    read_statuses,
    write_account_view,
)

CommandsArg = Union[None, str, Path, Sequence[dict[str, Any]]]


def lots_cap(root: Path, engine_max: int) -> Optional[int]:
    """Largest lots override: the engine's max and the risk limits' ``max_lots_per_trade`` for the
    active mode (``root/config/risk_limits.yaml``). None when the limits cannot be read."""
    try:
        from risk_engine.engine import load_limits

        cfg = load_limits(Path(root) / "config" / "risk_limits.yaml")
        return min(int(engine_max), int(cfg["modes"][cfg["mode"]]["max_lots_per_trade"]))
    except Exception:
        return None


def load_book(
    root: Path, commands: CommandsArg = None, *, as_of: Optional[float] = None, record: bool = False,
    engine_max_lots: Optional[int] = None,
) -> Optional[CommandBook]:
    """The commands a replay applies. None when there are none (the engine then runs unchanged).

    ``commands``: None reads ``root``'s log (and spool); a path reads that file only (replay of a
    saved commands file); a list uses those rows. For ``root``'s log, a bad line blocks entries from
    when the live loop first saw it (``record`` stores first sights at ``as_of``, the tape time).
    ``engine_max_lots``: cap lots overrides at ``lots_cap`` (unknown limits: an override may only lower).
    """
    if isinstance(commands, (list, tuple)):
        rows, problems, seen, blocked_from, last_good = [], [], set(), None, 0.0
        for n, row in enumerate(commands, start=1):
            err = validate_row(row)
            if err:
                problems.append(f"row {n}: {err}")
                blocked_from = last_good if blocked_from is None else min(blocked_from, last_good)
                continue
            last_good = max(last_good, float(row["ts"]))
            if row["id"] not in seen:
                seen.add(row["id"])
                rows.append(row)
    else:
        res = read_commands(root, path=Path(commands) if commands is not None else None)
        rows, problems, blocked_from = res.rows, res.problems, res.blocked_from
        if commands is None and res.anchors:
            blocked_from = anchor_first_seen(root, res, as_of=as_of, record=record)
    book = CommandBook(rows, problems, blocked_from)
    if not book:
        return None
    if engine_max_lots is not None:
        book.lots_cap = lots_cap(root, engine_max_lots)
    return book


__all__ = [
    "CONFIRM_KINDS", "EXIT_KINDS", "KINDS", "POSITION_KINDS", "CommandBook", "State", "anchor_first_seen", "append_command",
    "append_statuses", "load_book", "log_path", "lots_cap", "make_row", "read_commands", "read_statuses", "session_of",
    "validate_args", "validate_row", "write_account_view",
]

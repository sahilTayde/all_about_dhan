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
    append_command,
    append_statuses,
    log_path,
    read_commands,
    read_statuses,
    write_account_view,
)

CommandsArg = Union[None, str, Path, Sequence[dict[str, Any]]]


def load_book(root: Path, commands: CommandsArg = None) -> Optional[CommandBook]:
    """The commands a replay applies. None when there are none (the engine then runs unchanged).

    ``commands``: None reads ``root``'s log (and spool); a path reads that file only (replay of a
    saved commands file); a list uses those rows.
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
    book = CommandBook(rows, problems, blocked_from)
    return book if book else None


__all__ = [
    "CONFIRM_KINDS", "EXIT_KINDS", "KINDS", "POSITION_KINDS", "CommandBook", "State", "append_command",
    "append_statuses", "load_book", "log_path", "make_row", "read_commands", "read_statuses", "session_of",
    "validate_args", "validate_row", "write_account_view",
]

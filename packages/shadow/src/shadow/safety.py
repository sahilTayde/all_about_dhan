"""Fail-closed paper-only gate for the V2 shadow launcher.

Never constructs a Dhan broker. Never writes the legacy paper book.
Live / limited-live / dhan modes raise. Missing tape blocks new entries.
"""

from __future__ import annotations

import sys
from pathlib import Path

ALLOWED_MODES = frozenset({"paper", "shadow", "replay"})
LIVE_MODES = frozenset({"live", "limited_live", "dhan"})
ACCOUNT_ID = "v2-shadow"
# Broker-ish names that mean "this is not an isolated paper log".
_LIVEISH_BROKER = frozenset({"dhan", "live", "limited_live"})
_FORBIDDEN_WRITE_BUCKETS = frozenset({"recon", "ledger", "desk_intel", "tape", "knowledge"})
# Live / legacy paper-book modules. dhan_client.execution may already be
# imported by the recorder stack; it still refuses orders. We refuse the
# modules that would share a book or construct a live broker.
_FORBIDDEN_IMPORT_PREFIXES = (
    "brokers.dhan",
    "desk.paper",
    "desk_ml.paper_scalp",
    "desk_ml.picker",
    "oms.router",
)


class ShadowSafetyError(ValueError):
    """Hard refuse: live path, shared book, or illegal mode."""


class ShadowClosed(RuntimeError):
    """Fail closed: no new shadow entries. Process may keep running."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def assert_paper_only(mode: str) -> str:
    """Refuse live / Dhan process modes. ``shadow`` here means log-only, not a broker."""
    cleaned = (mode or "").strip().lower()
    if cleaned in LIVE_MODES or cleaned in _LIVEISH_BROKER:
        raise ShadowSafetyError(f"V2 shadow fail-closed: mode {mode!r} is live and cannot start")
    if cleaned not in ALLOWED_MODES:
        raise ShadowSafetyError(f"V2 shadow fail-closed: mode {mode!r} is not paper/shadow/replay")
    return cleaned


def assert_no_live_modules() -> None:
    """Process must not have imported a live broker or the legacy paper engine."""
    loaded = set(sys.modules)
    for name in _FORBIDDEN_IMPORT_PREFIXES:
        if name in loaded or any(mod == name or mod.startswith(name + ".") for mod in loaded):
            raise ShadowSafetyError(f"V2 shadow fail-closed: {name} is loaded; no shared live path")


def _data_bucket(path: Path) -> tuple[str, ...]:
    parts = path.resolve().parts
    if "data" not in parts:
        return ()
    i = parts.index("data")
    return parts[i + 1 :]


def is_forbidden_write(path: Path) -> bool:
    """True when a write would touch the legacy book, ledger, tape, or shadow-v1 root."""
    rest = _data_bucket(path)
    if not rest:
        return False
    if rest[0] in _FORBIDDEN_WRITE_BUCKETS:
        return True
    # Legacy desk_ml rows live at data/shadow/YYYY-MM-DD.jsonl — not under v2/.
    return rest[0] == "shadow" and (len(rest) == 1 or rest[1] != "v2")


def assert_isolated_state(state_dir: Path) -> Path:
    """Shadow state must not share a write path with the legacy paper book."""
    resolved = state_dir.expanduser()
    if is_forbidden_write(resolved):
        raise ShadowSafetyError(
            f"V2 shadow fail-closed: state_dir {resolved} shares a write path with the live paper book"
        )
    rest = _data_bucket(resolved)
    if rest[:1] == ("shadow",) and rest[:2] != ("shadow", "v2"):
        raise ShadowSafetyError(f"V2 shadow fail-closed: use data/shadow/v2 (not legacy data/shadow): {resolved}")
    return resolved


def refuse_broker_name(name: str) -> None:
    """Router-style guard: a live-like broker name is never acceptable."""
    if (name or "").strip().lower() in _LIVEISH_BROKER | LIVE_MODES:
        raise ShadowSafetyError(f"V2 shadow fail-closed: broker {name!r} is not paper")


def closed(reason: str) -> ShadowClosed:
    """Build the fail-closed signal used when the tape is missing or the feed is down."""
    return ShadowClosed(reason)

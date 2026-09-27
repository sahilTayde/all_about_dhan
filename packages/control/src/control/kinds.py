"""Founder command kinds, validation, and standing state (PR #18 port + V2 extras)."""

from __future__ import annotations

import math
import os
import re
from bisect import bisect_right
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))

KINDS = (
    "START",
    "STOP",
    "PAUSE",
    "BLOCKED_WINDOWS",
    "CUT_LOSS",
    "FLATTEN_ALL",
    "KILL",
    "REARM",
    "SET_LOTS",
    "INDEX",
    "BASKET_REMOVE",
    "MIN_CAPITAL",
    "ADD_FUNDS",
)
EXIT_KINDS = frozenset({"CUT_LOSS", "FLATTEN_ALL", "KILL"})
CONFIRM_KINDS = frozenset({"CUT_LOSS", "FLATTEN_ALL", "KILL", "REARM"})
# entry skip reasons (fail closed)
UNREADABLE = "FOUNDER_CONTROLS_UNREADABLE"
KILLED = "FOUNDER_KILL_SWITCH"
STOPPED = "FOUNDER_STOPPED"
PAUSED = "FOUNDER_PAUSED"
BLOCKED_WINDOW = "FOUNDER_BLOCKED_WINDOW"
INDEX_DISABLED = "FOUNDER_INDEX_DISABLED"
BELOW_MIN_CAPITAL = "FOUNDER_MIN_CAPITAL"
BASKET_REMOVED = "FOUNDER_BASKET_REMOVED"
LOTS_CAP = "FOUNDER_LOTS_CAP"
DEFAULT_LOTS_CEILING = 25

MAX_PAUSE_MINUTES = 24 * 60
MAX_WINDOWS = 12
MAX_FUNDS_INR = 1e8
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_INDEX = re.compile(r"^[A-Z][A-Z0-9]{1,19}$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_KIND_ALIAS = {"BLOCK_WINDOWS": "BLOCKED_WINDOWS"}


def session_of(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), IST).date().isoformat()


def aware_ist(value: datetime | str) -> datetime:
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(IST)


def ts_of(value: datetime | str | float) -> float:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return aware_ist(value if isinstance(value, (datetime, str)) else str(value)).timestamp()


def _minute(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _num(v: Any) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(float(v)) else None


def canonical_kind(kind: str) -> str:
    return _KIND_ALIAS.get(kind, kind)


def lots_ceiling(path: Path | None = None) -> int:
    """Paper max_lots_per_trade from config/risk_limits.yaml (currently 25)."""
    src = path
    if src is None:
        env = os.environ.get("AAD_RISK_LIMITS")
        src = Path(env) if env else Path(__file__).resolve().parents[4] / "config" / "risk_limits.yaml"
    try:
        import yaml  # type: ignore[import-untyped]

        cfg = yaml.safe_load(Path(src).read_text(encoding="utf-8")) or {}
        mode = str(cfg.get("mode") or "paper")
        raw = ((cfg.get("modes") or {}).get(mode) or {}).get("max_lots_per_trade")
        n = int(raw) if raw is not None else DEFAULT_LOTS_CEILING
        return n if n >= 1 else DEFAULT_LOTS_CEILING
    except Exception:
        return DEFAULT_LOTS_CEILING


def validate_args(kind: str, args: Any) -> str | None:
    kind = canonical_kind(kind)
    if not isinstance(args, dict):
        return "args must be an object"
    if kind in {"START", "STOP", "KILL", "REARM"}:
        return None
    if kind == "PAUSE":
        m = args.get("minutes")
        if isinstance(m, bool) or not isinstance(m, int) or not 0 <= m <= MAX_PAUSE_MINUTES:
            return f"minutes must be a whole number 0..{MAX_PAUSE_MINUTES} (0 resumes)"
        return None
    if kind == "BLOCKED_WINDOWS":
        wins = args.get("windows")
        if not isinstance(wins, list) or len(wins) > MAX_WINDOWS:
            return f"windows must be a list of at most {MAX_WINDOWS} {{start, end}} IST times"
        for w in wins:
            if not isinstance(w, dict) or not _HHMM.match(str(w.get("start"))) or not _HHMM.match(str(w.get("end"))):
                return "each window needs start and end as HH:MM (IST)"
            if _minute(str(w["start"])) >= _minute(str(w["end"])):
                return f"window {w['start']}-{w['end']} must end after it starts"
        return None
    if kind == "CUT_LOSS":
        tid = args.get("position_id") or args.get("trade_id") or args.get("instrument_id")
        if not isinstance(tid, str) or not tid.strip() or len(tid) > 200:
            return "position_id is required"
        return None
    if kind == "FLATTEN_ALL":
        und = args.get("underlying")
        if und is None or und == "":
            return None
        if not isinstance(und, str) or not _INDEX.match(und):
            return "underlying must be an index name like NIFTY"
        return None
    if kind == "SET_LOTS":
        n = args.get("lots")
        if n is None:
            return None
        ceil = lots_ceiling()
        if isinstance(n, bool) or not isinstance(n, int) or n < 1 or n > ceil:
            return f"lots must be a whole number 1..{ceil} (or null to clear)"
        return None
    if kind == "INDEX":
        if not isinstance(args.get("underlying"), str) or not _INDEX.match(str(args["underlying"])):
            return "underlying must be an index name like NIFTY"
        if not isinstance(args.get("enabled"), bool):
            return "enabled must be true or false"
        return None
    if kind == "BASKET_REMOVE":
        sid = args.get("strategy_id")
        if not isinstance(sid, str) or not sid.strip() or len(sid) > 64:
            return "strategy_id is required"
        return None
    if kind == "MIN_CAPITAL":
        v = args.get("amount_inr")
        if v is None:
            return None
        v = _num(v)
        if v is None or v < 0 or v > MAX_FUNDS_INR:
            return "amount_inr must be 0..1e8 (or null to clear)"
        return None
    if kind == "ADD_FUNDS":
        v = _num(args.get("amount_inr"))
        if v is None or v <= 0 or v > MAX_FUNDS_INR:
            return "amount_inr must be > 0 and <= 1e8"
        return None
    return f"unknown kind {kind!r}"


def validate_row(row: Any) -> str | None:
    if not isinstance(row, dict):
        return "not an object"
    cid = row.get("command_id") or row.get("id")
    if not isinstance(cid, str) or not _ID.match(cid):
        return "bad command_id"
    if row.get("available_ts") is not None:
        try:
            ts = ts_of(str(row["available_ts"]))
        except (TypeError, ValueError):
            return "bad available_ts"
    else:
        raw_ts = _num(row.get("ts"))
        if raw_ts is None or raw_ts <= 0:
            return "bad ts"
        ts = raw_ts
    if ts <= 0:
        return "bad ts"
    kind = canonical_kind(str(row.get("kind") or ""))
    if kind not in KINDS:
        return f"unknown kind {kind!r}"
    for key in ("actor", "reason"):
        if not isinstance(row.get(key), str) or not row[key].strip() or len(row[key]) > 500:
            return f"{key} is required"
    if row.get("status") not in (None, "received", "applied", "rejected", "pending"):
        return "bad status"
    return validate_args(kind, row.get("args") or {})


def make_row(
    kind: str,
    args: dict[str, Any],
    *,
    actor: str,
    reason: str,
    available_ts: datetime | str,
    command_id: str,
    source: str = "api",
    reject_reason: str | None = None,
) -> dict[str, Any]:
    kind = canonical_kind(kind)
    when = aware_ist(available_ts)
    iso = when.isoformat(timespec="seconds")
    row: dict[str, Any] = {
        "id": command_id,
        "command_id": command_id,
        "ts": when.timestamp(),
        "available_ts": iso,
        "session": when.date().isoformat(),
        "kind": kind,
        "args": dict(args),
        "actor": actor,
        "reason": reason,
        "source": source,
        "status": "rejected" if reject_reason else "received",
    }
    if reject_reason:
        row["status_reason"] = reject_reason
        row["reject_reason"] = reject_reason
    return row


@dataclass(frozen=True)
class State:
    running: bool = True
    pause_until: float | None = None
    windows: tuple[tuple[int, int], ...] = ()
    lots: int | None = None
    killed_ts: float | None = None
    index: dict[str, bool] = field(default_factory=dict)
    removed: frozenset[str] = field(default_factory=frozenset)
    min_capital: float | None = None
    funds_added: float = 0.0

    def as_dict(self, now: float | None = None) -> dict[str, Any]:
        def ist(ts: float | None) -> str | None:
            return None if ts is None else datetime.fromtimestamp(ts, IST).isoformat(timespec="seconds")

        paused = self.pause_until is not None and (now is None or now < self.pause_until)
        return {
            "running": self.running,
            "paused_until_ist": ist(self.pause_until) if paused else None,
            "blocked_windows": [
                {"start": f"{a // 60:02d}:{a % 60:02d}", "end": f"{b // 60:02d}:{b % 60:02d}"} for a, b in self.windows
            ],
            "lots": self.lots,
            "killed": self.killed_ts is not None,
            "killed_at_ist": ist(self.killed_ts),
            "index_enabled": dict(self.index),
            "basket_removed": sorted(self.removed),
            "min_capital_inr": self.min_capital,
            "funds_added_inr": round(self.funds_added, 2),
        }


def _fold(st: State, row: dict[str, Any]) -> State:
    kind = canonical_kind(str(row["kind"]))
    a = row.get("args") or {}
    ts = float(ts_of(row.get("ts") or row["available_ts"]))
    if kind in {"START", "STOP"}:
        return replace(st, running=kind == "START")
    if kind == "PAUSE":
        return replace(st, pause_until=ts + 60 * int(a["minutes"]) if a.get("minutes") else None)
    if kind == "BLOCKED_WINDOWS":
        return replace(st, windows=tuple((_minute(w["start"]), _minute(w["end"])) for w in a["windows"]))
    if kind == "SET_LOTS":
        return replace(st, lots=a.get("lots"))
    if kind == "KILL":
        return replace(st, killed_ts=ts)
    if kind == "REARM":
        return replace(st, killed_ts=None)
    if kind == "INDEX":
        return replace(st, index={**st.index, str(a["underlying"]): bool(a["enabled"])})
    if kind == "BASKET_REMOVE":
        return replace(st, removed=st.removed | {str(a["strategy_id"])})
    if kind == "MIN_CAPITAL":
        v = a.get("amount_inr")
        return replace(st, min_capital=None if v is None else float(v))
    if kind == "ADD_FUNDS":
        return replace(st, funds_added=st.funds_added + float(a["amount_inr"]))
    return st


class CommandBook:
    """Deterministic fold of the founder log. Entries fail closed; exits fail open."""

    def __init__(
        self,
        rows: list[dict[str, Any]],
        problems: list[str] | None = None,
        blocked_from: float | None = None,
    ) -> None:
        self.rejected = [r for r in rows if r.get("status") == "rejected"]
        self.commands = sorted(
            (r for r in rows if r.get("status") != "rejected"),
            key=lambda r: float(ts_of(r.get("ts") or r["available_ts"])),
        )
        self.problems = list(problems or [])
        self.blocked_from = (0.0 if blocked_from is None else float(blocked_from)) if self.problems else None
        self._ts: list[float] = []
        self._states: list[State] = []
        st = State()
        for row in self.commands:
            if canonical_kind(str(row["kind"])) in EXIT_KINDS - {"KILL"}:
                continue
            st = _fold(st, row)
            self._ts.append(float(ts_of(row.get("ts") or row["available_ts"])))
            self._states.append(st)
        self.lots_cap: int | None = None

    def state_at(self, ts: float) -> State:
        i = bisect_right(self._ts, float(ts))
        return self._states[i - 1] if i else State()

    def entry_reason(
        self, ts: float, *, underlying: str = "", strategy_id: str = "", capital_inr: float | None = None
    ) -> str | None:
        if self.blocked_from is not None and ts >= self.blocked_from:
            return UNREADABLE
        st = self.state_at(ts)
        if st.killed_ts is not None:
            return KILLED
        if not st.running:
            return STOPPED
        if st.pause_until is not None and ts < st.pause_until:
            return PAUSED
        dt = datetime.fromtimestamp(int(ts), IST)
        minute = dt.hour * 60 + dt.minute
        if any(a <= minute < b for a, b in st.windows):
            return BLOCKED_WINDOW
        if underlying and st.index.get(str(underlying).upper()) is False:
            return INDEX_DISABLED
        if strategy_id and strategy_id in st.removed:
            return BASKET_REMOVED
        if st.min_capital is not None and capital_inr is not None and capital_inr < st.min_capital:
            return BELOW_MIN_CAPITAL
        return None

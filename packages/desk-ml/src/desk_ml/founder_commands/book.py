"""What founder commands mean, as of a tick. Pure and deterministic: no clock, no disk.

Every command applies from its own timestamp. The live loop re-replays the whole day each cycle,
so a command never changes a trade booked before it, and a replay that loads the same commands
file gives the same trades. Human commands outrank every algo gate:

* Entries fail closed. An unreadable or invalid line in the log blocks every new entry from the
  last good command before it (from the start when there is none).
* Exits fail open. Cut loss and the kill switch run before the engine's own exit rules, still
  run when other lines of the log are corrupt, and still book when the normal close raises.

Settings (START/STOP, pause, blocked windows, lots, kill/re-arm, per-index, capital) are standing:
they hold across sessions until a later command changes them. Position commands (cut loss,
go for T2) name one ``trade_id``.
"""

from __future__ import annotations

import math
import re
from bisect import bisect_right
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Optional

IST = timezone(timedelta(hours=5, minutes=30))

KINDS = (
    "START", "STOP", "PAUSE", "BLOCK_WINDOWS", "CUT_LOSS", "GO_T2", "SET_LOTS",
    "KILL", "REARM", "INDEX", "MIN_CAPITAL", "ADD_FUNDS",
)
EXIT_KINDS = frozenset({"CUT_LOSS", "KILL"})
POSITION_KINDS = frozenset({"CUT_LOSS", "GO_T2"})
CONFIRM_KINDS = frozenset({"CUT_LOSS", "KILL", "REARM"})

# entry skip reasons (fail closed)
UNREADABLE = "FOUNDER_CONTROLS_UNREADABLE"
KILLED = "FOUNDER_KILL_SWITCH"
STOPPED = "FOUNDER_STOPPED"
PAUSED = "FOUNDER_PAUSED"
BLOCKED_WINDOW = "FOUNDER_BLOCKED_WINDOW"
INDEX_DISABLED = "FOUNDER_INDEX_DISABLED"
BELOW_MIN_CAPITAL = "FOUNDER_MIN_CAPITAL"
# exit reasons (never refused)
CUT_LOSS_REASON = "FOUNDER_CUT_LOSS"
KILL_REASON = "FOUNDER_KILL"

MAX_PAUSE_MINUTES = 24 * 60
MAX_WINDOWS = 12
MAX_FUNDS_INR = 1e8
_ID = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
_INDEX = re.compile(r"^[A-Z][A-Z0-9]{1,19}$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def session_of(ts: float) -> str:
    return datetime.fromtimestamp(float(ts), IST).date().isoformat()


def _minute(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def _num(v: Any) -> Optional[float]:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v) if math.isfinite(float(v)) else None


def validate_args(kind: str, args: Any) -> Optional[str]:
    """None when ``args`` fit ``kind``; otherwise the reason. Shared by the API and the engine."""
    if not isinstance(args, dict):
        return "args must be an object"
    if kind in {"START", "STOP", "KILL", "REARM"}:
        return None
    if kind == "PAUSE":
        m = args.get("minutes")
        if isinstance(m, bool) or not isinstance(m, int) or not 0 <= m <= MAX_PAUSE_MINUTES:
            return f"minutes must be a whole number 0..{MAX_PAUSE_MINUTES} (0 resumes)"
        return None
    if kind == "BLOCK_WINDOWS":
        wins = args.get("windows")
        if not isinstance(wins, list) or len(wins) > MAX_WINDOWS:
            return f"windows must be a list of at most {MAX_WINDOWS} {{start, end}} IST times"
        for w in wins:
            if not isinstance(w, dict) or not _HHMM.match(str(w.get("start"))) or not _HHMM.match(str(w.get("end"))):
                return "each window needs start and end as HH:MM (IST)"
            if _minute(w["start"]) >= _minute(w["end"]):
                return f"window {w['start']}-{w['end']} must end after it starts"
        return None
    if kind in POSITION_KINDS:
        tid = args.get("trade_id")
        if not isinstance(tid, str) or not tid.strip() or len(tid) > 200:
            return "trade_id is required"
        return None
    if kind == "SET_LOTS":
        n = args.get("lots")
        if n is None:
            return None
        if isinstance(n, bool) or not isinstance(n, int) or n < 1:
            return "lots must be a whole number >= 1 (or null to clear)"
        return None
    if kind == "INDEX":
        if not isinstance(args.get("underlying"), str) or not _INDEX.match(args["underlying"]):
            return "underlying must be an index name like NIFTY"
        if not isinstance(args.get("enabled"), bool):
            return "enabled must be true or false"
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


def validate_row(row: Any) -> Optional[str]:
    if not isinstance(row, dict):
        return "not an object"
    if not isinstance(row.get("id"), str) or not _ID.match(row["id"]):
        return "bad id"
    ts = _num(row.get("ts"))
    if ts is None or ts <= 0:
        return "bad ts"
    kind = row.get("kind")
    if kind not in KINDS:
        return f"unknown kind {kind!r}"
    for key in ("actor", "reason"):
        if not isinstance(row.get(key), str) or not row[key].strip() or len(row[key]) > 500:
            return f"{key} is required"
    if row.get("status") not in (None, "rejected"):
        return "bad status"
    return validate_args(kind, row.get("args"))


def make_row(
    kind: str, args: dict[str, Any], *, actor: str, reason: str, ts: float, command_id: str,
    source: str = "api", reject_reason: Optional[str] = None,
) -> dict[str, Any]:
    row = {
        "id": command_id, "ts": float(ts), "session": session_of(ts), "kind": kind, "args": dict(args),
        "actor": actor, "reason": reason, "source": source,
    }
    if reject_reason:
        row["status"] = "rejected"
        row["reject_reason"] = reject_reason
    return row


@dataclass(frozen=True)
class State:
    running: bool = True
    pause_until: Optional[float] = None
    windows: tuple[tuple[int, int], ...] = ()
    lots: Optional[int] = None
    killed_ts: Optional[float] = None
    index: dict[str, bool] = field(default_factory=dict)
    min_capital: Optional[float] = None
    funds_added: float = 0.0

    def as_dict(self, now: Optional[float] = None) -> dict[str, Any]:
        def ist(ts: Optional[float]) -> Optional[str]:
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
            "min_capital_inr": self.min_capital,
            "funds_added_inr": round(self.funds_added, 2),
        }


def _fold(st: State, row: dict[str, Any]) -> State:
    kind, a, ts = row["kind"], row.get("args") or {}, float(row["ts"])
    if kind in {"START", "STOP"}:
        return replace(st, running=kind == "START")
    if kind == "PAUSE":
        return replace(st, pause_until=ts + 60 * a["minutes"] if a["minutes"] else None)
    if kind == "BLOCK_WINDOWS":
        return replace(st, windows=tuple((_minute(w["start"]), _minute(w["end"])) for w in a["windows"]))
    if kind == "SET_LOTS":
        return replace(st, lots=a.get("lots"))
    if kind == "KILL":
        return replace(st, killed_ts=ts)
    if kind == "REARM":
        return replace(st, killed_ts=None)
    if kind == "INDEX":
        return replace(st, index={**st.index, a["underlying"]: bool(a["enabled"])})
    if kind == "MIN_CAPITAL":
        v = a.get("amount_inr")
        return replace(st, min_capital=None if v is None else float(v))
    if kind == "ADD_FUNDS":
        return replace(st, funds_added=st.funds_added + float(a["amount_inr"]))
    return st


class CommandBook:
    """One replay's view of the founder log. Records which command applied, and when."""

    def __init__(
        self, rows: list[dict[str, Any]], problems: Optional[list[str]] = None, blocked_from: Optional[float] = None
    ) -> None:
        self.rejected = [r for r in rows if r.get("status") == "rejected"]
        # sorted() is stable: commands with the same ts apply in log order
        self.commands = sorted((r for r in rows if r.get("status") != "rejected"), key=lambda r: float(r["ts"]))
        self.problems = list(problems or [])
        self.blocked_from = (0.0 if blocked_from is None else float(blocked_from)) if self.problems else None
        self._ts: list[float] = []
        self._states: list[State] = []
        st = State()
        for row in self.commands:
            if row["kind"] not in POSITION_KINDS:
                st = _fold(st, row)
                self._ts.append(float(row["ts"]))
                self._states.append(st)
        self.results: dict[str, dict[str, Any]] = {}
        self.last_ts: dict[str, int] = {}
        self.lots_cap: Optional[int] = None  # risk-limits cap for lots overrides; None = only lower

    def __bool__(self) -> bool:
        return bool(self.commands or self.rejected or self.problems)

    def state_at(self, ts: float) -> State:
        i = bisect_right(self._ts, float(ts))
        return self._states[i - 1] if i else State()

    def _observe(self, underlying: str, ts: int) -> None:
        u = str(underlying).upper()
        if int(ts) > self.last_ts.get(u, -1):
            self.last_ts[u] = int(ts)

    # ------------------------------------------------------------------ entries

    def account_inr(self, engine: Any, ts: int) -> float:
        """Desk capital + funds added + today's realized net, as of ``ts``.

        ponytail: realized net only sees indices the replay has walked so far (it walks one index
        at a time), the same limit as the risk-state rebuild; upgrade with a time-ordered replay.
        """
        day = session_of(ts)
        realized = sum(
            float(r.get("realized_pnl_inr") or 0.0)
            for r in engine.closed
            if r.get("closed_ts") is not None and int(r["closed_ts"]) <= ts and session_of(r["closed_ts"]) == day
        )
        desk = float((getattr(engine, "capital_plan", None) or {}).get("desk_capital_inr") or 0.0)
        return desk + self.state_at(ts).funds_added + realized

    def entry_gate(self, engine: Any, underlying: str, ts: int) -> tuple[Optional[str], Optional[bool]]:
        """``(skip_reason, index_enabled)``. ``index_enabled`` True = founder explicitly enabled it."""
        self._observe(underlying, ts)
        if self.blocked_from is not None and ts >= self.blocked_from:
            return UNREADABLE, None
        st = self.state_at(ts)
        if st.killed_ts is not None:
            return KILLED, None
        if not st.running:
            return STOPPED, None
        if st.pause_until is not None and ts < st.pause_until:
            return PAUSED, None
        dt = datetime.fromtimestamp(int(ts), IST)
        minute = dt.hour * 60 + dt.minute
        if any(a <= minute < b for a, b in st.windows):
            return BLOCKED_WINDOW, None
        enabled = st.index.get(str(underlying).upper())
        if enabled is False:
            return INDEX_DISABLED, None
        if st.min_capital is not None and self.account_inr(engine, ts) < st.min_capital:
            return BELOW_MIN_CAPITAL, None
        return None, enabled

    def sizing(self, capital: float, bounds: dict[str, int], ts: int) -> tuple[float, dict[str, int]]:
        """Added funds raise the book's capital; a lots override sets the next fills' size.

        The override never exceeds the engine's ``max_lots`` nor the risk limits' cap (``lots_cap``).
        When the limits could not be read it may only lower the engine's target (fail closed).
        """
        st = self.state_at(ts)
        capital = float(capital) + st.funds_added
        if st.lots is not None:
            cap = self.lots_cap if self.lots_cap is not None else int(bounds["target_lots"])
            n = min(int(st.lots), int(bounds["max_lots"]), int(cap))
            bounds = {"min_lots": min(n, int(bounds["min_lots"])), "target_lots": n, "max_lots": n}
        return capital, bounds

    # -------------------------------------------------------------------- exits

    def _exit_for(self, pos: Any, ts: int) -> Optional[tuple[str, dict[str, Any]]]:
        for cmd in self.commands:
            if float(cmd["ts"]) > ts:
                break
            if cmd["kind"] == "KILL" and float(pos.opened_ts) < float(cmd["ts"]):
                return KILL_REASON, cmd
            if cmd["kind"] == "CUT_LOSS" and cmd["args"]["trade_id"] == pos.trade_id:
                return CUT_LOSS_REASON, cmd
        return None

    def _go_t2(self, pos: Any, ts: int) -> None:
        for cmd in self.commands:
            if float(cmd["ts"]) > ts:
                break
            if cmd["kind"] == "GO_T2" and cmd["args"]["trade_id"] == pos.trade_id and not pos.founder_t2:
                pos.founder_t2 = True
                self._applied(cmd, ts, trade_id=pos.trade_id, target=pos.target)

    def _applied(self, cmd: dict[str, Any], ts: int, **detail: Any) -> None:
        res = self.results.setdefault(cmd["id"], {"status": "applied", "applied_ts": int(ts)})
        if cmd["kind"] == "KILL":
            res.setdefault("flattened", []).append(detail.get("trade_id"))
        else:
            res.update(detail)

    def manage(self, engine: Any, pos: Any, ts: int, ltp: Optional[float], close: Callable[..., None]) -> bool:
        """Founder exits for one open ticket at tick ``ts``. True when the ticket was closed."""
        self._observe(pos.underlying, ts)
        hit = self._exit_for(pos, ts)
        if hit is None:
            self._go_t2(pos, ts)
            return False
        reason, cmd = hit
        px = next((float(v) for v in (ltp, pos.last_ltp, pos.entry) if v is not None), 0.0)
        book_exit(engine, pos, px=px, ts=ts, reason=reason, close=close)
        self._applied(cmd, ts, trade_id=pos.trade_id, exit_px=round(px, 4))
        return True

    # ------------------------------------------------------------------ results

    def results_for(self, session_day: Optional[str]) -> list[dict[str, Any]]:
        """Status of every command this replay can judge: applied, rejected (with reason) or pending."""
        last_any = max(self.last_ts.values(), default=None)
        day = session_day or (session_of(last_any) if last_any is not None else None)
        out = [self._result(r, "rejected", r.get("reject_reason")) for r in self.rejected]
        for r in self.commands:
            if r["id"] in self.results:
                out.append({**self._result(r, "applied"), **self.results[r["id"]]})
            elif r["kind"] in POSITION_KINDS:
                session = r["session"] if isinstance(r.get("session"), str) else session_of(r["ts"])  # may be missing
                if day is not None and session < day:
                    continue  # judged by the replay of its own session
                und = next((u for u in self.last_ts if f"-{u}-" in r["args"]["trade_id"]), None)
                last = self.last_ts.get(und) if und else None
                if session == day and last is not None and last >= float(r["ts"]):
                    out.append(self._result(r, "rejected", "TRADE_NOT_OPEN: no open ticket with this id at or after the command"))
                else:
                    out.append(self._result(r, "pending"))
            elif last_any is not None and last_any >= float(r["ts"]):
                out.append({**self._result(r, "applied"), "applied_ts": int(math.ceil(float(r["ts"])))})
            else:
                out.append(self._result(r, "pending"))
        return out

    @staticmethod
    def _result(r: dict[str, Any], status: str, why: Optional[str] = None) -> dict[str, Any]:
        return {"id": r["id"], "kind": r["kind"], "ts": r["ts"], "status": status, "status_reason": why}


def book_exit(engine: Any, pos: Any, *, px: float, ts: int, reason: str, close: Callable[..., None]) -> None:
    """Close through the engine's normal ``close``; if that raises before booking, book a minimal row.

    A raise after the row is booked (e.g. the model log hit a full disk) leaves the booked close.
    """
    key = (pos.book_id, pos.underlying)
    try:
        close(engine, pos, ltp=float(px), ts=int(ts), reason=reason, root=engine.root)
        return
    except Exception as exc:  # the founder exit must still happen
        if engine.opens.get(key) is not pos:
            return
        engine.opens.pop(key, None)
        qty = pos.qty or (int(pos.lot_size or 0) * int(pos.lots or 0)) or None
        points = float(px) - float(pos.entry) if pos.filled else 0.0
        gross = round(points * qty, 2) if pos.filled and qty else 0.0
        opened = datetime.fromtimestamp(int(pos.opened_ts), IST).isoformat(timespec="seconds")
        closed = datetime.fromtimestamp(int(ts), IST).isoformat(timespec="seconds")
        engine.closed.append({
            "book_id": pos.book_id, "model_names": list(getattr(pos, "model_names", None) or [pos.book_id]),
            "underlying": pos.underlying, "side": pos.side, "trade_id": pos.trade_id,
            "status": "CLOSED_PAPER" if pos.filled else "CANCELLED_UNFILLED", "target_step": pos.target_step,
            "entry": pos.entry, "limit_price": pos.limit_price or pos.entry, "exit": round(float(px), 4),
            "stop": pos.stop, "target": pos.target, "atm_strike": pos.atm_strike, "exit_reason": reason,
            "sl_hit": False, "sl_loss_inr": None, "target_hit": False, "realized_pnl": round(points, 4),
            "gross_pnl_inr": gross, "charges_inr": None, "realized_pnl_inr": gross,
            "lots": pos.lots, "lot_size": pos.lot_size, "qty": qty, "capital_inr": pos.capital_inr,
            "opened_ts": pos.opened_ts, "closed_ts": int(ts), "last_updated_ts": int(ts),
            "opened_ist": opened, "closed_ist": closed, "last_updated_ist": closed,
            "justification": f"{pos.justification} | founder {reason}".strip(" |"),
            "won": gross > 0, "result": "CANCELLED" if not pos.filled else ("LOSS" if gross <= 0 else "TIME"),
            "filled": bool(pos.filled), "execution": "refused", "promote": False, "shadow": True,
            "founder_fallback": f"normal close raised {type(exc).__name__}; booked without charges",
        })
        if gross and hasattr(engine, "book_equity"):
            engine.equity[pos.book_id] = engine.book_equity(pos.book_id) + gross

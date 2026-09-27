"""Reliability primitives for the paper engine (PR-A).

- ``atomic_write_text`` / ``atomic_write_json``: temp file in the same folder, fsync, ``os.replace``,
  fsync the folder. A crash or ENOSPC mid-write leaves the old file, never a truncated one.
- ``AlertSink``: one HEALTH alert per ``(session, check, kind)``, persisted in
  ``data/health/alert_state.json`` so a new process does not alert again. The same state is the
  incident registry: ``first_seen`` is when the live loop first saw a condition, which is what
  time-bounded entry blocks start from. Never raises into a fail-safe path.
- ``ReplayContext``: the explicit inputs of one replay (data root, session, clock, sinks).
- ``ModelLogSink``: per-session model log, idempotent across re-replays (per-index tick
  high-water mark), SKIP/HOLD aggregated per minute, hard size cap.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional, Sequence

IST = timezone(timedelta(hours=5, minutes=30))
ALERTS_REL = Path("data") / "health" / "alerts.jsonl"
ALERT_STATE_REL = Path("data") / "health" / "alert_state.json"
MODEL_LOG_DIR_REL = Path("data") / "recon" / "model_log"
MODEL_LOG_CAP_BYTES = 50 * 1024 * 1024
MODEL_LOG_VERBOSE_ENV = "MODEL_LOG_VERBOSE"
AGGREGATED_EVENTS = frozenset({"HOLD", "SKIP"})
ALERT_STATE_KEEP_DAYS = 7


def wall_clock() -> datetime:
    return datetime.now(IST)


def _fsync_dir(folder: Path) -> None:
    try:
        fd = os.open(str(folder), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise
    _fsync_dir(path.parent)


def atomic_write_json(path: Path, obj: Any, **dumps_kw: Any) -> None:
    dumps_kw.setdefault("default", str)
    atomic_write_text(path, json.dumps(obj, **dumps_kw) + "\n")


def append_line(path: Path, line: str) -> None:
    """One fsync'd append. A crash leaves at most one partial last line (readers skip it)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(line if line.endswith("\n") else line + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def read_jsonl(path: Path) -> Optional[list[dict[str, Any]]]:
    """Rows of an append-only JSONL log, or None if the file does not exist.

    A last line without a newline that does not parse is an append still in progress and is
    ignored. Any other bad line, or a row that is not an object, raises ``ValueError``.
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return None
    text = raw.decode("utf-8")  # UnicodeDecodeError is a ValueError
    lines = text.split("\n")
    tail_open = not text.endswith("\n")
    rows: list[dict[str, Any]] = []
    for n, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            if tail_open and n == len(lines) - 1:
                break
            raise ValueError(f"{path}: line {n + 1} is not JSON")
        if not isinstance(row, dict):
            raise ValueError(f"{path}: line {n + 1} is not an object")
        rows.append(row)
    return rows


def _stderr(msg: str) -> None:
    try:
        print(msg, file=sys.stderr, flush=True)
    except Exception:  # noqa: BLE001 — stderr itself can be gone
        pass


# Incidents recorded while the state file could not be written. Shared by every sink in this
# process so a new sink per cycle still dedupes. ponytail: lost on restart when the disk refuses
# writes; the restart then alerts once more.
_UNSAVED_STATE: dict[str, dict[str, dict[str, Any]]] = {}
# Alert lines alerts.jsonl refused (disk full): written by the next emit that can write.
_PENDING_ALERTS: dict[str, list[str]] = {}


class AlertSink:
    """Persisted, deduplicated alerts and the live loop's incident registry."""

    def __init__(self, root: Path, *, clock: Callable[[], datetime] = wall_clock) -> None:
        self.root = Path(root)
        self.alerts_path = self.root / ALERTS_REL
        self.state_path = self.root / ALERT_STATE_REL
        self.clock = clock

    @staticmethod
    def key(session: str, check: str, kind: str) -> str:
        return f"{session}|{check}|{kind}"

    def _load(self) -> dict[str, dict[str, Any]]:
        try:
            blob = json.loads(self.state_path.read_text(encoding="utf-8"))
            state = blob.get("incidents") if isinstance(blob, dict) else None
            if not isinstance(state, dict):
                raise ValueError("alert state is not a mapping")
        except FileNotFoundError:
            state = {}
        except (OSError, ValueError) as exc:
            state = {}
            self._quarantine(exc)
        merged = dict(state)
        for k, v in _UNSAVED_STATE.get(str(self.state_path), {}).items():
            merged.setdefault(k, v)
        return merged

    def _quarantine(self, exc: BaseException) -> None:
        """Move a corrupt state file aside so it is not silently overwritten."""
        stamp = self.clock().strftime("%Y%m%dT%H%M%S")
        try:
            os.replace(self.state_path, self.state_path.with_name(f"{self.state_path.name}.corrupt.{stamp}"))
        except OSError:
            pass
        _stderr(f"alert state unreadable ({type(exc).__name__}: {exc}); starting a fresh registry")

    def incidents(self) -> dict[str, dict[str, Any]]:
        return self._load()

    def first_seen(self, session: str, check: str, kind: str) -> Optional[float]:
        row = self._load().get(self.key(session, check, kind))
        if not row:
            return None
        try:
            return float(row["first_ts"])
        except (KeyError, TypeError, ValueError):
            return None

    def record(self, *, session: str, check: str, kind: str, ts: Optional[float] = None,
               message: str = "") -> tuple[bool, float]:
        """Register an incident without alerting. Returns (new, first_ts)."""
        return self._record(session, check, kind, ts, message, alert=False, severity="INFO")

    def emit(self, *, session: str, check: str, kind: str, message: str, severity: str = "CRITICAL",
             ts: Optional[float] = None, **extra: Any) -> bool:
        """Alert once per (session, check, kind). True when this call wrote the alert."""
        new, _first = self._record(session, check, kind, ts, message, alert=True, severity=severity, extra=extra)
        return new

    def _record(self, session: str, check: str, kind: str, ts: Optional[float], message: str, *,
                alert: bool, severity: str, extra: Optional[Mapping[str, Any]] = None) -> tuple[bool, float]:
        try:
            state = self._load()
        except Exception as exc:  # noqa: BLE001 — never raise into a fail-safe path
            _stderr(f"alert state load failed: {exc}")
            state = {}
        k = self.key(session, check, kind)
        now = self.clock()
        row = state.get(k)
        if row and (row.get("alerted") or not alert):
            try:
                return False, float(row["first_ts"])
            except (KeyError, TypeError, ValueError):
                return False, float(ts if ts is not None else now.timestamp())
        first_ts = float(row["first_ts"]) if row and row.get("first_ts") is not None else float(
            ts if ts is not None else now.timestamp()
        )
        state[k] = {
            "session": session, "check": check, "kind": kind, "first_ts": first_ts,
            "first_wall": (row or {}).get("first_wall") or now.isoformat(timespec="seconds"),
            "alerted": bool(alert or (row or {}).get("alerted")), "message": str(message)[:500],
        }
        self._save(state, k)
        if alert:
            rec = {
                "ts": datetime.fromtimestamp(first_ts, IST).isoformat(timespec="seconds"),
                "wall_ts": now.isoformat(timespec="seconds"),
                "event": "ALERT", "check": check, "severity": severity, "error_kind": kind,
                "session": session, "message": str(message)[:2000], **dict(extra or {}),
            }
            line = json.dumps(rec, default=str)
            _PENDING_ALERTS.setdefault(str(self.alerts_path), []).append(line)
            if not self.flush_pending():
                _stderr(f"ALERT (alerts.jsonl unwritable; queued) {line}")
        return True, first_ts

    def flush_pending(self) -> bool:
        """Write queued alert lines. True when nothing is left queued. Never raises."""
        queue = _PENDING_ALERTS.get(str(self.alerts_path)) or []
        while queue:
            try:
                append_line(self.alerts_path, queue[0])
            except Exception:  # noqa: BLE001
                return False
            queue.pop(0)
        return True

    def _save(self, state: dict[str, dict[str, Any]], key: str) -> None:
        cutoff = (self.clock() - timedelta(days=ALERT_STATE_KEEP_DAYS)).date().isoformat()
        keep = {k: v for k, v in state.items() if str(v.get("session") or "") >= cutoff or k == key}
        try:
            atomic_write_json(self.state_path, {"incidents": keep}, indent=1, sort_keys=True)
        except Exception as exc:  # noqa: BLE001
            _UNSAVED_STATE.setdefault(str(self.state_path), {})[key] = state[key]
            _stderr(f"alert state not saved ({type(exc).__name__}: {exc}); kept in memory for this process")
            return
        _UNSAVED_STATE.get(str(self.state_path), {}).pop(key, None)


class ModelLogSink:
    """Per-session model log. Re-replaying the day writes each event once.

    The live loop re-derives the whole day every cycle. Each index has a persisted high-water
    mark (last tick ts written); events at or before it were written by an earlier cycle and are
    dropped. SKIP/HOLD rows (95% of the old file) become one row per minute, book, index and
    reason unless ``MODEL_LOG_VERBOSE=1``. Past ``cap_bytes`` the sink stops and alerts once.
    """

    def __init__(self, root: Path, session: str, *, alerts: Optional[AlertSink] = None,
                 cap_bytes: int = MODEL_LOG_CAP_BYTES, verbose: Optional[bool] = None) -> None:
        folder = Path(root) / MODEL_LOG_DIR_REL
        self.session = session
        self.path = folder / f"{session}.jsonl"
        self.state_path = folder / f"{session}.state.json"
        self.alerts = alerts
        self.cap_bytes = int(cap_bytes)
        self.verbose = (os.environ.get(MODEL_LOG_VERBOSE_ENV) == "1") if verbose is None else bool(verbose)
        self.hwm: dict[str, int] = {}
        self.agg_hwm: dict[str, int] = {}
        # Unknown progress (corrupt state): write nothing this replay, then resume from its last
        # tick. A gap in a diagnostic log is better than duplicating the whole day.
        self.skip_this_replay = False
        try:
            blob = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.hwm = {str(k): int(v) for k, v in (blob.get("hwm") or {}).items()}
            self.agg_hwm = {str(k): int(v) for k, v in (blob.get("agg_hwm_minute") or {}).items()}
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError, AttributeError):
            self.hwm, self.agg_hwm, self.skip_this_replay = {}, {}, True
        self.und: Optional[str] = None
        self.tick_ts: Optional[int] = None
        self.last_ts: dict[str, int] = {}
        self.rows: list[dict[str, Any]] = []
        self.agg: dict[tuple[str, int, str, str, str], int] = {}

    def set_tick(self, underlying: str, ts: int) -> None:
        self.und, self.tick_ts = str(underlying).upper(), int(ts)
        self.last_ts[self.und] = max(self.last_ts.get(self.und, 0), self.tick_ts)

    def write(self, rec: dict[str, Any]) -> None:
        und, ts = self.und, self.tick_ts
        if und is None or ts is None or self.skip_this_replay:
            return
        event = str(rec.get("event") or "")
        if event in AGGREGATED_EVENTS and not self.verbose:
            if ts // 60 <= self.agg_hwm.get(und, -1):
                return
            key = (und, ts // 60, event, str(rec.get("book_id") or rec.get("model") or ""), str(rec.get("reason") or ""))
            self.agg[key] = self.agg.get(key, 0) + 1
            return
        if ts <= self.hwm.get(und, 0):
            return
        self.rows.append({**rec, "session": self.session, "underlying": rec.get("underlying") or und, "tick_ts": ts})

    def flush(self) -> None:
        """Append this replay's new rows once. Never raises."""
        out = list(self.rows)
        new_agg_hwm = dict(self.agg_hwm)
        new_hwm = dict(self.hwm)
        for und, last in self.last_ts.items():
            done_minute = last // 60 - 1  # the current minute may still grow next cycle
            for (u, minute, event, book, reason), n in sorted(self.agg.items()):
                if u == und and minute <= done_minute:
                    out.append({"event": event, "book_id": book, "reason": reason, "count": n, "aggregated": "minute",
                                "session": self.session, "underlying": u, "tick_ts": minute * 60})
            new_agg_hwm[und] = max(new_agg_hwm.get(und, -1), done_minute)
            new_hwm[und] = max(new_hwm.get(und, 0), last)
        self.rows, self.agg = [], {}
        try:
            size = self.path.stat().st_size if self.path.exists() else 0
            text = "".join(json.dumps(r, default=str) + "\n" for r in out)
            if out and size + len(text.encode("utf-8")) > self.cap_bytes:
                if self.alerts is not None:
                    self.alerts.emit(session=self.session, check="model_log", kind="cap_reached",
                                     message=f"model log {self.path.name} reached {self.cap_bytes} bytes; writes stopped",
                                     severity="WARN")
                return
            if out:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(text)
                    fh.flush()
                    os.fsync(fh.fileno())
            atomic_write_json(self.state_path, {"hwm": new_hwm, "agg_hwm_minute": new_agg_hwm})
            self.hwm, self.agg_hwm, self.skip_this_replay = new_hwm, new_agg_hwm, False
        except Exception as exc:  # noqa: BLE001 — a diagnostic log must never stop the engine
            if self.alerts is not None:
                self.alerts.emit(session=self.session, check="model_log", kind=f"write_failed:{type(exc).__name__}",
                                 message=f"model log write failed: {exc}", severity="WARN")
            else:
                _stderr(f"model log write failed: {exc}")


@dataclass(frozen=True)
class ReplayContext:
    """Explicit inputs of one replay. Engine code reads these, never ``repo_root()`` or the wall clock.

    ``entry_blocks`` holds ``(reason, from_ts, until_ts or None)`` intervals: new entries are
    blocked for ``from_ts <= tick.ts < until_ts``, so a re-replay reproduces every trade booked
    before a block. The live cycle fills it from ``live_cycle.BlockRegistry``; offline replays
    leave it empty.
    """

    root: Path
    session_ist_date: Optional[str] = None
    live_loop: bool = False
    write: bool = False
    clock: Callable[[], datetime] = wall_clock
    alerts: Optional[AlertSink] = None
    model_log: Optional[ModelLogSink] = None
    entry_blocks: Sequence[tuple[str, float, Optional[float]]] = ()
    params: Optional[Mapping[str, Any]] = None
    risk_config: Optional[Path] = None
    # Live cycle only: the founder / override rows as read once for this cycle ("unknown" = no
    # trustworthy founder state at all). None = read them from ``root`` (offline replays).
    founder_rows: Any = None
    override_rows: Optional[Sequence[Mapping[str, Any]]] = None

    def block_at(self, ts: int) -> Optional[tuple[str, float]]:
        hits = [(float(lo), kind) for kind, lo, hi in self.entry_blocks
                if float(lo) <= float(ts) and (hi is None or float(ts) < float(hi))]
        if not hits:
            return None
        from_ts, kind = min(hits)
        return kind, from_ts

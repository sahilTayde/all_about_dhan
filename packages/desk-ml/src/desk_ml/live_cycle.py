"""One cycle of the live paper loop, shared by ``dual_tape --paper-scalp`` and ``paper_scalp run_loop``.

The loop re-replays the whole day from the tape every cycle. That is only safe if a re-run can
never change the past, so each cycle:

1. ingests control inputs with a timestamp (founder JSON edits, undated overrides) and turns
   every blocking condition (kill switch, halt, unreadable control files, a failing engine,
   an unwritable disk) into a time-bounded entry block (``BlockRegistry``);
2. freezes the session's params, risk limits and lot sizes at its first cycle (write-once);
3. replays with an explicit ``ReplayContext`` (no wall clock in the engine);
4. checks the replay against the append-only booked-trade file (``guard_history``): a booked
   trade can never vanish or change, a trade can never appear before the previous cycle's tape
   cut-off, and an open ticket that vanished is force-closed so nothing is left unmanaged;
5. writes the board atomically and an honest heartbeat (``engine_heartbeat.json``): a failed or
   hung cycle shows as dead, never as alive.

Offline replays do none of this and stay byte-identical.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, fields
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

from desk_ml.reliability import (
    AlertSink,
    ReplayContext,
    append_line,
    atomic_write_json,
    read_jsonl,
    wall_clock,
)

IST = timezone(timedelta(hours=5, minutes=30))
FROZEN_REL = Path("data") / "recon" / "params_frozen"
BOOKED_REL = Path("data") / "recon" / "paper_booked"
BLOCKS_REL = Path("data") / "recon" / "live_blocks"
HEARTBEAT_REL = Path("data") / "recon" / "engine_heartbeat.json"
HALT_REL = Path("data") / "desk" / "live_loop" / "mtm_halt.json"  # desk.executor.HALT_REL
ENGINE_FAIL_BLOCK_AFTER = 3
FORCED_HISTORY_CLOSE = "FORCED_HISTORY_GUARD"
FORCED_ENGINE_CLOSE = "FORCED_ENGINE_FAILURE"
CANONICAL_TRADE_KEYS = (
    "trade_id", "book_id", "underlying", "side", "atm_strike", "opened_ts", "closed_ts", "entry", "exit",
    "qty", "lots", "exit_reason", "gross_pnl_inr", "charges_inr", "realized_pnl_inr", "filled",
)

# Block kinds. Sticky blocks stay on for the rest of the session once opened.
KILL_SWITCH = "KILL_SWITCH"
MTM_HALT = "MTM_HALT"
HALT_FILE_CORRUPT = "HALT_FILE_CORRUPT"
FOUNDER_STATE_UNREADABLE = "FOUNDER_STATE_UNREADABLE"
OVERRIDE_LOG_UNREADABLE = "OVERRIDE_LOG_UNREADABLE"
PARAMS_UNREADABLE = "PARAMS_UNREADABLE"
RISK_CONFIG_UNREADABLE = "RISK_CONFIG_UNREADABLE"
DATA_ROOT_UNWRITABLE = "DATA_ROOT_UNWRITABLE"
HISTORY_REWRITE = "HISTORY_REWRITE"  # legacy name, kept for registries written by earlier builds
HISTORY_UNRECONCILABLE = "HISTORY_UNRECONCILABLE"  # CRITICAL + blocks entries
HISTORY_RECONCILED = "HISTORY_RECONCILED"  # WARN only: the booked truth was kept
ENGINE_FAILED = "ENGINE_FAILED"
BOOKED_LEDGER_UNREADABLE = "BOOKED_LEDGER_UNREADABLE"
BLOCK_REGISTRY_UNREADABLE = "BLOCK_REGISTRY_UNREADABLE"
FROZEN_PRIMARY_DAMAGED = "FROZEN_PARAMS_PRIMARY_DAMAGED"  # reported, not blocking (the backup is intact)
STICKY = frozenset({MTM_HALT, PARAMS_UNREADABLE, HISTORY_REWRITE, HISTORY_UNRECONCILABLE, ENGINE_FAILED, BOOKED_LEDGER_UNREADABLE,
                    BLOCK_REGISTRY_UNREADABLE})


def session_start_ts(day: str) -> float:
    y, m, d = (int(p) for p in day.split("-"))
    return datetime(y, m, d, tzinfo=IST).timestamp()


def canonical_trade(row: dict[str, Any]) -> dict[str, Any]:
    """The fields that make a booked trade what it is. JSON round-trip normalises number types."""
    return json.loads(json.dumps({k: row.get(k) for k in CANONICAL_TRADE_KEYS}, default=str))


# ------------------------------------------------------------------ blocks

# Registry state that could not be written; shared by every cycle in this process.
_UNSAVED_BLOCKS: dict[str, list[dict[str, Any]]] = {}


class BlockRegistry:
    """Entry-block intervals for one session, persisted in ``live_blocks/<day>.json``.

    A condition opens an interval at the moment the live loop first sees it and closes it when
    the condition clears (sticky kinds never close). Replays block entries with
    ``from <= tick.ts < until``, so re-running the day reproduces every earlier trade.
    """

    def __init__(self, root: Path, day: str, *, alerts: AlertSink, clock: Callable[[], datetime] = wall_clock) -> None:
        self.path = Path(root) / BLOCKS_REL / f"{day}.json"
        self.day, self.alerts, self.clock = day, alerts, clock
        self.rows: list[dict[str, Any]] = []
        try:
            blob = json.loads(self.path.read_text(encoding="utf-8"))
            rows = blob.get("intervals") if isinstance(blob, dict) else None
            if not isinstance(rows, list) or not all(isinstance(r, dict) and "kind" in r and "from" in r for r in rows):
                raise ValueError("intervals is not a list of blocks")
            self.rows = [dict(r) for r in rows]
        except FileNotFoundError:
            self.rows = list(_UNSAVED_BLOCKS.get(str(self.path), []))
        except (OSError, ValueError) as exc:
            # Past intervals are lost: block from now for the rest of the session. Re-derived entries
            # that a lost interval had blocked are caught by the booked-trade guard, never booked.
            stamp = self.clock().strftime("%H%M%S")
            try:
                os.replace(self.path, self.path.with_name(f"{self.path.name}.corrupt.{stamp}"))
            except OSError:
                pass
            self.rows = [{"kind": BLOCK_REGISTRY_UNREADABLE, "from": self.clock().timestamp(), "until": None,
                          "why": f"block registry unreadable ({type(exc).__name__}: {exc})"}]
            self._alert(self.rows[0], 0)
            self._save()

    def _open(self, kind: str) -> Optional[dict[str, Any]]:
        return next((r for r in self.rows if r["kind"] == kind and r.get("until") is None), None)

    def _alert(self, row: dict[str, Any], n: int) -> None:
        since = datetime.fromtimestamp(float(row["from"]), IST).isoformat(timespec="seconds")
        self.alerts.emit(session=self.day, check="entry_block", kind=f"{row['kind']}#{n}", ts=float(row["from"]),
                         message=f"New paper entries blocked from {since}: {row.get('why') or row['kind']}")

    def update(self, present: dict[str, tuple[Optional[float], str]], now_ts: float) -> None:
        changed = False
        for kind, (from_ts, why) in present.items():
            if self._open(kind) is None:
                row = {"kind": kind, "from": float(from_ts if from_ts is not None else now_ts), "until": None, "why": why}
                self.rows.append(row)
                self._alert(row, sum(1 for r in self.rows if r["kind"] == kind))
                changed = True
        for row in self.rows:
            if row.get("until") is None and row["kind"] not in STICKY and row["kind"] not in present:
                row["until"] = float(now_ts)
                changed = True
        if changed:
            self._save()

    def add_sticky(self, kind: str, from_ts: float, why: str) -> None:
        """Open a sticky block (if not already open) without touching the other intervals."""
        if self._open(kind) is None:
            row = {"kind": kind, "from": float(from_ts), "until": None, "why": why}
            self.rows.append(row)
            self._alert(row, sum(1 for r in self.rows if r["kind"] == kind))
            self._save()

    def _save(self) -> None:
        try:
            atomic_write_json(self.path, {"session": self.day, "intervals": self.rows}, indent=1)
        except OSError:
            _UNSAVED_BLOCKS[str(self.path)] = list(self.rows)
            return
        _UNSAVED_BLOCKS.pop(str(self.path), None)

    def intervals(self) -> list[tuple[str, float, Optional[float]]]:
        return [(r["kind"], float(r["from"]), None if r.get("until") is None else float(r["until"])) for r in self.rows]


# ------------------------------------------------------------------ frozen session inputs


def frozen_params_path(root: Path, day: str) -> Path:
    return Path(root) / FROZEN_REL / f"{day}.json"


def frozen_risk_path(root: Path, day: str) -> Path:
    return Path(root) / FROZEN_REL / f"{day}.risk.json"


def _read_snapshot(path: Path) -> Optional[dict[str, Any]]:
    try:
        blob = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        raise ValueError(f"{path}: {exc}") from exc
    if not isinstance(blob, dict) or not isinstance(blob.get("params"), dict):
        raise ValueError(f"{path}: not a frozen params snapshot")
    return blob


def read_frozen_params(root: Path, day: Optional[str]) -> Optional[dict[str, Any]]:
    """The session's frozen params, None if the session was never frozen. Raises ValueError if corrupt.

    Written once with a ``.bak`` twin; a damaged primary falls back to the twin.
    """
    if not day:
        return None
    path = frozen_params_path(root, day)
    try:
        return _read_snapshot(path)
    except ValueError as exc:
        backup = _read_snapshot(path.with_name(path.name + ".bak"))
        if backup is None:
            raise exc
        return backup


def write_frozen_params(root: Path, day: str, snap: dict[str, Any]) -> None:
    path = frozen_params_path(root, day)
    atomic_write_json(path, snap, indent=1)
    atomic_write_json(path.with_name(path.name + ".bak"), snap, indent=1)


def _strict_params(root: Path) -> tuple[dict[str, Any], Optional[str]]:
    """Session params as the engine loads them, plus a problem string if the file is unreadable."""
    from desk_ml.paper_scalp import PAPER_PARAMS_NAME, load_paper_params

    path = Path(root) / "data" / "recon" / PAPER_PARAMS_NAME
    problem = None
    if path.exists():
        try:
            if not isinstance(json.loads(path.read_text(encoding="utf-8")), dict):
                problem = "params file is not a JSON object"
        except (OSError, ValueError) as exc:
            problem = f"params file unreadable ({type(exc).__name__})"
    return load_paper_params(Path(root)), problem


def freeze_session(
    root: Path, day: str, *, clock: Callable[[], datetime]
) -> tuple[dict[str, Any], Optional[Path], dict[str, tuple[Optional[float], str]]]:
    """(frozen params incl. lot sizes, frozen risk limits path or None, blocking conditions)."""
    from desk_ml.event_path import resolve_risk_config
    from desk_ml.paper_lots import resolve_lot_size

    present: dict[str, tuple[Optional[float], str]] = {}
    now = clock().timestamp()
    try:
        snap = read_frozen_params(root, day)
    except ValueError as exc:
        snap = None
        present[PARAMS_UNREADABLE] = (None, f"frozen params unreadable: {exc}")
        good = _last_good(root).get("frozen_params")
        if isinstance(good, dict) and good.get("session") == day and isinstance(good.get("params"), dict):
            snap = good  # both copies damaged: keep the params the session has been running on
    if snap is not None and PARAMS_UNREADABLE not in present:
        try:
            _read_snapshot(frozen_params_path(root, day))
        except ValueError as exc:
            present[FROZEN_PRIMARY_DAMAGED] = (None, f"frozen params primary unreadable, running on its backup: {exc}")
    if snap is None and PARAMS_UNREADABLE not in present:
        params, problem = _strict_params(root)
        lots = {}
        for und in ("NIFTY", "BANKNIFTY", "SENSEX"):
            lot, src = resolve_lot_size(und, root=Path(root))
            lots[und] = [lot, src]
        snap = {"session": day, "frozen_ts": now, "params": params, "lot_sizes": lots,
                "source": "defaults_params_unreadable" if problem else "params_file"}
        if problem:
            present[PARAMS_UNREADABLE] = (now, problem)
        write_frozen_params(root, day, snap)
    elif snap is not None and snap.get("source") == "defaults_params_unreadable":
        present[PARAMS_UNREADABLE] = (float(snap.get("frozen_ts") or now), "session frozen on default params")
    if snap is not None and PARAMS_UNREADABLE not in present:
        _remember(root, "frozen_params", snap)
    params = dict((snap or {}).get("params") or {})
    if snap and snap.get("lot_sizes"):
        params["_lot_sizes"] = {k: tuple(v) for k, v in snap["lot_sizes"].items()}

    risk_path = frozen_risk_path(root, day)
    if not risk_path.exists():
        from risk_engine import load_limits

        live_cfg, _explicit = resolve_risk_config(live_session=True, root=Path(root))
        try:
            cfg = load_limits(live_cfg)
        except Exception as exc:  # noqa: BLE001 — entries blocked until a good file can be frozen
            present[RISK_CONFIG_UNREADABLE] = (None, f"{live_cfg.name} unreadable ({type(exc).__name__}: {exc})")
            return params, None, present
        # The kill switch stays live (a time-bounded block), not frozen.
        cfg = {**cfg, "kill_switch": False, "kill_switch_file": None, "_frozen_from": str(live_cfg), "_frozen_ts": now}
        atomic_write_json(risk_path, cfg, indent=1)
    return params, risk_path, present


# ------------------------------------------------------------------ control inputs


def kill_switch_on(root: Path) -> tuple[bool, str]:
    """Kill flag in the live risk yaml, or the kill file (relative to the data root). Errors = ON."""
    from desk_ml.event_path import resolve_risk_config

    live_cfg, _explicit = resolve_risk_config(live_session=True, root=Path(root))
    try:
        import yaml

        cfg = yaml.safe_load(Path(live_cfg).read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            raise ValueError("not a mapping")
    except Exception as exc:  # noqa: BLE001 — cannot read the kill flag: fail closed
        return True, f"{Path(live_cfg).name} unreadable, kill state unknown ({type(exc).__name__})"
    if cfg.get("kill_switch"):
        return True, "kill_switch: true in the risk config"
    raw = cfg.get("kill_switch_file")
    if raw:
        path = Path(str(raw))
        path = path if path.is_absolute() else Path(root) / path
        try:
            os.stat(path)
            return True, f"kill file present: {path}"
        except FileNotFoundError:
            pass
        except OSError as exc:
            return True, f"kill file state unknown ({type(exc).__name__}): {path}"
    return False, ""


def halt_condition(root: Path, day: str) -> dict[str, tuple[Optional[float], str]]:
    """The desk's persisted MTM halt (read-only here). A corrupt file blocks from first sight."""
    path = Path(root) / HALT_REL
    try:
        os.lstat(path)
        blob = json.loads(path.read_bytes().decode("utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as exc:
        return {HALT_FILE_CORRUPT: (None, f"halt file unreadable ({type(exc).__name__})")}
    if not isinstance(blob, dict) or not isinstance(blob.get("session"), str):
        return {HALT_FILE_CORRUPT: (None, "halt file is not a halt state")}
    if blob["session"] != day:
        return {}
    try:
        return {MTM_HALT: (float(blob["halt_ts"]), str(blob.get("reason") or "MTM halt"))}
    except (KeyError, TypeError, ValueError):
        return {HALT_FILE_CORRUPT: (None, "halt file has no halt_ts for this session")}


LAST_GOOD_REL = Path("data") / "recon" / "live_inputs_last_good.json"


def _last_good(root: Path) -> dict[str, Any]:
    try:
        blob = json.loads((Path(root) / LAST_GOOD_REL).read_text(encoding="utf-8"))
        return blob if isinstance(blob, dict) else {}
    except (OSError, ValueError):
        return {}


def _remember(root: Path, key: str, value: Any) -> None:
    good = _last_good(root)
    if good.get(key) == value:
        return
    try:
        atomic_write_json(Path(root) / LAST_GOOD_REL, {**good, key: value})
    except OSError:
        pass


def ingest_controls(
    root: Path, day: str, now_ts: float
) -> tuple[dict[str, tuple[Optional[float], str]], dict[str, Any]]:
    """(blocking conditions, replay inputs). Inputs are the founder and override rows the replay
    uses. If a log turns unreadable the replay keeps the last good rows (so everything before
    the damage re-derives identically) and new entries are blocked from first sight."""
    from desk_ml import founder_session, overrides

    root = Path(root)
    present: dict[str, tuple[Optional[float], str]] = {}
    good = _last_good(root)
    inputs: dict[str, Any] = {}
    try:
        founder_session.ingest_view_edits(root, ts=now_ts)
        inputs["founder_rows"] = founder_session.read_commands(root)
    except (founder_session.FounderStateError, OSError, ValueError) as exc:
        present[FOUNDER_STATE_UNREADABLE] = (None, str(exc))
        inputs["founder_rows"] = good.get("founder_rows", "unknown")
    try:
        overrides.ingest_legacy(root, ts=now_ts)
        inputs["override_rows"] = overrides.read_overrides(root)
    except (OSError, ValueError) as exc:
        present[OVERRIDE_LOG_UNREADABLE] = (None, str(exc))
        inputs["override_rows"] = good.get("override_rows", [])
    fresh = {k: inputs[k] for k in ("founder_rows", "override_rows") if k in inputs and inputs[k] != "unknown"}
    if FOUNDER_STATE_UNREADABLE not in present and OVERRIDE_LOG_UNREADABLE not in present:
        for key, value in fresh.items():
            _remember(root, key, value)
    on, why = kill_switch_on(root)
    if on:
        present[KILL_SWITCH] = (None, why)
    present.update(halt_condition(root, day))
    return present, inputs


# ------------------------------------------------------------------ heartbeat


def heartbeat_path(root: Path) -> Path:
    return Path(root) / HEARTBEAT_REL


def read_heartbeat(root: Path) -> dict[str, Any]:
    try:
        blob = json.loads(heartbeat_path(root).read_text(encoding="utf-8"))
        return blob if isinstance(blob, dict) else {}
    except (OSError, ValueError):
        return {}


def beat(root: Path, **fields_: Any) -> dict[str, Any]:
    """Merge fields into the heartbeat. Never raises (the heartbeat going stale is the signal)."""
    hb = {**read_heartbeat(root), **fields_, "pid": os.getpid()}
    try:
        atomic_write_json(heartbeat_path(root), hb, indent=1)
    except OSError:
        pass
    return hb


def loop_beat(root: Path, *, clock: Callable[[], datetime] = wall_clock) -> None:
    """Loop iteration started (the supervisor's hang signal). Not a claim that trading works."""
    now = clock()
    beat(root, last_loop_epoch=now.timestamp(), last_loop_ist=now.isoformat(timespec="seconds"))


def engine_state(root: Path, now: datetime) -> dict[str, Any]:
    hb = read_heartbeat(root)
    return {
        "alive": bool(hb.get("last_ok_epoch")) and not int(hb.get("consecutive_failures") or 0),
        "engine_last_ok_ist": hb.get("last_ok_ist"),
        "engine_last_ok_epoch": hb.get("last_ok_epoch"),
        "engine_consecutive_failures": int(hb.get("consecutive_failures") or 0),
        "engine_error": hb.get("last_error") if int(hb.get("consecutive_failures") or 0) else None,
        "beat_ist": now.isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------ booked-trade guard


def booked_path(root: Path, day: str) -> Path:
    return Path(root) / BOOKED_REL / f"{day}.jsonl"


def booked_state_path(root: Path, day: str) -> Path:
    return Path(root) / BOOKED_REL / f"{day}.state.json"


def read_booked(root: Path, day: str) -> dict[str, dict[str, Any]]:
    rows = read_jsonl(booked_path(root, day)) or []
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        out.setdefault(str(row.get("trade_id")), row)
    return out


def booked_quote(pos: Any, ticks: Sequence[Any]) -> tuple[float, dict[str, Any]]:
    """Exit price for a forced or guard close: the ticket's BOOKED strike and side, never another strike.

    Same rule as the SOD mark-to-market (``quote_for_side(strike=booked, itm_only=True)``): a wing
    cell for that strike, or the tape's ITM leg only when it IS that strike. Walks back to the last
    tick that quoted it (``stale``), then the ticket's own last mark, then its entry (both stale).
    """
    from desk_ml.paper_scalp import quote_for_side

    if pos.atm_strike is not None:
        for back, tick in enumerate(reversed(list(ticks))):
            if int(tick.ts) < int(pos.opened_ts):
                break
            ltp, _low, src = quote_for_side(tick, pos.side, strike=float(pos.atm_strike), itm_only=True)
            if ltp is not None and (src.startswith("STRIKE_") or src.startswith("ITM")):
                return float(ltp), {"quote_src": src, "quote_ts": int(tick.ts), "quote_stale": back > 0}
    if pos.last_ltp is not None:
        return float(pos.last_ltp), {"quote_src": "LAST_MARK_BOOKED_STRIKE", "quote_stale": True}
    return float(pos.entry), {"quote_src": "ENTRY_PRINT", "quote_stale": True}


def _snap_strike_quote(snap: dict[str, Any], strike: float, side: str) -> Optional[float]:
    """The booked strike's price in one raw tape snap (wing cell or a matching ITM leg), else None."""
    wings = snap.get("wing_quotes") if isinstance(snap.get("wing_quotes"), dict) else {}
    key = "ce" if side == "CE" else "pe"
    cell = wings.get(str(int(strike))) or wings.get(str(strike)) or wings.get(f"{strike:.1f}")
    candidates = [cell.get(key)] if isinstance(cell, dict) else []
    leg_strike = snap.get(f"itm_{key}_strike")
    try:
        if leg_strike is not None and abs(float(leg_strike) - float(strike)) < 1e-6:
            candidates.append(snap.get(f"itm_{key}_ltp"))
    except (TypeError, ValueError):
        pass
    for raw in candidates:
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val == val and val > 0 and val != float("inf"):
            return val
    return None


def booked_quote_from_tape(root: Path, day: str, pos: Any) -> tuple[float, dict[str, Any], int]:
    """``booked_quote`` on the day's tape when the engine cannot run: (price, meta, quote ts)."""
    try:
        from desk_ml.tape import load_dual_tape_triples

        ticks, _meta = load_dual_tape_triples(str(pos.underlying), root=Path(root), session_ist_date=day, strict=True)
        if ticks:
            px, meta = booked_quote(pos, ticks)
            return px, meta, int(meta.get("quote_ts") or ticks[-1].ts)
    except Exception:  # noqa: BLE001 — the loader may be what is failing; read the raw tape
        pass
    from desk_ml.tape import dual_tape_dir, parse_ts

    und, latest = str(pos.underlying).upper(), None
    try:
        lines = (dual_tape_dir(Path(root)) / f"{day}.jsonl").read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    for line in reversed(lines):
        try:
            blob = json.loads(line)
            ts = int(parse_ts(blob.get("as_of_ist")))
        except (ValueError, TypeError, AttributeError):
            continue
        for snap in blob.get("underlyings") or []:
            if not isinstance(snap, dict) or str(snap.get("underlying") or "").upper() != und:
                continue
            latest = ts if latest is None else latest
            px = _snap_strike_quote(snap, float(pos.atm_strike), pos.side) if pos.atm_strike is not None else None
            if px is not None:
                return px, {"quote_src": "RAW_TAPE_BOOKED_STRIKE", "quote_ts": ts, "quote_stale": ts != latest}, ts
        if ts < int(pos.opened_ts):
            break
    px, meta = booked_quote(pos, [])
    return px, meta, int(latest or pos.last_updated_ts or pos.opened_ts)


def read_booked_state(root: Path, day: str) -> dict[str, Any]:
    """{cutoff_ts, open} saved by the previous cycle; {} if none. Raises ValueError if unreadable."""
    try:
        state = json.loads(booked_state_path(root, day).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise ValueError(str(exc)) from exc
    if not isinstance(state, dict):
        raise ValueError("booked state is not an object")
    return state


class Pins:
    """Booked open tickets carried from the previous cycle into this replay.

    A ticket that was open at the previous cycle's cut-off stays the same ticket: from its booked
    open time it holds its slot (frozen, so other entries cannot take it), and at the first tick
    after the cut-off its saved state replaces whatever the re-derivation produced, so the engine
    manages it at its booked strike to its own exit. With a stable replay this changes nothing.
    """

    def __init__(self, engine: Any, ctx: ReplayContext) -> None:
        self.engine = engine
        self.saved = dict(ctx.pinned_open or {})
        self.cut = {str(k).upper(): int(v) for k, v in (ctx.pin_cutoffs or {}).items()}
        self.restored: set[str] = set()
        self.notes: list[str] = []
        engine.pinned_until = {}

    def _pos(self, tid: str) -> Any:
        from desk_ml.paper_scalp import OpenPaper

        known = {f.name for f in fields(OpenPaper)}
        return OpenPaper(**{k: v for k, v in self.saved[tid].items() if k in known})

    def _mine(self, und: str) -> list[str]:
        return [t for t, d in self.saved.items() if t not in self.restored and str(d.get("underlying")).upper() == und]

    def _slot(self, tid: str) -> tuple[str, str]:
        d = self.saved[tid]
        return str(d["book_id"]), str(d["underlying"]).upper()

    def _take_slot(self, tid: str) -> None:
        key = self._slot(tid)
        other = self.engine.opens.get(key)
        if other is not None and str(other.trade_id) != tid:
            self.engine.opens.pop(key)
            self.notes.append(f"replay opened {other.trade_id} while booked ticket {tid} was open; dropped it")

    def after_tick(self, und: str, ts: int) -> None:
        cut = self.cut.get(und)
        if cut is None or ts > cut:
            return
        for tid in self._mine(und):
            if ts < int(self.saved[tid]["opened_ts"]):
                continue
            if any(str(p.trade_id) == tid for p in self.engine.opens.values()):
                continue
            self._take_slot(tid)
            self.engine.opens[self._slot(tid)] = self._pos(tid)
            self.engine.pinned_until[tid] = cut
            hook = getattr(self.engine, "_pin_hook", None)
            if hook is not None:
                hook(self.engine.opens[self._slot(tid)])
            self.notes.append(f"booked open ticket {tid} was not re-derived; carried at its booked state")

    def _restore(self, tid: str) -> None:
        drifted = [r for r in self.engine.closed if str(r.get("trade_id")) == tid]
        if drifted:
            self.engine.closed = [r for r in self.engine.closed if str(r.get("trade_id")) != tid]
            for r in drifted:
                if r.get("realized_pnl_inr") is not None:
                    book = str(r.get("book_id"))
                    self.engine.equity[book] = self.engine.book_equity(book) - float(r["realized_pnl_inr"])
            self.notes.append(f"replay closed booked open ticket {tid} before the cut-off; kept it open")
        for key, p in list(self.engine.opens.items()):
            if str(p.trade_id) == tid:
                self.engine.opens.pop(key)
        self._take_slot(tid)
        self.engine.opens[self._slot(tid)] = self._pos(tid)
        self.engine.pinned_until.pop(tid, None)
        self.restored.add(tid)

    def before_tick(self, und: str, ts: int) -> None:
        cut = self.cut.get(und)
        if cut is not None and ts > cut:
            for tid in self._mine(und):
                self._restore(tid)

    def finish(self, und: str) -> None:
        """No tick after the cut-off for this index this cycle: keep the booked state as it was."""
        for tid in self._mine(und):
            self._restore(tid)


def guard_history(engine: Any, loaded: dict[str, list[Any]], ctx: ReplayContext) -> dict[str, Any]:
    """Make the replay agree with what earlier cycles booked. Mutates engine.closed / engine.opens.

    Returns ``{"status", "reconciled", "unreconcilable", "new"}``:
    - reconciled (a booked row kept as the truth, a re-derived ticket that was never booked dropped,
      a booked open ticket carried by ``Pins``): the board shows the booked truth, WARN alert;
    - unreconcilable (a booked open ticket with no saved state to carry): closed at its booked
      strike's price, CRITICAL alert, and the caller blocks new entries.
    """
    from desk_ml.paper_scalp import OpenPaper, _close

    root, day = Path(ctx.root), str(ctx.session_ist_date)
    try:
        booked = read_booked(root, day)
        state = read_booked_state(root, day)
    except (OSError, ValueError) as exc:
        return {"status": BOOKED_LEDGER_UNREADABLE, "reconciled": [], "unreconcilable": [f"booked file unreadable: {exc}"],
                "problems": [f"booked file unreadable: {exc}"], "new": []}
    cutoffs = {str(k): int(v) for k, v in (state.get("cutoff_ts") or {}).items()}
    prev_open: dict[str, dict[str, Any]] = dict(state.get("open") or {})

    def before_cutoff(und: str, ts: int) -> bool:
        return und in cutoffs and int(ts) <= cutoffs[und]

    pins = getattr(engine, "_pins", None)
    reconciled: list[str] = list(pins.notes) if pins is not None else []
    unreconcilable: list[str] = []
    replay = {str(r.get("trade_id")): r for r in engine.closed}
    for tid, row in booked.items():
        cur = replay.get(tid)
        if row.get("exit_reason") == FORCED_ENGINE_CLOSE:
            continue  # our own fail-safe close while the engine was down: expected to differ
        if cur is None:
            reconciled.append(f"booked trade {tid} missing from the replay; booked row kept")
        elif canonical_trade(cur) != canonical_trade(row):
            diff = {k: (row.get(k), cur.get(k)) for k in CANONICAL_TRADE_KEYS if canonical_trade(row)[k] != canonical_trade(cur)[k]}
            reconciled.append(f"booked trade {tid} re-derived differently {diff}; booked row kept")
    new_rows: list[dict[str, Any]] = []
    vanished: dict[str, dict[str, Any]] = {}
    for row in engine.closed:
        tid = str(row.get("trade_id"))
        if tid in booked:
            continue
        und = str(row.get("underlying") or "").upper()
        if tid not in prev_open and before_cutoff(und, int(row.get("opened_ts") or 0)):
            reconciled.append(f"trade {tid} appeared before the previous cycle's cut-off; not booked")
            continue
        if tid in prev_open and before_cutoff(und, int(row.get("closed_ts") or 0)):
            unreconcilable.append(f"booked open ticket {tid} now closes before the previous cycle's cut-off")
            vanished[tid] = prev_open[tid]
            continue
        new_rows.append(row)
    open_ids = set()
    for key, pos in list(engine.opens.items()):
        tid = str(pos.trade_id)
        und = str(pos.underlying).upper()
        if tid in booked:
            engine.opens.pop(key)
            if booked[tid].get("exit_reason") != FORCED_ENGINE_CLOSE:
                reconciled.append(f"booked-closed trade {tid} is open again in the replay; kept closed")
        elif tid not in prev_open and before_cutoff(und, int(pos.opened_ts)):
            engine.opens.pop(key)
            reconciled.append(f"open trade {tid} appeared before the previous cycle's cut-off; dropped")
        else:
            open_ids.add(tid)
    closed_ids = {str(r.get("trade_id")) for r in new_rows}
    for tid, blob in prev_open.items():
        if tid not in booked and tid not in closed_ids and tid not in open_ids and tid not in vanished:
            unreconcilable.append(f"booked open ticket {tid} vanished and could not be carried")
            vanished[tid] = blob
    known = {f.name for f in fields(OpenPaper)}
    for tid, blob in vanished.items():
        pos = OpenPaper(**{k: v for k, v in blob.items() if k in known})
        ticks = loaded.get(str(pos.underlying).upper()) or []
        px, meta = booked_quote(pos, ticks)
        ts = max(int(ticks[-1].ts) if ticks else int(pos.last_updated_ts or pos.opened_ts), int(pos.opened_ts))
        n = len(engine.closed)
        _close(engine, pos, ltp=px, ts=ts, reason=FORCED_HISTORY_CLOSE, root=None)
        for row in engine.closed[n:]:
            row.update(meta)
        new_rows.extend(engine.closed[n:])
    problems = reconciled + unreconcilable
    if problems or any(r.get("exit_reason") == FORCED_ENGINE_CLOSE for r in booked.values()):
        engine.closed = list(booked.values()) + new_rows
    new_cutoffs = dict(cutoffs)
    for und, ticks in loaded.items():
        if ticks:
            new_cutoffs[str(und).upper()] = max(new_cutoffs.get(str(und).upper(), 0), int(ticks[-1].ts))
    try:
        for row in new_rows:
            append_line(booked_path(root, day), json.dumps(row, default=str))
        atomic_write_json(booked_state_path(root, day), {
            "cutoff_ts": new_cutoffs,
            "open": {str(p.trade_id): asdict(p) for p in engine.opens.values()},
        }, indent=None)
    except OSError as exc:
        # Nothing new is marked booked; the next cycle retries these rows.
        return {"status": "UNSAVED", "reconciled": reconciled, "unreconcilable": unreconcilable, "problems": problems,
                "new": [], "error": f"{type(exc).__name__}: {exc}"}
    status = HISTORY_UNRECONCILABLE if unreconcilable else (HISTORY_RECONCILED if reconciled else "OK")
    return {"status": status, "reconciled": reconciled, "unreconcilable": unreconcilable, "problems": problems,
            "new": [str(r.get("trade_id")) for r in new_rows]}


def failsafe_flatten(root: Path, day: str) -> list[str]:
    """The engine keeps failing with open tickets: close them at their BOOKED strike's price and book them.

    Same rule as the desk's MTM fail-safe (stops cannot run, so do not stay exposed). The closes
    are appended to the booked file, so the board keeps them after the engine recovers.
    """
    from desk_ml.paper_scalp import BookEngine, OpenPaper, _close

    state_path = booked_state_path(root, day)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    opens = dict(state.get("open") or {})
    if not opens:
        return []
    known = {f.name for f in fields(OpenPaper)}
    scratch = BookEngine()
    closed: list[str] = []
    for tid, blob in list(opens.items()):
        pos = OpenPaper(**{k: v for k, v in blob.items() if k in known})
        px, meta, ts = booked_quote_from_tape(root, day, pos)
        n = len(scratch.closed)
        _close(scratch, pos, ltp=px, ts=max(int(ts), int(pos.opened_ts)), reason=FORCED_ENGINE_CLOSE, root=None)
        for row in scratch.closed[n:]:
            row.update(meta)
            append_line(booked_path(root, day), json.dumps(row, default=str))
        opens.pop(tid)
        closed.append(tid)
    atomic_write_json(state_path, {**state, "open": opens}, indent=None)
    return closed


# ------------------------------------------------------------------ the cycle


def _probe_writable(root: Path) -> Optional[str]:
    try:
        atomic_write_json(Path(root) / "data" / "recon" / ".write_probe", {"ok": True})
        return None
    except OSError as exc:
        return f"data root not writable ({type(exc).__name__}: {exc})"


def run_cycle(
    root: Path,
    *,
    underlyings: Sequence[str] = ("NIFTY", "BANKNIFTY", "SENSEX"),
    source: str = "dual-tape",
    clock: Callable[[], datetime] = wall_clock,
    session_ist_date: Optional[str] = None,
    replay_kw: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """One live cycle. Returns the published board. Records the failure and re-raises on error."""
    from desk_ml.paper_scalp import _append_mistakes, replay_paper_scalp, write_dashboard

    root = Path(root)
    now = clock()
    day = session_ist_date or now.date().isoformat()
    alerts = AlertSink(root, clock=clock)
    alerts.flush_pending()
    hb = read_heartbeat(root)
    unwritable: Optional[str] = None
    try:
        blocks = BlockRegistry(root, day, alerts=alerts, clock=clock)
        present: dict[str, tuple[Optional[float], str]] = {}
        unwritable = _probe_writable(root)
        if unwritable:
            present[DATA_ROOT_UNWRITABLE] = (None, unwritable)
        conditions, inputs = ingest_controls(root, day, now.timestamp())
        present.update(conditions)
        fails = int(hb.get("consecutive_failures") or 0)
        if hb.get("session") == day and fails >= ENGINE_FAIL_BLOCK_AFTER and int(hb.get("n_open") or 0) > 0:
            present[ENGINE_FAILED] = (float(hb.get("block_from_epoch") or now.timestamp()),
                                      f"engine failed {fails} cycles in a row with open tickets")
        params, risk_path, frozen_problems = freeze_session(root, day, clock=clock)
        present.update(frozen_problems)
        damaged = present.pop(FROZEN_PRIMARY_DAMAGED, None)
        if damaged:
            alerts.emit(session=day, check="frozen_params", kind="primary_damaged", ts=now.timestamp(),
                        severity="WARN", message=damaged[1])
        blocks.update(present, now.timestamp())
        try:
            carried = read_booked_state(root, day)
        except ValueError:
            carried = {}  # the guard reports the unreadable file and blocks entries
        ctx = ReplayContext(
            root=root, session_ist_date=day, live_loop=True, write=True, clock=clock, alerts=alerts,
            entry_blocks=tuple(blocks.intervals()), params=params, risk_config=risk_path,
            founder_rows=inputs.get("founder_rows"), override_rows=inputs.get("override_rows"),
            pinned_open=dict(carried.get("open") or {}), pin_cutoffs=dict(carried.get("cutoff_ts") or {}),
        )
        board = replay_paper_scalp(  # no model-log writes while the disk refuses them (already alerted)
            root=root, underlyings=tuple(underlyings), source=source, write=not unwritable, live_session=True,
            session_ist_date=day, live_loop=True, ctx=ctx, **dict(replay_kw or {}),
        )
        guard = board.get("history_guard") or {}
        if guard.get("status") in (HISTORY_UNRECONCILABLE, BOOKED_LEDGER_UNREADABLE):
            # Only a ticket the loop truly cannot carry blocks entries (one CRITICAL, via the block).
            blocks.add_sticky(guard["status"], now.timestamp(), "Booked tickets could not be reconciled: "
                              + "; ".join(guard.get("unreconcilable") or [])[:1500])
        if guard.get("reconciled"):
            alerts.emit(session=day, check="history_guard", kind=HISTORY_RECONCILED, ts=now.timestamp(), severity="WARN",
                        message="Replay drifted from booked trades; booked truth kept and open tickets carried: "
                        + "; ".join(guard["reconciled"])[:1500])
        bad = {u: int(((st or {}).get("tape") or {}).get("skipped_lines") or 0) for u, st in (board.get("steps") or {}).items()}
        if any(bad.values()):
            alerts.emit(session=day, check="tape", kind="corrupt_lines", ts=now.timestamp(), severity="WARN",
                        message=f"dual-tape has unreadable line(s) mid-file; skipped: {bad}")
        new_ids = set(guard.get("new") or [])
        _append_mistakes(root, [m for m in board.get("mistakes") or [] if str(m.get("trade_id")) in new_ids])
    except Exception as exc:
        fails = int(hb.get("consecutive_failures") or 0) + 1 if hb.get("session") == day else 1
        extra = {}
        if fails == ENGINE_FAIL_BLOCK_AFTER:
            extra["block_from_epoch"] = now.timestamp()
        beat(root, session=day, consecutive_failures=fails, last_error=f"{type(exc).__name__}: {exc}"[:500],
             last_fail_ist=now.isoformat(timespec="seconds"), last_cycle_epoch=now.timestamp(), **extra)
        alerts.emit(session=day, check="paper_engine", kind=f"cycle_failed:{type(exc).__name__}", ts=now.timestamp(),
                    message=f"paper engine cycle failed: {type(exc).__name__}: {exc}"[:1500])
        if fails >= ENGINE_FAIL_BLOCK_AFTER:
            try:
                forced = failsafe_flatten(root, day)
            except Exception as flat_exc:  # noqa: BLE001 — already failing; report, do not mask
                forced = []
                alerts.emit(session=day, check="paper_engine", kind="failsafe_flatten_failed", ts=now.timestamp(),
                            message=f"fail-safe flatten failed: {type(flat_exc).__name__}: {flat_exc}")
            if forced:
                alerts.emit(session=day, check="paper_engine", kind="failsafe_flatten", ts=now.timestamp(),
                            message=f"engine failed {fails} cycles with open tickets; closed at the last quote: {forced}")
        mark_dashboard_dead(root, clock=clock)
        raise
    hb = beat(root, session=day, consecutive_failures=0, last_error=None, last_ok_epoch=now.timestamp(),
              last_ok_ist=now.isoformat(timespec="seconds"), last_cycle_epoch=now.timestamp(),
              n_open=len(board.get("open_trades") or []), block_from_epoch=None)
    board["heartbeat"] = {**(board.get("heartbeat") or {}), **engine_state(root, now)}
    board["entry_blocks"] = [
        {"kind": k, "from_ist": datetime.fromtimestamp(f, IST).isoformat(timespec="seconds"),
         "until_ist": None if u is None else datetime.fromtimestamp(u, IST).isoformat(timespec="seconds")}
        for k, f, u in blocks.intervals()
    ]
    try:
        write_dashboard(board, root=root)
    except OSError as exc:
        if not unwritable:
            alerts.emit(session=day, check="paper_engine", kind=f"dashboard_write:{type(exc).__name__}",
                        message=f"dashboard not written ({exc}); engine state is in engine_heartbeat.json")
    return board


def mark_dashboard_dead(root: Path, *, clock: Callable[[], datetime] = wall_clock) -> None:
    """After a failed cycle the board on disk must stop claiming the engine is alive."""
    from desk_ml.paper_scalp import DASH_JSON_NAME

    path = Path(root) / "data" / "recon" / DASH_JSON_NAME
    try:
        board = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(board, dict):
            return
        board["heartbeat"] = {**(board.get("heartbeat") or {}), **engine_state(Path(root), clock())}
        atomic_write_json(path, board, indent=2)
    except (OSError, ValueError):
        pass

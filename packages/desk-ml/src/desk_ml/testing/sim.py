"""Fault-injection full-day simulations of the live paper loop, and the invariant checker.

``run_live_day`` emulates production: for each cycle cut-off it writes the dual-tape JSONL prefix
into a scratch root exactly as ``persist_tick`` would, applies the faults scheduled for that
cycle, and calls ``live_cycle.run_cycle`` (the same function ``dual_tape --paper-scalp`` calls),
flag off or flag on. A restart throws away every piece of process state. ``check`` returns
invariant violations (spec section 2.3); an empty list is a pass.

Paper only. Synthetic tapes only. Nothing outside the scratch root is written.
"""

from __future__ import annotations

import builtins
import contextlib
import errno
import io
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence

from desk_ml.features import Triple
from desk_ml.testing.canonical import LOT_SIZES, canonical_trade, tape_lines

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_CUTOFFS = ("09:45", "10:30", "11:15", "12:00", "12:45", "13:30", "14:15", "15:00", "15:30")
LIVE_MAX_LOTS = 25
LIVE_MAX_OPEN = 3
EXIT_REASONS_REQUIRED = True
REPLAY_KW = {"deny_model_signals": True, "nifty_cover_closed_1m": True}


def ts_at(day: str, hhmm: str) -> int:
    y, m, d = (int(p) for p in day.split("-"))
    hh, mm = (int(p) for p in hhmm.split(":")[:2])
    ss = int(hhmm.split(":")[2]) if hhmm.count(":") == 2 else 0
    return int(datetime(y, m, d, hh, mm, ss, tzinfo=IST).timestamp())


@dataclass
class Fault:
    """One scheduled fault. ``at``/``until`` are IST HH:MM on the simulated day.

    kinds: stall, feed_drop, chain_drop, half_line, corrupt_line, stale_quote, none_premium,
    dup_ooo, founder, override, params_change, corrupt, kill_on, kill_off, crash, restart,
    clock_skew, disk_full, broker_reject, broker_timeout.
    """

    kind: str
    at: str = "12:00"
    until: Optional[str] = None
    args: dict[str, Any] = field(default_factory=dict)


@dataclass
class SimResult:
    day: str
    flag: str
    root: Path
    cycles: list[dict[str, Any]] = field(default_factory=list)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    model_log: list[dict[str, Any]] = field(default_factory=list)
    blocks: list[dict[str, Any]] = field(default_factory=list)
    founder_rows: list[dict[str, Any]] = field(default_factory=list)
    faults: list[Fault] = field(default_factory=list)


# ------------------------------------------------------------------ process state


def simulate_restart() -> None:
    """A process restart: every in-memory cache and dedupe set is gone."""
    import desk_ml.live_cycle as lc
    import desk_ml.paper_lots as pl
    import desk_ml.reliability as rel

    rel._UNSAVED_STATE.clear()
    rel._PENDING_ALERTS.clear()
    lc._UNSAVED_BLOCKS.clear()
    pl._LOT_MEM.clear()
    try:
        import desk.executor as ex

        ex._LIVE_ALERTED.clear()
        ex._UNSAVED_HALTS.clear()
    except ImportError:
        pass


@contextlib.contextmanager
def _patched(obj: Any, name: str, value: Any) -> Iterator[None]:
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


@contextlib.contextmanager
def disk_full(root: Path) -> Iterator[None]:
    """ENOSPC for every write/append/replace under ``root/data`` (reads still work)."""
    real_open, real_replace = builtins.open, os.replace
    prefix = str(Path(root).resolve() / "data")

    def _hit(path: Any) -> bool:
        try:
            return str(Path(os.fspath(path)).resolve()).startswith(prefix)
        except TypeError:
            return False

    def fake_open(file: Any, mode: str = "r", *a: Any, **kw: Any) -> Any:
        if any(c in mode for c in "wax+") and _hit(file):
            raise OSError(errno.ENOSPC, "No space left on device (simulated)", str(file))
        return real_open(file, mode, *a, **kw)

    def fake_replace(src: Any, dst: Any, *a: Any, **kw: Any) -> None:
        if _hit(dst):
            raise OSError(errno.ENOSPC, "No space left on device (simulated)", str(dst))
        return real_replace(src, dst, *a, **kw)

    with _patched(builtins, "open", fake_open), _patched(io, "open", fake_open), _patched(os, "replace", fake_replace):
        yield


@contextlib.contextmanager
def broker_fault(kind: str, purpose: Optional[str]) -> Iterator[None]:
    """Paper broker refuses (``broker_reject``) or times out (``broker_timeout``) orders."""
    from brokers import OrderRefused
    from desk.paper import ClockedPaperBroker

    real = ClockedPaperBroker.place_order

    def fake(self: Any, intent: Any, decision: Any) -> Any:
        if purpose is None or intent.purpose == purpose:
            if kind == "broker_timeout":
                raise TimeoutError("broker did not answer (simulated)")
            raise OrderRefused("REJECTED by broker (simulated)")
        return real(self, intent, decision)

    with _patched(ClockedPaperBroker, "place_order", fake):
        yield


# ------------------------------------------------------------------ scratch root


def make_root(root: Path, *, day: str, founder: Sequence[str] = ("NIFTY", "BANKNIFTY", "SENSEX"),
              params: Optional[dict[str, Any]] = None) -> Path:
    """Scratch data root: founder log (START from ts=0), params, lot cache, risk config copies."""
    from desk_ml.founder_session import save_founder_book
    from desk_ml.persist import repo_root

    root = Path(root)
    recon = root / "data" / "recon"
    (recon / "paper_watch" / "DUAL-TAPE").mkdir(parents=True, exist_ok=True)
    save_founder_book(list(founder), root=root, ts=0.0)
    (recon / "ml_paper_session_params.json").write_text(json.dumps(params or {"stop_frac": 0.38, "scalp_hold_bars": 9}))
    (recon / "optidx_lot_cache.json").write_text(json.dumps({u: {"lot_size": n, "source": "sim"} for u, n in LOT_SIZES.items()}))
    cfg = root / "config"
    cfg.mkdir(parents=True, exist_ok=True)
    code = repo_root() / "config"
    (cfg / "risk_limits.yaml").write_text((code / "risk_limits.yaml").read_text())
    (cfg / "event_path.yaml").write_text(
        f"live_risk_config: {cfg / 'risk_limits.yaml'}\nreplay_risk_config: {code / 'risk_limits_replay.yaml'}\n"
    )
    return root


def _tape_for_cycle(lines: list[tuple[int, str]], cutoff: int, faults: Sequence[Fault], day: str, k: int) -> str:
    kept: list[str] = []
    for ts, line in lines:
        if ts > cutoff:
            break
        for f in faults:
            lo, hi = ts_at(day, f.at), ts_at(day, f.until or f.at)
            if f.kind == "stall" and lo <= ts < hi and cutoff < hi:
                line = ""  # not recorded yet; the recorder catches up later
            elif f.kind in ("feed_drop", "chain_drop") and lo <= ts < hi:
                blob = json.loads(line)
                if f.kind == "chain_drop":
                    line = ""
                else:
                    und = f.args.get("underlying", "NIFTY")
                    blob["underlyings"] = [s for s in blob["underlyings"] if s["underlying"] != und]
                    line = json.dumps(blob, separators=(",", ":")) if blob["underlyings"] else ""
            elif f.kind == "stale_quote" and lo <= ts < hi and line:
                blob = json.loads(line)
                for s in blob["underlyings"]:
                    s["itm_ce_ltp"] = f.args.get("px", 150.0)
                    s["itm_pe_ltp"] = f.args.get("px", 150.0)
                line = json.dumps(blob, separators=(",", ":"))
            elif f.kind == "none_premium" and lo <= ts < hi and line:
                blob = json.loads(line)
                for s in blob["underlyings"]:
                    s["itm_ce_ltp"] = None if ts % 2 else "NaN"
                line = json.dumps(blob, separators=(",", ":"))
        if line:
            kept.append(line)
    text = "\n".join(kept) + ("\n" if kept else "")
    for f in faults:
        lo, hi = ts_at(day, f.at), ts_at(day, f.until or f.at)
        if f.kind == "dup_ooo" and lo <= cutoff:
            extra = [ln for ts, ln in lines if lo <= ts < hi and ts <= cutoff]
            text += "".join(ln + "\n" for ln in reversed(extra))  # duplicates, out of order
        if f.kind == "corrupt_line" and lo <= cutoff:
            parts = text.split("\n")
            parts.insert(max(1, len(parts) // 2), '{"as_of_ist": "2026-09-10T11:00:00+05:30", "underly')
            text = "\n".join(parts)
        if f.kind == "half_line" and lo <= cutoff < hi and kept:
            text = text[: len(text) - 1 - len(kept[-1]) // 2]  # last line cut mid-JSON, no newline
    return text


def _corrupt(root: Path, target: str, how: str, day: str) -> None:
    recon = Path(root) / "data" / "recon"
    paths = {
        "founder_view": recon / "founder_trade_underlyings.json",
        "founder_log": recon / "founder_commands.jsonl",
        "override_log": recon / "human_overrides.jsonl",
        "halt": Path(root) / "data" / "desk" / "live_loop" / "mtm_halt.json",
        "params": recon / "ml_paper_session_params.json",
        "frozen_params": recon / "params_frozen" / f"{day}.json",
        "alert_state": Path(root) / "data" / "health" / "alert_state.json",
        "booked": recon / "paper_booked" / f"{day}.jsonl",
        "blocks": recon / "live_blocks" / f"{day}.json",
        "risk_yaml": Path(root) / "config" / "risk_limits.yaml",
    }
    path = paths[target]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_dir():
        return
    if how == "directory":
        if path.exists():
            path.unlink()
        path.mkdir()
        return
    if how == "permission":
        if not path.exists():
            path.write_text("{}")
        path.chmod(0)
        return
    data = {"empty": "", "truncated": '{"trade_underlyings": ["NIF', "list": "[1, 2, 3]\n", "garbage": "\x00\xff{"}[how]
    if target in ("founder_log", "override_log", "booked") and how == "truncated":
        data = '{"ts": 1, "underlying": "NIFTY"\n{"ts": 2}\n'  # a bad line mid-file
    path.write_text(data, encoding="utf-8", errors="surrogateescape")


# ------------------------------------------------------------------ the day


def run_live_day(
    root: Path,
    triples_by_und: dict[str, Sequence[Triple]],
    *,
    day: str,
    cutoffs: Sequence[str] = DEFAULT_CUTOFFS,
    faults: Sequence[Fault] = (),
    flag: str = "off",
) -> SimResult:
    import desk_ml.paper_scalp as ps
    from desk_ml.founder_session import set_index_trade
    from desk_ml.live_cycle import run_cycle

    root = Path(root)
    lines = tape_lines(triples_by_und)
    res = SimResult(day=day, flag=flag, root=root, faults=list(faults))
    tape_path = root / "data" / "recon" / "paper_watch" / "DUAL-TAPE" / f"{day}.jsonl"
    und = tuple(triples_by_und)
    simulate_restart()
    kw = dict(REPLAY_KW, use_event_bus=(flag == "on"))
    for k, hhmm in enumerate(cutoffs):
        cutoff = ts_at(day, hhmm)
        prev = ts_at(day, cutoffs[k - 1]) if k else 0
        due = [f for f in faults if prev < ts_at(day, f.at) <= cutoff]
        tape_path.write_text(_tape_for_cycle(lines, cutoff, faults, day, k), encoding="utf-8")
        skew = 0.0
        for f in faults:
            if f.kind == "clock_skew":
                skew = float(f.args.get("seconds", 0.0))
        for f in due:
            at = float(ts_at(day, f.at))
            if f.kind == "founder":
                set_index_trade(f.args["underlying"], f.args["action"], root=root, ts=at)
            elif f.kind == "override":
                row = res.cycles[-1]["open"] if res.cycles else []
                target = next((o for o in row if o["underlying"] == f.args.get("underlying", o["underlying"])), None)
                if target is not None:
                    ps.save_human_override({"action": "CANCEL", "trade_id": target["trade_id"],
                                            "underlying": target["underlying"], "side": target["side"]}, root=root, ts=at)
            elif f.kind == "params_change":
                (root / "data" / "recon" / "ml_paper_session_params.json").write_text(json.dumps(f.args["params"]))
            elif f.kind == "corrupt":
                _corrupt(root, f.args["target"], f.args.get("how", "truncated"), day)
            elif f.kind == "kill_on":
                (root / "data" / "ledger").mkdir(parents=True, exist_ok=True)
                (root / "data" / "ledger" / "KILL_SWITCH").write_text("")
            elif f.kind == "kill_off":
                (root / "data" / "ledger" / "KILL_SWITCH").unlink(missing_ok=True)
            elif f.kind == "restart":
                simulate_restart()
        clock_now = datetime.fromtimestamp(cutoff + 2 + skew, IST)
        active = [f for f in faults if ts_at(day, f.at) <= cutoff < ts_at(day, f.until or "23:59")]
        crash = any(f.kind == "crash" and ts_at(day, f.at) <= cutoff < ts_at(day, f.until or f.at) + 1 for f in faults)
        stack = contextlib.ExitStack()
        for f in active:
            if f.kind == "disk_full":
                stack.enter_context(disk_full(root))
            elif f.kind in ("broker_reject", "broker_timeout"):
                stack.enter_context(broker_fault(f.kind, f.args.get("purpose")))
        if crash:
            def boom(*_a: Any, **_k: Any) -> None:
                raise RuntimeError("engine crashed (simulated)")

            stack.enter_context(_patched(ps, "_replay_paper_scalp", boom))
        error, board = None, {}
        with stack:
            try:
                board = run_cycle(root, underlyings=und, source="dual-tape", clock=lambda: clock_now,
                                  session_ist_date=day, replay_kw=kw)
            except Exception as exc:  # noqa: BLE001 — recorded; the loop keeps going
                error = f"{type(exc).__name__}: {exc}"
        tape_cut = {}
        for u, tr in triples_by_und.items():
            seen = [int(t.ts) for t in tr if int(t.ts) <= cutoff]
            tape_cut[u] = max(seen) if seen else 0
        res.cycles.append({
            "k": k, "cutoff": cutoff, "hhmm": hhmm, "error": error, "tape_cut": tape_cut,
            "closed": [canonical_trade(r) for r in board.get("closed_trades") or []],
            "open": [{"trade_id": r.get("trade_id"), "underlying": r.get("underlying"), "side": r.get("side"),
                      "opened_ts": r.get("opened_ts"), "lots": r.get("lots"), "filled": r.get("filled")}
                     for r in board.get("open_trades") or []],
            "overall_pnl_inr": board.get("overall_pnl_inr"),
            "event_bus": {k2: (board.get("event_bus") or {}).get(k2) for k2 in ("ledger_trades_closed", "handler_errors")},
            "guard": board.get("history_guard"),
            "heartbeat": dict(board.get("heartbeat") or {}),
        })
    res.alerts = _read_lines(root / "data" / "health" / "alerts.jsonl")
    res.model_log = _read_lines(root / "data" / "recon" / "model_log" / f"{day}.jsonl")
    try:
        res.blocks = json.loads((root / "data" / "recon" / "live_blocks" / f"{day}.json").read_text()).get("intervals") or []
    except (OSError, ValueError):
        res.blocks = []
    try:
        from desk_ml.founder_session import read_commands

        res.founder_rows = read_commands(root) or []
    except Exception:  # noqa: BLE001 — a corrupt log is a scenario, not a harness error
        res.founder_rows = []
    return res


def _read_lines(path: Path) -> list[dict[str, Any]]:
    out = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


# ------------------------------------------------------------------ invariants


@dataclass
class Violation:
    invariant: str
    detail: str


def _intervals(res: SimResult) -> list[tuple[str, float, float]]:
    return [(b["kind"], float(b["from"]), float(b["until"]) if b.get("until") is not None else float("inf")) for b in res.blocks]


def check(res: SimResult, *, control: bool = False, expect_block_from: Optional[int] = None) -> list[Violation]:
    """Invariants I1-I10 over every cycle and at end of day. Empty list = pass."""
    out: list[Violation] = []
    good = [c for c in res.cycles if c["error"] is None]
    final = good[-1] if good else {"closed": [], "open": []}
    closed_final = {r["trade_id"]: r for r in final["closed"]}

    # I1 limits (live paper tier): lots per trade and concurrent filled positions.
    trades = [r for r in final["closed"] if r["filled"]] + [o for o in final["open"] if o.get("filled")]
    for r in trades:
        if int(r.get("lots") or 0) > LIVE_MAX_LOTS:
            out.append(Violation("I1", f"{r['trade_id']} has {r['lots']} lots > {LIVE_MAX_LOTS}"))
    spans = [(int(r["opened_ts"]), int(r.get("closed_ts") or 2**40)) for r in trades]
    for t0, _t1 in spans:
        n = sum(1 for a, b in spans if a <= t0 < b)
        if n > LIVE_MAX_OPEN:
            out.append(Violation("I1", f"{n} positions open at {t0} > {LIVE_MAX_OPEN}"))
            break

    # I2 nothing unmanaged at the end of the session.
    if res.cycles and res.cycles[-1]["cutoff"] >= ts_at(res.day, "15:20") and final["open"]:
        out.append(Violation("I2", f"open at session end: {[o['trade_id'] for o in final['open']]}"))
    if good and good[-1] is not res.cycles[-1]:
        out.append(Violation("I2", "last cycle failed: open positions may be unmanaged"))

    # I3 no entry inside a block, or after a founder STOP for that index.
    for r in list(closed_final.values()) + final["open"]:
        opened = int(r["opened_ts"])
        for kind, lo, hi in _intervals(res):
            if lo <= opened < hi:
                out.append(Violation("I3", f"{r['trade_id']} opened at {opened} inside block {kind} [{lo}, {hi})"))
        stops = [f for f in res.founder_rows if f["underlying"] == r["underlying"] and f["ts"] <= opened]
        if stops and stops[-1]["action"] == "STOP":
            out.append(Violation("I3", f"{r['trade_id']} opened after founder STOP {r['underlying']}"))
        if expect_block_from is not None and opened >= expect_block_from:
            out.append(Violation("I10", f"{r['trade_id']} opened at {opened} after the corrupt control file"))

    # I4 P&L reconciles: board total = sum of rows; flag on, ledger closed = filled rows.
    for c in good:
        rows = [r for r in c["closed"] if r["filled"]]
        total = round(sum(float(r["realized_pnl_inr"] or 0) for r in rows), 2)
        if c["overall_pnl_inr"] is not None and abs(float(c["overall_pnl_inr"]) - total) > 0.03 * max(1, len(rows)):
            out.append(Violation("I4", f"cycle {c['hhmm']}: board {c['overall_pnl_inr']} != rows {total}"))
        eb = c.get("event_bus") or {}
        if res.flag == "on" and eb.get("handler_errors"):
            out.append(Violation("I4", f"cycle {c['hhmm']}: event handler errors {eb['handler_errors'][:2]}"))

    # I5 every close has a reason.
    for r in closed_final.values():
        if not r.get("exit_reason"):
            out.append(Violation("I5", f"{r['trade_id']} closed without exit_reason"))

    # I6 no history rewrite across cycles and restarts (the published board).
    for i, a in enumerate(good):
        booked = {r["trade_id"]: r for r in a["closed"] if int(r["closed_ts"]) <= a["tape_cut"].get(r["underlying"], 0)}
        known = set(booked) | {o["trade_id"] for o in a["open"]}
        opens = {o["trade_id"]: o for o in a["open"]}
        for b in good[i + 1:]:
            later = {r["trade_id"]: r for r in b["closed"]}
            later_open = {o["trade_id"] for o in b["open"]}
            for tid, row in booked.items():
                if later.get(tid) != row:
                    out.append(Violation("I6", f"{tid} closed by {a['hhmm']} is {later.get(tid)} at {b['hhmm']} (was {row})"))
            for tid, o in opens.items():
                if tid in later and int(later[tid]["closed_ts"]) < a["tape_cut"].get(o["underlying"], 0):
                    out.append(Violation("I6", f"{tid} open at {a['hhmm']} closed in the past at {b['hhmm']}"))
                if tid not in later and tid not in later_open:
                    out.append(Violation("I6", f"{tid} open at {a['hhmm']} vanished at {b['hhmm']}"))
            for r in list(b["closed"]) + list(b["open"]):
                if r["trade_id"] not in known and int(r["opened_ts"]) <= a["tape_cut"].get(r["underlying"], 0):
                    out.append(Violation("I6", f"{r['trade_id']} appeared at {b['hhmm']} before {a['hhmm']}'s cut-off"))

    # I7 one alert per incident; none in the control run.
    keys: dict[tuple[str, str, str], int] = {}
    for al in res.alerts:
        key = (str(al.get("session")), str(al.get("check")), str(al.get("error_kind")))
        keys[key] = keys.get(key, 0) + 1
    for key, n in keys.items():
        if n > 1:
            out.append(Violation("I7", f"{n} alerts for one incident {key}"))
    if control and res.alerts:
        out.append(Violation("I7", f"control run raised alerts: {[a.get('error_kind') for a in res.alerts][:5]}"))

    # I9 model log: each event written once across all cycles.
    seen: set[tuple[Any, ...]] = set()
    for row in res.model_log:
        key = (row.get("session"), row.get("underlying"), row.get("trade_id"), row.get("event"), row.get("tick_ts"),
               row.get("book_id"), row.get("reason"), row.get("aggregated"))
        if key in seen:
            out.append(Violation("I9", f"duplicate model-log row {key}"))
            break
        seen.add(key)
    return out

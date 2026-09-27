"""Desk (PR-008): executes; never decides. Founder first, then risk engine, then PaperBroker.

Subscriptions (in-memory bus priorities: lower runs first):
  FOUNDER_COMMAND (0)  PAUSE_ENTRIES | RESUME_ENTRIES | FLATTEN_ALL [underlying]
  MARKET_TICK    (10)  mark-to-market: fills, stops, targets, overlay exits (no boss round trip)
  ENTRY_APPROVED (10)  founder pause -> risk_engine.check_entry -> broker.place_order -> book ticket
  EXIT_APPROVED  (10)  close one ticket now

Every entry/exit/cancel is mirrored to the broker and (through `attach_ledger`) the ledger.
A risk veto, a broker refusal, or any exception while building the order = no trade.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from brokers import Order, OrderRefused
from desk.paper import client_order_id, ledger_cancel_reason, ledger_exit_reason, option_symbol
from risk_engine import IST, TradeIntent

log = logging.getLogger("desk")

FOUNDER_PAUSED = "FOUNDER_PAUSED"
RISK_VETO = "RISK_VETO"
BROKER_REFUSED = "BROKER_REFUSED"
FOUNDER_REASON = "FOUNDER_COMMAND"
MTM_HALT = "MTM_HALT"  # mark-to-market / stop path failed; new entries blocked for the session
FAILSAFE_MTM = "failsafe_mtm_error"  # close the open ticket on that same tick
# Live paper loop only. Replays, lab, and parity of the same date must not read this.
HALT_REL = Path("data") / "desk" / "live_loop" / "mtm_halt.json"
# Second copy when the halt folder refuses writes (e.g. read-only), so the halt survives a restart.
HALT_FALLBACK_REL = Path("data") / "health" / "mtm_halt.fallback.json"
HALT_FILE_KIND = "halt_file"  # the halt file cannot be trusted: every entry is blocked
HALT_WRITE_KIND = "halt_write"  # the halt could not be saved; kept in this process instead
EXIT_UNMIRRORED_KIND = "exit_unmirrored"

# The live loop builds a new Desk every cycle in one process. These outlive a single desk.
# Alert dedupe is persisted by desk_ml.reliability.AlertSink when the engine has a data root;
# _LIVE_ALERTED is the in-process fallback. ponytail: a halt that neither the halt folder nor the
# fallback file accepted (whole disk refusing writes) lives only here and is lost on restart; the
# live cycle then blocks entries while the data root is unwritable.
_LIVE_ALERTED: set[tuple[str, str, str]] = set()  # (halt path, session, alert key)
_UNSAVED_HALTS: dict[str, dict[str, Any]] = {}  # halt path -> state the disk refused


def ist(ts: int) -> datetime:
    return datetime.fromtimestamp(int(ts), IST)


class Desk:
    def __init__(
        self,
        bus: Any,
        engine: Any,
        *,
        risk: Any,
        broker: Any,
        steps: dict[str, Any],
        health_alerts_path: Optional[Path] = None,
        live_loop: bool = False,
    ) -> None:
        from desk_ml import paper_scalp as ps

        self._ps = ps
        self._ticket_fields = {f.name for f in fields(ps.OpenPaper)}
        self.bus = bus
        self.engine = engine
        self.risk = risk
        self.broker = broker
        self.steps = steps
        self.now: Optional[datetime] = None
        self.now_ts: Optional[int] = None
        self.paused = False
        self.entries_blocked = False  # session halt after an MTM/stop error; flatten still runs
        self.mtm_halt_reason = ""
        self.halt_from_ts: Optional[int] = None  # block entries at or after this unix ts
        self.halt_fail_closed = False  # corrupt halt file: block every entry this session
        self.live_loop = bool(live_loop)  # only this run reads/writes the halt file
        self.forced_closes: dict[str, dict[str, Any]] = {}  # trade_id -> saved fail-safe close
        self.pending_exits: dict[str, dict[str, Any]] = {}  # trade_id -> closed row the broker has not mirrored
        self._alerted_kinds: set[str] = set()
        root = getattr(engine, "root", None)
        ctx = getattr(engine, "ctx", None)
        # Under the live cycle a corrupt halt file blocks entries from the moment it was first seen
        # (a time-bounded block the cycle owns), so re-running the day keeps earlier trades, and
        # alerts dedupe through the cycle's persisted AlertSink. Replays never touch that state.
        self.time_bounded = bool(getattr(ctx, "live_loop", False)) and self.live_loop
        self.alerts = getattr(ctx, "alerts", None) if self.time_bounded else None
        if health_alerts_path is None and root is not None:
            health_alerts_path = Path(root) / "data" / "health" / "alerts.jsonl"
        self.health_alerts_path = Path(health_alerts_path) if health_alerts_path is not None else None
        self.tickets: dict[str, dict[str, Any]] = {}
        self.latency_ms: dict[str, list[float]] = {"entry": [], "tick": []}
        self.vetoes: list[dict[str, Any]] = []
        self.subs = [
            bus.subscribe(["FOUNDER_COMMAND"], self.on_founder, priority=0),
            bus.subscribe(["MARKET_TICK"], self.on_tick, priority=10),
            bus.subscribe(["ENTRY_APPROVED"], self.on_entry, priority=10),
            bus.subscribe(["EXIT_APPROVED"], self.on_exit, priority=10),
        ]

    def clock(self) -> datetime:
        return self.now or datetime.now(IST)

    def _publish(self, kind: str, payload: dict[str, Any]) -> None:
        self.bus.publish(kind, payload, source="desk")

    # ------------------------------------------------------------- founder

    def on_founder(self, event: Any) -> None:
        cmd = str(event.payload.get("command") or "").upper()
        und = event.payload.get("underlying")
        log.warning("FOUNDER_COMMAND %s %s", cmd, und or "ALL")
        if cmd == "PAUSE_ENTRIES":
            self.paused = True
        elif cmd == "RESUME_ENTRIES":
            self.paused = False
        elif cmd == "FLATTEN_ALL":
            self.paused = True
            for pos in list(self.engine.opens.values()):
                if und is None or str(pos.underlying).upper() == str(und).upper():
                    self.exit_now(pos, FOUNDER_REASON)
        else:
            self._publish("HEALTH_ALERT", {"service": "desk", "status": "WARN", "reason": f"UNKNOWN_FOUNDER_COMMAND {cmd}"})

    # ---------------------------------------------------------------- ticks

    def on_tick(self, event: Any) -> None:
        t0 = time.perf_counter()
        step = self.steps.get((event.payload or {}).get("key"))
        try:
            if step is not None:
                ts = int(step.tick.ts)
                self._apply_persisted_halt(ist(ts).date().isoformat(), ts)
                self._reapply_forced_closes(ts)
            self._retry_pending_exits()
            self._mark_tick(event)
        except Exception as exc:
            # Stops did not run. Close the open tickets on this tick, then keep entries blocked.
            # Flatten (FOUNDER_COMMAND) does not go through this path.
            self.entries_blocked = True
            forced = self._failsafe_close(step)
            self._halt_entries(exc, step, forced)
        finally:
            self.latency_ms["tick"].append((time.perf_counter() - t0) * 1000.0)

    def _mark_tick(self, event: Any) -> None:
        s = self.steps[event.payload["key"]]
        self.now_ts = int(s.tick.ts)
        self.now = ist(self.now_ts)
        n_closed = len(self.engine.closed)
        was_filled = {p.trade_id: p.filled for (_b, u), p in self.engine.opens.items() if u == s.und}
        self._ps.step_mark(self.engine, s)
        for (_b, u), pos in list(self.engine.opens.items()):
            if u == s.und and pos.filled and was_filled.get(pos.trade_id) is False:
                self._fill_entry(pos.trade_id, self._ps.costs.booked_entry(self.engine, pos), self.now_ts)
        for row in self.engine.closed[n_closed:]:
            self._mirror_close(row)
        for (_b, u), pos in self.engine.opens.items():
            if u == s.und:
                self._publish("POSITION_UPDATE", {
                    "trade_id": pos.trade_id, "book_id": pos.book_id, "underlying": pos.underlying,
                    "side": pos.side, "filled": bool(pos.filled), "entry": pos.entry, "stop": pos.stop,
                    "target": pos.target, "last_ltp": pos.last_ltp, "ts": self.now_ts,
                })

    def _data_base(self) -> Path:
        root = getattr(self.engine, "root", None)
        if root:
            return Path(root)
        return self.health_alerts_path.parent if self.health_alerts_path is not None else Path(".")

    def _halt_path(self) -> Path:
        return self._data_base() / HALT_REL

    def _fallback_path(self) -> Path:
        return self._data_base() / HALT_FALLBACK_REL

    def _read_fallback(self, session: str) -> Optional[dict[str, Any]]:
        """The fallback copy for this session, or None. Unreadable = ignored (the primary rules)."""
        try:
            data = json.loads(self._fallback_path().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        verdict, parsed = self._parse_halt(data, session)
        return parsed if verdict == "ok" else None

    def _read_halt(self) -> tuple[str, dict[str, Any], str]:
        """(status, state, fingerprint). status is missing, ok, or corrupt.

        Only "no such file" is missing. A directory, a broken link, a parent that is a file,
        an unreadable file, bad UTF-8, bad JSON, or JSON that is not an object is corrupt.
        The fingerprint names the file state so the same bad file alerts once.
        """
        path = self._halt_path()
        try:
            os.lstat(path)
            raw = path.read_bytes()
        except FileNotFoundError:
            if path.is_symlink():
                return "corrupt", {}, "broken_symlink"
            return "missing", {}, ""
        except OSError as exc:
            return "corrupt", {}, f"{type(exc).__name__}:{exc.errno}"
        digest = "sha256:" + hashlib.sha256(raw).hexdigest()[:16]
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            return "corrupt", {}, digest
        if not isinstance(data, dict):
            return "corrupt", {}, digest
        return "ok", data, digest

    @staticmethod
    def _parse_halt(state: dict[str, Any], session: str) -> tuple[str, dict[str, Any]]:
        """("other_session" | "ok" | "bad: why", normalised). Anything odd for today is bad."""
        saved = state.get("session")
        if not isinstance(saved, str) or len(saved) != 10:
            return "bad: no session date", {}
        if saved != session:
            return "other_session", {}
        try:
            halt_ts = int(state["halt_ts"])
        except (KeyError, TypeError, ValueError):
            return "bad: no halt_ts for this session", {}
        raw_closes = state.get("forced_closes", [])
        if not isinstance(raw_closes, list):
            return "bad: forced_closes is not a list", {}
        closes: dict[str, dict[str, Any]] = {}
        for row in raw_closes:
            try:
                trade_id = str(row["trade_id"])
                fc = {**row, "trade_id": trade_id, "closed_ts": int(row["closed_ts"]), "exit": float(row["exit"])}
            except (KeyError, TypeError, ValueError):
                return "bad: unreadable forced close", {}
            if not trade_id:
                return "bad: forced close without trade_id", {}
            closes.setdefault(trade_id, fc)
        kinds = state.get("kinds") or []
        kinds = [str(k) for k in kinds] if isinstance(kinds, list) else []
        return "ok", {
            "session": session, "halt_ts": halt_ts, "kinds": kinds,
            "forced_closes": closes, "reason": str(state.get("reason") or ""),
        }

    @staticmethod
    def _merge_halt(a: Optional[dict[str, Any]], b: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Union of two parsed halts for one session: earliest halt_ts, every kind, every forced close."""
        if not a:
            return b
        if not b:
            return a
        closes = dict(a["forced_closes"])
        for tid, fc in b["forced_closes"].items():
            closes.setdefault(tid, fc)
        stamps = [t for t in (a.get("halt_ts"), b.get("halt_ts")) if t is not None]
        return {
            "session": a["session"], "halt_ts": min(stamps) if stamps else None,
            "kinds": list(dict.fromkeys(list(a["kinds"]) + list(b["kinds"]))),
            "forced_closes": closes, "reason": b.get("reason") or a.get("reason") or "",
        }

    def _unsaved_halt(self, session: str) -> Optional[dict[str, Any]]:
        state = _UNSAVED_HALTS.get(str(self._halt_path()))
        if state and state.get("session") == session:
            return state
        return None

    def _write_halt(self, state: dict[str, Any]) -> None:
        """Atomic replace, so a crash mid-write never leaves a half-written (corrupt) file."""
        path = self._halt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        out = {**state, "entries_blocked": True, "forced_closes": list(state["forced_closes"].values())}
        tmp.write_text(json.dumps(out) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _apply_persisted_halt(self, session: str, ts: int) -> None:
        """Live loop only. Entries before halt_ts still book; entries at or after it do not."""
        if not self.live_loop or self.halt_fail_closed:
            return
        status, state, fp = self._read_halt()
        if status == "corrupt":
            self._fail_closed_halt(session, "unreadable or corrupt halt file", fp)
            return
        parsed = None
        if status == "ok":
            verdict, parsed = self._parse_halt(state, session)
            if verdict.startswith("bad"):
                self._fail_closed_halt(session, verdict[5:], fp)
                return
            if verdict != "ok":
                parsed = None
        merged = self._merge_halt(self._merge_halt(parsed, self._read_fallback(session)), self._unsaved_halt(session))
        if not merged or merged.get("halt_ts") is None:
            return
        halt_ts = int(merged["halt_ts"])
        if self.halt_from_ts is None or halt_ts < self.halt_from_ts:
            self.halt_from_ts = halt_ts
        for tid, fc in merged["forced_closes"].items():
            self.forced_closes.setdefault(tid, fc)
        self.mtm_halt_reason = merged.get("reason") or self.mtm_halt_reason
        self._alerted_kinds.update(merged["kinds"])
        if int(ts) >= halt_ts:
            self.entries_blocked = True

    def _reapply_forced_closes(self, ts: int) -> None:
        """Re-book a saved fail-safe close at its saved time and price, even if this cycle's tape no
        longer errors there. Without this the replay would run the trade to a different exit."""
        if not self.forced_closes:
            return
        for pos in list(self.engine.opens.values()):
            fc = self.forced_closes.get(str(pos.trade_id))
            if fc is None or int(ts) < int(fc["closed_ts"]):
                continue
            log.warning("re-applying saved fail-safe close %s at %s", pos.trade_id, fc["exit"])
            self.close(pos, ltp=float(fc["exit"]), ts=int(fc["closed_ts"]), reason=FAILSAFE_MTM)

    def _fail_closed_halt(self, session: str, why: str, fingerprint: str = "") -> None:
        """Cannot trust the halt file. Block entries rather than keep trading. Alert once per file state.

        Under the live cycle the block starts when the cycle first saw the bad file (it alerts and
        blocks from then on), so this desk does not block the whole session retroactively.
        """
        reason = f"MTM halt file failed closed ({why}). New entries blocked for this session."
        self.mtm_halt_reason = reason
        if self.time_bounded:
            log.error("%s (time-bounded by the live cycle) path=%s", reason, self._halt_path())
            return
        self.halt_fail_closed = True
        self.entries_blocked = True
        if self._alert_once(session, f"{HALT_FILE_KIND}:{fingerprint}", reason, HALT_FILE_KIND):
            log.error("%s path=%s state=%s", reason, self._halt_path(), fingerprint)
        else:
            log.debug("%s (already alerted) path=%s", reason, self._halt_path())

    def _alert_once(self, session: str, key: str, reason: str, kind: str) -> bool:
        """One HEALTH_ALERT per key: per desk, and in the live loop per (halt path, session, key)."""
        if key in self._alerted_kinds:
            return False
        self._alerted_kinds.add(key)
        if self.live_loop:
            shared = (str(self._halt_path()), session, key)
            if shared in _LIVE_ALERTED:
                return False
            _LIVE_ALERTED.add(shared)
        if self.alerts is not None:  # persisted: a restart does not alert the same incident again
            if not self.alerts.emit(session=session or "unknown", check="desk_mtm", kind=key, message=reason,
                                    ts=float(self.now_ts) if self.now_ts else None, entries_blocked=True):
                return False
            try:
                self._publish("HEALTH_ALERT", {
                    "service": "desk", "status": "CRITICAL", "check": "desk_mtm",
                    "reason": reason, "entries_blocked": True, "error_kind": kind, "session": session,
                })
            except Exception:
                log.exception("failed to publish HEALTH_ALERT")
            return True
        try:
            self._publish("HEALTH_ALERT", {
                "service": "desk", "status": "CRITICAL", "check": "desk_mtm",
                "reason": reason, "entries_blocked": True, "error_kind": kind, "session": session,
            })
        except Exception:
            log.exception("failed to publish HEALTH_ALERT")
        try:
            self._append_health_alert(reason, kind)
        except OSError:
            log.exception("failed to append health alert")
        return True

    def _entry_halted(self, ts: int) -> bool:
        if self.halt_fail_closed:
            return True
        if self.halt_from_ts is not None and int(ts) >= int(self.halt_from_ts):
            return True
        return False

    def _failsafe_price(self, pos: Any, step: Any) -> float:
        """Last good quote of the booked strike, then this tick's quote of THAT strike, then the entry.

        Never the tape's current ITM/ATM leg when it is another strike.
        """
        if getattr(pos, "last_ltp", None) is not None:
            return float(pos.last_ltp)
        tick = getattr(step, "tick", None) if step is not None else None
        if tick is not None and getattr(pos, "atm_strike", None) is not None:
            ltp, _low, src = self._ps.quote_for_side(tick, str(pos.side).upper(), strike=float(pos.atm_strike), itm_only=True)
            if ltp is not None and (src.startswith("STRIKE_") or src.startswith("ITM")):
                return float(ltp)
        if getattr(pos, "entry", None) is not None:
            return float(pos.entry)
        return 0.0

    def _failsafe_close(self, step: Any) -> list[dict[str, Any]]:
        """Close whatever this tick failed to mark, at the last good quote, on this same tick."""
        if step is not None:
            self.now_ts = int(step.tick.ts)
            self.now = ist(self.now_ts)
            und = str(getattr(step, "und", "") or "").upper()
        else:
            und = ""
        ts = int(self.now_ts if self.now_ts is not None else 0)
        forced: list[dict[str, Any]] = []
        for pos in list(self.engine.opens.values()):
            if und and str(getattr(pos, "underlying", "") or "").upper() != und:
                continue
            if ts <= 0:
                ts = int(getattr(pos, "opened_ts", 0) or 0)
            price = self._failsafe_price(pos, step)
            try:
                self.close(pos, ltp=price, ts=ts, reason=FAILSAFE_MTM)
            except Exception:
                log.exception("failsafe close failed for %s", getattr(pos, "trade_id", "?"))
                continue
            forced.append({
                "trade_id": str(pos.trade_id), "book_id": pos.book_id, "underlying": pos.underlying,
                "side": pos.side, "entry": pos.entry, "opened_ts": int(pos.opened_ts),
                "exit": float(price), "closed_ts": int(ts), "reason": FAILSAFE_MTM,
            })
        return forced

    def _halt_entries(self, exc: BaseException, step: Any = None, forced: Optional[list[dict[str, Any]]] = None) -> None:
        """Block new entries for the rest of the session. One HEALTH_ALERT per error kind."""
        self.entries_blocked = True
        kind = type(exc).__name__
        reason = (
            f"MTM or stop path failed ({kind}: {exc}). "
            "Open tickets closed at the last good quote. New entries blocked for this session."
        )
        halt_ts = int(step.tick.ts) if step is not None else int(self.now_ts or 0)
        if halt_ts > 0 and (self.halt_from_ts is None or halt_ts < self.halt_from_ts):
            self.halt_from_ts = halt_ts
        for fc in forced or []:
            self.forced_closes.setdefault(fc["trade_id"], fc)
        self.mtm_halt_reason = reason
        log.error("%s", reason)
        session = ""
        if step is not None:
            session = ist(int(step.tick.ts)).date().isoformat()
        elif self.now_ts is not None:
            session = ist(int(self.now_ts)).date().isoformat()
        if self.live_loop and session:
            self._persist_halt(session, kind, reason)
        self._alert_once(session, kind, reason, kind)

    def _persist_halt(self, session: str, kind: str, reason: str) -> None:
        """Merge this halt into the saved state. Never replace a corrupt file: it keeps blocking."""
        if self.halt_fail_closed:
            log.error("halt file already failed closed; not overwriting it path=%s", self._halt_path())
            return
        status, state, fp = self._read_halt()
        if status == "corrupt":
            self._fail_closed_halt(session, "unreadable or corrupt halt file", fp)
            log.error("halt file is corrupt; not overwriting it path=%s", self._halt_path())
            mine = {"session": session, "halt_ts": self.halt_from_ts, "kinds": [kind],
                    "forced_closes": dict(self.forced_closes), "reason": reason}
            self._save_fallback(self._merge_halt(self._read_fallback(session), mine), session)
            return
        saved = None
        if status == "ok":
            verdict, saved = self._parse_halt(state, session)
            if verdict.startswith("bad"):
                self._fail_closed_halt(session, verdict[5:], fp)
                log.error("halt file is not valid for this session; not overwriting it")
                return
            if verdict != "ok":
                saved = None  # another session's file: stale, replace it
        mine = {
            "session": session, "halt_ts": self.halt_from_ts, "kinds": [kind],
            "forced_closes": dict(self.forced_closes), "reason": reason,
        }
        merged = self._merge_halt(self._merge_halt(saved, self._unsaved_halt(session)), mine)
        key = str(self._halt_path())
        try:
            self._write_halt(merged)
        except OSError as exc:
            reason_w = f"MTM halt could not be saved ({type(exc).__name__}: {exc})."
            self._alert_once(session, HALT_WRITE_KIND, reason_w, HALT_WRITE_KIND)
            log.error("%s path=%s", reason_w, key)
            self._save_fallback(self._merge_halt(self._read_fallback(session), merged), session)
            return
        _UNSAVED_HALTS.pop(key, None)

    def _save_fallback(self, state: Optional[dict[str, Any]], session: str) -> None:
        """Fallback copy of a halt the primary path could not hold; memory if that fails too."""
        if not state:
            return
        key = str(self._halt_path())
        out = {**state, "entries_blocked": True, "forced_closes": list(state["forced_closes"].values())}
        try:
            from desk_ml.reliability import atomic_write_json

            atomic_write_json(self._fallback_path(), out)
        except OSError as exc:
            _UNSAVED_HALTS[key] = state  # later desks in this process still apply it
            log.error("halt fallback not saved either (%s); kept in memory for this process", exc)

    def _append_health_alert(self, reason: str, kind: str) -> None:
        """Same JSONL shape as packages/health (served by GET /health/alerts). Session-clock ts."""
        path = self.health_alerts_path
        if path is None:  # rootless unit-test desk: log only
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": self.clock().isoformat(timespec="seconds"),
            "wall_ts": datetime.now(IST).isoformat(timespec="seconds"),
            "event": "ALERT",
            "check": "desk_mtm",
            "severity": "CRITICAL",
            "error_kind": kind,
            "message": reason,
        }
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    # --------------------------------------------------------------- entries

    def _veto(self, pos: Any, reason: str, detail: dict[str, Any]) -> None:
        """``reason`` is the skip code and ``reason_code`` the machine code. Human text is ``reason_text``."""
        self.engine.mark_skip(pos.book_id, pos.underlying, reason, ts=pos.opened_ts, seen_side=pos.side, **detail)
        row = {**detail, "trade_id": pos.trade_id, "book_id": pos.book_id, "underlying": pos.underlying,
               "side": pos.side, "reason": reason, "ts": pos.opened_ts}
        self.vetoes.append(row)
        self._publish("ENTRY_VETOED", row)

    def on_entry(self, event: Any) -> None:
        t0 = time.perf_counter()
        ticket = event.payload["ticket"]
        pos = self._ps.OpenPaper(**{k: v for k, v in ticket.items() if k in self._ticket_fields})
        if self.paused:
            self._veto(pos, FOUNDER_PAUSED, {})
            return
        opened = int(pos.opened_ts)
        self._apply_persisted_halt(ist(opened).date().isoformat(), opened)  # even before this desk's first tick
        if self._entry_halted(opened):
            self._veto(pos, MTM_HALT, {"reason_code": MTM_HALT, "reason_text": self.mtm_halt_reason})
            return
        symbol = option_symbol(pos.underlying, pos.atm_strike, pos.side)
        try:
            intent = TradeIntent(
                symbol=symbol, side="BUY", lots=int(pos.lots), lot_size=int(pos.lot_size), order_type="LIMIT",
                price=float(pos.limit_price or pos.entry), decision_price=float(pos.entry),
                stop_loss=float(pos.stop), target=float(pos.target), purpose="ENTRY", trade_id=pos.trade_id,
                client_order_id=client_order_id(pos.trade_id, "E"),
            )
            decision = self.risk.check_entry(intent, now=self.clock())
        except Exception as exc:  # cannot size or check the order -> no trade
            self._veto(pos, RISK_VETO, {"reason_code": "ENGINE_ERROR", "reason_text": f"{type(exc).__name__}: {exc}"})
            return
        ticket_risk = None
        try:
            ticket_risk = round(float(intent.worst_case_loss()), 2)
        except (TypeError, ValueError):
            ticket_risk = None
        if not decision.approved:
            self._veto(pos, RISK_VETO, {
                "reason_code": decision.reason_code, "reason_text": decision.reason,
                "ticket_risk_inr": ticket_risk, "critical": bool(decision.critical),
            })
            return
        try:
            order = self.broker.place_order(intent, decision)
        except OrderRefused as exc:
            self._veto(pos, BROKER_REFUSED, {"reason_code": BROKER_REFUSED, "reason_text": str(exc)})
            return
        except Exception as exc:  # timeout / broker error: the order state is unknown -> no entry
            self._veto(pos, BROKER_REFUSED, {"reason_code": "BROKER_ERROR", "reason_text": f"{type(exc).__name__}: {exc}"})
            return
        self.tickets[pos.trade_id] = {"order": order, "symbol": symbol, "filled": False, "pos": pos}
        self._publish("ORDER_SUBMITTED", self._order_payload(order, pos.trade_id))
        self._ps._commit_open(self.engine, pos)
        if pos.filled:
            self._fill_entry(pos.trade_id, self._ps.costs.booked_entry(self.engine, pos), int(pos.opened_ts))
        self.latency_ms["entry"].append((time.perf_counter() - t0) * 1000.0)

    def adopt_booked(self, pos: Any) -> None:
        """Mirror a ticket booked in an earlier live cycle (already approved then) to broker + ledger.

        The live loop carries booked open tickets instead of re-deriving them; the broker and the
        per-cycle ledger must hold them too so their exits are mirrored. Not a new entry.
        """
        from risk_engine import RiskDecision

        if pos.trade_id in self.tickets:
            return
        symbol = option_symbol(pos.underlying, pos.atm_strike, pos.side)
        try:
            intent = TradeIntent(
                symbol=symbol, side="BUY", lots=int(pos.lots), lot_size=int(pos.lot_size), order_type="LIMIT",
                price=float(pos.limit_price or pos.entry), decision_price=float(pos.entry),
                stop_loss=float(pos.stop), target=float(pos.target), purpose="ENTRY", trade_id=pos.trade_id,
                client_order_id=client_order_id(pos.trade_id, "E"),
            )
            when = ist(int(pos.opened_ts))
            decision = RiskDecision(True, intent.client_order_id, "ENTRY", "ADOPTED",
                                    "booked in an earlier live cycle", self.now or when)
            order = self.broker.place_order(intent, decision)
        except Exception as exc:  # the engine still manages it; only the mirror is missing
            session = ist(int(pos.opened_ts)).date().isoformat()
            self._alert_once(session, f"adopt_failed:{pos.trade_id}", f"carried ticket {pos.trade_id} not mirrored: {exc}",
                             "adopt_failed")
            return
        self.tickets[pos.trade_id] = {"order": order, "symbol": symbol, "filled": False, "pos": pos}
        if pos.filled:
            self._fill_entry(pos.trade_id, float(pos.entry), int(self.now_ts or pos.opened_ts))

    def _order_payload(self, order: Order, trade_id: str, **extra: Any) -> dict[str, Any]:
        i = order.intent
        return {"trade_id": trade_id, "client_order_id": order.client_order_id, "symbol": i.symbol, "side": i.side,
                "qty": i.qty, "order_type": i.order_type, "price": order.price, "purpose": i.purpose,
                "state": order.state.value, "mode": order.mode, **extra}

    def _fill_entry(self, trade_id: str, price: float, ts: int) -> None:
        t = self.tickets.get(trade_id)
        if t is None or t["filled"]:
            return
        self.broker.fill_at(t["order"], price, ist(ts))
        t["filled"] = True
        self._publish("ORDER_FILLED", self._order_payload(
            t["order"], trade_id, fill_price=t["order"].avg_fill_price, engine_price=price, ts=int(ts)))

    # ----------------------------------------------------------------- exits

    def on_exit(self, event: Any) -> None:
        trade_id = event.payload.get("trade_id")
        pos = next((p for p in self.engine.opens.values() if p.trade_id == trade_id), None)
        if pos is None:
            log.warning("EXIT_APPROVED for unknown/closed ticket %s", trade_id)
            return
        self.exit_now(pos, str(event.payload.get("reason") or "BOSS_OVERRIDE"))

    def exit_now(self, pos: Any, reason: str) -> None:
        ltp = pos.last_ltp if pos.last_ltp is not None else pos.entry
        self.close(pos, ltp=float(ltp), ts=int(self.now_ts if self.now_ts is not None else pos.opened_ts), reason=reason)

    def close(self, pos: Any, *, ltp: float, ts: int, reason: str) -> None:
        """Close one ticket with the paper engine's `_close`, then mirror it to broker + ledger."""
        n_closed = len(self.engine.closed)
        self._ps._close(self.engine, pos, ltp=ltp, ts=ts, reason=reason, root=self.engine.root)
        for row in self.engine.closed[n_closed:]:
            self._mirror_close(row)

    def _retry_pending_exits(self) -> None:
        for trade_id, pend in list(self.pending_exits.items()):
            self.tickets.setdefault(trade_id, pend["ticket"])
            self.pending_exits.pop(trade_id, None)
            self._mirror_close(pend["row"])

    def _pend_exit(self, trade_id: str, t: dict[str, Any], row: dict[str, Any], why: str) -> None:
        """The engine booked the close; the broker/ledger did not. Keep it and retry every tick."""
        self.pending_exits[trade_id] = {"ticket": t, "row": row}
        self._alert_unmirrored(trade_id, why)

    def _mirror_close(self, row: dict[str, Any]) -> None:
        trade_id = str(row.get("trade_id"))
        t = self.tickets.pop(trade_id, None)
        if t is None:
            return
        try:
            self._mirror_close_ticket(trade_id, t, row)
        except Exception as exc:  # never lose the exit: retry next tick
            self._pend_exit(trade_id, t, row, f"exit mirror failed: {type(exc).__name__}: {exc}")

    def _mirror_close_ticket(self, trade_id: str, t: dict[str, Any], row: dict[str, Any]) -> None:
        order, ts = t["order"], int(row["closed_ts"])
        if row.get("filled"):
            if not t["filled"]:
                self.tickets[trade_id] = t
                self._fill_entry(trade_id, float(row["entry"]), ts)
                self.tickets.pop(trade_id, None)
            i = order.intent
            intent = TradeIntent(
                symbol=i.symbol, side="SELL", lots=i.lots, lot_size=i.lot_size, order_type="MARKET",
                decision_price=float(row.get("decision_exit", row["exit"])), purpose="EXIT",
                exit_reason=ledger_exit_reason(row["exit_reason"]),
                trade_id=trade_id, client_order_id=client_order_id(trade_id, "X"),
            )
            exit_order = t.get("exit_order")  # a retry after the exit was placed but not filled
            if exit_order is None:
                decision = self.risk.check_exit(intent, now=self.clock())
                if not decision.approved:
                    self._pend_exit(trade_id, t, row, f"exit refused by risk: {decision.reason_code}")
                    return
                exit_order = self.broker.place_order(intent, decision)
                t["exit_order"] = exit_order
                self._publish("ORDER_SUBMITTED", self._order_payload(exit_order, trade_id))
            if exit_order.is_open:
                self.broker.fill_at(exit_order, float(row["exit"]), ist(ts))
                self._publish("ORDER_FILLED", self._order_payload(
                    exit_order, trade_id, fill_price=exit_order.avg_fill_price, engine_price=row["exit"], ts=ts))
        elif order.is_open:
            decision = self.risk.check_exit(order.intent, "CANCEL", now=self.clock())
            if not decision.approved:
                self._pend_exit(trade_id, t, row, f"cancel refused by risk: {decision.reason_code}")
                return
            else:
                self.broker.cancel_order(order, decision, reason=ledger_cancel_reason(row["exit_reason"]))
                self._publish("ORDER_CANCELLED", self._order_payload(order, trade_id, reason=order.cancel_reason))
        self._publish("POSITION_CLOSED", {
            k: row.get(k) for k in (
                "trade_id", "book_id", "underlying", "side", "filled", "entry", "exit", "exit_reason", "lots", "qty",
                "gross_pnl_inr", "charges_inr", "realized_pnl_inr", "opened_ts", "closed_ts",
            )
        })

    def _alert_unmirrored(self, trade_id: str, why: str) -> None:
        """One alert per trade (not per retry)."""
        log.error("paper close %s not mirrored to broker: %s", trade_id, why)
        session = ist(int(self.now_ts)).date().isoformat() if self.now_ts else "unknown"
        self._alert_once(session, f"{EXIT_UNMIRRORED_KIND}:{trade_id}", f"paper close {trade_id} not mirrored: {why}",
                         EXIT_UNMIRRORED_KIND)

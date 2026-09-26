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

import json
import logging
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
HALT_REL = Path("data") / "desk" / "mtm_halt.json"


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
        self._alerted_kinds: set[str] = set()
        if health_alerts_path is None:
            from desk_ml.persist import repo_root

            health_alerts_path = repo_root() / "data" / "health" / "alerts.jsonl"
        self.health_alerts_path = Path(health_alerts_path)
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
                self._apply_persisted_halt(ist(int(step.tick.ts)).date().isoformat())
            self._mark_tick(event)
        except Exception as exc:
            # Stops did not run. Close the open tickets on this tick, then keep entries blocked.
            # Flatten (FOUNDER_COMMAND) does not go through this path.
            self.entries_blocked = True
            self._failsafe_close(step)
            self._halt_entries(exc, step)
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
                self._fill_entry(pos.trade_id, float(pos.entry), self.now_ts)
        for row in self.engine.closed[n_closed:]:
            self._mirror_close(row)
        for (_b, u), pos in self.engine.opens.items():
            if u == s.und:
                self._publish("POSITION_UPDATE", {
                    "trade_id": pos.trade_id, "book_id": pos.book_id, "underlying": pos.underlying,
                    "side": pos.side, "filled": bool(pos.filled), "entry": pos.entry, "stop": pos.stop,
                    "target": pos.target, "last_ltp": pos.last_ltp, "ts": self.now_ts,
                })

    def _halt_path(self) -> Path:
        root = getattr(self.engine, "root", None)
        base = Path(root) if root else self.health_alerts_path.parent
        return base / HALT_REL

    def _read_halt(self) -> dict[str, Any]:
        path = self._halt_path()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _write_halt(self, state: dict[str, Any]) -> None:
        path = self._halt_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state) + "\n", encoding="utf-8")

    def _apply_persisted_halt(self, session: str) -> None:
        """The live loop rebuilds the desk every cycle. The block has to survive that."""
        state = self._read_halt()
        if state.get("session") != session or not state.get("entries_blocked"):
            return
        self.entries_blocked = True
        self.mtm_halt_reason = str(state.get("reason") or self.mtm_halt_reason)
        self._alerted_kinds.update(str(k) for k in (state.get("kinds") or []))

    def _failsafe_price(self, pos: Any, step: Any) -> float:
        """Last good quote, then this tick's premium, then the entry."""
        if getattr(pos, "last_ltp", None) is not None:
            return float(pos.last_ltp)
        tick = getattr(step, "tick", None) if step is not None else None
        side = str(getattr(pos, "side", "") or "").upper()
        if tick is not None:
            attrs = ("itm_ce_close", "ce_close") if side == "CE" else ("itm_pe_close", "pe_close")
            for attr in attrs:
                raw = getattr(tick, attr, None)
                if raw is not None:
                    return float(raw)
        if getattr(pos, "entry", None) is not None:
            return float(pos.entry)
        return 0.0

    def _failsafe_close(self, step: Any) -> None:
        """Close whatever this tick failed to mark, at the last good quote, on this same tick."""
        if step is not None:
            self.now_ts = int(step.tick.ts)
            self.now = ist(self.now_ts)
            und = str(getattr(step, "und", "") or "").upper()
        else:
            und = ""
        ts = int(self.now_ts if self.now_ts is not None else 0)
        for pos in list(self.engine.opens.values()):
            if und and str(getattr(pos, "underlying", "") or "").upper() != und:
                continue
            if ts <= 0:
                ts = int(getattr(pos, "opened_ts", 0) or 0)
            try:
                self.close(pos, ltp=self._failsafe_price(pos, step), ts=ts, reason=FAILSAFE_MTM)
            except Exception:
                log.exception("failsafe close failed for %s", getattr(pos, "trade_id", "?"))

    def _halt_entries(self, exc: BaseException, step: Any = None) -> None:
        """Block new entries for the rest of the session. One HEALTH_ALERT per error kind."""
        self.entries_blocked = True
        kind = type(exc).__name__
        reason = (
            f"MTM or stop path failed ({kind}: {exc}). "
            "Open tickets closed at the last good quote. New entries blocked for this session."
        )
        self.mtm_halt_reason = reason
        log.error("%s", reason)
        session = ""
        if step is not None:
            session = ist(int(step.tick.ts)).date().isoformat()
        elif self.now_ts is not None:
            session = ist(int(self.now_ts)).date().isoformat()
        state = self._read_halt()
        if state.get("session") != session:
            state = {"session": session, "entries_blocked": True, "kinds": []}
        kinds = [str(k) for k in (state.get("kinds") or [])]
        state["entries_blocked"] = True
        state["reason"] = reason
        already = kind in kinds or kind in self._alerted_kinds
        if not already:
            kinds.append(kind)
            self._alerted_kinds.add(kind)
            try:
                self._publish("HEALTH_ALERT", {
                    "service": "desk", "status": "CRITICAL", "check": "desk_mtm",
                    "reason": reason, "entries_blocked": True, "error_kind": kind,
                })
            except Exception:
                log.exception("failed to publish HEALTH_ALERT")
            self._append_health_alert(reason, kind)
        state["kinds"] = kinds
        if session:
            self._write_halt(state)

    def _append_health_alert(self, reason: str, kind: str) -> None:
        """Same JSONL shape as packages/health (served by GET /health/alerts)."""
        path = self.health_alerts_path
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(IST).isoformat(timespec="seconds"),
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
        self.engine.mark_skip(pos.book_id, pos.underlying, reason, ts=pos.opened_ts, seen_side=pos.side, **detail)
        row = {"trade_id": pos.trade_id, "book_id": pos.book_id, "underlying": pos.underlying, "side": pos.side,
               "reason": reason, "ts": pos.opened_ts, **detail}
        self.vetoes.append(row)
        self._publish("ENTRY_VETOED", row)

    def on_entry(self, event: Any) -> None:
        t0 = time.perf_counter()
        ticket = event.payload["ticket"]
        pos = self._ps.OpenPaper(**{k: v for k, v in ticket.items() if k in self._ticket_fields})
        if self.paused:
            self._veto(pos, FOUNDER_PAUSED, {})
            return
        if self.entries_blocked:
            self._veto(pos, MTM_HALT, {"reason_code": MTM_HALT, "detail": self.mtm_halt_reason})
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
            self._veto(pos, RISK_VETO, {"reason_code": "ENGINE_ERROR", "detail": f"{type(exc).__name__}: {exc}",
                                        "reason": f"{type(exc).__name__}: {exc}"})
            return
        ticket_risk = None
        try:
            ticket_risk = round(float(intent.worst_case_loss()), 2)
        except (TypeError, ValueError):
            ticket_risk = None
        if not decision.approved:
            self._veto(pos, RISK_VETO, {
                "reason_code": decision.reason_code, "detail": decision.reason, "reason": decision.reason,
                "ticket_risk_inr": ticket_risk, "critical": bool(decision.critical),
            })
            return
        try:
            order = self.broker.place_order(intent, decision)
        except OrderRefused as exc:
            self._veto(pos, BROKER_REFUSED, {"detail": str(exc)})
            return
        self.tickets[pos.trade_id] = {"order": order, "symbol": symbol, "filled": False, "pos": pos}
        self._publish("ORDER_SUBMITTED", self._order_payload(order, pos.trade_id))
        self._ps._commit_open(self.engine, pos)
        if pos.filled:
            self._fill_entry(pos.trade_id, float(pos.entry), int(pos.opened_ts))
        self.latency_ms["entry"].append((time.perf_counter() - t0) * 1000.0)

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

    def _mirror_close(self, row: dict[str, Any]) -> None:
        trade_id = str(row.get("trade_id"))
        t = self.tickets.pop(trade_id, None)
        if t is None:
            return
        order, ts = t["order"], int(row["closed_ts"])
        if row.get("filled"):
            if not t["filled"]:
                self.tickets[trade_id] = t
                self._fill_entry(trade_id, float(row["entry"]), ts)
                self.tickets.pop(trade_id, None)
            i = order.intent
            intent = TradeIntent(
                symbol=i.symbol, side="SELL", lots=i.lots, lot_size=i.lot_size, order_type="MARKET",
                decision_price=float(row["exit"]), purpose="EXIT", exit_reason=ledger_exit_reason(row["exit_reason"]),
                trade_id=trade_id, client_order_id=client_order_id(trade_id, "X"),
            )
            decision = self.risk.check_exit(intent, now=self.clock())
            if not decision.approved:
                self._alert_unmirrored(trade_id, f"exit refused by risk: {decision.reason_code}")
            else:
                exit_order = self.broker.place_order(intent, decision)
                self._publish("ORDER_SUBMITTED", self._order_payload(exit_order, trade_id))
                self.broker.fill_at(exit_order, float(row["exit"]), ist(ts))
                self._publish("ORDER_FILLED", self._order_payload(
                    exit_order, trade_id, fill_price=exit_order.avg_fill_price, engine_price=row["exit"], ts=ts))
        elif order.is_open:
            decision = self.risk.check_exit(order.intent, "CANCEL", now=self.clock())
            if not decision.approved:
                self._alert_unmirrored(trade_id, f"cancel refused by risk: {decision.reason_code}")
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
        log.error("paper close %s not mirrored to broker: %s", trade_id, why)
        self._publish("HEALTH_ALERT", {"service": "desk", "status": "CRITICAL", "trade_id": trade_id, "reason": why})

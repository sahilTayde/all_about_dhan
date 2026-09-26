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
        try:
            self._mark_tick(event)
        except Exception as exc:
            # Fail safe: do not swallow a mark/stop error and keep taking entries.
            # Flatten (FOUNDER_COMMAND) does not go through this path.
            self._halt_entries(exc)
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

    def _halt_entries(self, exc: BaseException) -> None:
        """Block new entries for the rest of the session and surface the error on /health/alerts."""
        self.entries_blocked = True
        reason = (
            f"MTM or stop path failed ({type(exc).__name__}: {exc}). "
            "New entries blocked for this session. Flatten still runs."
        )
        self.mtm_halt_reason = reason
        log.error("%s", reason)
        try:
            self._publish("HEALTH_ALERT", {
                "service": "desk", "status": "CRITICAL", "check": "desk_mtm",
                "reason": reason, "entries_blocked": True,
            })
        except Exception:
            log.exception("failed to publish HEALTH_ALERT")
        self._append_health_alert(reason)

    def _append_health_alert(self, reason: str) -> None:
        """Same JSONL shape as packages/health (served by GET /health/alerts)."""
        path = self.health_alerts_path
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {
            "ts": datetime.now(IST).isoformat(timespec="seconds"),
            "event": "ALERT",
            "check": "desk_mtm",
            "severity": "CRITICAL",
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
            self._veto(pos, RISK_VETO, {"reason_code": "ENGINE_ERROR", "detail": f"{type(exc).__name__}: {exc}"})
            return
        if not decision.approved:
            self._veto(pos, RISK_VETO, {"reason_code": decision.reason_code, "detail": decision.reason,
                                        "critical": bool(decision.critical)})
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

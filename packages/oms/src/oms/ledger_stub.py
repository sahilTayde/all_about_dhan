"""In-memory ledger adapter. Same plan/snapshot API as SqliteLedgerStore for paper tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from contracts.instruments import India
from ledger.charges import (  # type: ignore[import-untyped, unused-ignore]
    exchange_for,
    order_charges,
)
from risk_engine.engine import IST  # type: ignore[import-untyped, unused-ignore]

_INDIA = India()
_PLAN_IMMUTABLE = frozenset({"decision_id", "signal_id", "mode", "action", "created_at"})


def _fill_lot_size(instrument_id: str) -> int | None:
    if not instrument_id:
        return None
    try:
        symbol = str(_INDIA.parse_instrument_id(instrument_id).get("symbol") or "")
        return _INDIA.lot_size(symbol)
    except ValueError:
        return None


@dataclass
class ChargeRow:
    client_order_id: str
    side: str
    qty: int
    price: float
    exchange: str | None
    components: dict[str, Decimal]
    charges_status: str  # FINAL | PENDING
    fill_model: str
    slippage_source: str


@dataclass
class MemoryLedger:
    """Paper/test double of V2-10: plans, session_halts, and snapshot veto fields. No disk."""

    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    fills: list[dict[str, Any]] = field(default_factory=list)
    charges: list[ChargeRow] = field(default_factory=list)
    positions: dict[str, dict[str, Any]] = field(default_factory=dict)
    closed: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    protective: dict[str, str] = field(default_factory=dict)  # position_key -> stop order_id
    entry_plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    session_halts: list[dict[str, Any]] = field(default_factory=list)
    rates: dict[str, Any] | None = None
    recon_ok: bool = True
    last_loss_exit_at: datetime | None = None
    realized_pnl_today: float = 0.0

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        return self.entry_plans.get(plan_id)

    def upsert_plan(self, row: dict[str, Any]) -> dict[str, Any]:
        pid = str(row["plan_id"])
        if pid in self.entry_plans:
            held = self.entry_plans[pid]
            created = held.get("created_at")
            for key, value in row.items():
                if key in _PLAN_IMMUTABLE and key in held:
                    continue
                held[key] = value
            if created is not None:
                held["created_at"] = created
        else:
            self.entry_plans[pid] = dict(row)
        return self.entry_plans[pid]

    def pending_plans(self) -> list[dict[str, Any]]:
        return [p for p in self.entry_plans.values() if p.get("status") in ("PENDING", "WORKING")]

    def get_position(self, key: str) -> dict[str, Any] | None:
        return self.positions.get(key)

    def get_protective(self, key: str) -> str | None:
        got = self.protective.get(key)
        return str(got) if got else None

    def clear_protective(self, key: str) -> None:
        self.protective.pop(key, None)

    def mark_order_status(
        self, client_order_id: str, status: str, *, cancel_reason: str | None = None
    ) -> None:
        row = self.orders.get(client_order_id)
        if row is None:
            return
        row["state"] = status
        row["status"] = status
        if cancel_reason is not None:
            row["cancel_reason"] = cancel_reason

    def get_order(self, client_order_id: str) -> dict[str, Any] | None:
        return self.orders.get(client_order_id)

    def insert_order(self, row: dict[str, Any]) -> dict[str, Any]:
        cid = row["client_order_id"]
        if cid in self.orders:
            return self.orders[cid]
        self.orders[cid] = dict(row)
        return self.orders[cid]

    def mark_needs_lookup(self, client_order_id: str) -> None:
        if client_order_id in self.orders:
            self.orders[client_order_id]["needs_lookup"] = True

    def record_decision(self, decision: dict[str, Any]) -> None:
        self.decisions.append(decision)

    def record_fill(
        self,
        client_order_id: str,
        qty: int,
        price: float,
        *,
        fill_model: str,
        ts: datetime | None = None,
        side: str = "BUY",
        symbol: str = "",
        instrument_id: str = "",
        account_id: str = "",
        strategy_id: str = "",
    ) -> ChargeRow:
        stamp = ts or datetime.now(IST)
        lot = _fill_lot_size(instrument_id)
        if lot is not None and int(qty) % lot != 0:
            raise ValueError(f"fill qty {qty} is not a multiple of lot size {lot}")
        status = "PENDING"
        components: dict[str, Decimal] = {}
        exchange: str | None = None
        if self.rates is not None:
            exchange = exchange_for(symbol or instrument_id, self.rates)
            components = order_charges(side, qty, price, self.rates, exchange=exchange)
            status = "FINAL"
        row = ChargeRow(
            client_order_id=client_order_id,
            side=side,
            qty=qty,
            price=price,
            exchange=exchange,
            components=components,
            charges_status=status,
            fill_model=fill_model,
            slippage_source=fill_model if fill_model in ("depth", "fcmeas") else "fcmeas",
        )
        self.fills.append(
            {
                "client_order_id": client_order_id,
                "qty": qty,
                "price": price,
                "ts": stamp,
                "fill_model": fill_model,
                "charges_status": status,
            }
        )
        self.charges.append(row)
        key = instrument_id or symbol
        prev = self.positions.get(key)
        if side == "BUY":
            if prev is not None and int(prev.get("net_qty") or 0) > 0:
                old_qty = int(prev["net_qty"])
                nq = old_qty + qty
                prev["avg_price"] = (float(prev["avg_price"]) * old_qty + price * qty) / nq
                prev["net_qty"] = nq
                prev["updated_at"] = stamp
                prev["orig_qty"] = nq
            else:
                self.positions[key] = {
                    "instrument_id": instrument_id,
                    "symbol": symbol,
                    "net_qty": qty,
                    "avg_price": price,
                    "entry_order_id": client_order_id,
                    "account_id": account_id,
                    "strategy_id": strategy_id,
                    "opened_at": stamp,
                    "updated_at": stamp,
                    "fill_ts": stamp,
                    "position_id": client_order_id,
                    "realized_pnl": 0.0,
                    "orig_qty": qty,
                    "partials_done": 0,
                }
        elif prev is not None:
            closed_qty = min(qty, int(prev.get("net_qty") or 0))
            pnl = (price - float(prev.get("avg_price") or 0)) * closed_qty
            prev["realized_pnl"] = float(prev.get("realized_pnl") or 0) + pnl
            prev["net_qty"] = int(prev.get("net_qty") or 0) - closed_qty
            prev["updated_at"] = stamp
            prev["last_exit_price"] = price
            prev["last_exit_qty"] = closed_qty
            prev["last_exit_ts"] = stamp
            self.realized_pnl_today += pnl
            if pnl < 0:
                self.last_loss_exit_at = stamp
            if int(prev["net_qty"]) == 0:
                self.closed.append(dict(prev))
                del self.positions[key]
                self.protective.pop(key, None)
        return row

    def set_protective(self, position_key: str, stop_order_id: str) -> None:
        self.protective[position_key] = stop_order_id

    def has_protective(self, position_key: str) -> bool:
        return position_key in self.protective

    def open_positions(self) -> list[dict[str, Any]]:
        return [p for p in self.positions.values() if int(p.get("net_qty") or 0) != 0]

    def risk_snapshot(self, now: datetime, idempotency_seconds: int) -> dict[str, Any]:
        since = now - timedelta(seconds=idempotency_seconds)
        used = {
            d["client_order_id"]
            for d in self.decisions
            if d.get("approved") and d.get("action") in ("ENTRY", "EXIT")
        }
        fps: list[tuple[datetime, str]] = []
        for d in self.decisions:
            if d.get("approved") and d.get("action") == "ENTRY" and d.get("fingerprint"):
                ts = d.get("ts")
                if isinstance(ts, datetime) and ts >= since:
                    fps.append((ts, str(d["fingerprint"])))
        return {
            "open_positions": len(self.open_positions()),
            "realized_pnl_today": float(self.realized_pnl_today),
            "last_loss_exit_at": self.last_loss_exit_at,
            "recent_fingerprints": fps,
            "used_client_order_ids": used,
            "recon_ok": self.recon_ok,
            "feed_status": "UP",
            "strategy_pnl": {},
            "halt_unreadable": False,
        }

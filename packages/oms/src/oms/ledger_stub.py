"""In-memory ledger stub until V2-10. Paper fills always get a charges row (or PENDING)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from ledger.charges import (  # type: ignore[import-untyped, unused-ignore]
    exchange_for,
    order_charges,
)
from risk_engine.engine import IST


@dataclass
class ChargeRow:
    client_order_id: str
    side: str
    qty: int
    price: float
    exchange: str | None
    components: dict[str, float]
    charges_status: str  # FINAL | PENDING
    fill_model: str
    slippage_source: str


@dataclass
class MemoryLedger:
    """V2-10 comes later. Enough for router/risk/fill tests. No disk writes."""

    orders: dict[str, dict[str, Any]] = field(default_factory=dict)
    fills: list[dict[str, Any]] = field(default_factory=list)
    charges: list[ChargeRow] = field(default_factory=list)
    positions: dict[str, dict[str, Any]] = field(default_factory=dict)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    protective: dict[str, str] = field(default_factory=dict)  # position_key -> stop order_id
    rates: dict[str, Any] | None = None
    recon_ok: bool = True

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
    ) -> ChargeRow:
        stamp = ts or datetime.now(IST)
        status = "PENDING"
        components: dict[str, float] = {}
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
        if side == "BUY":
            key = instrument_id or symbol
            self.positions[key] = {
                "instrument_id": instrument_id,
                "symbol": symbol,
                "net_qty": qty,
                "avg_price": price,
                "entry_order_id": client_order_id,
            }
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
            "realized_pnl_today": 0.0,
            "last_loss_exit_at": None,
            "recent_fingerprints": fps,
            "used_client_order_ids": used,
            "recon_ok": self.recon_ok,
        }

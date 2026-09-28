"""Durable LedgerStore: SQLite-WAL, checkpoint + outbox, positions_v2. Paper only."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import fields, is_dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from pathlib import Path
from typing import Any, Protocol, Self

from ledger.charges import UNDERLYING_EXCHANGE, exchange_for, load_rates, order_charges
from ledger.migrate import (
    CODE_SCHEMA_VERSION,
    LegacyPathError,
    SchemaTooNew,
    check_schema,
    is_legacy_path,
    migrate,
)
from ledger.store import IST, OPEN_ORDER_STATES, Ledger, iso_ist

_PAISE = Decimal("0.01")
# Longer names first so BANKNIFTY is not matched as NIFTY.
_LOT_SIZES = (
    ("BANKNIFTY", 30),
    ("MIDCPNIFTY", 50),
    ("FINNIFTY", 40),
    ("BANKEX", 15),
    ("SENSEX", 20),
    ("NIFTY", 65),
)


def money(value: Any) -> Decimal:
    """Quantize to paise. Never use Python float for ledger money."""
    if isinstance(value, Decimal):
        return value.quantize(_PAISE, rounding=ROUND_HALF_UP)
    return Decimal(str(value)).quantize(_PAISE, rounding=ROUND_HALF_UP)


def money_sql(value: Any) -> str:
    return format(money(value), "f")


def _charges_api_price(px: Decimal) -> float:
    """charges.order_charges still types price as float; it re-Decimals immediately."""
    return float(money_sql(px))


_PLAN_COLS = frozenset(
    {
        "plan_id",
        "account_id",
        "decision_id",
        "signal_id",
        "mode",
        "action",
        "shadow_action",
        "zone",
        "zone_price",
        "entry_distance_atr",
        "signal_candle_atr",
        "limit_price",
        "expires_at",
        "status",
        "client_order_id",
        "created_at",
        "payload_json",
    }
)
_PLAN_IMMUTABLE = frozenset({"decision_id", "signal_id", "mode", "action", "created_at"})
_PLAN_PRICE_COLS = frozenset({"zone_price", "limit_price"})
_PLAN_ATR_COLS = frozenset({"entry_distance_atr", "signal_candle_atr"})
_PLAN_DT_COLS = frozenset({"created_at", "expires_at", "bar_close_ts", "sent_at", "shadow_until", "updated_at"})


def _iso_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=IST)
        return dt.isoformat()
    return str(value)


def _atr_sql(value: Any) -> str | None:
    """Full-precision ATR. Never go through money_sql (paise quantize)."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    return format(Decimal(str(value)), "f")


_PLAN_TYPE_CACHE: dict[str, type[Any]] | None = None


def _known_plan_types() -> dict[str, type[Any]]:
    global _PLAN_TYPE_CACHE
    if _PLAN_TYPE_CACHE is not None:
        return _PLAN_TYPE_CACHE
    found: dict[str, type[Any]] = {}
    try:
        from contracts.payloads import Decision, EntryPlanResult

        found["Decision"] = Decision
        found["EntryPlanResult"] = EntryPlanResult
    except ImportError:
        pass
    try:
        from oms.planner import CardPolicy, Side  # type: ignore[import-untyped]

        found["CardPolicy"] = CardPolicy
        found["Side"] = Side
    except ImportError:
        pass
    try:
        from oms.router import Account  # type: ignore[import-untyped]

        found["Account"] = Account
    except ImportError:
        pass
    _PLAN_TYPE_CACHE = found
    return found


def _encode_plan_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return {"__enum__": type(value).__name__, "value": value.value}
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=IST)
        return {"__dt__": dt.isoformat()}
    if isinstance(value, Decimal):
        return {"__dec__": format(value, "f")}
    if is_dataclass(value) and not isinstance(value, type):
        blob: dict[str, Any] = {"__class__": type(value).__name__}
        for item in fields(value):
            blob[item.name] = _encode_plan_value(getattr(value, item.name))
        return blob
    if isinstance(value, dict):
        return {str(k): _encode_plan_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_encode_plan_value(v) for v in value]
    if hasattr(value, "__dict__") and not isinstance(value, type):
        blob = {"__class__": type(value).__name__}
        for key, item in vars(value).items():
            if not key.startswith("_"):
                blob[key] = _encode_plan_value(item)
        return blob
    return str(value)


def _construct_plan_type(cls: type[Any], payload: dict[str, Any]) -> Any:
    if isinstance(cls, type) and issubclass(cls, Enum):
        raw = payload.get("value", payload.get("name"))
        try:
            return cls(raw)
        except (TypeError, ValueError):
            return cls[str(raw)]
    if is_dataclass(cls):
        allowed = {item.name for item in fields(cls)}
        kw = {k: v for k, v in payload.items() if k in allowed}
        if cls.__name__ == "CardPolicy" and isinstance(kw.get("zones"), list):
            kw["zones"] = tuple(kw["zones"])
        return cls(**kw)
    return payload


def _decode_plan_value(value: Any) -> Any:
    if isinstance(value, dict):
        if "__dt__" in value:
            dt = datetime.fromisoformat(str(value["__dt__"]))
            return dt if dt.tzinfo is not None else dt.replace(tzinfo=IST)
        if "__dec__" in value:
            return Decimal(str(value["__dec__"]))
        if "__enum__" in value:
            cls = _known_plan_types().get(str(value["__enum__"]))
            if cls is not None:
                return _construct_plan_type(cls, value)
            return value.get("value")
        if "__class__" in value:
            inner = {k: _decode_plan_value(v) for k, v in value.items() if k != "__class__"}
            cls = _known_plan_types().get(str(value["__class__"]))
            if cls is not None:
                return _construct_plan_type(cls, inner)
            return inner
        return {str(k): _decode_plan_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_plan_value(v) for v in value]
    return value


def _aware_from_text(value: Any) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=IST)
    dt = datetime.fromisoformat(str(value))
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=IST)


def _row_to_plan(row: sqlite3.Row) -> dict[str, Any]:
    out = dict(row)
    blob = out.pop("payload_json", None)
    if blob:
        extra = json.loads(blob)
        if isinstance(extra, dict):
            out.update(_decode_plan_value(extra))
    for key in _PLAN_DT_COLS:
        if key in out and out[key] is not None and not isinstance(out[key], datetime):
            try:
                out[key] = _aware_from_text(out[key])
            except ValueError:
                pass
    for key in _PLAN_PRICE_COLS | _PLAN_ATR_COLS:
        if key in out and out[key] is not None and not isinstance(out[key], Decimal):
            try:
                out[key] = Decimal(str(out[key]))
            except (ValueError, ArithmeticError):
                pass
    return out


def _plan_payload(row: dict[str, Any]) -> dict[str, Any]:
    extras = {k: v for k, v in row.items() if k not in _PLAN_COLS}
    for key in _PLAN_PRICE_COLS | _PLAN_ATR_COLS | _PLAN_DT_COLS:
        if row.get(key) is not None:
            extras[key] = row[key]
    extras.pop("payload_json", None)
    for key in _PLAN_IMMUTABLE:
        extras.pop(key, None)
    return {k: _encode_plan_value(v) for k, v in extras.items()}


def _connect_sqlite(path: Path | str) -> sqlite3.Connection:
    """Open for reads even when the file is chmod 444 or file:...mode=ro. Never ALTER."""
    raw = str(path)
    if raw == ":memory:":
        conn = sqlite3.connect(":memory:", isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn
    if raw.startswith("file:"):
        conn = sqlite3.connect(raw, isolation_level=None, uri=True)
        conn.row_factory = sqlite3.Row
        if "mode=ro" not in raw:
            _try_wal(conn)
        return conn
    disk = Path(raw)
    if disk.exists() and not os.access(disk, os.W_OK):
        uri = f"file:{disk.resolve().as_posix()}?mode=ro"
        conn = sqlite3.connect(uri, isolation_level=None, uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    conn = sqlite3.connect(str(disk), isolation_level=None)
    conn.row_factory = sqlite3.Row
    _try_wal(conn)
    return conn


def _try_wal(conn: sqlite3.Connection) -> None:
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
    except sqlite3.OperationalError:
        return


def lot_size_for_symbol(symbol_or_id: str) -> int:
    text = (symbol_or_id or "").upper()
    for name, size in _LOT_SIZES:
        if name in text:
            return size
    return 65


def lots_from_qty(qty: int, symbol_or_id: str) -> tuple[int, int]:
    lot = lot_size_for_symbol(symbol_or_id)
    if lot <= 0 or qty <= 0 or qty % lot != 0:
        raise ValueError(f"qty {qty} is not a whole multiple of lot size {lot}")
    return qty // lot, lot


def resolve_order_qty(row: dict[str, Any]) -> int:
    """Store contracts. Never multiply an already-contract qty by lot_size."""
    symbol = str(row.get("symbol") or row.get("instrument_id") or "")
    lot = int(row["lot_size"]) if row.get("lot_size") not in (None, "") else lot_size_for_symbol(symbol)
    if row.get("qty") not in (None, ""):
        qty = int(row["qty"])
    elif row.get("lots") not in (None, ""):
        qty = int(row["lots"]) * lot
    else:
        raise ValueError("order needs qty or lots")
    if lot <= 0 or qty <= 0 or qty % lot != 0:
        raise ValueError(f"qty {qty} is not a whole multiple of lot size {lot}")
    return qty


class CheckpointEnvelope(Protocol):
    """Structural envelope. Properties so a frozen dataclass matches."""

    @property
    def event_id(self) -> str: ...

    @property
    def stream(self) -> str: ...

    @property
    def available_ts(self) -> str: ...

    @property
    def event_type(self) -> str: ...

    @property
    def payload(self) -> dict[str, Any]: ...


class SqliteTransaction:
    def __init__(self, store: SqliteLedgerStore) -> None:
        self.store = store

    def __enter__(self) -> Self:
        if self.store._in_txn:
            raise RuntimeError("nested transaction")
        self.store._in_txn = True
        self.store.conn.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        try:
            if exc_type is not None:
                self.store.conn.rollback()
            else:
                self.store.conn.commit()
        finally:
            self.store._in_txn = False


class SqliteLedgerStore:
    """V2 store. Migrations run only when migrate=True (or `python -m ledger migrate`)."""

    def __init__(
        self,
        path: Path | str,
        *,
        migrate_schema: bool = False,
        allow_legacy: bool = False,
        rates: dict[str, Any] | None = None,
        role: str = "engine",
        feed_status: str = "UP",
    ) -> None:
        raw = str(path)
        uri = raw.startswith("file:")
        if uri:
            no_qs = raw.split("?", 1)[0].removeprefix("file:")
            self.path = Path(no_qs)
        elif raw == ":memory:":
            self.path = Path(":memory:")
        else:
            self.path = Path(path)
        self.role = role
        self.feed_status = feed_status
        self._in_txn = False
        self._seq = 0
        self._crash_after: str | None = None
        check_path = self.path if uri else path
        if is_legacy_path(check_path) and not allow_legacy:
            raise LegacyPathError(f"v2 store refuses legacy path {path} unless allow_legacy=True")
        if migrate_schema and not uri:
            migrate(self.path if raw != ":memory:" else path, allow_legacy=allow_legacy)
        if raw != ":memory:" and not uri:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        # isolation_level=None: explicit BEGIN IMMEDIATE / COMMIT (no implicit txn)
        # Schema writes (ALTER / DROP+CREATE TRIGGER) happen only in migrate.py.
        self.conn = _connect_sqlite(path)
        self.schema_version = check_schema(self.conn)
        if self.schema_version > CODE_SCHEMA_VERSION:
            raise SchemaTooNew(f"{self.schema_version} > {CODE_SCHEMA_VERSION}")
        self.rates = rates
        # Bind legacy helpers to this connection. Never open the same file again
        # (Ledger() would CREATE TABLE/TRIGGER and fail on a read-only path).
        self._legacy = Ledger(":memory:", rates=rates if rates is not None else load_rates())
        self._legacy.conn.close()
        self._legacy.conn = self.conn
        self._legacy.rates = rates if rates is not None else self._legacy.rates

    def close(self) -> None:
        self.conn.close()

    def transaction(self) -> SqliteTransaction:
        return SqliteTransaction(self)

    def checkpoint(self, envelope: CheckpointEnvelope) -> None:
        if not self._in_txn:
            raise RuntimeError("checkpoint outside transaction")
        self._seq += 1
        stamp = iso_ist()
        session = datetime.fromisoformat(envelope.available_ts).astimezone(IST).date().isoformat()
        self.conn.execute(
            "INSERT INTO engine_checkpoint (role, stream, last_entry_id, input_seq, session, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(role, stream) DO UPDATE SET "
            "last_entry_id=excluded.last_entry_id, input_seq=excluded.input_seq, "
            "session=excluded.session, updated_at=excluded.updated_at",
            (self.role, envelope.stream, envelope.event_id, self._seq, session, stamp),
        )
        self.enqueue_outbox(envelope)

    def get_last_checkpoint(self) -> tuple[str, str] | None:
        row = self.conn.execute(
            "SELECT last_entry_id, updated_at FROM engine_checkpoint WHERE role=? ORDER BY input_seq DESC LIMIT 1",
            (self.role,),
        ).fetchone()
        return (row[0], row[1]) if row else None

    def enqueue_outbox(self, envelope: CheckpointEnvelope) -> None:
        payload = {
            "event_id": envelope.event_id,
            "event_type": envelope.event_type,
            "available_ts": envelope.available_ts,
            "payload": envelope.payload,
        }
        self.conn.execute(
            "INSERT OR IGNORE INTO outbox (event_id, stream, envelope_json, created_at) VALUES (?, ?, ?, ?)",
            (envelope.event_id, envelope.stream, json.dumps(payload, sort_keys=True), iso_ist()),
        )

    def drain_outbox(self) -> list[dict[str, Any]]:
        rows = [dict(r) for r in self.conn.execute("SELECT * FROM outbox WHERE published_at IS NULL ORDER BY seq")]
        stamp = iso_ist()
        for r in rows:
            self.conn.execute("UPDATE outbox SET published_at=? WHERE seq=?", (stamp, r["seq"]))
        if not self._in_txn:
            self.conn.commit()
        return rows

    def upsert_position_v2(
        self,
        account_id: str,
        instrument_id: str,
        net_qty: int,
        avg_price: Decimal | float | str,
        *,
        strategy_id: str | None = None,
        exit_plan_json: str | None = None,
        opened_at: str | None = None,
    ) -> None:
        stamp = iso_ist()
        self.conn.execute(
            "INSERT INTO positions_v2 (account_id, instrument_id, net_qty, avg_price, opened_at, "
            "strategy_id, exit_plan_json, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(account_id, instrument_id) DO UPDATE SET net_qty=excluded.net_qty, "
            "avg_price=excluded.avg_price, strategy_id=excluded.strategy_id, "
            "exit_plan_json=excluded.exit_plan_json, updated_at=excluded.updated_at",
            (
                account_id,
                instrument_id,
                net_qty,
                money_sql(avg_price),
                opened_at or stamp,
                strategy_id,
                exit_plan_json,
                stamp,
            ),
        )
        if not self._in_txn:
            self.conn.commit()

    def positions_v2(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM positions_v2 WHERE net_qty != 0")]

    def open_positions(self) -> list[dict[str, Any]]:
        if self._has_table("positions_v2"):
            rows = self.positions_v2()
            return [
                {
                    "symbol": r["instrument_id"],
                    "instrument_id": r["instrument_id"],
                    "net_qty": r["net_qty"],
                    "avg_price": r["avg_price"],
                    "account_id": r["account_id"],
                    "strategy_id": r["strategy_id"],
                    "exit_plan_json": r["exit_plan_json"],
                }
                for r in rows
            ]
        return self._legacy.open_positions()

    def open_orders(self) -> list[dict[str, Any]]:
        marks = ", ".join("?" * len(OPEN_ORDER_STATES))
        return [
            dict(r) for r in self.conn.execute(f"SELECT * FROM orders WHERE status IN ({marks})", OPEN_ORDER_STATES)
        ]

    def todays_trades(self, day: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM trades WHERE day=?", (day,))]

    def load_book(self, day: str | None = None) -> dict[str, Any]:
        return {
            "open_orders": self.open_orders(),
            "positions_v2": self.positions_v2() if self._has_table("positions_v2") else [],
            "trades": self.todays_trades(day) if day else [dict(r) for r in self.conn.execute("SELECT * FROM trades")],
        }

    def get_order(self, client_order_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM orders WHERE client_order_id=?", (client_order_id,)).fetchone()
        return dict(row) if row else None

    def get_plan(self, plan_id: str) -> dict[str, Any] | None:
        if not self._has_table("entry_plans"):
            return None
        row = self.conn.execute("SELECT * FROM entry_plans WHERE plan_id=?", (plan_id,)).fetchone()
        return _row_to_plan(row) if row is not None else None

    def upsert_plan(self, row: dict[str, Any]) -> dict[str, Any]:
        if not self._has_table("entry_plans"):
            raise RuntimeError("entry_plans table missing; run ledger migrate")
        if not self._has_column("entry_plans", "payload_json"):
            raise RuntimeError("entry_plans.payload_json missing; run ledger migrate")
        pid = str(row["plan_id"])
        created = row.get("created_at")
        created_s = _iso_text(created) if created is not None else iso_ist()
        extras = _plan_payload(row)
        self.conn.execute(
            "INSERT INTO entry_plans (plan_id, account_id, decision_id, signal_id, mode, action, "
            "shadow_action, zone, zone_price, entry_distance_atr, signal_candle_atr, limit_price, "
            "expires_at, status, client_order_id, created_at, payload_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(plan_id) DO UPDATE SET "
            "zone_price=excluded.zone_price, limit_price=excluded.limit_price, "
            "expires_at=excluded.expires_at, status=excluded.status, "
            "client_order_id=excluded.client_order_id, payload_json=excluded.payload_json",
            (
                pid,
                str(row.get("account_id") or "founder"),
                str(row.get("decision_id") or ""),
                str(row.get("signal_id") or ""),
                str(row.get("mode") or "chase"),
                str(row.get("action") or "CHASE"),
                row.get("shadow_action"),
                row.get("zone"),
                None if row.get("zone_price") is None else money_sql(row.get("zone_price")),
                None if row.get("entry_distance_atr") is None else _atr_sql(row.get("entry_distance_atr")),
                None if row.get("signal_candle_atr") is None else _atr_sql(row.get("signal_candle_atr")),
                None if row.get("limit_price") is None else money_sql(row.get("limit_price")),
                _iso_text(row.get("expires_at")),
                str(row.get("status") or "PENDING"),
                row.get("client_order_id"),
                created_s,
                json.dumps(extras, sort_keys=True),
            ),
        )
        if not self._in_txn:
            self.conn.commit()
        return self.get_plan(pid) or dict(row)

    def pending_plans(self) -> list[dict[str, Any]]:
        if not self._has_table("entry_plans"):
            return []
        rows = self.conn.execute("SELECT * FROM entry_plans WHERE status IN ('PENDING', 'WORKING')").fetchall()
        return [_row_to_plan(r) for r in rows]

    @property
    def entry_plans(self) -> dict[str, dict[str, Any]]:
        if not self._has_table("entry_plans"):
            return {}
        return {str(p["plan_id"]): p for p in (_row_to_plan(r) for r in self.conn.execute("SELECT * FROM entry_plans"))}

    def insert_order(self, row: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_order(row["client_order_id"])
        if existing is not None:
            return existing
        stamp = iso_ist()
        self.conn.execute(
            "INSERT INTO orders (client_order_id, broker_order_id, trade_id, broker, mode, symbol, "
            "instrument_id, side, qty, order_type, price, trigger_price, decision_price, purpose, "
            "status, filled_qty, avg_fill_price, exit_reason, cancel_reason, created_at, updated_at, "
            "account_id, signal_id, decision_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["client_order_id"],
                row.get("broker_order_id"),
                row.get("trade_id"),
                row.get("broker") or "paper",
                row.get("mode") or "paper",
                row.get("symbol") or row.get("instrument_id") or "",
                row.get("instrument_id"),
                row.get("side") or "BUY",
                resolve_order_qty(row),
                row.get("order_type") or "LIMIT",
                None if row.get("price") is None else money_sql(row.get("price")),
                None
                if row.get("trigger_price") is None and row.get("stop_loss") is None
                else money_sql(row.get("trigger_price") or row.get("stop_loss")),
                None
                if row.get("decision_price") is None and row.get("price") is None
                else money_sql(row.get("decision_price") or row.get("price")),
                row.get("purpose") or "ENTRY",
                row.get("state") or row.get("status") or "NEW",
                int(row.get("filled_qty") or 0),
                None if row.get("avg_fill_price") is None else money_sql(row.get("avg_fill_price")),
                row.get("exit_reason"),
                row.get("cancel_reason"),
                stamp,
                stamp,
                row.get("account_id") or "founder",
                row.get("signal_id"),
                row.get("decision_id"),
            ),
        )
        if not self._in_txn:
            self.conn.commit()
        return self.get_order(row["client_order_id"]) or dict(row)

    def mark_needs_lookup(self, client_order_id: str) -> None:
        # orders is mutable (status / broker id); not in the no-update set
        self.conn.execute(
            "UPDATE orders SET broker_order_id=COALESCE(broker_order_id, 'needs_lookup'), updated_at=? "
            "WHERE client_order_id=?",
            (iso_ist(), client_order_id),
        )
        if not self._in_txn:
            self.conn.commit()

    def mark_order_status(self, client_order_id: str, status: str, *, cancel_reason: str | None = None) -> None:
        self.conn.execute(
            "UPDATE orders SET status=?, cancel_reason=COALESCE(?, cancel_reason), updated_at=? "
            "WHERE client_order_id=?",
            (status, cancel_reason, iso_ist(), client_order_id),
        )
        self.conn.execute(
            "INSERT INTO order_events (client_order_id, ts, from_state, to_state, reason) VALUES (?,?,?,?,?)",
            (client_order_id, iso_ist(), None, status, cancel_reason or ""),
        )
        if not self._in_txn:
            self.conn.commit()

    def record_decision(self, decision: dict[str, Any]) -> None:
        self._legacy.record_decision(decision)

    def record_recon(self, mismatches: list[dict[str, Any]], ts: Any = None) -> None:
        self._legacy.record_recon(mismatches, ts)

    def record_fill(
        self,
        client_order_id: str,
        qty: int,
        price: Decimal | float | str,
        *,
        fill_model: str = "fcmeas",
        ts: datetime | None = None,
        side: str = "BUY",
        symbol: str = "",
        instrument_id: str = "",
        account_id: str = "founder",
        strategy_id: str | None = None,
        rates: dict[str, Any] | None = None,
        fill_seq: int = 1,
        fill_id: str | None = None,
    ) -> dict[str, Any]:
        px = money(price)
        qty = int(qty)
        identity = fill_id or f"{client_order_id}:{fill_seq}"
        own = False
        if not self._in_txn:
            self.conn.execute("BEGIN IMMEDIATE")
            self._in_txn = True
            own = True
        try:
            result = self._record_fill_inner(
                client_order_id,
                qty,
                px,
                fill_model=fill_model,
                ts=ts,
                side=side,
                symbol=symbol,
                instrument_id=instrument_id,
                account_id=account_id,
                strategy_id=strategy_id,
                rates=rates,
                fill_seq=fill_seq,
                fill_id=identity,
            )
            if own:
                self.conn.commit()
            return result
        except Exception:
            if own:
                self.conn.rollback()
            raise
        finally:
            if own:
                self._in_txn = False

    def _record_fill_inner(
        self,
        client_order_id: str,
        qty: int,
        px: Decimal,
        *,
        fill_model: str,
        ts: datetime | None,
        side: str,
        symbol: str,
        instrument_id: str,
        account_id: str,
        strategy_id: str | None,
        rates: dict[str, Any] | None,
        fill_seq: int,
        fill_id: str,
    ) -> dict[str, Any]:
        existing = self.conn.execute(
            "SELECT * FROM fills WHERE fill_id=? OR (client_order_id=? AND fill_seq=?)",
            (fill_id, client_order_id, fill_seq),
        ).fetchone()
        if existing is not None:
            return self._existing_fill_result(existing)
        stamp = iso_ist(ts)
        rates = rates if rates is not None else self.rates
        o = self.get_order(client_order_id)
        if o is not None:
            side = str(o.get("side") or side)
            symbol = str(o.get("symbol") or symbol)
            instrument_id = str(o.get("instrument_id") or instrument_id)
            account_id = str(o.get("account_id") or account_id)
        lot = lot_size_for_symbol(symbol or instrument_id)
        if qty <= 0 or qty % lot != 0:
            raise ValueError(f"qty {qty} is not a whole multiple of lot size {lot}")
        status = "PENDING"
        components: dict[str, Decimal] = {}
        exchange: str | None = None
        if rates is not None and rates.get(UNDERLYING_EXCHANGE):
            exchange = exchange_for(symbol or instrument_id, rates)
            if exchange is None:
                raise ValueError(f"unmapped underlying for {symbol or instrument_id!r}")
            try:
                components = {
                    k: money(v)
                    for k, v in order_charges(side, qty, _charges_api_price(px), rates, exchange=exchange).items()
                }
                status = "FINAL"
            except (ValueError, KeyError, TypeError):
                status = "PENDING"
                components = {}
        elif rates is not None:
            try:
                components = {k: money(v) for k, v in order_charges(side, qty, _charges_api_price(px), rates).items()}
                status = "FINAL"
            except (ValueError, KeyError, TypeError):
                status = "PENDING"
                components = {}
        key = instrument_id or symbol
        open_trade = self.conn.execute(
            "SELECT * FROM trades WHERE account_id=? AND instrument_id=? AND status='OPEN'",
            (account_id, key),
        ).fetchone()
        signed = qty if side == "BUY" else -qty
        is_close = open_trade is not None and (
            (open_trade["direction"] == "LONG" and side == "SELL")
            or (open_trade["direction"] == "SHORT" and side == "BUY")
        )
        trade_id = str(open_trade["trade_id"]) if is_close else ((o or {}).get("trade_id") or f"T-{client_order_id}")
        tagged = exchange or "UNKNOWN"
        if tagged == "UNKNOWN" and rates is not None and rates.get(UNDERLYING_EXCHANGE):
            raise ValueError(f"unmapped underlying for {symbol or instrument_id!r}")
        self.conn.execute(
            "INSERT INTO fills (client_order_id, trade_id, ts, symbol, side, qty, price, "
            "decision_price, slippage, fill_model, slippage_source, fill_id, fill_seq) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                client_order_id,
                trade_id,
                stamp,
                symbol,
                side,
                qty,
                money_sql(px),
                None if not o or o.get("decision_price") is None else money_sql(o.get("decision_price")),
                None,
                fill_model,
                "depth" if fill_model == "depth" else "fcmeas",
                fill_id,
                fill_seq,
            ),
        )
        if self._crash_after == "fills":
            raise RuntimeError("injected crash after fills")
        turnover = money(qty) * px
        self.conn.execute(
            "INSERT INTO charges (trade_id, client_order_id, ts, day, turnover, brokerage, stt, "
            "exchange, sebi, stamp, gst, total, charges_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                trade_id,
                client_order_id,
                stamp,
                stamp[:10],
                money_sql(turnover),
                money_sql(components["brokerage"]) if status == "FINAL" else money_sql(0),
                money_sql(components["stt"]) if status == "FINAL" else money_sql(0),
                money_sql(components["exchange"]) if status == "FINAL" else money_sql(0),
                money_sql(components["sebi"]) if status == "FINAL" else money_sql(0),
                money_sql(components["stamp"]) if status == "FINAL" else money_sql(0),
                money_sql(components["gst"]) if status == "FINAL" else money_sql(0),
                money_sql(components["total"]) if status == "FINAL" else money_sql(-1),
                status,
            ),
        )
        if is_close and open_trade is not None:
            entry_px = money(open_trade["entry_price"])
            close_qty = min(abs(int(open_trade["entry_qty"] or qty)), qty)
            if open_trade["direction"] == "LONG":
                gross = (px - entry_px) * money(close_qty)
            else:
                gross = (entry_px - px) * money(close_qty)
            self.conn.execute(
                "UPDATE trades SET status='CLOSED', exit_time=?, exit_qty=?, exit_value=?, exit_price=?, "
                "gross_pnl=?, charges=?, net_pnl=?, exchange=? WHERE trade_id=?",
                (
                    stamp,
                    close_qty,
                    money_sql(px * money(close_qty)),
                    money_sql(px),
                    money_sql(gross),
                    money_sql(0),
                    money_sql(gross),
                    tagged if tagged != "UNKNOWN" else (open_trade["exchange"] or tagged),
                    trade_id,
                ),
            )
            self._apply_trade_charges(trade_id)
        else:
            self.conn.execute(
                "INSERT INTO trades (trade_id, symbol, instrument_id, direction, status, mode, broker, "
                "entry_client_order_id, entry_time, day, entry_qty, entry_value, entry_price, account_id, "
                "strategy_id, exchange, charges, gross_pnl, net_pnl) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(trade_id) DO UPDATE SET day=excluded.day, exchange=excluded.exchange",
                (
                    trade_id,
                    symbol,
                    instrument_id,
                    "LONG" if side == "BUY" else "SHORT",
                    "OPEN",
                    "paper",
                    "paper",
                    client_order_id,
                    stamp,
                    stamp[:10],
                    qty,
                    money_sql(turnover),
                    money_sql(px),
                    account_id,
                    strategy_id,
                    tagged if tagged != "UNKNOWN" else (exchange or "UNKNOWN"),
                    money_sql(0),
                    money_sql(0),
                    money_sql(0),
                ),
            )
        prev = self.conn.execute(
            "SELECT net_qty, avg_price FROM positions_v2 WHERE account_id=? AND instrument_id=?",
            (account_id, key),
        ).fetchone()
        net = int(prev[0]) + signed if prev else signed
        if net == 0:
            avg = money(0)
        elif prev and (int(prev[0]) > 0) == (signed > 0):
            avg = (money(prev[1]) * money(abs(int(prev[0]))) + px * money(qty)) / money(abs(net))
        else:
            avg = px
        self.upsert_position_v2(account_id, key, net, avg, strategy_id=strategy_id, opened_at=stamp)
        self.conn.execute(
            "UPDATE orders SET status=?, filled_qty=filled_qty+?, avg_fill_price=?, updated_at=? "
            "WHERE client_order_id=?",
            ("FILLED", qty, money_sql(px), stamp, client_order_id),
        )
        return {
            "trade_id": trade_id,
            "charges_status": status,
            "exchange": exchange,
            "components": components,
            "client_order_id": client_order_id,
            "fill_id": fill_id,
            "fill_seq": fill_seq,
        }

    def _existing_fill_result(self, existing: sqlite3.Row) -> dict[str, Any]:
        ch = self.conn.execute(
            "SELECT charges_status, total FROM charges WHERE client_order_id=? AND trade_id=? ORDER BY id DESC LIMIT 1",
            (existing["client_order_id"], existing["trade_id"]),
        ).fetchone()
        trade = self.conn.execute("SELECT exchange FROM trades WHERE trade_id=?", (existing["trade_id"],)).fetchone()
        return {
            "trade_id": existing["trade_id"],
            "charges_status": ch["charges_status"] if ch else "PENDING",
            "exchange": trade["exchange"] if trade else None,
            "components": {},
            "client_order_id": existing["client_order_id"],
            "fill_id": existing["fill_id"],
            "fill_seq": existing["fill_seq"],
            "idempotent": True,
        }

    def _apply_trade_charges(self, trade_id: str) -> None:
        row = self.conn.execute(
            "SELECT COALESCE(SUM(total),0) FROM charges WHERE trade_id=? AND charges_status='FINAL' AND total > 0",
            (trade_id,),
        ).fetchone()
        total = money(row[0] if row else 0)
        trade = self.conn.execute("SELECT gross_pnl FROM trades WHERE trade_id=?", (trade_id,)).fetchone()
        gross = money(trade[0] if trade and trade[0] is not None else 0)
        self.conn.execute(
            "UPDATE trades SET charges=?, net_pnl=? WHERE trade_id=?",
            (money_sql(total), money_sql(gross - total), trade_id),
        )

    def recharge_pending(self, rates: dict[str, Any]) -> int:
        """REG-16c: finalize PENDING rows in place. Never add a second FINAL."""
        rows = list(self.conn.execute("SELECT * FROM charges WHERE charges_status='PENDING'"))
        n = 0
        for r in rows:
            fill = self.conn.execute(
                "SELECT * FROM fills WHERE client_order_id=? AND trade_id=?",
                (r["client_order_id"], r["trade_id"]),
            ).fetchone()
            if fill is None:
                continue
            trade = self.conn.execute("SELECT * FROM trades WHERE trade_id=?", (r["trade_id"],)).fetchone()
            symbol = (trade["symbol"] if trade else fill["symbol"]) or ""
            ex = exchange_for(symbol, rates)
            ch = {
                k: money(v)
                for k, v in order_charges(
                    fill["side"], int(fill["qty"]), _charges_api_price(money(fill["price"])), rates, exchange=ex
                ).items()
            }
            if ch["total"] == 0:
                raise RuntimeError("recharge produced zero charges; refuse")
            self.conn.execute(
                "UPDATE charges SET turnover=?, brokerage=?, stt=?, exchange=?, sebi=?, stamp=?, gst=?, "
                "total=?, charges_status='FINAL' WHERE id=?",
                (
                    money_sql(ch["turnover"]),
                    money_sql(ch["brokerage"]),
                    money_sql(ch["stt"]),
                    money_sql(ch["exchange"]),
                    money_sql(ch["sebi"]),
                    money_sql(ch["stamp"]),
                    money_sql(ch["gst"]),
                    money_sql(ch["total"]),
                    r["id"],
                ),
            )
            self._apply_trade_charges(str(r["trade_id"]))
            if ex:
                self.conn.execute("UPDATE trades SET exchange=? WHERE trade_id=?", (ex, r["trade_id"]))
            n += 1
        if n and not self._in_txn:
            self.conn.commit()
        return n

    def record_ingest_error(
        self,
        source: str,
        path: str,
        line_no: int,
        byte_offset: int,
        error: str,
        line: str,
    ) -> None:
        digest = hashlib.sha256(line.encode("utf-8", errors="replace")).hexdigest()
        self.conn.execute(
            "INSERT OR IGNORE INTO ingest_errors (source, path, line_no, byte_offset, error, line_sha256, first_seen) "
            "VALUES (?,?,?,?,?,?,?)",
            (source, path, line_no, byte_offset, error, digest, iso_ist()),
        )
        if not self._in_txn:
            self.conn.commit()

    def ingest_errors(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute("SELECT * FROM ingest_errors ORDER BY first_seen")]

    def record_halt(
        self,
        session: str,
        account_id: str,
        halt_ts: str,
        kind: str,
        forced_closes: Any,
    ) -> None:
        body = forced_closes if isinstance(forced_closes, str) else json.dumps(forced_closes)
        self.conn.execute(
            "INSERT INTO session_halts (session, account_id, halt_ts, kind, forced_closes_json, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (session, account_id, halt_ts, kind, body, iso_ist()),
        )
        if not self._in_txn:
            self.conn.commit()

    def load_halts(self) -> tuple[list[dict[str, Any]], bool]:
        """Returns (parsed_halts, unreadable). Unreadable blocks every entry (REG-05e)."""
        if not self._has_table("session_halts"):
            return [], False
        rows = list(self.conn.execute("SELECT * FROM session_halts"))
        out: list[dict[str, Any]] = []
        unreadable = False
        for r in rows:
            rec = dict(r)
            try:
                rec["forced_closes"] = json.loads(r["forced_closes_json"])
                if not isinstance(rec["forced_closes"], list):
                    raise TypeError("forced_closes must be a list")
            except (json.JSONDecodeError, TypeError, ValueError):
                unreadable = True
                rec["forced_closes"] = None
            out.append(rec)
        return out, unreadable

    def book_forced_close(self, close: dict[str, Any]) -> None:
        """Re-book a halt flatten at the saved time and price."""
        ts = close["ts"]
        self.record_fill(
            close.get("client_order_id") or f"halt-{close['instrument_id']}",
            int(close["qty"]),
            money(close["price"]),
            ts=datetime.fromisoformat(ts) if isinstance(ts, str) else ts,
            side=str(close.get("side") or "SELL"),
            symbol=str(close.get("symbol") or close["instrument_id"]),
            instrument_id=str(close["instrument_id"]),
            account_id=str(close.get("account_id") or "founder"),
            fill_model="halt",
        )

    def set_protective(self, position_key: str, stop_order_id: str) -> None:
        row = self.conn.execute(
            "SELECT * FROM positions_v2 WHERE instrument_id=? OR instrument_id LIKE ?",
            (position_key, f"%{position_key}%"),
        ).fetchone()
        if row is None:
            return
        plan = {}
        if row["exit_plan_json"]:
            try:
                plan = json.loads(row["exit_plan_json"])
            except json.JSONDecodeError:
                plan = {}
        plan["protective_stop_id"] = stop_order_id
        self.conn.execute(
            "UPDATE positions_v2 SET exit_plan_json=?, updated_at=? WHERE account_id=? AND instrument_id=?",
            (json.dumps(plan), iso_ist(), row["account_id"], row["instrument_id"]),
        )
        if not self._in_txn:
            self.conn.commit()

    def has_protective(self, position_key: str) -> bool:
        row = self.conn.execute(
            "SELECT exit_plan_json FROM positions_v2 WHERE instrument_id=?", (position_key,)
        ).fetchone()
        if row is None or not row[0]:
            return False
        try:
            return bool(json.loads(row[0]).get("protective_stop_id"))
        except json.JSONDecodeError:
            return False

    def risk_snapshot(self, now: datetime, idempotency_seconds: int) -> dict[str, Any]:
        snap = self._legacy.risk_snapshot(now, idempotency_seconds)
        if self._has_table("positions_v2"):
            snap["open_positions"] = self.conn.execute(
                "SELECT COUNT(*) FROM positions_v2 WHERE net_qty != 0"
            ).fetchone()[0]
        strategy_pnl: dict[str, str] = {}
        if self._has_column("trades", "strategy_id"):
            day = iso_ist(now)[:10]
            for r in self.conn.execute(
                "SELECT strategy_id, COALESCE(SUM(net_pnl),0) FROM trades "
                "WHERE status='CLOSED' AND day=? AND strategy_id IS NOT NULL GROUP BY strategy_id",
                (day,),
            ):
                if r[0]:
                    strategy_pnl[str(r[0])] = money_sql(r[1])
        _, halt_bad = self.load_halts()
        snap["feed_status"] = self.feed_status
        snap["strategy_pnl"] = strategy_pnl
        snap["halt_unreadable"] = halt_bad
        return snap

    def _has_table(self, name: str) -> bool:
        return (
            self.conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
            is not None
        )

    def _has_column(self, table: str, col: str) -> bool:
        cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        return col in cols

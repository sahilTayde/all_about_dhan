"""Durable LedgerStore: SQLite-WAL, checkpoint + outbox, positions_v2. Paper only."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, Self


class CheckpointEnvelope(Protocol):
    event_id: str
    stream: str
    available_ts: str
    event_type: str
    payload: dict[str, Any]
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
        self.path = Path(path) if str(path) != ":memory:" else Path(":memory:")
        self.role = role
        self.feed_status = feed_status
        self._in_txn = False
        self._seq = 0
        if is_legacy_path(path) and not allow_legacy:
            raise LegacyPathError(f"v2 store refuses legacy path {path} unless allow_legacy=True")
        if migrate_schema:
            migrate(path, allow_legacy=allow_legacy)
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.schema_version = check_schema(self.conn)
        if self.schema_version > CODE_SCHEMA_VERSION:
            raise SchemaTooNew(f"{self.schema_version} > {CODE_SCHEMA_VERSION}")
        self.rates = rates
        self._legacy = Ledger(path, rates=rates if rates is not None else load_rates())
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
        avg_price: float,
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
            (account_id, instrument_id, net_qty, avg_price, opened_at or stamp, strategy_id, exit_plan_json, stamp),
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
            dict(r)
            for r in self.conn.execute(
                f"SELECT * FROM orders WHERE status IN ({marks})", OPEN_ORDER_STATES
            )
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

    def insert_order(self, row: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_order(row["client_order_id"])
        if existing is not None:
            return existing
        stamp = iso_ist()
        self.conn.execute(
            "INSERT INTO orders (client_order_id, broker_order_id, trade_id, broker, mode, symbol, "
            "instrument_id, side, qty, order_type, price, trigger_price, decision_price, purpose, "
            "status, filled_qty, avg_fill_price, exit_reason, cancel_reason, created_at, updated_at, "
            "account_id, signal_id, decision_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                row["client_order_id"],
                row.get("broker_order_id"),
                row.get("trade_id"),
                row.get("broker") or "paper",
                row.get("mode") or "paper",
                row.get("symbol") or row.get("instrument_id") or "",
                row.get("instrument_id"),
                row.get("side") or "BUY",
                int(row.get("qty") or row.get("lots") or 0) * int(row.get("lot_size") or 1)
                if row.get("lots")
                else int(row.get("qty") or 0),
                row.get("order_type") or "LIMIT",
                row.get("price"),
                row.get("trigger_price") or row.get("stop_loss"),
                row.get("decision_price") or row.get("price"),
                row.get("purpose") or "ENTRY",
                row.get("state") or row.get("status") or "NEW",
                int(row.get("filled_qty") or 0),
                row.get("avg_fill_price"),
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

    def mark_order_status(
        self, client_order_id: str, status: str, *, cancel_reason: str | None = None
    ) -> None:
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
        price: float,
        *,
        fill_model: str = "fcmeas",
        ts: datetime | None = None,
        side: str = "BUY",
        symbol: str = "",
        instrument_id: str = "",
        account_id: str = "founder",
        strategy_id: str | None = None,
        rates: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stamp = iso_ist(ts)
        rates = rates if rates is not None else self.rates
        o = self.get_order(client_order_id)
        if o is not None:
            side = str(o.get("side") or side)
            symbol = str(o.get("symbol") or symbol)
            instrument_id = str(o.get("instrument_id") or instrument_id)
            account_id = str(o.get("account_id") or account_id)
        status = "PENDING"
        components: dict[str, float] = {}
        exchange: str | None = None
        if rates is not None and rates.get(UNDERLYING_EXCHANGE):
            exchange = exchange_for(symbol or instrument_id, rates)
            if exchange is None:
                raise ValueError(f"unmapped underlying for {symbol or instrument_id!r}")
            try:
                components = order_charges(side, qty, price, rates, exchange=exchange)
                status = "FINAL"
            except (ValueError, KeyError, TypeError):
                status = "PENDING"
                components = {}
        elif rates is not None:
            try:
                components = order_charges(side, qty, price, rates)
                status = "FINAL"
            except (ValueError, KeyError, TypeError):
                status = "PENDING"
                components = {}
        trade_id = (o or {}).get("trade_id") or f"T-{client_order_id}"
        self.conn.execute(
            "INSERT INTO fills (client_order_id, trade_id, ts, symbol, side, qty, price, "
            "decision_price, slippage, fill_model, slippage_source) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                client_order_id,
                trade_id,
                stamp,
                symbol,
                side,
                qty,
                price,
                (o or {}).get("decision_price"),
                None,
                fill_model,
                "depth" if fill_model == "depth" else "fcmeas",
            ),
        )
        turnover = float(qty) * float(price)
        self.conn.execute(
            "INSERT INTO charges (trade_id, client_order_id, ts, day, turnover, brokerage, stt, "
            "exchange, sebi, stamp, gst, total, charges_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                trade_id,
                client_order_id,
                stamp,
                stamp[:10],
                turnover,
                components.get("brokerage", 0.0) if status == "FINAL" else 0.0,
                components.get("stt", 0.0) if status == "FINAL" else 0.0,
                components.get("exchange", 0.0) if status == "FINAL" else 0.0,
                components.get("sebi", 0.0) if status == "FINAL" else 0.0,
                components.get("stamp", 0.0) if status == "FINAL" else 0.0,
                components.get("gst", 0.0) if status == "FINAL" else 0.0,
                components["total"] if status == "FINAL" else -1.0,
                status,
            ),
        )
        tagged = exchange or "UNKNOWN"
        if tagged == "UNKNOWN" and rates is not None and rates.get(UNDERLYING_EXCHANGE):
            raise ValueError(f"unmapped underlying for {symbol or instrument_id!r}")
        self.conn.execute(
            "INSERT INTO trades (trade_id, symbol, instrument_id, direction, status, mode, broker, "
            "entry_client_order_id, entry_time, day, entry_qty, entry_value, entry_price, account_id, "
            "strategy_id, exchange) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) "
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
                turnover,
                price,
                account_id,
                strategy_id,
                tagged if tagged != "UNKNOWN" else (exchange or "UNKNOWN"),
            ),
        )
        if tagged == "UNKNOWN":
            # PENDING path may lack a tag; refuse only when we had a map and still failed
            if rates is not None and rates.get(UNDERLYING_EXCHANGE):
                raise ValueError(f"unmapped underlying for {symbol or instrument_id!r}")
        signed = qty if side == "BUY" else -qty
        key = instrument_id or symbol
        prev = self.conn.execute(
            "SELECT net_qty, avg_price FROM positions_v2 WHERE account_id=? AND instrument_id=?",
            (account_id, key),
        ).fetchone()
        net = int(prev[0]) + signed if prev else signed
        if net == 0:
            avg = 0.0
        elif prev and (int(prev[0]) > 0) == (signed > 0):
            avg = (float(prev[1]) * abs(int(prev[0])) + price * qty) / abs(net)
        else:
            avg = price
        self.upsert_position_v2(account_id, key, net, avg, strategy_id=strategy_id, opened_at=stamp)
        self.conn.execute(
            "UPDATE orders SET status=?, filled_qty=filled_qty+?, avg_fill_price=?, updated_at=? "
            "WHERE client_order_id=?",
            ("FILLED", qty, price, stamp, client_order_id),
        )
        if not self._in_txn:
            self.conn.commit()
        return {
            "trade_id": trade_id,
            "charges_status": status,
            "exchange": exchange,
            "components": components,
            "client_order_id": client_order_id,
        }

    def recharge_pending(self, rates: dict[str, Any]) -> int:
        """REG-16c: apply valid rates to PENDING charge rows. Never invent a zero total."""
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
            ch = order_charges(fill["side"], int(fill["qty"]), float(fill["price"]), rates, exchange=ex)
            if ch["total"] == 0:
                raise RuntimeError("recharge produced zero charges; refuse")
            # charges is append-only: insert a FINAL correcting row; leave PENDING as history
            self.conn.execute(
                "INSERT INTO charges (trade_id, client_order_id, ts, day, turnover, brokerage, stt, "
                "exchange, sebi, stamp, gst, total, charges_status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["trade_id"],
                    r["client_order_id"],
                    iso_ist(),
                    iso_ist()[:10],
                    ch["turnover"],
                    ch["brokerage"],
                    ch["stt"],
                    ch["exchange"],
                    ch["sebi"],
                    ch["stamp"],
                    ch["gst"],
                    ch["total"],
                    "FINAL",
                ),
            )
            self.conn.execute(
                "UPDATE trades SET charges=ROUND(charges+?,2), net_pnl=ROUND(gross_pnl-(charges+?),2), "
                "exchange=? WHERE trade_id=?",
                (ch["total"], ch["total"], ex, r["trade_id"]),
            )
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
                    raise ValueError("forced_closes must be a list")
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
            float(close["price"]),
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
        strategy_pnl: dict[str, float] = {}
        if self._has_column("trades", "strategy_id"):
            day = iso_ist(now)[:10]
            for r in self.conn.execute(
                "SELECT strategy_id, COALESCE(SUM(net_pnl),0) FROM trades "
                "WHERE status='CLOSED' AND day=? AND strategy_id IS NOT NULL GROUP BY strategy_id",
                (day,),
            ):
                if r[0]:
                    strategy_pnl[str(r[0])] = float(r[1])
        _, halt_bad = self.load_halts()
        snap["feed_status"] = self.feed_status
        snap["strategy_pnl"] = strategy_pnl
        snap["halt_unreadable"] = halt_bad
        return snap

    def _has_table(self, name: str) -> bool:
        return (
            self.conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
            ).fetchone()
            is not None
        )

    def _has_column(self, table: str, col: str) -> bool:
        cols = {r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")}
        return col in cols

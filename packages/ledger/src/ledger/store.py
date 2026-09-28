"""Append-only SQLite ledger: orders, order events, fills, positions, trades, charges,
risk decisions and reconciliation runs. Daily P&L is a view over closed trades.

ponytail: stdlib sqlite3 instead of DuckDB. This is a single-writer operational store
(one desk process writes; health/API read), which is exactly SQLite's sweet spot, and
docs/02_TARGET_ARCHITECTURE.md recommends SQLite for positions/orders/ledger. DuckDB stays
the analytics warehouse; the nightly ETL can read this file directly.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Union

from ledger.charges import DEFAULT_CHARGES_PATH, exchange_for, load_rates, order_charges

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_LEDGER_PATH = Path("data/ledger/ledger.sqlite")
OPEN_ORDER_STATES = ("NEW", "SUBMITTED", "PARTIAL")

EXIT_REASONS = frozenset(
    {"TARGET_HIT", "STOP_HIT", "FLATTEN_EOD", "KILL_SWITCH", "BOSS_OVERRIDE", "FOUNDER_COMMAND", "TIME_EXIT", "MANUAL"}
)
CANCEL_REASONS = frozenset(
    {
        "USER_CANCEL",
        "KILL_SWITCH",
        "TIMEOUT_UNFILLED",
        "OCO_SIBLING_FILLED",
        "BOSS_CHANGED_MIND",
        "FOUNDER_COMMAND",
        "BROKER_CANCELLED",
        "EOD",
        "STALE_ON_RESTART",
    }
)

# Runtime alias: `str | datetime | None` is a TypeError on CPython 3.9 (PEP 604).
Ts = Union[None, str, datetime]  # noqa: UP007

SCHEMA = """
CREATE TABLE IF NOT EXISTS orders (
    client_order_id TEXT PRIMARY KEY,
    broker_order_id TEXT,
    trade_id TEXT,
    broker TEXT NOT NULL,
    mode TEXT NOT NULL,
    symbol TEXT NOT NULL,
    instrument_id TEXT,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    order_type TEXT NOT NULL,
    price REAL,
    trigger_price REAL,
    decision_price REAL,
    purpose TEXT NOT NULL,
    status TEXT NOT NULL,
    filled_qty INTEGER NOT NULL DEFAULT 0,
    avg_fill_price REAL,
    exit_reason TEXT,
    cancel_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS order_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_order_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    reason TEXT
);
CREATE TABLE IF NOT EXISTS fills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_order_id TEXT NOT NULL,
    trade_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    qty INTEGER NOT NULL,
    price REAL NOT NULL,
    decision_price REAL,
    slippage REAL
);
CREATE TABLE IF NOT EXISTS positions (
    symbol TEXT PRIMARY KEY,
    instrument_id TEXT,
    net_qty INTEGER NOT NULL,
    avg_price REAL NOT NULL,
    trade_id TEXT,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    instrument_id TEXT,
    direction TEXT NOT NULL,
    status TEXT NOT NULL,
    mode TEXT,
    broker TEXT,
    entry_client_order_id TEXT,
    entry_time TEXT,
    exit_time TEXT,
    day TEXT,
    entry_qty INTEGER NOT NULL DEFAULT 0,
    entry_value REAL NOT NULL DEFAULT 0,
    entry_price REAL,
    entry_slip_sum REAL NOT NULL DEFAULT 0,
    entry_slip_qty INTEGER NOT NULL DEFAULT 0,
    entry_slippage REAL,
    exit_qty INTEGER NOT NULL DEFAULT 0,
    exit_value REAL NOT NULL DEFAULT 0,
    exit_price REAL,
    exit_slip_sum REAL NOT NULL DEFAULT 0,
    exit_slip_qty INTEGER NOT NULL DEFAULT 0,
    exit_slippage REAL,
    gross_pnl REAL NOT NULL DEFAULT 0,
    charges REAL NOT NULL DEFAULT 0,
    net_pnl REAL NOT NULL DEFAULT 0,
    exit_reason TEXT,
    cancel_reason TEXT
);
CREATE TABLE IF NOT EXISTS charges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT NOT NULL,
    client_order_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    day TEXT NOT NULL,
    turnover REAL NOT NULL,
    brokerage REAL NOT NULL,
    stt REAL NOT NULL,
    exchange REAL NOT NULL,
    sebi REAL NOT NULL,
    stamp REAL NOT NULL,
    gst REAL NOT NULL,
    total REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS risk_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    day TEXT NOT NULL,
    client_order_id TEXT NOT NULL,
    fingerprint TEXT,
    action TEXT NOT NULL,
    approved INTEGER NOT NULL,
    reason_code TEXT NOT NULL,
    reason TEXT,
    critical INTEGER NOT NULL DEFAULT 0,
    intent_json TEXT
);
CREATE TABLE IF NOT EXISTS recon_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    ok INTEGER NOT NULL,
    mismatches_json TEXT NOT NULL
);
CREATE VIEW IF NOT EXISTS daily_pnl AS
    SELECT day, COUNT(*) AS n_trades, ROUND(SUM(gross_pnl), 2) AS gross_pnl,
           ROUND(SUM(charges), 2) AS charges, ROUND(SUM(net_pnl), 2) AS net_pnl
    FROM trades WHERE status = 'CLOSED' GROUP BY day;
"""

_NO_DELETE = ("orders", "order_events", "fills", "trades", "charges", "risk_decisions", "recon_runs")
_NO_UPDATE = ("order_events", "fills", "charges", "risk_decisions", "recon_runs")
TRIGGERS = "".join(
    f"CREATE TRIGGER IF NOT EXISTS {t}_no_delete BEFORE DELETE ON {t} "
    "BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;\n"
    for t in _NO_DELETE
) + "".join(
    f"CREATE TRIGGER IF NOT EXISTS {t}_no_update BEFORE UPDATE ON {t} "
    "BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;\n"
    for t in _NO_UPDATE
)


def iso_ist(ts: Ts = None) -> str:
    if ts is None:
        ts = datetime.now(IST)
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=IST)
        return ts.astimezone(IST).isoformat(timespec="seconds")
    return str(ts)


class Ledger:
    def __init__(
        self,
        path: str | Path = DEFAULT_LEDGER_PATH,
        *,
        rates: dict[str, float] | None = None,
        charges_path: Path = DEFAULT_CHARGES_PATH,
    ) -> None:
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.rates = rates if rates is not None else load_rates(charges_path)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA + TRIGGERS)

    def close(self) -> None:
        self.conn.close()

    def _one(self, sql: str, args: tuple = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, args).fetchone()

    def _all(self, sql: str, args: tuple = ()) -> list[dict[str, Any]]:
        return [dict(r) for r in self.conn.execute(sql, args).fetchall()]

    # ---------------------------------------------------------------- orders

    def record_order(
        self, row: dict[str, Any], from_state: str | None, to_state: str, reason: str = "", ts: Ts = None
    ) -> None:
        """Upsert the order row and append one order_events line for this transition."""
        if row.get("exit_reason") and row["exit_reason"] not in EXIT_REASONS:
            raise ValueError(f"unknown exit_reason {row['exit_reason']!r}")
        if to_state == "CANCELLED" and row.get("cancel_reason") not in CANCEL_REASONS:
            raise ValueError(f"CANCELLED needs a cancel_reason in {sorted(CANCEL_REASONS)}")
        stamp = iso_ist(ts)
        cols = (
            "client_order_id",
            "broker_order_id",
            "trade_id",
            "broker",
            "mode",
            "symbol",
            "instrument_id",
            "side",
            "qty",
            "order_type",
            "price",
            "trigger_price",
            "decision_price",
            "purpose",
            "filled_qty",
            "avg_fill_price",
            "exit_reason",
            "cancel_reason",
        )
        values = [row.get(c) for c in cols]
        mutable = ("broker_order_id", "price", "trigger_price", "filled_qty", "avg_fill_price", "cancel_reason")
        with self.conn:
            self.conn.execute(
                f"INSERT INTO orders ({', '.join(cols)}, status, created_at, updated_at) "
                f"VALUES ({', '.join('?' * len(cols))}, ?, ?, ?) "
                "ON CONFLICT(client_order_id) DO UPDATE SET status = excluded.status, "
                "updated_at = excluded.updated_at, " + ", ".join(f"{c} = excluded.{c}" for c in mutable),
                (*values, to_state, stamp, stamp),
            )
            self.conn.execute(
                "INSERT INTO order_events (client_order_id, ts, from_state, to_state, reason) VALUES (?, ?, ?, ?, ?)",
                (row["client_order_id"], stamp, from_state, to_state, reason),
            )
            if to_state == "CANCELLED" and row.get("purpose") == "ENTRY" and not row.get("filled_qty"):
                self.conn.execute(
                    "INSERT OR IGNORE INTO trades (trade_id, symbol, instrument_id, direction, status, mode, broker, "
                    "entry_client_order_id, day, cancel_reason) VALUES (?, ?, ?, ?, 'CANCELLED', ?, ?, ?, ?, ?)",
                    (
                        row.get("trade_id") or f"T-{row['client_order_id']}",
                        row["symbol"],
                        row.get("instrument_id"),
                        "LONG" if row["side"] == "BUY" else "SHORT",
                        row.get("mode"),
                        row.get("broker"),
                        row["client_order_id"],
                        stamp[:10],
                        row["cancel_reason"],
                    ),
                )

    def order_events(self, client_order_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM order_events WHERE client_order_id = ? ORDER BY id", (client_order_id,))

    def open_orders(self) -> list[dict[str, Any]]:
        marks = ", ".join("?" * len(OPEN_ORDER_STATES))
        return self._all(f"SELECT * FROM orders WHERE status IN ({marks})", OPEN_ORDER_STATES)

    # ----------------------------------------------------------------- fills

    def record_fill(self, client_order_id: str, qty: int, price: float, ts: Ts = None) -> str:
        """Record one fill: fills + charges rows, position update, trade open/close. Returns trade_id."""
        if qty <= 0 or price < 0:
            raise ValueError("fill needs qty > 0 and price >= 0")
        o = self._one("SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,))
        if o is None:
            raise KeyError(f"unknown order {client_order_id}")
        stamp = iso_ist(ts)
        dp = o["decision_price"]
        slip = None if dp is None else round(price - dp, 4)
        signed = qty if o["side"] == "BUY" else -qty
        with self.conn:
            first = self._one("SELECT 1 FROM fills WHERE client_order_id = ? LIMIT 1", (client_order_id,)) is None
            ch = order_charges(
                o["side"],
                qty,
                price,
                self.rates,
                include_brokerage=first,
                exchange=exchange_for(o["symbol"], self.rates),
            )
            pos = self._one("SELECT * FROM positions WHERE symbol = ?", (o["symbol"],))
            net = pos["net_qty"] if pos else 0
            avg = pos["avg_price"] if pos else 0.0
            trade_id = pos["trade_id"] if pos and net else None
            charge_trade = None
            remaining = signed
            if net and (net > 0) != (signed > 0):
                closing = min(abs(net), abs(signed))
                direction = 1 if net > 0 else -1
                self._add_leg("exit", trade_id, closing, price, slip)
                self.conn.execute(
                    "UPDATE trades SET gross_pnl = gross_pnl + ? WHERE trade_id = ?",
                    ((price - avg) * closing * direction, trade_id),
                )
                net -= direction * closing
                remaining += direction * closing
                charge_trade = trade_id
                if net == 0:
                    self.conn.execute(
                        "UPDATE trades SET status = 'CLOSED', exit_time = ?, day = ?, exit_reason = ? WHERE trade_id = ?",
                        (stamp, stamp[:10], o["exit_reason"], trade_id),
                    )
            if remaining:
                if net == 0:
                    trade_id = self._open_trade(o, stamp)
                    avg = 0.0
                new_net = net + remaining
                avg = (avg * abs(net) + price * abs(remaining)) / abs(new_net)
                self._add_leg("entry", trade_id, abs(remaining), price, slip)
                net = new_net
                charge_trade = charge_trade or trade_id
            self.conn.execute(
                "INSERT INTO positions (symbol, instrument_id, net_qty, avg_price, trade_id, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(symbol) DO UPDATE SET net_qty = excluded.net_qty, "
                "avg_price = excluded.avg_price, trade_id = excluded.trade_id, updated_at = excluded.updated_at",
                (o["symbol"], o["instrument_id"], net, avg if net else 0.0, trade_id if net else None, stamp),
            )
            self.conn.execute(
                "INSERT INTO fills (client_order_id, trade_id, ts, symbol, side, qty, price, decision_price, slippage) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (client_order_id, charge_trade, stamp, o["symbol"], o["side"], qty, price, dp, slip),
            )
            self.conn.execute(
                "INSERT INTO charges (trade_id, client_order_id, ts, day, turnover, brokerage, stt, exchange, sebi, "
                "stamp, gst, total) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    charge_trade,
                    client_order_id,
                    stamp,
                    stamp[:10],
                    float(ch["turnover"]),
                    float(ch["brokerage"]),
                    float(ch["stt"]),
                    float(ch["exchange"]),
                    float(ch["sebi"]),
                    float(ch["stamp"]),
                    float(ch["gst"]),
                    float(ch["total"]),
                ),
            )
            self.conn.execute(
                "UPDATE trades SET charges = ROUND(charges + ?, 2), net_pnl = ROUND(gross_pnl - (charges + ?), 2) "
                "WHERE trade_id = ?",
                (float(ch["total"]), float(ch["total"]), charge_trade),
            )
        return charge_trade

    def _open_trade(self, o: sqlite3.Row, stamp: str) -> str:
        base = o["trade_id"] or f"T-{o['client_order_id']}"
        trade_id, n = base, 1
        while self._one("SELECT 1 FROM trades WHERE trade_id = ?", (trade_id,)):
            n += 1
            trade_id = f"{base}-{n}"
        self.conn.execute(
            "INSERT INTO trades (trade_id, symbol, instrument_id, direction, status, mode, broker, "
            "entry_client_order_id, entry_time) VALUES (?, ?, ?, ?, 'OPEN', ?, ?, ?, ?)",
            (
                trade_id,
                o["symbol"],
                o["instrument_id"],
                "LONG" if o["side"] == "BUY" else "SHORT",
                o["mode"],
                o["broker"],
                o["client_order_id"],
                stamp,
            ),
        )
        return trade_id

    def _add_leg(self, leg: str, trade_id: str, qty: int, price: float, slip: float | None) -> None:
        ss, sq = (slip * qty, qty) if slip is not None else (0.0, 0)
        self.conn.execute(
            f"UPDATE trades SET {leg}_qty = {leg}_qty + :q, {leg}_value = {leg}_value + :q * :p, "
            f"{leg}_price = ROUND(({leg}_value + :q * :p) / ({leg}_qty + :q), 4), "
            f"{leg}_slip_sum = {leg}_slip_sum + :ss, {leg}_slip_qty = {leg}_slip_qty + :sq, "
            f"{leg}_slippage = CASE WHEN {leg}_slip_qty + :sq > 0 "
            f"THEN ROUND(({leg}_slip_sum + :ss) / ({leg}_slip_qty + :sq), 4) END "
            "WHERE trade_id = :t",
            {"q": qty, "p": price, "ss": ss, "sq": sq, "t": trade_id},
        )

    # --------------------------------------------------------------- queries

    def open_positions(self) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM positions WHERE net_qty != 0 ORDER BY symbol")

    def trades(self, day: str | None = None) -> list[dict[str, Any]]:
        if day:
            return self._all("SELECT * FROM trades WHERE day = ? ORDER BY entry_time", (day,))
        return self._all("SELECT * FROM trades ORDER BY entry_time")

    def trade(self, trade_id: str) -> dict[str, Any] | None:
        row = self._one("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        return dict(row) if row else None

    def charges_for(self, trade_id: str) -> list[dict[str, Any]]:
        return self._all("SELECT * FROM charges WHERE trade_id = ? ORDER BY id", (trade_id,))

    def daily_pnl(self, day: str) -> dict[str, Any]:
        row = self._one("SELECT * FROM daily_pnl WHERE day = ?", (day,))
        return dict(row) if row else {"day": day, "n_trades": 0, "gross_pnl": 0.0, "charges": 0.0, "net_pnl": 0.0}

    # ------------------------------------------------- risk + reconciliation

    def record_decision(self, decision: dict[str, Any]) -> None:
        stamp = iso_ist(decision.get("ts"))
        with self.conn:
            self.conn.execute(
                "INSERT INTO risk_decisions (ts, day, client_order_id, fingerprint, action, approved, reason_code, "
                "reason, critical, intent_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    stamp,
                    stamp[:10],
                    decision["client_order_id"],
                    decision.get("fingerprint"),
                    decision["action"],
                    int(bool(decision["approved"])),
                    decision["reason_code"],
                    decision.get("reason"),
                    int(bool(decision.get("critical"))),
                    json.dumps(decision.get("intent"), default=str),
                ),
            )

    def record_recon(self, mismatches: list[dict[str, Any]], ts: Ts = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO recon_runs (ts, ok, mismatches_json) VALUES (?, ?, ?)",
                (iso_ist(ts), int(not mismatches), json.dumps(mismatches, default=str)),
            )

    def risk_snapshot(self, now: datetime, idempotency_seconds: int) -> dict[str, Any]:
        """Everything the risk engine needs, rebuilt from disk (so a restart loses nothing)."""
        stamp = iso_ist(now)
        day = stamp[:10]
        since = iso_ist(now - timedelta(seconds=idempotency_seconds))
        last_loss = self._one(
            "SELECT MAX(exit_time) FROM trades WHERE status = 'CLOSED' AND day = ? AND net_pnl < 0", (day,)
        )[0]
        recon = self._one("SELECT ok FROM recon_runs ORDER BY id DESC LIMIT 1")
        return {
            "open_positions": self._one("SELECT COUNT(*) FROM positions WHERE net_qty != 0")[0],
            "realized_pnl_today": self._one(
                "SELECT COALESCE(SUM(net_pnl), 0) FROM trades WHERE status = 'CLOSED' AND day = ?", (day,)
            )[0],
            "last_loss_exit_at": datetime.fromisoformat(last_loss) if last_loss else None,
            "recent_fingerprints": [
                (datetime.fromisoformat(r["ts"]), r["fingerprint"])
                for r in self._all(
                    "SELECT ts, fingerprint FROM risk_decisions WHERE approved = 1 AND action = 'ENTRY' AND ts >= ?",
                    (since,),
                )
            ],
            "used_client_order_ids": {
                r["client_order_id"]
                for r in self._all(
                    "SELECT client_order_id FROM risk_decisions WHERE approved = 1 AND action IN ('ENTRY', 'EXIT') "
                    "AND day = ?",
                    (day,),
                )
            },
            "recon_ok": True if recon is None else bool(recon["ok"]),
            "feed_status": getattr(self, "feed_status", "UP"),
            "strategy_pnl": {},
            "halt_unreadable": False,
        }

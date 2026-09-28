-- V1 operational ledger (same tables as ledger.store.SCHEMA). Additive only.
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

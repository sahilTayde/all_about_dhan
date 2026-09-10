"""DDL for DATA-001/002. Schema version 3 adds strike rows + constituents.

Tiers match docs/PRODUCT_ARCHITECTURE_STANDARDS.md.
counsel_events matches TOKEN_ML_STRATEGY.md cache keys.

Timeframes: HQ 1m/5m/15m/60m + daily; 3m resampled from 1m; 1w resampled from 1d.
HQ enum has no 3m and no week candle.
"""

from __future__ import annotations

SCHEMA_VERSION = 3

DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_market_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    symbol TEXT NOT NULL,
    segment TEXT NOT NULL,
    received_at TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (source, symbol, segment, received_at, payload_hash)
);

CREATE TABLE IF NOT EXISTS bars_1m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    oi REAL,
    source TEXT NOT NULL,
    UNIQUE (symbol, ts, source)
);

CREATE TABLE IF NOT EXISTS bars_5m (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    oi REAL,
    source TEXT NOT NULL,
    UNIQUE (symbol, ts, source)
);

CREATE TABLE IF NOT EXISTS chain_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    underlying TEXT NOT NULL,
    ts TEXT NOT NULL,
    expiry TEXT,
    atm TEXT,
    pcr REAL,
    payload_hash TEXT NOT NULL,
    payload_json TEXT,
    UNIQUE (underlying, ts, payload_hash)
);

CREATE TABLE IF NOT EXISTS features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    ts TEXT NOT NULL,
    feature_set_version TEXT NOT NULL,
    feature_json TEXT NOT NULL,
    UNIQUE (symbol, ts, feature_set_version)
);

CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL UNIQUE,
    ts TEXT NOT NULL,
    underlying TEXT NOT NULL,
    stage TEXT NOT NULL,
    side TEXT,
    levels_json TEXT,
    model_version TEXT,
    feature_set_version TEXT,
    is_paper INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS ticket_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    ts TEXT NOT NULL,
    old_state TEXT,
    new_state TEXT NOT NULL,
    reason_code TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    exit_reason TEXT,
    points REAL,
    is_mock INTEGER NOT NULL DEFAULT 1,
    ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_sources (
    source_id TEXT PRIMARY KEY,
    url TEXT,
    title TEXT,
    retrieved_at TEXT,
    layer TEXT NOT NULL,
    hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rag_chunks (
    chunk_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    kind TEXT,
    layer TEXT NOT NULL,
    text TEXT NOT NULL,
    fts_terms TEXT
);

CREATE TABLE IF NOT EXISTS model_runs (
    run_id TEXT PRIMARY KEY,
    model_version TEXT NOT NULL,
    train_window TEXT,
    test_window TEXT,
    metrics_json TEXT,
    verdict TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS counsel_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    facts_hash TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    prompt_version TEXT NOT NULL,
    token_estimate INTEGER,
    output_hash TEXT,
    verdict TEXT,
    together TEXT,
    ts TEXT NOT NULL,
    UNIQUE (job_id, facts_hash, prompt_version, model)
);

CREATE INDEX IF NOT EXISTS idx_raw_symbol_ts ON raw_market_events (symbol, received_at);
CREATE TABLE IF NOT EXISTS ohlc_bars (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    ts TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    oi REAL,
    source TEXT NOT NULL,
    origin TEXT NOT NULL,
    UNIQUE (symbol, timeframe, ts, source)
);

CREATE INDEX IF NOT EXISTS idx_bars1_symbol_ts ON bars_1m (symbol, ts);
CREATE INDEX IF NOT EXISTS idx_bars5_symbol_ts ON bars_5m (symbol, ts);
CREATE INDEX IF NOT EXISTS idx_ohlc_sym_tf_ts ON ohlc_bars (symbol, timeframe, ts);
CREATE INDEX IF NOT EXISTS idx_chain_und_ts ON chain_snapshots (underlying, ts);
CREATE INDEX IF NOT EXISTS idx_feat_symbol_ts ON features (symbol, ts);
CREATE INDEX IF NOT EXISTS idx_ticket_signal_ts ON ticket_events (signal_id, ts);
CREATE INDEX IF NOT EXISTS idx_research_layer ON research_sources (source_id, layer);
CREATE INDEX IF NOT EXISTS idx_counsel_job_ts ON counsel_events (job_id, ts);

CREATE TABLE IF NOT EXISTS chain_strike_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    underlying TEXT NOT NULL,
    expiry TEXT,
    as_of TEXT NOT NULL,
    strike REAL NOT NULL,
    ce_ltp REAL,
    pe_ltp REAL,
    ce_oi INTEGER,
    pe_oi INTEGER,
    ce_oi_prev INTEGER,
    pe_oi_prev INTEGER,
    ce_volume INTEGER,
    pe_volume INTEGER,
    ce_security_id INTEGER,
    pe_security_id INTEGER,
    ce_delta REAL,
    pe_delta REAL,
    ce_gamma REAL,
    pe_gamma REAL,
    ce_theta REAL,
    pe_theta REAL,
    ce_vega REAL,
    pe_vega REAL,
    ce_iv REAL,
    pe_iv REAL
);

CREATE TABLE IF NOT EXISTS option_levels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    underlying TEXT NOT NULL,
    expiry TEXT,
    as_of TEXT NOT NULL,
    side TEXT NOT NULL,
    strike REAL,
    entry REAL,
    stop_hyp REAL,
    target_hyp REAL,
    dealer_action TEXT,
    dealer_reason TEXT,
    layer TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS index_constituents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    as_of TEXT NOT NULL,
    index_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    security_id TEXT,
    segment TEXT,
    weight_pct REAL,
    weight_layer TEXT NOT NULL,
    ltp REAL,
    quote_ok INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_strikes_snap ON chain_strike_rows (snapshot_id, strike);
CREATE INDEX IF NOT EXISTS idx_levels_und ON option_levels (underlying, as_of);
CREATE INDEX IF NOT EXISTS idx_const_idx ON index_constituents (index_id, as_of);
"""

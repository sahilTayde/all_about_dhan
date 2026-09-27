-- V2-10 schema additions (architecture §3.3). Additive; never DROP/RENAME.
ALTER TABLE orders       ADD COLUMN account_id TEXT NOT NULL DEFAULT 'founder';
ALTER TABLE orders       ADD COLUMN signal_id TEXT;
ALTER TABLE orders       ADD COLUMN decision_id TEXT;
ALTER TABLE fills        ADD COLUMN fill_model TEXT;
ALTER TABLE fills        ADD COLUMN slippage_source TEXT;
ALTER TABLE trades       ADD COLUMN account_id TEXT NOT NULL DEFAULT 'founder';
ALTER TABLE trades       ADD COLUMN strategy_id TEXT;
ALTER TABLE trades       ADD COLUMN exchange TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE charges      ADD COLUMN charges_status TEXT NOT NULL DEFAULT 'FINAL';

CREATE TABLE IF NOT EXISTS positions_v2 (
  account_id TEXT NOT NULL, instrument_id TEXT NOT NULL, net_qty INTEGER NOT NULL,
  avg_price NUMERIC(18,4) NOT NULL, opened_at TEXT, strategy_id TEXT, exit_plan_json TEXT,
  updated_at TEXT NOT NULL, PRIMARY KEY (account_id, instrument_id));

CREATE TABLE IF NOT EXISTS engine_checkpoint (
  role TEXT NOT NULL, stream TEXT NOT NULL, last_entry_id TEXT NOT NULL, input_seq INTEGER NOT NULL,
  session TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY (role, stream));

CREATE TABLE IF NOT EXISTS outbox (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, stream TEXT NOT NULL,
  envelope_json TEXT NOT NULL, created_at TEXT NOT NULL, published_at TEXT);

CREATE TABLE IF NOT EXISTS founder_commands (
  command_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, kind TEXT NOT NULL, args_json TEXT NOT NULL,
  actor TEXT NOT NULL, reason TEXT, received_ts TEXT NOT NULL, applied_ts TEXT, status TEXT NOT NULL,
  status_reason TEXT);

CREATE TABLE IF NOT EXISTS strategy_day_stats (
  session TEXT NOT NULL, strategy_id TEXT NOT NULL, version TEXT NOT NULL, stage TEXT NOT NULL,
  signals INTEGER, decisions INTEGER, trades INTEGER, gross_pnl NUMERIC(18,4), net_pnl NUMERIC(18,4),
  disabled_reason TEXT, PRIMARY KEY (session, strategy_id, version));

CREATE TABLE IF NOT EXISTS session_halts (
  session TEXT NOT NULL, account_id TEXT NOT NULL, halt_ts TEXT NOT NULL, kind TEXT NOT NULL,
  forced_closes_json TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS ingest_errors (
  source TEXT NOT NULL, path TEXT NOT NULL, line_no INTEGER NOT NULL, byte_offset INTEGER NOT NULL,
  error TEXT NOT NULL, line_sha256 TEXT NOT NULL, first_seen TEXT NOT NULL,
  PRIMARY KEY (source, path, line_no));

CREATE TABLE IF NOT EXISTS forward_trades (
  spec_id TEXT NOT NULL, spec_hash TEXT NOT NULL, session TEXT NOT NULL, signal_id TEXT NOT NULL,
  leg TEXT NOT NULL,
  entry_ts TEXT, exit_ts TEXT, exit_reason TEXT, gross_inr NUMERIC(18,4), net_depth_inr NUMERIC(18,4),
  net_fcmeas_inr NUMERIC(18,4), PRIMARY KEY (spec_id, signal_id, leg));

CREATE TABLE IF NOT EXISTS forward_checkpoints (
  spec_id TEXT NOT NULL, spec_hash TEXT NOT NULL, session TEXT NOT NULL, n INTEGER NOT NULL,
  state TEXT NOT NULL, stats_json TEXT NOT NULL, PRIMARY KEY (spec_id, session));

CREATE TABLE IF NOT EXISTS entry_plans (
  plan_id TEXT PRIMARY KEY, account_id TEXT NOT NULL, decision_id TEXT NOT NULL, signal_id TEXT NOT NULL,
  mode TEXT NOT NULL, action TEXT NOT NULL, shadow_action TEXT, zone TEXT, zone_price NUMERIC(18,4),
  entry_distance_atr NUMERIC(18,4), signal_candle_atr NUMERIC(18,4), limit_price NUMERIC(18,4),
  expires_at TEXT, status TEXT NOT NULL, client_order_id TEXT, created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL);

-- REG-17d: backfill exchange from the symbol's underlying (v2 never writes UNKNOWN).
UPDATE trades SET exchange = 'BSE'
 WHERE exchange IN ('UNKNOWN', '')
   AND (UPPER(symbol) LIKE 'SENSEX%' OR UPPER(symbol) LIKE 'BANKEX%');
UPDATE trades SET exchange = 'NSE'
 WHERE exchange IN ('UNKNOWN', '')
   AND (UPPER(symbol) LIKE 'NIFTY%' OR UPPER(symbol) LIKE 'BANKNIFTY%'
        OR UPPER(symbol) LIKE 'FINNIFTY%' OR UPPER(symbol) LIKE 'MIDCPNIFTY%');

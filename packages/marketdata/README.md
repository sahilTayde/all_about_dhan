# marketdata

V2 market data recorder: depth, quotes, and OI cadence (V2-D2). Standalone package, no dependency on contracts.

## Installation

```bash
# From repo root
uv pip install -e packages/dhan-client -e packages/marketdata
# or
pip install -e packages/dhan-client -e packages/marketdata
```

## Usage

Set credentials in environment or `.env` file in repo root:
```bash
export DHAN_CLIENT_ID=your_client_id
export DHAN_ACCESS_TOKEN=your_access_token
```

Run recorder:
```bash
# NIFTY (default)
python -m marketdata --record-only

# BANKNIFTY
python -m marketdata --record-only --underlying BANKNIFTY

# SENSEX
python -m marketdata --record-only --underlying SENSEX
```

## Output

Tapes written to `data/tape/v2/YYYY-MM-DD/` (IST date) from repo root:
- `depth_quotes.jsonl` - DEPTH_QUOTE per instrument, ≤1/sec, heartbeat every 1s
- `quote_snapshots.jsonl` - QUOTE_SNAPSHOT every 5s (options only)
- `oi_cadence.jsonl` - OI update stats every minute
- `raw_frames.jsonl` - Base64 raw frames (while DECODER_VERIFIED=False)
- `ingest_errors.jsonl` - Bad frames/packets with reason and sha256
- `coverage_summary.json` - Daily coverage stats (written at 15:30 IST stop)

Recorder stops automatically at 15:30 IST. Use Ctrl-C to stop early.

## Scope

- Paper only: market data recording, no order placement
- Standalone: no Redis, no event bus, no engine
- Crash-safe: append-only JSONL, fsync every 1s, repairs truncated lines
- No credentials in logs or tapes

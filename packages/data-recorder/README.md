# Market Data Recorder

Daily market data capture for DhanHQ: index ticks, futures with volume, option chain with OI/IV/greeks, heavyweights, news, and global markets.

**Priority: P0 — HIGHEST.** This data **cannot be backfilled**. Start recording immediately.

## Features

✅ **Reuses existing Dhan client infrastructure** (`dhan-client`, `desk-intel`)
✅ **Respects existing rate limits** (3-minute option chain polling)
✅ **No competing websocket connections** (extends existing feed infrastructure)
✅ **Read-only** (no order endpoints, only market data)
✅ **Daily file rotation** (YYYYMMDD.jsonl format)
✅ **Graceful shutdown** (SIGINT/SIGTERM handlers)
✅ **Health heartbeat** (written every minute)
✅ **Dry-run mode** (test without credentials)

## Quick Start

### Dry-Run (No Credentials Needed)

Test the recorder without calling Dhan API:

```bash
# From repo root
./scripts/start_recorder.sh --dry-run

# Check output files
ls -lh data/recon/*/
cat data/recon/index_ticks/*.jsonl | head -1 | python3 -m json.tool

# Stop recorder
./scripts/stop_recorder.sh
```

### Production Mode

**Requirements:**
1. Dhan credentials (set in `.env` or environment variables)
2. Python packages: `feedparser`, `yfinance` (for news and global markets)

```bash
# Install dependencies
pip install feedparser yfinance

# Set credentials (DO NOT commit these)
export DHAN_CLIENT_ID="your_client_id"
export DHAN_ACCESS_TOKEN="your_access_token"

# Start recorder
./scripts/start_recorder.sh

# Check status
tail -f /tmp/recorder.log
tail -f data/recon/recorder_heartbeat.jsonl

# Stop recorder
./scripts/stop_recorder.sh
```

## File Layout

Data is written to `data/recon/` (gitignored):

```
data/recon/
├── index_ticks/20260926.jsonl         # NIFTY, BANKNIFTY, SENSEX 1-min OHLCV
├── futures_ticks/20260926.jsonl       # Futures with volume (CRITICAL)
├── option_chain/20260926.jsonl        # All strikes, OI/IV/greeks (CRITICAL)
├── heavyweight_ticks/20260926.jsonl   # Top 15 NIFTY stocks
├── news/20260926.jsonl                # MoneyControl, Economic Times headlines
├── global_markets/20260926.jsonl      # SPY, DXY, US10Y, crude, gold, USDINR, VIX
└── recorder_heartbeat.jsonl           # Health status (updated every minute)
```

## Data Schemas

### Index Ticks

```json
{
    "symbol": "NIFTY",
    "timestamp": "2026-09-26T11:53:00",
    "open": 19800.0,
    "high": 19820.0,
    "low": 19785.0,
    "close": 19810.0,
    "volume": null
}
```

### Futures Ticks (CRITICAL: volume field)

```json
{
    "symbol": "NIFTYFUT",
    "expiry": "2026-09-30",
    "timestamp": "2026-09-26T11:53:00",
    "open": 19850.0,
    "high": 19875.0,
    "low": 19832.0,
    "close": 19862.0,
    "volume": 1234567,
    "open_interest": 5000000
}
```

### Option Chain (CRITICAL: OI, IV, greeks)

```json
{
    "underlying": "NIFTY",
    "expiry": "2026-09-26",
    "strike": 19700.0,
    "option_type": "CE",
    "timestamp": "2026-09-26T11:53:00",
    "ltp": 80.0,
    "bid": 79.5,
    "ask": 80.5,
    "volume": 12345,
    "open_interest": 500000,
    "iv": 0.16,
    "delta": 0.5,
    "gamma": 0.001,
    "theta": -5.0,
    "vega": 10.0
}
```

## Rate Limits & Feed Sharing

- **Option chain**: Polls every **3 minutes** (respects existing `desk_intel.option_chain_poller` limit)
- **Websocket feeds**: Reuses existing `DhanClient.feed_collector()` infrastructure
- **No conflicts**: Recorder uses separate feed subscriptions; does not interfere with paper trading engine

## Tests

Run tests to validate behavior:

```bash
# Unit tests (writer behavior)
python3 packages/data-recorder/tests/test_writer.py

# Dry-run integration tests (schemas, file layout)
python3 packages/data-recorder/tests/test_dry_run.py
```

Expected output:
```
✅ CRITICAL check passed: futures volume = 1234567
✅ CRITICAL checks passed: OI=500000, IV=0.16
✅ All dry-run tests passed!
```

## Production Checklist

Before running in production:

1. ✅ Set `DHAN_CLIENT_ID` and `DHAN_ACCESS_TOKEN` (never commit)
2. ✅ Install dependencies: `pip install feedparser yfinance`
3. ✅ Test dry-run mode first: `./scripts/start_recorder.sh --dry-run`
4. ✅ Run production for 5 minutes, check logs and files
5. ✅ Verify futures volume > 0, option OI/IV present
6. ✅ Schedule for market hours (09:00-15:35 IST via cron/systemd)

## Known TODOs (for production implementation)

1. **Instrument lookup**: Futures and heavyweight instruments need full instrument master parsing
   - Use `client.instruments.fetch_scrip_master_text()` to fetch CSV
   - Filter by symbol + instrument type + expiry
   - Extract security IDs for feed subscriptions

2. **Greeks computation**: If Dhan API doesn't return greeks, compute client-side
   - Use Black-Scholes formula with spot, strike, expiry, IV, interest rate
   - Or use sensibull-style approximation

3. **Error handling**: Add retry logic for network errors
   - Reconnect websocket on disconnect
   - Retry REST calls 3× with exponential backoff
   - Log errors and alert founder (via PR-004 health monitoring)

## Troubleshooting

**Recorder won't start in production:**
- Check credentials: `echo $DHAN_CLIENT_ID`
- Check dependencies: `python3 -c "import feedparser, yfinance"`
- Check logs: `tail -f /tmp/recorder.log`

**No data being written:**
- Check heartbeat: `tail -f data/recon/recorder_heartbeat.jsonl`
- If heartbeat is updating, recorder is alive but may have subscription issues
- Check logs for errors

**High CPU usage:**
- Check number of websocket subscriptions (max 5000 instruments per connection)
- Reduce heavyweight symbols list if needed

## Architecture Notes

**Why not duplicate logic:**
- Reuses `dhan-client.DhanClient` for REST + websocket
- Reuses `dhan-client.instruments` for security ID lookup
- Reuses `desk_intel.option_chain_poller` rate limiting
- No new credential loading (uses existing `dhan-client.config`)

**Why separate from paper trading:**
- Independent process (crash in recorder doesn't affect trading)
- Different data retention (trading only needs recent data; recorder archives forever)
- Different rate limits (trading needs real-time; recorder can batch/poll)

**Data flow:**
```
Dhan API → DhanClient (existing) → Recorder → JSON Lines files → Warehouse (PR-013)
```

## Next Steps

1. **After 1 month of recording**: Start PR-013 (nightly warehouse ETL) to make data queryable
2. **After warehouse ETL**: Run backtests on real historical data
3. **After validation**: Deploy proven fixes from Phase 3 tape runs

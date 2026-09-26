# Data Recorder for all_about_dhan

**Purpose:** Records market data daily (cannot be backfilled). Runs independently of trading loop.

**Priority:** **P0 — Highest.** Start immediately (PR-001 in migration plan).

---

## What It Records

1. **Index ticks (1-min OHLCV):** NIFTY, BANKNIFTY, SENSEX
2. **Futures ticks (1-min OHLCV + volume + OI):** NIFTYFUT, BANKNIFTYFUT, SENSEXFUT
3. **Option chain (per minute, all strikes):** LTP, bid, ask, volume, OI, IV, greeks (delta, gamma, theta, vega)
4. **Heavyweights (1-min LTP):** Top 15 NIFTY stocks (Reliance, TCS, HDFC Bank, etc.)
5. **News (headlines):** MoneyControl, Economic Times RSS feeds
6. **Global markets (daily close):** SPX, DXY, US10Y, crude, gold, USDINR

**Output:** JSON Lines (`.jsonl`) files under `data/recon/` (gitignored). One file per source per day.

**Pattern:** `data/recon/{source}/YYYYMMDD.jsonl`

Example:
```
data/recon/index_ticks/20260926.jsonl
data/recon/futures_ticks/20260926.jsonl
data/recon/option_chain/20260926.jsonl
data/recon/heavyweight_ticks/20260926.jsonl
data/recon/news/20260926.jsonl
data/recon/global_markets/20260926.jsonl
```

---

## How to Run (For Sahil)

### Dry-Run Mode (Testing, No Credentials Needed)

Generates synthetic data to test file layout, rotation, and restart behavior:

```bash
cd /workspace
python -m data_recorder.runner
```

or (if installed via pip):

```bash
data-recorder
```

This will:
- Create `data/recon/` directory
- Generate synthetic ticks (a few records per source)
- Write to `.jsonl` files with today's date
- Exit after ~1 second

**Check output:**
```bash
ls -lh data/recon/*/
cat data/recon/index_ticks/20260926.jsonl | head -3
```

### Production Mode (Real Market Data)

**Prerequisites:**
1. Dhan API credentials:
   - `DHAN_TOKEN` environment variable (from Dhan login)
   - `DHAN_CLIENT_ID` environment variable
2. Install dependencies:
   ```bash
   pip install feedparser yfinance
   ```
   (For news scraping and global markets; Dhan websocket TBD based on Dhan SDK)

**Run:**
```bash
export DHAN_TOKEN="your_token_here"
export DHAN_CLIENT_ID="your_client_id_here"
python -m data_recorder.runner --production
```

**Schedule (recommended):**

Run at **09:00 IST** (before market open at 09:15), stop at **15:35 IST** (5 min after close).

Using cron:
```cron
0 9 * * 1-5 cd /workspace && /path/to/venv/bin/python -m data_recorder.runner --production >> logs/data_recorder.log 2>&1
35 15 * * 1-5 pkill -f "data_recorder.runner"
```

Or systemd timer (better for VPS).

**Monitor:**
```bash
tail -f logs/data_recorder.log
ls -lh data/recon/*/$(date +%Y%m%d).jsonl
```

---

## File Format

**JSON Lines (`.jsonl`):** One JSON object per line (not an array). Easy to append, easy to resume after crash.

Example `index_ticks/20260926.jsonl`:
```json
{"symbol": "NIFTY", "timestamp": "2026-09-26T09:15:00", "open": 19800.0, "high": 19820.0, "low": 19795.0, "close": 19810.0, "volume": null}
{"symbol": "NIFTY", "timestamp": "2026-09-26T09:16:00", "open": 19810.0, "high": 19835.0, "low": 19808.0, "close": 19825.0, "volume": null}
{"symbol": "BANKNIFTY", "timestamp": "2026-09-26T09:15:00", "open": 44000.0, "high": 44050.0, "low": 43980.0, "close": 44020.0, "volume": null}
...
```

Example `futures_ticks/20260926.jsonl`:
```json
{"symbol": "NIFTYFUT", "expiry": "2026-09-30", "timestamp": "2026-09-26T09:15:00", "open": 19850.0, "high": 19870.0, "low": 19845.0, "close": 19860.0, "volume": 1234567, "open_interest": 5000000}
...
```

Example `option_chain/20260926.jsonl`:
```json
{"underlying": "NIFTY", "expiry": "2026-09-26", "strike": 19800.0, "option_type": "CE", "timestamp": "2026-09-26T09:15:00", "ltp": 52.0, "bid": 51.5, "ask": 52.5, "volume": 12345, "open_interest": 500000, "iv": 0.15, "delta": 0.5, "gamma": 0.001, "theta": -5.0, "vega": 10.0}
...
```

**Each line is independent** (can parse line-by-line without loading entire file into memory).

---

## Configuration

Edit `src/data_recorder/config.py` to change:
- Symbols to record
- Output path (default: `data/recon/`)
- Verbosity

---

## Safety & Performance

**Safety:**
- **Append-only writes:** Can resume after crash without overwriting data.
- **Daily rotation:** New file each day (prevents unbounded file growth).
- **Gitignored:** `data/recon/` is in `.gitignore` (never committed to PUBLIC repo).
- **Independent process:** Crash in recorder doesn't affect trading loop (and vice versa).

**Performance:**
- **Lightweight:** ~5-10 MB RAM per recorder (total ~30-50 MB for all).
- **Low CPU:** Write operations are disk I/O bound (< 5% CPU per recorder).
- **Flush on write:** Ensures data is written immediately (safety vs performance trade-off; acceptable for 1-minute data).

**Disk usage estimate:**
- Index ticks: ~1 KB/minute × 375 minutes/day × 3 symbols = ~1 MB/day
- Futures ticks: ~1 KB/minute × 375 minutes × 3 symbols = ~1 MB/day
- Option chain: ~200 bytes/row × 150 strikes × 2 types × 375 minutes = ~22 MB/day (largest)
- Heavyweights: ~200 bytes/row × 15 stocks × 375 minutes = ~1 MB/day
- News: ~500 bytes/headline × ~20 headlines/day = ~10 KB/day
- Global markets: ~200 bytes/symbol × 7 symbols = ~1.5 KB/day
- **Total: ~25 MB/day uncompressed, ~5-10 MB/day gzipped.**
- 1 year = ~2.5-3.5 GB (manageable).

---

## Testing

**Unit tests with fixtures:**
```bash
cd packages/data-recorder
pytest tests/
```

Tests verify:
- File creation and rotation (test runs on two simulated days, checks two files created)
- JSON Lines format (each line is valid JSON)
- Schema compliance (required fields present)
- Restart/resume behavior (append to existing file if same day)
- Dry-run mode (no network calls, generates synthetic data)

**Dry-run acceptance test (as per PR-001 migration plan):**
```bash
python -m data_recorder.runner  # Dry-run mode
ls -lh data/recon/*/$(date +%Y%m%d).jsonl  # Check 6 files created
cat data/recon/index_ticks/$(date +%Y%m%d).jsonl | wc -l  # Should be 6 lines (3 symbols × 2 minutes)
cat data/recon/option_chain/$(date +%Y%m%d).jsonl | wc -l  # Should be 6 lines (3 strikes × 2 types)
```

---

## Production Implementation (TODO)

**Current status:** Dry-run mode works (generates synthetic data). Production mode is stubbed.

**To implement production mode:**

1. **Dhan API integration:**
   - Research Dhan Python SDK or use websocket library (e.g., `websockets`, `python-socketio`).
   - Subscribe to symbols: index, futures, option chain, heavyweights.
   - Capture ticks in callbacks, call `writer.write(tick)`.
   - Example (hypothetical):
     ```python
     from dhanhq import marketfeed  # Check Dhan docs for actual SDK
     client = marketfeed.DhanFeed(token=DHAN_TOKEN, client_id=DHAN_CLIENT_ID)
     client.subscribe(symbols=["NIFTY", "BANKNIFTY", "SENSEX"], mode="full")
     client.on_tick(lambda tick: index_recorder._write_tick(tick))
     client.connect()
     ```

2. **Option chain polling:**
   - If Dhan doesn't support websocket for full chain, poll REST API every 60 seconds:
     ```python
     import requests
     response = requests.get("https://api.dhan.co/api/v1/market-data/option-chain", 
                             params={"symbol": "NIFTY", "expiry": "2026-09-26"},
                             headers={"Authorization": f"Bearer {DHAN_TOKEN}"})
     chain = response.json()
     for option in chain['data']:
         option_chain_recorder.writer.write(option)
     ```
   - Check rate limits (may need to poll every 2-3 min if limited).

3. **News scraper:**
   - Install `feedparser`: `pip install feedparser`
   - Parse RSS feeds:
     ```python
     import feedparser
     feed = feedparser.parse("https://www.moneycontrol.com/rss/latestnews.xml")
     for entry in feed.entries:
         headline = {
             "news_id": hashlib.md5(entry.link.encode()).hexdigest()[:16],
             "timestamp": entry.published,
             "source": "MoneyControl",
             "headline": entry.title,
             "url": entry.link,
             "sentiment": None,  # Compute later
             "relevance": None,
             "event_tags": None
         }
         news_scraper.writer.write(headline)
     ```

4. **Global markets fetcher:**
   - Install `yfinance`: `pip install yfinance`
   - Fetch daily close:
     ```python
     import yfinance as yf
     ticker = yf.Ticker("^GSPC")
     hist = ticker.history(period="1d")
     close = hist['Close'].iloc[-1]
     prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else None
     change_pct = ((close - prev_close) / prev_close) if prev_close else None
     global_fetcher.writer.write({
         "symbol": "^GSPC",
         "date": date.today().isoformat(),
         "close": close,
         "change_pct": change_pct
     })
     ```

**See `NotImplementedError` messages in each recorder for specific instructions.**

---

## Troubleshooting

**Files not created:**
- Check `data/recon/` directory exists (should be created automatically).
- Check permissions (write access to `data/` directory).
- Run with verbose mode (default) to see log messages.

**Network errors in production mode:**
- Check Dhan API credentials (`DHAN_TOKEN`, `DHAN_CLIENT_ID` env vars).
- Check internet connection.
- Check Dhan API status (https://status.dhan.co or similar).
- Check rate limits (Dhan may throttle if too many requests).

**Disk full:**
- Data grows ~25 MB/day. If disk full, delete old files or compress with gzip:
  ```bash
  gzip data/recon/*/*.jsonl  # Compress all .jsonl files (5:1 ratio)
  ```

**Crash / restart behavior:**
- Recorder is safe to restart (appends to existing file if same day).
- On new day (midnight rollover), creates new file automatically.
- If crash during write, last line may be incomplete (parser should skip invalid JSON lines).

---

## Integration with Nightly Warehouse ETL

After market hours (16:00 IST), the nightly warehouse ETL job (PR-013) will:
1. Read all `data/recon/*/YYYYMMDD.jsonl` files
2. Clean (deduplicate, validate, fill missing values)
3. Transform (compute derived fields, join)
4. Aggregate (daily summaries, per-analyst win rates, per-stage loss attribution)
5. Write to warehouse (DuckDB or Postgres)
6. Archive raw files: `mv data/recon/ data/archive/YYYYMMDD/` (keep 30 days, then delete or compress)

**Until PR-013 is implemented, raw files stay in `data/recon/` (manual review via `cat` / `jq` / pandas).**

---

## Security

**Repository is PUBLIC. Do NOT commit:**
- `data/recon/` directory (already in `.gitignore`)
- Dhan API credentials (use env vars, not hardcoded)
- Any `.env` files with secrets

`.gitignore` entry (added in this PR):
```
# Data recorder output (never commit market data or credentials)
data/recon/
data/archive/
```

---

**Questions?** See `docs/01_CURRENT_STATE_AND_GAPS.md` § Data Capture or `docs/03_DATA_CONTRACTS.md` for full specification.

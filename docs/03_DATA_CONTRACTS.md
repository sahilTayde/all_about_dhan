# Data Contracts

**Purpose:** This document specifies the daily data capture set (what we record, why, and how), join keys for relating data across sources, storage layout, nightly warehouse ETL job, and which Dhan websocket/REST feeds supply each piece of data.

**Critical priority:** Data capture is PR-001 in migration plan. **Cannot be backfilled.** Start immediately. Lab journal (line 80): "binding constraint is missing data (futures 1m volume, multi-strike option history with OI/IV, heavyweights, more tape days)."

---

## Daily Capture Set (What We Record)

### 1. Index Ticks (1-Minute Bars)

**What:** NIFTY, BANKNIFTY, SENSEX spot index levels. OHLCV (open, high, low, close, volume) per 1-minute bar, 09:00 IST (pre-open) through 15:30 IST (close).

**Why:** 
- Core signal generation (trend, regime classification, breakout detection).
- Backtest precision (1-minute bars capture intraday moves; daily bars miss intraday edge).
- Replay engine (exact prices at each minute for strategy simulation).

**Dhan feed:** 
- **Websocket:** `wss://api.dhan.co/market-data` (verify current docs), subscribe to NIFTY, BANKNIFTY, SENSEX.
- **Fallback REST:** `GET /api/v1/market-data/quote?symbol=NIFTY` (if websocket drops; poll every 60 sec). Less preferred (higher latency).

**Schema:**
```sql
CREATE TABLE index_ticks (
    symbol VARCHAR(20) NOT NULL,          -- NIFTY, BANKNIFTY, SENSEX
    timestamp TIMESTAMP NOT NULL,         -- UTC or IST (choose one; recommend UTC for DB, convert to IST in app)
    open DECIMAL(10,2) NOT NULL,
    high DECIMAL(10,2) NOT NULL,
    low DECIMAL(10,2) NOT NULL,
    close DECIMAL(10,2) NOT NULL,
    volume BIGINT,                        -- Spot index has no volume (N/A); store NULL or 0
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_index_ticks_time ON index_ticks(timestamp);
```

**Storage:** DuckDB table `index_ticks` or Parquet file `data/warehouse/index_ticks/YYYYMMDD.parquet` (one file per day; faster backtest queries, lower storage).

**Retention:** Indefinite (or ≥3 years for backtesting; after 3 years, archive to cold storage or delete if storage constrained).

---

### 2. Futures Ticks (1-Minute Bars)

**What:** NIFTY, BANKNIFTY, SENSEX futures (current month + next month). OHLCV per 1-minute bar, with **volume** (critical for analysis).

**Why:**
- **Volume is missing in current system** (lab journal line 80). Needed for volume-based analysts (unusual volume, VWAP, volume profile).
- Futures lead spot (institutional trading). Futures volume spikes indicate smart money flow.
- Backtest: Futures volume + spot price → better entry filters.

**Dhan feed:**
- **Websocket:** Same as index ticks, subscribe to NIFTYFUT, BANKNIFTYFUT, SENSEXFUT (current month expiry). Verify Dhan supports futures websocket (may be separate channel or same `market-data` with different symbol).
- **Fallback REST:** `GET /api/v1/market-data/quote?symbol=NIFTYFUT` (poll every 60 sec).

**Schema:**
```sql
CREATE TABLE futures_ticks (
    symbol VARCHAR(20) NOT NULL,          -- NIFTYFUT, BANKNIFTYFUT, SENSEXFUT
    expiry DATE NOT NULL,                 -- Expiry date (e.g., 2026-09-26 for Sep 26 weekly)
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(10,2) NOT NULL,
    high DECIMAL(10,2) NOT NULL,
    low DECIMAL(10,2) NOT NULL,
    close DECIMAL(10,2) NOT NULL,
    volume BIGINT NOT NULL,               -- CRITICAL: Volume
    open_interest BIGINT,                 -- Optional but useful (OI changes indicate trend strength)
    PRIMARY KEY (symbol, expiry, timestamp)
);
CREATE INDEX idx_futures_ticks_time ON futures_ticks(timestamp);
CREATE INDEX idx_futures_ticks_expiry ON futures_ticks(expiry);
```

**Storage:** DuckDB table or Parquet `data/warehouse/futures_ticks/YYYYMMDD.parquet`.

**Retention:** ≥3 years (archive after 3 years).

---

### 3. Option Chain (Full Chain, All Strikes, OI/IV/Greeks)

**What:** NIFTY, BANKNIFTY, SENSEX option chain. **All strikes** (not just ATM ±5), both CE and PE, for current weekly and monthly expiries. Per-minute snapshot. Fields: LTP (last traded price), bid, ask, volume, OI (open interest), IV (implied volatility), delta, gamma, theta, vega.

**Why:**
- **Multi-strike OI history missing** (lab journal line 80). Current system polls chain every 1 min (`option_chain_poller.py`) but may not store all strikes or may not store OI/IV consistently.
- OI build-up analysis (H05 in lab round 1: OI absorption filter showed +29.2k on tape, but only 8 trades; needs more data to validate).
- Greeks-based analysts (delta-neutral, vega exposure, gamma scalp).
- Max pain, put-call OI ratio, skew analysis.
- Backtest: Realistic option pricing (use actual IV + greeks, not Black-Scholes with guessed IV).

**Dhan feed:**
- **Websocket (preferred if available):** Subscribe to option chain updates. **Check Dhan docs:** May require separate websocket channel or batch REST API.
- **REST (current method):** `GET /api/v1/market-data/option-chain?symbol=NIFTY` (returns full chain; poll every 60 sec). If rate-limited, poll every 2-3 min (acceptable for 1-min bar backtest; interpolate if needed).

**Schema:**
```sql
CREATE TABLE option_chain (
    underlying VARCHAR(20) NOT NULL,      -- NIFTY, BANKNIFTY, SENSEX
    expiry DATE NOT NULL,
    strike DECIMAL(10,2) NOT NULL,
    option_type VARCHAR(2) NOT NULL,      -- CE, PE
    timestamp TIMESTAMP NOT NULL,
    ltp DECIMAL(10,2),                    -- Last traded price (may be NULL if no trades)
    bid DECIMAL(10,2),
    ask DECIMAL(10,2),
    volume BIGINT,
    open_interest BIGINT NOT NULL,        -- CRITICAL: OI
    iv DECIMAL(6,4),                      -- Implied volatility (0.0 to 2.0; e.g., 0.15 = 15%)
    delta DECIMAL(6,4),
    gamma DECIMAL(8,6),
    theta DECIMAL(8,4),
    vega DECIMAL(8,4),
    PRIMARY KEY (underlying, expiry, strike, option_type, timestamp)
);
CREATE INDEX idx_option_chain_time ON option_chain(timestamp);
CREATE INDEX idx_option_chain_expiry ON option_chain(expiry);
CREATE INDEX idx_option_chain_strike ON option_chain(strike);
```

**Notes:**
- **Full chain = all strikes.** If Dhan API returns only ATM ±10 strikes, request wider range or fallback to NSE bhavcopy (end-of-day only; not real-time, but useful for OI v2 per lab journal line 66).
- **Greeks:** If Dhan provides greeks, use them. If not, compute client-side (Black-Scholes or sensibull-style approximation; store computed greeks in DB for replay).

**Storage:** DuckDB table or Parquet (compressed; chain is large: ~100-200 strikes × 2 types × 375 minutes/day = ~150k rows/day per underlying; ×3 underlyings = ~450k rows/day; ×250 days/year = ~112M rows/year; Parquet compresses well; ~1-2 GB/year uncompressed, ~200-500 MB compressed).

**Retention:** ≥3 years (archive after 3 years).

---

### 4. Heavyweights (Top NIFTY Constituents, Intraday LTP)

**What:** Top 10-15 NIFTY stocks by weight (e.g., Reliance, TCS, HDFC Bank, Infosys, ICICI Bank, Bharti Airtel, ITC, HUL, SBI, Kotak Bank, Axis Bank, L&T, Asian Paints, Maruti, Titan). LTP (last traded price) per 1-minute bar.

**Why:**
- **Missing data** (lab journal line 80). H06 heavyweight breadth filter showed +35.2k on tape (4 trades blocked, 0 worse days), but only ~42 days of history overlap.
- Breadth analysis (how many heavyweights are up/down; strong breadth = healthy trend, weak breadth = divergence/reversal signal).
- Constituent-weighted contribution (Phase 3 suggests using official NIFTY weights from NSE factsheet; e.g., if Reliance is 10% of NIFTY and up 2%, that's +0.2% contribution; sum contributions = NIFTY move).

**Dhan feed:**
- **Websocket:** Subscribe to Reliance, TCS, HDFC Bank, etc. (NSE equity symbols: `RELIANCE`, `TCS`, `HDFCBANK`).
- **REST fallback:** Poll quotes every 60 sec.

**Schema:**
```sql
CREATE TABLE heavyweight_ticks (
    symbol VARCHAR(20) NOT NULL,          -- RELIANCE, TCS, HDFCBANK, etc.
    timestamp TIMESTAMP NOT NULL,
    ltp DECIMAL(10,2) NOT NULL,
    volume BIGINT,                        -- Cumulative volume (day so far)
    PRIMARY KEY (symbol, timestamp)
);
CREATE INDEX idx_heavyweight_ticks_time ON heavyweight_ticks(timestamp);
```

**List of heavyweights (as of Sep 2026; verify with NSE factsheet):**
1. Reliance Industries (`RELIANCE`) — ~10% weight
2. TCS (`TCS`) — ~4%
3. HDFC Bank (`HDFCBANK`) — ~8%
4. Infosys (`INFY`) — ~4%
5. ICICI Bank (`ICICIBANK`) — ~7%
6. Bharti Airtel (`BHARTIARTL`) — ~3%
7. ITC (`ITC`) — ~4%
8. HUL (`HINDUNILVR`) — ~4%
9. SBI (`SBIN`) — ~3%
10. Kotak Mahindra Bank (`KOTAKBANK`) — ~3%
11. Axis Bank (`AXISBANK`) — ~2%
12. L&T (`LT`) — ~3%
13. Asian Paints (`ASIANPAINT`) — ~2%
14. Maruti Suzuki (`MARUTI`) — ~2%
15. Titan (`TITAN`) — ~2%

**Storage:** DuckDB table or Parquet `data/warehouse/heavyweight_ticks/YYYYMMDD.parquet`.

**Retention:** ≥3 years (archive after 3 years).

---

### 5. Global Markets (Daily Close)

**What:** S&P 500 (SPX), Nasdaq 100 (NDX), DXY (US Dollar Index), US 10-Year Treasury Yield (US10Y), Crude Oil (WTI), Gold (XAUUSD), USDINR (currency pair). Daily close (previous day's close, fetched before 09:15 IST).

**Why:**
- Intermarket analysis (Phase 3 report: US stocks, DXY, oil correlate with NIFTY gap ~0.4, not intraday). 
- Pre-market summary (boss needs context: "SPX +1.2%, DXY -0.3% overnight → risk-on").
- Lab journal line 67: "Intermarket as a daily/weekly regime, not intraday bias" (queued for round 2).

**Frequency:** Daily (no intraday needed; lab journal confirms: "After 09:15 they say almost nothing (−0.14 DEV, −0.04 OOS)").

**API:**
- **Yahoo Finance** (`yfinance` Python package): Free, covers all above. Example: `yf.download('^GSPC ^IXIC DX-Y.NYB ^TNX CL=F GC=F USDINR=X', period='1d')`.
- **Alpha Vantage** (free tier 5 calls/min): Fallback if Yahoo breaks.

**Schema:**
```sql
CREATE TABLE global_markets_daily (
    symbol VARCHAR(20) NOT NULL,          -- SPX, NDX, DXY, US10Y, WTI, GOLD, USDINR
    date DATE NOT NULL,                   -- Trading date (e.g., 2026-09-25 for overnight close before 2026-09-26 Indian market)
    close DECIMAL(10,2) NOT NULL,
    change_pct DECIMAL(6,4),              -- % change from previous day (e.g., +1.2% = 0.0120)
    PRIMARY KEY (symbol, date)
);
CREATE INDEX idx_global_markets_date ON global_markets_daily(date);
```

**Storage:** DuckDB table (small; ~7 symbols × 250 days/year = 1,750 rows/year).

**Retention:** Indefinite (tiny storage footprint).

---

### 6. News (Headlines + Event Tags)

**What:** News headlines from MoneyControl, Economic Times, NSE announcements, Twitter/X finance handles (optional). Fields: headline, timestamp, URL, source, sentiment (bullish/bearish/neutral), relevance (NIFTY, BANKNIFTY, sector, stock), event tags.

**Why:**
- Pre-market context (boss needs to know: "RBI holds rates", "US Fed hikes", "IT layoffs", "Banking scandal").
- Event memory (Phase 3 § 13: "Analog memory: score excludes outliers; remember the event type" per `EVENT_MEMORY.md`). Tag events (earnings, policy, global shock, sector news) so post-market analysis can say: "On RBI policy days (n=8), NIFTY gapped +0.3% on avg but reversed by 11am (5/8 days); avoid trend-following on policy days."
- Corpus for RAG (future; optional): Search historical news similar to today's events, recall what happened next.

**Frequency:** 
- **Pre-market:** Scrape at 08:00 IST (before pre-market analysis at 08:45).
- **Intraday (optional):** Scrape every 30 min during market hours (09:15-15:30) for breaking news (e.g., crude oil spike, global market crash). GROK monitoring (requirement line 96) can alert boss.

**Sources:**
- **MoneyControl RSS:** `https://www.moneycontrol.com/rss/latestnews.xml` (free, no API key).
- **Economic Times RSS:** `https://economictimes.indiatimes.com/rssfeedstopstories.cms`.
- **NSE announcements:** `https://www.nseindia.com/api/corporate-announcements` (REST API; may require headers/cookies to avoid blocking).
- **Twitter/X (optional):** Track finance handles (@NSEIndia, @BloombergQuint, @CNBCTV18News). Requires Twitter API key (free tier 1500 tweets/month; may not be enough; skip unless founder has paid tier).

**Schema:**
```sql
CREATE TABLE news (
    news_id VARCHAR(64) PRIMARY KEY,      -- Hash of (source + URL + timestamp) for dedup
    timestamp TIMESTAMP NOT NULL,         -- When news was published (or scraped if publish time unavailable)
    source VARCHAR(50) NOT NULL,          -- MoneyControl, EconomicTimes, NSE, Twitter
    headline TEXT NOT NULL,
    url TEXT,
    sentiment VARCHAR(10),                -- BULLISH, BEARISH, NEUTRAL (from keyword heuristic or LLM)
    relevance TEXT,                       -- JSON array: ["NIFTY", "BANKNIFTY", "BANKING", "HDFCBANK"]
    event_tags TEXT,                      -- JSON array: ["RBI_POLICY", "EARNINGS", "GLOBAL_SHOCK"]
    content TEXT                          -- Optional: Full article text (for future RAG)
);
CREATE INDEX idx_news_time ON news(timestamp);
CREATE INDEX idx_news_source ON news(source);
```

**Event tag taxonomy (initial; expand as needed):**
- **Policy:** `RBI_POLICY`, `UNION_BUDGET`, `STATE_ELECTION`, `GST_CHANGE`
- **Global:** `FED_DECISION`, `US_GDP`, `CHINA_DATA`, `CRUDE_SPIKE`, `GEOPOLITICAL` (war, sanctions)
- **Sector:** `BANKING_RESULTS`, `IT_LAYOFFS`, `PHARMA_APPROVAL`, `AUTO_SALES`
- **Stock:** `EARNINGS` (specific stock result), `SCANDAL`, `MGMT_CHANGE`, `M&A`
- **Market:** `CIRCUIT_BREAKER`, `EXPIRY_DAY`, `F&O_BAN` (stock in F&O ban)

**Sentiment heuristic (simple keyword-based; LLM is optional but expensive):**
- Bullish: headline contains "surges", "rallies", "all-time high", "beats estimates", "upgrades", "approval", "deal", "growth".
- Bearish: headline contains "crashes", "plunges", "falls", "misses estimates", "downgrades", "scandal", "layoffs", "loss", "concern".
- Neutral: otherwise.

**Storage:** DuckDB table.

**Retention:** ≥3 years (news corpus grows; ~100 headlines/day × 250 days/year = 25k/year; ×3 = 75k; manageable).

---

### 7. Multi-Timeframe Levels (Daily, 4H, Weekly, 52-Week High/Low)

**What:** NIFTY, BANKNIFTY, SENSEX support/resistance levels. Daily: yesterday's high/low/close, weekly: last week's high/low/close, 52-week high/low, daily pivot points (optional; classic, Fibonacci, Camarilla).

**Why:**
- Pre-market context (boss: "NIFTY at daily R1 19850; near 52w high 20100; strong resistance").
- Level-based analysts (breakout above R1, rejection at S1, 52w high breakout → trending market).
- Backtest: Test "only trade if index is above weekly pivot" or "avoid shorts near 52w high".

**Frequency:** 
- **Daily levels:** Computed once at 15:31 IST (after market close) for next day.
- **Weekly levels:** Computed once on Friday 15:31 IST (or Monday 08:00 IST).
- **52-week high/low:** Rolling (updated daily).

**Computation (no external API; compute from index_ticks):**
- Yesterday's high/low/close: Query `SELECT MAX(high), MIN(low), close FROM index_ticks WHERE symbol='NIFTY' AND DATE(timestamp)='2026-09-25'`.
- Pivot points (classic): `P = (H + L + C) / 3`, `R1 = 2P - L`, `S1 = 2P - H`, `R2 = P + (H - L)`, `S2 = P - (H - L)`.
- 52-week high/low: `SELECT MAX(high), MIN(low) FROM index_ticks WHERE symbol='NIFTY' AND timestamp >= NOW() - INTERVAL '52 weeks'`.

**Schema:**
```sql
CREATE TABLE levels_daily (
    symbol VARCHAR(20) NOT NULL,          -- NIFTY, BANKNIFTY, SENSEX
    date DATE NOT NULL,                   -- Date these levels apply to (e.g., 2026-09-26)
    prev_high DECIMAL(10,2),
    prev_low DECIMAL(10,2),
    prev_close DECIMAL(10,2),
    pivot DECIMAL(10,2),
    r1 DECIMAL(10,2),
    s1 DECIMAL(10,2),
    r2 DECIMAL(10,2),
    s2 DECIMAL(10,2),
    week_high DECIMAL(10,2),
    week_low DECIMAL(10,2),
    week_close DECIMAL(10,2),
    high_52w DECIMAL(10,2),
    low_52w DECIMAL(10,2),
    PRIMARY KEY (symbol, date)
);
CREATE INDEX idx_levels_daily_date ON levels_daily(date);
```

**Storage:** DuckDB table (tiny; 3 symbols × 250 days/year = 750 rows/year).

**Retention:** ≥3 years.

---

## Join Keys (How Data Relates)

**Primary entities:** `symbol` (NIFTY, BANKNIFTY, SENSEX, futures, options, stocks), `timestamp` (1-min granularity), `date` (daily granularity), `expiry` (for futures/options).

**Join key hierarchy:**

```
date (2026-09-26)
  ├── global_markets_daily (SPX, DXY, etc. for 2026-09-25 close)
  ├── levels_daily (NIFTY support/resistance for 2026-09-26)
  ├── news (headlines on 2026-09-26 or overnight)
  └── timestamp (2026-09-26 09:15:00, 09:16:00, ...)
      ├── index_ticks (NIFTY at 09:15, 09:16, ...)
      ├── futures_ticks (NIFTYFUT at 09:15, 09:16, ...)
      ├── option_chain (NIFTY 19800 CE/PE at 09:15, 09:16, ...)
      └── heavyweight_ticks (Reliance, TCS at 09:15, 09:16, ...)
```

**Example join (pre-market analysis):**
```sql
SELECT 
    d.date,
    d.prev_high, d.prev_low, d.prev_close, d.pivot, d.r1, d.s1,
    g.symbol AS global_symbol, g.close AS global_close, g.change_pct AS global_change_pct,
    n.headline, n.sentiment, n.event_tags
FROM levels_daily d
LEFT JOIN global_markets_daily g ON g.date = d.date - INTERVAL '1 day'  -- Overnight close
LEFT JOIN news n ON DATE(n.timestamp) = d.date AND n.relevance LIKE '%NIFTY%'
WHERE d.symbol = 'NIFTY' AND d.date = '2026-09-26';
```

**Example join (backtest: analyst vote at 10:30 IST):**
```sql
SELECT 
    i.timestamp, i.close AS nifty_close,
    f.close AS nifty_fut_close, f.volume AS nifty_fut_volume,
    o.strike, o.option_type, o.ltp AS option_ltp, o.iv, o.delta, o.open_interest AS option_oi,
    h.symbol AS hw_symbol, h.ltp AS hw_ltp
FROM index_ticks i
LEFT JOIN futures_ticks f ON f.timestamp = i.timestamp AND f.symbol = 'NIFTYFUT'
LEFT JOIN option_chain o ON o.timestamp = i.timestamp AND o.underlying = i.symbol AND o.strike BETWEEN i.close - 200 AND i.close + 200
LEFT JOIN heavyweight_ticks h ON h.timestamp = i.timestamp
WHERE i.symbol = 'NIFTY' AND i.timestamp = '2026-09-26 10:30:00';
```

**Foreign keys (logical; enforce in app or DB constraints if using Postgres):**
- `option_chain.underlying` → `index_ticks.symbol`
- `futures_ticks.symbol` (e.g., NIFTYFUT) → `index_ticks.symbol` (NIFTY; strip "FUT")
- `levels_daily.symbol` → `index_ticks.symbol`
- `news.relevance` (JSON array) contains → `index_ticks.symbol` or stock symbol

---

## Storage Layout

**File structure (if using Parquet + DuckDB):**

```
data/
  warehouse/
    index_ticks/
      20260926.parquet
      20260925.parquet
      ...
    futures_ticks/
      20260926.parquet
      ...
    option_chain/
      20260926.parquet        -- Large file (~50-100 MB/day compressed)
      ...
    heavyweight_ticks/
      20260926.parquet
      ...
    warehouse.duckdb          -- DuckDB file (tables below OR just metadata + queries on Parquet files)
      tables:
        - global_markets_daily
        - news
        - levels_daily
        - analyst_votes         (operational table, not from data capture; see below)
        - position_metrics_1min (operational table)
        - trades_closed         (operational table)
        - pre_market_summaries  (operational table)
```

**Operational tables (not captured from market, but logged by system):**
- `analyst_votes` (timestamp, analyst_id, signal, confidence, reasoning, metadata_json): Every vote logged.
- `position_metrics_1min` (timestamp, total_open_pnl, total_closed_pnl, drawdown, win_rate): Metrics from monitor layer.
- `trades_closed` (trade_id, entry_time, exit_time, symbol, side, lots, entry_price, exit_price, realized_pnl, exit_reason, analysts_json, boss_decision_json): Closed trade records.
- `pre_market_summaries` (date, gap_pct, intermarket_score, news_summary, levels_summary, tagged_events_json): Pre-market output.

**DuckDB vs Parquet choice:**
- **Option 1 (simpler):** DuckDB file only (`warehouse.duckdb`). All tables inside. Pro: Single file, easy to query. Con: Single-writer (post-market ETL is single process, so OK; but if real-time writes during market, may need Postgres).
- **Option 2 (recommended for scale):** Parquet files for market data (index_ticks, futures_ticks, option_chain, heavyweight_ticks). DuckDB tables for operational data (analyst_votes, trades_closed, etc.) and metadata. DuckDB queries Parquet files directly: `SELECT * FROM read_parquet('data/warehouse/index_ticks/20260926.parquet')`. Pro: Parquet is columnar (fast analytical queries), compressed (small storage), portable (can load into pandas, Arrow, Spark). Con: Slightly more complex (file naming convention, ETL writes Parquet not just DB inserts).

**Recommendation:** Start with **Option 1** (DuckDB file only; simpler). Migrate to **Option 2** (Parquet + DuckDB) after 3 months if storage grows or query performance degrades.

---

## Nightly Warehouse Job (ETL)

**Purpose:** Read raw JSON from `data/recon/` (written by real-time data capture scripts), clean, transform, join, aggregate, write to warehouse (DuckDB or Parquet).

**Schedule:** Run at 16:00 IST (30 min after market close at 15:30). Allow time for final ticks/fills to settle. Cron: `0 16 * * 1-5 /path/to/venv/bin/python /path/to/scripts/warehouse_etl.py` (Mon-Fri; adjust for Indian holidays using NSE calendar).

**Steps:**

1. **Read raw data:**
   - `data/recon/index_ticks/YYYYMMDD.json` (if exists; or CSV, or already in temp DB)
   - `data/recon/futures_ticks/YYYYMMDD.json`
   - `data/recon/option_chain/YYYYMMDD.json`
   - `data/recon/heavyweight_ticks/YYYYMMDD.json`
   - `data/recon/news/YYYYMMDD.json`

2. **Clean:**
   - Deduplicate (by primary key: symbol + timestamp).
   - Handle missing values (LTP = NULL if no trade; fill with previous LTP or bid/ask midpoint).
   - Convert timestamps (if raw JSON has IST strings, parse to UTC timestamp or keep as IST; be consistent).
   - Validate (e.g., high ≥ low, close between high and low; if violated, log anomaly, keep data but flag).

3. **Transform:**
   - Compute derived fields:
     - `change_pct` for index/futures (close / prev_close - 1).
     - Pivot points for levels_daily.
     - Sentiment + event tags for news (keyword heuristic or LLM call; if LLM, batch all headlines → one API call to save cost).
   - Join heavyweight ticks with NIFTY weights (from static config or NSE factsheet) → compute weighted contribution per stock.

4. **Aggregate (daily summaries):**
   - `index_daily_summary` (symbol, date, open, high, low, close, volume, change_pct).
   - `analyst_daily_performance` (analyst_id, date, votes_count, wins, losses, win_rate, avg_profit, avg_loss).
   - `strategy_daily_performance` (strategy_id, date, trades_count, wins, losses, win_rate, total_pnl, max_dd).
   - `stage_loss_attribution` (stage, date, total_loss): Which stage (entry, boss, desk, exit) contributed to losses.

5. **Write to warehouse:**
   - INSERT INTO `index_ticks` (from raw JSON).
   - INSERT INTO `futures_ticks`.
   - INSERT INTO `option_chain`.
   - INSERT INTO `heavyweight_ticks`.
   - INSERT INTO `news`.
   - INSERT INTO `levels_daily` (computed).
   - INSERT INTO `global_markets_daily` (fetched from Yahoo Finance before ETL).
   - INSERT INTO aggregate tables.

6. **Archive raw JSON:**
   - Move `data/recon/YYYYMMDD/*` to `data/archive/YYYYMMDD/` (keep for 30 days, then delete or compress to .tar.gz).

7. **Vacuum / optimize:**
   - If DuckDB: Run `VACUUM` (reclaim space).
   - If Parquet: No vacuum needed (immutable files).

**Error handling:**
- If raw JSON missing (data capture script failed): Log error, send alert to founder, skip day (cannot backfill; note gap).
- If ETL fails mid-run: Use transaction (BEGIN; INSERT; COMMIT;). If fails, ROLLBACK. Retry once. If still fails, alert founder, manual investigation.

**Estimated runtime:** ~5-10 min for 1 day of data (~500k rows option chain, ~100k rows other). Acceptable (not blocking; runs after hours).

---

## Dhan Feed Mapping (Websocket / REST)

**Note:** Verify all below with current Dhan API docs (https://api.dhan.co or https://dhanhq.co/docs). API may have changed since last known version.

### Websocket (Real-Time Data)

**Endpoint:** `wss://api.dhan.co/market-data` (or similar; check docs).

**Authentication:** Bearer token (from login API or OAuth). Send in header: `Authorization: Bearer <token>`.

**Subscribe message (JSON):**
```json
{
  "action": "subscribe",
  "symbols": ["NIFTY", "BANKNIFTY", "SENSEX", "NIFTYFUT", "BANKNIFTYFUT", "SENSEXFUT", "RELIANCE", "TCS", "HDFCBANK", ...],
  "mode": "full"  // or "quote" for LTP only, "full" for OHLCV + OI + greeks
}
```

**Incoming tick message (JSON example):**
```json
{
  "type": "tick",
  "symbol": "NIFTY",
  "ltp": 19820.50,
  "open": 19800.00,
  "high": 19850.00,
  "low": 19780.00,
  "close": 19820.50,
  "volume": 12345678,
  "timestamp": "2026-09-26T10:30:00Z"
}
```

**For option chain:** May require separate subscription (e.g., `symbols: ["NIFTY26SEP19800CE", "NIFTY26SEP19800PE", ...]`) or batch REST API (if websocket does not support full chain).

**Heartbeat:** Send ping every 30 sec to keep connection alive. If no message received for 60 sec, reconnect.

**Error handling:** If websocket drops, buffer last known LTP (in-memory cache), reconnect, resubscribe. Log disconnect event (monitor layer alerts if downtime > 2 min).

### REST API (Fallback / Daily Data)

**Base URL:** `https://api.dhan.co/api/v1` (verify).

**Endpoints:**

| Data | Method | Endpoint | Query Params | Response |
|------|--------|----------|--------------|----------|
| **Index quote** | GET | `/market-data/quote` | `symbol=NIFTY` | `{symbol, ltp, open, high, low, close, volume, timestamp}` |
| **Futures quote** | GET | `/market-data/quote` | `symbol=NIFTYFUT` | Same as above + `open_interest` |
| **Option chain** | GET | `/market-data/option-chain` | `symbol=NIFTY&expiry=2026-09-26` | Array of strikes with CE/PE data |
| **Stock quote** | GET | `/market-data/quote` | `symbol=RELIANCE` | Same as index quote |
| **Order placement** | POST | `/orders` | Body: `{symbol, side, quantity, order_type, limit_price, sl_price}` | `{order_id, status}` |
| **Order status** | GET | `/orders/{order_id}` | None | `{order_id, status, fill_price, fill_quantity, timestamp}` |
| **Positions** | GET | `/positions` | None | Array of `{symbol, quantity, avg_price, pnl}` |
| **Funds** | GET | `/funds` | None | `{available_balance, margin_used}` |

**Rate limits:** Check docs. Typical: 10 req/sec for market data, 5 req/sec for orders. If exceeded, backoff + retry.

**Authentication:** All requests need `Authorization: Bearer <token>` header.

**Error codes:**
- `401`: Unauthorized (token expired; re-login).
- `429`: Rate limit exceeded (backoff 1 sec, retry).
- `400`: Bad request (invalid symbol, missing params).
- `500`: Server error (Dhan API down; alert founder).

---

## Data Capture Scripts (Implementation Outline)

**Script:** `scripts/data_capture/realtime_recorder.py` (runs during market hours 09:00-15:35 IST).

**Flow:**

```python
# Pseudocode
import asyncio
import dhan_websocket  # Hypothetical Dhan websocket client
import sqlite3  # or duckdb

conn = sqlite3.connect('data/trading.db')  # Temp DB for intraday writes; ETL moves to warehouse

async def on_tick(tick: dict):
    symbol = tick['symbol']
    timestamp = tick['timestamp']
    # Insert into temp DB (fast write)
    conn.execute("INSERT INTO temp_index_ticks (symbol, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (symbol, timestamp, tick['open'], tick['high'], tick['low'], tick['close'], tick.get('volume')))
    conn.commit()
    # Also write to JSON for backup (in case DB write fails)
    with open(f'data/recon/index_ticks/{date.today()}.jsonl', 'a') as f:
        f.write(json.dumps(tick) + '\n')

async def main():
    ws = dhan_websocket.connect(token=DHAN_TOKEN)
    await ws.subscribe(['NIFTY', 'BANKNIFTY', 'SENSEX', 'NIFTYFUT', ...])
    async for tick in ws:
        await on_tick(tick)

asyncio.run(main())
```

**Start:** Cron or systemd timer at 09:00 IST. **Stop:** 15:35 IST (5 min after close; ensure last ticks captured).

**Separate script for option chain:** `scripts/data_capture/option_chain_recorder.py` (polls REST API every 1 min; websocket if available).

**Separate script for news:** `scripts/data_capture/news_scraper.py` (runs at 08:00, 10:00, 12:00, 14:00, 16:00 IST; scrapes RSS/API).

**Separate script for global markets:** `scripts/data_capture/global_markets_fetcher.py` (runs at 08:30 IST; fetches Yahoo Finance).

---

## Open Questions (For Founder to Clarify)

1. **Dhan websocket support:** Does Dhan API provide websocket for option chain (all strikes real-time)? Or only REST polling? If only REST, polling every 1 min is acceptable but may hit rate limits (need to batch or cache).
2. **Dhan historical data:** Does Dhan provide historical download (e.g., last 3 years of option chain with OI/IV)? If yes, bulk load into warehouse (backfill). If no, start recording now, accumulate over months.
3. **Greeks from Dhan:** Does Dhan API return greeks (delta, gamma, theta, vega) or must we compute client-side? If client-side, use Black-Scholes or sensibull-style approximation?
4. **Storage budget:** How much storage available? 3 years of full chain data = ~500 MB/year compressed Parquet = ~1.5 GB total (manageable). If storage constrained, can reduce to ATM ±10 strikes only (loses some OI analysis but workable).
5. **Twitter API:** Should we track Twitter/X for breaking news? Requires paid API ($100/month for higher tier). Recommend: Skip for now, use RSS only (MoneyControl, ET are sufficient).

---

**Last updated:** 2026-09-26 (Rebuild planning package)

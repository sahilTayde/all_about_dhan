# Websocket Connection Limits (Dhan API)

Source: `packages/dhan-client/src/dhan_client/endpoints.py`

## Dhan API Limits

- **Max connections per user**: 5
- **Max instruments per connection**: 5,000
- **Max instruments per subscribe message**: 100
- **Server ping interval**: 10 seconds
- **Stale disconnect timeout**: ~40 seconds without pong

## Recorder Usage

**Data recorder uses 3 websocket connections:**

1. **Index feed**: 3 instruments (NIFTY, BANKNIFTY, SENSEX)
   - Mode: TICKER
   - Exchange segment: NSE_FNO (1)

2. **Futures feed**: 3-6 instruments (current month + rollover)
   - NIFTYFUT, BANKNIFTYFUT, SENSEXFUT (3)
   - During rollover week: +3 next-month contracts (total 6)
   - Mode: FULL (to get volume and OI)
   - Exchange segment: NSE_FNO (2)

3. **Heavyweights feed**: 15 instruments (top NIFTY stocks)
   - RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK, etc.
   - Mode: TICKER
   - Exchange segment: NSE_EQ (0)

**Total instruments**: 21-24 (well under 5,000 per connection limit)

## Paper Trading Engine Usage

Estimated usage (based on existing `paper_scalp.py` and tape recording):

- **1 websocket connection** for real-time option chain strikes (ATM ±5-10)
  - Subscribes to ~20-40 option instruments (10-20 strikes × CE/PE)
  - Mode: QUOTE or FULL
  - Exchange segment: NSE_FNO

## Combined Usage

**Recorder + Paper Engine:**
- **4 connections** total (3 recorder + 1 paper engine)
- **Well within 5 connections per user limit**
- **~60-70 instruments** total (well under 5,000 per connection)

## Reconnect Logic

**Existing `DhanClient.feed_collector()` handles reconnect:**
- Automatic reconnect with exponential backoff (default: `reconnect=True`)
- Max backoff: configurable (default 30 seconds)
- Resubscribes to all instruments on reconnect
- Client-side pong response to server ping (handled by `websockets` library)

**Recorder error handling:**
- Each recorder (index, futures, heavyweights) runs in separate task
- On websocket disconnect or error: exponential backoff retry
- After 10 consecutive failures: writes `DATA_STALE` to heartbeat file
- Recorder continues retrying (does not crash)
- Heartbeat updated every minute with status

## Connection Sharing

**Recorder and paper engine do NOT share connections:**
- Each creates separate `DhanClient` instance
- Each calls `client.feed_collector()` independently
- No shared state or connection pooling
- If recorder crashes, paper engine is unaffected (and vice versa)

## Safety Margin

- **Used**: 4 connections
- **Available**: 5 connections
- **Remaining**: 1 connection free for manual testing / development

If adding more feeds (e.g., more heavyweights, FII/DII data), monitor total connections.
Each `feed_collector()` call = 1 new connection.

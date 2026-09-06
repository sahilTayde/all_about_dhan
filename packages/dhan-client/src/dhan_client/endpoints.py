"""Documented DhanHQ v2 URLs and paths.

Source: https://dhanhq.co/docs/v2/ and child pages fetched 2026-08-30.
Do not add paths that are not on those pages.
"""

from __future__ import annotations

# Introduction: resource base for REST.
# https://dhanhq.co/docs/v2/
API_BASE = "https://api.dhan.co/v2"
AUTH_BASE = "https://auth.dhan.co"

# Live Market Feed — query params: version, token, clientId, authType
# https://dhanhq.co/docs/v2/live-market-feed/
FEED_WS_BASE = "wss://api-feed.dhan.co"
FEED_VERSION = "2"
FEED_AUTH_TYPE = "2"

# Market Quote — POST, up to 1000 instruments, 1 req/s
# https://dhanhq.co/docs/v2/market-quote/
MARKETFEED_LTP = "/marketfeed/ltp"
MARKETFEED_OHLC = "/marketfeed/ohlc"
MARKETFEED_QUOTE = "/marketfeed/quote"

# Historical — POST
# https://dhanhq.co/docs/v2/historical-data/
CHARTS_HISTORICAL = "/charts/historical"
CHARTS_INTRADAY = "/charts/intraday"

# Option chain — POST; 1 unique request / 3 s
# https://dhanhq.co/docs/v2/option-chain/
OPTION_CHAIN = "/optionchain"
OPTION_CHAIN_EXPIRY_LIST = "/optionchain/expirylist"

# Expired / rolling options — POST (not wired in the first REST helpers)
# https://dhanhq.co/docs/v2/expired-options-data/
CHARTS_ROLLING_OPTION = "/charts/rollingoption"

# Instrument list
# https://dhanhq.co/docs/v2/instruments/
SCRIP_MASTER_CSV = "https://images.dhan.co/api-data/api-scrip-master.csv"
SCRIP_MASTER_DETAILED_CSV = (
    "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
)
# Segment-wise list. Official snippet: curl --location '.../instrument/{exchangeSegment}'
# Method not named in the sentence; curl --location with no -X is GET. VERIFY FROM DOCS.
INSTRUMENT_SEGMENT = "/instrument/{exchange_segment}"

# Auth / session (not auto-called by this skeleton)
# https://dhanhq.co/docs/v2/authentication/
PROFILE = "/profile"
RENEW_TOKEN = "/RenewToken"  # VERIFY HTTP method + response body (docs curl omits -X)

# Rate limits from https://dhanhq.co/docs/v2/ (Introduction) and child pages.
RATE_LIMIT_QUOTE_PER_SEC = 1
RATE_LIMIT_DATA_PER_SEC = 5
RATE_LIMIT_OPTION_CHAIN_SECONDS = 3
RATE_LIMIT_ORDER_PER_SEC = 10  # never called — ExecutionClient refuses
RATE_LIMIT_NON_TRADING_PER_SEC = 20  # profile, instruments, etc.
QUOTE_MAX_INSTRUMENTS = 1000
FEED_MAX_INSTRUMENTS_PER_CONNECTION = 5000
FEED_MAX_INSTRUMENTS_PER_MESSAGE = 100
FEED_MAX_CONNECTIONS_PER_USER = 5
FEED_SERVER_PING_SECONDS = 10
FEED_STALE_DISCONNECT_SECONDS = 40

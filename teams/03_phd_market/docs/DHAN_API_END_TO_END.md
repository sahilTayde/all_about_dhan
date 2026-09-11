# DhanHQ API — end-to-end desk book

**Owner:** 03 market (facts) + 00 (what this company may call).  
**Audience:** D1 developers (`packages/dhan-client`, warehouse, paper) and D2 analysts (01/02/04/05/06).  
**Fetched:** 2026-09-10 from official Dhan pages listed below. **Layer:** `SOURCE_FACT` for fields and limits on those pages. Desk policy (`USE` / `NEVER`) is a **00 call**, not a Dhan claim.  
**Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`. **No live orders.** Do not invent REST fields, lots, fills, or index weights.

This file is the **one inventory**. Official HTML remains the publisher of record if Dhan changes a field. Do not treat Dhan Cloud, MCP trade tools, or `dhanhq-skills` order helpers as permission to place.

---

## Official surfaces we read

| URL | What it is |
|-----|------------|
| https://dhanhq.co/trading-apis | Marketing: Trading / Market Feed / Portfolio / Historical / Statement. Claims: trading APIs ₹0, Data APIs extra (page listed ₹499), ~20k req/day marketing, sandbox, official Python lib. **Rate-limit numbers on this page are marketing; use the v2 Introduction table for coding.** |
| https://docs.dhanhq.co/ | Hub: Trading API, Data API, **MCP** (read *and* trade — we do not enable trade), **Agent Skills** (`dhan-oss/dhanhq-skills`, 12 categories), Dhan Cloud. |
| https://docs.dhanhq.co/skills/ | Skill pack installer (`skills add dhan-oss/dhanhq-skills --skill dhanhq`). Fetch of this path returned **409** this session; content is the same pack as GitHub. |
| https://docs.dhanhq.co/api/v2/ | OpenAPI/Swagger UI (fetch **409** this session). Live schemas also at https://api.dhan.co/v2/#/ and sandbox https://sandbox.dhan.co/v2/#/. Example schema: `UserIPResponse`. |
| https://dhanhq.co/docs/v2/ | **Canonical v2 book.** Intro, auth, orders, quotes, charts, chain, instruments, annexure. |
| https://dhanhq.co/docs/v2/option-chain/ | Same as `/docs/v2/option-chain/` (user also sent `dhanhq.co/docs/v2/option-chain/`). |
| https://github.com/dhan-oss/dhanhq-skills | `SKILL.md` + `references/*` (orders, portfolio, market-data, option-chain, instruments, funds, live-feed, error-codes, ScanX, workflows, options analysis, backtesting). |

**Hosts**

| Host | Use |
|------|-----|
| `https://api.dhan.co/v2` | Live REST. |
| `https://auth.dhan.co` | Token / consent / TOTP generate. |
| `wss://api-feed.dhan.co` | Live market feed (binary). |
| `wss://depth-api-feed.dhan.co/twentydepth` | 20/200-level depth (official full-depth page; VERIFY path if Dhan moves it). |
| `https://images.dhan.co/api-data/` | Public instrument CSVs (no token). |
| `https://sandbox.dhan.co` / `https://api-sandbox.dhan.co` | Closed sandbox. **Not** NSE/BSE tape. Paper gather on this desk uses **live** `api.dhan.co` **reads** when the founder asks — never sandbox as a substitute for chain/LTP. |

---

## How Dhan splits the product (algo view)

Dhan sells **Trading APIs** (free for Dhan users) and **Data APIs** (need `dataPlan: Active` on `GET /profile`).

| Bucket | Typical calls | Desk |
|--------|---------------|------|
| **Trading** | Place / modify / cancel, slice, super, forever, convert, exit-all, kill switch, P&L exit | **NEVER implement write paths.** `ExecutionClient` raises `SafeModeError`. |
| **Data** | Quotes, charts, option chain, expired/rolling options, live WS, 20/200 depth | **USE** for signals, warehouse, backtest, ML. Need data plan. |
| **Account read** | Profile, IP get, funds, holdings, positions, order/trade *GET*, ledger | **OPTIONAL later** (customer book / dealer). Not alpha. |
| **Account write (non-order)** | Set/modify IP, eDIS, convert, kill, P&L exit | **NEVER** without an explicit founder ticket after the research gate. |
| **Alerts / ScanX / Conditional Trigger** | Indicator *names* in Annexure; `/alerts/orders` | **Docs only.** No Supertrend/RSI/MACD **series** REST. Do not wire `/alerts/orders`. |
| **MCP + official skills** | Natural-language trade + data | Knowledge OK. **Do not** let MCP or skill scripts place/modify/cancel. |
| **Dhan Cloud** | Host *their* strategy runtime | Out of scope. We run our warehouse + paper here. |

Official Python: `pip install dhanhq` (`DhanContext`, `dhanhq`). **This repo uses `packages/dhan-client`**, not a second client. Do not fork a third wrapper.

---

## Auth, headers, IP (`UserIPResponse`)

**Every data/trading REST call** needs an access token. Many data calls also need `client-id`.

| Header / query | Where |
|----------------|--------|
| `access-token: {JWT}` | Almost all `api.dhan.co/v2` calls. |
| `client-id: {dhanClientId}` | Option chain, marketfeed LTP/OHLC/quote (official curl). |
| `dhanClientId` | RenewToken header; some order bodies. |
| `Content-Type: application/json` | POST/PUT. |

**How individuals get a token** (https://dhanhq.co/docs/v2/authentication/)

1. **Web 24h token** — `web.dhan.co` → My Profile → Access DhanHQ APIs. Optional postback URL for order updates (we do not need postback while orders are refused).
2. **TOTP generate** — `POST https://auth.dhan.co/app/generateAccessToken?dhanClientId=&pin=&totp=` → `accessToken`, `expiryTime` (~24h), `givenPowerOfAttorney`.
3. **Renew** — `https://api.dhan.co/v2/RenewToken` with current JWT + `dhanClientId`. **Only active web tokens.** Expired token cannot renew.
4. **API key + secret** (12 months) — generate-consent → browser login → consume consent → same token shape.
5. **Partners** — partner_id / partner_secret consent flow. We are not a listed partner unless the founder signs that.

**Profile** `GET /v2/profile` — first health check.

| Field | Meaning for us |
|-------|----------------|
| `dhanClientId` | Must match `DHAN_CLIENT_ID`. |
| `tokenValidity` | When the JWT dies. |
| `activeSegment` | Equity / Derivative / … |
| `ddpi` | `Active` / `Deactive` — delivery; not needed for index-option *signals*. |
| `mtf` | Margin trading facility — **not** our product. |
| `dataPlan` | Must be `Active` for chain/quotes/charts/WS. |
| `dataValidity` | Data-plan expiry. |

Errors: `DH-901` bad/expired token; `DH-902` / `806` no data plan; `807`–`810` auth.

**Static IP** (SEBI/exchange). Required **only** for order *placement* family (orders, super, forever). **Not** required for quotes, chain, charts, GET order book.

| Method | Path | Body / result |
|--------|------|----------------|
| POST | `/ip/setIP` | `dhanClientId`, `ip`, `ipFlag` `PRIMARY`\|`SECONDARY`. Locked ~7 days. |
| PUT | `/ip/modifyIP` | Same; only when modify window is open. |
| GET | `/ip/getIP` | **`UserIPResponse`:** `primaryIP`, `secondaryIP`, `modifyDatePrimary`, `modifyDateSecondary`. |

We may **GET** IP for ops. We do **not** SET/MODIFY from agents.

**Never** log tokens, PIN, TOTP, or IP write payloads.

---

## Rate limits (code from v2 Introduction — not the marketing page)

| Category | /s | /min | /h | /day | Examples |
|----------|---:|-----:|---:|-----:|----------|
| Order APIs | 10 | 250 | 1000 | 7000 | We never call writes. Official also: 25 modifications / order. |
| Data APIs | 5 | — | — | 100000 | Charts, rolling options. |
| Quote APIs | 1 | Unlimited | Unlimited | Unlimited | `/marketfeed/ltp` `ohlc` `quote`. Max **1000** ids / request. |
| Non-trading | 20 | Unlimited | Unlimited | Unlimited | Profile, instruments, funds, GET books. |
| Option chain | **1 unique / 3 s** | — | — | — | Full chain is heavy; OI updates slower than LTP. |

Marketing page also lists “25 orders/sec” and “5000 orders/day” — **do not code those**. Use the table above.

---

## Instrument identity (do this before any strategy)

Public CSVs (no auth):

- Compact: `https://images.dhan.co/api-data/api-scrip-master.csv`
- Detailed: `https://images.dhan.co/api-data/api-scrip-master-detailed.csv`
- Segment: `GET /v2/instrument/{exchangeSegment}`

**Columns analysts actually need** (detailed names; compact aliases in official table): `EXCH_ID`, `SEGMENT`, `INSTRUMENT`, `UNDERLYING_SECURITY_ID`, `UNDERLYING_SYMBOL`, `SYMBOL_NAME`, `DISPLAY_NAME`, `INSTRUMENT_TYPE`, `SERIES`, `LOT_SIZE`, `SM_EXPIRY_DATE`, `STRIKE_PRICE`, `OPTION_TYPE` (`CE`/`PE`), `TICK_SIZE`, `EXPIRY_FLAG` (`W`/`M`), `ISIN`, ASM/GSM flags, MTF leverage (equity only).

**Official index underlyings** (Dhan skill + our yaml VERIFY):

| Name | `security_id` | Segment |
|------|---------------|---------|
| NIFTY 50 | `13` | `IDX_I` |
| BANKNIFTY | `25` | `IDX_I` |
| SENSEX | `51` | `IDX_I` |
| FINNIFTY / MIDCPNIFTY | `27` / `442` | `IDX_I` — **not** customer default |

FUTIDX / OPTIDX **security_id** come from the CSV (example from our 2026-09-03 resolve: NIFTY FUT `68407`, BANKNIFTY FUT `68390`, SENSEX FUT `844615` — **re-resolve; ids rotate**).

**Not in Dhan:** official NSE/BSE **index weights**. Constituent *names* + cash LTP are available via master + quote. Weight % = `DATA_INSUFFICIENT` until an exchange file.

Annexure **exchangeSegment:** `IDX_I` `0`, `NSE_EQ` `1`, `NSE_FNO` `2`, `NSE_CURRENCY` `3`, `BSE_EQ` `4`, `MCX_COMM` `5`, `BSE_CURRENCY` `7`, `BSE_FNO` `8`.

Annexure **instrument:** `INDEX` `FUTIDX` `OPTIDX` `EQUITY` `FUTSTK` `OPTSTK` `FUTCOM` `OPTFUT` `FUTCUR` `OPTCUR`.

Annexure **expiryCode** (charts): `0` near, `1` next, `2` far.

---

## API inventory (what exists → what you get → what we do)

Policy: **USE** / **STORE** / **READ-ONLY later** / **NEVER**.

### A. Profile & session — USE

| Method | Path | You get | Desk use |
|--------|------|---------|----------|
| GET | `/profile` | Token + dataPlan | First probe. Block data jobs if plan inactive. |
| POST | `auth.dhan.co/app/generateAccessToken` | JWT | Human/ops only. |
| * | `/RenewToken` | New JWT | Ops only; method VERIFY if docs omit `-X`. |
| GET | `/ip/getIP` | `UserIPResponse` | Ops. |
| POST/PUT | `/ip/setIP` `/ip/modifyIP` | Saved IP | NEVER from agents. |

### B. Instruments — USE / STORE daily

CSV + `GET /instrument/{segment}` → lot, tick, expiry, strike, CE/PE, underlying id. Warehouse / paper must refresh; never hardcode lots.

### C. Market quote snapshots — USE (1 req/s, ≤1000 ids)

Body shape: `{ "IDX_I": [13,25,51], "NSE_EQ": […], "NSE_FNO": […] }`.

| POST | Path | Fields you get | Analyst / code |
|------|------|----------------|----------------|
| | `/marketfeed/ltp` | `last_price` | Spot + ATM premium + constituent tape. Cheap. |
| | `/marketfeed/ohlc` | `last_price` + `ohlc.open/high/low/close` | Day range. F&O OHLC can be **0** in samples — treat as missing, not zero vol. |
| | `/marketfeed/quote` | LTP, day OHLC, `average_price` (**day VWAP**), volume, OI + `oi_day_high/low` (NSE_FNO), circuits, net_change, last qty/time, 5-level `depth.buy/sell` (qty, orders, price) | Dealer liquidity *hint*. Not a fill. INDEX volume ≠ cash VWAP tape. |

SDK names: `ticker_data` / `ohlc_data` / `quote_data`.

### D. Historical OHLC — USE / STORE (data 5/s; 90-day chunks for intraday)

| POST | Path | Request | Response | Desk |
|------|------|---------|----------|------|
| | `/charts/historical` | `securityId`, `exchangeSegment`, `instrument`, `fromDate`, `toDate` (toDate **non-inclusive**), optional `expiryCode`, `oi` | Parallel arrays: `open` `high` `low` `close` `volume` `timestamp` (epoch) `open_interest` | Daily / weekly (we **resample 1w from 1d**). Inception-long for listed scrips. |
| | `/charts/intraday` | Same + `interval` ∈ **`1`,`5`,`15`,`25`,`60`** only; `fromDate`/`toDate` may include IST time; max **90 days** / call; last **5 years** for *active* instruments | Same arrays | Official TF only. **No 3m or 1w REST.** We resample `3m` from stored `1m`, `1w` from `1d`. Set `oi: true` only on FUT/OPT. |

**INDEX candles** = index level, not futures. **INDEX volume is not a traded tape.** Teacher recipes that need FUTIDX 3m / OPTIDX premium must pull those instruments — INDEX resample stays labeled **PROXY**.

### E. Option chain — USE / STORE (1 unique / 3 s)

| POST | Path | In | Out |
|------|------|----|-----|
| | `/optionchain/expirylist` | `UnderlyingScrip` (int, e.g. 13), `UnderlyingSeg` (`IDX_I`) | `data[]` ISO dates `YYYY-MM-DD` |
| | `/optionchain` | + `Expiry` | `data.last_price` (underlying LTP), `data.oc["{strike}.000000"].ce|pe` |

**Per CE/PE (official):** `last_price`, `average_price`, `volume`, `oi`, `previous_oi`, `previous_volume`, `previous_close_price`, `implied_volatility`, `security_id`, `top_bid_price/quantity`, `top_ask_price/quantity`, `greeks.delta/theta/gamma/vega`.

**What analysts may do (honest):**

- ATM = strike nearest `last_price`. CE vs PE LTP, OI, ΔOI, PCR = put OI / call OI (heuristic, **not a law**).
- IV / greeks: store. **Not** win odds (02).
- Bid/ask: spread for dealer HOLD, not a guaranteed fill.
- Full strike book = desk book. Compact ATM/PCR alone is **not** the book (00, 2026-09-10).

**What they must not do:** invent a strike Dhan did not return; treat missing greeks as 0; poll full chain every 1s (rate limit + product: **3m** poll).

### F. Expired / rolling options — USE for backtest (not live ticket)

Official: https://dhanhq.co/docs/v2/expired-options-data/  
Our client constant: `POST /charts/rollingoption`.

Rolling **ATM±** history up to **5 years**, **≤30 days** / call, minute intervals `1/5/15/25/60`. You do **not** need dead `security_id`.

| Request | Values |
|---------|--------|
| `securityId` | Underlying (e.g. 13) |
| `exchangeSegment` / `instrument` | e.g. NSE_FNO / `OPTIDX` |
| `expiryFlag` | `WEEK` or `MONTH` |
| `expiryCode` | 0/1/2 |
| `strike` | `ATM`, `ATM+N`, `ATM-N` (index near: ±10; else ±3) |
| `drvOptionType` | `CALL` or `PUT` |
| `requiredData` | any of `open` `high` `low` `close` `iv` `volume` `strike` `oi` `spot` |

06 already ran option-premium OOS on this surface — **FAIL, no promote**. Still the correct **premium** history API.

**Strike-label semantics (verified live 2026-09-11, NIFTY, with `requiredData: ["strike"]` cross-check):**

- Documented `ATM` / `ATM+N` / `ATM-N` work **both directions**: `ATM-1` CALL returned the strike one step **below** spot with a richer ITM premium; `ATM+N` steps above. Use only these.
- Undocumented `ITMn` / `OTMn` aliases are a trap: **both** map to the strike n steps **above** spot (identical data), regardless of side.
- **Unknown labels silently fall back to ATM** (a bogus string returns ATM data with no error). `premium_tape.ALLOWED_STRIKE_LABELS` whitelists the documented labels so a typo can never masquerade as ATM.
- The response fills only the side matching `drvOptionType` — one call per side (unchanged).

### G. Live market feed WebSocket — USE when founder starts paper loop

`wss://api-feed.dhan.co?version=2&token=…&clientId=…&authType=2`

- Up to **5** sockets / user, **5000** instruments / socket, **100** ids / subscribe JSON.
- Requests JSON; **responses binary little-endian**.
- Server ping 10s; silent >40s → drop.
- Subscribe codes (annexure): `15` ticker, `17` quote, `21` full, `16/18/22` unsubscribe, `12` disconnect. `23/24` full depth (20/200) on the **depth** socket.

| Packet (response code) | Payload (official) |
|------------------------|--------------------|
| Ticker `2` | LTP, LTT epoch |
| Prev close `6` | Prev close, prev OI |
| Quote `4` | LTP, last qty, LTT, ATP, volume, tot sell/buy qty, day O/H/L/C |
| OI `5` | Open interest |
| Full `8` | Quote + OI + OI day high/low + **5-level** bid/ask (20 bytes × 5) |
| Index `1` | Index packet (annexure) |
| Disconnect `50` | Reason code (805 = too many sockets) |

**Efficient agents:** WS for live INDEX + ATM OPTIDX + maybe FUTIDX. Do **not** hammer `/marketfeed/quote` every tick. Chain still REST at ≥3s unique (we use 3m).

20-level: ≤50 instruments / connection; bid (`41`) and ask (`51`) packets separately, 20 × 16 bytes. 200-level: **1 instrument / connection**. Official page: https://dhanhq.co/docs/v2/full-market-depth/.

### H. Orders / super / forever — NEVER (document so nobody “discovers” them)

Regular (`https://dhanhq.co/docs/v2/orders/`):

| Method | Path |
|--------|------|
| POST | `/orders` |
| PUT | `/orders/{order-id}` |
| DELETE | `/orders/{order-id}` |
| POST | `/orders/slicing` |
| GET | `/orders` `/orders/{order-id}` `/orders/external/{correlation-id}` |
| GET | `/trades` `/trades/{order-id}` |

Place body includes `transactionType` `exchangeSegment` `productType` `orderType` `validity` `securityId` `quantity` `price` `triggerPrice` `afterMarketOrder` `amoTime` `boProfitValue` `boStopLossValue` `correlationId`. Statuses: TRANSIT PENDING REJECTED CANCELLED PART_TRADED TRADED (+ super CLOSED/TRIGGERED).

**GET order/trade book** does not need static IP. Still **do not** wire GET into the customer ticket as “we are live.”

Super: `POST/PUT/GET /super/orders`, `DELETE /super/orders/{id}/{ENTRY_LEG|TARGET_LEG|STOP_LOSS_LEG}` — entry + target + SL + trail. Needs static IP.

Forever / GTT: `POST/PUT/DELETE /forever/orders`, list docs show `GET /forever/orders` and also `GET /forever/all` — **VERIFY which list path is current before any future read.** `SINGLE` / `OCO`. Needs static IP.

Skill pack defaults: confirm before place, LIMIT default, lot check, warn notional > ₹50k. **We go further: refuse all writes.** Official skill also says market orders may be converted to limit with MPP.

### I. Portfolio — READ-ONLY later / NEVER writes

| Method | Path | Data | Desk |
|--------|------|------|------|
| GET | `/holdings` | Demat qty, T1, avg cost, ISIN | Not index-option inventory. |
| GET | `/positions` | Day + carry F&O: netQty, realized/unrealized, `drvExpiryDate` `drvOptionType` `drvStrikePrice` | Future shadow vs paper. |
| POST | `/positions/convert` | Intraday ↔ CNC | NEVER. |
| DELETE | `/positions` | **Exit all + cancel all** | NEVER. |

F&O product types: `INTRADAY`, `MARGIN` only (not CNC/MTF).

### J. Funds & margin — READ-ONLY later

| Path | You get | Desk |
|------|---------|------|
| GET `/fundlimit` | `availabelBalance` (official spelling), SOD, collateral, utilized, withdrawable | Customer capital check — not a signal. |
| POST `/margincalculator` | `totalMargin` span/exposure/VAR, brokerage, leverage, insufficient | Pre-flight **if** we ever paper-size a lot. Indicative, same session. |
| POST `/margincalculator/multi` | Basket margins + hedge_benefit | Same. |

### K. Statements — READ-ONLY later

| Path | You get |
|------|---------|
| GET `/ledger?from-date=&to-date=` | Debit/credit, running bal, voucher |
| GET `/trades/{from}/{to}/{page}` | Fills + statutory charges (STT, stamp, brokerage, …) |

Useful for **after-cost** recon when we have *our* paper fills — not for inventing Dhan fills.

### L. Trader control — NEVER writes; GET kill status optional

| Path | Role |
|------|------|
| POST/GET `/killswitch` | Disable trading for the day. NEVER POST from agents. |
| POST/DELETE/GET `/pnlExit` | Auto-exit on ₹ profit/loss. NEVER POST. |

### M. Conditional Trigger / ScanX / charts UI — not series APIs

Annexure lists **alert comparison** indicator **names** (`SMA_*`, `EMA_5…200`, `RSI_14`, `MACD_*`, BB, ATR, Stochastic). That is for **Dhan’s alert product**, not a candle-of-RSI endpoint.

- No `EMA_9` in annexure.
- Supertrend on tv.dhan.co / ScanX = **UI**. We may **compute** ST/MACD/RSI from **our** stored OHLC as confirm-or-kill ([`SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)).
- `/alerts/orders` — **not wired**. Do not live-trade it.
- ScanX: fundamentals / screeners Dhan REST does not give. **Out of product** unless founder adds a ScanX ticket. Not a substitute for `@DhanHQ` transcripts.

### N. eDIS / TPIN — NEVER

Delivery authorization. Irrelevant to CE/PE buy-first paper.

---

## Efficient gather (WebSocket-first) — standing 00 call

**Do not start the loop until the founder asks.** This is the plan so we do not burn Quote (1/s) or Data (5/s) limits.

Dhan’s own skill (`references/live-feed.md`, fetched from [dhan-oss/dhanhq-skills](https://github.com/dhan-oss/dhanhq-skills) 2026-09-10) says the same split we will use:

| Need | Skill says | We do |
|------|------------|--------|
| Point-in-time snapshot | REST `ticker_data` / `ohlc_data` / `quote_data` | Boot / one-shot only |
| Live LTP / quote / OI on known ids | `MarketFeed` WebSocket | **Default live path** |
| Full chain + Greeks + all strikes | REST `option_chain` (1 unique / 3s) | **Must stay REST** — there is no chain WS |
| History / backtest bars | REST charts + rollingoption | PRE / nightly, not a tick loop |
| 20/200 book | `FullDepth` (50 ids / 1 id; NSE_EQ + NSE_FNO only) | **Skip** for default ticket (uses a 2nd of 5 sockets) |
| Order / fill stream | `OrderUpdate` | **Skip** — we do not place |

WS is **not** rate-limited like REST quotes. Caps are **connection** caps: 5 sockets / user, 5000 ids / socket, 100 ids per subscribe JSON, ping 10s / drop ~40s. Official feed: `wss://api-feed.dhan.co`. We already have this in `dhan_client.feed.MarketFeedCollector` — **do not vendor** their `MarketFeed` example or `place_*_order.py`.

**Honest limit:** WS will not give you greeks, full strike OI, or IV. Those stay on `/optionchain`. WS **does** replace looping `/marketfeed/ltp` and `/quote` (that is the 1/s trap).

### Live socket (one connection)

Subscribe after the first chain (so we know ATM `security_id`s):

| Instrument | Count | Mode | Why |
|------------|------:|------|-----|
| INDEX NIFTY / BANKNIFTY / SENSEX | 3 | Ticker or Quote | Spot. Not futures. |
| FUTIDX same 3 | 3 | Quote | Teacher tape / lean. Ids from master (they rotate). |
| ATM CE + ATM PE × 3 | 6 | **Full** | Premium LTP + OI + 5-level hint without REST quote. |
| Optional ATM±2 CE/PE × 3 | ≤24 | Ticker | Wings without another quote poll. |
| Cash constituents (Nifty 50 + BN + Sensex names) | ~90 | **Ticker** | HOLD overlay. **Do not** 1/s REST LTP in a loop. |

That is well under 5000. Stay on **one** MarketFeed socket. Save the other four; do not open FullDepth or OrderUpdate.

After each 3m chain: if ATM `security_id` changed, **unsubscribe old / subscribe new** (skill: `subscribe_symbols` / `unsubscribe_symbols`). Do not grow a zombie id list.

Build 1m/3m/5m bars **locally** from WS ticks + the warehouse reader. Do not call `/charts/intraday` every minute.

### REST that must remain (slow, scheduled)

| Call | Cadence | Why REST |
|------|---------|----------|
| `GET /profile` | Boot + token worry | Session |
| Scrip master CSV | Once / day | Lots, FUT/OPT ids |
| `/optionchain/expirylist` | Boot / expiry day | Dates |
| `/optionchain` × 3 underlyings | **3m** (`desk_intel.poll.chain_interval`) | Full book + greeks. Space ≥3s unique (three names ≈ 9s sequential; 3m budget is huge). |
| `/charts/*` | PRE / gap-fill / ML | History. Data API 5/s, 90-day pages. |
| `/charts/rollingoption` | Backtest jobs | Expired premium |
| `/marketfeed/ltp` | **Never in the live loop** | Boot-only if WS is down |

If WS dies: reconnect (our collector already does). Fallback REST LTP is **one** snapshot, then back to WS — not a 1s poll.

### Skill pack vs our code — verdict (no copy)

Checked on GitHub 2026-09-10: `SKILL.md`, `references/{live-feed,option-chain,market-data,error-codes,instruments,options-analysis-patterns,backtesting-with-dhan}`, `scripts/` (`dhan_helpers`, `resolve_security`, `validate_order`, `trade_logger`), `examples/` (`place_equity_order`, `place_fno_order`, `super_order_with_sl`, live WS, iron condor, …).

| Their artifact | Add to our tree? |
|----------------|------------------|
| Field lists, 3s chain, 1/s quote, WS vs snapshot split | **Already in this book.** Refresh if Dhan edits. |
| `fetch_chain_df` / `ce_ltp` names | **No.** Repo-defined aliases, not Dhan fields. We parse `data.oc`. |
| `MarketFeed` / `FullDepth` samples | **No.** We have `MarketFeedCollector` + official binary decode. |
| `validate_order` / `place_*` / super / forever / `OrderUpdate` | **Never.** SafeMode. |
| ScanX / PCR-max-pain cookbook | **No** as production. Heuristic only. |
| Install `npx skills add dhan-oss/dhanhq-skills` into Cursor | Optional **read-only** for humans. Agents must still refuse writes. |

**We are good on code for now.** Next implementation (when founder asks) is **wire the existing feed** to warehouse ticks + 3m chain REST — not a second client.

### Day plan (analyst + developer)

```text
Once / day (or on boot) — REST, tiny
  1. GET /profile → dataPlan Active
  2. Scrip master CSV → lots, FUTIDX, OPTIDX
  3. POST expirylist × 3

PRE / one-shot (founder ask) — REST history only
  4. Charts INDEX 1/5/15/60 + daily → warehouse; resample 3m/1w
  5. Optional later: same charts FUTIDX + ATM OPTIDX
  6. One chain × 3 → strike book + ATM ids

Live session (founder must start) — WS default
  7. ONE wss://api-feed.dhan.co : INDEX + FUTIDX + ATM CE/PE [+ constituents Ticker]
  8. REST chain every 3m only; swap ATM ids on the socket
  9. No /marketfeed/ltp loop. No 20-level unless dealer ticket.
 10. MIX → dealer → counsel (no CE/PE from LLM)

Backtest / ML — REST offline
 11. Stored bars + rollingoption ATM±
```

**Agents / Cursor:** this file + [`packages/dhan-client`](../../../packages/dhan-client/). Official skill is **how Dhan documents the SDK**, not an order bot.

**Counsel:** `DHAN_API_REVIEW` — they do not invent endpoints or CE/PE.

---

## Map: Dhan surface → our code / tables

| Dhan | Package / table | Status (2026-09-10) |
|------|-----------------|---------------------|
| `/profile` | `dhan_client.profile` | Live 200; dataPlan Active |
| scrip master | `dhan_client.instruments` | Used; TATAMOTORS rename = UNKNOWN |
| `/marketfeed/ltp` | `quote.py` | Probe 200 INDEX |
| `/optionchain*` | `option_chain.py` | Probe 200; warehouse desk-book |
| `/charts/intraday` `historical` | `historical.py` + `warehouse` `ohlc_bars` | INDEX multi-TF stored; 3m/1w derived |
| `/charts/rollingoption` | backtest path | Used 2026-09-03; FAIL / no promote |
| Market feed WS | `feed.py` | Skeleton; paper loop **not** started |
| 20/200 depth | — | Not required for default ticket |
| Orders / super / forever | `execution.py` | **Always refuse** |
| Funds / positions / ledger | — | Not wired |
| MCP / Cloud / skill order scripts | — | Out of scope |

---

## Official Agent Skills — what we take / reject

Pack (12): orders, portfolio, market-data, option-chain, instruments, funds, live-feed, error-codes, common-workflows, options-analysis (PCR, max pain, IV skew, payoff), backtesting-with-dhan, ScanX.

**Take (VALIDATION of *how Dhan works*):**

- Confirm `dataPlan` before quotes.
- Epoch timestamps → IST explicitly.
- Chain keyed by strike **string** under `data.oc`; helper names like `ce_ltp` are **ours**, not Dhan’s.
- Intraday method is `intraday_minute_data` / `POST /charts/intraday` — not a fictional `historical_minute_data`.
- Quote 1/s; chain 1 unique / 3s.
- Lot/tick from master, not hardcoded.
- Their own warning: SDK `expiry_code` may accept `3`; **docs say 0/1/2** — prefer docs.

**Reject for this company:**

- `place_order` / super / forever / kill_switch examples.
- Iron-condor / credit / sell default (we are buy-first; 013/014 stay PARKED).
- ScanX PE/EPS/RSI as production features.
- Treating skill “options analysis” PCR/max-pain as a proven MIX (heuristic only; extreme PCR without price = HOLD overlay).
- Installing their skill as an autonomous trader (they say the same: assistant, not auto-trader). We are stricter: **no write API**.

---

## Sandbox vs live vs paper

| Environment | Tape | Our policy |
|-------------|------|------------|
| `api.dhan.co` + data plan | Real exchange | Allowed **reads** for probe / one-shot ingest / future paper `--live-chain`. |
| Sandbox swagger | Fake | Learn schemas (`UserIPResponse`, order bodies). **Not** a backtest. |
| Our `--offline` fixtures | Frozen JSON | Default when token empty or founder says no live. |
| Dhan Cloud runs | Their runtime | Do not deploy STRATs there. |

---

## Faculty consensus (2026-09-10)

```text
From: 00 after 01 / 02 / 03 / 04 / 05 / 06 / 09 + official fetch
Gate: not RESEARCH_READY_FOR_PROGRAMMING

01: Official docs + dhanhq-skills are TIER_2_SECONDARY (how the API works).
    Not a substitute for @DhanHQ transcripts. Promo trading-apis page ≠ rate table.
02: Store greeks/IV; do not treat as P(win). Compute ST/MACD/RSI from our OHLC only.
    Charts intervals are 1/5/15/25/60. 3m/1w = resample, labeled derived.
03: INDEX ≠ FUTIDX ≠ OPTIDX. Chain fields above are SOURCE_FACT. Weights DI.
    INDEX volume ≠ VWAP tape. Lot from master.
04: Honest ticket numbers = live ATM LTP + spot from chain/ltp. SL/TP geometry
    remains HYPOTHESIS. 5m ST/MACD = confirm-or-kill. No STRAT-015+. KEEP_ALL.
05: Constituent shock = HOLD overlay, not a 50-name stock product. Dealer still
    needs same-session premium range. News / extreme PCR = hold ticket.
06: Rollingoption + stored bars = research OOS path. Prior premium book FAIL.
    Do not promote because we now “know the APIs.”
09: NOTES_ONLY. Inventory ≠ five-pass. Auditor PASS ≠ product gate.

Accepted: one desk book (this file); developers code only USE paths via dhan-client;
  analysts design MIX on fields that exist; counsel reviews API use, not CE/PE.
Rejected: Second HTTP client; MCP/skill order placement; invent 3m REST;
  sandbox as live tape; /alerts/orders; live orders.
UNKNOWN: swagger 409 this session; forever list path `/forever/orders` vs `/forever/all`;
  exact 20-level WS host if Dhan moved it; current official index basket vs our names.
```

---

## UNKNOWN / DATA_INSUFFICIENT

- Official **index weights** — not in Dhan.
- Continuous **FUTIDX** / **OPTIDX premium** candles in the default warehouse pull (INDEX is in).
- Whether Dhan **intraday 5y** includes every expired OPTIDX id (rollingoption is the documented expired path).
- GIFT/SGX/pre-open — **not** Dhan REST.
- CAS / IEP live — not Dhan REST.
- `docs.dhanhq.co/api/v2/` and `/skills/` HTTP **409** on fetch this session — use `dhanhq.co/docs/v2/` + GitHub skill pack.

---

## Related files

- Client constants: [`packages/dhan-client/src/dhan_client/endpoints.py`](../../../packages/dhan-client/src/dhan_client/endpoints.py)
- Indicator vs chart: [`../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md`](../../01_research/docs/DHAN_OFFICIAL_INDICATORS.md), [`../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md`](../../02_phd_math/docs/DHAN_INDICATOR_API_MAP.md)
- Ecosystem URL classes: [`../../01_research/docs/DHAN_ECOSYSTEM.md`](../../01_research/docs/DHAN_ECOSYSTEM.md)
- Chain metrics: [`CHAIN_METRICS.md`](CHAIN_METRICS.md)
- Warehouse plan: [`../../00_orchestrator/docs/DATA_PLAN_DESK_BOOK.md`](../../00_orchestrator/docs/DATA_PLAN_DESK_BOOK.md)
- Counsel: [`../../00_orchestrator/docs/COUNSEL_LLM.md`](../../00_orchestrator/docs/COUNSEL_LLM.md)

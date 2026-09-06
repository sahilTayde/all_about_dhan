# packages/dhan-client

Generic **DhanHQ v2** REST + WebSocket skeleton. Dhan / DhanHQ **only**.

No live orders. No strategy. No YouTube. Tokens from env / `.env` only — never committed, never logged, never pasted into chat.

Official docs used (do not invent paths):

- [Introduction](https://dhanhq.co/docs/v2/)
- [Authentication](https://dhanhq.co/docs/v2/authentication/)
- [Market Quote](https://dhanhq.co/docs/v2/market-quote/)
- [Historical Data](https://dhanhq.co/docs/v2/historical-data/)
- [Option Chain](https://dhanhq.co/docs/v2/option-chain/)
- [Live Market Feed](https://dhanhq.co/docs/v2/live-market-feed/)
- [Instruments](https://dhanhq.co/docs/v2/instruments/)
- [Annexure](https://dhanhq.co/docs/v2/annexure/)

See [`docs/SECURITY.md`](../../docs/SECURITY.md) and [`.env.example`](../../.env.example).

---

## Dry-run (no live token)

Empty `DHAN_CLIENT_ID` / `DHAN_ACCESS_TOKEN` ⇒ dry-run. No HTTP, no WebSocket.

```bash
cd /Users/sahiltayde/Documents/all_about_dhan
python3 -m venv .venv
source .venv/bin/activate
pip install -e packages/dhan-client

python -m dhan_client status
python -m dhan_client --dry-run quote
python -m dhan_client --dry-run historical
python -m dhan_client --dry-run option-chain
python -m dhan_client --dry-run feed
python -m dhan_client --dry-run execution
```

`status` prints whether env **names** are set (`true`/`false`), never values.

Rate limits (official): [`docs/RATE_LIMITS.md`](docs/RATE_LIMITS.md). Quote **1/s**, Data **5/s**, option chain **1 unique / 3s**. Order APIs are **never called**.

---

## Live Data API (no orders)

```bash
python -m dhan_client --live status
python -m dhan_client --live execution   # must refuse place_order
python -m dhan_client --live profile     # keys only
python -m dhan_client --live paper-probe # NIFTY/BANKNIFTY/SENSEX yaml scrips; writes data/recon/PAPER_PROBE_*.json
python -m backtest_engine --live         # INDEX 5m counts; win_rate null
python -m desk_intel morning --live      # news+chain fuse; HOLD ≠ catalog delete
```

Missing Data API plan → `DH-902` / `806`. Do not invent REST fields.

---

## Modules

| Module | Role |
|--------|------|
| `dhan_client.config` | Load `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` from repo-root `.env` |
| `dhan_client.logging_util` | Redact tokens in logs / URLs |
| `dhan_client.endpoints` | Documented base URL + paths only |
| `dhan_client.annexure` | Exchange / feed enums from annexure |
| `dhan_client.rest` | Generic GET/POST helper + dry-run envelope |
| `dhan_client.quote` | `POST /marketfeed/ltp`, `/ohlc`, `/quote` |
| `dhan_client.historical` | `POST /charts/historical`, `/charts/intraday` |
| `dhan_client.option_chain` | `POST /optionchain`, `/optionchain/expirylist` (live calls gated 3s) |
| `dhan_client.rate_limit` | `MinIntervalGate` — option-chain 1 unique / 3 s |
| `dhan_client.instruments` | Public scrip-master CSV URLs + `GET /instrument/{segment}` |
| `dhan_client.feed` | WS connect, subscribe (≤100/msg), reconnect |
| `dhan_client.decode` | Binary header + ticker; quote/full placeholder |
| `dhan_client.refresh` | **Not implemented** — VERIFY FROM DOCS |
| `dhan_client.execution` | SafeMode: `place_order` always raises |
| `dhan_client.client` | Facade `DhanClient` |

Room to edit: request TypedDicts, decode offsets, instrument CSV column names.

---

## What needs a real token (later)

Put values in repo-root `.env` (never chat). Then:

```bash
python -m dhan_client --live status
python -m dhan_client --live quote          # needs Data API plan
python -m dhan_client --live feed           # Live Market Feed WS
```

| Call | Token? | Also |
|------|--------|------|
| Quote / historical / option chain | yes | Data API subscription (`DH-902` / `806` if missing) |
| Live feed WebSocket | yes | Query `token` + `clientId`; up to 5 sockets |
| Scrip-master CSV on `images.dhan.co` | no (docs show a public URL) | Large file; dry-run skips download |
| `GET /v2/profile` | yes | Not wrapped yet — easy add in `rest.py` |
| Token refresh (`/v2/RenewToken`) | yes | **Unwired.** Can invalidate the current token. VERIFY method + response body |
| Orders | — | **Refused** in `execution.py` |

NIFTY / BANKNIFTY / SENSEX **security IDs** are not hardcoded. Look them up in the instrument CSV (`IDX_I` / `OPTIDX`). Official option-chain example uses `UnderlyingScrip: 13` without naming the index.

---

## UNKNOWN / VERIFY FROM DOCS

- **`DHAN_REFRESH_TOKEN`**: official RenewToken curl uses the current `access-token`, not a refresh_token field.
- **`DHAN_CLIENT_SECRET`**: official individual OAuth uses `app_id` / `app_secret`, not this name.
- **RenewToken HTTP method**: curl has no `-X`. Do not assume POST.
- **RenewToken response body**: not shown on the auth page we fetched.
- **Historical `client-id` header**: quote/option-chain require it; historical curl omits it.
- **Intraday `interval`**: table says integer; sample JSON uses `"1"` (string). We send a string.
- **Feed `message length`**: full packet vs payload-after-header — heuristic in `decode.py`.
- **Index packet (code 1) / market status (code 7)**: annexure names only; payload UNKNOWN.
- **Compact CSV security-id column name**: inspect the live header (`SECURITY_ID` candidates in `instruments.py`).
- **`GET /instrument/{exchangeSegment}`**: path documented; method inferred from `curl --location`.

---

## Headers (live)

Most data POSTs: `access-token`, `client-id`, `Content-Type: application/json`.

Feed URL: `wss://api-feed.dhan.co?version=2&token=...&clientId=...&authType=2`.

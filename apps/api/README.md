# apps/api

FastAPI skeleton for **all_about_dhan**. DhanHQ only. Tokens stay in `packages/dhan-client` — this app never copies them.

**This pass:** `GET /health`, mock `GET /signals` (dashboard shape), optional `/ws/feed`.  
**Not in this pass:** strategy, live orders, YouTube.

Owned by team 07_coding. Client: [`packages/dhan-client`](../../packages/dhan-client/README.md).

---

## Dry-run (no live token)

Empty Dhan env vars is enough. Health reports `dry_run: true`.

```bash
cd /Users/sahiltayde/Documents/all_about_dhan
python3 -m venv .venv
source .venv/bin/activate
pip install -e packages/dhan-client
pip install -e apps/api

python -m api
# or: uvicorn api.main:app --app-dir apps/api/src --reload --host 127.0.0.1 --port 8000
```

Then:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/paper/signal   # same JSON as apps/web/public/mock/signal.json
curl -s http://127.0.0.1:8000/signals        # alias of /paper/signal
curl -s -X POST http://127.0.0.1:8000/signals/mock-nifty-001/took-trade \
  -H 'Content-Type: application/json' \
  -d '{"took_trade": true, "lots": 1, "spot": 24850, "reported_pnl": 12.5}'
```

Point the Vite UI at this API: `apps/web/.env` with `VITE_API_URL=http://127.0.0.1:8000`.

OpenAPI: http://127.0.0.1:8000/docs

WebSocket (dry-run placeholder, then idle pings):

```bash
# e.g. websocat or a browser dashboard later
# ws://127.0.0.1:8000/ws/feed?segment=NSE_EQ&security_id=1333&mode=ticker
```

---

## `/paper/signal` and `/signals` (dashboard)

Same JSON as [`apps/web/public/mock/signal.json`](../web/public/mock/signal.json): `meta`, `underlyings`, `signals` keyed by NIFTY / BANKNIFTY / SENSEX, each with `side` (`BUY_CE` / `BUY_PE`), strike/entry/stop/target, `expiry`, `systemOutcome.mtmPts`, `staged`, and `lifecycle.outcome` (`INVALIDATED` / `ACHIEVED` / `STOPPED` / `LOST` / `EXPIRED` or null while open). Mock: BANKNIFTY ACHIEVED, SENSEX INVALIDATED.

The web app calls **`GET /paper/signal`**. `/signals` is an alias. Took-trade stays local in the UI for now; `POST /signals/{id}/took-trade` is an in-memory stub (`mock-nifty-001`, …).

Edit `src/api/models.py` when a reviewed spec exists. `expiry: "placeholder"` is mock-only.

---

## Modules

| Path | Role |
|------|------|
| `src/api/main.py` | App factory, `/health`, `/signals` |
| `src/api/models.py` | Pydantic dashboard models |
| `src/api/store.py` | In-memory mock store |
| `src/api/ws.py` | Optional feed proxy |
| `src/api/config.py` | Wraps `dhan_client.config.load_settings` |

---

## What needs a real token tomorrow

Nothing for `/health` or `/signals`. Those stay mock until a strategy is reviewed.

For `/ws/feed` against Dhan: `DHAN_CLIENT_ID` + `DHAN_ACCESS_TOKEN` in repo-root `.env`, Data API access, a real `security_id` from the instrument master, and `?live=1`. Default WS is dry-run even if tokens exist.

Do not enable `execution.place_order` from this app.

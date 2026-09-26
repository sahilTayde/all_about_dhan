# brokers (PR-002)

Broker-agnostic order execution. **Paper is the default. Nothing here is wired into the running
desk yet** (that is PR-008).

- `orders.py`: `TradeIntent` (from risk-engine) → `Order` state machine
  `NEW → SUBMITTED → PARTIAL → FILLED | REJECTED | CANCELLED | EXPIRED`; every transition is
  logged, kept in `order.history`, and (with `attach_ledger`) written to the ledger.
  `BrokerAdapter` is the interface a Forex broker would implement later.
- `paper.py`: `PaperBroker`. Fills on the **next** tick (`on_tick(symbol, ltp)`), slippage
  `slippage_ticks × tick_size` (default 1 × ₹0.05). MARKET, LIMIT, SL, SL-M, super order
  (target + stop legs, OCO, trailing jump), modify, cancel, exit, flatten all.
- `dhan.py`: `DhanBroker`. Maps intents to Dhan v2: `POST /orders` (MARKET, LIMIT,
  STOP_LOSS, STOP_LOSS_MARKET), `POST /super/orders` (entry + target + SL + trailingJump),
  `PUT /orders/{id}` and `PUT /super/orders/{id}` (target shift, trailing SL),
  `DELETE /orders/{id}`, `DELETE /super/orders/{id}/ENTRY_LEG`, exit = opposite MARKET order,
  flatten all = `DELETE /positions`, `GET /orders/{id}`, `GET /orders`, `GET /positions`,
  `GET /fundlimit`. Uses `dhan_client.RestClient` for auth; `correlationId` = our client order id.
- `reconcile.py`: broker positions/orders vs the ledger. Any mismatch (or broker error) is logged
  as `RECONCILIATION MISMATCH ALARM`, written to `recon_runs`, halts new entries in the risk
  engine and raises a health alert until a clean run.

## Live gate

`DhanBroker` refuses (raises `LiveOrderRefused` and logs) any order, modify, cancel, exit or
flatten unless **all** are true:

1. `config/risk_limits.yaml` `mode` is `limited_live` or `live`;
2. env `ALL_ABOUT_DHAN_LIVE_CONFIRM` is exactly `I_UNDERSTAND_REAL_MONEY`;
3. the call carries a `RiskDecision` from the risk engine that approved this exact action and
   client order id in the last 30 s.

Idempotency: one client order id is sent at most once. If Dhan's response is lost, the retry
first asks `GET /orders/external/{correlationId}`; if that lookup fails it refuses to resend.

## Tests (from repo root, no credentials, no network)

```bash
PYTHONPATH=packages/ledger/src:packages/risk-engine/src:packages/brokers/src \
  .venv/bin/python -m pytest packages/brokers -q
```

`DhanBroker` is tested only through `httpx.MockTransport`; request payloads are asserted
against the Dhan v2 docs.

# DhanHQ v2 rate limits (official — do not invent)

**Source (fetched 2026-09-03):** [Introduction](https://dhanhq.co/docs/v2/) table *Rate Limit*.  
Child pages add tighter caps. This repo **does not place orders**.

| Bucket | per second | per minute | per hour | per day | This client |
|--------|------------|------------|----------|---------|-------------|
| **Order APIs** | 10 | 250 | 1000 | 7000 | **Never called.** `ExecutionClient` raises `SafeModeError`. Order modifications 25/order — unused. |
| **Data APIs** | 5 | — | — | 100000 | `/charts/historical`, `/charts/intraday` gated `1/5 s`. |
| **Quote APIs** | 1 | Unlimited | Unlimited | Unlimited | `/marketfeed/ltp`, `/ohlc`, `/quote` gated **1 s**. Max **1000** instruments / request. |
| **Non Trading APIs** | 20 | Unlimited | Unlimited | Unlimited | `GET /profile`, `GET /instrument/{segment}`. |

**Option chain (tighter than Data APIs):** [option-chain](https://dhanhq.co/docs/v2/option-chain/) — **one unique request every 3 seconds** (expiry list **and** chain share the budget). OI updates slowly. Desk default full-chain poll is **3 minutes** (`workspace.yaml`).

**Live Market Feed:** [live-market-feed](https://dhanhq.co/docs/v2/live-market-feed/) — up to **5000** instruments / connection, **100** / subscribe message, **5** connections / user, ping **10 s**, stale disconnect **40 s**.

**Intraday history:** max **90 days** per `/charts/intraday` call; intervals **1, 5, 15, 25, 60** only (no 3m token).

**Missing Data API plan:** docs mention `DH-902` / `806` — treat as subscription errors, not a reason to invent fields.

Do not poll full option chain every minute as the default. Do not burst Data API past 5/s. Do not call Order APIs from this workspace.

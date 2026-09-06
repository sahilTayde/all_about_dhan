# CAS daily — YYYY-MM-DD

**Layer:** `UNVALIDATED`  
**Session tag:** NORMAL | EXPIRY | NEWS_DAY  
**Window:** `REF_VWAP` / `IEP` / `MATCH` / `research_only`

| Underlying | Bias | Confidence | Mechanism | Realized vs 15:15 |
|------------|------|------------|-----------|-------------------|
| NIFTY | SIDEWAYS | 0.00 | CLOSING_AUCTION_SESSION | DATA_INSUFFICIENT |
| BANKNIFTY | SIDEWAYS | 0.00 | CLOSING_AUCTION_SESSION | DATA_INSUFFICIENT |
| SENSEX | SIDEWAYS | 0.00 | CLOSING_AUCTION_SESSION | DATA_INSUFFICIENT |

Confidence is lean-completeness, **not** a hit rate.

## Evidence used

- CAS IEP / imbalance / indicative index:
- Heavy-weight contribution:
- Cash vs futures (`CASH_BASIS`):
- Option chain (DhanHQ or fixture):
- News / events (URLs):
- Expiry:
- Pre-open (`PRE_OPEN`, if used):

## Gaps

- DATA_INSUFFICIENT:

## Recon

Write `../calls/YYYY-MM-DD.json`. Nightly copies into `data/recon/YYYY-MM-DD.json` → `cas_calls[]`.  
Proposals stay `BACKTEST_REQUIRED`. No auto-retune. No orders.

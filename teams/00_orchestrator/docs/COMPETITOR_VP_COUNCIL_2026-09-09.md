# Competitor VP council — AmiSignals / Stockara / Trend Finder / BreakingTrade

**Date:** 2026-09-09  
**Policy:** review only. Keys never printed. **No live orders. NO_PROMOTE.**  
**Web source caveat:** Stockara direct page returned 409; third-party snippets are `VERIFY`.

## VP Council Result

Gemini and OpenAI both answered. Substance was aligned, but OpenAI led with `DATA_INSUFFICIENT` because some competitor claims are unverified. 00 ruling: use competitor pages for **feature baseline**, not evidence of accuracy.

## Product VP

Match:

- Clear signal ticket with entry / stop / target / invalidation.
- Alerts: in-app sound/toast first, Telegram/webhook later.
- Scanner/watchlist flow.
- AI assistant category.
- Reports and history.

Reject:

- “100% accurate” marketing.
- Profit testimonials as evidence.
- Wide market scope before index options work.

## Quant VP

Match:

- Multi-timeframe confirmation.
- Volatility-aware risk manager.
- Option-chain context.
- Market profile ideas can be research, not customer clutter.

Improve:

- DhanHQ-native NIFTY/BANKNIFTY/SENSEX focus.
- Staged signal lifecycle.
- Backtestable reason codes.

## Risk VP

Add:

- Dealer feasibility before publish.
- Exit/kill/expire priority.
- LLM counsel only as risk review.
- No fake fills and no live orders.

Example accepted behavior: sudden OI reversal can create `RISK_REVIEW` / partial-booking suggestion. It cannot place an order.

## Engineering VP

Add:

- Append-only warehouse.
- Precomputed UI read model.
- WebSocket/stale heartbeat.
- Token budget and counsel cache.
- PM health cards.

Keep:

- SQLite + FTS5 now.
- Local ML first.
- No LLM on the blocking fast path.

## Customer VP

Portal must be:

- Fast.
- Mobile-first.
- Beautiful and calm.
- One primary decision.
- Plain-English why.
- Visible invalidation.
- Honest MOCK/PAPER/SHADOW labels.

## 00 Ruling

We can build similar category software, but our baseline is narrower and stronger:

```text
DhanHQ index-options signal company
  + dealer intelligence
  + mistake learning
  + local ML
  + controlled live LLM risk counsel
  + founder PM health canvas
```

This is **not** approval for live execution or win-rate claims.


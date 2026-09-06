# STRAT-013 — Bull put credit spread (weekly)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT` / **`WAITING` (not Phase-1 buy default)** / **`BACKTEST_BOOK`** (`KEEP_ALL` — not deleted; [`MIX_CATALOG.md`](../MIX_CATALOG.md) `MIX-SELL-013`, style `OPTION_SELLER`)  
**Origin:** `DHAN-DERIVED` (`gA5FtEnSABM` EN 07:20–10:50). Bind **CONFIRMED sell**.  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Do not convert to a CE ticket. Do not map this fill onto STRAT-011 buy.**

2h/1h bullish view (e.g. RSI divergence) → **sell** nearer put, **buy** further OTM put; skip 0 DTE; skip event weeks (budget example). Max loss known; margin from broker. Rupee figures in video `[UNCERTAIN_TRANSCRIPT]`.

Sideways-to-mild-up regime.

**Do not code for paper UI (BUY CE/PE) until Phase selling is opened.**

## Invalidation

Gap through short strike; event IV; defined-risk still large vs capital.

## Risk

Selling. Margin. European cash-settled still gaps.

# Nightly handoffs — REVIEW, not auto-apply

`NIGHTLY_YYYY-MM-DD.md` is written by `python -m desk_intel nightly` (POST_MARKET). It is a **paper + shadow** recon packet for **02_phd_math**.

## What you do

**Read and REVIEW.** Check math/indicator notes, lagging-late copy, and whether a candidate hint is even a well-posed parameter (OHLC Supertrend vs REST, session close VERIFY, etc.). Keep every suggestion **UNVALIDATED**.

## What you do not do

- **Do not auto-apply** params, STRAT mix, or yaml knobs because one recon day looked bad.
- **Do not** treat this folder as production. Nightly never writes `teams/04_quant/docs/candidates/` or `packages/indicators/`.
- **Do not** invent backtest results. Team **06** owns the [RETUNE_GATE](../../../06_backtesting/docs/RETUNE_GATE.md): OOS + `NORMAL` (non-event) days; promote only on robust metrics vs current, or a documented glitch fix that backtests clean.

News days / expiry days (`NEWS_DAY` / `EXPIRY`) make the book look broken. Default: **keep current strategy**. JSON field `retune_proposal.status` is **`BACKTEST_REQUIRED`** until 06 says otherwise.

Older `NIGHTLY_*.md` files may lack `session_kind` / `RETUNE_PROPOSAL` sections; re-run nightly `--offline` for the stub schema. Do not live-trade.

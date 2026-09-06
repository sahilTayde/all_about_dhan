# STRAT-001 — Dual-TF MACD + MA stack, long premium

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT`  
**Origin:** `DHAN-DERIVED` recipe (`HAUSZx-hYdY` EN 41:32–01:03:10). Phase-1 **index-only** `market: [NIFTY, BANKNIFTY, SENSEX]` = **`PROJECT_MIX`**.  
**Bind:** [`TRANSCRIPT_STRATEGY_BIND.md`](../../../01_research/docs/handoffs/TRANSCRIPT_STRATEGY_BIND.md)  
**Not claimed profitable.**

```yaml
strategy_id: STRAT-001
name: DualTF_MACD_MA_LongPremium
market: [NIFTY, BANKNIFTY, SENSEX]  # PROJECT_MIX — spoken universe is NIFTY 100 stocks + options application
instrument: {type: INDEX_OPTION, side: BUY}
timeframe: {primary: 1h, confirmation: 5m}  # 10m child alt spoken; 15m child alt spoken (01:02:51). 2h parent NOT_IN_EN (that is gA5, different recipe)
regime: trending (bull CE / bear PE)
```

Spoken universe (`HAUSZx` 43:14–44:19): **Nifty’s top 100 stocks**; “I am following this strategy in Nifty 100.” Options application is spoken (01:03:04–01:03:09). The Phase-1 **index-options book** is a transfer — tag **`PROJECT_MIX`**, not “Dhan taught NIFTY/BN/SENSEX as the only chart.”

## Rule (testable)

**Bullish:** Parent 1h: MACD histogram > 0 **and** MA(10) > MA(30) > MA(100).  
Child 5m (or spoken 10m): same two conditions; **buy CE** on break of that child candle high (HAUS **entry** — not desk staging).  
**Bearish:** invert histogram < 0 and MA(10) < MA(30) < MA(100); buy PE.

MACD: spoken 12/26 then ×3 **or** ×4 all params (`WEAK` — do not freeze 48/104/36); histogram only. Signal length 9 **not clearly spoken**.  
**Test grid (do not pick a winner on IS):** defaults 12/26/9 vs 48/104/36 vs 36/78/27.  
MA 9 vs 10 (`WEAK`) and 100 vs 300 (`CONFLICT` same video): **search, do not silently correct**.

Attach STRAT-002 (strike/target) and STRAT-007 (clock) — **same speaker**. Do **not** attach 002 to 003. Underlying stop = recent swing (HAUS). Flatten EOD default.

Desk **5m MACD confirm-or-kill** is a **different** hypothesis (`PROJECT_MIX` / [`SIGNAL_STAGING.md`](../SIGNAL_STAGING.md)). Do not average with this HAUS entry.

## Data

Underlying (prefer **futures** for tradable series; speaker used **NIFTY 100 stocks**/spot) 1h+5m OHLC; option bid/ask.

## Invalidation

No edge after costs on both NIFTY and one of {BANKNIFTY, SENSEX}; or MACD×N is unidentified and all grids fail OOS; or the index transfer (`PROJECT_MIX`) fails while NIFTY-100 cash/options would not.

## Risk

Discrete lots; stop on underlying ≠ known rupee option loss; `[UNCERTAIN_TRANSCRIPT]` params. Index book is **`PROJECT_MIX`**.

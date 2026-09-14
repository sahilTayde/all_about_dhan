# MIX-TV-EP-001..023 rule cards (no Pine)

**Retrieved:** pine-facade 2026-09-14. **Layer:** HYPOTHESIS. **Gate:** not `RESEARCH_READY_FOR_PROGRAMMING`.  
**KEEP_ALL** `STRAT-001`–`014`. IDs stay `MIX-TV-EP-*`. No live orders. Win rate is not customer truth.  
Public source was read to extract **entry/exit/session/pyramiding/commission + inputs**. Full Pine is **not** in git.

Indian OPTIDX notes that apply to **all 23:** NSE cash session **09:15–15:30 IST** (not 24×7); option **theta/decay** on PREMIUM tape; INDEX points ≠ premium P/L; buy CE/PE first (no invented Dhan fields).

| Class | Meaning |
|-------|---------|
| OHLC_ANYWHERE | Signal uses OHLC that can run on any chart |
| FX_FX / FX_SESSION | FX sessions, leverage, or London/NY boxes |
| CRYPTO_MARTINGALE | Crypto 24×7 and/or martingale size |
| TV_VIZ_TEMPLATE | Report/template/external signal — tradeable core is a stand-in or flat |
| US_EQUITY_ETF | TQQQ/weekly US session recipe |
| COMMODITY | Ag harvest calendar |

---

### MIX-TV-EP-001 — Ag Selling Model — `ag_sell` — COMMODITY — **partial**
- **Entry:** short when `high ≥ SMA(src,40) + ATR(20)×2.5` in sale window (harvest month + delay). **Exit:** cover at next harvest. **Pyramiding:** 3. **Commission:** 300 cash/contract.
- **Inputs:** Source=close, MA=40, ATR=20, factor=2.5, harvest month=11, delay=2, days between=30.
- **Gap:** NSE options have no crop calendar; 1m premium ≠ daily grain futures.

### MIX-TV-EP-002 — One Percent A Week — `one_pct_week` — US_EQUITY_ETF — **partial**
- **Entry:** Monday regular open; limit long at −1%. **Exit:** +1% next day, BE after −0.5% (TV), Friday close flatten. **Qty:** 10% equity. No named commission.
- **Gap:** TQQQ weekly; 0.5% BE not in lean simulator.

### MIX-TV-EP-003 — CSV Report Generator — `csv_replay` — TV_VIZ_TEMPLATE — **partial**
- **Entry:** `strategy.order` from CSV fills. **No OHLC alpha.** Margin 0/0.
- **Gap:** always HOLD unless `csv_long` test hook. Queued so the MIX row is never stub.

### MIX-TV-EP-004 — TrendMaster Pro — `trendmaster_ma` — FX_SESSION — **partial**
- **Core entry:** SMA/EMA short 9 vs long 21 cross. **Sessions:** Asia/London/NY AM/PM default on (FX). SL% + RR TP. Overlay=true.
- **Gap:** FX session boxes skipped on NSE 09:15–15:30; S/R/RSI/MACD soup not ported.

### MIX-TV-EP-005 — Double Tap — `double_tap` — OHLC_ANYWHERE — **partial**
- **Entry:** double top → short, double bottom → long (pivot length 50, tol 15%). **Commission:** 0.04%. Cash qty 1000 / capital 1000.
- **Gap:** Fib target/stop, 3Commas alerts omitted.

### MIX-TV-EP-006 — Trailing SL/Target — `ema_trail` — OHLC_ANYWHERE — **partial**
- **Entry:** EMA 20/50 cross, process_orders_on_close. **Exit:** % or point trail (TV).
- **Gap:** trail engine not in `simulate_leans`.

### MIX-TV-EP-007 — TTS Backtester — `tts_ma_cross` — TV_VIZ_TEMPLATE — **partial**
- **Internal default:** SMA 21/49 cross + EMA200 filter (not fully ported). **Pyramiding:** 0. **Commission:** 0.1%. Session day/time filters.
- **Gap:** 222-input trail/limit/stop template.

### MIX-TV-EP-008 — 3Commas Bot — `bot3c_ma` — OHLC_ANYWHERE — **partial**
- **Entry:** EMA 21 vs EMA 50. **Commission:** 0.05%, slippage 1. Optional ATR trail / R:R.
- **Gap:** webhook JSON omitted.

### MIX-TV-EP-009 — Monthly Returns table — `pivot_rev` — TV_VIZ_TEMPLATE — **partial**
- **Demo entry:** pivot-high stop long / pivot-low stop short (left=2, right=1). **Commission:** 0.1%, 25% equity. calc_on_every_tick.
- **Gap:** monthly table is viz.

### MIX-TV-EP-010 — Leverage/Margin demo — `stoch_kd` — FX_FX — **partial**
- **Entry:** Stoch K(13) SMA smooth 4 cross D(3); long if K<80, short if K>20. **Pyramiding:** 100. **Margin:** ~1.67% (30×). TP 100 ticks.
- **Gap:** leverage is TV emulator.

### MIX-TV-EP-011 — Risk position size — `risk_size_demo` — TV_VIZ_TEMPLATE — **partial**
- **Entry:** `bar_index % 333` long / `% 444` short. **SL:** 10%. **Risk:** 2% equity. Margin 10.
- **Gap:** random cadence, not a market rule.

### MIX-TV-EP-012 — Oscillator Evaluator — `osc_ma` — OHLC_ANYWHERE — **partial**
- **Default selector:** MA Crossover (short 3 / long 9). **Pyramiding:** 500. Cash 500 / capital 700.
- **Gap:** Laguerre MA → EMA proxy; other oscillator modes omitted.

### MIX-TV-EP-013 — Kelly + Keltner — `keltner_stop` — OHLC_ANYWHERE — **partial**
- **Entry:** close cross of EMA±ATR×1 (length 20, ATR 10). **Commission:** 0.1%. TP/SL inputs default off.
- **Gap:** Kelly qty omitted.

### MIX-TV-EP-014 — Ultimate Strategy Template — `ext_signal_sma` — TV_VIZ_TEMPLATE — **partial**
- **TV:** `ext_source == ±1`. Session `0000-2345`. Commission 0.075%, pyramid 3.
- **Gap:** close is never ±1 → SMA 14/28 stand-in.

### MIX-TV-EP-015 — SL/TP in $$ — `sma_sltp_money` — OHLC_ANYWHERE — **partial**
- **Entry:** SMA 14/28 cross. **Exit:** TP $200 / SL $100 via mintick.
- **Gap:** dollar stops need pointvalue.

### MIX-TV-EP-016 — Stepped trailing — `sma_step_trail` — OHLC_ANYWHERE — **partial**
- **Entry:** long-only SMA 14/28. **SL/TP:** 5/5/10/15%.
- **Gap:** staged trail omitted.

### MIX-TV-EP-017 — PMax Explorer — `pmax` — OHLC_ANYWHERE — **partial**
- **Entry:** EMA(hl2,10) cross PMax ATR(10)×3. Screener of 20 tickers.
- **Gap:** VAR/ZLEMA/TSF and multi-symbol screen omitted.

### MIX-TV-EP-018 — Grid Like — `grid_like` — CRYPTO_MARTINGALE — **partial**
- **Entry:** close breaks baseline ± `point` (default 2). **Qty:** martingale after loss. process_orders_on_close. Author: don’t trade.
- **Gap:** size pyramid ignored.

### MIX-TV-EP-019 — Gap Filling — `gap_fill` — OHLC_ANYWHERE — **ported core**
- **Entry:** fade (default) or invert session gap (`change(time("D"))`). Exit to gap fill or new session.
- **NSE:** cash gaps > OPTIDX 1m continuity.

### MIX-TV-EP-020 — inwCoin Martingale — `macd_martingale` — CRYPTO_MARTINGALE — **partial**
- **Entry:** long-only when MACD Fast>Slow (EMA of EMA2). TP 5%. Pyramid if −10%, mult 2. **Pyramiding:** 100. Commission 0%. Proof-of-ruin script.
- **Gap:** qty pyramid; theta kills option martingale.

### MIX-TV-EP-021 — LUBE — `lube_friction` — CRYPTO_MARTINGALE — **partial**
- **Entry:** low “friction” (price revisits) + FIR trend. Bars back 500. Overlay=false. BTC 30m. Leverage 2. Shorts optional.
- **Gap:** 24×7 crypto vs NSE session.

### MIX-TV-EP-022 — Backtest time ranges — `timed_sma` — OHLC_ANYWHERE — **partial**
- **Entry:** SMA 14/28 long. Session `0000-0000` = always. **Commission:** 0.27%. Pyramid 0. Capital 100000.
- **Gap:** date-range inputs not wired; long-only.

### MIX-TV-EP-023 — Grover Llorens Activator — `grover_llorens` — OHLC_ANYWHERE — **partial**
- **Entry:** SAR-like `diff` zero-cross, length=480, mult=14 (hardcoded in Pine). Overlay=false.
- **Gap:** 480-bar ATR is slow on 1m; grid exposes `length=20`.

---

Factory calibrators `MIX-TV-EP-024` `sma_cross` / `025` `macd_hist` are **not** Editors’ Pick cards.

# TV-EP paper leaderboard

**UNVALIDATED.** **NO_PROMOTE.** Not a TradingView Strategy Tester clone. Not customer `/`. Not `RESEARCH_READY_FOR_PROGRAMMING`. Live orders **refused**. INDEX points ≠ option P/L. `WATCH` is lab/fixture only.

- cells: 912 · MIX kept: 25
- WATCH: 223 · TESTED_FAIL: 419 · PARK: 270 · DATA_INSUFFICIENT: 0
- event calendar: DATA_INSUFFICIENT
- prefer_strike: None (unused unless OPTIDX universe exists)
- tapes: BANKNIFTY/INDEX, BANKNIFTY/PREMIUM, NIFTY/INDEX, NIFTY/PREMIUM, SENSEX/INDEX, SENSEX/PREMIUM

## KEEP_ALL MIX rows (never delete because FAIL / PARK / DI / n=0)

| MIX | name | side | cells | trades | buy_ce cells | buy_pe cells | status | tune hint |
|-----|------|------|-------|--------|--------------|--------------|--------|-----------|
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | PE | 96 | 3800 | 0 | 96 | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash commissi… |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | BOTH | 24 | 158 | 16 | 16 | TESTED_FAIL | TQQQ weekly session; 0.5% BE exit not in lean simulator |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | NONE | 24 | 0 | 0 | 0 | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | BOTH | 144 | 19109 | 144 | 144 | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD soup no… |
| `MIX-TV-EP-005` | Bjorgum Double Tap | BOTH | 48 | 11167 | 46 | 47 | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-006` | Traling.SL.Target | BOTH | 24 | 1329 | 23 | 23 | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | BOTH | 24 | 1619 | 24 | 24 | TESTED_FAIL | 222-input trailing template; internal SMA 21/49 only; … |
| `MIX-TV-EP-008` | 3Commas Bot | BOTH | 24 | 1293 | 23 | 23 | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR trail omit… |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | BOTH | 24 | 19193 | 24 | 24 | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineScript | BOTH | 24 | 11808 | 24 | 24 | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | BOTH | 24 | 2104 | 24 | 24 | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | BOTH | 24 | 7499 | 24 | 24 | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic position sizing | BOTH | 24 | 6325 | 24 | 24 | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-014` | Ultimate Strategy Template | BOTH | 24 | 2780 | 24 | 24 | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | BOTH | 24 | 2780 | 24 | 24 | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-016` | Stepped trailing strategy example | BOTH | 24 | 1456 | 24 | 11 | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | BOTH | 96 | 2 | 2 | 2 | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-018` | Grid Like Strategy | BOTH | 24 | 20478 | 24 | 24 | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-019` | Gap Filling Strategy | BOTH | 24 | 3 | 23 | 22 | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoin ) | BOTH | 24 | 136 | 24 | 12 | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV commission |
| `MIX-TV-EP-021` | LUBE | NONE | 24 | 0 | 0 | 0 | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | BOTH | 24 | 1456 | 24 | 11 | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% commission |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | BOTH | 48 | 3098 | 43 | 43 | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossover (not… | BOTH | 24 | 1917 | 23 | 24 | TESTED_FAIL | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogram zer… | BOTH | 24 | 5033 | 24 | 24 | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |

## TF × market cells that actually produced BUY_CE and BUY_PE

Fixture or cache simulation only. Empty matrix ⇒ no ported adapter fired both sides.

| tf | underlying | tape | BUY_CE | BUY_PE | MIX with CE | MIX with PE |
|----|------------|------|--------|--------|-------------|-------------|
| 15m | BANKNIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 15m | BANKNIFTY | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-007,MIX-TV-EP-009,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-007,MI… |
| 15m | NIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 15m | NIFTY | PREMIUM | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 15m | SENSEX | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 15m | SENSEX | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 1m | BANKNIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 1m | BANKNIFTY | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 1m | NIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 1m | NIFTY | PREMIUM | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 1m | SENSEX | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 1m | SENSEX | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 3m | BANKNIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 3m | BANKNIFTY | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 3m | NIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 3m | NIFTY | PREMIUM | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 3m | SENSEX | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 3m | SENSEX | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 5m | BANKNIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 5m | BANKNIFTY | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |
| 5m | NIFTY | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 5m | NIFTY | PREMIUM | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 5m | SENSEX | INDEX | yes | yes | MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… | MIX-TV-EP-001,MIX-TV-EP-002,MIX-TV-EP-004,MIX-TV-EP-005,MI… |
| 5m | SENSEX | PREMIUM | yes | yes | MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MIX-TV-EP-007,MI… | MIX-TV-EP-001,MIX-TV-EP-004,MIX-TV-EP-005,MIX-TV-EP-006,MI… |

## Grid cells (KEEP_ALL; status + reason only)

| MIX | name | tf | underlying | tape | side (CE/PE) | trades | after-cost note | status | tune hint |
|-----|------|----|------------|------|--------------|--------|-----------------|--------|-----------|
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | INDEX | PE | 7 | INDEX proxy gross 12.2500 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | INDEX | PE | 7 | INDEX proxy gross 157.7000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | INDEX | PE | 10 | INDEX proxy gross 41.3000 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | INDEX | PE | 7 | INDEX proxy gross 263.9500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | INDEX | PE | 171 | INDEX proxy gross 246.3000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | INDEX | PE | 135 | INDEX proxy gross 245.8000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | INDEX | PE | 170 | INDEX proxy gross 208.4000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | INDEX | PE | 139 | INDEX proxy gross 349.7000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | PREMIUM | PE | 18 | PREMIUM after-cost -267.0455 (1% RT HY… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | PREMIUM | PE | 11 | PREMIUM after-cost -113.1765 (1% RT HY… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | PREMIUM | PE | 18 | PREMIUM after-cost -147.0995 (1% RT HY… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | BANKNIFTY | PREMIUM | PE | 11 | PREMIUM after-cost -155.0860 (1% RT HY… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | INDEX | PE | 53 | INDEX proxy gross 252.3000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | INDEX | PE | 44 | INDEX proxy gross 161.8500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | INDEX | PE | 54 | INDEX proxy gross 300.8500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | INDEX | PE | 47 | INDEX proxy gross -180.1500 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | PREMIUM | PE | 3 | PREMIUM after-cost -37.6435 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | PREMIUM | PE | 1 | PREMIUM after-cost -17.9065 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | PREMIUM | PE | 4 | PREMIUM after-cost -37.9670 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | BANKNIFTY | PREMIUM | PE | 1 | PREMIUM after-cost -17.9065 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | INDEX | PE | 35 | INDEX proxy gross 234.3000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | INDEX | PE | 23 | INDEX proxy gross -462.9500 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | INDEX | PE | 35 | INDEX proxy gross -99.8000 (≠ option P… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | INDEX | PE | 27 | INDEX proxy gross -288.0500 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | PREMIUM | PE | 1 | PREMIUM after-cost -3.1160 (1% RT HYPO… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | PREMIUM | PE | 1 | PREMIUM after-cost -3.1160 (1% RT HYPO… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | BANKNIFTY | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | INDEX | PE | 9 | INDEX proxy gross 68.3000 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | INDEX | PE | 7 | INDEX proxy gross 125.2500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | INDEX | PE | 10 | INDEX proxy gross 82.9500 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | INDEX | PE | 7 | INDEX proxy gross -65.8000 (≠ option P… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | PREMIUM | PE | 7 | PREMIUM after-cost 10.5800 (1% RT HYPO… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | PREMIUM | PE | 7 | PREMIUM after-cost 6.1840 (1% RT HYPOT… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | PREMIUM | PE | 7 | PREMIUM after-cost 6.5960 (1% RT HYPOT… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | NIFTY | PREMIUM | PE | 7 | PREMIUM after-cost 6.8370 (1% RT HYPOT… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | INDEX | PE | 179 | INDEX proxy gross 184.0000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | INDEX | PE | 147 | INDEX proxy gross 173.5500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | INDEX | PE | 175 | INDEX proxy gross 168.2500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | INDEX | PE | 145 | INDEX proxy gross 154.3000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | PREMIUM | PE | 114 | PREMIUM after-cost -92.1390 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | PREMIUM | PE | 106 | PREMIUM after-cost -81.1820 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | PREMIUM | PE | 115 | PREMIUM after-cost -88.9225 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | NIFTY | PREMIUM | PE | 103 | PREMIUM after-cost -81.5015 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | INDEX | PE | 58 | INDEX proxy gross 72.0000 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | INDEX | PE | 48 | INDEX proxy gross 94.4000 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | INDEX | PE | 57 | INDEX proxy gross 77.4000 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | INDEX | PE | 47 | INDEX proxy gross 168.0000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | PREMIUM | PE | 35 | PREMIUM after-cost -19.2685 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | PREMIUM | PE | 32 | PREMIUM after-cost -7.8185 (1% RT HYPO… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | PREMIUM | PE | 35 | PREMIUM after-cost -18.3980 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | NIFTY | PREMIUM | PE | 33 | PREMIUM after-cost -5.3545 (1% RT HYPO… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | INDEX | PE | 37 | INDEX proxy gross 52.7500 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | INDEX | PE | 26 | INDEX proxy gross -15.5000 (≠ option P… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | INDEX | PE | 38 | INDEX proxy gross -119.5000 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | INDEX | PE | 28 | INDEX proxy gross -104.8000 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | PREMIUM | PE | 20 | PREMIUM after-cost -20.2050 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | PREMIUM | PE | 16 | PREMIUM after-cost -23.4320 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | PREMIUM | PE | 21 | PREMIUM after-cost -11.0305 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | NIFTY | PREMIUM | PE | 19 | PREMIUM after-cost -16.3160 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | INDEX | PE | 8 | INDEX proxy gross 334.3400 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | INDEX | PE | 5 | INDEX proxy gross 182.3800 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | INDEX | PE | 9 | INDEX proxy gross -19.2800 (≠ option P… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | INDEX | PE | 9 | INDEX proxy gross 37.1900 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 15m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | INDEX | PE | 175 | INDEX proxy gross 585.1700 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | INDEX | PE | 145 | INDEX proxy gross 391.2200 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | INDEX | PE | 172 | INDEX proxy gross 75.7500 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | INDEX | PE | 145 | INDEX proxy gross 281.6800 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | PREMIUM | PE | 21 | PREMIUM after-cost -96.4040 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | PREMIUM | PE | 10 | PREMIUM after-cost -45.4285 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | PREMIUM | PE | 18 | PREMIUM after-cost -88.9775 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 1m | SENSEX | PREMIUM | PE | 10 | PREMIUM after-cost -51.8385 (1% RT HYP… | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | INDEX | PE | 57 | INDEX proxy gross 547.5200 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | INDEX | PE | 45 | INDEX proxy gross 507.1800 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | INDEX | PE | 55 | INDEX proxy gross 291.9000 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | INDEX | PE | 46 | INDEX proxy gross 562.7500 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | PREMIUM | PE | 3 | PREMIUM after-cost -29.6150 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | PREMIUM | PE | 3 | PREMIUM after-cost -23.3640 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | PREMIUM | PE | 3 | PREMIUM after-cost -29.6150 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 3m | SENSEX | PREMIUM | PE | 3 | PREMIUM after-cost -29.8580 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | INDEX | PE | 34 | INDEX proxy gross 229.0100 (≠ option P… | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | INDEX | PE | 26 | INDEX proxy gross 99.0100 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | INDEX | PE | 38 | INDEX proxy gross -140.3500 (≠ option … | TESTED_FAIL | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | INDEX | PE | 27 | INDEX proxy gross 26.9200 (≠ option P/L) | WATCH | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | PREMIUM | PE | 3 | PREMIUM after-cost -88.6280 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | PREMIUM | PE | 2 | PREMIUM after-cost -14.3085 (1% RT HYP… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-001` | TASC 2026.08 An Ag Selling Model | 5m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | commodity harvest calendar; pyramiding=3 cash … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | BANKNIFTY | INDEX | BOTH | 2 | INDEX proxy gross 128.7000 (≠ option P… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | BANKNIFTY | INDEX | BOTH | 2 | INDEX proxy gross 5.7500 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | BANKNIFTY | INDEX | BOTH | 2 | INDEX proxy gross -69.2000 (≠ option P… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | BANKNIFTY | INDEX | BOTH | 2 | INDEX proxy gross 15.4000 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | NIFTY | INDEX | BOTH | 3 | INDEX proxy gross 14.1000 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | NIFTY | PREMIUM | BOTH | 22 | PREMIUM after-cost 1.8000 (1% RT HYPOT… | WATCH | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | NIFTY | INDEX | BOTH | 3 | INDEX proxy gross 15.8500 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | NIFTY | PREMIUM | BOTH | 40 | PREMIUM after-cost -13.7640 (1% RT HYP… | TESTED_FAIL | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | NIFTY | INDEX | BOTH | 3 | INDEX proxy gross 10.4500 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | NIFTY | PREMIUM | BOTH | 33 | PREMIUM after-cost -16.3140 (1% RT HYP… | TESTED_FAIL | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | NIFTY | INDEX | BOTH | 3 | INDEX proxy gross -1.1500 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | NIFTY | PREMIUM | BOTH | 31 | PREMIUM after-cost 0.5110 (1% RT HYPOT… | WATCH | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | SENSEX | INDEX | BOTH | 3 | INDEX proxy gross 49.2300 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | SENSEX | INDEX | BOTH | 3 | INDEX proxy gross 39.5400 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | SENSEX | INDEX | BOTH | 3 | INDEX proxy gross 20.9600 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | SENSEX | INDEX | BOTH | 3 | INDEX proxy gross 7.0400 (≠ option P/L) | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-002` | TASC 2026.03 One Percent A Week | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | TQQQ weekly session; 0.5% BE exit not in lean … |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-003` | Trading Report Generator from CSV | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | needs Transactions CSV; no OHLC alpha |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 35 | INDEX proxy gross 408.8000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 18 | INDEX proxy gross 346.7000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 34 | INDEX proxy gross -19.3000 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 19 | INDEX proxy gross -232.5000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 36 | INDEX proxy gross -877.6500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | INDEX | BOTH | 18 | INDEX proxy gross 366.9500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 9 | PREMIUM after-cost -59.3245 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 2 | PREMIUM after-cost -7.5610 (1% RT HYPO… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 11 | PREMIUM after-cost -61.1260 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 2 | PREMIUM after-cost -7.5610 (1% RT HYPO… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 9 | PREMIUM after-cost -86.9090 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | BANKNIFTY | PREMIUM | BOTH | 3 | PREMIUM after-cost -28.9990 (1% RT HYP… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 589 | INDEX proxy gross 181.5000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 425 | INDEX proxy gross -77.9000 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 583 | INDEX proxy gross 228.1000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 405 | INDEX proxy gross -290.7000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 595 | INDEX proxy gross 624.8500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | INDEX | BOTH | 379 | INDEX proxy gross -803.9500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 134 | PREMIUM after-cost -1181.2015 (1% RT H… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 119 | PREMIUM after-cost -1094.8030 (1% RT H… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 137 | PREMIUM after-cost -1259.8500 (1% RT H… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 109 | PREMIUM after-cost -823.1845 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 131 | PREMIUM after-cost -1376.8935 (1% RT H… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | BANKNIFTY | PREMIUM | BOTH | 91 | PREMIUM after-cost -539.3410 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 213 | INDEX proxy gross -562.8500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 149 | INDEX proxy gross -178.8000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 219 | INDEX proxy gross -816.8000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 141 | INDEX proxy gross -203.5000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 216 | INDEX proxy gross 501.7000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | INDEX | BOTH | 131 | INDEX proxy gross 60.4500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 42 | PREMIUM after-cost -437.1755 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 28 | PREMIUM after-cost -325.6800 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 42 | PREMIUM after-cost -401.7180 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 23 | PREMIUM after-cost -70.2190 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 48 | PREMIUM after-cost -418.5495 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | BANKNIFTY | PREMIUM | BOTH | 20 | PREMIUM after-cost -240.1650 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 126 | INDEX proxy gross -144.9000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 76 | INDEX proxy gross -722.3500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 123 | INDEX proxy gross -12.6500 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 69 | INDEX proxy gross -266.9000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 130 | INDEX proxy gross -34.3500 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | INDEX | BOTH | 65 | INDEX proxy gross 56.6000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 23 | PREMIUM after-cost -333.5305 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 12 | PREMIUM after-cost -58.2220 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 22 | PREMIUM after-cost -244.9185 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -31.1705 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 18 | PREMIUM after-cost -63.4655 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -139.0040 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 29 | INDEX proxy gross 106.6000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 20 | INDEX proxy gross 53.8000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 28 | INDEX proxy gross -209.3000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 20 | INDEX proxy gross 82.4500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 27 | INDEX proxy gross 29.0000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | INDEX | BOTH | 21 | INDEX proxy gross 60.1500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 22 | PREMIUM after-cost -12.0110 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -8.4035 (1% RT HYPO… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 21 | PREMIUM after-cost -9.6305 (1% RT HYPO… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 11 | PREMIUM after-cost -6.1655 (1% RT HYPO… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 20 | PREMIUM after-cost -16.1815 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | NIFTY | PREMIUM | BOTH | 6 | PREMIUM after-cost -1.6285 (1% RT HYPO… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 582 | INDEX proxy gross 70.6500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 441 | INDEX proxy gross 43.3500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 566 | INDEX proxy gross -69.9500 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 423 | INDEX proxy gross 67.0000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 595 | INDEX proxy gross 55.3000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | INDEX | BOTH | 388 | INDEX proxy gross 120.1500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 340 | PREMIUM after-cost -253.6980 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 222 | PREMIUM after-cost -158.1865 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 331 | PREMIUM after-cost -252.0105 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 218 | PREMIUM after-cost -201.3435 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 352 | PREMIUM after-cost -257.8855 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | NIFTY | PREMIUM | BOTH | 212 | PREMIUM after-cost -169.8895 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 201 | INDEX proxy gross -336.1500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 143 | INDEX proxy gross 147.1500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 194 | INDEX proxy gross -234.5000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 140 | INDEX proxy gross 55.9000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 202 | INDEX proxy gross 129.7000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | INDEX | BOTH | 134 | INDEX proxy gross -20.9500 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 109 | PREMIUM after-cost -81.6660 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 73 | PREMIUM after-cost -63.6295 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 106 | PREMIUM after-cost -79.6430 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 73 | PREMIUM after-cost -54.6900 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 112 | PREMIUM after-cost -95.3405 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | NIFTY | PREMIUM | BOTH | 67 | PREMIUM after-cost -32.0530 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 120 | INDEX proxy gross 100.0500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 81 | INDEX proxy gross -21.3000 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 120 | INDEX proxy gross 7.7500 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 80 | INDEX proxy gross 40.1000 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 117 | INDEX proxy gross -258.0000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | INDEX | BOTH | 76 | INDEX proxy gross -40.5500 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 65 | PREMIUM after-cost -67.0320 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 42 | PREMIUM after-cost -24.3725 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 66 | PREMIUM after-cost -69.0295 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 39 | PREMIUM after-cost -23.1535 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 60 | PREMIUM after-cost -64.9180 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | NIFTY | PREMIUM | BOTH | 40 | PREMIUM after-cost -14.6465 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 36 | INDEX proxy gross 741.8300 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 20 | INDEX proxy gross 259.3900 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 35 | INDEX proxy gross 21.2900 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 21 | INDEX proxy gross 445.1500 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 33 | INDEX proxy gross -537.4000 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | INDEX | BOTH | 22 | INDEX proxy gross 437.8800 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost 102.6385 (1% RT HYP… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 1 | PREMIUM after-cost 24.1995 (1% RT HYPO… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost 113.4870 (1% RT HYP… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 1 | PREMIUM after-cost 24.1995 (1% RT HYPO… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 3 | PREMIUM after-cost 202.8905 (1% RT HYP… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost -41.9580 (1% RT HYP… | PARK | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 615 | INDEX proxy gross -900.2700 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 440 | INDEX proxy gross -229.0200 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 599 | INDEX proxy gross -228.5800 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 416 | INDEX proxy gross -232.1500 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 603 | INDEX proxy gross 385.2700 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | INDEX | BOTH | 376 | INDEX proxy gross -452.1800 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 137 | PREMIUM after-cost -734.2725 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 109 | PREMIUM after-cost -482.9895 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 134 | PREMIUM after-cost -685.5320 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 104 | PREMIUM after-cost -530.2630 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 141 | PREMIUM after-cost -1056.2475 (1% RT H… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 1m | SENSEX | PREMIUM | BOTH | 93 | PREMIUM after-cost -658.6850 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 210 | INDEX proxy gross -262.1100 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 138 | INDEX proxy gross -514.5400 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 205 | INDEX proxy gross 275.3300 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 132 | INDEX proxy gross -401.9900 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 200 | INDEX proxy gross 158.0300 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | INDEX | BOTH | 126 | INDEX proxy gross -71.6100 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 39 | PREMIUM after-cost -194.7280 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 29 | PREMIUM after-cost -130.5435 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 35 | PREMIUM after-cost -58.0580 (1% RT HYP… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 26 | PREMIUM after-cost -192.8335 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 49 | PREMIUM after-cost -126.8480 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 3m | SENSEX | PREMIUM | BOTH | 26 | PREMIUM after-cost -351.9605 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 124 | INDEX proxy gross -11.6600 (≠ option P… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 74 | INDEX proxy gross 150.1000 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 122 | INDEX proxy gross -470.2800 (≠ option … | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 76 | INDEX proxy gross 686.6100 (≠ option P… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 123 | INDEX proxy gross 83.2800 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | INDEX | BOTH | 69 | INDEX proxy gross 55.6200 (≠ option P/L) | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 24 | PREMIUM after-cost -108.2570 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 24 | PREMIUM after-cost -149.9420 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 27 | PREMIUM after-cost -410.0735 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 23 | PREMIUM after-cost -103.6385 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 29 | PREMIUM after-cost -112.5585 (1% RT HY… | TESTED_FAIL | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-004` | TrendMaster Pro 2.3 with Alerts | 5m | SENSEX | PREMIUM | BOTH | 20 | PREMIUM after-cost 153.8925 (1% RT HYP… | WATCH | FX Asia/London/NY session boxes + S/R/RSI/MACD… |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | BANKNIFTY | INDEX | BOTH | 63 | INDEX proxy gross 1143.7000 (≠ option … | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | BANKNIFTY | INDEX | BOTH | 30 | INDEX proxy gross 395.7500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | BANKNIFTY | PREMIUM | BOTH | 4 | PREMIUM after-cost -31.1295 (1% RT HYP… | PARK | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | BANKNIFTY | PREMIUM | PE | 2 | PREMIUM after-cost 119.5905 (1% RT HYP… | PARK | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | BANKNIFTY | INDEX | BOTH | 1192 | INDEX proxy gross 982.2500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | BANKNIFTY | INDEX | BOTH | 642 | INDEX proxy gross 417.8500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | BANKNIFTY | PREMIUM | BOTH | 125 | PREMIUM after-cost -1524.1715 (1% RT H… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | BANKNIFTY | PREMIUM | BOTH | 59 | PREMIUM after-cost -872.7830 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | BANKNIFTY | INDEX | BOTH | 389 | INDEX proxy gross 1445.9500 (≠ option … | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | BANKNIFTY | INDEX | BOTH | 194 | INDEX proxy gross 864.0500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | BANKNIFTY | PREMIUM | BOTH | 46 | PREMIUM after-cost -382.1015 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | BANKNIFTY | PREMIUM | BOTH | 18 | PREMIUM after-cost -135.3540 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | BANKNIFTY | INDEX | BOTH | 215 | INDEX proxy gross -72.5500 (≠ option P… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | BANKNIFTY | INDEX | BOTH | 104 | INDEX proxy gross -192.8500 (≠ option … | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | BANKNIFTY | PREMIUM | BOTH | 29 | PREMIUM after-cost -209.8265 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | BANKNIFTY | PREMIUM | BOTH | 7 | PREMIUM after-cost 30.6945 (1% RT HYPO… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | NIFTY | INDEX | BOTH | 69 | INDEX proxy gross 237.9000 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | NIFTY | INDEX | BOTH | 42 | INDEX proxy gross -41.3000 (≠ option P… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | NIFTY | PREMIUM | BOTH | 40 | PREMIUM after-cost -65.5530 (1% RT HYP… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | NIFTY | PREMIUM | BOTH | 20 | PREMIUM after-cost -66.0810 (1% RT HYP… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | NIFTY | INDEX | BOTH | 1240 | INDEX proxy gross 316.0000 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | NIFTY | INDEX | BOTH | 708 | INDEX proxy gross 254.7500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | NIFTY | PREMIUM | BOTH | 604 | PREMIUM after-cost -462.5475 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | NIFTY | PREMIUM | BOTH | 358 | PREMIUM after-cost -266.1655 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | NIFTY | INDEX | BOTH | 406 | INDEX proxy gross 276.8000 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | NIFTY | INDEX | BOTH | 224 | INDEX proxy gross 153.0500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | NIFTY | PREMIUM | BOTH | 219 | PREMIUM after-cost -184.2485 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | NIFTY | PREMIUM | BOTH | 121 | PREMIUM after-cost -93.9990 (1% RT HYP… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | NIFTY | INDEX | BOTH | 238 | INDEX proxy gross 330.8500 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | NIFTY | INDEX | BOTH | 125 | INDEX proxy gross 310.7000 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | NIFTY | PREMIUM | BOTH | 137 | PREMIUM after-cost -104.2545 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | NIFTY | PREMIUM | BOTH | 66 | PREMIUM after-cost -55.3775 (1% RT HYP… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | SENSEX | INDEX | BOTH | 74 | INDEX proxy gross 265.6600 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | SENSEX | INDEX | BOTH | 41 | INDEX proxy gross -218.1400 (≠ option … | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | SENSEX | PREMIUM | BOTH | 8 | PREMIUM after-cost -105.2045 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | SENSEX | INDEX | BOTH | 1230 | INDEX proxy gross 1416.1100 (≠ option … | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | SENSEX | INDEX | BOTH | 732 | INDEX proxy gross 941.1400 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | SENSEX | PREMIUM | BOTH | 130 | PREMIUM after-cost -885.1930 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 1m | SENSEX | PREMIUM | BOTH | 66 | PREMIUM after-cost -485.4975 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | SENSEX | INDEX | BOTH | 432 | INDEX proxy gross 1236.7900 (≠ option … | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | SENSEX | INDEX | BOTH | 236 | INDEX proxy gross 442.4100 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | SENSEX | PREMIUM | BOTH | 49 | PREMIUM after-cost -30.4375 (1% RT HYP… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 3m | SENSEX | PREMIUM | BOTH | 21 | PREMIUM after-cost 202.7040 (1% RT HYP… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | SENSEX | INDEX | BOTH | 241 | INDEX proxy gross 297.6800 (≠ option P… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | SENSEX | INDEX | BOTH | 124 | INDEX proxy gross 16.3100 (≠ option P/L) | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | SENSEX | PREMIUM | BOTH | 34 | PREMIUM after-cost -138.6370 (1% RT HY… | TESTED_FAIL | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-005` | Bjorgum Double Tap | 5m | SENSEX | PREMIUM | BOTH | 13 | PREMIUM after-cost 219.8210 (1% RT HYP… | WATCH | Fib target/stop + 3Commas alerts omitted |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | BANKNIFTY | INDEX | BOTH | 22 | INDEX proxy gross -157.3500 (≠ option … | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | BANKNIFTY | INDEX | BOTH | 231 | INDEX proxy gross 182.2500 (≠ option P… | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | BANKNIFTY | PREMIUM | BOTH | 73 | PREMIUM after-cost -483.1585 (1% RT HY… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | BANKNIFTY | INDEX | BOTH | 64 | INDEX proxy gross 83.9000 (≠ option P/L) | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | BANKNIFTY | PREMIUM | BOTH | 11 | PREMIUM after-cost -86.7480 (1% RT HYP… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | BANKNIFTY | INDEX | BOTH | 30 | INDEX proxy gross -44.4000 (≠ option P… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | BANKNIFTY | PREMIUM | BOTH | 12 | PREMIUM after-cost -1.2295 (1% RT HYPO… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | NIFTY | INDEX | BOTH | 12 | INDEX proxy gross -50.9000 (≠ option P… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | NIFTY | PREMIUM | BOTH | 5 | PREMIUM after-cost -2.9780 (1% RT HYPO… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | NIFTY | INDEX | BOTH | 220 | INDEX proxy gross -85.3500 (≠ option P… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | NIFTY | PREMIUM | BOTH | 108 | PREMIUM after-cost -83.2300 (1% RT HYP… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | NIFTY | INDEX | BOTH | 53 | INDEX proxy gross 80.0000 (≠ option P/L) | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | NIFTY | PREMIUM | BOTH | 37 | PREMIUM after-cost -17.4045 (1% RT HYP… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | NIFTY | INDEX | BOTH | 31 | INDEX proxy gross 9.7000 (≠ option P/L) | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | NIFTY | PREMIUM | BOTH | 18 | PREMIUM after-cost -7.8955 (1% RT HYPO… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | SENSEX | INDEX | BOTH | 12 | INDEX proxy gross 308.2900 (≠ option P… | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost -54.8175 (1% RT HYP… | PARK | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | SENSEX | INDEX | BOTH | 220 | INDEX proxy gross 519.3600 (≠ option P… | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 1m | SENSEX | PREMIUM | BOTH | 70 | PREMIUM after-cost 29.6315 (1% RT HYPO… | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | SENSEX | INDEX | BOTH | 59 | INDEX proxy gross 180.3500 (≠ option P… | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 3m | SENSEX | PREMIUM | BOTH | 11 | PREMIUM after-cost -3.9200 (1% RT HYPO… | TESTED_FAIL | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | SENSEX | INDEX | BOTH | 25 | INDEX proxy gross 82.3900 (≠ option P/L) | WATCH | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-006` | Traling.SL.Target | 5m | SENSEX | PREMIUM | BOTH | 3 | PREMIUM after-cost 41.8910 (1% RT HYPO… | PARK | percent trailing SL/target is TV close engine |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | BANKNIFTY | INDEX | BOTH | 17 | INDEX proxy gross -297.0500 (≠ option … | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | BANKNIFTY | PREMIUM | BOTH | 1 | PREMIUM after-cost -25.2160 (1% RT HYP… | PARK | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | BANKNIFTY | INDEX | BOTH | 267 | INDEX proxy gross 81.6500 (≠ option P/L) | WATCH | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | BANKNIFTY | PREMIUM | BOTH | 60 | PREMIUM after-cost -622.5705 (1% RT HY… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | BANKNIFTY | INDEX | BOTH | 75 | INDEX proxy gross -182.3000 (≠ option … | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | BANKNIFTY | PREMIUM | BOTH | 9 | PREMIUM after-cost -200.9430 (1% RT HY… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | BANKNIFTY | INDEX | BOTH | 47 | INDEX proxy gross -51.6500 (≠ option P… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | BANKNIFTY | PREMIUM | BOTH | 9 | PREMIUM after-cost -64.2610 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | NIFTY | INDEX | BOTH | 13 | INDEX proxy gross 17.6500 (≠ option P/L) | WATCH | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | NIFTY | PREMIUM | BOTH | 6 | PREMIUM after-cost -5.7860 (1% RT HYPO… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | NIFTY | INDEX | BOTH | 279 | INDEX proxy gross -69.9500 (≠ option P… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | NIFTY | PREMIUM | BOTH | 132 | PREMIUM after-cost -101.5015 (1% RT HY… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | NIFTY | INDEX | BOTH | 84 | INDEX proxy gross -47.3000 (≠ option P… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | NIFTY | PREMIUM | BOTH | 47 | PREMIUM after-cost -38.1800 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | NIFTY | INDEX | BOTH | 44 | INDEX proxy gross -49.5500 (≠ option P… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | NIFTY | PREMIUM | BOTH | 30 | PREMIUM after-cost -16.3430 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | SENSEX | INDEX | BOTH | 18 | INDEX proxy gross 109.3900 (≠ option P… | WATCH | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost 31.2325 (1% RT HYPO… | PARK | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | SENSEX | INDEX | BOTH | 268 | INDEX proxy gross -226.1900 (≠ option … | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 1m | SENSEX | PREMIUM | BOTH | 59 | PREMIUM after-cost -61.7500 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | SENSEX | INDEX | BOTH | 77 | INDEX proxy gross -535.6500 (≠ option … | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 3m | SENSEX | PREMIUM | BOTH | 23 | PREMIUM after-cost -68.0960 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | SENSEX | INDEX | BOTH | 46 | INDEX proxy gross 499.2800 (≠ option P… | WATCH | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-007` | Template Trailing Strategy (Backtester) | 5m | SENSEX | PREMIUM | BOTH | 6 | PREMIUM after-cost -79.9355 (1% RT HYP… | TESTED_FAIL | 222-input trailing template; internal SMA 21/4… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | BANKNIFTY | INDEX | BOTH | 21 | INDEX proxy gross -74.3500 (≠ option P… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | BANKNIFTY | INDEX | BOTH | 222 | INDEX proxy gross 219.5000 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | BANKNIFTY | PREMIUM | BOTH | 69 | PREMIUM after-cost -441.0870 (1% RT HY… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | BANKNIFTY | INDEX | BOTH | 61 | INDEX proxy gross 45.6500 (≠ option P/L) | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | BANKNIFTY | PREMIUM | BOTH | 11 | PREMIUM after-cost -86.7480 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | BANKNIFTY | INDEX | BOTH | 27 | INDEX proxy gross 122.1500 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -33.8020 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | NIFTY | INDEX | BOTH | 11 | INDEX proxy gross 21.4500 (≠ option P/L) | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | NIFTY | PREMIUM | BOTH | 6 | PREMIUM after-cost -0.1155 (1% RT HYPO… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | NIFTY | INDEX | BOTH | 216 | INDEX proxy gross -59.4000 (≠ option P… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | NIFTY | PREMIUM | BOTH | 106 | PREMIUM after-cost -95.3885 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | NIFTY | INDEX | BOTH | 53 | INDEX proxy gross 106.2500 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | NIFTY | PREMIUM | BOTH | 36 | PREMIUM after-cost -23.3485 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | NIFTY | INDEX | BOTH | 30 | INDEX proxy gross -67.8500 (≠ option P… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | NIFTY | PREMIUM | BOTH | 18 | PREMIUM after-cost -22.5105 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | SENSEX | INDEX | BOTH | 12 | INDEX proxy gross 183.9100 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost -16.3750 (1% RT HYP… | PARK | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | SENSEX | INDEX | BOTH | 220 | INDEX proxy gross 109.1400 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 1m | SENSEX | PREMIUM | BOTH | 66 | PREMIUM after-cost -33.5075 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | SENSEX | INDEX | BOTH | 56 | INDEX proxy gross -21.1800 (≠ option P… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 3m | SENSEX | PREMIUM | BOTH | 11 | PREMIUM after-cost -57.9585 (1% RT HYP… | TESTED_FAIL | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | SENSEX | INDEX | BOTH | 26 | INDEX proxy gross 147.7700 (≠ option P… | WATCH | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-008` | 3Commas Bot | 5m | SENSEX | PREMIUM | BOTH | 3 | PREMIUM after-cost 41.8910 (1% RT HYPO… | PARK | 3Commas webhook/JSON; 0.05% commission; ATR tr… |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | BANKNIFTY | INDEX | BOTH | 209 | INDEX proxy gross 476.7500 (≠ option P… | WATCH | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | BANKNIFTY | PREMIUM | BOTH | 28 | PREMIUM after-cost -304.2600 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | BANKNIFTY | INDEX | BOTH | 3151 | INDEX proxy gross -2908.0000 (≠ option… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | BANKNIFTY | PREMIUM | BOTH | 446 | PREMIUM after-cost -4596.6455 (1% RT H… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | BANKNIFTY | INDEX | BOTH | 1105 | INDEX proxy gross -2046.9500 (≠ option… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | BANKNIFTY | PREMIUM | BOTH | 160 | PREMIUM after-cost -1624.1390 (1% RT H… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | BANKNIFTY | INDEX | BOTH | 638 | INDEX proxy gross 467.7000 (≠ option P… | WATCH | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | BANKNIFTY | PREMIUM | BOTH | 93 | PREMIUM after-cost -800.3175 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | NIFTY | INDEX | BOTH | 207 | INDEX proxy gross 284.6000 (≠ option P… | WATCH | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | NIFTY | PREMIUM | BOTH | 114 | PREMIUM after-cost -52.0270 (1% RT HYP… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | NIFTY | INDEX | BOTH | 3137 | INDEX proxy gross -1002.2000 (≠ option… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | NIFTY | PREMIUM | BOTH | 1479 | PREMIUM after-cost -1171.8355 (1% RT H… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | NIFTY | INDEX | BOTH | 1067 | INDEX proxy gross -674.1500 (≠ option … | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | NIFTY | PREMIUM | BOTH | 577 | PREMIUM after-cost -393.7520 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | NIFTY | INDEX | BOTH | 631 | INDEX proxy gross -69.2000 (≠ option P… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | NIFTY | PREMIUM | BOTH | 354 | PREMIUM after-cost -210.4525 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | SENSEX | INDEX | BOTH | 211 | INDEX proxy gross -363.6600 (≠ option … | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 15m | SENSEX | PREMIUM | BOTH | 30 | PREMIUM after-cost -284.7085 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | SENSEX | INDEX | BOTH | 3145 | INDEX proxy gross -1573.9600 (≠ option… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 1m | SENSEX | PREMIUM | BOTH | 469 | PREMIUM after-cost -2228.2095 (1% RT H… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | SENSEX | INDEX | BOTH | 1076 | INDEX proxy gross -933.6700 (≠ option … | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 3m | SENSEX | PREMIUM | BOTH | 145 | PREMIUM after-cost -969.3195 (1% RT HY… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | SENSEX | INDEX | BOTH | 623 | INDEX proxy gross 473.0800 (≠ option P… | WATCH | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-009` | Monthly Returns in PineScript Strategies | 5m | SENSEX | PREMIUM | BOTH | 98 | PREMIUM after-cost -76.2110 (1% RT HYP… | TESTED_FAIL | monthly returns table is viz; 0.1% commission |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | BANKNIFTY | INDEX | BOTH | 120 | INDEX proxy gross -225.7500 (≠ option … | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | BANKNIFTY | PREMIUM | BOTH | 17 | PREMIUM after-cost -308.2725 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | BANKNIFTY | INDEX | BOTH | 1920 | INDEX proxy gross 1824.8000 (≠ option … | WATCH | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | BANKNIFTY | PREMIUM | BOTH | 332 | PREMIUM after-cost -3148.6745 (1% RT H… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | BANKNIFTY | INDEX | BOTH | 631 | INDEX proxy gross -737.6500 (≠ option … | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | BANKNIFTY | PREMIUM | BOTH | 120 | PREMIUM after-cost -779.1875 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | BANKNIFTY | INDEX | BOTH | 359 | INDEX proxy gross 1126.2000 (≠ option … | WATCH | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | BANKNIFTY | PREMIUM | BOTH | 76 | PREMIUM after-cost -408.4115 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | NIFTY | INDEX | BOTH | 123 | INDEX proxy gross -556.5000 (≠ option … | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | NIFTY | PREMIUM | BOTH | 67 | PREMIUM after-cost -9.2410 (1% RT HYPO… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | NIFTY | INDEX | BOTH | 1890 | INDEX proxy gross 799.0500 (≠ option P… | WATCH | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | NIFTY | PREMIUM | BOTH | 934 | PREMIUM after-cost -635.8570 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | NIFTY | INDEX | BOTH | 632 | INDEX proxy gross -465.6000 (≠ option … | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | NIFTY | PREMIUM | BOTH | 355 | PREMIUM after-cost -333.4800 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | NIFTY | INDEX | BOTH | 395 | INDEX proxy gross 128.4000 (≠ option P… | WATCH | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | NIFTY | PREMIUM | BOTH | 213 | PREMIUM after-cost -153.9950 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | SENSEX | INDEX | BOTH | 128 | INDEX proxy gross -1084.5900 (≠ option… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 15m | SENSEX | PREMIUM | BOTH | 18 | PREMIUM after-cost -122.3170 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | SENSEX | INDEX | BOTH | 1929 | INDEX proxy gross -2115.7100 (≠ option… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 1m | SENSEX | PREMIUM | BOTH | 330 | PREMIUM after-cost -2412.0225 (1% RT H… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | SENSEX | INDEX | BOTH | 642 | INDEX proxy gross -814.6600 (≠ option … | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 3m | SENSEX | PREMIUM | BOTH | 131 | PREMIUM after-cost -784.2365 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | SENSEX | INDEX | BOTH | 376 | INDEX proxy gross 57.7600 (≠ option P/L) | WATCH | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-010` | How to use Leverage and Margin in PineSc… | 5m | SENSEX | PREMIUM | BOTH | 70 | PREMIUM after-cost -297.9195 (1% RT HY… | TESTED_FAIL | pyramiding=100 / 30x margin TV-only |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | BANKNIFTY | INDEX | BOTH | 20 | INDEX proxy gross -187.6500 (≠ option … | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | BANKNIFTY | PREMIUM | BOTH | 3 | PREMIUM after-cost -65.7100 (1% RT HYP… | PARK | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | BANKNIFTY | INDEX | BOTH | 346 | INDEX proxy gross 1140.5000 (≠ option … | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | BANKNIFTY | PREMIUM | BOTH | 46 | PREMIUM after-cost -603.4950 (1% RT HY… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | BANKNIFTY | INDEX | BOTH | 115 | INDEX proxy gross -5.0000 (≠ option P/L) | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | BANKNIFTY | PREMIUM | BOTH | 16 | PREMIUM after-cost -265.0540 (1% RT HY… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | BANKNIFTY | INDEX | BOTH | 69 | INDEX proxy gross -56.7500 (≠ option P… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -60.2620 (1% RT HYP… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | NIFTY | INDEX | BOTH | 20 | INDEX proxy gross -59.7500 (≠ option P… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | NIFTY | PREMIUM | BOTH | 13 | PREMIUM after-cost 17.3980 (1% RT HYPO… | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | NIFTY | INDEX | BOTH | 346 | INDEX proxy gross 200.4500 (≠ option P… | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | NIFTY | PREMIUM | BOTH | 191 | PREMIUM after-cost -128.1925 (1% RT HY… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | NIFTY | INDEX | BOTH | 115 | INDEX proxy gross 46.2000 (≠ option P/L) | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | NIFTY | PREMIUM | BOTH | 64 | PREMIUM after-cost -62.3670 (1% RT HYP… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | NIFTY | INDEX | BOTH | 69 | INDEX proxy gross -2.2500 (≠ option P/L) | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | NIFTY | PREMIUM | BOTH | 36 | PREMIUM after-cost -28.4740 (1% RT HYP… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | SENSEX | INDEX | BOTH | 20 | INDEX proxy gross -0.9400 (≠ option P/L) | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 15m | SENSEX | PREMIUM | BOTH | 3 | PREMIUM after-cost -0.6445 (1% RT HYPO… | PARK | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | SENSEX | INDEX | BOTH | 346 | INDEX proxy gross 335.0700 (≠ option P… | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 1m | SENSEX | PREMIUM | BOTH | 46 | PREMIUM after-cost -367.5040 (1% RT HY… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | SENSEX | INDEX | BOTH | 115 | INDEX proxy gross 209.3400 (≠ option P… | WATCH | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 3m | SENSEX | PREMIUM | BOTH | 16 | PREMIUM after-cost -22.2035 (1% RT HYP… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | SENSEX | INDEX | BOTH | 69 | INDEX proxy gross -441.7100 (≠ option … | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-011` | Сalculation a position size based on risk | 5m | SENSEX | PREMIUM | BOTH | 10 | PREMIUM after-cost -51.5545 (1% RT HYP… | TESTED_FAIL | random bar_index demo; risk qty not a lean |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | BANKNIFTY | INDEX | BOTH | 75 | INDEX proxy gross -221.2000 (≠ option … | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | BANKNIFTY | PREMIUM | BOTH | 19 | PREMIUM after-cost 88.3765 (1% RT HYPO… | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | BANKNIFTY | INDEX | BOTH | 1171 | INDEX proxy gross 219.8500 (≠ option P… | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | BANKNIFTY | PREMIUM | BOTH | 285 | PREMIUM after-cost -2567.5635 (1% RT H… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | BANKNIFTY | INDEX | BOTH | 410 | INDEX proxy gross 0.9000 (≠ option P/L) | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | BANKNIFTY | PREMIUM | BOTH | 112 | PREMIUM after-cost -666.4765 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | BANKNIFTY | INDEX | BOTH | 242 | INDEX proxy gross -513.5500 (≠ option … | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | BANKNIFTY | PREMIUM | BOTH | 71 | PREMIUM after-cost -226.1125 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | NIFTY | INDEX | BOTH | 68 | INDEX proxy gross -184.2500 (≠ option … | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | NIFTY | PREMIUM | BOTH | 39 | PREMIUM after-cost 5.3045 (1% RT HYPOT… | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | NIFTY | INDEX | BOTH | 1119 | INDEX proxy gross 70.0500 (≠ option P/L) | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | NIFTY | PREMIUM | BOTH | 562 | PREMIUM after-cost -405.3660 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | NIFTY | INDEX | BOTH | 401 | INDEX proxy gross -23.8000 (≠ option P… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | NIFTY | PREMIUM | BOTH | 199 | PREMIUM after-cost -188.2305 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | NIFTY | INDEX | BOTH | 245 | INDEX proxy gross 81.6500 (≠ option P/L) | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | NIFTY | PREMIUM | BOTH | 116 | PREMIUM after-cost -134.8270 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | SENSEX | INDEX | BOTH | 63 | INDEX proxy gross 39.4000 (≠ option P/L) | WATCH | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 15m | SENSEX | PREMIUM | BOTH | 15 | PREMIUM after-cost -24.7180 (1% RT HYP… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | SENSEX | INDEX | BOTH | 1194 | INDEX proxy gross -663.5700 (≠ option … | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 1m | SENSEX | PREMIUM | BOTH | 276 | PREMIUM after-cost -1132.7365 (1% RT H… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | SENSEX | INDEX | BOTH | 397 | INDEX proxy gross -375.5300 (≠ option … | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 3m | SENSEX | PREMIUM | BOTH | 109 | PREMIUM after-cost -466.4160 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | SENSEX | INDEX | BOTH | 248 | INDEX proxy gross -1042.0700 (≠ option… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-012` | Oscillator Evaluator (Analysis tool) | 5m | SENSEX | PREMIUM | BOTH | 63 | PREMIUM after-cost -257.7795 (1% RT HY… | TESTED_FAIL | oscillator compare / Laguerre MA → EMA proxy |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | BANKNIFTY | INDEX | BOTH | 61 | INDEX proxy gross 1362.7000 (≠ option … | WATCH | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | BANKNIFTY | PREMIUM | CE | 1 | PREMIUM after-cost -33.9740 (1% RT HYP… | PARK | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | BANKNIFTY | INDEX | BOTH | 1037 | INDEX proxy gross 19.5500 (≠ option P/L) | WATCH | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | BANKNIFTY | PREMIUM | BOTH | 177 | PREMIUM after-cost -1406.9490 (1% RT H… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | BANKNIFTY | INDEX | BOTH | 328 | INDEX proxy gross -505.0500 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | BANKNIFTY | PREMIUM | BOTH | 17 | PREMIUM after-cost -194.6655 (1% RT HY… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | BANKNIFTY | INDEX | BOTH | 185 | INDEX proxy gross -709.3000 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | BANKNIFTY | PREMIUM | BOTH | 3 | PREMIUM after-cost -26.9730 (1% RT HYP… | PARK | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | NIFTY | INDEX | BOTH | 51 | INDEX proxy gross -63.9500 (≠ option P… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | NIFTY | PREMIUM | BOTH | 39 | PREMIUM after-cost -9.8335 (1% RT HYPO… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | NIFTY | INDEX | BOTH | 1076 | INDEX proxy gross -184.0500 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | NIFTY | PREMIUM | BOTH | 550 | PREMIUM after-cost -422.7375 (1% RT HY… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | NIFTY | INDEX | BOTH | 342 | INDEX proxy gross -226.4000 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | NIFTY | PREMIUM | BOTH | 214 | PREMIUM after-cost -133.8545 (1% RT HY… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | NIFTY | INDEX | BOTH | 190 | INDEX proxy gross -189.4000 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | NIFTY | PREMIUM | BOTH | 121 | PREMIUM after-cost -79.1720 (1% RT HYP… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | SENSEX | INDEX | BOTH | 50 | INDEX proxy gross 229.2300 (≠ option P… | WATCH | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 15m | SENSEX | PREMIUM | BOTH | 3 | PREMIUM after-cost 103.2500 (1% RT HYP… | PARK | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | SENSEX | INDEX | BOTH | 1123 | INDEX proxy gross -1238.8100 (≠ option… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 1m | SENSEX | PREMIUM | BOTH | 178 | PREMIUM after-cost -972.1825 (1% RT HY… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | SENSEX | INDEX | BOTH | 351 | INDEX proxy gross -361.0600 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 3m | SENSEX | PREMIUM | BOTH | 26 | PREMIUM after-cost -67.8420 (1% RT HYP… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | SENSEX | INDEX | BOTH | 191 | INDEX proxy gross -628.6400 (≠ option … | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-013` | Built-in Kelly ratio for dynamic positio… | 5m | SENSEX | PREMIUM | BOTH | 11 | PREMIUM after-cost -204.5915 (1% RT HY… | TESTED_FAIL | Kelly fraction omitted; 0.1% commission |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | BANKNIFTY | INDEX | BOTH | 22 | INDEX proxy gross 57.4500 (≠ option P/L) | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | BANKNIFTY | PREMIUM | BOTH | 7 | PREMIUM after-cost -229.3335 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | BANKNIFTY | INDEX | BOTH | 436 | INDEX proxy gross -192.7500 (≠ option … | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | BANKNIFTY | PREMIUM | BOTH | 101 | PREMIUM after-cost -1104.9705 (1% RT H… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | BANKNIFTY | INDEX | BOTH | 161 | INDEX proxy gross 279.2000 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | BANKNIFTY | PREMIUM | BOTH | 26 | PREMIUM after-cost -267.9825 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | BANKNIFTY | INDEX | BOTH | 76 | INDEX proxy gross 287.7000 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | BANKNIFTY | PREMIUM | BOTH | 14 | PREMIUM after-cost -198.5580 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | NIFTY | INDEX | BOTH | 21 | INDEX proxy gross 135.3500 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | NIFTY | PREMIUM | BOTH | 12 | PREMIUM after-cost -30.2685 (1% RT HYP… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | NIFTY | INDEX | BOTH | 445 | INDEX proxy gross 202.3500 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | NIFTY | PREMIUM | BOTH | 248 | PREMIUM after-cost -201.8150 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | NIFTY | INDEX | BOTH | 153 | INDEX proxy gross 91.3500 (≠ option P/L) | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | NIFTY | PREMIUM | BOTH | 76 | PREMIUM after-cost -61.0375 (1% RT HYP… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | NIFTY | INDEX | BOTH | 90 | INDEX proxy gross 127.8000 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | NIFTY | PREMIUM | BOTH | 45 | PREMIUM after-cost -54.4470 (1% RT HYP… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | SENSEX | INDEX | BOTH | 21 | INDEX proxy gross 157.1700 (≠ option P… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 15m | SENSEX | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | SENSEX | INDEX | BOTH | 443 | INDEX proxy gross -258.2100 (≠ option … | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 1m | SENSEX | PREMIUM | BOTH | 94 | PREMIUM after-cost -527.6290 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | SENSEX | INDEX | BOTH | 153 | INDEX proxy gross -154.9800 (≠ option … | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 3m | SENSEX | PREMIUM | BOTH | 29 | PREMIUM after-cost -260.9555 (1% RT HY… | TESTED_FAIL | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | SENSEX | INDEX | BOTH | 84 | INDEX proxy gross 68.7000 (≠ option P/L) | WATCH | template needs external ±1 source |
| `MIX-TV-EP-014` | Ultimate Strategy Template | 5m | SENSEX | PREMIUM | BOTH | 23 | PREMIUM after-cost 163.6210 (1% RT HYP… | WATCH | template needs external ±1 source |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | BANKNIFTY | INDEX | BOTH | 22 | INDEX proxy gross 57.4500 (≠ option P/L) | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | BANKNIFTY | PREMIUM | BOTH | 7 | PREMIUM after-cost -229.3335 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | BANKNIFTY | INDEX | BOTH | 436 | INDEX proxy gross -192.7500 (≠ option … | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | BANKNIFTY | PREMIUM | BOTH | 101 | PREMIUM after-cost -1104.9705 (1% RT H… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | BANKNIFTY | INDEX | BOTH | 161 | INDEX proxy gross 279.2000 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | BANKNIFTY | PREMIUM | BOTH | 26 | PREMIUM after-cost -267.9825 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | BANKNIFTY | INDEX | BOTH | 76 | INDEX proxy gross 287.7000 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | BANKNIFTY | PREMIUM | BOTH | 14 | PREMIUM after-cost -198.5580 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | NIFTY | INDEX | BOTH | 21 | INDEX proxy gross 135.3500 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | NIFTY | PREMIUM | BOTH | 12 | PREMIUM after-cost -30.2685 (1% RT HYP… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | NIFTY | INDEX | BOTH | 445 | INDEX proxy gross 202.3500 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | NIFTY | PREMIUM | BOTH | 248 | PREMIUM after-cost -201.8150 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | NIFTY | INDEX | BOTH | 153 | INDEX proxy gross 91.3500 (≠ option P/L) | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | NIFTY | PREMIUM | BOTH | 76 | PREMIUM after-cost -61.0375 (1% RT HYP… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | NIFTY | INDEX | BOTH | 90 | INDEX proxy gross 127.8000 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | NIFTY | PREMIUM | BOTH | 45 | PREMIUM after-cost -54.4470 (1% RT HYP… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | SENSEX | INDEX | BOTH | 21 | INDEX proxy gross 157.1700 (≠ option P… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 15m | SENSEX | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | SENSEX | INDEX | BOTH | 443 | INDEX proxy gross -258.2100 (≠ option … | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 1m | SENSEX | PREMIUM | BOTH | 94 | PREMIUM after-cost -527.6290 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | SENSEX | INDEX | BOTH | 153 | INDEX proxy gross -154.9800 (≠ option … | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 3m | SENSEX | PREMIUM | BOTH | 29 | PREMIUM after-cost -260.9555 (1% RT HY… | TESTED_FAIL | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | SENSEX | INDEX | BOTH | 84 | INDEX proxy gross 68.7000 (≠ option P/L) | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-015` | Stop loss and Take Profit in $$ example | 5m | SENSEX | PREMIUM | BOTH | 23 | PREMIUM after-cost 163.6210 (1% RT HYP… | WATCH | $$ SL/TP needs mintick/pointvalue |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | BANKNIFTY | INDEX | CE | 12 | INDEX proxy gross 162.1500 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | BANKNIFTY | PREMIUM | CE | 4 | PREMIUM after-cost -148.8050 (1% RT HY… | PARK | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | BANKNIFTY | INDEX | CE | 222 | INDEX proxy gross -286.2000 (≠ option … | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | BANKNIFTY | PREMIUM | CE | 57 | PREMIUM after-cost -597.2940 (1% RT HY… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | BANKNIFTY | INDEX | CE | 85 | INDEX proxy gross -75.3000 (≠ option P… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | BANKNIFTY | PREMIUM | CE | 18 | PREMIUM after-cost -128.2260 (1% RT HY… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | BANKNIFTY | INDEX | CE | 43 | INDEX proxy gross 530.3500 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | BANKNIFTY | PREMIUM | CE | 8 | PREMIUM after-cost -62.8940 (1% RT HYP… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | NIFTY | INDEX | CE | 11 | INDEX proxy gross 105.7500 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | NIFTY | PREMIUM | CE | 5 | PREMIUM after-cost -7.7630 (1% RT HYPO… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | NIFTY | INDEX | CE | 232 | INDEX proxy gross 231.2000 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | NIFTY | PREMIUM | CE | 128 | PREMIUM after-cost -92.0770 (1% RT HYP… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | NIFTY | INDEX | CE | 80 | INDEX proxy gross 24.6000 (≠ option P/L) | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | NIFTY | PREMIUM | CE | 37 | PREMIUM after-cost -21.2815 (1% RT HYP… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | NIFTY | INDEX | CE | 49 | INDEX proxy gross 132.0500 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | NIFTY | PREMIUM | CE | 21 | PREMIUM after-cost -13.0960 (1% RT HYP… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | SENSEX | INDEX | CE | 11 | INDEX proxy gross 436.9800 (≠ option P… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 15m | SENSEX | PREMIUM | CE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | SENSEX | INDEX | CE | 229 | INDEX proxy gross -211.8000 (≠ option … | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 1m | SENSEX | PREMIUM | CE | 51 | PREMIUM after-cost -147.3475 (1% RT HY… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | SENSEX | INDEX | CE | 78 | INDEX proxy gross -162.6000 (≠ option … | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 3m | SENSEX | PREMIUM | CE | 17 | PREMIUM after-cost -130.9920 (1% RT HY… | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | SENSEX | INDEX | CE | 44 | INDEX proxy gross -240.1000 (≠ option … | TESTED_FAIL | long-only; stepped trail stages omitted |
| `MIX-TV-EP-016` | Stepped trailing strategy example | 5m | SENSEX | PREMIUM | CE | 14 | PREMIUM after-cost 82.5660 (1% RT HYPO… | WATCH | long-only; stepped trail stages omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | PREMIUM | CE | 1 | PREMIUM after-cost -1.0160 (1% RT HYPO… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | PREMIUM | CE | 1 | PREMIUM after-cost -1.0160 (1% RT HYPO… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-017` | PMax Explorer STRATEGY & SCREENER | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | 20-ticker screener + VAR/ZLEMA MA types omitted |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | BANKNIFTY | INDEX | BOTH | 268 | INDEX proxy gross 160.3000 (≠ option P… | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | BANKNIFTY | PREMIUM | BOTH | 45 | PREMIUM after-cost -254.9300 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | BANKNIFTY | INDEX | BOTH | 3677 | INDEX proxy gross 1868.0000 (≠ option … | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | BANKNIFTY | PREMIUM | BOTH | 560 | PREMIUM after-cost -5089.5415 (1% RT H… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | BANKNIFTY | INDEX | BOTH | 1271 | INDEX proxy gross -1307.9000 (≠ option… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | BANKNIFTY | PREMIUM | BOTH | 199 | PREMIUM after-cost -1302.4105 (1% RT H… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | BANKNIFTY | INDEX | BOTH | 799 | INDEX proxy gross -1141.7000 (≠ option… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | BANKNIFTY | PREMIUM | BOTH | 122 | PREMIUM after-cost -861.4175 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | NIFTY | INDEX | BOTH | 267 | INDEX proxy gross 46.6500 (≠ option P/L) | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | NIFTY | PREMIUM | BOTH | 98 | PREMIUM after-cost -71.2765 (1% RT HYP… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | NIFTY | INDEX | BOTH | 3398 | INDEX proxy gross 1027.6000 (≠ option … | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | NIFTY | PREMIUM | BOTH | 385 | PREMIUM after-cost -495.0190 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | NIFTY | INDEX | BOTH | 1238 | INDEX proxy gross -195.3000 (≠ option … | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | NIFTY | PREMIUM | BOTH | 227 | PREMIUM after-cost -307.8345 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | NIFTY | INDEX | BOTH | 790 | INDEX proxy gross -646.2000 (≠ option … | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | NIFTY | PREMIUM | BOTH | 178 | PREMIUM after-cost -254.2375 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | SENSEX | INDEX | BOTH | 269 | INDEX proxy gross 212.6400 (≠ option P… | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 15m | SENSEX | PREMIUM | BOTH | 41 | PREMIUM after-cost 266.2075 (1% RT HYP… | WATCH | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | SENSEX | INDEX | BOTH | 3718 | INDEX proxy gross -1532.9500 (≠ option… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 1m | SENSEX | PREMIUM | BOTH | 550 | PREMIUM after-cost -3425.2855 (1% RT H… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | SENSEX | INDEX | BOTH | 1283 | INDEX proxy gross -3357.4600 (≠ option… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 3m | SENSEX | PREMIUM | BOTH | 196 | PREMIUM after-cost -414.0005 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | SENSEX | INDEX | BOTH | 772 | INDEX proxy gross -1606.7100 (≠ option… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-018` | Grid Like Strategy | 5m | SENSEX | PREMIUM | BOTH | 127 | PREMIUM after-cost -128.1375 (1% RT HY… | TESTED_FAIL | martingale qty ignored; author says don't trade |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | BANKNIFTY | PREMIUM | CE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | BANKNIFTY | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | BANKNIFTY | PREMIUM | CE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | BANKNIFTY | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | NIFTY | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | NIFTY | PREMIUM | BOTH | 1 | PREMIUM after-cost -0.4070 (1% RT HYPO… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | NIFTY | PREMIUM | BOTH | 1 | PREMIUM after-cost -0.4070 (1% RT HYPO… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | NIFTY | PREMIUM | BOTH | 1 | PREMIUM after-cost -0.4070 (1% RT HYPO… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 15m | SENSEX | PREMIUM | PE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 1m | SENSEX | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 3m | SENSEX | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-019` | Gap Filling Strategy | 5m | SENSEX | PREMIUM | BOTH | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | BANKNIFTY | PREMIUM | BOTH | 3 | PREMIUM after-cost 21.7330 (1% RT HYPO… | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | BANKNIFTY | PREMIUM | BOTH | 5 | PREMIUM after-cost -38.7810 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | BANKNIFTY | INDEX | CE | 1 | INDEX proxy gross 56.3500 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | BANKNIFTY | PREMIUM | BOTH | 6 | PREMIUM after-cost -75.4250 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | BANKNIFTY | INDEX | CE | 1 | INDEX proxy gross -12.1000 (≠ option P… | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | BANKNIFTY | PREMIUM | BOTH | 8 | PREMIUM after-cost -101.5180 (1% RT HY… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | NIFTY | PREMIUM | BOTH | 19 | PREMIUM after-cost -26.7330 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | NIFTY | PREMIUM | BOTH | 7 | PREMIUM after-cost -12.3285 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | NIFTY | INDEX | CE | 1 | INDEX proxy gross 4.5000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | NIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -17.8740 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | NIFTY | INDEX | CE | 1 | INDEX proxy gross 3.2000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | NIFTY | PREMIUM | BOTH | 16 | PREMIUM after-cost -18.5155 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 15m | SENSEX | PREMIUM | BOTH | 9 | PREMIUM after-cost 71.1080 (1% RT HYPO… | WATCH | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 1m | SENSEX | PREMIUM | BOTH | 17 | PREMIUM after-cost -155.7960 (1% RT HY… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | SENSEX | INDEX | CE | 1 | INDEX proxy gross 11.1900 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 3m | SENSEX | PREMIUM | BOTH | 23 | PREMIUM after-cost -13.5000 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | SENSEX | INDEX | CE | 1 | INDEX proxy gross 12.9300 (≠ option P/L) | PARK | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-020` | inwCoin Martingale Strategy ( for Bitcoi… | 5m | SENSEX | PREMIUM | BOTH | 7 | PREMIUM after-cost -64.0675 (1% RT HYP… | TESTED_FAIL | crypto martingale pyramid; long-only; 0% TV co… |
| `MIX-TV-EP-021` | LUBE | 15m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | BANKNIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 15m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | NIFTY | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 15m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 1m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 3m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | SENSEX | INDEX | NONE | 0 | INDEX proxy gross 0.0000 (≠ option P/L) | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-021` | LUBE | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | BTC 30m origin; leverage input ignored |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | BANKNIFTY | INDEX | CE | 12 | INDEX proxy gross 162.1500 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | BANKNIFTY | PREMIUM | CE | 4 | PREMIUM after-cost -148.8050 (1% RT HY… | PARK | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | BANKNIFTY | INDEX | CE | 222 | INDEX proxy gross -286.2000 (≠ option … | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | BANKNIFTY | PREMIUM | CE | 57 | PREMIUM after-cost -597.2940 (1% RT HY… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | BANKNIFTY | INDEX | CE | 85 | INDEX proxy gross -75.3000 (≠ option P… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | BANKNIFTY | PREMIUM | CE | 18 | PREMIUM after-cost -128.2260 (1% RT HY… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | BANKNIFTY | INDEX | CE | 43 | INDEX proxy gross 530.3500 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | BANKNIFTY | PREMIUM | CE | 8 | PREMIUM after-cost -62.8940 (1% RT HYP… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | NIFTY | INDEX | CE | 11 | INDEX proxy gross 105.7500 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | NIFTY | PREMIUM | CE | 5 | PREMIUM after-cost -7.7630 (1% RT HYPO… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | NIFTY | INDEX | CE | 232 | INDEX proxy gross 231.2000 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | NIFTY | PREMIUM | CE | 128 | PREMIUM after-cost -92.0770 (1% RT HYP… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | NIFTY | INDEX | CE | 80 | INDEX proxy gross 24.6000 (≠ option P/L) | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | NIFTY | PREMIUM | CE | 37 | PREMIUM after-cost -21.2815 (1% RT HYP… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | NIFTY | INDEX | CE | 49 | INDEX proxy gross 132.0500 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | NIFTY | PREMIUM | CE | 21 | PREMIUM after-cost -13.0960 (1% RT HYP… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | SENSEX | INDEX | CE | 11 | INDEX proxy gross 436.9800 (≠ option P… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 15m | SENSEX | PREMIUM | CE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | SENSEX | INDEX | CE | 229 | INDEX proxy gross -211.8000 (≠ option … | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 1m | SENSEX | PREMIUM | CE | 51 | PREMIUM after-cost -147.3475 (1% RT HY… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | SENSEX | INDEX | CE | 78 | INDEX proxy gross -162.6000 (≠ option … | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 3m | SENSEX | PREMIUM | CE | 17 | PREMIUM after-cost -130.9920 (1% RT HY… | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | SENSEX | INDEX | CE | 44 | INDEX proxy gross -240.1000 (≠ option … | TESTED_FAIL | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-022` | How To Set Backtest Time Ranges | 5m | SENSEX | PREMIUM | CE | 14 | PREMIUM after-cost 82.5660 (1% RT HYPO… | WATCH | session 0000-0000 = always; long-only; 0.27% c… |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | BANKNIFTY | INDEX | BOTH | 30 | INDEX proxy gross 33.2500 (≠ option P/L) | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | BANKNIFTY | INDEX | BOTH | 3 | INDEX proxy gross -11.2500 (≠ option P… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | BANKNIFTY | PREMIUM | BOTH | 4 | PREMIUM after-cost 0.8890 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | BANKNIFTY | INDEX | BOTH | 437 | INDEX proxy gross -136.3000 (≠ option … | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | BANKNIFTY | INDEX | BOTH | 86 | INDEX proxy gross -386.1000 (≠ option … | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | BANKNIFTY | PREMIUM | BOTH | 59 | PREMIUM after-cost -586.6305 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -154.0705 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | BANKNIFTY | INDEX | BOTH | 146 | INDEX proxy gross -39.7000 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | BANKNIFTY | INDEX | BOTH | 28 | INDEX proxy gross -6.2500 (≠ option P/L) | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | BANKNIFTY | PREMIUM | BOTH | 20 | PREMIUM after-cost -150.1810 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | BANKNIFTY | PREMIUM | CE | 1 | PREMIUM after-cost -18.6875 (1% RT HYP… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | BANKNIFTY | INDEX | BOTH | 86 | INDEX proxy gross 197.7500 (≠ option P… | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | BANKNIFTY | INDEX | BOTH | 12 | INDEX proxy gross 15.3500 (≠ option P/L) | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | BANKNIFTY | PREMIUM | BOTH | 13 | PREMIUM after-cost -239.5315 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | BANKNIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | NIFTY | INDEX | BOTH | 31 | INDEX proxy gross 101.3500 (≠ option P… | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | NIFTY | INDEX | BOTH | 3 | INDEX proxy gross -7.1000 (≠ option P/L) | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | NIFTY | PREMIUM | BOTH | 14 | PREMIUM after-cost -13.1445 (1% RT HYP… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | NIFTY | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | NIFTY | INDEX | BOTH | 432 | INDEX proxy gross -10.9500 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | NIFTY | INDEX | BOTH | 80 | INDEX proxy gross 18.7000 (≠ option P/L) | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | NIFTY | PREMIUM | BOTH | 241 | PREMIUM after-cost -175.5585 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | NIFTY | PREMIUM | BOTH | 42 | PREMIUM after-cost -27.7000 (1% RT HYP… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | NIFTY | INDEX | BOTH | 138 | INDEX proxy gross 26.1000 (≠ option P/L) | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | NIFTY | INDEX | BOTH | 28 | INDEX proxy gross -57.1500 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | NIFTY | PREMIUM | BOTH | 81 | PREMIUM after-cost -82.7260 (1% RT HYP… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | NIFTY | PREMIUM | BOTH | 13 | PREMIUM after-cost -8.7825 (1% RT HYPO… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | NIFTY | INDEX | BOTH | 83 | INDEX proxy gross -49.7000 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | NIFTY | INDEX | BOTH | 12 | INDEX proxy gross -43.4500 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | NIFTY | PREMIUM | BOTH | 43 | PREMIUM after-cost -17.3780 (1% RT HYP… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | NIFTY | PREMIUM | BOTH | 5 | PREMIUM after-cost -0.5465 (1% RT HYPO… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | SENSEX | INDEX | BOTH | 30 | INDEX proxy gross 66.5100 (≠ option P/L) | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | SENSEX | INDEX | BOTH | 3 | INDEX proxy gross -49.4900 (≠ option P… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | SENSEX | PREMIUM | BOTH | 4 | PREMIUM after-cost 65.9845 (1% RT HYPO… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 15m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | SENSEX | INDEX | BOTH | 430 | INDEX proxy gross -86.6100 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | SENSEX | INDEX | BOTH | 81 | INDEX proxy gross 499.5400 (≠ option P… | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | SENSEX | PREMIUM | BOTH | 60 | PREMIUM after-cost -177.7975 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 1m | SENSEX | PREMIUM | BOTH | 9 | PREMIUM after-cost -152.6375 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | SENSEX | INDEX | BOTH | 140 | INDEX proxy gross 100.5900 (≠ option P… | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | SENSEX | INDEX | BOTH | 27 | INDEX proxy gross -32.1500 (≠ option P… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | SENSEX | PREMIUM | BOTH | 21 | PREMIUM after-cost -295.3035 (1% RT HY… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 3m | SENSEX | PREMIUM | CE | 1 | PREMIUM after-cost 38.0675 (1% RT HYPO… | PARK | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | SENSEX | INDEX | BOTH | 83 | INDEX proxy gross 244.0200 (≠ option P… | WATCH | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | SENSEX | INDEX | BOTH | 15 | INDEX proxy gross -147.8800 (≠ option … | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | SENSEX | PREMIUM | BOTH | 13 | PREMIUM after-cost -71.2045 (1% RT HYP… | TESTED_FAIL | length=480 needs long tape |
| `MIX-TV-EP-023` | Grover Llorens Activator Strategy Analysis | 5m | SENSEX | PREMIUM | NONE | 0 | PREMIUM after-cost 0.0000 (1% RT HYPOT… | PARK | length=480 needs long tape |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | BANKNIFTY | INDEX | BOTH | 17 | INDEX proxy gross -234.0000 (≠ option … | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | BANKNIFTY | PREMIUM | PE | 1 | PREMIUM after-cost -11.1225 (1% RT HYP… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | BANKNIFTY | INDEX | BOTH | 325 | INDEX proxy gross -595.8500 (≠ option … | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | BANKNIFTY | PREMIUM | BOTH | 93 | PREMIUM after-cost -537.9520 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | BANKNIFTY | INDEX | BOTH | 100 | INDEX proxy gross 238.3500 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | BANKNIFTY | PREMIUM | BOTH | 17 | PREMIUM after-cost -30.1660 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | BANKNIFTY | INDEX | BOTH | 43 | INDEX proxy gross -39.6500 (≠ option P… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | BANKNIFTY | PREMIUM | BOTH | 10 | PREMIUM after-cost -7.4125 (1% RT HYPO… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | NIFTY | INDEX | BOTH | 18 | INDEX proxy gross 112.7500 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | NIFTY | PREMIUM | BOTH | 8 | PREMIUM after-cost -13.2095 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | NIFTY | INDEX | BOTH | 305 | INDEX proxy gross 69.1000 (≠ option P/L) | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | NIFTY | PREMIUM | BOTH | 153 | PREMIUM after-cost -111.6140 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | NIFTY | INDEX | BOTH | 100 | INDEX proxy gross 160.6000 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | NIFTY | PREMIUM | BOTH | 47 | PREMIUM after-cost -45.8865 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | NIFTY | INDEX | BOTH | 61 | INDEX proxy gross -22.2500 (≠ option P… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | NIFTY | PREMIUM | BOTH | 32 | PREMIUM after-cost -24.3730 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | SENSEX | INDEX | BOTH | 23 | INDEX proxy gross 43.7700 (≠ option P/L) | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 15m | SENSEX | PREMIUM | BOTH | 2 | PREMIUM after-cost 9.9155 (1% RT HYPOT… | PARK | n<5 trades; longer tape or faster public params |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | SENSEX | INDEX | BOTH | 312 | INDEX proxy gross 274.6300 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 1m | SENSEX | PREMIUM | BOTH | 80 | PREMIUM after-cost -456.2715 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | SENSEX | INDEX | BOTH | 87 | INDEX proxy gross 470.0300 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 3m | SENSEX | PREMIUM | BOTH | 22 | PREMIUM after-cost -229.1005 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | SENSEX | INDEX | BOTH | 49 | INDEX proxy gross -150.2400 (≠ option … | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-024` | Factory calibrator — public SMA crossove… | 5m | SENSEX | PREMIUM | BOTH | 12 | PREMIUM after-cost -156.7415 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | BANKNIFTY | INDEX | BOTH | 45 | INDEX proxy gross 929.5000 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | BANKNIFTY | PREMIUM | BOTH | 12 | PREMIUM after-cost 15.3100 (1% RT HYPO… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | BANKNIFTY | INDEX | BOTH | 810 | INDEX proxy gross 326.7500 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | BANKNIFTY | PREMIUM | BOTH | 210 | PREMIUM after-cost -1813.5630 (1% RT H… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | BANKNIFTY | INDEX | BOTH | 254 | INDEX proxy gross -78.1000 (≠ option P… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | BANKNIFTY | PREMIUM | BOTH | 71 | PREMIUM after-cost -177.3930 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | BANKNIFTY | INDEX | BOTH | 154 | INDEX proxy gross -615.2000 (≠ option … | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | BANKNIFTY | PREMIUM | BOTH | 32 | PREMIUM after-cost 36.1805 (1% RT HYPO… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | NIFTY | INDEX | BOTH | 41 | INDEX proxy gross 75.3000 (≠ option P/L) | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | NIFTY | PREMIUM | BOTH | 27 | PREMIUM after-cost 10.1770 (1% RT HYPO… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | NIFTY | INDEX | BOTH | 808 | INDEX proxy gross -27.6000 (≠ option P… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | NIFTY | PREMIUM | BOTH | 442 | PREMIUM after-cost -338.1040 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | NIFTY | INDEX | BOTH | 243 | INDEX proxy gross 7.9500 (≠ option P/L) | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | NIFTY | PREMIUM | BOTH | 138 | PREMIUM after-cost -93.0640 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | NIFTY | INDEX | BOTH | 125 | INDEX proxy gross -73.9000 (≠ option P… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | NIFTY | PREMIUM | BOTH | 75 | PREMIUM after-cost -47.9455 (1% RT HYP… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | SENSEX | INDEX | BOTH | 44 | INDEX proxy gross 156.8700 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 15m | SENSEX | PREMIUM | BOTH | 8 | PREMIUM after-cost 38.4780 (1% RT HYPO… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | SENSEX | INDEX | BOTH | 809 | INDEX proxy gross -924.1500 (≠ option … | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 1m | SENSEX | PREMIUM | BOTH | 196 | PREMIUM after-cost -816.7300 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | SENSEX | INDEX | BOTH | 256 | INDEX proxy gross 567.1500 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 3m | SENSEX | PREMIUM | BOTH | 68 | PREMIUM after-cost -201.5550 (1% RT HY… | TESTED_FAIL | after-cost/gross ≤0; KEEP; do not promote |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | SENSEX | INDEX | BOTH | 134 | INDEX proxy gross 482.6800 (≠ option P… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |
| `MIX-TV-EP-025` | Factory calibrator — public MACD histogr… | 5m | SENSEX | PREMIUM | BOTH | 31 | PREMIUM after-cost 95.7480 (1% RT HYPO… | WATCH | lab only; OOS+NORMAL still required; NO_PROMOTE |

## Paper-live later

Attach ticks to **this** JSON (`paper_sessions[]` / `paper_live[]`). Still `NO_PROMOTE`. Do not write customer `/`.
Paper tuner: [`TV_EP_PAPER_TUNE.md`](TV_EP_PAPER_TUNE.md) — `python -m backtest_engine tv-ep-paper-tune`.

Recon copies (gitignored): `data/recon/tv_ep_leaderboard.{json,md}`.
Harness: [`TV_EP_BACKTEST_FACTORY.md`](TV_EP_BACKTEST_FACTORY.md).


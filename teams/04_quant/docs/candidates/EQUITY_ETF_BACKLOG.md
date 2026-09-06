# EQUITY / ETF / STOCK_OPTION candidate slots

**Team:** 04_quant  
**Status:** `HYPOTHESIS` / `UNVALIDATED` / `DRAFT` / `WAITING_FOR_EDIT`  
**Date:** 2026-09-03  
**Origin packet:** [`teams/01_research/docs/handoffs/EQUITY_ETF_PACKET.md`](../../../01_research/docs/handoffs/EQUITY_ETF_PACKET.md) (`SOURCE_FACT`)  
**Not claimed profitable. No win rates. No algos. Not Phase-1 index options.**

These IDs are **`EQ-*` / `ETF-*` / `SO-*`**. They are **not** `STRAT-015+`. Do **not** append them to [`MASTER_STRATEGY_PLAN.md`](../MASTER_STRATEGY_PLAN.md) or the NIFTY/BANKNIFTY/SENSEX CE/PE book. Phase-1 remains **14 DRAFT index candidates** only.

Every slot below is a **testable hypothesis to write later**, not a proven screen. ScanX / “FREE screener” is a **Dhan product UI**. Replicating a filter list in research is still **not** an OOS backtest.

**Instruments (when a transcript exists):** cash equity unless a `SO-*` slot says single-stock option. Lots, circuit limits, STT, and stock-option lot size = **instrument master**, never constants.

---

## How to read a slot

| Field | Meaning |
|-------|---------|
| Packet tag | `EQUITY` / `ETF` / `STOCK_OPTION` |
| Evidence | English transcript + timestamps **or** catalog title/playlist only |
| ScanX | If yes: **product**, not a validated universe |
| Next | 02/03 `VALIDATION` then a spec — **not** 07_coding |

Invalidation for **all** slots: costs + slippage + discrete lots wipe any paper edge; or the spoken clock/filter set is unidentified after `[UNCERTAIN_TRANSCRIPT]`; or the idea only exists as a ScanX share code we do not have.

---

## A. English-transcript slots (`EQUITY`)

### EQ-001 — Intraday Alpha at 09:45 (volume + mcap + 20 EMA + Supertrend)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `MfGUybW4O4c`  
**ScanX/product:** yes (spoken screener)

```yaml
slot_id: EQ-001
instrument: {type: CASH_EQUITY, side: BUY}  # sell-side named, not specified as a filter set
clock: run_0945_IST  # not 0900 / 0930 / 1000 as the *same* screener
filters_spoken:
  volume_shares: 1000000  # also "Rs 10 lakh" ASR
  market_cap_cr: 5000
  price: above_EMA_20
  supertrend: price_gte_ST  # period/mult UNKNOWN
  day_pct: 0.50_to_1.50     # UNCERTAIN_TRANSCRIPT
skip: first_15m_for_newcomers
```

**Not proven.** Nifty 5m snapshot in the video is **not** the universe. Supertrend params `UNKNOWN`.

**Invalidation:** 09:45 vs other clocks; volume 10 lakh vs 1M; ST params unidentified; small-cap leak if mcap filter dropped.

---

### EQ-002 — Intraday Momentum Blast (IMB) on ScanX

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `O8h44rgJ84k` (primary) · sister `kJ5HZKzpZqQ`  
**ScanX/product:** **yes — not a backtested screen**

```yaml
slot_id: EQ-002
instrument: {type: CASH_EQUITY, side: BUY}
clock: 0945_or_1000_IST  # conflict; search, do not pick
scanx_filters_O8h:
  price_gt_open: true
  day_pct_gt: 1.0
  rsi_gt: 60          # period UNKNOWN unless product default
  macd_gt: 0
  unusual_volume_1d: true  # token UNKNOWN
  price_gt_supertrend: true  # params UNKNOWN
  market_cap_cr: 50000  # speaker practice; alt 20000; first figure UNCERTAIN
optional: OT_web_futures_OI_buildup
do_not_change: any_param_except_market_cap  # as spoken
```

Sister `kJ5HZKzpZqQ`: mcap **10000** or **5000–20000**; **5>20>100 EMA**; MACD histogram; usable **until 15:00**; spoken **0.6%** after costs as a **personal hurdle**, not a measured expectancy.

**Not proven.** HAL/DLF/Adani tape in-video ≠ sample. Do not code a ScanX bot.

**Invalidation:** 9:45 vs 10:00; mcap 20k vs 50k vs 10k; unusual-volume definition missing; Supertrend params missing; OI overlay changes the set.

---

### EQ-003 — BTST proxy (~15:10–15:15 cash)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `IvSnlbt89yw`  
**ScanX/product:** proxy screener on ScanX — **shortlist only** (speaker: do not buy from screener)

```yaml
slot_id: EQ-003
instrument: {type: CASH_EQUITY, side: BUY}
horizon: BTST  # overnight gap risk spoken
entry_window: 1510_to_1515_IST  # also "3:15" / ASR "5:15"; search
exit_window: next_open_0915_to_1000_IST
daily_filters_spoken:
  rsi_14_gt: 65
  open_gt_prior_open: true
  close_gt_prior_close: true
  volume_gte: 2x_10day_sma
  near_52w_high: 0.90_of_250d_high  # UNCERTAIN wording
```

**Not proven.** Hero/Federal/Kalyan examples are **education**. Overnight news = structural risk, not a footnote.

**Invalidation:** gap-down cluster; 3:15 vs 3:10 vs 5:15; 90%-of-year-high rule unidentifiable; volume×2 too rare or too wide after costs.

**Do not** merge `G31RFueZLvk` into this **cash** slot. G31 is **F&O stocks + stock options** at 14:55 — see `SO-003`.

---

### EQ-004 — Pullback / buy-the-dip (EMA stack + 30m trigger)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `4TT8IV5S1_A`  
**ScanX/product:** yes

```yaml
slot_id: EQ-004
instrument: {type: CASH_EQUITY, side: BUY}
uptrend:
  price_gt_ema50: true
  ema20_gt_ema50: true
  ema50_gt_ema200: true
pullback_optional:
  two_week_pct: -10_to_-5  # speaker: no set criteria
  rsi: 40_to_55            # UNCERTAIN 40-50 vs 40-55
  market_cap_cr: 5000      # optional
trigger_30m:
  ma5_gt_ema15_gt_ema50: true
  do_not_buy_on_pullback_alone: true
```

**Not proven.** “13% in 2 days” is an **anecdote**.

**Invalidation:** dip is a reversal; 5/15/50 stack never fires; mcap on/off changes names; two-week % band arbitrary.

---

### EQ-005 — Intraday Rockers at 09:20

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `_byuht38r5s`  
**ScanX/product:** yes

```yaml
slot_id: EQ-005
instrument: {type: CASH_EQUITY, side: BUY}
clock: 0920_IST
filters_spoken:
  close_gt_ema20: true          # also "21 EMA" later — conflict
  close_gt_supertrend: {length: 7, mult: 3}  # UNCERTAIN vs 10,3 elsewhere
  rsi_14: between_55_and_UNKNOWN_upper
  volume_gt: 2x_10day_avg
  macd_hist_bullish: true
  day_pct_gt: 0.50
exit_anecdote: 0.6_to_0.7_pct  # not a tested target
```

**Not proven.** Recording-day Nifty “slightly positive” is **not** a regime study.

**Invalidation:** ST 7×3 vs 10×3; EMA 20 vs 21; RSI band incomplete; 09:20 too early vs Alpha 09:45 (EQ-001) — **do not silently merge.**

---

### EQ-006 — RLB (Rocket Launcher Breakout)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `pBQ1oVDVe3M`  
**ScanX/product:** yes · optional F&O OI on OT web

```yaml
slot_id: EQ-006
instrument: {type: CASH_EQUITY, side: BUY}
filters_spoken:
  price_gt_prior_day_high: true
  close_gt_open: true
  close_gt_ema20_and_ema50: true  # SMA50 alt UNCERTAIN
  rsi_gt: 65  # also "60 preferably 65"
  day_pct_gt: 2.0
  volume_gt_sma5_volume: true
optional: futures_OI_buildup
```

**Not proven.** “38% in a month” / MTF 4× stories are **CTA + anecdote**. Do not multiply imaginary 10% by leverage in any table.

**Invalidation:** prior-day-high breakouts fail after costs; RSI 60 vs 65; OI filter unavailable historically.

---

### EQ-007 — Four-name cash book (20 EMA + VWAP)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `OZRfSMg4qUY`

```yaml
slot_id: EQ-007
instrument: {type: CASH_EQUITY, side: BUY_or_SELL}
universe: 3_to_4_names_fixed_for_3_to_4_months
exclude: NIFTY_INDEX, BANKNIFTY_INDEX, hopping_scanners
indicators: [VWAP, EMA_20]  # ASR VVIP/VWP
long: pullback_to_ema20_after_bullish_cross  # wording search
short: price_below_ema20_and_vwap_then_pullback
examples_not_universe: [Titan, Maruti, Bajaj_Finserv, ...]  # spoken then edited
stock_options: speaker_discourages_if_already_in_index_options
```

**Not proven.** “90% of mistakes” is **rhetoric**. Example names are **not** a mandated book.

**Invalidation:** four-name sample too small for inference; VWAP on cash vs futures; stop rule unidentified (“four stops”).

---

### EQ-008 — 09:08 sector gap → 09:20 stock PA

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `ZoCD4fLKy6M`

```yaml
slot_id: EQ-008
instrument: {type: CASH_EQUITY, side: BUY_or_SELL}
preopen:
  block_deals_window: 0845_0900_IST  # context only
  sector_watchlist_at: 0908_IST      # Dhan Charts scan watchlist
open:
  session: 0915_IST
  first_5m_candle: 0915_0920
style: price_action  # indicators optional
stop_target: small_stop_large_target  # no numbers
```

Uses **Nifty sector indices as a map** to **stocks**. Not an index-option slot. Stop size `UNKNOWN`.

**Invalidation:** 09:08 print is not a tradable auction; gap fades; no numeric stop.

---

### EQ-009 — RSI oversold + green candle → Supertrend child (equity native)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `H_6keeRUCDM`  
**Note:** Phase-1 `STRAT-011` is a **projected index transfer**. This slot stays on **stocks / listed examples**. Do not collapse the two.

```yaml
slot_id: EQ-009
instrument: {type: CASH_EQUITY, side: BUY}  # gold futures also spoken — out of this packet
parent_tf: weekly  # examples
parent_rule: RSI_oversold_AND_green_candle
child_tf: one_step_lower  # daily in the weekly example
child_rule: close_above_supertrend_10_3
rsi_period: UNKNOWN
mtf_pledge: product_CTA_not_a_rule
```

**Not proven.** Info Edge / Adani weekly charts are **illustrations**. MTF interest arithmetic is **not** a return.

**Invalidation:** RSI period unidentified; oversold threshold unidentified; rarity → too few trades after costs.

---

### EQ-010 — Intraday PA + VWAP (stock examples)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / **thin**  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `PUkzVgVPCf0`

Needs a second SOURCE_FACT pass. Spoken pieces already in packet: trail **swing low**, **VWAP**, “open = low.” **VWAP on traded tape only.**

**Invalidation:** incomplete rule set (`DATA_INSUFFICIENT` until edit pass).

---

### EQ-014 — Multi-year ATH breakout (price + volume + delivery)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `EQUITY`  
**Origin:** `DHAN-DERIVED` `dEvF8biE02M`  
**ScanX/product:** 52-week-high screener is a **weekend shortlist only**, not the 5-year rule

```yaml
slot_id: EQ-014
instrument: {type: CASH_EQUITY, side: BUY}
horizon: positional_6_to_8_months  # guest; not a mandate
structure: 5y_horizontal_at_ATH  # not bottom consolidation
entry: monthly_close_breakout  # wait candle close spoken
volume: plus_40pct_vs_average  # UNCERTAIN vs 40% body
delivery_pct: gte_40  # NSE / bhav
stop: breakout_candle_low_minus_1pct
target_1: range_height_above_breakout  # book 50%
trail: two_weekly_closes_below_EMA_21  # after T1 only
do_not_copy: 100pct_in_2y_guest_language
```

**Not proven.** 50%→60% accuracy speech is **not** a measured lift. AB Capital / named charts = education.

**Invalidation:** 40% means three different things; delivery series unidentified; 5-year ATH set too rare after costs; ScanX 52w ≠ 5y ATH.

**Do not** merge with `EQ-011` (playlist still `TRANSCRIPT_PENDING`).

---

## B. Waiting slots — catalog titles / playlists only

**No English transcript. No spoken parameters. Do not invent filters from the title.**

### EQ-011 — Swing Trading Series (10 episodes)

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `TRANSCRIPT_PENDING`  
**Tag:** `EQUITY`  
**Origin:** catalog playlist `PLnuHyqUCoJsOGfQZoHUy56MdTu2LcOK9k`  
Ep3 title *How To Pick Stocks For Swing Trading* (`BvhUn6W8AmI`) is the stock-selection pointer — **title only**.

Long EN masterclass `2YBmiyVmNNw` is **not** a substitute for this series (`DATA_INSUFFICIENT` for rules). `dEvF8biE02M` is a **different** recipe — see `EQ-014`. Ignore guest % talk.

---

### EQ-012 — Pair trading stock futures

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `TRANSCRIPT_PENDING`  
**Tag:** `EQUITY`  
**Origin:** titles `qRNkN7eKNHI` / `dMPdRjiWx-8`  
Instrument: **stock futures** (catalog). No legs, hedge ratio, or universe in evidence.

---

### EQ-013 — Muhurat / penny-stock shorts (do not promote)

**Status:** `REJECTED` as strategy slots until transcript  
**Tag:** `EQUITY`  
`tPRs6gqErAE` (Muhurat 1-hour) · `r3VdWESNSy8` (25s penny-stock quiz). Catalog `STOCK_ONLY`. **No recipe.**

---

### ETF-001 — ETF trading / silver ETF / pledge-margin ETFs

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `TRANSCRIPT_PENDING`  
**Tag:** `ETF`  
**Origin:** catalog titles only — `vQfWtqHTVJE` (ETF Trading Strategy Explained), `TzvPlqfRpts` (Silver ETFs technical + fundamental), plus product/excluded rows `oxlW6BGQn2k`, `dU76pTcZx1w`, `1Hy8sT94J6Q`, `mhdlO4eAyhI`, `tUl9Zc1KLKo`, `Cl7C8bTcl6U`, `fFhiw6DQTQk`.

**Cannot** write a silver-ETF rule set from the title. US-listed stocks/ETFs on Dhan are **product walkthroughs**, not NSE cash screens.

---

### SO-001 — Stock Options Trading Series + masterclass

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `TRANSCRIPT_PENDING`  
**Tag:** `STOCK_OPTION`  
**Origin:** catalog `STOCK_ONLY` + playlist `PLnuHyqUCoJsOMo_zyEPYTHRHlALuVg5eR` + extra titles `H_-8Nzlb5dY`, `CRzuVqisVo4`, `gApsIjlswDI`, `JOafo3S1xKs`, `-4cOh1JbpQc`

Title map (not spoken claims): myths → IV/time → delta → chain → hedging → bear put spread → covered call → covered put → backtesting → risk. **Covered call/put and spreads are not Phase-1 index buy.**

EQ-007’s speaker **discourages** stock options for index-option traders (liquidity/lot). That is **opinion**, not a kill switch for this slot.

---

### SO-002 — ScanX “options strategy” title

**Status:** `HYPOTHESIS` / `UNVALIDATED` / `TRANSCRIPT_PENDING`  
**Tag:** `STOCK_OPTION` or mixed — **unknown until transcript**  
**Origin:** title `gQXaA2dPBa8` *Options Trading Strategy with ScanX Screener!*  
**ScanX/product:** yes. Could be index or stock. **Do not assume NIFTY.**

---

### SO-003 — F&O-stock BTST + near-ITM option overlay (14:55)

**Status:** `HYPOTHESIS` / `UNVALIDATED`  
**Tag:** `STOCK_OPTION`  
**Origin:** `DHAN-DERIVED` `G31RFueZLvk`  
**ScanX/product:** F&O list + Power Scalper **UI**, not a scanner REST

```yaml
slot_id: SO-003
instrument: {type: STOCK_OPTION, side: BUY}  # after cash F&O-name filter
universe: NSE_FNO_stocks  # dated membership
clock:
  shortlist: 1455_IST
  option_tick: 1515_to_1520_IST
  exit: next_open_0915_to_0920_IST
stock_filters:
  rank: pct_change_top_gainers_or_losers  # vs index sentiment; subjective
  close_gt_prior_day_high: true  # CPR overlay
  rsi_5m: 50_to_75  # 85+ skip; "5 to 75" ASR
option_filters:
  strike: near_ITM  # not far OTM
  tf: 5m
  supertrend: {length: 10, mult: 3}  # spoken "103"
  hull_ma: 32
  call: close_above_ST_and_hull
  put: close_below_ST_and_hull
stop: TIME_BASED_next_open  # not a price SL; gap risk spoken
```

**Not proven.** Exide / Cummins tapes are **examples**. Hull 32 “backtest” is **claimed in-video, not in repo**. Do **not** merge with `EQ-003` (cash BTST ~15:15).

**Invalidation:** RSI band unidentifiable; overnight option gap through SL; F&O list churn; Hull 32 unidentified vs Dhan default.

---

## C. Explicitly **not** candidate slots

| Why | What |
|-----|------|
| ScanX is a **product**, not a tested screen | Playlists How To Use Scanx / Use ScanX for Trading; `ugmYfiTpUsc`, `wCXyqT4BSFw`, heatmaps `lK3BXwqfqIA`, live feed `fxGbC7eMFkY` — **UI education**. May inform **how to replicate a filter**, never a performance claim. |
| `EXCLUDED_STOCK_ONLY` investing/MF/SIP/gold/AMC | Stay excluded from strategy construction. Listed in the packet so they are not “lost,” not so they become slots. |
| Index-only EN videos | Other agents. |
| `EVk_Wa_1cm0` Darvas Box clip | Product dots; **no** params — not a slot. |
| Algo playlists | Out of charter (no algos). |
| Guest CAGR / “38% month” / “0.6% after ST” / “100% in 2 years” | Anecdote or hurdle **speech**, not backtest output. |

---

## What 06_backtesting must not do (if this packet is ever queued)

- Mix `EQ-*` fills into NIFTY option blotters.
- Use ScanX click-results as a historical series (no scanner REST on HQ docs).
- Report a win rate from a YouTube chart-day.
- Implement Python/DEXT algos from this backlog.

**Review:** five-pass **not started**. `RESEARCH_READY_FOR_PROGRAMMING` = **no**.

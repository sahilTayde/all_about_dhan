# SOURCE_FACT — HAUSZx-hYdY

**Status:** `EXTRACTED` (layer A only). `DRAFT` / `WAITING_FOR_EDIT`.  
**Do not treat as strategy, advice, or validated edge.**

| Field | Value |
|-------|--------|
| video_id | `HAUSZx-hYdY` |
| title | The Ultimate 1-Hour Masterclass on Option Buying Strategies \| Option Trading Strategy \| Dhan |
| url | https://www.youtube.com/watch?v=HAUSZx-hYdY |
| retrieved_at | 2026-08-31T03:16:20Z |
| language | hi (ASR generated) |
| transcript | `data/transcripts/normalized/HAUSZx-hYdY.md` |
| english | `ENGLISH_PENDING` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |
| relevance | HIGH / OPTIONS, OPTION_CHAIN, VOLATILITY, GREEKS, RISK_MANAGEMENT, STRATEGY_DESIGN |
| guests | Host (Dhan) + Himanshu Arora (spoken as guest / “star trader”) |

**Disclaimer spoken in video:** examples are educational; speaker says he does not want to share recommendations; NIFTY/stock names are examples only (~09:18–09:27).

**ASR warning:** Hindi auto-captions. All **numbers** below that are not trivially restated are tagged `[UNCERTAIN_TRANSCRIPT]`. Do not silently “correct.”

---

## Topics (from transcript, not title)

OPTIONS, OPTION_CHAIN, CE/PE, ITM/ATM/OTM, INTRINSIC/TIME VALUE, DELTA, THETA, IV, OI, EXPIRY, LIQUIDITY, DUAL_TIMEFRAME, MACD, MOVING_AVERAGES, RISK, INTRADAY.

---

## Claims (layer = SOURCE_FACT)

### Education / payoff (not a production rule)

| claim_id | timestamp | claim (paraphrase of spoken) | type | confidence |
|----------|-----------|------------------------------|------|------------|
| HAUS-C01 | 00:07–00:14, 06:00–06:04, 06:41–06:47 | Option **buyer** profit can be unlimited; loss limited (premium). Option **seller** loss can be unlimited; profit limited. | education | high (repeated) |
| HAUS-C02 | 01:41–01:45, 15:49–15:53 | Host cites “93% lose / 7% make money” as prior data. **Not independently sourced in this video.** | statistic | low; `[UNCERTAIN_TRANSCRIPT]` 93/7 |
| HAUS-C03 | 02:38–02:56 | Speaker: there is no “holy grail” 99% strategy in options. Only “never sell a share at a loss and hold for life” is framed as 100% — not an options rule. | education | high |
| HAUS-C04 | 03:34–03:42 | Speaker’s personal view: trading strategy role at best ~49%; ~51% risk management + behaviour. `[UNCERTAIN_TRANSCRIPT]` 49/51 | opinion | medium |
| HAUS-C05 | 04:01–05:11 | Derivatives: futures = both parties have right **and** obligation; options compared to insurance = buyer has right, seller has obligation. | education | high |
| HAUS-C06 | 06:16–06:32 | Four parties: call buyer, put buyer, call seller, put seller. Video focus: buying (call buyer + put buyer). | education | high |
| HAUS-C07 | 08:37–08:48 | Bullish view → buy call (right to buy at predetermined price). Bearish → buy put (right to sell at predetermined price). | education | high |
| HAUS-C08 | 09:29–13:16 | Hypothetical NIFTY ~₹25,000; strike is the deal price; **NSE decides strikes**; NIFTY strikes in **50-point multiples** (cannot pick 24,970). Premium from demand/supply plus other factors. | education + contract | high on concept; live LTP numbers `[UNCERTAIN_TRANSCRIPT]` |
| HAUS-C09 | 11:39–12:32 | Live chain example: NIFTY ~24827; 24600 call premium spoken ₹343 × lot size; 24700 ~₹275; 25000 ~₹100–115. **Screen-day snapshot only.** `[UNCERTAIN_TRANSCRIPT]` | example | low (ephemeral) |
| HAUS-C10 | 14:05–15:10 | If market rises, call premiums tend to rise and put demand falls (and vice versa). Bullish view → buy calls; bearish → buy puts. | education | high |
| HAUS-C11 | 15:28–16:44 | Derivatives expire. NIFTY ETF / cash shares do not. Buyer must be right **within the expiry window**. Spoken NIFTY expiries: 19 Jun (that day), then Thu 26 Jun, 3 Jul, 10 Jul, 17 Jul. Speaker notes NSE/SEBI recently changing expiries — **not discussed further**. Weekly + month-end “big” monthly expiry mentioned. | education + dated market | medium; expiry **calendar is time-stamped**; do not freeze |
| HAUS-C12 | 16:57–18:33 | Buyer can exit before expiry if premium appreciates (example ₹100 → 120). Whole game for buyer is **premium appreciation**. Need predefined buy / stop / target. | education | high |
| HAUS-C13 | 18:41–20:03 | Buyer must be right **quickly**; time value decays. Linear ₹1/day example is spoken as **not** the real calc. | education | high |
| HAUS-C14 | 20:05–22:24 | Premium ≈ intrinsic + time value. ITM call example: NIFTY 25000 vs 24500 call intrinsic ≥500; live 24832 vs 24500 intrinsic 332, option ~425 so ~100 time value. Longer expiry (31 Jul vs 26 Jun) → same intrinsic, higher time value. `[UNCERTAIN_TRANSCRIPT]` | education | medium |
| HAUS-C15 | 23:26–26:03 | **ITM:** exercise vs spot would profit (calls below spot; puts above). **OTM:** exercise would lose. **ATM / around-the-money / CTM:** ~no profit/loss on immediate exercise. OTM intrinsic = 0 (not negative). Same strike ATM for both call and put when spot = strike. | education | high |
| HAUS-C16 | 27:27–29:14 | Chain fields spoken: strike (exchange-set), LTP, LTP change (₹ or %), volume (lots/qty), OI = outstanding contracts; 1 buyer + 1 seller = 1 OI (not 2). OI change: new contracts vs unwind. | education | high |
| HAUS-C17 | 30:42–31:35 | **Delta** = rate of change of option premium w.r.t. underlying. Spoken: 24500 call delta ~0.8143 → ~₹80–81 on ₹100 NIFTY move; ATM ~0.52 → ~₹52; OTM 0.1–0.3 → ~₹20–25. Gamma mentioned, deferred. `[UNCERTAIN_TRANSCRIPT]` decimals | education | medium |
| HAUS-C18 | 32:08–33:50 | High confidence → higher delta (ITM). Low confidence / “hero trade” → tiny delta / ₹2 options (OTM lottery). Hypothetical 70–80% win-rate traders would use 70–80 delta. **Not a tested win rate.** | education / opinion | medium |
| HAUS-C19 | 33:52–34:12 | **Theta** = rate of change of premium w.r.t. time; generally a **negative** number for the long option (time decay). | education | high |
| HAUS-C20 | 34:17–35:42 | **IV** = implied volatility, not “intensive value.” Events (Fed, budget, election) → options get expensive as IV rises. Speaker: IV is a risk gauge; seller’s risk more affected because seller loss unlimited. | education | high |
| HAUS-C21 | 37:14–38:48 | Buyer fights theta: premium must rise **more than theta**. Need direction **and** speed. Theta decay **not linear**; accelerates near expiry (spoken “exponentially”). | education | high |
| HAUS-C22 | 38:19–38:29 | Speaker experience: if purchased option not in profit within next **four days**, chances it will profit are “very low.” | opinion / heuristic | medium |
| HAUS-C23 | 40:10–40:58 | Buyer plays **profitability** (large wins, lower hit rate); seller plays **probability**. Buyer compared to Afridi/Sehwag (hit and leave), not Dravid. | education / metaphor | high |
| HAUS-C24 | 40:50–41:12 | If profitable **intraday**, exit; profit after 4 days not guaranteed. Asian Paints example: stock up but call can still lose due to time. | education | high |

### Strategy rules as spoken (still SOURCE_FACT, not a coded strategy)

**Logic (not indicator yet):** parent TF = direction + momentum; child TF = replicate when child also aligns. Dual TF “more than sufficient”; multi-TF too complex for option buying (~41:32–41:54).

| field | spoken |
|-------|--------|
| Parent TF | Hourly chart |
| Child TF | 5 **or** 10 minutes (both spoken) |
| Preferred horizon for buyer | Intraday (theta “hardly” hurts) |
| Underlying move cited | ~0.5–1% in NIFTY/underlying can make option ROI larger `[UNCERTAIN_TRANSCRIPT]` |
| Universe spoken | NIFTY 100 stocks “highly liquid”; ~230 stocks have options but not all liquid; check bid-ask gap “nominal” (~43:14–44:12). **Stock universe — not index-only.** |
| Momentum indicators named | Williams %R, RSI, CCI, MACD (reversal/momentum); Supertrend, SMA, EMA (trend) (~44:29–45:00) |
| MACD used | Default spoken **12 and 26** period MAs; speaker **multiplies parameters ~4×** (“three/four times”; “all three parameters”). Histogram-only after dropping MACD/signal lines. Green hist = bullish, red = bearish. `[UNCERTAIN_TRANSCRIPT]` exact 4× of 12/26/**9** |
| MA stack | **10, 30, 100** period. Bullish if 10 > 30 and 30 > 100. Later entry recap also says 10 above 30 **and 300** (~59:26) — **conflict; `[UNCERTAIN_TRANSCRIPT]`** |
| Trail / exit MA | 10-period above 30 to hold; later “**9**-period MA below 30” to exit (~56:24–56:48, 01:02:15). **9 vs 10 conflict; `[UNCERTAIN_TRANSCRIPT]`** |
| Call example date | 13 May 2025 hourly bullish; 5m child (~54:07–54:26) |
| Put example date | 13 Feb 2025; 5m; stock ~2.5–3% down that day (~48:49–50:36) |
| Session filter | New trades mostly **after 10:00**; mostly **not after 14:30**; **certainly not after 15:00**. Best personal window ~11:00–13:00. 10:00–14:30 system; 14:45 vs 15:00 wording messy `[UNCERTAIN_TRANSCRIPT]` (~55:18–55:42, 01:00:22–01:00:35) |
| Entry | After 10:00 and before 14:30: on **child** MACD bullish **and** 10/30/100 bullish stack; buy **above that candle’s high**. Slightly **OTM** option. Mirror for puts when both bearish. |
| Strike | Speaker personally: **1–2 strikes OTM** (~0.40 delta spoken for adverse case). ATM called most “overvalued/pumped.” Conviction % “equals your delta” as a personal rule (~57:26–59:01). |
| Target | ~**20–30%** option value increase; or rupee examples ₹2500 on ₹10k / ₹5000 on ₹1 lakh margin — **ASR money figures messy** `[UNCERTAIN_TRANSCRIPT]` (~01:01:05–01:02:02) |
| Stops | (1) **Time stop** = end of day if used as intraday (speaker does not overnight; viewers may BTST). (2) Indicator: 9/10 MA vs 30 or MACD bearish. (3) **Ultimate stop = recent swing low of underlying**, **not** option-premium chart (speaker tried premium stops; got wicked then recovered). Beginner rupee cap ~1500–1700 vs 2500 target (~1:1.5 RR, speaker says not 1:2/1:3) `[UNCERTAIN_TRANSCRIPT]` |
| Carry | Speaker: no overnight. Strategy “not purely intraday”; BTST possible if you choose (~01:00:41–01:00:54). Decide **before** entry (~01:06:30–01:06:50). |
| Alt TF | Parent 2h + child 15m also spoken (~01:02:51–01:02:54). Need a large gap between parent and child. |
| Lot | Lot size set by NSE/SEBI; cannot buy 1–2 shares (~01:04:00–01:04:05). **No numeric lot hardcoded as eternal.** |
| Greeks caveat | Exact option price at a given underlying level depends on delta, gamma, theta, vega, rho; retail usually cannot compute exact mapping (~01:01:24–01:01:44). |

**Speaker examples of option ROI on ~0.5–3% underlying moves are anecdotes, not backtests.** Education ≠ proof.

---

## Indicators (params as spoken)

| Name | Params as spoken | TF | Use |
|------|------------------|----|-----|
| MACD | 12, 26 (and implied signal); then ×3 or ×4 all params; histogram only | hourly parent, 5m child | momentum / fewer signals |
| SMA/EMA stack | 10, 30, 100 (and conflicting 300 / 9) | same | trend alignment |
| Supertrend, RSI, Williams %R, CCI | named, **not parameterized** in this video | n/a | named alternatives |

---

## Options mapping spoken

Underlying examples: NIFTY, stocks (Bajaj Auto, Asian Paints, Reliance, TCS), commodities mentioned as possible. Expiry weekly/monthly. ATM/ITM/OTM defined. CE/PE LTP, volume, OI, OI change, IV, delta, theta; gamma/vega/rho named late. Bid-ask gap for liquidity. **Strike: test 1–2 OTM vs ATM vs ITM; do not assume ATM.**

---

## Data requirements (for later teams)

```text
DATA_SOURCE: DhanHQ / exchange (later) — not from this video
INSTRUMENT: index options CE/PE (project scope) vs speaker’s NIFTY-100 stocks
EXCHANGE_SEGMENT: NSE for NIFTY examples; stock F&O if stock universe used
CALCULATION: MACD, MAs on **underlying** (hourly + 5m); option LTP for target %; underlying swing for stop
TIMEFRAME: 1h parent, 5m (or 10m) child; session 10:00–14:30 IST new entries
```

VWAP **not** used in this video.

---

## What this video is NOT

- Not a NIFTY/BANKNIFTY/SENSEX-only strategy (NIFTY-100 stocks + option overlay).
- Not a backtest. Dates (Feb/May 2025) are cherry-picked walkthroughs.
- Not English-verified (`ENGLISH_PENDING`).

---

## Handoff to 02 / 03

Validate: delta/theta/IV/OI definitions; ITM intrinsic; theta non-linearity; MACD 4× params; 9 vs 10 MA; NIFTY strike step 50; expiry calendar **as of recording vs now**; lot size never freeze; liquidity/bid-ask.

# SOURCE_FACT — 2RnBT9DDDNI

**Status:** `EXTRACTED`. `DRAFT` / `WAITING_FOR_EDIT`. Layer A only.

| Field | Value |
|-------|--------|
| video_id | `2RnBT9DDDNI` |
| title | FREE Option Buying Masterclass: This Changes How You Trade Forever |
| url | https://www.youtube.com/watch?v=2RnBT9DDDNI |
| retrieved_at | 2026-08-31T03:17:15Z |
| language | hi ASR |
| transcript | `data/transcripts/normalized/2RnBT9DDDNI.md` |
| english | `data/transcripts/normalized_en/2RnBT9DDDNI.md` (`ENGLISH_VERIFIED`; Hindi claims below not rewritten this pass) |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |
| guest | Dr. Gokul Chhabra / Jhabra (ASR variants) — spoken as SEBI-registered research analyst |

MTF Excel / Google Form promo (~05:52–06:45) is **NOT_EVIDENCE** for strategies.

---

## Scope as spoken

- Topic: **index options buying** (Index OB).
- Indices named: NIFTY, BANKNIFTY, BANKex, Fin Nifty, Midcap — ASR messy (`बैंकक्स`, `मिडC`, `ससेक्स`).
- Strategy **recommended for index only**, not stock options this video (~22:13–22:16).
- Analysis on **futures** (volume exists); **spot** used to pick strike; **trade the premium** (option). Never trade NIFTY cash/spot (~17:59–18:36, 18:46–19:20).
- Spot volume on NIFTY is **not** “how much NIFTY traded” (~18:46–18:52).

---

## Claims

| claim_id | timestamp | claim | type |
|----------|-----------|-------|------|
| GOK-C01 | 00:14–08:16 | Biggest killer of option buyers ranked: (1) emotional instability (2) position sizing (3) timing. Analysis is what people over-focus on. | opinion |
| GOK-C02 | 10:12–10:22 | Market three ways: up / down / flat. Buyer max win probability spoken “less than 33%.” `[UNCERTAIN_TRANSCRIPT]` | education |
| GOK-C03 | 12:18–12:23 | **Two** strategies will be taught. | meta |
| GOK-C04 | 15:23–17:19 | Toy example: NIFTY ~24000 call LTP 137, target 160, stop 131/130; RR ~1:3; capital example 65×140 ≈ ₹8900. **Lot 65 is a dated example — VERIFY, never freeze.** `[UNCERTAIN_TRANSCRIPT]` | example |
| GOK-C05 | 16:04–16:09 | Option components named: gamma, theta, vega (ASR “बीगा”), rho. | education |
| GOK-C06 | 19:39–19:51 | Futures: current / near / far expiry. Focus **current**. Far not needed for this class. | education |
| GOK-C07 | 22:24–22:36 | If asked BANKNIFTY / Midcap / Sensex: speaker would recommend working **that index’s futures** (same idea). | education |
| GOK-C08 | 23:07–23:40 | FinNifty / Bankex expiries spoken as more **monthly**, lower volume vs NIFTY/BANKNIFTY/Midcap/Sensex. FinNifty “derived” from BANKNIFTY components. **Calendar must be re-verified — SEBI weekly-expiry regime changed after many recordings.** | market (dated) |
| GOK-C09 | 24:26–24:30 | “Option buying is 70% non-trading and 30% trading.” `[UNCERTAIN_TRANSCRIPT]` | opinion |
| GOK-C10 | 01:00:36–01:02:05 | Volatility **bearing** (sitting through MTM) harder than direction. Same 70/30 non-trade/trade restated. | opinion |
| GOK-C11 | 01:03:53–01:04:05 | Host: generally avoids **50-multiple** NIFTY strikes (liquidity thinner vs 100s). Guest: still trades them; problem bigger on FinNifty/Bankex. | liquidity opinion |
| GOK-C12 | 01:04:28–01:05:00 | Priority spoken: (1) NIFTY (2) BANKNIFTY (3) SENSEX (4) Midcap then FinNifty/Bankex mainly in expiry week. BANKNIFTY “hotspot” 1.5–2y ago; now NIFTY and Sensex. **Dated.** | opinion |
| GOK-C13 | 01:08:37–01:09:29 | If NIFTY buy signal and BANKNIFTY sell (mixed): **avoid that day** or trade only **dominant** index — not both. If all three aligned, opportunity; still don’t trade all blindly. |
| GOK-C14 | 01:10:32–01:11:19 | If three indices all buy: diversify **one lot each** better than three lots in one index (capital-dependent). |

---

## Strategy 1 — futures VWAP + VWMA + Supertrend (intraday)

| field | spoken |
|-------|--------|
| Chart | **Index futures** (example NIFTY June futures), 3-minute |
| Ignore | **09:15–09:45** candles completely |
| Flat | All positions **before 15:15** (`3:15`); intraday only; no overnight/BTST |
| Indicators | VWAP **default** (color only). VWMA **length 20**. Supertrend **default 10,3** (spoken “103”) |
| Put buy | Price **below** VWAP **and** VWMA **and** Supertrend |
| Call buy | Price **above** all three |
| Stop | Supertrend: exit if price **closes** on other side of Supertrend on 3m — **track**, do not rest a broker stop on Supertrend necessarily |
| Trail | Do **not** trail to cost-to-cost on Supertrend trail (will get shaken); if shaken, **re-enter** if setup valid |
| Sideways / no-trade | When Supertrend and VWAP **disagree** (e.g. ST bearish, VWAP bullish) → no **new** entry; existing may continue (~34:54–36:01) |
| VWMA role | “Pullback engine” — wait pullback to VWMA rather than chase (~32:45–33:30) |
| Min RR | 1:1 minimum; 1:2 discussed; then trail (~28:11–28:26) |
| Strike | From **spot** at signal time, not futures. **ITM, maximum ATM. OTM not recommended** for this strategy (~38:06–38:13). Guest example: ATM + 1 ITM; or “ITM two” = two strikes ITM if capital allows (~39:01–39:20) |
| Premium stop | Prefer **do not** set stop on option chart; follow futures Supertrend; after 1:1 move, optional cost-to-cost on premium (~39:30–40:40) |
| Delta mapping | Host asks delta; guest analogizes RSI 50–75 in bull market → use **~0.60 to 0.75** (spoken 60–75, then 0.63–0.74 / 0.66). Puts = **negative** of that. Deep >0.74 “not that logical.” Capital: thin capital → nearer ATM (~01:02:42–01:03:50) `[UNCERTAIN_TRANSCRIPT]` |
| Dhan tool | Power Scalper / Super Scalper for option ladder |

---

## Strategy 2 — premium chart Fast/Slow EMA (Dhan Super Scalper)

| field | spoken |
|-------|--------|
| Chart | **Option premium** (ITM/ATM call or put matching strategy 1 direction) |
| TF | Super Scalper **1-minute** (~51:24) |
| Indicators | Fast EMA, Slow EMA, buy/sell levels (Dhan custom; **numeric lengths NOT clearly spoken** — UNKNOWN) |
| Confirm | Triple: futures setup + spot strike + premium EMAs. For **long call**: price **above** fast and slow EMA; buy signal only when fast above slow. Ignore “sell” signals as “sell the call” — they are exits/noise for a long-premium book (~52:45–53:02) |
| Stop on premium | Below **slow EMA** (~51:50–52:06) |
| Target | At least 1:2 if triple confirmation (~52:12–52:20) |

---

## Data requirements

```text
INSTRUMENT: NIFTY / BANKNIFTY / SENSEX index futures (signals) + index options (execution)
EXCHANGE_SEGMENT: NSE F&O for NIFTY/BANKNIFTY; BSE for SENSEX
CALCULATION: VWAP, VWMA(20), Supertrend(10,3) on **futures** 3m — NOT cash index volume
TIMEFRAME: 3m futures; 1m option premium; skip 09:15–09:45; flatten < 15:15
```

---

## Not extracted as rules

- 24%/100-point anecdotes (~29:55, 41:30).
- “Bots do FII trading” (~01:07:40) — rhetoric, not a testable rule.

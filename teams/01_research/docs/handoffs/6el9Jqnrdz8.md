# SOURCE_FACT — 6el9Jqnrdz8 (option **selling** / hedge)

**Status:** `EXTRACTED`. `DRAFT`. Layer A only.  
**Phase-1 product is CE/PE buy-first.** This video is **selling + hedge**. Keep as corpus; do not silently convert into a buy strategy.

| Field | Value |
|-------|--------|
| video_id | `6el9Jqnrdz8` |
| title | Hedge Like a Pro: 100% FREE Option Selling Masterclass (Hedging Strategy) \| Dhan |
| url | https://www.youtube.com/watch?v=6el9Jqnrdz8 |
| retrieved_at | 2026-08-31T03:16:36Z (approx; see file header) |
| language | hi ASR |
| transcript | `data/transcripts/normalized/6el9Jqnrdz8.md` |
| english | `ENGLISH_PENDING` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |

---

## High-level spoken claims

| claim_id | ts | claim |
|----------|-----|--------|
| SELL-C01 | 00:34–00:39, 22:30–22:32 | Option seller plays probability; spoken “70% times seller will win” `[UNCERTAIN_TRANSCRIPT]` |
| SELL-C02 | 09:40–12:09 | Naked selling needs large margin; hedge reduces margin (example ₹2 lakh → ₹60k) `[UNCERTAIN_TRANSCRIPT]` |
| SELL-C03 | 20:03–20:28 | OTM long has ~0 intrinsic; theta eats buyer; speaker “gives 10%” to buyer then still theta `[UNCERTAIN_TRANSCRIPT]` |
| SELL-C04 | 21:29, 05:47–05:54 | 7% profitable framed as sellers; 100 buyers vs 100 sellers anecdote |
| SELL-C05 | 23:56 | “Option sellers eat like an ant and shit like an elephant” (tail-risk proverb) |
| SELL-C06 | 32:02, 33:10–33:13 | Gap risk: NIFTY 200 pts in 1 min; BANKNIFTY 17 Jan (year ASR 204) gap down 1600 pts `[UNCERTAIN_TRANSCRIPT]` year |
| SELL-C07 | 39:03–39:17 | Collateral margin can fund selling; **not** option buying |
| SELL-C08 | 41:38–41:52 | NIFTY expiry spoken as **Tuesday**; enter Monday into **next** Tuesday (bi-weekly label because of that one day) |
| SELL-C09 | 59:11–59:43 | Weekly BANKNIFTY expiry removed (Nov ASR 204); BANKNIFTY “only monthly” now — **dated; re-verify** |
| SELL-C10 | 01:00:04 | Same structure claimed usable on NIFTY and BANKNIFTY if product exists |

---

## Strategy as spoken (weekly NIFTY, Monday 09:45)

| field | spoken |
|-------|--------|
| Underlying | NIFTY |
| Style | Positional ~4–5 days; **Monday 09:45** entry; hold to **Friday** exit; **no weekend carry** |
| Expiry | Next week’s Tuesday expiry (“buy weekly” because Monday→next Tuesday) |
| Target / stop | **1% of capital** target and **1%** stop, **fixed**; no chart adjustment (~42:38–42:45) |
| Structure (spot 26000 example) | Buy 1 lot **200 pts OTM** call (26200); sell **3 lots** 400 pts OTM (26400); buy **2 lots** hedge 600 pts OTM (26600) → **1×3×2** fully hedged (3 long / 3 short) |
| Execution | Basket: buys first then sell for margin benefit |
| Margin spoken | ~₹1.3–1.4 lakh per “one lot” unit `[UNCERTAIN_TRANSCRIPT]` |
| Target ₹ | ~₹1300–1500 per lot `[UNCERTAIN_TRANSCRIPT]` |
| Brokerage anecdote | ~₹60 buy + ₹60 sell `[UNCERTAIN_TRANSCRIPT]` |
| Strike hygiene | Avoid 50-point strikes; if spot 26350, treat next 100-strike as ATM (~45:21–45:44) |
| POP spoken | >80–85% `[UNCERTAIN_TRANSCRIPT]` — **education claim, not our backtest** |
| Adjustments | None in base rule |
| Gamma | Avoid 0 DTE / 1 DTE because gamma risk (~46:23–46:28) |

**Unlimited-risk ratio converted to defined-risk by wings.** Still **selling**, not Phase-1 buy-first.

---

## Data requirements

NIFTY option chain, lot size **from exchange file at trade date**, margins, bid/ask for 3-leg basket, Tuesday expiry calendar **as-of**.

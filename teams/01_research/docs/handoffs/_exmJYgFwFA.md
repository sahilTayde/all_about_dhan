# SOURCE_FACT — `_exmJYgFwFA` (option selling)

**Status:** `EXTRACTED` (layer A). `DRAFT` / `WAITING_FOR_EDIT`.  
**Phase-1 product is CE/PE buy-first.** This video is **selling + hedge + OI**. Keep as corpus. Do not convert into a buy strategy.

| Field | Value |
|-------|--------|
| video_id | `_exmJYgFwFA` |
| title | FREE 1-Hour Masterclass on OPTION SELLING \| Option Trading Strategy \| Dhan |
| url | https://www.youtube.com/watch?v=_exmJYgFwFA |
| retrieved_at | 2026-09-01T19:57:00Z |
| language | en (`youtube_translate` from hi) |
| transcript | `data/transcripts/normalized_en/_exmJYgFwFA.md` |
| english_status | `ENGLISH_VERIFIED` |
| qa_flags | `UNCERTAIN_TRANSCRIPT` |
| relevance | HIGH / OPTIONS, GREEKS, RISK_MANAGEMENT, STRATEGY_DESIGN |
| guests | Host + Himanshu Arora (sequel to HAUSZx buying class) |

**No invented quotes.** Numbers `[UNCERTAIN_TRANSCRIPT]` unless trivially restated.

---

## Topics (from transcript)

OPTIONS, OPTION_SELLING, THETA, IV, DELTA, MARGIN / VAR, OI, CHANGE_IN_OI, HEDGE, SPREADS, NIFTY (chain examples), STOCKS (Eternal, Bajaj Auto — **not index-only**).

---

## Claims (SOURCE_FACT)

| claim_id | timestamp | claim (paraphrase of English) | type | confidence |
|----------|-----------|-------------------------------|------|------------|
| EXM-C01 | 04:12–05:32 | Call buyer needs a large enough up-move. Call seller can profit if up-small / flat / down. Buyer benefit “less than 1/3”; seller “more than two thirds.” Buyer P(win) “not more than 1/3” / “less than 30%” / “<3 of 10.” Depends on premium and vol. | education / opinion | medium; `[UNCERTAIN]` percents |
| EXM-C02 | 05:40–08:06 | Buy = profitability (rare, large). Sell = probability (often, smaller). Seller aims to win in **two of three** directions. | education | high |
| EXM-C03 | 08:31–09:47 | Seller thesis: “Nifty will not go above this level” → sell that call. Wants premium → 0 at OTM expiry. Profit capped at premium; loss unlimited. | education | high |
| EXM-C04 | 10:55–11:13 | Budget / election: selling painful. IV friend of buyer, enemy of seller. | education | high |
| EXM-C05 | 13:40–14:49 | Theta = d(premium)/d(time); seller’s “biggest friend.” Same-day expiry chain: OTM LTP 5–10 paise treated as ~0. If spot stays ~24793, next-week OTM premia (178/151/…) also → 0. `[UNCERTAIN]` | education + screen | medium |
| EXM-C06 | 15:23–17:30 | Buyer max loss ≈ premium (₹100 × lot **75** → ₹7500). Seller needs exchange **VAR / “war” margin** (vol-based; “99% of days”). Screen: buy margin 9672 vs sell 5535; deep OTM buy ₹143 vs sell ₹124793 “100s of times.” `[UNCERTAIN]` all rupees / lot 75 **dated** | example | low |
| EXM-C07 | 19:45–21:00 | Wrong product: buying a call only because you cannot afford to sell the put. High conviction → buy CE/PE; low conviction “won’t crash” → put sell. 93% cited again. | opinion | medium |
| EXM-C08 | 21:01–21:22 | Naked “₹ lakh margin” is a myth if hedged; can bring to ~1/4 or 50–60k / <50k. `[UNCERTAIN]` | hedge | medium |
| EXM-C09 | 22:10–22:38 | Seller only needs “market not go too far against me.” Basic S/R, PA, Fibonacci, or indicators enough **if** backtested. Not “anyone can do it.” | opinion | high |
| EXM-C10 | 29:21–34:07 | Assumption: institutions smarter / more capital. Highest OI + rising OI on a call ≈ resistance they will defend; same on puts ≈ support. Screen NIFTY ~24790; 25k / 25500 / 26k / 23500 / 24k OI lakh-figures. Israel–Iran, Fed, tariffs, “18% from bottom.” **Ephemeral + dated.** `[UNCERTAIN]` | OI heuristic | low (snapshot) |
| EXM-C11 | 36:30–36:54 | Theta decay not linear; steeper near expiry (“exponential”). | education | high |
| EXM-C12 | 39:21–40:37 | Naked unlimited risk. Speaker: **7/10** selling trades in **calls**, **3/10** in **puts** (crash / lower-circuit asymmetry). If naked, prefer call sell vs put sell. If hedged, either. **Not a tested win rate.** | opinion | medium |
| EXM-C13 | 42:39–46:10 | **Stock** setup: Williams %R (default **14**; “increase parameter” — “140” spoken `[UNCERTAIN]`); bands −20/−80 and extreme −5/−95. Then MA 10/30/100; also “below 300.” Hourly. Sell call ~**5%** from recent swing high. Target **3% of capital deployed** — speaker **refuses** return promises; attacks 20%/month screenshots. | rule-as-spoken | medium |
| EXM-C14 | 48:01–50:30 | Bajaj Auto ~8500; sell 9000 call (~5%); near-week expiry thin so next month; Mon/Tue margin note. Naked ~93k vs hedged ~52k; max loss defined ~32k. Profit if down / flat / modest up. **Stock F&O.** `[UNCERTAIN]` | example | low |
| EXM-C15 | 52:52–54:56 | Why options: trade the **index** (via FUT/OPT); profit in falls; leverage; **hedging**. Hedge = buy a **cheaper** option than the short (caps loss). Names iron condor, bull/bear call/put spreads. Full hedge hour deferred. | education | high |
| EXM-C16 | 55:19–55:50 | Practice / paper / forward-test first; selling uses more capital; loss can be huge. OT Web to build/track. | process | high |

---

## Indicators (params as spoken)

| Name | Params as spoken | TF | Use |
|------|------------------|----|-----|
| Williams %R | Default 14; speaker “increases” — “140” `[UNCERTAIN]` | hourly (stock) | overbought for call sell |
| SMA/EMA stack | 10, 30, 100 (and 300 conflict) | hourly | trend not-bullish |
| RSI, CCI | named as alternate oscillators | n/a | named only |

---

## Options mapping spoken

NIFTY chain for OI/theta education. Execution examples are **stocks** (Bajaj Auto, Eternal). Index named as something you trade via futures/options. Expiry weekly/monthly. OTM short + further-OTM long hedge. Greeks: theta emphasized; delta named, not parameterized for the sell.

**Strike: do not assume ATM. Speaker’s sell is ~5% OTM on the stock example.**

---

## Data requirements

```text
DATA_SOURCE: DhanHQ / exchange (later)
INSTRUMENT: index options (project) vs speaker stock F&O examples
EXCHANGE_SEGMENT: NSE for NIFTY examples
CALCULATION: OI + COI on chain; Williams %R + MA on underlying hourly
TIMEFRAME: hourly for the stock sell; chain = current + next expiry
```

Lot 75 and all rupee margins = **dated examples**. Never freeze.

---

## What this video is NOT

- Not a NIFTY/BANKNIFTY/SENSEX-only sell book (stock examples dominate the “strategy” half).
- Not a backtest. Screen-day OI and Israel/Fed tape are one session.
- Not Phase-1 buy evidence. 04 may park as WAITING sell (`UNVALIDATED`) — **no new STRAT ID required.**

---

## Handoff to 02 / 03

Validate: VAR/SPAN vs “war margin”; theta non-linearity; OI-as-S/R; Williams 14 vs 140; lot 75. Re-verify expiry weekdays and index vs stock option liquidity.

# CAS_FROM_DHAN_VIDEOS — spoken English vs Closing Auction Session

**Team:** 01_research  
**Date:** 2026-09-03  
**Layer:** `SOURCE_FACT` only. Not `VALIDATION`. Not `HYPOTHESIS`.  
**Status:** `EXTRACTED` / `DRAFT`. Gate: **not** `RESEARCH_READY_FOR_PROGRAMMING`.  
**Corpus:** `data/transcripts/normalized_en/` (`tlang=en`). OPTIONS_INDEX packet checked for false “15:35” clock hits. Hindi packets **not** overwritten. **No invented quotes.**

**CAS** here means NSE **Closing Auction Session** (cash close matching / indicative equilibrium), **not** Chartered Accountants, **not** RSI “equilibrium,” **not** morning pre-open.

Official CAS rules, 15:15–15:35 window, and indicative index stay **03_phd_market VALIDATION** (exchange pages). This file only answers: did a Dhan HQ English caption **name** that mechanism?

---

## Verdict

**DATA_INSUFFICIENT for DHAN-DERIVED CAS recipes.**

No English transcript in this corpus names **Closing Auction Session**, **CAS** (as the auction), **15:15–15:35 equilibrium**, or **indicative index**. Do not teach CAS from `@DhanHQ` videos. Do not map STRAT-009 flatten-15:15 or BTST 15:15–15:30 to auction matching.

---

## Searched (all `normalized_en/`)

| query | result |
|-------|--------|
| `closing auction` / `call auction` / `auction session` | **zero** hits |
| `\bCAS\b` | one hit: `6el9Jqnrdz8` “If they are **CAs**” = Chartered Accountants (~09:57) |
| `indicative index` | **zero** |
| `equilibrium` | RSI **50** “equilibrium or neutral zone” (`_byuht38r5s`) — oscillator, not auction |
| `pre-open` / `preopen` | **morning** pre-open / 9:08 data (`G31RFueZLvk`, `ZoCD4fLKy6M`) |
| spoken clock **15:35** / **15:40** / **3:35** / **3:40** as session | **not found** (those strings are almost all **caption timestamps**) |
| `indicative` | `2RnBT9DDDNI` NIFTY **spot volume** is not indicative of how much NIFTY traded |

`OPTIONS_INDEX_PACKET.md` **HAUS-EN-07** `15:35–16:42` is a **video timestamp range** (expiry education), not a CAS clock.

---

## Bind table (what *was* spoken, and what it is not)

| claim sought | video_id | EN timestamp | paraphrase of English | bind | notes |
|--------------|----------|--------------|------------------------|------|-------|
| Closing Auction Session / CAS named | — | — | — | **NOT_IN_EN** | No recipe. `DATA_INSUFFICIENT` for DHAN-DERIVED CAS. |
| 15:15–15:35 equilibrium / matching | — | — | — | **NOT_IN_EN** | Nobody describes an auction book or equilibrium price in that window. |
| Indicative index | — | — | — | **NOT_IN_EN** | — |
| Flatten **before 15:15** (intraday option buy) | `2RnBT9DDDNI` | 23:48–24:06 | Ignore 09:15–09:45; start after 09:45; cut all positions from **3:15**; intraday, not BTST. | **CONFIRMED** as **STRAT-009 clock**, **NOT_IN_EN** as CAS | Same speaker later: “A real trader thinks his game is at **3:30** It's over” then homework **3:30 to 9:15** (~56:39–56:47) — practice after cash close, not auction. |
| Indian session **09:15–15:30** = 75 five-minute candles | `DzT_681GThA` | 18:20–18:25 | “between **9:15 to 3:30**, 75 candles are formed in the Indian markets on a 5-minute chart.” | **CONFIRMED** as **continuous-session length**, **NOT_IN_EN** as CAS | Demo is Reliance. 15:30 as spoken cash/F&O continuous close — **VERIFY** vs circular on 03. |
| Intraday **09:15–15:30** | `2YBmiyVmNNw` | 13:18–13:21 | “intraday **9:15 to 3:30** and thereafter Swing research.” | **CONFIRMED** as session habit | Not auction. |
| Last-minutes **BTST** buy ~15:15, wait to **15:30** | `IvSnlbt89yw` | 00:04–00:27, 13:34–13:44 | Buy stocks ~10 minutes before close; purchase at **3:15** can still hit SL **before 3:30**. Execute by 3:15; “**Wait till 3:30**” then next-day 09:15–10:00 exit. After **3:25** “hands might start shaking.” | **CONFIRMED** as **equity BTST last-print**, **NOT_IN_EN** as CAS | Title: *How to Find BTST Stocks at 3:15 PM*. Continuous session, not closing-auction matching. |
| Same-day exit **before 15:30** (BTST / stock options) | `G31RFueZLvk` | 00:17–00:20, 33:19–33:40 | “Same day before **3:30** He will give you good returns.” “You will have to pay before **3:30 pm** on the same day.” Trade even “at the same time as the **market closing time**.” | **CONFIRMED** as **15:30 close language**, **NOT_IN_EN** as CAS | Stock / BTST. F&O 15:30 vs 15:40 still **03 VERIFY**. |
| Next-morning **pre-open** for overnight exit | `G31RFueZLvk` | 01:03:13–01:03:43 | Cut at **9:15** / **9:18**. “**Find out in the pre-open market** what is going to happen to my stock.” Exit by **9:18 or 9:20**. | **CONFIRMED** as **morning pre-open**, **NOT_IN_EN** as CAS | Opposite end of the day from closing auction. |
| **9:08 / 9:20** pre-market sector/stock data | `ZoCD4fLKy6M` | 00:41–01:32, 01:54–02:35 | Times that matter: “before the market opens and at **9:20**.” “**9:08 am** and **9:20 am**.” Block deals **8:45–9:00**. Bets **9:00–9:07**. “On **98**, NSC releases the first data” on sector/stock gap. | **CONFIRMED** as **NSE morning pre-open / 9:08 print**, **NOT_IN_EN** as CAS | Equity scan. Catalog `STOCK_ONLY`. |
| Opening range **09:15–10:00** | `eApl0SfVBBY` | 05:44–05:51 | “for me the time from **9:15 to 10:00** is the opening range.” | **CONFIRMED** as **ORB**, **NOT_IN_EN** as CAS | Morning box. |
| RSI “equilibrium” ~50 | `_byuht38r5s` | 04:30–04:33 | “nor should it be above the **equilibrium zone**. The zone of **50** is our equilibrium or neutral zone.” | **CONFIRMED** as **RSI 50**, **NOT_IN_EN** as CAS equilibrium | Intraday stock screener. |
| “Indicative” volume | `2RnBT9DDDNI` | 18:49–18:52 | NIFTY spot “volume is **not indicative** of this. How much trading is happening in NiFi.” | **CONFIRMED** as **cash-index volume pitfall**, **NOT_IN_EN** as indicative **index** (CAS) | Already in OPTIONS_INDEX. |
| Friday **15:15** EOD (sell book) | `6el9Jqnrdz8` | 52:50–52:58 | If not profitable by Friday, “Friday will be cut off after EOD.” “**Friday at 3:15 pm** with Strategy We will exit.” | **CONFIRMED** as **014 flatten**, **NOT_IN_EN** as CAS | Hedged call ratio, WAITING sell. |
| Shop-hours **3:30 p.m.** metaphor | `_exmJYgFwFA` | 27:12–27:17 | Treat trading as a business: open 5:15 am, “At least **3:30 p.m.** Let's close the shop.” | **WEAK** | Metaphor, not a matching-session spec. |
| “Nifty is a **6-hour** trading session” | `wpdqqXhhq88` | 15:15–15:18 | “Because Nifty is a 6-hour trading session.” (vs crypto 24h; speaker using 1h chart) | **WEAK** | Session-length anecdote. Does **not** name 15:15–15:35 auction. 9:15–15:15 = 6h; not proven as CAS. |
| Commodity after **15:30** | `dYva2rO1LOw` | title + 00:00–00:10 | Title: *Trading Doesn't Stop at **3:30 PM**! Commodity Trading.* “Your market does not close in the afternoon.” | **CONFIRMED** as **MCX after NSE cash**, **NOT_IN_EN** as CAS | Promo. Not index-option CAS. |

---

## What 03 / 04 / 05 must not do

- Invent a Dhan-video CAS playbook.  
- Relabel STRAT-009 15:15 flatten, IvSnl/G31 15:30, or ZoCD 09:08 as Closing Auction Session.  
- Use product **CasPanel** / desk CAS analyst as transcript evidence (those are **03 / 07**, not 01 SOURCE_FACT).  
- Collapse this `DATA_INSUFFICIENT` into a coded edge.

**03** owns official CAS (exchange). **01** has no DHAN-DERIVED CAS recipe to hand off.

---

## HANDOFF (01)

**Accepted:** English corpus searched. CAS / closing auction / indicative index / 15:15–15:35 equilibrium **not spoken**. Morning pre-open (ZoCD, G31) and 15:15/15:30 **continuous-session** clocks are spoken and tagged as such.

**Rejected:** Treating 15:15 flatten or BTST 15:15–15:30 as auction matching. Inventing quotes.

**UNKNOWN / DATA_INSUFFICIENT:** Any DHAN-DERIVED CAS equilibrium / indicative-index rule. F&O 15:30 vs 15:40 remains 03.

Review: n/a. Not `RESEARCH_READY_FOR_PROGRAMMING`.

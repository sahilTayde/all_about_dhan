# CAS research — what the term means (Indian cash + index)

**Date:** 2026-09-01  
**Layer:** `SOURCE_FACT` + `VALIDATION` (this file). Daily bias is `HYPOTHESIS` / `UNVALIDATED`.  
**Do not freeze a single expansion if new circulars contradict.** Re-read NSE/BSE/SEBI before treating any clock as eternal.

This note is the first pass from **official exchange pages and circulars**, plus broker explainers and launch-week press. No live orders. No invented win rates.

---

## Working verdict (2026-09-01)

| Tag | Expansion | Official? | Can it flip NIFTY / BANKNIFTY / SENSEX? |
|-----|-----------|-----------|------------------------------------------|
| **CAS** | **Closing Auction Session** | **Yes — NSE, BSE, SEBI (2026)** | **Yes.** Official close of F&O cash stocks is an equilibrium auction, not last-30-min VWAP. Index close is built from those stock closes. Launch-week press: Nifty ~200 pts vs the 15:15 print. |
| PRE_OPEN | Pre-open **call auction** (cash; F&O pre-open aligned later) | Yes — older SEBI/NSE; 2026 timing tweak | Open gap / open print. Related microstructure, **not** the 2026 “CAS” acronym. |
| PCA / PCAS | **Periodic call auction** (illiquid / ESM) | Yes — NSE 2013+ | **No** for these indices. F&O names are excluded from illiquid PCA. |
| POST_CLOSE | Post-close / legacy “closing session” | Yes — NSE 2003+; clock moved after CAS | Trades **at** the already-discovered close. Does not rediscover the index close. |
| CASH_BASIS | Trader nickname “cash” vs F&O | Informal | Basis / cash-futures volume can lean the close, but **“CAS” on nseindia.com is not this.** Track as overlay only. |

**Primary object of this analyst:** `CLOSING_AUCTION_SESSION` (official **CAS**).  
**Also tracked, clearly tagged:** `PRE_OPEN`, `PCA`, `POST_CLOSE`, `CASH_BASIS`.

If a later circular renames the session, update this table. Do not silently treat PCA or “cash market” as CAS.

---

## 1. Closing Auction Session (CAS) — official

### NSE product page (fetched 2026-09-01)

- URL: [https://www.nseindia.com/static/products-services/closing-auction-session](https://www.nseindia.com/static/products-services/closing-auction-session)
- Page updated on the site: **12/08/2026**.
- **Phase 1 applicability:** cash-segment stocks **on which derivative contracts are available**.
- **Clock (all trading days):** separate **20-minute** session **15:15–15:35 IST**.

| Phase | IST | What happens |
|-------|-----|----------------|
| Reference / CTS → CAS | 15:15–15:20 | Continuous trading for CAS names has ended. Reference price = **VWAP of 15:00–15:15** trades. |
| Order entry (MKT + LMT) | 15:20–15:25 | Entry / modify / cancel limit **and** market. |
| Order entry (limit only) | 15:25–15:30* | Limit only. **No** market entry / modify / cancel. *System **random close in the last 2 minutes** (≈15:28–15:30). |
| Match + confirm | 15:30–15:35 | Match starts when order-entry ends. Single **equilibrium** price. |
| Buffer | 15:35–15:50 | Transition to post-close. |
| Post-close | 15:50–16:00 | Same post-close mechanics; **clock shifted**. |

**Non-CAS cash:** continuous **09:15–15:30**.  
**Equity derivatives:** **09:15–15:40** (NSE CAS page + NSE market-timings page).

**Close rule (CAS names):** equilibrium price (max executable volume). If no equilibrium: **reference price**. If no trade that day: prior close.

**Band:** **±3%** from reference. Stop-loss and iceberg **not** allowed in CAS. Unexecuted CTS limits inside the band **carry** (except SL / iceberg / outside band).

**Equilibrium tie-break (NSE page):** max volume → min |imbalance| → closest to reference → if reference is the midpoint, use reference. Market + limit both count.

**Disseminated during CAS (NEAT / MBP):** indicative equilibrium, tradable qty, cumulative buy/sell, imbalance at IEP, market-order imbalance, **indicative index**.

### NSE circulars (listed on the official CAS page)

| Date | Ref | Subject |
|------|-----|---------|
| 2026-01-19 | NSE/CMTR/72394 | Introduction of CAS in equity cash + pre-open modifications |
| 2026-03-18 | NSE/CMTR/73362 | Operational guidelines / SOP |
| 2026-04-22 | NSE/CMTR/73845 | Security-master file changes (CAS flag) |
| 2026-05-29 | NSE/CMTR/74466 | Trading modalities (cash) |
| 2026-05-29 | NSE/FAOP/74467 | Derivatives-segment timing / modality changes |

Mirror of **74466** (same text as member circular; not a substitute for nseindia.com download):  
[https://www.canmoney.in/pdf/CMTR74466-CAS.pdf](https://www.canmoney.in/pdf/CMTR74466-CAS.pdf)

**74466 facts used here:** live from **Monday 3 August 2026**. CAS skipped if an **index circuit** ends the day early (then last-30-min VWAP / LTP as before). Market type `"N"`, book `RL`. Unexecuted CAS orders **cancelled** after match. CAS trades **cannot** be cancelled. Security master gets a **CAS-eligible** flag.

NSE FAQ attachment (member download, listed on Continuous Markets FAQs, page updated **25/08/2026**):  
[https://www.nseindia.com/static/trade/continuous-markets-FAQs](https://www.nseindia.com/static/trade/continuous-markets-FAQs) — row *“Closing Auction Session (CAS) in Equity segment(CM) and changes in Equity Derivatives(F&O) Segment”*.

### NSE market timings (fetched 2026-09-01)

- URL: [https://www.nseindia.com/static/market-data/market-timings](https://www.nseindia.com/static/market-data/market-timings)
- Page **Updated on: 04/08/2025** — **stale vs CAS.** Still shows Normal/Odd-lot close **15:30**, Closing session **15:40–16:00**, Call-auction illiquid 6×1h, Equity derivatives close **15:40**.
- **VALIDATION:** do **not** treat this table as the CAS clock. Use the CAS product page + 74466 for F&O-cash names (CTS **15:15**, CAS **15:15–15:35**, post-close **15:50–16:00**). Derivatives **15:40** is consistent across CAS page and this timings page.

### SEBI

- Circular **SEBI/HO/47/11/11(3)2025-MRD-POD2/I/2765/2026** dated **16 January 2026** (cited by BSE notice 20260610-41 and legal commentary).  
  PDF not archived in this repo yet — **VERIFY** on sebi.gov.in before quoting clause numbers in code.

### BSE (SENSEX)

- Notice **20260610-41** (10 Jun 2026): *Introduction of Closing Auction Session in the Equity Segment – Detailed Operating Guidelines*.  
  [https://www.bseindia.com/downloads/UploadDocs/Notices/20260610-41/20260610-41.pdf](https://www.bseindia.com/downloads/UploadDocs/Notices/20260610-41/20260610-41.pdf)
- Same Phase-1 idea: stocks with derivatives (BSE exclusions: CDSL, BSE itself unless BCP). Same 15:15–15:35 skeleton. Non-CAS CTS to 15:30; post-close **15:50–16:00**.
- BSE disseminates the same indicative package **including Indicative Index**, and says it is on the exchange site under **“Closing auction session”**.
- Launch-day press (secondary): [Hindu Business Line, 3–8 Aug 2026](https://www.thehindubusinessline.com/markets/bse-launches-closing-auction-session-market-stays-stable-on-day-one/article71303857.ece) — SENSEX **−0.048% vs 15:15 reference** on day one; 400+ members, 200+ scrips. **Not** a volatility proof.

### Why this can “flip” the index

Official + launch-week clarification:

1. **Index close ≠ 15:15 LTP.** Close is the **CAS equilibrium of constituents** (Nifty/Sensex/Bankex names that are F&O-cash).
2. **15:15–15:30 there is no continuous matching** on CAS stocks. Charts that paint last-traded look **flat**, then print the auction.
3. NSE said the graph must be read as **indicative equilibrium / indicative index**, not a sudden cash tape. Sources:  
   - [Economic Times](https://economictimes.indiatimes.com/markets/stocks/news/niftys-value-doesnt-change-suddenly-at-330-pm-nse-clarifies-amid-cas-confusion/articleshow/132850802.cms)  
   - [News18](https://www.news18.com/business/markets/nse-explains-200-point-nifty-spike-during-closing-auction-says-no-sudden-jump-in-index-ws-l-10250514.html)
4. **Two order books (NSE vs BSE)** ⇒ stock closes and **index prints can differ** across venues.
5. **Expiry / settlement / NAV / pledge / index funds** use the official close. A large auction imbalance in a few heavy weights moves **index points** even if the 15:15 tape was quiet.
6. **F&O still trades until 15:40** while cash CAS is discovering the close — cash/futures **basis** can gap in that window.

This is the mechanism the user described as a “hidden” close that can flip NIFTY / BANKNIFTY / SENSEX.

---

## 2. Pre-open call auction — related, not CAS

- NSE periodic-call page also restates **pre-open call auction** for non-illiquid scrips:  
  [https://www.nseindia.com/static/products-services/equity-market-periodic-call-auction](https://www.nseindia.com/static/products-services/equity-market-periodic-call-auction)
- NSE timings page: regular pre-open **09:00**, close shown **09:08** (pre-2026-alignment table).
- **2026 alignment:** SEBI/NSE moved pre-open toward the CAS-style random close. Broker explainers (not circular PDFs in-repo): cash/F&O pre-open **random close 09:08–09:10**, match ~09:10–09:12, buffer to 09:15, **effective 7 September 2026**.  
  Example: [Upstox learning note](https://upstox.com/learning-center/share-market/what-is-a-pre-open-market-session-in-the-stock-market/article-1659/).
- Tag daily notes **`PRE_OPEN`**, never **`CAS`**.

---

## 3. Periodic call auction (illiquid) — not index CAS

- Official: [https://www.nseindia.com/static/products-services/equity-market-periodic-call-auction](https://www.nseindia.com/static/products-services/equity-market-periodic-call-auction)
- Live watch: [https://www.nseindia.com/market-data/stocks-in-call-auction](https://www.nseindia.com/market-data/stocks-in-call-auction)
- **Hourly** sessions from **09:30**; illiquid / ESM names. Surveillance circulars exclude **securities having derivative products**.
- **Cannot** be the Nifty/Banknifty/Sensex flip tool. Tag **`PCA`**.

---

## 4. Legacy post-close / “closing session”

- NSE equity-segment page (historical closing session **15:40–16:00**, market orders **at** the close):  
  [https://www.nseindia.com/static/products-services/equity-market-segment](https://www.nseindia.com/static/products-services/equity-market-segment)
- After CAS, post-close is **15:50–16:00** (74466 / BSE 20260610-41). Tag **`POST_CLOSE`**.

---

## 5. “Cash” as a trader nickname

Some desks say “watch the cash” for cash-segment vs futures. That is **`CASH_BASIS`**: cash vs futures volume, premium/discount into 15:15, then F&O trading through 15:40 against a cash auction.

**Not** what NSE prints as **CAS**. Do not collapse the two.

Broker explainer (secondary, useful for retail clocks, not a circular):  
[Zerodha — What is SEBI's Closing Auction Session (CAS)](https://support.zerodha.com/category/trading-and-markets/trading-faqs/general/articles/closing-auction-session)

Zerodha (and similar) correctly state: CAS close feeds **Nifty / Sensex**, **NAV**, **F&O settlement**, **P/L marks**, **pledge**. GTT/alerts on F&O **stocks** stop at **15:15**; futures/options alerts to **15:40**.

---

## 6. What we still do not have in-repo

| Gap | Status |
|-----|--------|
| Official SEBI PDF + NSE 72394/73362/73845/74467 binaries | **TODO** — cite from exchange download, do not invent clauses |
| Live indicative-index / imbalance tape (DhanHQ) | **DATA_INSUFFICIENT** — no documented Dhan “CAS book” REST found in this workspace |
| Constituent weights for today’s Nifty/Banknifty/Sensex | **VERIFY** from NSE/BSE index files; never hardcode |
| Day-1 200-pt Nifty print as a **repeatable edge** | Press only. **UNVALIDATED**. Not a win rate. |
| NSE market-timings HTML vs CAS clocks | **Conflict** — timings page last updated 04/08/2025 |

---

## 7. Implications for this desk (VALIDATION, not a strategy)

- **Do not hardcode 15:30 as F&O close.** Equity derivatives: **15:40** (NSE CAS page + timings). Cash CAS names: CTS **15:15**.
- **Index “spike” at 15:30** may be **auction discovery**, not a continuous-trend continuation.
- **Monthly / weekly expiry settlement** of stock F&O (and index marks that use the cash close) is **CAS-sensitive**.
- **SENSEX** needs **BSE** CAS / indicative index, not NSE-only.
- Nightly `cas_calls[]` learn patterns. Proposals stay **`BACKTEST_REQUIRED`**. Never auto-retune.

Methodology: [`METHODOLOGY.md`](METHODOLOGY.md). Daily notes: [`notes/`](notes/). Call JSON: [`calls/`](calls/).

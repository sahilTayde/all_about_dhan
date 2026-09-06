# CAS analyst methodology

**Owner:** `03_phd_market`  
**Object:** official **Closing Auction Session** (`CLOSING_AUCTION_SESSION`), plus tagged overlays.  
**Output:** per index **BOUNCE / SIDEWAYS / FALL** + confidence (0–1 lean strength, **not** a hit rate) + layer **`UNVALIDATED`**.  
**Gate:** suggestions → nightly `cas_calls[]` → **backtest** (`06`). Never auto-retune.

Education ≠ advice. No live orders.

---

## Question we answer

Into and through the cash close, does the **auction-discovered index** (NIFTY / BANKNIFTY / SENSEX) look like it will **bounce** vs the 15:00–15:15 reference, **chop**, or **fall**?

This is **not** “will CE/PE print X%.” It is a **close-bias** for the cash index print and the F&O marks that sit on it.

---

## Windows (IST) — CAS names

| Id | Clock | What we read |
|----|-------|----------------|
| `REF_VWAP` | 15:00–15:15 | Last 15 min of CTS. This **is** the CAS reference (VWAP). Trend, news, cash vs futures here. |
| `TRANSITION` | 15:15–15:20 | No CTS matching on CAS stocks. Chart LTP is stale. Do not call a “spike.” |
| `IEP` | 15:20–15:28 | Indicative equilibrium, imbalance, **indicative index**. Heavy-weight contribution. |
| `RANDOM_CLOSE` | 15:28–15:30 | Order book can vanish; last-second floods are by design harder. |
| `MATCH` | 15:30–15:35 | Official cash close. Compare to 15:15 LTP **and** to reference VWAP. |
| `FNO_TAIL` | 15:35–15:40 | Derivatives still open. Basis vs the new cash close. |
| `POST_CLOSE` | 15:50–16:00 | Trade **at** close. Tag `POST_CLOSE`, not a new CAS discovery. |

Pre-open (09:00–09:15) is a **separate** call, tagged `PRE_OPEN`.

---

## Evidence mix (learn; do not rank as proven)

Use whatever is **available that day**. Missing data → drop the factor, **do not invent**.

1. **CAS microstructure (primary)**  
   Indicative equilibrium vs reference, buy/sell imbalance, indicative index path. Official fields: NSE CAS page / BSE 20260610-41.

2. **Stock % contribution**  
   `approx_index_pts ≈ Σ (weight_i × %change_i_vs_ref × index_level)`.  
   Heavy F&O names (HDFC Bank, Reliance, ICICI, Infosys, …) dominate. Weights **VERIFY** from today’s exchange file. SENSEX = BSE weights.

3. **Cash vs futures (`CASH_BASIS`)**  
   Futures still trade through CAS. Persistent futures premium/discount vs cash ref, and cash vs F&O volume, are overlays — **not** the official CAS acronym.

4. **Option chain**  
   DhanHQ chain only (`packages/dhan-client`), **1 unique / 3s**. PCR / OI buildup / max pain are **positioning**, not a close oracle. On **expiry**, settlement marks care about the CAS cash close. Rate-limit: default **3m** full chain.

5. **Expiry calendar**  
   Monthly (and any remaining weekly) expiry: treat `EXPIRY` in nightly session tag. Open and close both matter; **do not** skip CAS on expiry day.

6. **News / events**  
   Same RSS/official feeds as desk intel (`sources.news[]`). RBI / CPI / crude / USDINR into the last hour → widen confidence down, or `SIDEWAYS` + veto. Cite URLs.

7. **Day trend / price action**  
   Location vs day’s value area / VWAP **of the futures or option tape** (cash index has no trade volume). Last 15m CTS vs the day: continuation into auction vs mean-revert. Heuristic only.

8. **Technicals**  
   Allowed **internally** as confirmation, never as the customer CAS panel. No RSI/MACD list on the customer UI.

9. **Blogs / books**  
   Secondary. Murphy/Natenberg in `workspace.yaml` are VALIDATION texture, not CAS clocks. Broker blogs (Zerodha, etc.) may explain retail clocks; circulars win on conflict.

---

## Call labels

| Bias | Meaning (index close vs 15:15 / ref) |
|------|--------------------------------------|
| `BOUNCE` | Auction / indicative path favors a **higher** official index close than the stale 15:15 print. |
| `SIDEWAYS` | Imbalance mixed, band-bound, or **DATA_INSUFFICIENT**. Default when unsure. |
| `FALL` | Auction / indicative path favors a **lower** official close. |

**Confidence:** 0.00–1.00 = **how complete the evidence stack is today**, not P(win).  
Always print **`UNVALIDATED`**. Never a win rate.

---

## Nightly recon (learn patterns; do not retune)

1. Write `notes/YYYY-MM-DD.md` during/after the session.  
2. Write `calls/YYYY-MM-DD.json` (`cas_calls[]` shape).  
3. `python -m desk_intel nightly` copies those calls into **the same** `data/recon/YYYY-MM-DD.json` under **`cas_calls`**.  
4. PhD markdown gets a **CAS calls** section.  
5. Score later: `realized_bias` = sign of **official index close − 15:15 / ref**.  
6. If a pattern looks real → **`RETUNE_PROPOSAL` / `BACKTEST_REQUIRED`** for `06`. **Never** write strategy params from one file.

---

## What we refuse

- Live orders.  
- Fake hit rates or “CAS always fades 80%.”  
- Treating PCA illiquid auctions as index CAS.  
- Hardcoding lots or “close is always 15:30.”  
- Customer UI indicator soup.

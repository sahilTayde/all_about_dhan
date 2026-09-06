# MISSED_TRADE_POSTMORTEM — lagging Supertrend/MACD vs missed PE

**Team:** 09_review (notes only — **not** a five-pass)  
**Status:** `DRAFT` / `WAITING_FOR_EDIT`  
**Gate:** `RESEARCH_READY_FOR_PROGRAMMING` **not** issued  
**Date:** 2026-09-01  
**Ticket:** [`teams/00_orchestrator/docs/TASK_STAGED_SIGNALS.md`](../../00_orchestrator/docs/TASK_STAGED_SIGNALS.md)  
**Staging spec:** [`teams/04_quant/docs/SIGNAL_STAGING.md`](../../04_quant/docs/SIGNAL_STAGING.md)  
**Persona:** [`teams/00_orchestrator/docs/PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md)

This is a **product-owner case write-up**. It is **not** a reconstructed tape, **not** a fill blotter, and **not** a review pass. Do not invent prices, times, or fills.

---

## Source

**Layer:** product-owner narrative (`SOURCE_FACT` as *what they said*; market numbers below are **not** independently verified).

They were using **Supertrend + RSI + EMA 9 + MACD**. They described a **missed PE** of **~30 pts on 5m**. Supertrend **waited for confirmation**; **after a big red candle** it flipped sell; the **MACD cross came after** the ~30-pt move.

They also wrote: **“put buy on 24100 ce.”**

---

## SOURCE_UNCERTAIN — CE vs PE / strike

Do **not** resolve the instrument without the user.

| Reading | Status |
|---------|--------|
| Intent: **short / PE lean** that lagging TA missed | **Captured** (matches Supertrend sell-flip + missed PE wording) |
| “24100” as a NIFTY (or other) **strike** | `SOURCE_UNCERTAIN` — index, expiry, and session **not** given |
| “put buy” vs “24100 **ce**” | `SOURCE_UNCERTAIN` — could be PE buy **referenced against** 24100 CE (wall/ATM marker), a slip for 24100 **PE**, or a CE ticket that contradicts the PE story |
| ~30 pts = index points vs option premium | `SOURCE_UNCERTAIN` |
| Exact time, underlying print, bid/ask, fill, whether they traded | **Not provided** — **do not invent** |

**No invented fill prices.** No reconstructed OHLC. No “you would have made X.”

---

## What failed (mechanism, not P&L)

| Tool | What the owner described | Staging label (HYPOTHESIS) |
|------|--------------------------|------------------------------|
| Supertrend | Waited for confirmation; flipped **after** the large red candle | Lagging **promote** — too late for **entry** |
| MACD | Cross **after** the ~30-pt 5m move | Same — **CONFIRMED-late** |
| RSI + EMA 9 | In the stack; not described as the first fire | Filters, not a lead in this telling |
| News / option chain | **Not mentioned** in the miss | If the desk had only the canned stack, mix was **incomplete** vs PERSONA_DESK |

**Intent to keep:** lagging TA **missed a short/PE**. A product that only waits for Supertrend + MACD agreement will **systematically** print after the impulse on 5m.

---

## What we will not claim

- That 30 pts were “left on the table” as a fill.
- That an EARLY state **would have** caught this bar.
- That 1-minute lead is proven.
- That 24100 CE or PE was the correct contract.

---

## Product implication (for 04 / UI later)

States **WATCH / EARLY / CONFIRMED / IN-PROGRESS / EXPIRED / VETOED**, color + honesty copy (“not confirmed, wait ~2 min”), 5m ST/MACD as **confirmation not entry**. **IN-PROGRESS** = live after CONFIRMED; then ACHIEVED/STOPPED/INVALIDATED. Quality bar: wrong EARLY can cost the company **up to 30% of capital** in customer penalty — EARLY must not be reckless. Details in SIGNAL_STAGING.md.

**Verdict:** none. Packet remains `DRAFT`. Do not send to 07_coding.

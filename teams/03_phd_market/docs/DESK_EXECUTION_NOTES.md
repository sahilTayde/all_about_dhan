# Desk / production-trader notes (conceptual)

**Status:** `DRAFT`. Not a live playbook. No order-routing. Complements `VALIDATION_MARKET.md`.

---

## Fills

- Education videos assume **you get the LTP**. Live: you pay **ask** to buy, hit **bid** to sell (or worse in a fast tape).
- Index option bid/ask **widens** into the open (09:15–09:45), events, and far OTM. HAUS “nominal gap” is a **filter**, not a guarantee.
- Supertrend “close beyond” on 3m: the **next** 3m open can gap through the theoretical stop. Model **stop slippage** as a fraction of ATR or a fixed index-point shock — do not assume touch fills.
- Premium-chart stops (Gokul warns against resting them) wick more than futures. HAUS same: underlying swing > option LTP stop.

## Slippage / costs

- Round-trip: brokerage + STT (sell-side on options in India — **verify current tax**) + exchange + GST + stamp + **spread**.
- Scalps (2m, 15–25 NIFTY points on futures-equivalent) die first when costs are applied. **Prefer fewer candidates that survive costs** over more entries.
- 1-3-2 selling: 6 contracts of friction per “unit”; ₹120 brokerage anecdote is **not** our cost model.

## Position / risk

- Lot is discrete. You cannot size to 0.37 lots. If 1 lot > risk budget, **no trade** (HAUS: only if RM allows).
- Mapping underlying stop → rupee risk on the option is **UNKNOWN ex ante** (gamma/IV). Desk practice: risk **premium at risk** (long debit) **and** a hard rupee cap.
- Circuit-breaker days: working orders cancelled/queued; do not “assume flatten at 15:15.”
- Overnight / BTST on long options: gap + IV crush. Speakers disagree (HAUS no carry vs optional BTST). **Default Phase-1: flatten same session** unless a candidate says otherwise and review accepts it.

## Buy vs sell (desk)

- Long premium: defined debit, path-dependent; needs **move now**.
- Short premium / spreads: margin, assignment not applicable on European index but **gap** and **margin call** are real.
- Mixed NIFTY vs BANKNIFTY signals: Gokul “avoid the day” is a **risk overlay**, not alpha.

## Implementation realism (later coding)

- Signals on **futures 3m** must not peek the unclosed bar.
- Session clock **IST**, exchange holidays.
- SENSEX on BSE: separate token, lot, strike, expiry.
- Order-flow widgets (DEXT) may **not** be in DhanHQ historical API — `DATA_INSUFFICIENT` for backtest of STRAT-010 until proven.

---

**No profitability claimed.**

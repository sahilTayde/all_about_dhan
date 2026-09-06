# Option-chain metrics (desk intel) — VALIDATION vs HYPOTHESIS

**Status:** `DRAFT`. Complements [`VALIDATION_MARKET.md`](VALIDATION_MARKET.md) and [`DESK_EXECUTION_NOTES.md`](DESK_EXECUTION_NOTES.md).

Used by `packages/desk-intel`. Persona: [`teams/00_orchestrator/docs/PERSONA_DESK.md`](../../00_orchestrator/docs/PERSONA_DESK.md).

These are **definitions**, not a trade. Lot sizes stay VERIFY — never hardcode.

---

## SOURCE / plumbing

- DhanHQ `POST /optionchain` body: `UnderlyingScrip`, `UnderlyingSeg`, `Expiry`. Docs: https://dhanhq.co/docs/v2/option-chain/
- Historical / expired rolling tape: `POST /charts/rollingoption` — [`ROLLING_OPTION.md`](ROLLING_OPTION.md). FNO segment + underlying id (13 / 25 / 51). **Not** this 3m live poll. Data API **5/s**, 30 days/call.
- Live-chain rate limit: **1 unique request / 3 seconds** (OI updates slowly vs LTP). Rollingoption is the **Data API 5/s** bucket — see [`ROLLING_OPTION.md`](ROLLING_OPTION.md).
- Response: `data.last_price`, `data.oc.{strike}.ce|pe` with `oi`, `previous_oi`, `volume`, `greeks`, `security_id`, bid/ask.
- Index options: NIFTY/BANKNIFTY typically `NSE_FNO` quotes; SENSEX `BSE_FNO`. Underlying segment in the chain body is usually `IDX_I`. **VERIFY scrips from the instrument master** (`config/workspace.yaml` `markets[]`).

---

## VALIDATION (what the number is)

| Metric | Definition in this repo |
|--------|-------------------------|
| PCR(OI) | Σ PE OI / Σ CE OI on the snapshot. Undefined if CE OI is 0. |
| PCR(volume) | Same with day volume. |
| ATM | Strike closest to `last_price`. |
| Buildup (morning) | `oi - previous_oi` (Dhan: previous **day** OI). |
| Buildup (3m / 1m) | `oi - last snapshot oi` when `last.json` (or a prior timestamped file) exists. Also PCR Δ and ATM CE–PE Δ vs that snapshot. |
| CE/PE wall | Strike with max CE OI / max PE OI on this expiry sheet. |
| Max-pain stub | Strike minimizing Σ intrinsic × OI if expired at that strike. Ignores lot, discounts, and other expiries. |
| Gamma-load stub | Σ \|gamma\| × OI on ATM±N. **Not** dealer gamma. |

---

## HYPOTHESIS (how operators *talk* — unvalidated)

- CE wall as resistance / PE wall as support.
- Rising CE OI + falling CE premium = writing into the rally (cap).
- Rising CE OI + rising premium = demand / short-cover.
- Extreme PCR as contrarian **without price** is not a signal.
- Pin at max pain into expiry afternoon.

Do not collapse these into SOURCE_FACT. Desk intel fusion treats them as reasons with vetoes, confidence capped.

---

## 1-minute OI

Exchange OI is not a one-second series. Dhan documents the 3s chain cap for that reason. A 1m **full** chain poll is the wrong default. ATM±N via quote/cached ids is the designed path; whether quote JSON includes `oi` is **VERIFY FROM DOCS**.

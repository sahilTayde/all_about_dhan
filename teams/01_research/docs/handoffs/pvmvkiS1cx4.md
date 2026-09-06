# SOURCE_FACT — pvmvkiS1cx4 (2-minute scalping)

**Status:** `EXTRACTED`. `DRAFT`. Layer A. Explicitly **NIFTY / BANKNIFTY / SENSEX** + options.

| Field | Value |
|-------|--------|
| video_id | `pvmvkiS1cx4` |
| title | The 2-Minute Scalping Strategy That Actually Works |
| url | https://www.youtube.com/watch?v=pvmvkiS1cx4 |
| retrieved_at | 2026-08-31T03:17:04Z |
| language | hi |
| qa_flags | none on file (still treat numbers cautiously) |
| speaker | Mukul Choudhary (spoken) |

---

## Rules as spoken

| field | spoken |
|-------|--------|
| Practice | Do not deploy without practice/backtest (~00:21–00:41) |
| Underlyings | NIFTY 50, SENSEX, BANKNIFTY. Analysis on **spot** (easier backtest); **execution on options** (~00:46–01:03) |
| Strike | **ITM only** — not ATM, not OTM, not deep ITM. ~**100–200 points** ITM on all three. Delta ~**0.55–0.60** (ASR “555 से 6”) `[UNCERTAIN_TRANSCRIPT]` (~01:03–01:32) |
| TF | **2 minutes** for this specific system; 3m/5m allowed but speaker suggests 2m only after 5m confidence (~01:53–02:12) |
| Indicators | **EMA 10 and EMA 20** only. No oscillators. EMA not SMA/DEMA (~02:33–02:46) |
| Instruments | Long or short via CE/PE as desired (~01:34–01:37) |
| Beginners | **Should not scalp by buying options**; speaker says sell-side scalp OK, don’t buy-scalp (~13:10–13:17) — **conflicts with ITM buy description**; keep both as spoken |
| Stop | Should not be “more than” a bound tied to ITM option with delta 0.55–0.6 (~17:08–17:15); skip if stop too wide. Pullback/stop-hunt / 50% retrace language later `[UNCERTAIN_TRANSCRIPT]` |

Full candle-by-candle entries are in the transcript (~07:00–19:00): entries near stop clusters, trail or skip wide stops. Extract more detail in a later edit pass (`WAITING_FOR_EDIT`).

---

## Data

Spot (or futures — speaker used spot for BT) 2m OHLC; EMA(10), EMA(20); option chain ITM 100–200 pts / delta 0.55–0.6; bid/ask (scalps die on spread).

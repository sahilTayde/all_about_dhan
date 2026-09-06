# Team 02 — Math / indicator / Greeks VALIDATION

**Status:** `DRAFT` / `INDEPENDENTLY_VALIDATED` **partial** (concepts only).  
**Not** a rewrite of Dhan quotes. Layer B. External sources are **VALIDATION only**; production indicators remain Dhan-spoken + Dhan charts.

Official HQ tokens vs this layer: [`DHAN_INDICATOR_API_MAP.md`](DHAN_INDICATOR_API_MAP.md) (fetched with 01_research 2026-09-01). Supertrend / session VWAP are **not** annexure names.

Retrieved for this note: 2026-08-30.

---

## Method

Checked textbook/standard definitions (Hull *Options, Futures, and Other Derivatives* ch. 13/17; Black–Scholes Greeks lecture notes; common TA definitions: Appel MACD, Wilder RSI/ATR, session VWAP).  
Did **not** re-simulate Dhan screen numbers.

Verdict vocabulary: `supported` | `partially_supported` | `context-dependent` | `unsupported` | `UNKNOWN`.

---

## Options math

| Spoken claim (pointer) | Verdict | Notes |
|------------------------|---------|--------|
| Long option: loss limited to premium; profit theoretically large | **supported** | Long call/put payoff max(0, S−K)−premium / max(0, K−S)−premium. “Unlimited” is pedagogical; bounded by move + liquidity. |
| Short option: profit limited, loss can be large / “unlimited” | **supported** | Naked short call unbounded in theory; short put bounded by K. Spreads cap this. |
| Call = right to buy; put = right to sell at strike | **supported** | Standard. |
| Four parties (buy/sell × call/put) | **supported** | Accounting identity. |
| Premium ≈ intrinsic + time value | **supported** | American/European nuances; OTM intrinsic = 0 (supported; HAUS spoken). |
| ITM/ATM/OTM via immediate-exercise vs spot | **partially_supported** | Correct **for calls/puts vs spot** as taught. Index options in India are **European, cash-settled** — you cannot “exercise now into NIFTY.” Pedagogy still used for moneyness. Futures vs spot basis can shift ATM. |
| ATM call and put both ATM at same strike when S=K | **supported** (spot moneyness) | Put-call parity: ATM call/put prices differ by carry/dividends; “same ATM label” ≠ same premium. |
| 1 buyer + 1 seller = 1 OI | **supported** | Exchange OI definition. |
| Delta = ∂premium/∂underlying | **supported** | Hull. Per **point** of index, not per “₹100 move” unless you scale. Spoken 0.81 → ₹81 on ₹100 move is **delta×100**, a common desk shorthand — **context-dependent** (ignores gamma, IV, time). |
| Higher ITM → higher call delta; OTM smaller | **supported** | Call delta ∈ (0,1) approx; put ∈ (−1,0). |
| Theta = ∂premium/∂time, typically negative for long vanilla | **supported** | Deep ITM European **puts** can have positive theta in some rate/div settings — **context-dependent**. |
| Theta not linear; larger near expiry | **supported** | For ATM, theta typically peaks near expiry; deep ITM/OTM differ. “Exponential” is informal. |
| IV rises into events → premiums rise | **supported** | Vega>0 for long vanilla. |
| Seller “plays probability,” buyer “plays payout” | **context-dependent** | Not a theorem. Short premium often has high win-rate and left-tail; not 70% as a law. **unsupported** as a universal constant. |
| 93/7 or 7% club | **unsupported** (as math) | No derivation. Industry folklore / SEBI-style retail F&O loss stats exist in other documents — **not verified here**. `DATA_INSUFFICIENT` from this video. |
| Conviction % = delta | **unsupported** as identity | Delta is not a frequentist win probability of *your* setup. Risk-neutral N(d2) ≠ your edge. |
| Option P&L at a future S is determined only by delta | **unsupported** | Need gamma/vega/theta (speaker later correctly names this). |
| Volume **delta** (buy vol − sell vol) | **supported** as microstructure definition | **Different symbol** from Greek delta. Do not collapse. |
| VAH/VAL = 70% of volume | **context-dependent** | Common Market Profile / volume-profile convention (often ~70% ≈ 1σ if lognormal — **heuristic**, not a proof). |

---

## Indicator math

| Item | Verdict | Notes |
|------|---------|-------|
| MACD = EMA(fast)−EMA(slow); signal = EMA of MACD; hist = MACD−signal. Defaults 12/26/9 (Appel) | **supported** | HAUS “12 and 26” **supported**; signal 9 not clearly spoken. |
| MACD parameters ×4 (48/104/36 if 9×4) | **context-dependent** | Linear scale of periods is a **filter choice**, not a theorem. Does not “preserve purpose” in a proven sense. Exact 4× **UNKNOWN** (3× vs 4× spoken). |
| Histogram sign = trend | **partially_supported** | Hist>0 often aligned with MACD>signal; not a complete regime classifier. |
| SMA/EMA stack 10>30>100 | **supported** as a trend heuristic | No optimality. 9 vs 10 and 100 vs 300 are **SOURCE_UNCERTAIN**. |
| Supertrend ATR(10)×3 | **supported** as a **common default** (TV-style), not unique truth. Alternate 10×1 / 10×2 exist. |
| RSI Wilder 14; oversold ~30 | **supported** as Wilder’s original framing | Divergence is a **pattern**, not a proven predictor. |
| EMA 10/20 cross | **supported** as definition | Lagging; scalping sensitivity to noise **context-dependent**. |
| Session VWAP = Σ(P×V)/ΣV from session open | **supported** | **Requires traded volume.** Cash **NIFTY 50 index is not a traded tape** — VWAP on cash index is **unsupported / misuse**. VWAP on **index futures** or **options** is coherent. Spoken in 2RnBT9DDDNI: use futures — **supported**. |
| VWMA length 20 | **supported** as a definition | Volume-weighted MA ≠ VWAP. |

---

## Statistical claims from transcripts

| Claim | Verdict |
|-------|---------|
| 70% seller win / 33% buyer win / 70% no-trade | **unsupported** as constants |
| 20–30% premium target, 1:1 / 1:2 RR | **parameters as spoken**, not expectancy proofs |
| POP 80–85% on 1-3-2 | **unsupported** without a specified model + vol surface |

---

## Open UNKNOWN

- Dhan Super Scalper fast/slow EMA periods.
- Exact MACD triple after “×4.”
- Whether Dhan chain IV is Black–76 / BSM / exchange methodology — `VERIFY BEFORE IMPLEMENTATION` vs DhanHQ docs (Tier 2). Option-chain page lists `implied_volatility` / `greeks.*` **without** a model.
- Conditional Trigger `timeFrame` vs `timeframe`, sample `DAY` vs table `DATE`.
- Identity of quote `average_price` vs WS ATP vs chart session VWAP.
- Supertrend ATR period/multiplier on ScanX / tv.dhan.co (not in annexure).

---

## Handoff

Math layer does **not** approve strategies. Compatible concepts may be used as `HYPOTHESIS` inputs by 04_quant.

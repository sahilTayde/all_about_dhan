# SESSION_PREP_ML — paper start 09:30 IST Mon–Fri (flatten 15:16, ticks to 15:29)

**Team:** 06_backtesting (runbook) · 07 `packages/desk-ml` · 05 dual-tape  
**Date:** 2026-09-15 (IST)  
**Status:** `HYPOTHESIS` / **NO_PROMOTE** / `production_params_written: false`  
**Gate:** **not** `RESEARCH_READY_FOR_PROGRAMMING`  
**Orders:** refused. Do **not** enable `ExecutionClient`. No Super Order.

Education ≠ advice. Cluster / OU numbers are cache counts, not a win rate.

This is how to start **paper gather + overlay score**. **FOUNDER LOCK:** dual-tape live **Mon–Fri 09:30–15:29 IST only**. No Sat/Sun. NEW paper **09:30–15:16**; flatten all books **15:16**; ticks (no trade) until **15:29**. It is **not** a promote. Customer default stays `MIX-DEFAULT-BUY`. KEEP_ALL STRAT-001–014.

---

## Now (what is true)

| Piece | State |
|-------|--------|
| Dual-tape | `python -m trading_agents_india dual-tape` — INDEX LTP/1m + ATM CE/PE. No LLM. No orders. |
| ML-001 | KMeans k=4 + IsolationForest. Fit on warehouse `ohlc_bars`/`bars_1m` ∪ `premium_tape`. Seed **14**. Embargo last **5** 1m rows from fit (AFML analog, **not** CPCV / **not** OOS). |
| ML-002 | OU on residual + VWMA windows **40 / 60 / 90** only (max 3 tweaks). FOLLOW-GAP HOLD. SENSEX OU may be `DATA_INSUFFICIENT` / not mean-reverting on the thin ATM book. |
| Score CLI | `python -m desk_ml score --underlying NIFTY --source dual-tape` after two ticks with all three LTPs. |
| Live Super Order | **off** |

**FOLLOW-GAP:** index moved and ATM CE/PE did **not** confirm → overlay **HOLD**. Do not open a new paper CE/PE. Dealer note stays deterministic (`desk_divergence`). ML overlay may not override a hard stop.

---

## 09:30 first NEW / 15:16 flatten / 15:29 last tick (laptop, Mon–Fri only)

Do **not** restart npm / Vite. Do **not** start the old LLM `market-hours` loop (`paper_ops_STOPPED.flag` stays). Dual-tape only honours `paper_dual_tape_STOPPED.flag`.

```bash
cd /path/to/all_about_dhan

# Optional: cache inventory (no Dhan HTTP)
python -m desk_ml inventory --calendar-days 21

# Fit from warehouse + premium_tape if models missing under data/recon/ml/
python -m desk_ml fit --underlying NIFTY --seed 14 --embargo-bars 5
python -m desk_ml fit --underlying SENSEX --seed 14 --embargo-bars 5
python -m desk_ml mrr-fit --underlying NIFTY
python -m desk_ml mrr-fit --underlying SENSEX

# Paper dual-tape at the open (live chain; 0 = until stop flag)
python -m trading_agents_india dual-tape --live-chain --paper-train --paper-scalp --tick-seconds 10 --max-ticks 0
```

After **two** ticks with `index_ltp` + `atm_ce_ltp` + `atm_pe_ltp` on NIFTY (and SENSEX):

```bash
python -m desk_ml score --underlying NIFTY --source dual-tape
python -m desk_ml score --underlying SENSEX --source dual-tape
python -m desk_ml score --underlying NIFTY --source dual-tape --model-id both
python -m desk_ml overlay --source dual-tape
```

`session_action=HOLD` or `follow_gap=true` → **no new paper CE/PE**. `WATCH_ONLY` is still not a fill and not a MIX write.

Dual-tape persist also writes `paper_watch/DUAL-TAPE/overlay_last.json` (fail-soft). Thin ticks (<2 INDEX+CE+PE) → **HOLD**. Residual z is **causal** (past window only). `oos_claim: false`.

**Stop dual-tape:** `touch data/recon/paper_dual_tape_STOPPED.flag`

---

## HOLD rules (FOLLOW-GAP)

| Case | Action |
|------|--------|
| Index down, PE not up and/or CE not down | HOLD |
| Index up, CE not up | HOLD |
| Dual-tape missing ATM / stale / wrong strike | HOLD |
| ML-001 overlay HOLD / PREMIUM_DIVERGENCE | HOLD new paper CE/PE |
| ML-002 residual \|z\|≥2 or FOLLOW-GAP | HOLD |
| INDEX 1m `SIDEWAYS` (low ER / flips / tight band) | HOLD **new** paper CE/PE. Flatten/cancel still run. HYPOTHESIS. |
| Score CLI `DATA_INSUFFICIENT` | HOLD |

Do not treat `TREND_UP` / cluster id as BUY_CE.

**INDEX S/R (pre-market / first dual-tape walk):** `build_sr_levels` on INDEX 1m closes — previous IST day high/low/close (PDH/PDL/PDC), then today session high/low as prints arrive, plus swing proxies on 15m / 30m / 60m / 1d / 1w. A last-3 1m dump/rally does **not** override the ITM CE/PE bin until volume + candle + option premiums confirm, and not as a false break at those levels. Proxy POC is typical (H+L+C)/3, not order flow. **NO_PROMOTE.**

**Replay tape (18 Sep):** dual-tape persist writes `replay_index` / `replay_premium` / `replay_strike` / `replay_features` / `replay_decision` into local sqlite. INDEX 1m REST miss **carries** last LTP. Paper OPEN **and CLOSE** rows include `justification` (SUCCESS/LOSS/CANCEL). Ship overlay: NIFTY **CE or PE** + strength + max4, skip BN+SENSEX, no T2. See `BACKTEST_REPLAY_TAPE.md`.

**Two work types (do not mix):**

| Desk | Job | Tune when |
|------|-----|-----------|
| Signal | Dealer / logit / XR / greeks say CE or PE (strike/limit). ML-001/002 observe (no own side). | Later: inspect *what* they fired and *why*. |
| Booking | After fill: path SL, trail, STALL only in INDEX ER<0.35 chop; TREND ER≥0.35 same-wing is retracement hold. AGAINST / bin / unwind / IV. | Every session. Do not recode without founder confirm. |

Same ticket, different skill. Switching bins / watching the other wing is **booking**, not a new MIX. `python -m desk_ml fix-first` scores booking. ML retune is parked.

**FIX-FIRST drill (pre-open and post-market, every session):** write=false from **2026-09-17**. Labels each IST **hour** TRENDING / SIDEWAYS / CHOPPY / VOLATILE from INDEX 1m ER/flips/range (**not** itm_bin TREND; lunch ER ~0.05 is chop). Fill `market_kind` = open ER (missing → UNKNOWN); close kind stamped at exit. Hour kind scores **booking**. Same job also writes `signal_desk` (dealer vs logit vs XR vs observe) — **do not mix** with STALL/TARGET recodes. Overlay exits unchanged until founder confirms. `data/recon/fix_first_progress.json`. CLI: `python -m desk_ml fix-first` / `python -m jobs pre-market` / `python -m jobs post-market`.

---

## Must not

- `ExecutionClient` / Super Order / `/alerts/orders`
- Blocking LLM on this path
- `production_params_written: true`
- Promote from book-tune JSON
- Claim CPCV / OOS from the 5-bar embargo

```text
HANDOFF
From:     teams/06_backtesting
To:       founder / 00 / 05 / 07
Date:     2026-09-15
Status:   PAPER PREP / NO_PROMOTE / BACKTEST_REQUIRED
Gate:     not RESEARCH_READY_FOR_PROGRAMMING

Accepted: Dual-tape + desk_ml score at 09:15 IST. FOLLOW-GAP HOLD.
  FIX-FIRST pre-open + post-market drill from 17 Sep write=false. production_params_written false.
  ExecutionClient unused.
Rejected: Live Super Order; treat embargo as OOS; STRAT-015+.
UNKNOWN: Same-session ATM depth after open; SENSEX OU mean-reversion.
```
